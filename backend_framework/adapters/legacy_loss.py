"""LegacyLoss - 适配原始 Pipeline 损失函数

复用 model/multi_crack.py 的 weighted_multi_crack_loss 和 MultiCrackDualHeadLoss。
"""
from typing import Dict, Any, Tuple, Union
import torch
import torch.nn as nn
import sys
from pathlib import Path

from backend_framework.protocols import LossProtocol
from backend_framework.registry.losses import register_loss


CODE_ROOT = Path(r"D:\研\土木水利\论文\代码\github")
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from model.multi_crack import (
    weighted_multi_crack_loss as _weighted_multi_crack_loss,
    MultiCrackDualHeadLoss as _MultiCrackDualHeadLoss,
)


@register_loss("legacy_weighted")
class LegacyWeightedLoss:
    """原始加权损失函数适配器 (单头模型)"""
    
    name = "legacy_weighted"
    
    def __init__(self, miss_weight: float = 5.0):
        self.miss_weight = miss_weight
    
    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        miss_weight = kwargs.get("miss_weight", self.miss_weight)
        return _weighted_multi_crack_loss(pred, target, miss_weight)
    
    def __call__(self, pred, target, **kwargs):
        return self.forward(pred, target, **kwargs)
    
    def get_config(self) -> Dict[str, Any]:
        return {"miss_weight": self.miss_weight, "name": self.name}
    
    def set_config(self, **kwargs):
        if "miss_weight" in kwargs:
            self.miss_weight = kwargs["miss_weight"]


@register_loss("legacy_dual_head")
class LegacyDualHeadLoss:
    """原始双头损失函数适配器"""
    
    name = "legacy_dual_head"
    
    def __init__(self, miss_weight: float = 5.0, reg_weight: float = 1.0):
        self._loss_fn = _MultiCrackDualHeadLoss(miss_weight=miss_weight, reg_weight=reg_weight)
        self.miss_weight = miss_weight
        self.reg_weight = reg_weight
    
    def forward(
        self,
        pred: Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]],
        target: torch.Tensor,
        **kwargs
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        if isinstance(pred, tuple):
            cls_pred, reg_pred = pred
        else:
            raise ValueError("DualHeadLoss 要求 pred 为 (cls_pred, reg_pred) 元组")
        
        miss_weight = kwargs.get("miss_weight", self.miss_weight)
        reg_weight = kwargs.get("reg_weight", self.reg_weight)
        
        # 临时更新权重
        if miss_weight != self._loss_fn.miss_weight or reg_weight != self._loss_fn.reg_weight:
            self._loss_fn.miss_weight = miss_weight
            self._loss_fn.reg_weight = reg_weight
        
        return self._loss_fn(cls_pred, reg_pred, target)
    
    def __call__(self, pred, target, **kwargs):
        return self.forward(pred, target, **kwargs)
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "miss_weight": self.miss_weight,
            "reg_weight": self.reg_weight,
            "name": self.name,
        }
    
    def set_config(self, **kwargs):
        if "miss_weight" in kwargs:
            self.miss_weight = kwargs["miss_weight"]
            self._loss_fn.miss_weight = kwargs["miss_weight"]
        if "reg_weight" in kwargs:
            self.reg_weight = kwargs["reg_weight"]
            self._loss_fn.reg_weight = kwargs["reg_weight"]