from executor import run


def train_model(model_type: str, n_samples: int):
    """流程 T1：训练模型。先 report 预计耗时并确认是前端/AI 职责。"""
    # 生成数据（不一定每次需要；视 model_type）
    argv = [
        "scripts/01_generate_data.py",
        "--n_samples", str(n_samples),
        "--output", "outputs/data/training_data.npz",
    ]
    return {"stdout": run(argv)}
