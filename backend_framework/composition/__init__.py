"""backend_framework.composition - 管线组装与实验运行

提供从 YAML 配置构建完整 Pipeline、运行单实验、A/B 测试的功能。
"""
from .pipeline_builder import PipelineBuilder, build_pipeline_from_config
from .experiment_runner import ExperimentRunner, run_single_experiment, run_ab_test

__all__ = [
    "PipelineBuilder",
    "build_pipeline_from_config",
    "ExperimentRunner",
    "run_single_experiment",
    "run_ab_test",
]