"""Optimizer 注册表

预导出常用优化器，供快速访问。
"""
from backend_framework.registry import register, get, list_all_names

COMPONENT_TYPE = "optimizer"

__all__ = [
    "register_optimizer",
    "get_optimizer",
    "list_optimizers",
    "COMPONENT_TYPE",
]

def register_optimizer(name: str):
    return register(COMPONENT_TYPE, name)

def get_optimizer(name: str):
    return get(COMPONENT_TYPE, name)

def list_optimizers() -> list:
    return list_all_names(COMPONENT_TYPE)