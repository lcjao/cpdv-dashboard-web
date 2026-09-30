"""LegacyModel - 适配原始 Pipeline 模型

复用 model/multi_crack.py 的 MultiCrackPredictor 和 MultiCrackDualHead。
"""
from typing import Dict, Any, List, Optional, Tuple, Union
import torch
import torch.nn as nn
import sys
from pathlib import Path

from backend_framework.protocols import ModelProtocol
from backend_framework.registry.models import register_model


CODE_ROOT = Path(r"D:\研\土木水利\论文\代码\github")
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from model.multi_crack import (
    MultiCrackPredictor as _MultiCrackPredictor,
    MultiCrackDualHead as _MultiCrackDualHead,
)


@register_model("legacy")
class LegacyModel:
    """原始基础模型适配器 (单头)"""
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 256,
        num_layers: int = 3,
        max_cracks: int = 5,
        dropout: float = 0.2,
    ):
        self._model = _MultiCrackPredictor(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            max_cracks=max_cracks,
            dropout=dropout,
        )
        self.max_cracks = max_cracks
        self.output_dim = max_cracks * 2
        self.dual_head = False
        self._config = {
            "input_dim": input_dim,
            "hidden_dim": hidden_dim,
            "num_layers": num_layers,
            "max_cracks": max_cracks,
            "dropout": dropout,
        }
    
    @property
    def model(self) -> _MultiCrackPredictor:
        return self._model
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self._model(x)
    
    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        return self._model(x)
    
    def parameters(self):
        return self._model.parameters()
    
    def named_parameters(self):
        return self._model.named_parameters()
    
    def get_parameters(self) -> Dict[str, torch.Tensor]:
        return self._model.state_dict()
    
    def state_dict(self) -> Dict[str, torch.Tensor]:
        return self._model.state_dict()
    
    def load_state_dict(self, state_dict: Dict[str, torch.Tensor], strict: bool = True):
        self._model.load_state_dict(state_dict, strict=strict)
    
    def save(self, path: str, **metadata):
        save_dict = {
            "model_state_dict": self._model.state_dict(),
            **self._config,
            "dual_head": False,
            **metadata,
        }
        torch.save(save_dict, path)
    
    @classmethod
    def load(cls, path: str, device: torch.device = None) -> "LegacyModel":
        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            input_dim=checkpoint["input_dim"],
            hidden_dim=checkpoint.get("hidden_dim", 256),
            num_layers=checkpoint.get("num_layers", 3),
            max_cracks=checkpoint.get("max_cracks", 5),
            dropout=checkpoint.get("dropout", 0.2),
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        return model
    
    def decode_output(
        self,
        pred: torch.Tensor,
        threshold: float = 0.0,
        cls_threshold: float = 0.3,
    ) -> List[List[Dict]]:
        return self._model.decode_output(pred, threshold=threshold)
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            **self._config,
            "dual_head": False,
            "param_count": sum(p.numel() for p in self._model.parameters()),
        }
    
    def num_parameters(self) -> int:
        return sum(p.numel() for p in self._model.parameters())
    
    def train(self, mode: bool = True):
        self._model.train(mode)
        return self
    
    def eval(self):
        self._model.eval()
        return self
    
    def to(self, device: torch.device):
        self._model.to(device)
        return self


@register_model("legacy_dual_head")
class LegacyDualHeadModel:
    """原始双头模型适配器"""
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 256,
        num_layers: int = 3,
        max_cracks: int = 5,
        dropout: float = 0.2,
    ):
        self._model = _MultiCrackDualHead(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            max_cracks=max_cracks,
            dropout=dropout,
        )
        self.max_cracks = max_cracks
        self.output_dim = max_cracks * 2
        self.dual_head = True
        self._config = {
            "input_dim": input_dim,
            "hidden_dim": hidden_dim,
            "num_layers": num_layers,
            "max_cracks": max_cracks,
            "dropout": dropout,
        }
    
    @property
    def model(self) -> _MultiCrackDualHead:
        return self._model
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        return self._model(x)
    
    def __call__(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        return self._model(x)
    
    def parameters(self):
        return self._model.parameters()
    
    def named_parameters(self):
        return self._model.named_parameters()
    
    def get_parameters(self) -> Dict[str, torch.Tensor]:
        return self._model.state_dict()
    
    def state_dict(self) -> Dict[str, torch.Tensor]:
        return self._model.state_dict()
    
    def load_state_dict(self, state_dict: Dict[str, torch.Tensor], strict: bool = True):
        self._model.load_state_dict(state_dict, strict=strict)
    
    def save(self, path: str, **metadata):
        save_dict = {
            "model_state_dict": self._model.state_dict(),
            **self._config,
            "dual_head": True,
            **metadata,
        }
        torch.save(save_dict, path)
    
    @classmethod
    def load(cls, path: str, device: torch.device = None) -> "LegacyDualHeadModel":
        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            input_dim=checkpoint["input_dim"],
            hidden_dim=checkpoint.get("hidden_dim", 256),
            num_layers=checkpoint.get("num_layers", 3),
            max_cracks=checkpoint.get("max_cracks", 5),
            dropout=checkpoint.get("dropout", 0.2),
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        return model
    
    def decode_output(
        self,
        cls_pred: torch.Tensor,
        reg_pred: torch.Tensor,
        threshold: float = 0.0,
        cls_threshold: float = 0.3,
    ) -> List[List[Dict]]:
        return self._model.decode_output(cls_pred, reg_pred, cls_threshold=cls_threshold)
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            **self._config,
            "dual_head": True,
            "param_count": sum(p.numel() for p in self._model.parameters()),
        }
    
    def num_parameters(self) -> int:
        return sum(p.numel() for p in self._model.parameters())
    
    def train(self, mode: bool = True):
        self._model.train(mode)
        return self
    
    def eval(self):
        self._model.eval()
        return self
    
    def to(self, device: torch.device):
        self._model.to(device)
        return self