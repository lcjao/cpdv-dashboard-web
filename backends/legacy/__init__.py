"""backends.legacy - 原始 Pipeline 适配版 (baseline)

导入即自动注册所有 legacy 组件到注册表。
"""
from backend_framework.adapters import (
    LegacyDataLoader,
    LegacyModel,
    LegacyDualHeadModel,
    LegacyWeightedLoss,
    LegacyDualHeadLoss,
    LegacyAdamW,
    LegacyAdam,
    LegacyThreePhaseTrainer,
    LegacyHungarianEvaluator,
)


def register_all():
    """显式触发注册（导入时已自动通过 @register 装饰器注册）"""
    # 验证注册是否成功
    from backend_framework.registry import list_all_names
    
    print("=== Legacy Backend 已注册组件 ===")
    for comp_type in ["data_loader", "model", "loss", "optimizer", "trainer", "evaluator"]:
        names = list_all_names(comp_type)
        print(f"  {comp_type}: {names}")


# 导入时自动执行注册
if __name__ != "__main__":
    register_all()