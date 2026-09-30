"""TrainerProtocol - 训练器契约

统一训练接口：train() 完整训练流程、evaluate() 评估流程。
返回标准化 TrainResult，包含模型状态、指标、历史、产物路径。
"""
from typing import Protocol, Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
import torch
from .model import ModelProtocol
from .data_loader import DataLoaderProtocol
from .loss import LossProtocol
from .optimizer import OptimizerProtocol


@dataclass
class TrainResult:
    """训练结果标准数据类
    
    所有 TrainerProtocol.train() 必须返回此结构。
    """
    # 核心结果
    model_state: Dict[str, torch.Tensor]  # model.state_dict()
    metrics: Dict[str, float]             # 最终验证/测试指标 {f1, pos_mae, depth_mae, recall, precision, ...}
    
    # 训练历史
    history: Dict[str, List[float]] = field(default_factory=dict)  # {"train_loss": [...], "val_loss": [...], "phase": [...]}
    
    # 产物路径
    artifacts: Dict[str, str] = field(default_factory=dict)  # {"model_path": ..., "history_path": ..., "config_path": ...}
    
    # 元信息
    duration_s: float = 0.0
    epochs_completed: int = 0
    best_epoch: int = 0
    best_val_loss: float = float("inf")
    early_stopped: bool = False
    config: Dict[str, Any] = field(default_factory=dict)  # 完整训练配置（用于复现）
    
    def to_dict(self) -> Dict[str, Any]:
        """转为可序列化字典（用于 JSON 保存）"""
        return {
            "metrics": self.metrics,
            "history": self.history,
            "artifacts": self.artifacts,
            "duration_s": self.duration_s,
            "epochs_completed": self.epochs_completed,
            "best_epoch": self.best_epoch,
            "best_val_loss": self.best_val_loss,
            "early_stopped": self.early_stopped,
            "config": self.config,
        }


# 进度回调类型
ProgressCallback = Callable[[str, str, float, Dict[str, Any]], None]
# stage_name, message, percent, extra_data


class TrainerProtocol(Protocol):
    """训练器协议
    
    所有后端训练器必须实现此接口。
    封装完整训练流程：数据准备、模型创建、训练循环、验证、早停、保存。
    """
    
    # ===== 必需属性 =====
    name: str  # 训练器名称，如 "three_phase", "lightning", "custom_v1"
    
    # ===== 核心训练 =====
    def train(
        self,
        model: ModelProtocol,
        train_loader: DataLoaderProtocol,
        val_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        optimizer: OptimizerProtocol,
        config: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> TrainResult:
        """执行完整训练流程
        
        Args:
            model: 模型实例（已初始化，未训练）
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器
            loss_fn: 损失函数
            optimizer: 优化器
            config: 训练配置字典，包含：
                - max_epochs: int
                - phase1_epochs: int (可选)
                - phase2_epochs: int (可选)
                - phase3_epochs: int (可选)
                - early_stopping_patience: int
                - gradient_accumulation_steps: int
                - clip_grad: float
                - lr_finetune: float
                - device: str ("cuda"/"cpu")
                - save_dir: str
                - seed: int
            progress_callback: 可选进度回调 stage_name, message, percent, extra_data
            
        Returns:
            TrainResult: 标准化训练结果
        """
        ...
    
    # ===== 评估 =====
    def evaluate(
        self,
        model: ModelProtocol,
        test_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        config: Dict[str, Any],
    ) -> Dict[str, float]:
        """在测试集上评估模型
        
        Args:
            model: 已训练模型
            test_loader: 测试数据加载器
            loss_fn: 损失函数
            config: 评估配置，包含：
                - cls_threshold: float (双头模型分类阈值)
                - pos_threshold: float (基础模型位置阈值)
                - match_cost: float (匈牙利匹配最大代价)
                - device: str
                
        Returns:
            metrics dict: {pos_mae, depth_mae, recall, precision, f1, n_matched, n_gt, n_pred}
        """
        ...
    
    # ===== 配置 =====
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认训练配置"""
        ...
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """校验配置，返回错误信息列表（空表示通过）"""
        ...