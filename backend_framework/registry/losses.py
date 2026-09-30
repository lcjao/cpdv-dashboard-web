"""Loss 注册表

预导出常用损失函数，供快速访问。
"""
from backend_framework.registry import register, get, list_all_names

COMPONENT_TYPE = "loss"

__all__ = [
    "register_loss",
    "get_loss",
    "list_losses",
    "COMPONENT_TYPE",
]

def register_loss(name: str):
    return register(COMPONENT_TYPE, name)

def get_loss(name: str):
    return get(COMPONENT_TYPE, name)

def list_losses() -> list:
    return list_all_names(COMPONENT_TYPE)