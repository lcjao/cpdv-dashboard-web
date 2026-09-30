"""backend.routes - 路由模块统一导出"""
from . import dashboard, analysis, bridges, llm, command, external_code, algorithm

__all__ = [
    "dashboard",
    "analysis",
    "bridges",
    "llm",
    "command",
    "external_code",
    "algorithm",
]