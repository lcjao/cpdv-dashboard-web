"""backend_framework.adapters - 原始 Pipeline 组件适配器

将原始 Pipeline (D:\\研\\土木水利\\论文\\代码\\github) 的组件适配为标准 Protocol。
"""
from .legacy_data_loader import LegacyDataLoader
from .legacy_model import LegacyModel, LegacyDualHeadModel
from .legacy_loss import LegacyWeightedLoss, LegacyDualHeadLoss
from .legacy_optimizer import LegacyAdamW, LegacyAdam
from .legacy_trainer import LegacyThreePhaseTrainer
from .legacy_evaluator import LegacyHungarianEvaluator

__all__ = [
    "LegacyDataLoader",
    "LegacyModel",
    "LegacyDualHeadModel",
    "LegacyWeightedLoss",
    "LegacyDualHeadLoss",
    "LegacyAdamW",
    "LegacyAdam",
    "LegacyThreePhaseTrainer",
    "LegacyHungarianEvaluator",
]