"""Trainer 注册表

预导出常用训练器，供快速访问。
"""
from backend_framework.registry import register, get, list_all_names

COMPONENT_TYPE = "trainer"

__all__ = [
    "register_trainer",
    "get_trainer",
    "list_trainers",
    "COMPONENT_TYPE",
]

def register_trainer(name: str):
    return register(COMPONENT_TYPE, name)

def get_trainer(name: str):
    return get(COMPONENT_TYPE, name)

def list_trainers() -> list:
    return list_all_names(COMPONENT_TYPE)