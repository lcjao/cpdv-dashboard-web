from executor import run


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
    return {"stdout": run(argv)}
