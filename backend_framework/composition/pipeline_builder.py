"""PipelineBuilder - 从配置构建完整训练管线

支持 YAML 配置驱动组件组装、变量插值、实例化。
"""
from typing import Dict, Any, Optional, Tuple
import yaml
import re
from pathlib import Path
from datetime import datetime

from backend_framework.protocols import (
    DataLoaderProtocol, ModelProtocol, LossProtocol,
    OptimizerProtocol, TrainerProtocol, EvaluatorProtocol,
    TrainResult, EvaluationResult
)
from backend_framework.registry import (
    get, get_instance, list_all_names,
    PROTOCOL_MAP
)


class PipelineBuilder:
    """管线构建器
    
    从配置字典构建完整的训练/评估管线：
    - 解析组件类型和参数
    - 实例化各组件
    - 处理依赖关系（模型需要 input_dim/max_cracks 来自数据加载器）
    - 支持配置变量插值
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 完整实验配置，包含 experiment, components, output 等节
        """
        self.config = config
        self.experiment_config = config.get("experiment", {})
        self.components_config = config.get("components", {})
        self.output_config = config.get("output", {})
        
        # 运行时上下文
        self._context: Dict[str, Any] = {}
        self._built_components: Dict[str, Any] = {}
    
    def build(self) -> Tuple[
        DataLoaderProtocol, ModelProtocol, LossProtocol,
        OptimizerProtocol, TrainerProtocol, EvaluatorProtocol
    ]:
        """构建完整管线，返回六元组
        
        Returns:
            (data_loader, model, loss_fn, optimizer, trainer, evaluator)
        """
        # 1. 准备上下文变量
        self._prepare_context()
        
        # 2. 构建数据加载器（最先，因为模型需要 input_dim/max_cracks）
        data_loader = self._build_data_loader()
        self._built_components["data_loader"] = data_loader
        
        # 3. 构建模型（需要数据加载器的维度信息）
        model = self._build_model(data_loader)
        self._built_components["model"] = model
        
        # 4. 构建损失函数
        loss_fn = self._build_loss()
        self._built_components["loss_fn"] = loss_fn
        
        # 5. 构建优化器（需要模型参数）
        optimizer = self._build_optimizer(model)
        self._built_components["optimizer"] = optimizer
        
        # 6. 构建训练器
        trainer = self._build_trainer()
        self._built_components["trainer"] = trainer
        
        # 7. 构建评估器
        evaluator = self._build_evaluator()
        self._built_components["evaluator"] = evaluator
        
        return data_loader, model, loss_fn, optimizer, trainer, evaluator
    
    def _prepare_context(self):
        """准备模板变量上下文"""
        exp = self.experiment_config
        self._context = {
            "experiment": exp,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "date": datetime.now().strftime("%Y%m%d"),
            "time": datetime.now().strftime("%H%M%S"),
        }
        # 合并实验配置到上下文
        for k, v in exp.items():
            self._context[k] = v
    
    def _interpolate(self, value: Any) -> Any:
        """递归插值字符串中的 ${var} 变量"""
        if isinstance(value, str):
            def repl(match):
                var_name = match.group(1)
                return str(self._context.get(var_name, match.group(0)))
            return re.sub(r"\$\{(\w+)\}", repl, value)
        elif isinstance(value, dict):
            return {k: self._interpolate(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._interpolate(v) for v in value]
        return value
    
    def _get_component_config(self, component_type: str) -> Dict[str, Any]:
        """获取组件配置并插值"""
        comp_config = self.components_config.get(component_type, {})
        return self._interpolate(comp_config)
    
    def _build_data_loader(self) -> DataLoaderProtocol:
        """构建数据加载器"""
        comp_config = self._get_component_config("data_loader")
        comp_type = comp_config.get("type", "legacy")
        params = comp_config.get("params", {})
        
        # 获取类并实例化
        cls = get("data_loader", comp_type)
        return cls(**params)
    
    def _build_model(self, data_loader: DataLoaderProtocol) -> ModelProtocol:
        """构建模型（注入数据维度）"""
        comp_config = self._get_component_config("model")
        comp_type = comp_config.get("type", "legacy_dual_head")
        params = comp_config.get("params", {})
        
        # 自动注入数据维度（如果配置中未显式指定）
        if "input_dim" not in params:
            params["input_dim"] = data_loader.get_input_dim()
        if "max_cracks" not in params:
            params["max_cracks"] = data_loader.get_max_cracks()
        
        cls = get("model", comp_type)
        return cls(**params)
    
    def _build_loss(self) -> LossProtocol:
        """构建损失函数"""
        comp_config = self._get_component_config("loss")
        comp_type = comp_config.get("type", "legacy_dual_head")
        params = comp_config.get("params", {})
        
        cls = get("loss", comp_type)
        return cls(**params)
    
    def _build_optimizer(self, model: ModelProtocol) -> OptimizerProtocol:
        """构建优化器"""
        comp_config = self._get_component_config("optimizer")
        comp_type = comp_config.get("type", "legacy_adamw")
        params = comp_config.get("params", {})
        
        cls = get("optimizer", comp_type)
        return cls.create(model.parameters(), **params)
    
    def _build_trainer(self) -> TrainerProtocol:
        """构建训练器"""
        comp_config = self._get_component_config("trainer")
        comp_type = comp_config.get("type", "legacy_three_phase")
        params = comp_config.get("params", {})
        
        cls = get("trainer", comp_type)
        return cls(**params)
    
    def _build_evaluator(self) -> EvaluatorProtocol:
        """构建评估器"""
        comp_config = self._get_component_config("evaluator")
        comp_type = comp_config.get("type", "legacy_hungarian")
        params = comp_config.get("params", {})
        
        cls = get("evaluator", comp_type)
        return cls(**params)
    
    def get_output_dir(self) -> Path:
        """获取输出目录（已插值）"""
        save_dir = self.output_config.get("save_dir", "experiments/results/${experiment.name}_${timestamp}")
        save_dir = self._interpolate(save_dir)
        path = Path(save_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def save_config(self, output_dir: Optional[Path] = None):
        """保存完整配置到输出目录"""
        if output_dir is None:
            output_dir = self.get_output_dir()
        config_path = output_dir / "config_used.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, allow_unicode=True, sort_keys=False)
        return config_path


def build_pipeline_from_config(config: Dict[str, Any]) -> Tuple[
    DataLoaderProtocol, ModelProtocol, LossProtocol,
    OptimizerProtocol, TrainerProtocol, EvaluatorProtocol
]:
    """便捷函数：从配置构建管线"""
    builder = PipelineBuilder(config)
    return builder.build()