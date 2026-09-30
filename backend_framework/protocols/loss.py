"""LossProtocol - 损失函数契约

统一损失函数接口：前向计算、损失分量拆解、名称标识。
"""
from typing import Protocol, Dict, Any, Tuple, Union
import torch
import torch.nn as nn


class LossProtocol(Protocol):
    """损失函数协议
    
    所有后端损失函数必须实现此接口。
    支持单一损失值返回，或 (total_loss, loss_dict) 多组件返回。
    """
    
    # ===== 必需属性 =====
    name: str  # 损失函数名称，用于日志和配置标识
    
    # ===== 前向计算 =====
    def forward(
        self,
        pred: Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]],
        target: torch.Tensor,
        **kwargs
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, Dict[str, torch.Tensor]]]:
        """计算损失
        
        Args:
            pred: 模型输出
                单头: (batch_size, max_cracks * 2)
                双头: (cls_pred, reg_pred) 其中 cls_pred: (batch_size, max_cracks), reg_pred: (batch_size, max_cracks * 2)
            target: (batch_size, max_cracks * 2) 真实标签，填充位为 -1
            **kwargs: 损失特定参数（如 miss_weight, reg_weight, cls_threshold 等）
            
        Returns:
            单一张量: total_loss
            或元组: (total_loss, loss_dict) 其中 loss_dict 包含各分量如 {"cls_loss": ..., "reg_loss": ...}
        """
        ...
    
    def __call__(
        self,
        pred: Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]],
        target: torch.Tensor,
        **kwargs
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, Dict[str, torch.Tensor]]]:
        """别名：forward"""
        ...
    
    # ===== 配置 =====
    def get_config(self) -> Dict[str, Any]:
        """获取损失函数配置（用于记录、复现）
        
        Returns:
            dict: 所有超参数
        """
        ...
    
    def set_config(self, **kwargs):
        """动态更新配置"""
        ...