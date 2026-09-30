"""OptimizerProtocol - 优化器契约

统一优化器接口：步进、梯度清零、学习率获取/设置、状态字典。
"""
from typing import Protocol, Dict, Any, Iterator, Optional
import torch
import torch.optim as optim


class OptimizerProtocol(Protocol):
    """优化器协议
    
    所有后端优化器必须实现此接口。
    封装 PyTorch Optimizer，提供统一接口。
    """
    
    # ===== 必需属性 =====
    name: str  # 优化器名称，如 "adam", "adamw", "sgd"
    
    # ===== 核心操作 =====
    def step(self):
        """执行一步参数更新"""
        ...
    
    def zero_grad(self, set_to_none: bool = True):
        """清零梯度
        
        Args:
            set_to_none: True 时将梯度设为 None（节省内存），False 时设为 0
        """
        ...
    
    # ===== 学习率管理 =====
    def get_lr(self) -> float:
        """获取当前学习率（主参数组）"""
        ...
    
    def set_lr(self, lr: float):
        """设置学习率（所有参数组）"""
        ...
    
    def get_lr_scheduler(self) -> Optional[Any]:
        """获取关联的学习率调度器（可选）"""
        ...
    
    # ===== 状态字典 =====
    def state_dict(self) -> Dict[str, Any]:
        """获取优化器状态字典（用于 checkpoint）"""
        ...
    
    def load_state_dict(self, state_dict: Dict[str, Any]):
        """加载优化器状态字典"""
        ...
    
    # ===== 参数组 =====
    def add_param_group(self, param_group: Dict[str, Any]):
        """添加参数组"""
        ...
    
    @property
    def param_groups(self) -> list:
        """参数组列表"""
        ...
    
    # ===== 配置 =====
    def get_config(self) -> Dict[str, Any]:
        """获取优化器配置（用于记录、复现）"""
        ...
    
    @classmethod
    def create(
        cls,
        model_params: Iterator[torch.nn.Parameter],
        lr: float = 1e-3,
        weight_decay: float = 1e-5,
        **kwargs
    ) -> "OptimizerProtocol":
        """工厂方法：创建优化器实例
        
        Args:
            model_params: model.parameters()
            lr: 学习率
            weight_decay: 权重衰减
            **kwargs: 优化器特定参数（如 betas, eps, momentum 等）
            
        Returns:
            OptimizerProtocol 实例
        """
        ...