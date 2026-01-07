
import numpy as np
import matplotlib.patches as patches
import torch
from torchvision import transforms
from PIL import Image
from matplotlib import pyplot as plt

import os
from collections import OrderedDict
cuda_ = "cuda"
device = torch.device(cuda_ if torch.cuda.is_available() else "cpu")
    
from import_ai import create_model_resnet
class _Objectdetection_test_RESNET_SPPAN():
    def __init__(self, model_path, device = None):
        self.class_names = {
        0: 'apple',
        1: 'oranges',
        2: 'pears',
        3: 'watermelon',
        4: 'lemon',
        5: 'korean melons',
        6: 'cantalop'
        }
        self.device = device or torch.device(cuda_ if torch.cuda.is_available() else "cpu")
        self.model = self.load_model(model_path)
        self.transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.65496546, 0.5711497, 0.4338386],
            std=[0.27230927, 0.27169436, 0.3182361]
        )
    ])

    def load_model(self, model_path):
        model = create_model_resnet(len(self.class_names), device=self.device)
        checkpoint = torch.load(model_path, map_location=self.device)
        model.load_state_dict(checkpoint)
        model.to(self.device)
        model.eval()
        return model
    
    def predict(self, img_path, confident_interval):
        image = Image.open(img_path).convert("RGB")
        orig_w, orig_h = image.size
        
        # Resize while maintaining aspect ratio (common sizes: 640x640, 1024x1024)
        target_size = 512
        img_resized = image.copy()
        
        # Calculate new dimensions
        scale = target_size / max(orig_w, orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
        # Resize image
        img_resized = img_resized.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Pad to square
        img_padded = Image.new('RGB', (target_size, target_size), (114, 114, 114))
        pad_x = (target_size - new_w) // 2
        pad_y = (target_size - new_h) // 2
        img_padded.paste(img_resized, (pad_x, pad_y))
        
        # Transform and predict
        img_t = self.transform(img_padded).to(self.device)
        
        with torch.no_grad():
            pred = self.model([img_t])[0]
            keep = pred['scores'] > confident_interval
            boxes = pred['boxes'][keep].cpu().numpy()
            scores = pred['scores'][keep].cpu().numpy()
            labels = pred['labels'][keep].cpu().numpy()
        
        # Correct boxes back to original coordinates
        if boxes.size > 0:
            # Remove padding offset
            boxes[:, [0, 2]] -= pad_x
            boxes[:, [1, 3]] -= pad_y
            # Scale back to original size
            boxes[:, [0, 2]] /= scale
            boxes[:, [1, 3]] /= scale
            # Clip to image bounds
            boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, orig_w - 1)
            boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, orig_h - 1)
        
        return {
            'boxes': boxes,
            'scores': scores,
            'labels': labels,
            'image': np.array(image)
        }
    
    def visualizing(self, results, save_path=None):
        boxes  = results['boxes']
        labels = results['labels']
        scores = results['scores']

        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        ax.imshow(results['image'])

        for box, score, label in zip(boxes, scores, labels):
            x1, y1, x2, y2 = box
            rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                                    linewidth=2, edgecolor='red', facecolor='none')
            ax.add_patch(rect)
            class_name = self.class_names.get(int(label), f'class_{int(label)}')
            text_y = max(y1 - 10, 10)
            ax.text(x1, text_y, f'{class_name}: {score:.2f}',
                    bbox=dict(facecolor='red', alpha=0.8), fontsize=10, color='white')

        ax.axis('off')
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=150)
        plt.show()

    def predict_debug(self, img_path, confident_interval):
        # Fix: Consistent image loading
        image = Image.open(img_path).convert("RGB")
        orig_w, orig_h = image.size
        
        # Use same preprocessing as predict method
        target_size = 512
        scale = target_size / max(orig_w, orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
        img_resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        img_padded = Image.new('RGB', (target_size, target_size), (114, 114, 114))
        pad_x = (target_size - new_w) // 2
        pad_y = (target_size - new_h) // 2
        img_padded.paste(img_resized, (pad_x, pad_y))
        
        img_t = self.transform(img_padded).to(self.device)
        
        with torch.no_grad():
            # Fix: Add batch dimension
            pred = self.model(img_t.unsqueeze(0))[0]
            
            # Debug: Print raw predictions
            print(f"Raw predictions:")
            print(f"  Boxes shape: {pred['boxes'].shape}")
            print(f"  Scores shape: {pred['scores'].shape}")
            print(f"  Labels shape: {pred['labels'].shape}")
            
            # Handle empty predictions
            if len(pred['scores']) > 0:
                print(f"  Max score: {pred['scores'].max():.4f}")
                print(f"  Min score: {pred['scores'].min():.4f}")
                print(f"  Mean score: {pred['scores'].mean():.4f}")
                print(f"  Scores > 0.01: {(pred['scores'] > 0.01).sum()}")
                print(f"  Scores > 0.1: {(pred['scores'] > 0.1).sum()}")
                print(f"  Scores > 0.3: {(pred['scores'] > 0.3).sum()}")
            else:
                print(f"  No detections found (empty scores tensor)")
                print(f"  Scores > 0.01: 0")
                print(f"  Scores > 0.1: 0") 
                print(f"  Scores > 0.3: 0")
            
            keep = pred['scores'] > confident_interval
            print(f"  Keeping {keep.sum()} detections with threshold {confident_interval}")
            
            boxes = pred['boxes'][keep].cpu().numpy()
            scores = pred['scores'][keep].cpu().numpy()
            labels = pred['labels'][keep].cpu().numpy()
        
        # Apply same box corrections as in predict method
        if boxes.size > 0:
            boxes[:, [0, 2]] -= pad_x
            boxes[:, [1, 3]] -= pad_y
            boxes[:, [0, 2]] /= scale
            boxes[:, [1, 3]] /= scale
            boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, orig_w - 1)
            boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, orig_h - 1)
        
        return {
            'boxes': boxes,
            'scores': scores,
            'labels': labels,
            'image': np.array(image)
        }