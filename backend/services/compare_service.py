from executor import run


def compare_bridges(bridge_a: str, bridge_b: str):
    """双桥数据按 x/L 归一化 → 幅值/扰动位置对比。"""
    # 对比逻辑依赖读取两桥 JSON；此处为接线骨架，实际按数据源补全
    return {"bridge_a": bridge_a, "bridge_b": bridge_b, "note": "对比逻辑待接入"}
