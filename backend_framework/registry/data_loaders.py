"""Data Loader 注册表

预导出常用数据加载器，供快速访问。
"""
from backend_framework.registry import register, get, list_all_names

# 组件类型常量
COMPONENT_TYPE = "data_loader"

# 导出核心函数
__all__ = [
    "register_data_loader",
    "get_data_loader",
    "list_data_loaders",
    "COMPONENT_TYPE",
]

# 便捷别名
def register_data_loader(name: str):
    """注册数据加载器的装饰器"""
    return register(COMPONENT_TYPE, name)

def get_data_loader(name: str):
    """获取数据加载器类"""
    return get(COMPONENT_TYPE, name)

def list_data_loaders() -> list:
    """列出所有已注册的数据加载器名称"""
    return list_all_names(COMPONENT_TYPE)