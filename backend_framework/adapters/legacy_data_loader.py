"""LegacyDataLoader - 适配原始 Pipeline 数据加载

复用 scripts/data_loader.py 和原始 NPZ 数据格式。
"""
from typing import Dict, Any, Optional, Tuple
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
import sys
from pathlib import Path

from backend_framework.protocols import DataLoaderProtocol
from backend_framework.registry.data_loaders import register_data_loader


# 确保能导入原始 pipeline 模块
CODE_ROOT = Path(r"D:\研\土木水利\论文\代码\github")
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from scripts.data_loader import load_data as load_npz_data  # 原始加载函数


@register_data_loader("legacy")
class LegacyDataLoader:
    """原始 Pipeline 数据加载器适配器
    
    支持加载 NPZ 格式训练数据，返回标准 DataLoader 和 numpy 数组。
    """
    
    def __init__(
        self,
        data_path: str = "outputs/data/multi_condition.npz",
        code_root: Optional[str] = None,
    ):
        """
        Args:
            data_path: 相对于 code_root 的数据文件路径
            code_root: 原始代码根目录，默认使用环境变量或硬编码路径
        """
        self.data_path = data_path
        self.code_root = Path(code_root) if code_root else CODE_ROOT
        self._data: Optional[Dict[str, np.ndarray]] = None
        self._stats: Dict[str, np.ndarray] = {}
        self._input_dim: Optional[int] = None
        self._max_cracks: Optional[int] = None
    
    def _ensure_loaded(self):
        """懒加载数据"""
        if self._data is not None:
            return
        
        full_path = self.code_root / self.data_path
        if not full_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {full_path}")
        
        self._data = load_npz_data(str(full_path))
        
        # 提取统计量
        for key in ("X_mean", "X_std", "y_mean", "y_std"):
            if key in self._data.get("stats", {}):
                self._stats[key] = self._data["stats"][key]
        
        # 推导维度
        X_train = self._data["X_train"]
        y_train = self._data["y_train"]
        self._input_dim = X_train.shape[0]
        self._max_cracks = y_train.shape[0] // 2
    
    def get_train_loader(
        self,
        batch_size: int = 64,
        shuffle: bool = True,
        num_workers: int = 0,
        **kwargs
    ) -> DataLoader:
        self._ensure_loaded()
        X_t = torch.FloatTensor(self._data["X_train"].T)
        y_t = torch.FloatTensor(self._data["y_train"].T)
        dataset = TensorDataset(X_t, y_t)
        return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers)
    
    def get_val_loader(
        self,
        batch_size: int = 64,
        shuffle: bool = False,
        num_workers: int = 0,
        **kwargs
    ) -> DataLoader:
        self._ensure_loaded()
        X_t = torch.FloatTensor(self._data["X_val"].T)
        y_t = torch.FloatTensor(self._data["y_val"].T)
        dataset = TensorDataset(X_t, y_t)
        return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers)
    
    def get_test_loader(
        self,
        batch_size: int = 64,
        shuffle: bool = False,
        num_workers: int = 0,
        **kwargs
    ) -> DataLoader:
        self._ensure_loaded()
        X_t = torch.FloatTensor(self._data["X_test"].T)
        y_t = torch.FloatTensor(self._data["y_test"].T)
        dataset = TensorDataset(X_t, y_t)
        return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers)
    
    def get_data_arrays(self) -> Dict[str, np.ndarray]:
        self._ensure_loaded()
        return {
            "X_train": self._data["X_train"],
            "y_train": self._data["y_train"],
            "X_val": self._data["X_val"],
            "y_val": self._data["y_val"],
            "X_test": self._data["X_test"],
            "y_test": self._data["y_test"],
            "stats": self._data.get("stats", {}),
        }
    
    def get_input_dim(self) -> int:
        self._ensure_loaded()
        return self._input_dim
    
    def get_max_cracks(self) -> int:
        self._ensure_loaded()
        return self._max_cracks
    
    def get_stats(self) -> Dict[str, np.ndarray]:
        self._ensure_loaded()
        return self._stats.copy()