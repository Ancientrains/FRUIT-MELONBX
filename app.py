import io
import os
import zipfile
from typing import List

from flask import Flask, jsonify, request, send_from_directory, send_file
from PIL import Image, ImageDraw, ImageFont
import torch
from torchvision import transforms

from detector import ObjectDetectionResnetSPPAN
from SSL_test import load_model


APP_ROOT = "template"
DETECTOR_MODEL_PATH = "static/V17_model_resnet.pth"
SSL_MODEL_PATH = "static/V10_kfold_siamese_SPP_attention_Ichannel.txt_fold4_best.pth"
CONFIDENCE_THRESHOLD = 0.5
NUM_VIEWS = 3

DEVICE = torch.device("cpu")

app = Flask(__name__, static_folder=APP_ROOT, static_url_path="")


def build_ssl_transform():
    return transforms.Compose([
        transforms.Resize((512, 512)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.4259037971496582, 0.4447304904460907, 0.3118171691894531],
            std=[0.2147604376077652, 0.20491182804107666, 0.1996799111366272],
        ),
    ])


def crop_image(image: Image.Image, box):
    if box is None:
        return image
    x1, y1, x2, y2 = box
    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(image.width, int(x2))
    y2 = min(image.height, int(y2))
    if x2 <= x1 or y2 <= y1:
        return image
    return image.crop((x1, y1, x2, y2))


def select_best_box(results):
    boxes = results.get("boxes")
    scores = results.get("scores")
    if boxes is None or scores is None or len(boxes) == 0:
        return None
    best_idx = int(scores.argmax())
    return boxes[best_idx]


def select_best_label(results):
    boxes = results.get("boxes")
    scores = results.get("scores")
    labels = results.get("labels")
    if boxes is None or scores is None or labels is None or len(boxes) == 0:
        return None
    best_idx = int(scores.argmax())
    return {
        "box": boxes[best_idx],
        "label": int(labels[best_idx]),
        "score": float(scores[best_idx]),
    }


def build_view_tensors(images: List[Image.Image], detector, transform):
    view_tensors = []
    for image in images:
        results = detector.predict_image(image, confident_interval=CONFIDENCE_THRESHOLD)
        best_box = select_best_box(results)
        if best_box is None:
            continue
        cropped = crop_image(image, best_box)
        view_tensors.append(transform(cropped))

    if not view_tensors:
        return None

    while len(view_tensors) < NUM_VIEWS:
        view_tensors.append(view_tensors[-1])
    if len(view_tensors) > NUM_VIEWS:
        view_tensors = view_tensors[:NUM_VIEWS]
    return torch.stack(view_tensors, dim=0).unsqueeze(0)


def load_images_from_request(files):
    images = []
    for idx, f in enumerate(files):
        data = f.read()
        if not data:
            continue
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            continue
        name = f.filename or f"image_{idx + 1}.png"
        base, _ = os.path.splitext(name)
        images.append({"name": base or f"image_{idx + 1}", "image": img})
    return images


def annotate_image(image: Image.Image, label_info, brix_value: float):
    if label_info is None:
        label_line = f"brix {brix_value:.3f}\nno_detection\n"
        return image.copy(), label_line

    box = label_info["box"]
    class_id = label_info["label"]
    score = label_info["score"]
    class_name = detector.class_names.get(class_id, f"class_{class_id}")

    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.load_default()

    x1, y1, x2, y2 = map(float, box)
    draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)

    label_text = f"{class_name} {score:.2f}"
    text_x = max(0, int(x1))
    text_y = max(0, int(y1) - 12)
    draw.text((text_x, text_y), label_text, fill=(255, 0, 0), font=font)

    label_line = (
        f"brix {brix_value:.3f}\n"
        f"{class_id} {class_name} {score:.4f} {x1:.1f} {y1:.1f} {x2:.1f} {y2:.1f}\n"
    )
    return annotated, label_line


def predict_brix_for_box(image: Image.Image, box):
    if box is None:
        return 0.0
    cropped = crop_image(image, box)
    view = ssl_transform(cropped)
    views = view.unsqueeze(0).repeat(NUM_VIEWS, 1, 1, 1).unsqueeze(0)
    with torch.no_grad():
        prediction = ssl_model(views.to(DEVICE)).cpu().item()
    return round(float(prediction), 3)


detector = ObjectDetectionResnetSPPAN(DETECTOR_MODEL_PATH, device=DEVICE)
ssl_model = load_model(SSL_MODEL_PATH, num_views=NUM_VIEWS, fusion_method="attention", device=DEVICE)
ssl_transform = build_ssl_transform()


@app.get("/")
def index():
    return send_from_directory(APP_ROOT, "v2index.html")


@app.get("/fonts/<path:filename>")
def fonts(filename):
    return send_from_directory("fonts", filename)


@app.post("/api/predict")
def predict():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "No images provided."}), 400

    items = load_images_from_request(files)
    if not items:
        return jsonify({"error": "No valid images provided."}), 400
    images = [item["image"] for item in items]

    with torch.no_grad():
        views = build_view_tensors(images, detector, ssl_transform)
        if views is None:
            prediction = 0.0
        else:
            views = views.to(DEVICE)
            prediction = round(ssl_model(views).cpu().item(), 3)

    return jsonify({"sweetness": float(prediction)})


@app.post("/api/annotate")
def annotate():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "No images provided."}), 400

    items = load_images_from_request(files)
    if not items:
        return jsonify({"error": "No valid images provided."}), 400

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            image = item["image"]
            name = item["name"]

            results = detector.predict_image(image, confident_interval=CONFIDENCE_THRESHOLD)
            label_info = select_best_label(results)
            box = label_info["box"] if label_info else None
            brix_value = predict_brix_for_box(image, box)
            annotated, label_line = annotate_image(image, label_info, brix_value)

            img_buf = io.BytesIO()
            annotated.save(img_buf, format="PNG")
            zf.writestr(f"{name}_boxed.png", img_buf.getvalue())
            zf.writestr(f"{name}_label.txt", label_line)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="labeled_images.zip",
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
