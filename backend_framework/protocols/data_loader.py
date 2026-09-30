"""DataLoaderProtocol - 数据加载器契约

标准化数据加载接口，支持训练/验证/测试三种模式。
返回格式统一为 dict，包含 Tensor 或 numpy 数组。
"""
from typing import Protocol, Dict, Any, Optional, Tuple
import numpy as np
import torch


class DataLoaderProtocol(Protocol):
    """数据加载器协议
    
    所有后端数据加载器必须实现此接口。
    返回格式统一，便于 TrainerProtocol 直接使用。
    """
    
    def get_train_loader(
        self,
        batch_size: int = 64,
        shuffle: bool = True,
        num_workers: int = 0,
        **kwargs
    ) -> torch.utils.data.DataLoader:
        """获取训练数据 DataLoader
        
        Args:
            batch_size: 批大小
            shuffle: 是否打乱
            num_workers: 数据加载进程数
            **kwargs: 后端特定参数
            
        Returns:
            PyTorch DataLoader，yield (batch_x, batch_y)
        """
        ...
    
    def get_val_loader(
        self,
        batch_size: int = 64,
        shuffle: bool = False,
        num_workers: int = 0,
        **kwargs
    ) -> torch.utils.data.DataLoader:
        """获取验证数据 DataLoader"""
        ...
    
    def get_test_loader(
        self,
        batch_size: int = 64,
        shuffle: bool = False,
        num_workers: int = 0,
        **kwargs
    ) -> torch.utils.data.DataLoader:
        """获取测试数据 DataLoader"""
        ...
    
    def get_data_arrays(
        self
    ) -> Dict[str, np.ndarray]:
        """获取原始 numpy 数组（用于评估、导出等）
        
        Returns:
            dict with keys: X_train, y_train, X_val, y_val, X_test, y_test, stats
            stats 可选，包含 X_mean, X_std, y_mean, y_std 等归一化参数
        """
        ...
    
    def get_input_dim(self) -> int:
        """获取输入特征维度"""
        ...
    
    def get_max_cracks(self) -> int:
        """获取最大裂缝数（由标签维度推导：y.shape[0] // 2）"""
        ...
    
    def get_stats(self) -> Dict[str, np.ndarray]:
        """获取归一化统计量（可选）
        
        Returns:
            dict with optional keys: X_mean, X_std, y_mean, y_std
        """
        ...