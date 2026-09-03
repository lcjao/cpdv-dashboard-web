from executor import run


def predict_single(model: str, input_data: str):
    """流程 C2：单裂缝推理（BP 默认 cracknet.json）。"""
    argv = [
        "scripts/03_run_inference.py",
        "--model", model,
        "--input", input_data,
    ]
    return {"stdout": run(argv)}
