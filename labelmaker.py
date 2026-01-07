# labelmaker.py
import os
import cv2
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from test_file import _Objectdetection_test_RESNET_SPPAN
import PIL.ImageOps as ImageOps
#from new_test_file import create_model_resnet

# ---------------------------
# Configuration Section
# ---------------------------
MODEL_PATH = "V17_model_resnet.pth"   # Adjust if needed
IMAGE_DIR = "test"  # Folder with input images
LABELS_DIR = "test_label"
MISLABELED_DIR = "mislabeled"
CONFIDENCE_THRESHOLD = 0.5
FIXED_QUALITY_RATING = 1  # used for AUTO detections only



# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Provide one sugar content (float) per image to be processed, in order.
# If there are more images than entries here, the remaining images use 0.0.
SUGAR_VALUES = [0.0]
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Ensure necessary directories exist
os.makedirs(LABELS_DIR, exist_ok=True)
os.makedirs(MISLABELED_DIR, exist_ok=True)

print("Loading model...")
detector = _Objectdetection_test_RESNET_SPPAN(MODEL_PATH)

def load_and_preprocess_image(img_path):
    """Load image and apply the same preprocessing as the detector for consistent display"""
    image = Image.open(img_path).convert("RGB")
    orig_w, orig_h = image.size

    target_size = 512
    scale = target_size / max(orig_w, orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    # Resize maintaining aspect ratio
    img_resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Pad to square
    img_padded = Image.new('RGB', (target_size, target_size), (114, 114, 114))
    pad_x = (target_size - new_w) // 2
    pad_y = (target_size - new_h) // 2
    img_padded.paste(img_resized, (pad_x, pad_y))

    return np.array(img_padded), (orig_w, orig_h), (pad_x, pad_y), scale

class ManualBoxDrawer:
    """OpenCV-based click-drag rectangle drawer (more reliable than global screen listeners)."""
    def __init__(self, image_512):
        self.img = image_512.copy()
        self.preview = image_512.copy()
        self.drawing = False
        self.start_pt = None
        self.end_pt = None
        self.done = False

    def _mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_pt = (x, y)
            self.end_pt = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.end_pt = (x, y)
            self.preview = self.img.copy()
            cv2.rectangle(self.preview, self.start_pt, self.end_pt, (0, 255, 0), 2)
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.end_pt = (x, y)
            self.preview = self.img.copy()
            cv2.rectangle(self.preview, self.start_pt, self.end_pt, (0, 255, 0), 2)

    def draw(self, win_name="Manual Box: click-drag, ENTER to confirm, ESC to skip"):
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 700, 700)
        cv2.setMouseCallback(win_name, self._mouse)

        while True:
            cv2.imshow(win_name, self.preview)
            k = cv2.waitKey(10) & 0xFF
            if k == 13:  # Enter to confirm
                if self.start_pt and self.end_pt:
                    x1, y1 = self.start_pt
                    x2, y2 = self.end_pt
                    x1, x2 = sorted([x1, x2])
                    y1, y2 = sorted([y1, y2])
                    cv2.destroyWindow(win_name)
                    return x1, y1, x2, y2
                else:
                    # nothing drawn; keep waiting
                    pass
            elif k == 27:  # ESC to cancel/skip
                cv2.destroyWindow(win_name)
                return None

def map_display_box_to_original(box_disp, pad_x, pad_y, scale, orig_w, orig_h):
    """Inverse of display mapping: from 512-padded coords -> original image coords."""
    x1d, y1d, x2d, y2d = box_disp
    x1o = (x1d - pad_x) / scale
    y1o = (y1d - pad_y) / scale
    x2o = (x2d - pad_x) / scale
    y2o = (y2d - pad_y) / scale
    # clip to original bounds
    x1o = np.clip(x1o, 0, orig_w - 1)
    x2o = np.clip(x2o, 0, orig_w - 1)
    y1o = np.clip(y1o, 0, orig_h - 1)
    y2o = np.clip(y2o, 0, orig_h - 1)
    return float(x1o), float(y1o), float(x2o), float(y2o)

# Gather images
image_extensions = ['.jpg', '.jpeg', '.png']
image_dir = Path(IMAGE_DIR)
image_files = [p for p in image_dir.iterdir() if p.suffix.lower() in image_extensions]
image_files.sort()  # stable, predictable order matching SUGAR_VALUES

print(f"Found {len(image_files)} image(s) to process.")

# Iterate with index to align sugar values
for idx, image_path in enumerate(image_files):
    print(f"\nProcessing: {image_path.name}")
    try:
        # Get image-level sugar (default 0.0 if not provided)
        sugar = float(SUGAR_VALUES[idx]) if idx < len(SUGAR_VALUES) else 0.0

        # Run detector
        results = detector.predict(str(image_path), confident_interval=CONFIDENCE_THRESHOLD)

        # Load original for dimensions & potential copy
        original_image = Image.open(image_path).convert("RGB")
        orig_w, orig_h = original_image.size

        # Preprocessed preview for consistent visualization
        display_img, (_, _), (pad_x, pad_y), scale = load_and_preprocess_image(str(image_path))

        boxes = results['boxes']
        labels = results['labels']
        scores = results['scores']

        label_lines = []

        if len(boxes) == 0:
            print("No detections found — entering manual box mode.")
            # Show the 512x512 display image and let user draw a box
            drawer = ManualBoxDrawer(display_img)
            drawn = drawer.draw()

            if drawn is not None:
                # Map back to original image coordinates
                x1o, y1o, x2o, y2o = map_display_box_to_original(drawn, pad_x, pad_y, scale, orig_w, orig_h)

                # Minimal prompts for manual case: class and quality
                try:
                    lab = int(input("Enter class id for manual box (e.g., 0): ").strip())
                except Exception:
                    lab = 0
                try:
                    quality = int(input("Enter quality rating for manual box (int): ").strip())
                except Exception:
                    quality = FIXED_QUALITY_RATING

                # Convert to YOLO (normalized)
                x_center = ((x1o + x2o) / 2.0) / orig_w
                y_center = ((y1o + y2o) / 2.0) / orig_h
                width    = (x2o - x1o) / orig_w
                height   = (y2o - y1o) / orig_h

                label_lines.append(f"{lab} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f} {sugar:.2f} {quality}\n")

                # Save label
                label_file = Path(LABELS_DIR) / (image_path.stem + ".txt")
                with open(label_file, 'w') as f:
                    f.writelines(label_lines)

                print(f"Saved 1 manual object to {label_file}")
            else:
                print("Manual mode skipped; no label written for this image.")

            # Single remaining prompt
            move_mis = input("Did the model mislabel anything? Move to mislabeled? (y/n): ").strip().lower()
            if move_mis == 'y':
                cv2.imwrite(str(Path(MISLABELED_DIR) / image_path.name),
                            cv2.cvtColor(np.array(original_image), cv2.COLOR_RGB2BGR))
            continue  # proceed to next image

        # If we have detections: draw on display image for visual QA
        display_boxes = boxes.copy()
        if len(display_boxes) > 0:
            display_boxes[:, [0, 2]] = display_boxes[:, [0, 2]] * scale + pad_x
            display_boxes[:, [1, 3]] = display_boxes[:, [1, 3]] * scale + pad_y
            display_boxes[:, [0, 2]] = np.clip(display_boxes[:, [0, 2]], 0, 511)
            display_boxes[:, [1, 3]] = np.clip(display_boxes[:, [1, 3]], 0, 511)

        display_img_with_boxes = display_img.copy()
        for (x1, y1, x2, y2) in display_boxes.astype(int):
            cv2.rectangle(display_img_with_boxes, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow("Detected Image", cv2.cvtColor(display_img_with_boxes, cv2.COLOR_RGB2BGR))
        cv2.waitKey(1)

        # Write labels (AUTO case uses fixed quality = 1)
        for lab, (x1, y1, x2, y2) in zip(labels, boxes):
            x_center = ((x1 + x2) / 2.0) / orig_w
            y_center = ((y1 + y2) / 2.0) / orig_h
            width    = (x2 - x1) / orig_w
            height   = (y2 - y1) / orig_h
            lab = int(lab) if hasattr(lab, "item") else int(lab)
            label_lines.append(f"{lab} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f} {sugar:.2f} {FIXED_QUALITY_RATING}\n")

        label_file = Path(LABELS_DIR) / (image_path.stem + ".txt")
        with open(label_file, 'w') as f:
            f.writelines(label_lines)

        print(f"Saved {len(label_lines)} objects to {label_file}")

        # SINGLE remaining prompt per your earlier requirement
        move_mis = input("Did the model mislabel anything? Move to mislabeled? (y/n): ").strip().lower()
        if move_mis == 'y':
            cv2.imwrite(str(Path(MISLABELED_DIR) / image_path.name),
                        cv2.cvtColor(np.array(original_image), cv2.COLOR_RGB2BGR))

    except Exception as e:
        print(f"Error processing {image_path.name}: {e}")
        continue
    finally:
        cv2.destroyAllWindows()

print("\nAll images processed.")
