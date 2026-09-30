"""backend_framework.registry - 插件注册表核心

提供 register/get/list_all 机制，支持装饰器自动注册。
所有后端组件通过导入即自动注册。
"""
from typing import Type, TypeVar, Dict, Any, Callable, Optional
from backend_framework.protocols import (
    DataLoaderProtocol, ModelProtocol, LossProtocol,
    OptimizerProtocol, TrainerProtocol, EvaluatorProtocol
)

T = TypeVar('T')

# 组件类型 -> Protocol 映射（用于运行时校验）
PROTOCOL_MAP: Dict[str, type] = {
    "data_loader": DataLoaderProtocol,
    "model": ModelProtocol,
    "loss": LossProtocol,
    "optimizer": OptimizerProtocol,
    "trainer": TrainerProtocol,
    "evaluator": EvaluatorProtocol,
}

# 组件类型 -> 注册表映射
_REGISTRIES: Dict[str, Dict[str, Type]] = {
    "data_loader": {},
    "model": {},
    "loss": {},
    "optimizer": {},
    "trainer": {},
    "evaluator": {},
}

# 组件类型 -> 实例缓存（单例模式可选）
_INSTANCES: Dict[str, Dict[str, Any]] = {
    "data_loader": {},
    "model": {},
    "loss": {},
    "optimizer": {},
    "trainer": {},
    "evaluator": {},
}


def register(component_type: str, name: str) -> Callable[[Type[T]], Type[T]]:
    """注册装饰器
    
    用法：
        @register("model", "custom_v1")
        class CustomModel:
            ...
    
    Args:
        component_type: 组件类型，必须是 PROTOCOL_MAP 的键之一
        name: 组件名称，唯一标识符
        
    Returns:
        装饰器函数
    """
    if component_type not in _REGISTRIES:
        raise ValueError(
            f"未知组件类型: {component_type}. "
            f"支持的类型: {list(_REGISTRIES.keys())}"
        )
    
    def decorator(cls: Type[T]) -> Type[T]:
        # 可选：运行时校验是否实现了对应 Protocol
        protocol = PROTOCOL_MAP.get(component_type)
        if protocol is not None:
            # 结构化子类型检查（Python 3.8+）
            # 这里只做简单检查，避免导入时过度校验
            pass
        
        if name in _REGISTRIES[component_type]:
            existing = _REGISTRIES[component_type][name]
            raise ValueError(
                f"组件已注册: {component_type}.{name} -> {existing.__module__}.{existing.__name__}. "
                f"新注册: {cls.__module__}.{cls.__name__}"
            )
        
        _REGISTRIES[component_type][name] = cls
        return cls
    
    return decorator


def get(component_type: str, name: str) -> Type:
    """获取注册的组件类
    
    Args:
        component_type: 组件类型
        name: 组件名称
        
    Returns:
        组件类
        
    Raises:
        KeyError: 组件未注册
    """
    if component_type not in _REGISTRIES:
        raise KeyError(f"未知组件类型: {component_type}")
    
    if name not in _REGISTRIES[component_type]:
        available = list(_REGISTRIES[component_type].keys())
        raise KeyError(
            f"组件未注册: {component_type}.{name}. "
            f"可用组件: {available}"
        )
    
    return _REGISTRIES[component_type][name]


def get_instance(
    component_type: str,
    name: str,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """获取或创建组件实例（单例缓存）
    
    Args:
        component_type: 组件类型
        name: 组件名称
        config: 组件配置字典
        **kwargs: 传递给构造函数的额外参数
        
    Returns:
        组件实例
    """
    cache_key = name
    if config:
        # 简单的配置哈希作为缓存键
        import hashlib
        config_str = str(sorted(config.items()))
        cache_key = f"{name}@{hashlib.md5(config_str.encode()).hexdigest()[:8]}"
    
    if cache_key not in _INSTANCES[component_type]:
        cls = get(component_type, name)
        _INSTANCES[component_type][cache_key] = cls(**(config or {}), **kwargs)
    
    return _INSTANCES[component_type][cache_key]


def clear_instance_cache(component_type: Optional[str] = None):
    """清理实例缓存"""
    if component_type:
        _INSTANCES[component_type].clear()
    else:
        for cache in _INSTANCES.values():
            cache.clear()


def list_all(component_type: str) -> Dict[str, Type]:
    """列出某类型所有已注册组件
    
    Args:
        component_type: 组件类型
        
    Returns:
        {name: class} 字典副本
    """
    if component_type not in _REGISTRIES:
        raise KeyError(f"未知组件类型: {component_type}")
    return _REGISTRIES[component_type].copy()


def list_all_names(component_type: str) -> list:
    """列出某类型所有已注册组件名称"""
    return list(_REGISTRIES.get(component_type, {}).keys())


def is_registered(component_type: str, name: str) -> bool:
    """检查组件是否已注册"""
    return component_type in _REGISTRIES and name in _REGISTRIES[component_type]


def get_protocol(component_type: str) -> Optional[type]:
    """获取组件类型对应的 Protocol"""
    return PROTOCOL_MAP.get(component_type)


def register_all():
    """显式触发所有后端注册
    
    在应用启动时调用，确保所有 @register 装饰器已执行。
    通常在各 backends/*/__init__.py 中定义 register_all() 并在此汇总调用。
    """
    # 导入各后端的 register_all 触发注册
    # 实际注册由各 backend 的 __init__.py 中的 @register 装饰器完成
    pass


# 便捷导出
__all__ = [
    "register",
    "get",
    "get_instance",
    "clear_instance_cache",
    "list_all",
    "list_all_names",
    "is_registered",
    "get_protocol",
    "register_all",
    "PROTOCOL_MAP",
    "_REGISTRIES",
]