from executor import run


def predict_multi_crack(model: str, input_data: str):
    """流程 C3：多裂缝推理。默认 multi_crack_dual_retrained.pth。"""
    argv = [
        "scripts/05_infer_multi_crack.py",
        "--model", model,
        "--input", input_data,
    ]
    return {"stdout": run(argv)}
