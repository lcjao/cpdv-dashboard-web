"""LegacyOptimizer - 适配原始 Pipeline 优化器

封装 PyTorch Adam/AdamW，提供统一接口。
"""
from typing import Dict, Any, Iterator, Optional, Tuple
import torch
import torch.optim as optim

from backend_framework.protocols import OptimizerProtocol
from backend_framework.registry.optimizers import register_optimizer


@register_optimizer("legacy_adamw")
class LegacyAdamW:
    """原始 AdamW 优化器适配器"""
    
    name = "legacy_adamw"
    
    def __init__(
        self,
        model_params: Iterator[torch.nn.Parameter],
        lr: float = 1e-3,
        weight_decay: float = 1e-5,
        betas: Tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
    ):
        self._optimizer = optim.AdamW(
            model_params,
            lr=lr,
            weight_decay=weight_decay,
            betas=betas,
            eps=eps,
        )
        self._config = {
            "lr": lr,
            "weight_decay": weight_decay,
            "betas": betas,
            "eps": eps,
        }
    
    def step(self):
        self._optimizer.step()
    
    def zero_grad(self, set_to_none: bool = True):
        self._optimizer.zero_grad(set_to_none=set_to_none)
    
    def get_lr(self) -> float:
        return self._optimizer.param_groups[0]["lr"]
    
    def set_lr(self, lr: float):
        for group in self._optimizer.param_groups:
            group["lr"] = lr
    
    def get_lr_scheduler(self):
        return None
    
    def state_dict(self) -> Dict[str, Any]:
        return self._optimizer.state_dict()
    
    def load_state_dict(self, state_dict: Dict[str, Any]):
        self._optimizer.load_state_dict(state_dict)
    
    def add_param_group(self, param_group: Dict[str, Any]):
        self._optimizer.add_param_group(param_group)
    
    @property
    def param_groups(self):
        return self._optimizer.param_groups
    
    def get_config(self) -> Dict[str, Any]:
        return {**self._config, "name": self.name}
    
    @classmethod
    def create(
        cls,
        model_params: Iterator[torch.nn.Parameter],
        lr: float = 1e-3,
        weight_decay: float = 1e-5,
        **kwargs
    ) -> "LegacyAdamW":
        return cls(
            model_params=model_params,
            lr=lr,
            weight_decay=weight_decay,
            betas=kwargs.get("betas", (0.9, 0.999)),
            eps=kwargs.get("eps", 1e-8),
        )


@register_optimizer("legacy_adam")
class LegacyAdam(LegacyAdamW):
    """原始 Adam 优化器适配器"""
    
    name = "legacy_adam"
    
    def __init__(
        self,
        model_params: Iterator[torch.nn.Parameter],
        lr: float = 1e-3,
        weight_decay: float = 1e-5,
        betas: Tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
    ):
        self._optimizer = optim.Adam(
            model_params,
            lr=lr,
            weight_decay=weight_decay,
            betas=betas,
            eps=eps,
        )
        self._config = {
            "lr": lr,
            "weight_decay": weight_decay,
            "betas": betas,
            "eps": eps,
        }
    
    @classmethod
    def create(
        cls,
        model_params: Iterator[torch.nn.Parameter],
        lr: float = 1e-3,
        weight_decay: float = 1e-5,
        **kwargs
    ) -> "LegacyAdam":
        return cls(
            model_params=model_params,
            lr=lr,
            weight_decay=weight_decay,
            betas=kwargs.get("betas", (0.9, 0.999)),
            eps=kwargs.get("eps", 1e-8),
        )