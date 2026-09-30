"""backend_framework.protocols - 所有组件的 Protocol 定义

统一导出接口，供新后端实现参考、注册表校验使用。
"""
from .data_loader import DataLoaderProtocol
from .model import ModelProtocol
from .loss import LossProtocol
from .optimizer import OptimizerProtocol
from .trainer import TrainerProtocol, TrainResult
from .evaluator import EvaluatorProtocol, EvaluationResult

__all__ = [
    "DataLoaderProtocol",
    "ModelProtocol",
    "LossProtocol",
    "OptimizerProtocol",
    "TrainerProtocol",
    "TrainResult",
    "EvaluatorProtocol",
    "EvaluationResult",
]