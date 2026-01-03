import os
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import numpy as np
from glob import glob
import pandas as pd
from collections import defaultdict
import json


# ----------------------------
# Model Architecture (copied from training)
# ----------------------------
class SPPNeck(nn.Module):
    """Spatial Pyramid Pooling neck"""
    def __init__(self, in_channels: int, bins=(1, 2, 4), proj_out: int = 512, use_bn=True):
        super().__init__()
        self.bins = bins
        self.in_channels = in_channels
        self.out_dim = in_channels * sum(b*b for b in bins)  # C * (1^2 + 2^2 + 4^2)
        
        self.proj = nn.Linear(self.out_dim, proj_out)
        self.norm = nn.LayerNorm(proj_out) if use_bn else nn.Identity()
        self.act = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        pooled = []
        for b in self.bins:
            p = nn.functional.adaptive_avg_pool2d(x, output_size=(b, b))
            pooled.append(p.flatten(1))
        v = torch.cat(pooled, dim=1)
        v = self.proj(v)
        v = self.norm(v)
        v = self.act(v)
        return v


class MultiViewSiameseRegressor(nn.Module):
    """Multi-view regression model (V10 architecture)"""
    def __init__(self, num_views, pretrained=True, fusion_method='attention'):
        super().__init__()
        self.num_views = num_views
        self.fusion_method = fusion_method

        # Backbone
        resnet = models.resnet50(pretrained=pretrained)
        self.backbone = nn.Sequential(*list(resnet.children())[:-2])
        backbone_channels = 2048

        # SPP Neck - outputs 1536 (not 512)
        self.spp = SPPNeck(
            in_channels=backbone_channels,
            bins=(1, 2, 4),
            proj_out=1536,
            use_bn=True
        )
        self.feature_dim = 1536

        # Feature projection
        self.feature_proj = nn.Sequential(
            nn.Linear(self.feature_dim, 1536),
            nn.ReLU(),
            nn.LayerNorm(1536)
        )

        # Fusion mechanism
        if fusion_method == 'attention':
            self.attention = nn.MultiheadAttention(
                embed_dim=1536,
                num_heads=8,
                batch_first=True
            )
            self.fusion_dim = 1536
        elif fusion_method == 'concat':
            self.fusion_dim = 1536 * num_views
        elif fusion_method == 'mean':
            self.fusion_dim = 1536
        else:
            raise ValueError(f"Unknown fusion method: {fusion_method}")

        # Neck MLP
        self.use_neck = True
        if self.use_neck:
            self.neck = nn.Sequential(
                nn.Linear(self.fusion_dim, self.fusion_dim),
                nn.ReLU(),
                nn.LayerNorm(self.fusion_dim),
                nn.Dropout(0.1)
            )

        # Regression head
        self.regressor = nn.Sequential(
            nn.Linear(self.fusion_dim, 1024),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(1024, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 1)
        )

    def forward(self, multi_view_input):
        """
        multi_view_input: (B, num_views, C, H, W)
        Returns: pred (B,)
        """
        B = multi_view_input.shape[0]
        view_features = []

        for i in range(self.num_views):
            view = multi_view_input[:, i]
            feat_map = self.backbone(view)
            spp_vec = self.spp(feat_map)
            feat = self.feature_proj(spp_vec)
            view_features.append(feat)

        stacked_features = torch.stack(view_features, dim=1)  # (B, num_views, 1536)

        # Fusion
        if self.fusion_method == 'attention':
            fused, _ = self.attention(stacked_features, stacked_features, stacked_features)
            fused = fused.mean(dim=1)  # (B, 1536)
        elif self.fusion_method == 'concat':
            if stacked_features.shape[1] < self.num_views:
                pad = self.num_views - stacked_features.shape[1]
                last = stacked_features[:, -1:].repeat(1, pad, 1)
                stacked_features = torch.cat([stacked_features, last], dim=1)
            elif stacked_features.shape[1] > self.num_views:
                stacked_features = stacked_features[:, :self.num_views]
            fused = stacked_features.flatten(1)  # (B, num_views*1536)
        else:  # 'mean'
            fused = stacked_features.mean(dim=1)  # (B, 1536)

        if self.use_neck:
            fused = fused + self.neck(fused)

        pred = self.regressor(fused).squeeze(1)  # (B,)
        return pred


# ----------------------------
# Testing Functions
# ----------------------------
def load_model(checkpoint_path, num_views=3, fusion_method='attention', device='cuda'):
    """Load trained model from checkpoint"""
    model = MultiViewSiameseRegressor(
        num_views=num_views,
        pretrained=False,  # Don't need pretrained weights when loading checkpoint
        fusion_method=fusion_method
    )
    
    # Load state dict
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    
    print(f"Model loaded from {checkpoint_path}")
    return model


def load_image_with_bbox(img_path, label_path, transform, min_bbox_size=15):
    """Load and crop image based on bounding box from label file"""
    try:
        # Read label
        with open(label_path, "r") as f:
            line = f.readline().strip()
        parts = line.split()
        
        if len(parts) < 8:
            print(f"Invalid label format in {label_path}")
            return None, None, None
        
        _, xc_s, yc_s, w_s, h_s, val_s, _, fruit_id = parts[:8]
        
        xc = float(xc_s)
        yc = float(yc_s)
        w = float(w_s)
        h = float(h_s)
        true_value = float(val_s)
        
        # Load image
        img = Image.open(img_path).convert('RGB')
        W, H = img.size
        
        # Convert normalized coords to pixels
        x1 = int((xc - w/2) * W)
        y1 = int((yc - h/2) * H)
        x2 = int((xc + w/2) * W)
        y2 = int((yc + h/2) * H)
        
        # Ensure valid bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(W, x2)
        y2 = min(H, y2)
        
        # Check if bbox is too small
        if (x2 - x1) < min_bbox_size or (y2 - y1) < min_bbox_size:
            print(f"Bbox too small in {img_path}, using full image")
            cropped = img
        else:
            # Add padding
            pad = 5
            x1p = max(0, x1 - pad)
            y1p = max(0, y1 - pad)
            x2p = min(W, x2 + pad)
            y2p = min(H, y2 + pad)
            cropped = img.crop((x1p, y1p, x2p, y2p))
        
        # Apply transform
        if transform:
            cropped = transform(cropped)
        
        return cropped, true_value, fruit_id
    
    except Exception as e:
        print(f"Error loading {img_path}: {e}")
        return None, None, None


def test_model(model, img_dir, label_dir, transform, num_views=3, device='cuda', img_ext='.jpg'):
    """
    Test model on all images in the directory (each image treated independently)
    
    Returns:
        DataFrame with predictions and ground truth values
    """
    model.eval()
    
    txt_files = sorted(glob(os.path.join(label_dir, "*.txt")))
    
    print(f"Found {len(txt_files)} label files")
    
    results = []
    
    with torch.no_grad():
        for txt_file in txt_files:
            base_name = os.path.basename(txt_file)
            img_name = base_name.replace('.txt', img_ext)
            img_path = os.path.join(img_dir, img_name)
            
            if not os.path.exists(img_path):
                continue
            
            # Load the image
            tensor, true_value, fruit_id = load_image_with_bbox(img_path, txt_file, transform)
            
            if tensor is None:
                continue
            
            # Replicate the single image to fill num_views (treating as same view repeated)
            view_tensors = [tensor] * num_views
            
            # Stack and predict
            multi_view_tensor = torch.stack(view_tensors, dim=0).unsqueeze(0).to(device)  # [1, V, C, H, W]
            
            prediction = model(multi_view_tensor).cpu().item()
            
            results.append({
                'image_name': img_name,
                'fruit_id': fruit_id,
                'predicted_value': prediction,
                'true_value': true_value,
                'error': abs(prediction - true_value) if true_value is not None else None
            })
            
            if len(results) % 50 == 0:
                print(f"Processed {len(results)} images...")
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Calculate metrics
    if 'error' in df.columns:
        mae = df['error'].mean()
        rmse = np.sqrt((df['error'] ** 2).mean())
        
        print(f"\n{'='*50}")
        print(f"Test Results Summary")
        print(f"{'='*50}")
        print(f"Total images tested: {len(df)}")
        print(f"Mean Absolute Error (MAE): {mae:.4f}")
        print(f"Root Mean Squared Error (RMSE): {rmse:.4f}")
        print(f"{'='*50}\n")
    
    return df


def test_single_fruit(model, image_paths, transform, device='cuda', label_paths=None):
    """
    Test model on a single fruit given 1-3 image paths
    
    Args:
        model: trained model
        image_paths: list of 1-3 image paths (if less than num_views, will be repeated)
        transform: image transformation
        device: device to run on
        label_paths: optional list of label paths for bbox cropping (if None, uses full image)
    
    Returns:
        predicted value
    """
    model.eval()
    
    view_tensors = []
    
    with torch.no_grad():
        for idx, img_path in enumerate(image_paths):
            # If label path provided, crop using bbox
            if label_paths and idx < len(label_paths):
                tensor, _, _ = load_image_with_bbox(img_path, label_paths[idx], transform)
                if tensor is not None:
                    view_tensors.append(tensor)
            else:
                # Just load and transform the full image
                img = Image.open(img_path).convert('RGB')
                if transform:
                    img_tensor = transform(img)
                    view_tensors.append(img_tensor)
        
        # Ensure we have the right number of views
        num_views = model.num_views
        if len(view_tensors) == 0:
            raise ValueError("No valid images loaded")
        
        # Replicate to fill num_views if needed
        if len(view_tensors) < num_views:
            while len(view_tensors) < num_views:
                view_tensors.append(view_tensors[-1])
        elif len(view_tensors) > num_views:
            view_tensors = view_tensors[:num_views]
        
        multi_view_tensor = torch.stack(view_tensors, dim=0).unsqueeze(0).to(device)
        prediction = model(multi_view_tensor).cpu().item()
    
    return prediction


# ----------------------------
# Main Testing Script
# ----------------------------
if __name__ == "__main__":
    # Configuration
    CHECKPOINT_PATH = "V10_siamese_attention_Ichannel_fold4-sweetness-gauge.pth"  # Update this path
    IMG_DIR = "test"
    LABEL_DIR = "test_label"
    NUM_VIEWS = 3
    FUSION_METHOD = 'attention'  # Should match training
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"Using device: {DEVICE}")
    
    # Define transform (same as validation transform in training)
    transform_test = transforms.Compose([
        transforms.Resize((512, 512)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.4259037971496582, 0.4447304904460907, 0.3118171691894531],
            std=[0.2147604376077652, 0.20491182804107666, 0.1996799111366272]
        )
    ])
    
    # Load model
    print("Loading model...")
    model = load_model(CHECKPOINT_PATH, NUM_VIEWS, FUSION_METHOD, DEVICE)
    
    # Test on all images
    print("\nTesting model on dataset...")
    results_df = test_model(
        model=model,
        img_dir=IMG_DIR,
        label_dir=LABEL_DIR,
        transform=transform_test,
        num_views=NUM_VIEWS,
        device=DEVICE
    )
    
    # Save results
    results_df.to_csv("test_predictions.csv", index=False)
    print("\nResults saved to test_predictions.csv")
    
    # Show some examples
    print("\nSample Predictions:")
    print(results_df.head(10).to_string(index=False))
    
    # Example: Test on 1-3 specific images (watermelon photos)
    print("\n" + "="*50)
    print("Example: Testing on specific images")
    print("="*50)
    print("You can test with 1-3 watermelon images.")
    print("If you provide fewer than 3 images, the last image will be repeated.")
    
    # Uncomment and modify these lines to test specific images
    # Single image example:
    # prediction = test_single_fruit(model, ["path/to/watermelon.jpg"], transform_test, DEVICE)
    # print(f"Predicted value (1 image): {prediction:.4f}°Bx")
    
    # Multiple images example:
    # example_images = [
    #     "All/Img/example1.jpg",
    #     "All/Img/example2.jpg",
    #     "All/Img/example3.jpg"
    # ]
    # prediction = test_single_fruit(model, example_images, transform_test, DEVICE)
    # print(f"Predicted value (3 images): {prediction:.4f}°Bx")