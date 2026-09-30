"""ModelProtocol - 模型契约

统一模型接口：前向传播、参数访问、状态保存/加载、输出解码。
支持基础模型和双头模型两种架构。
"""
from typing import Protocol, Dict, Any, List, Optional, Tuple, Union
import torch
import torch.nn as nn


class ModelProtocol(Protocol):
    """模型协议
    
    所有后端模型必须实现此接口。
    支持单头（基础）和双头（分类+回归）两种架构。
    """
    
    # ===== 必需属性 =====
    max_cracks: int
    output_dim: int
    dual_head: bool
    
    # ===== 前向传播 =====
    def forward(self, x: torch.Tensor) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """前向传播
        
        Args:
            x: (batch_size, input_dim) 输入张量
            
        Returns:
            单头: (batch_size, max_cracks * 2) 回归输出
            双头: (cls_out, reg_out) 其中
                cls_out: (batch_size, max_cracks) 分类 logits
                reg_out: (batch_size, max_cracks * 2) 回归输出
        """
        ...
    
    def __call__(self, x: torch.Tensor) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """别名：forward"""
        ...
    
    # ===== 参数访问 =====
    def parameters(self):
        """返回模型参数迭代器（用于优化器）"""
        ...
    
    def named_parameters(self):
        """返回命名参数迭代器"""
        ...
    
    def get_parameters(self) -> Dict[str, torch.Tensor]:
        """获取所有参数的 state_dict 格式字典"""
        ...
    
    # ===== 状态保存/加载 =====
    def state_dict(self) -> Dict[str, torch.Tensor]:
        """获取模型状态字典（含参数、缓冲区）"""
        ...
    
    def load_state_dict(self, state_dict: Dict[str, torch.Tensor], strict: bool = True):
        """加载模型状态字典"""
        ...
    
    def save(self, path: str, **metadata):
        """保存模型到文件
        
        Args:
            path: 保存路径
            **metadata: 额外元数据（input_dim, hidden_dim, num_layers, max_cracks, dual_head, metrics 等）
        """
        ...
    
    @classmethod
    def load(cls, path: str, device: torch.device = None) -> "ModelProtocol":
        """从文件加载模型（类方法）
        
        Args:
            path: 模型文件路径
            device: 目标设备
            
        Returns:
            实例化的模型
        """
        ...
    
    # ===== 输出解码 =====
    def decode_output(
        self,
        *outputs,
        threshold: float = 0.0,
        cls_threshold: float = 0.3
    ) -> List[List[Dict]]:
        """将网络输出解码为裂缝列表
        
        单头模型: decode_output(pred, threshold=0.0)
        双头模型: decode_output(cls_pred, reg_pred, cls_threshold=0.3)
        
        Returns:
            List[List[Dict]]: batch_size 个样本，每个样本为裂缝列表
            每个裂缝 Dict: {"position": float, "depth": float}
        """
        ...
    
    # ===== 模型信息 =====
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型元信息（用于日志、记录）
        
        Returns:
            dict: input_dim, hidden_dim, num_layers, max_cracks, dual_head, param_count 等
        """
        ...
    
    def num_parameters(self) -> int:
        """获取总参数量"""
        ...
    
    def train(self, mode: bool = True):
        """设置训练/评估模式"""
        ...
    
    def eval(self):
        """设置评估模式"""
        ...
    
    def to(self, device: torch.device) -> "ModelProtocol":
        """移动到设备"""
        ...