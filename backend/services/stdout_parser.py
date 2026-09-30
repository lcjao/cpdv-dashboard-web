"""G11: 通用 stdout 结构化提取工具。

支持匹配（按优先级）：
  1. xxx = 数字  /  xxx: 数字  /  xxx：数字
  2. 数字+可选单位（mm/m/Hz/s/%）兜底
  3. 输出路径（"图表已保存至: ..."  / "Output: ..."）

返回 dict；找不到的字段不返回（不强行 None）。
"""
import re

# 关键 key=value 提取
_RE_KV = re.compile(
    r"(?:^|\s)([A-Za-z\u4e00-\u9fa5_][A-Za-z0-9\u4e00-\u9fa5_]*)\s*[:=]\s*"
    r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
)

# 关键路径提取
_RE_OUTPUT = re.compile(
    r"(?:图表已保存至|Output|输出)\s*[:：]\s*(.+)"
)


def parse(stdout: str) -> dict:
    """从任意 pipeline stdout 提取关键字段。"""
    metrics = {}
    for m in _RE_KV.finditer(stdout):
        key = m.group(1).strip().lower()
        try:
            val = float(m.group(2))
            # 同 key 多次出现：后写覆盖
            metrics[key] = val
        except ValueError:
            pass
    out_m = _RE_OUTPUT.search(stdout)
    return {
        "metrics": metrics,
        "output_path": out_m.group(1).strip() if out_m else None,
    }