import torch
import torch.nn as nn
from torchvision import models


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

