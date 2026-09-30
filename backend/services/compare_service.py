"""桥梁对比服务（评审 G4 — 简单方案 A）。

数据源：
- registry.json（每桥的 params + 最新的 meta 含 metrics/model）
- records.jsonl（每桥最近 N 条实验记录）

输出：
- bridges: {bridge_id: {params, metrics, last_record, registry_status}}
- diff: 
  - params_diff: {key: [val_a, val_b] for common keys}
  - only_in_a / only_in_b: 列表
  - equal: 布尔列表
  - numeric_diff_pct: {key: pct}（仅对数值键）
- summary: 一句话描述差异

不调 pipeline，纯 registry + records 内存对比，毫秒级返回。
"""
from typing import Optional
from data_loader import load_registry, load_records


def _normalize_bridge_id(name_or_id: str) -> Optional[str]:
    reg = load_registry()
    for b in reg.get("bridges", []):
        if b.get("id") == name_or_id or b.get("name") == name_or_id:
            return b.get("id") or name_or_id
    return None


def _bridge_snapshot(bridge_id: str) -> dict:
    """整合 registry + records 给出桥的当前快照。"""
    reg = load_registry()
    target = None
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            target = b
            break
    if not target:
        return {
            "id": bridge_id, "found": False,
            "params": {}, "metrics": {}, "status": "not_found",
        }
    last_record = load_records(bridge_id=target.get("id"), limit=1)
    last = last_record[-1] if last_record else None
    return {
        "id": target.get("id"),
        "name": target.get("name"),
        "found": True,
        "params": target.get("params") or {},
        "metrics": (target.get("meta") or {}).get("metrics", {}),
        "model_path": (target.get("meta") or {}).get("model_path"),
        "last_trained_at": (target.get("meta") or {}).get("last_trained_at"),
        "status": target.get("status"),
        "last_record": (
            {k: last[k] for k in ("timestamp", "action", "params", "note") if k in last}
            if last else None
        ),
    }


def _param_diff(a: dict, b: dict) -> dict:
    """对比两个字典的 params，给出差异。"""
    keys = set(a.keys()) | set(b.keys())
    only_a = sorted(k for k in keys if k not in b)
    only_b = sorted(k for k in keys if k not in a)
    common = sorted(k for k in keys if k in a and k in b)
    values_diff = {}
    equal = []
    numeric_diff_pct = {}
    for k in common:
        va, vb = a[k], b[k]
        if va == vb:
            equal.append(k)
            continue
        values_diff[k] = [va, vb]
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            try:
                base = abs(va) + abs(vb)
                if base > 0:
                    numeric_diff_pct[k] = round(abs(va - vb) / base * 200, 2)
            except Exception:
                pass
    return {
        "common_count": len(common),
        "equal_count": len(equal),
        "only_in_a": only_a,
        "only_in_b": only_b,
        "values_diff": values_diff,
        "numeric_diff_pct": numeric_diff_pct,
        "equal_keys": equal,
    }


def _label(meta: dict) -> str:
    """稳定桥梁标签：优先显示 id，并附带 name（若 name 干净）。

    若 name 是空、缺失，或是 history 里被 GBK 污染的乱码（如 '??01'），
    直接降级只用 id，避免 summary 显示一串问号。
    """
    bid = meta.get("id") or "?"
    raw_name = meta.get("name")
    if not raw_name or not isinstance(raw_name, str):
        return bid
    # 过滤掉被损坏的 name（含 ? 或控制字符）
    if any(ch in raw_name for ch in ("?", "\x00", "\n", "\t")):
        return bid
    return f"{raw_name}[{bid}]"


def _summary(a_meta: dict, b_meta: dict, p_diff: dict) -> str:
    """给一句话总结差异。"""
    a_label = _label(a_meta)
    b_label = _label(b_meta)
    eq = p_diff.get("equal_count", 0)
    cm = p_diff.get("common_count", 0)
    diff_keys = list(p_diff.get("values_diff", {}).keys())
    lines = [f"{a_label} ↔ {b_label}: {eq}/{cm} 参数完全相等"]
    if diff_keys:
        lines.append(f"差异 key: {', '.join(diff_keys[:5])}"
                     + ("..." if len(diff_keys) > 5 else ""))
    if p_diff.get("only_in_a"):
        lines.append(f"仅 A 独有: {', '.join(p_diff['only_in_a'][:3])}")
    if p_diff.get("only_in_b"):
        lines.append(f"仅 B 独有: {', '.join(p_diff['only_in_b'][:3])}")
    return " | ".join(lines)


def compare_bridges(bridge_a: str, bridge_b: str) -> dict:
    """对比两桥（按名字或 id）。

    返回 dict：
      - bridges.{a, b}: 快照
      - diff.params:     _param_diff 结果
      - diff.metrics:    指标差异（仅当双方都有）
      - summary:         字符串
    """
    a_id = _normalize_bridge_id(bridge_a)
    b_id = _normalize_bridge_id(bridge_b)
    if a_id is None:
        return {"error": f"桥梁 A '{bridge_a}' 未注册", "bridge_a": bridge_a,
                "bridge_b": bridge_b}
    if b_id is None:
        return {"error": f"桥梁 B '{bridge_b}' 未注册", "bridge_a": bridge_a,
                "bridge_b": bridge_b}
    if a_id == b_id:
        return {"error": f"两桥不能相同: '{a_id}'", "bridge_a": bridge_a,
                "bridge_b": bridge_b}

    snap_a = _bridge_snapshot(a_id)
    snap_b = _bridge_snapshot(b_id)

    diff = {
        "params": _param_diff(snap_a.get("params") or {}, snap_b.get("params") or {}),
        "metrics": _param_diff(snap_a.get("metrics") or {}, snap_b.get("metrics") or {}),
    }
    return {
        "bridge_a": bridge_a,
        "bridge_b": bridge_b,
        "bridges": {"a": snap_a, "b": snap_b},
        "diff": diff,
        "summary": _summary(snap_a, snap_b, diff["params"]),
    }
