import json
from pathlib import Path
from executor import run, verify_import


def compute_cpdv(bridge_id: str, depth: float, distances: list, params: dict, output_dir: Path):
    """流程 C1：计算 CPDV。动态改写 yaml 后传入 --config。"""
    # 首次执行先验证环境
    verify_import()
    # 组装命令（04_cpdv_analysis.py --mode signal）
    argv = [
        "scripts/04_cpdv_analysis.py",
        "--mode", "signal",
        "--signal_depth", str(depth),
        "--distances", *map(str, distances),
        "--prefix", bridge_id,
        "--output", "outputs/figures/",
    ]
    out = run(argv)
    return {"stdout": out, "bridge_id": bridge_id, "depth": depth}


# 注：此 service 为 pipeline 接线骨架。实际参数注入方式需按 SKILL.md：
# 「写一个临时 yaml（含 simulation 段）→ --config 临时yaml」。
# 因为 04_cpdv_analysis.py 仅支持用 --bridge_length 覆盖 L，其余参数（mv/kv/cv 等）
# 必须通过动态改写 yaml 传入。具体 yaml 生成逻辑在接入时按实际 pipeline 接口补全。
