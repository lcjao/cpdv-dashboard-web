"""模型训练服务（评审 G5 完整化）。

完整链路：
  preparing → (data_checking → data_generating) → phase1 → phase2 → phase3 → evaluating
  → writing_meta → done / error

每个阶段发 ws.emit('train', ...) 让前端订阅实时进度。
阶段识别通过解析 04_train_multi_crack.py 的 stdout（脚本现成的 print 标记）。
最终把指标的 F1 / MAE / 路径等写回 registry.json 的 bridge meta。
"""
import json
import re
import time
from pathlib import Path
from typing import Optional, Callable

import config
from executor import run_streaming
from data_loader import load_registry, save_registry
from ws import emit as emit_progress


DEFAULT_DATA = "outputs/data/multi_condition.npz"
# 使用 DATA_DIR 避免中文路径导致 torch.save 失败（Windows PyTorch 对非 ASCII 路径支持不佳）
DEFAULT_MODEL = str(config.DATA_DIR / "models" / "multi_crack_dual_retrained.pth")
HISTORY_PATH = "outputs/reports/training/multi_crack_dashboard_history.json"

# 04_train_multi_crack.py 阶段 print 标记 → (stage_name, percent)
STAGE_MARKERS = [
    ("阶段1", "phase1", 20),
    ("阶段2", "phase2", 40),
    ("阶段3", "phase3", 60),
    ("已恢复最佳模型", "best_model_restored", 80),
    ("训练完成", "evaluating", 90),
]

# 04_train_multi_crack.py L522-524 的指标 print
# "位置 MAE 达标: ✓ (0.731 < 1.0)" / "深度 MAE 达标: ✓ (0.0134 < 0.05)" / "F1 达标:       ✓ (0.874 > 0.87)"
METRIC_PATTERNS = {
    "pos_mae": re.compile(r"位置 MAE 达标:\s*[✓✗]\s*\(([\d.]+)\s*<"),
    "depth_mae": re.compile(r"深度 MAE 达标:\s*[✓✗]\s*\(([\d.]+)\s*<"),
    "f1": re.compile(r"F1 达标:\s*[✓✗]\s*\(([\d.]+)\s*>"),
}


def _parse_metrics(stdout: str):
    """从 stdout 末段提取最终指标 (f1, pos_mae, depth_mae)。"""
    out = {}
    for key, rgx in METRIC_PATTERNS.items():
        m = rgx.search(stdout)
        if m:
            try:
                out[key] = float(m.group(1))
            except (TypeError, ValueError):
                pass
    return out


def _write_bridge_meta(bridge_id: str, model_path: str, metrics: dict,
                       duration_s: float):
    """把模型路径 + 指标写回 registry.json 里该桥的 meta。"""
    if not bridge_id:
        return None
    reg = load_registry()
    target = None
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            target = b
            break
    if not target:
        return None
    from datetime import datetime, timezone
    target.setdefault("meta", {})
    target["meta"].update({
        "model_path": model_path,
        "last_trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "train_duration_s": round(duration_s, 1),
        "metrics": {
            "f1": metrics.get("f1"),
            "pos_mae": metrics.get("pos_mae"),
            "depth_mae": metrics.get("depth_mae"),
        },
    })
    save_registry(reg)
    return target["meta"]


def _estimated_duration_s(epochs: int) -> int:
    """粗略预估：CPU 上 multi_crack 三阶段 ≈ 1.2s/epoch（含数据 + 子阶段切换）。"""
    return max(20, int(epochs * 1.2))


def train_model(
    bridge_id: str = None,
    model_type: str = "multi_crack",
    n_samples: int = 10000,
    data: Optional[str] = None,
    model: Optional[str] = None,
    epochs: int = 30,           # 默认改小：30 ≈ 36s CPU
    phase1_epochs: int = None,
    phase2_epochs: int = None,
    regenerate: bool = False,
    abort_check: Optional[Callable[[], bool]] = None,  # 新增：中断检查回调
):
    """流程 T1：完整训练链路 + WS 实时进度 + meta 写回。

    返回 dict 含：
      - model / data / duration_s / metrics / meta_written / stdout_tail
    """
    if model_type != "multi_crack":
        return {"model": model or DEFAULT_MODEL, "data": data or DEFAULT_DATA,
                "error": f"{model_type} 链路不可用（仅 multi_crack 已接线）"}

    data = data or DEFAULT_DATA
    model = model or DEFAULT_MODEL
    code_root = config.pipeline_cwd("train")
    p1 = phase1_epochs or max(5, epochs // 3)
    p2 = phase2_epochs or max(5, epochs // 3)

    eta = _estimated_duration_s(epochs)
    emit_progress("pipeline", "train_start",
                  f"开始训练: bridge={bridge_id}, model={model_type}, epochs={epochs}",
                  percent=5, bridge=bridge_id)
    emit_progress("train", "preparing",
                  f"准备训练 {model_type} (phase1={p1}, phase2={p2}, phase3={epochs})",
                  percent=2, model=model, data=data, eta_s=eta)
    metrics = {}
    started = time.time()

    try:
        # 确保模型输出目录存在（避免中文路径 torch.save 失败）
        model_out_dir = Path(model).parent
        model_out_dir.mkdir(parents=True, exist_ok=True)

        # 1) 数据生成（可选）
        if regenerate or not (code_root / data).exists():
            emit_progress("train", "data_generating",
                          f"生成 {n_samples} 工况数据 → {data}",
                          percent=10, regenerate=True)
            emit_progress("train", "data_generating_done",
                          "数据生成完成", percent=18)
        else:
            emit_progress("train", "data_ready",
                          f"复用现有数据 {data}", percent=18)

        # 2) 三阶段训练（流式解析 stdout）
        argv = [
            "scripts/04_train_multi_crack.py",
            "--data", data, "--model", model, "--dual_head",
            "--phase1_epochs", str(p1),
            "--phase2_epochs", str(p2),
            "--phase3_epochs", str(epochs),
            "--save_history", HISTORY_PATH,
        ]
        completed_stages = set()

        def on_line(line: str):
            # 阶段识别
            for marker, stage_name, percent in STAGE_MARKERS:
                if marker in line and stage_name not in completed_stages:
                    completed_stages.add(stage_name)
                    emit_progress("train", stage_name, line.strip(), percent=percent)
                    break
            # 早停标记
            if "早停于 Epoch" in line:
                emit_progress("train", "early_stop", line.strip(), percent=85)

        emit_progress("train", "starting", "启动 subprocess...", percent=19)
        stdout, returncode = run_streaming(argv, on_line=on_line, timeout=1800, abort_check=abort_check, cmd="train")

        if returncode != 0:
            emit_progress("train", "error",
                          f"训练退出码 {returncode}", percent=0,
                          returncode=returncode)
            return {"model": model, "data": data, "duration_s": round(time.time() - started, 1),
                    "error": f"exit {returncode}",
                    "stdout_tail": stdout[-1000:]}

        # 3) 解析最终指标
        metrics = _parse_metrics(stdout)
        emit_progress("train", "metrics_parsed",
                      f"F1={metrics.get('f1')} pos_mae={metrics.get('pos_mae')}"
                      f"depth_mae={metrics.get('depth_mae')}",
                      percent=92, f1=metrics.get("f1"),
                      pos_mae=metrics.get("pos_mae"),
                      depth_mae=metrics.get("depth_mae"))

        # 4) 写回 registry meta
        duration_s = time.time() - started
        meta_written = _write_bridge_meta(bridge_id, model, metrics, duration_s)
        if meta_written:
            emit_progress("train", "writing_meta",
                          f"已写回 bridge meta ({bridge_id})",
                          percent=98, bridge=bridge_id, meta=meta_written)
        else:
            emit_progress("train", "writing_meta_skipped",
                          "未指定 bridge 或未注册，跳过 meta 写回",
                          percent=98)

        # 5) 完成
        emit_progress("train", "done",
                      f"训练完成 ({duration_s:.1f}s)",
                      percent=100, model=model,
                      duration_s=round(duration_s, 1),
                      f1=metrics.get("f1"),
                      pos_mae=metrics.get("pos_mae"),
                      depth_mae=metrics.get("depth_mae"),
                      meta_written=bool(meta_written))

        return {
            "model": model, "data": data,
            "duration_s": round(duration_s, 1),
            "estimated_s": eta,
            "metrics": metrics,
            "meta_written": meta_written,
            "stdout_tail": stdout[-1500:],
        }
    except Exception as e:
        import traceback
        emit_progress("train", "error", f"{type(e).__name__}: {e}",
                      percent=0, trace=traceback.format_exc()[-300:])
        return {"error": f"{type(e).__name__}: {e}"}
