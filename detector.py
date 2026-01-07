import torch
import numpy as np
from PIL import Image
from torchvision import transforms

from import_ai import create_model_resnet

class ObjectDetectionResnetSPPAN:
    def __init__(self, model_path, device=None):
        self.class_names = {
            0: "apple",
            1: "oranges",
            2: "pears",
            3: "watermelon",
            4: "lemon",
            5: "korean melons",
            6: "cantalop",
        }
        self.device = device or torch.device("cpu")
        self.model = self.load_model(model_path)
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.65496546, 0.5711497, 0.4338386],
                std=[0.27230927, 0.27169436, 0.3182361],
            ),
        ])

    def load_model(self, model_path):
        model = create_model_resnet(len(self.class_names), device=self.device)
        checkpoint = torch.load(model_path, map_location=self.device)
        model.load_state_dict(checkpoint)
        model.to(self.device)
        model.eval()
        return model

    def predict_path(self, img_path, confident_interval=0.5):
        image = Image.open(img_path).convert("RGB")
        return self.predict_image(image, confident_interval=confident_interval)

    def predict_image(self, image, confident_interval=0.5):
        orig_w, orig_h = image.size
        target_size = 512

        scale = target_size / max(orig_w, orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)

        img_resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        img_padded = Image.new("RGB", (target_size, target_size), (114, 114, 114))
        pad_x = (target_size - new_w) // 2
        pad_y = (target_size - new_h) // 2
        img_padded.paste(img_resized, (pad_x, pad_y))

        img_t = self.transform(img_padded).to(self.device)

        with torch.no_grad():
            pred = self.model([img_t])[0]
            keep = pred["scores"] > confident_interval
            boxes = pred["boxes"][keep].cpu().numpy()
            scores = pred["scores"][keep].cpu().numpy()
            labels = pred["labels"][keep].cpu().numpy()

        if boxes.size > 0:
            boxes[:, [0, 2]] -= pad_x
            boxes[:, [1, 3]] -= pad_y
            boxes[:, [0, 2]] /= scale
            boxes[:, [1, 3]] /= scale
            boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, orig_w - 1)
            boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, orig_h - 1)

        return {
            "boxes": boxes,
            "scores": scores,
            "labels": labels,
            "image": np.array(image),
        }
