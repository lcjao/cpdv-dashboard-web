from executor import run
from services.stdout_parser import parse as _parse


def random_condition(mode: str, n_samples: int, positions: list):
    """流程 C4：随机多工况分析。mode=single|multi_pos。"""
    argv = [
        "scripts/05_random_condition_cpdv.py",
        "--mode", mode,
        "--n_samples", str(n_samples),
        "--seed", "42",
    ]
    if mode == "multi_pos" and positions:
        argv += ["--positions", *map(str, positions)]
    out = run(argv, cmd="random")
    return {
        "stdout": out,
        "mode": mode,
        "n_samples": n_samples,
        "positions": positions,
        "parsed": _parse(out),  # G11
    }
