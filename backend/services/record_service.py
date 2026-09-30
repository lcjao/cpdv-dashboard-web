"""实验记录服务（评审 G6）。

设计要点：
- append-only JSONL：每行一条完整记录，避免读改锁；写入带线程安全。
- 字段：timestamp / action / bridge_id / params / result / note
- 查询简单：bridge_id + action 过滤
- 「记录实验」自然语言命令示例：
    记录实验 bridge_01 depth=0.05 mv=8000
    记录实验 本次CPVD计算结果 depth=0.5
"""

from data_loader import append_record, load_records, count_records


def record_experiment(
    bridge_id: str,
    action: str,
    params: dict,
    result: dict = None,
    note: str = None,
) -> dict:
    """追加一条实验记录，返回 dict（含 auto-generated timestamp）。"""
    record = {
        "bridge_id": bridge_id,
        "action": action,
        "params": params or {},
        "result": result or {},
    }
    if note:
        record["note"] = note
    return append_record(record)


def list_records(bridge_id: str = None, action: str = None, limit: int = 50):
    """列出历史记录。limit 默认 50，按时间正序（最新在尾）。"""
    items = load_records(bridge_id=bridge_id, action=action, limit=limit)
    return {
        "total": count_records(),
        "filter": {"bridge_id": bridge_id, "action": action, "limit": limit},
        "items": items,
    }
