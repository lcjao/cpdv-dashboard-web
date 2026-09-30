# 显式 import 子模块，确保 `from services import record_service` 可用。
from . import (
    cpdv_service,
    compare_service,
    evaluate_service,
    multi_crack_service,
    predict_service,
    random_service,
    record_service,
    train_service,
)

__all__ = [
    "cpdv_service", "compare_service", "evaluate_service",
    "multi_crack_service", "predict_service", "random_service", "record_service", "train_service",
]
