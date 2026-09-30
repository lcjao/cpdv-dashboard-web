from executor import run
from services.stdout_parser import parse as _parse


def predict_single(model: str, input_data: str):
    """流程 C2：单裂缝推理（BP 默认 cracknet.json）。"""
    argv = [
        "scripts/03_run_inference.py",
        "--model", model,
        "--input", input_data,
    ]
    out = run(argv, cmd="predict")
    return {
        "stdout": out,
        "model": model,
        "input_data": input_data,
        "parsed": _parse(out),  # G11
    }
