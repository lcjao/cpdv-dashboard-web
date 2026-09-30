"""EvaluatorProtocol - 评估器契约

统一评估接口：离线评估、指标计算、结果导出。
独立于训练器，可用于已训练模型的复现评估、A/B 测试指标收集。
"""
from typing import Protocol, Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import torch
import numpy as np
from .model import ModelProtocol
from .data_loader import DataLoaderProtocol
from .loss import LossProtocol


@dataclass
class EvaluationResult:
    """评估结果标准数据类"""
    # 核心指标
    metrics: Dict[str, float]  # {pos_mae, depth_mae, recall, precision, f1, n_matched, n_gt, n_pred}
    
    # 逐样本详细结果（可选，用于深度分析）
    per_sample: List[Dict[str, Any]] = field(default_factory=list)
    
    # 匹配详情
    matches: List[Dict[str, Any]] = field(default_factory=list)
    
    # 混淆矩阵相关
    confusion: Dict[str, int] = field(default_factory=dict)  # tp, fp, fn, tn (若适用)
    
    # 元信息
    model_path: str = ""
    data_path: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0


from dataclasses import dataclass, field


class EvaluatorProtocol(Protocol):
    """评估器协议
    
    所有后端评估器必须实现此接口。
    支持完整评估流程：加载模型、推理、匈牙利匹配、指标计算、结果导出。
    """
    
    # ===== 必需属性 =====
    name: str  # 评估器名称，如 "hungarian", "legacy", "custom_v1"
    
    # ===== 核心评估 =====
    def evaluate(
        self,
        model: ModelProtocol,
        test_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        config: Dict[str, Any],
    ) -> EvaluationResult:
        """执行完整评估流程
        
        Args:
            model: 已训练模型（已 load_state_dict）
            test_loader: 测试数据加载器
            loss_fn: 损失函数（可选，用于计算 test loss）
            config: 评估配置，包含：
                - cls_threshold: float = 0.3 (双头模型分类阈值)
                - pos_threshold: float = 0.0 (基础模型位置阈值)
                - match_cost: float = 5.0 (匈牙利匹配最大位置代价)
                - device: str = "auto"
                - save_details: bool = False (是否保存逐样本详情)
                - output_dir: str = None (详细结果保存目录)
                
        Returns:
            EvaluationResult: 标准化评估结果
        """
        ...
    
    # ===== 批量评估（用于 A/B 测试）=====
    def evaluate_multiple(
        self,
        model_paths: List[str],
        test_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        config: Dict[str, Any],
        n_runs: int = 1,
    ) -> List[EvaluationResult]:
        """对多个模型进行评估（支持多轮重复）
        
        Args:
            model_paths: 模型文件路径列表
            test_loader: 测试数据加载器
            loss_fn: 损失函数
            config: 评估配置
            n_runs: 每个模型重复评估次数（用于统计显著性）
            
        Returns:
            EvaluationResult 列表，长度 = len(model_paths) * n_runs
        """
        ...
    
    # ===== 指标计算（底层，可被外部直接调用）=====
    def compute_metrics(
        self,
        pred_batch: np.ndarray,
        target_batch: np.ndarray,
        cls_pred_batch: Optional[np.ndarray] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """计算指标（纯 numpy，不依赖模型前向）
        
        Args:
            pred_batch: (batch_size, max_cracks * 2) 预测回归值
            target_batch: (batch_size, max_cracks * 2) 真实标签
            cls_pred_batch: (batch_size, max_cracks) 分类概率/logits（双头模型）
            config: 指标计算配置
            
        Returns:
            metrics dict
        """
        ...
    
    # ===== 配置 =====
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认评估配置"""
        ...
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """校验配置"""
        ...