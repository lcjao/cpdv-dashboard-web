import json
import re
from pathlib import Path
import config


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_registry():
    return read_json(config.DATA_DIR / "registry.json", {"bridges": []})


def save_registry(data):
    write_json(config.DATA_DIR / "registry.json", data)


def load_dashboard_data():
    """优先读取看板工作区的 dashboard_data.js；否则返回空结构。"""
    js_path = config.DASHBOARD_WORKSPACE / "看板原型" / "dashboard_data.js"
    # 兼容不同编码环境
    for encoding in ("utf-8", "gbk", "utf-8-sig"):
        try:
            if js_path.exists():
                text = js_path.read_text(encoding=encoding)
                m = re.search(r"window\.DASHBOARD_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$", text)
                if m:
                    return json.loads(m.group(1))
            break
        except UnicodeDecodeError:
            continue
    return {"meta": {"metrics": {}}, "bridges": []}


# G13: 看板阈值默认值。env 覆盖格式：CPDV_THRESHOLDS_JSON='{"f1_min":0.9}'
# 与前端 Header.tsx 的 DEFAULT_THRESHOLDS 保持同步（只在此处管理）。
_DEFAULT_THRESHOLDS = {
    "pos_mae_max": 1.0,     # m
    "depth_mae_max": 0.05,  # 5%
    "f1_min": 0.87,
    "recall_min": 0.80,
    "precision_min": 0.80,
}


def _normalize_metrics(metrics: dict) -> dict:
    """Normalize metric keys from registry to frontend format.
    
    Registry may have old keys (pos_mae_m, depth_mae_m) or new keys (pos_mae, depth_mae).
    Frontend expects: pos_mae, depth_mae, f1, recall, precision, n_matched, n_gt, n_pred
    """
    return {
        "f1": metrics.get("f1", 0.0),
        "pos_mae": metrics.get("pos_mae") or metrics.get("pos_mae_m", 0.0),
        "depth_mae": metrics.get("depth_mae") or metrics.get("depth_mae_m", 0.0),
        "recall": metrics.get("recall", 0.0),
        "precision": metrics.get("precision", 0.0),
        "n_matched": metrics.get("n_matched", 0),
        "n_gt": metrics.get("n_gt", 0),
        "n_pred": metrics.get("n_pred", 0),
    }


def _empty_metrics() -> dict:
    """空 metrics 默认值（前端 Header.tsx 调 .toFixed() 不炸）。"""
    return {
        "pos_mae": 0.0,
        "depth_mae": 0.0,
        "recall": 0.0,
        "precision": 0.0,
        "f1": 0.0,
        "n_matched": 0,
        "n_gt": 0,
        "n_pred": 0,
    }


def _dashboard_thresholds() -> dict:
    """返回 DashboardMeta.thresholds 字段。可通过 env CPDV_THRESHOLDS_JSON 覆盖。"""
    import os as _os
    raw = _os.environ.get("CPDV_THRESHOLDS_JSON", "").strip()
    if not raw:
        return dict(_DEFAULT_THRESHOLDS)
    try:
        override = json.loads(raw)
        merged = {**_DEFAULT_THRESHOLDS, **override}
        return merged
    except json.JSONDecodeError:
        return dict(_DEFAULT_THRESHOLDS)


# ─────────────────────────────────────────────────────────────────────
# Dashboard 合并视图（G8：单一前端看板入口，registry + records 自动合并）
# ─────────────────────────────────────────────────────────────────────
def load_dashboard_merged() -> dict:
    """合并 registry.json + records.jsonl 返回 DashboardData 兼容结构。

    schema（与前端 types.ts 中 DashboardData / Bridge / DashboardMeta 保持一致）：
      {
        meta:   { model, checkpoint, metrics, n_bridges, n_records, generated, source },
        bridges: [
          { id, name, params, cpdv, cpdv_len, cpdv_offset,
            n_true, n_pred, n_hit, n_miss, n_false,
            true_cracks, pred_cracks,
            metrics, model_path, last_trained_at, last_record },
          ...
        ]
      }

    字段填充策略：
      - id/name/params: 来自 registry.json
      - metrics/model_path/last_trained_at: 来自 registry[i].meta（训练后才有）
      - last_record: 来自 records.jsonl 的最近 1 条（按 bridge_id 过滤）
      - cpdv*/n_*/cracks*: 默认空（用户跑 cpdv/predict 后由前端单独缓存）
      - meta.metrics: 默认取首桥 meta；多桥时取第一座有训练的桥
      - n_bridges/n_records: 实时统计
    """
    from datetime import datetime, timezone

    reg = load_registry()
    raw_bridges = reg.get("bridges", [])

    bridges = []
    fallback_meta = None
    for b in raw_bridges:
        bid = b.get("id")
        meta = b.get("meta") or {}
        # 最近一条 record
        recs = load_records(bridge_id=bid, limit=1)
        last = recs[-1] if recs else None
        last_record = (
            {k: last[k] for k in ("timestamp", "action", "params", "note", "result")
             if k in last}
            if last else None
        )
        bridge_view = {
            "id": bid,
            "name": b.get("name") or bid,
            "params": b.get("params") or {},
            # 占位 cpdv / 真伪裂缝字段；用户主动跑 cpdv 才会有真实数据
            "cpdv": [],
            "cpdv_len": 0,
            "cpdv_offset": 0,
            "cpdv_signals": b.get("cpdv_signals") or [],
            "combined_cpdv": b.get("combined_cpdv") or [],
            # 方案A（2026-09）：多裂缝预测结果由 multi_crack_service 写回 registry，
            # 看板合并视图直接读取 → 预测后刷新即展示（不再前端缓存）
            "n_true": b.get("n_true", 0),
            "n_pred": b.get("n_pred", 0),
            "n_hit": b.get("n_hit", 0),
            "n_miss": b.get("n_miss", 0),
            "n_false": b.get("n_false", 0),
            "true_cracks": b.get("true_cracks") or [],
            "pred_cracks": b.get("pred_cracks") or [],
            "last_predict_at": b.get("last_predict_at"),
            # 注册后的附加信息（直接暴露方便前端展示）
            "metrics": _normalize_metrics(meta.get("metrics") or {}),
            "model_path": meta.get("model_path"),
            "last_trained_at": meta.get("last_trained_at"),
            "train_duration_s": meta.get("train_duration_s"),
            "status": b.get("status") or "registered",
            "last_record": last_record,
            "last_updated": b.get("last_updated"),
            # G23: 信号文件元数据（用于前端懒加载）
            "signal_files": b.get("signal_files") or {},
        }
        # 加载实际信号数据
        sf = b.get("signal_files") or {}
        if sf.get("has_signals"):
            sig_data = load_bridge_signals(bid)
            if sig_data:
                bridge_view["cpdv_signals"] = sig_data.get("cpdv_signals") or []
                bridge_view["combined_cpdv"] = sig_data.get("combined_cpdv") or []
        bridges.append(bridge_view)
        if fallback_meta is None and meta:
            fallback_meta = {
                "model_path": meta.get("model_path"),
                "metrics": _normalize_metrics(meta.get("metrics") or {}),
                "last_trained_at": meta.get("last_trained_at"),
            }

    # meta 信息（兼容 DashboardMeta，但加 source 标识）
    if fallback_meta:
        meta_out = {
            "model": fallback_meta.get("model_path") or "",
            "checkpoint": fallback_meta.get("model_path") or "",
            "metrics": fallback_meta.get("metrics") or _empty_metrics(),
            "thresholds": _dashboard_thresholds(),  # G13: 随 meta 下发
            "test_size": 0,
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "由 /api/dashboard 在 GET 时合并 registry+records 实时生成（评审 G8 联动方案 B）",
        }
    else:
        # 与有数据分支保持一致：永远下发完整的 metrics 字段（缺则 0），
        # 否则前端 Header.tsx 调 .toFixed() 会炸。
        meta_out = {
            "model": "",
            "checkpoint": "",
            "metrics": _empty_metrics(),
            "thresholds": _dashboard_thresholds(),  # G13
            "test_size": 0,
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "暂无桥梁训练数据；注册 + 训练后这里会自动出现指标。",
        }

    return {
        "meta": {
            **meta_out,
            "n_bridges": len(bridges),
            "n_records": count_records(),
            "source": "registry+records(merged)",
        },
        "bridges": bridges,
    }


def merge_legacy_bridges(merged: dict, legacy: dict) -> dict:
    """把 legacy dashboard_data.js 的桥合并进 merged 视图（id 去重）。

    背景：G8 合并视图（registry+records）的桥 cpdv 为占位空数组；而 legacy
    dashboard_data.js 含真实 CPDV 信号（400 点/桥）。合并后注册桥在前、
    legacy 桥在后，保证看板 CPDV 图有真实数据可渲染。
    """
    out = dict(merged)
    bridges = list(out.get("bridges", []))
    seen = {b.get("id") for b in bridges}
    for lb in legacy.get("bridges", []):
        bid = lb.get("id")
        if bid in seen:
            continue
        seen.add(bid)
        bridges.append({**lb, "status": "legacy", "source": "legacy.dashboard_data.js"})
    out["bridges"] = bridges
    return out


# ─────────────────────────────────────────────────────────────────────
# CPDV 完整时间序列持久化（G19：registry 桥条目新增 cpdv_signals）
# ─────────────────────────────────────────────────────────────────────
def save_bridge_cpdv_signals(bridge_id: str, signals: list):
    """把 [{'pos': float, 'signal': [...]}, ...] 写入 registry 对应桥条目，返回 True/False。"""
    reg = load_registry()
    _script_dir = Path(__file__).parent
    signals_dir = _script_dir / 'data' / 'signals' / bridge_id
    signals_dir.mkdir(parents=True, exist_ok=True)
    with open(signals_dir / 'cpdv_signals.json', 'w', encoding='utf-8') as f:
        json.dump(signals, f, ensure_ascii=False)
    # 写回 registry 元数据（缩进修复：原版本文件写入代码误放错层级，registry 一直未更新）
    found = False
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            b["cpdv_signals"] = signals
            b["signal_files"] = {
                "has_signals": True,
                "cpdv_signals": str(signals_dir / 'cpdv_signals.json'),
            }
            found = True
    if found:
        save_registry(reg)
    return found



def save_bridge_combined_cpdv(bridge_id: str, combined_signal: list):
    """保存多裂缝组合 CPDV 信号到 registry（G21）。"""
    reg = load_registry()
    _script_dir = Path(__file__).parent
    signals_dir = _script_dir / 'data' / 'signals' / bridge_id
    signals_dir.mkdir(parents=True, exist_ok=True)
    with open(signals_dir / 'combined_cpdv.json', 'w', encoding='utf-8') as f:
        json.dump(combined_signal, f, ensure_ascii=False)
    found = False
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            b["combined_cpdv"] = combined_signal
            sf = b.setdefault("signal_files", {"has_signals": False})
            sf["combined_cpdv"] = str(signals_dir / 'combined_cpdv.json')
            sf["has_signals"] = True
            found = True
    if found:
        save_registry(reg)
    return found

def save_bridge_multi_crack_result(bridge_id: str, result: dict):
    """把多裂缝预测结果（true/pred_cracks + n_* 统计）写入 registry 对应桥条目，返回 True/False。

    方案A（2026-09）：prediction 字典字段直接落盘；加载见 load_dashboard_merged。
    """
    reg = load_registry()
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            for k in ("n_true", "n_pred", "n_hit", "n_miss", "n_false",
                      "true_cracks", "pred_cracks", "combined_cpdv"):
                if k in result:
                    b[k] = result[k]
            from datetime import datetime, timezone
            b["last_predict_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            save_registry(reg)
            return True
    return False


# ─────────────────────────────────────────────────────────────────────
# 实验记录（records.jsonl，每行一条 JSON，便于追加）
# ─────────────────────────────────────────────────────────────────────
def _records_path():
    return config.DATA_DIR / "records.jsonl"


def append_record(record: dict):
    """追加一条实验记录到 records.jsonl，返回带 timestamp 的 record dict。"""
    path = _records_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if "timestamp" not in record:
        from datetime import datetime, timezone
        record["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_records(bridge_id: str = None, action: str = None, limit: int = None):
    """读取 records.jsonl，可按 bridge_id / action 过滤，limit 取最近 N 条。"""
    path = _records_path()
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if bridge_id and r.get("bridge_id") != bridge_id:
                continue
            if action and r.get("action") != action:
                continue
            out.append(r)
    if limit:
        out = out[-limit:]
    return out


def count_records() -> int:
    path = _records_path()
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n




def load_bridge_signals(bridge_id: str) -> dict | None:
    """Lazy load CPDV signals from separate signal files."""
    # Signals are stored in backend/data/signals, not in the workspace
    _script_dir = Path(__file__).parent
    signals_dir = _script_dir / 'data' / 'signals' / bridge_id
    if not signals_dir.exists():
        return None
    
    result = {}
    
    # Load cpdv_signals
    signals_file = signals_dir / 'cpdv_signals.json'
    if signals_file.exists():
        with open(signals_file, 'r', encoding='utf-8') as f:
            result['cpdv_signals'] = json.load(f)
    
    # Load combined_cpdv
    combined_file = signals_dir / 'combined_cpdv.json'
    if combined_file.exists():
        with open(combined_file, 'r', encoding='utf-8') as f:
            result['combined_cpdv'] = json.load(f)
    
    return result if result else None


def clean_associated_data(bridge_id: str) -> dict:
    """删除桥梁相关的所有派生数据（看板 JSON、CPDV 信号图、推理缓存、实验记录等）。

    Returns:
        dict: 清理结果统计 {removed_files, removed_records, errors}
    """
    import glob
    import os
    from pathlib import Path
    import config

    # 输出目录：algorithm-code 看板导出 outputs/ 目录（config.OUTPUTS_DIR）
    OUTPUTS_DIR = config.OUTPUTS_DIR

    result = {"removed_files": [], "removed_records": 0, "errors": []}

    def _safe_remove(path: Path, desc: str):
        try:
            if path.exists():
                path.unlink()
                result["removed_files"].append(f"{desc}: {path}")
        except Exception as e:
            result["errors"].append(f"{desc} {path}: {e}")

    # 1) 看板工作区 JSON（若存在）
    dash_dir = config.DASHBOARD_WORKSPACE / "bridges"
    _safe_remove(dash_dir / f"{bridge_id}.json", "看板桥梁JSON")

    # 2) CPDV 信号图（outputs/figures/）
    for fig in glob.glob(str(OUTPUTS_DIR / "figures" / f"cpdv_{bridge_id}_*.png")):
        _safe_remove(Path(fig), "CPDV信号图")

    # 3) 训练/推理产生的模型/报告（若按 bridge_id 命名）
    for pattern in [
        OUTPUTS_DIR / "models" / f"*{bridge_id}*.pth",
        OUTPUTS_DIR / "reports" / f"*{bridge_id}*.json",
    ]:
        for p in glob.glob(str(pattern)):
            _safe_remove(Path(p), "模型/报告")

    # 4) 实验记录（records.jsonl）——按 bridge_id 过滤重写
    records_path = _records_path()
    if records_path.exists():
        try:
            kept = []
            removed = 0
            with open(records_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        kept.append(line)
                        continue
                    if r.get("bridge_id") == bridge_id:
                        removed += 1
                    else:
                        kept.append(line)
            if removed:
                with open(records_path, "w", encoding="utf-8", newline="\n") as f:
                    for line in kept:
                        f.write(line + "\n")
                result["removed_records"] = removed
                result["removed_files"].append(f"实验记录: 删 {removed} 条")
        except Exception as e:
            result["errors"].append(f"records.jsonl 清理失败: {e}")

    return result
