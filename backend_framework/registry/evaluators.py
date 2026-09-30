"""Evaluator 注册表

预导出常用评估器，供快速访问。
"""
from backend_framework.registry import register, get, list_all_names

COMPONENT_TYPE = "evaluator"

__all__ = [
    "register_evaluator",
    "get_evaluator",
    "list_evaluators",
    "COMPONENT_TYPE",
]

def register_evaluator(name: str):
    return register(COMPONENT_TYPE, name)

def get_evaluator(name: str):
    return get(COMPONENT_TYPE, name)

def list_evaluators() -> list:
    return list_all_names(COMPONENT_TYPE)