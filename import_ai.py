#import pandas as pd
#import numpy as np
#from pathlib import Path
#import sys
#import requests
import torch
#from torch import nn
#from torch.utils.data import Dataset, DataLoader
#from torchvision.transforms import ToTensor
#from torchvision import transforms
import torch.nn.functional as F
#from PIL import Image
#import os
#from torch.optim.lr_scheduler import ReduceLROnPlateau
#import torchvision.models as models
#from torchvision.models.detection import FasterRCNN
#from torchvision.models.detection.rpn import AnchorGenerator
#from torchvision.models import resnet50, ResNet50_Weights
#from torchvision.models.detection.backbone_utils import resnet_fpn_backbone
from torchvision.models.detection.roi_heads import RoIHeads
#from torchvision.models.detection.roi_heads import fastrcnn_loss
#import gc
#from collections import OrderedDict
#from timm.models import create_model
#from torchvision.ops.feature_pyramid_network import FeaturePyramidNetwork

# Device configuration
cuda_ = "cuda"
device = torch.device(cuda_ if torch.cuda.is_available() else "cpu")

class CustomRoIHeads(RoIHeads):
    def fastrcnn_loss(self, class_logits, box_regression, labels, regression_targets):
        # Classification loss with label smoothing
        from torchvision.ops import complete_box_iou
        classification_loss = F.cross_entropy(class_logits, labels, label_smoothing=0.1)
        
        # Combined box loss (GIoU + L1)
        giou_loss = complete_box_iou(box_regression, regression_targets, reduction="mean")
        l1_loss = F.smooth_l1_loss(box_regression, regression_targets, reduction="mean", beta=0.1)
        box_loss = 0.8 * giou_loss + 0.2 * l1_loss
        return classification_loss, box_loss

def create_model_resnet(num_classes, device):
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torchvision.models import resnet50
    try:
        from torchvision.models import ResNet50_Weights
        _weights = ResNet50_Weights.DEFAULT
    except Exception:
        _weights = None
    from torchvision.models.detection import FasterRCNN
    from torchvision.models.detection.rpn import AnchorGenerator

    class ResNetC5(nn.Module):
        def __init__(self, weights='DEFAULT'):
            super().__init__()
            if _weights is not None and weights == 'DEFAULT':
                backbone = resnet50(weights=_weights)
            else:
                backbone = resnet50(pretrained=True)
            # C5 output (2048 channels, stride 32)
            self.stem = nn.Sequential(*list(backbone.children())[:-2])
            self.reduce = nn.Conv2d(2048, 1536, kernel_size=1, bias=True)
            self.out_channels = 1536
            nn.init.kaiming_normal_(self.reduce.weight, mode='fan_out', nonlinearity='relu')
            if self.reduce.bias is not None:
                nn.init.constant_(self.reduce.bias, 0)

        def forward(self, x):
            x = self.stem(x)
            x = self.reduce(x)
            return x  # [B, 2048, H/32, W/32]

    class SPPNeck(nn.Module):
        def __init__(self, channels=1536, pool_sizes=(5, 9, 13)):
            super().__init__()
            self.pool_sizes = pool_sizes
            self.fuse = nn.Conv2d(channels * (1 + len(pool_sizes)), channels, kernel_size=1, bias=True)
            nn.init.kaiming_normal_(self.fuse.weight, mode='fan_out', nonlinearity='relu')
            if self.fuse.bias is not None:
                nn.init.constant_(self.fuse.bias, 0)

        def forward(self, x):
            feats = [x]
            for k in self.pool_sizes:
                feats.append(F.max_pool2d(x, kernel_size=k, stride=1, padding=k // 2))
            x = torch.cat(feats, dim=1)          # [B, 2048*4, H/32, W/32]
            x = self.fuse(x)                     # [B, 2048,   H/32, W/32]
            return x

    class BackboneWithNeck(nn.Module):
        def __init__(self, extractor, neck):
            super().__init__()
            self.extractor = extractor
            self.neck = neck
            self.out_channels = 1536  # informs heads

        def forward(self, x):
            x = self.extractor(x)
            x = self.neck(x)
            return x  # Tensor is fine; FasterRCNN will wrap as {'0': x}

    extractor = ResNetC5(weights='DEFAULT')
    neck = SPPNeck(channels=1536)
    backbone = BackboneWithNeck(extractor, neck)

    anchor_generator = AnchorGenerator(
        sizes=((71.3745, 115.2471, 164.0995, 203.9403, 256.9571, 377.2102),),  # sizes = scales
        aspect_ratios=((0.9839, 0.6845, 0.6977, 1.036, 0.9466),)
    )

    model = FasterRCNN(
        backbone=backbone,
        num_classes=num_classes + 1,
        rpn_anchor_generator=anchor_generator,
        box_score_thresh=0.5,
        box_nms_thresh=0.3,
        box_detections_per_img=100,
        box_fg_iou_thresh=0.6,
        box_bg_iou_thresh=0.4,
    ).to(device)

    # Custom RoI heads: 2048 * 7 * 7 -> 1024 -> 1024
    model.roi_heads = CustomRoIHeads(
        box_roi_pool=model.roi_heads.box_roi_pool,
        box_head=nn.Sequential(
            nn.Flatten(),
            nn.Linear(1536 * 7 * 7, 1024),
            nn.ReLU(inplace=True),
            nn.Linear(1024, 1024),
            nn.ReLU(inplace=True),
        ),
        box_predictor=model.roi_heads.box_predictor,
        fg_iou_thresh=0.6,
        bg_iou_thresh=0.4,
        batch_size_per_image=512,
        positive_fraction=0.4,
        bbox_reg_weights=None,
        score_thresh=0.03,
        nms_thresh=0.3,
        detections_per_img=100
    ).to(device)

    return model #looking for previous version? go to chatgpt recent logh                                            

