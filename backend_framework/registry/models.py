"""Model 注册表

预导出常用模型，供快速访问。
"""
from backend_framework.registry import register, get, list_all_names

COMPONENT_TYPE = "model"

__all__ = [
    "register_model",
    "get_model",
    "list_models",
    "COMPONENT_TYPE",
]

def register_model(name: str):
    return register(COMPONENT_TYPE, name)

def get_model(name: str):
    return get(COMPONENT_TYPE, name)

def list_models() -> list:
    return list_all_names(COMPONENT_TYPE)