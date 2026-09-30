"""模型评估服务（评审 G6 — 完善评估指标）。

运行外部评估脚本 (05_infer_multi_crack.py) 计算完整指标：
- pos_mae, depth_mae, recall, precision, f1
- n_matched, n_gt, n_pred

并将结果写回 registry.json 的 bridge meta。
"""
import os
import json
import time
from pathlib import Path
from typing import Optional

import config
from executor import run
from data_loader import load_registry, save_registry
from ws import emit as emit_progress


DEFAULT_MODEL = str(config.DATA_DIR / "models" / "multi_crack_dual_retrained.pth")
DEFAULT_DATA = "outputs/data/multi_condition.npz"


def _parse_eval_metrics(stdout: str) -> dict:
    """从 05_infer_multi_crack.py stdout 解析评估指标。"""
    metrics = {}
    patterns = {
        "pos_mae": r"位置 MAE:\s+([\d.]+)",
        "depth_mae": r"深度 MAE:\s+([\d.]+)",
        "recall": r"Recall:\s+([\d.]+)",
        "precision": r"Precision:\s+([\d.]+)",
        "f1": r"F1 Score:\s+([\d.]+)",
        "n_matched": r"匹配数:\s+(\d+)",
        "n_gt": r"真实裂缝数:\s+(\d+)",
        "n_pred": r"预测裂缝数:\s+(\d+)",
    }
    for key, pattern in patterns.items():
        import re
        m = re.search(pattern, stdout)
        if m:
            try:
                val = float(m.group(1)) if key in ("pos_mae", "depth_mae", "recall", "precision", "f1") else int(m.group(1))
                metrics[key] = val
            except (TypeError, ValueError):
                pass
    return metrics


def _write_bridge_eval_meta(bridge_id: str, metrics: dict) -> dict:
    """把评估指标写回 registry.json 里该桥的 meta。
    
    Raises:
        ValueError: 如果 bridge_id 未指定或桥梁未注册
        RuntimeError: 如果写入失败
    """
    if not bridge_id:
        raise ValueError("bridge_id 未指定，无法写回评估指标")
    reg = load_registry()
    target = None
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            target = b
            break
    if not target:
        raise ValueError(f"桥梁 '{bridge_id}' 未注册，无法写回评估指标")
    from datetime import datetime, timezone
    target.setdefault("meta", {})
    target["meta"].update({
        "last_evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metrics": metrics,  # 完整覆盖，包含 recall/precision/n_matched 等
    })
    save_registry(reg)
    # 校验写入成功
    if target["meta"].get("metrics") != metrics:
        raise RuntimeError("registry 写入后校验失败：metrics 不一致")
    return target["meta"]


def run_streaming_with_timeout(cmd_args, timeout=300):
    """简化版流式执行，返回 (stdout, returncode)。"""
    import subprocess
    import threading
    import os

    _ENV = {**{k: v for k, v in os.environ.items() if v is not None}, "PYTHONIOENCODING": "utf-8"}
    _CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

    proc = subprocess.Popen(
        [config.PYTHON_EXE, *cmd_args],
        cwd=str(config.pipeline_cwd("evaluate")),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        env=_ENV, creationflags=_CREATE_NO_WINDOW,
    )
    captured = []
    stop_event = threading.Event()

    def reader():
        try:
            while not stop_event.is_set():
                line = proc.stdout.readline()
                if not line:
                    break
                captured.append(line)
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    try:
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            captured.append(f"\n[timeout after {timeout}s, killed]\n")
        stop_event.set()
        reader_thread.join(timeout=2)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return "".join(captured), proc.returncode


def evaluate_model(
    bridge_id: str = None,
    model: str = None,
    input_data: str = None,
    cls_threshold: float = 0.3,
    match_cost: float = 5.0,
    pos_threshold: float = 0.0,
) -> dict:
    """流程 E1：运行完整评估 + 写回 registry meta。

    返回 dict 含：
      - model / input_data / duration_s / metrics / meta_written / stdout_tail
    """
    model = model or DEFAULT_MODEL
    input_data = input_data or DEFAULT_DATA
    code_root = config.pipeline_cwd("evaluate")

    # 修复 LLM 工具调用 JSON 转义破坏的路径（退格符/双反斜杠）
    model = config.sanitize_path(model)

    # 模型路径兜底：LLM 常传裸文件名；相对 code_root 找不到时回退 backend/data/models/（train 产出位置）
    # 绝对路径（含 LLM 传的全路径，可能已被 sanitize）不存在时，同样按文件名回退
    _mp = Path(model)
    if _mp.is_absolute():
        if not _mp.exists():
            _fb = config.DATA_DIR / "models" / _mp.name
            if _fb.exists():
                model = str(_fb)
    else:
        if not (code_root / model).exists() and (config.DATA_DIR / "models" / _mp.name).exists():
            model = str(config.DATA_DIR / "models" / _mp.name)

    # 检查模型和数据文件
    if not (Path(model) if Path(model).is_absolute() else (code_root / model)).exists():
        return {"error": f"模型文件不存在: {model}"}
    if not (code_root / input_data).exists():
        return {"error": f"数据文息不存在: {input_data}"}

    emit_progress("evaluate", "preparing",
                  f"准备评估 bridge={bridge_id or 'unknown'} model={model}",
                  percent=2, bridge=bridge_id, model=model, data=input_data)

    started = time.time()

    try:
        # 运行评估脚本
        argv = [
            "scripts/05_infer_multi_crack.py",
            "--model", model,
            "--input", input_data,
            "--cls_threshold", str(cls_threshold),
            "--match_cost", str(match_cost),
            "--pos_threshold", str(pos_threshold),
        ]

        emit_progress("evaluate", "starting", "启动评估脚本...", percent=10)
        stdout, returncode = run_streaming_with_timeout(argv, timeout=300)

        if returncode != 0:
            emit_progress("evaluate", "error",
                          f"评估退出码 {returncode}", percent=0,
                          returncode=returncode)
            return {"model": model, "data": input_data,
                    "duration_s": round(time.time() - started, 1),
                    "error": f"exit {returncode}",
                    "stdout_tail": stdout[-1500:]}

        # 解析指标
        metrics = _parse_eval_metrics(stdout)
        emit_progress("evaluate", "metrics_parsed",
                      f"F1={metrics.get('f1')} pos_mae={metrics.get('pos_mae')} "
                      f"depth_mae={metrics.get('depth_mae')} recall={metrics.get('recall')} "
                      f"precision={metrics.get('precision')}",
                      percent=90, **metrics)

        # 写回 registry meta
        duration_s = time.time() - started
        meta_written = _write_bridge_eval_meta(bridge_id, metrics)
        emit_progress("evaluate", "writing_meta",
                      f"已写回 bridge meta ({bridge_id})",
                      percent=98, bridge=bridge_id, meta=meta_written)

        emit_progress("evaluate", "done",
                      f"评估完成 ({duration_s:.1f}s)",
                      percent=100, duration_s=round(duration_s, 1),
                      **metrics, meta_written=True)

        return {
            "model": model, "data": input_data,
            "duration_s": round(duration_s, 1),
            "metrics": metrics,
            "meta_written": meta_written,
            "stdout_tail": stdout[-1500:],
        }

    except Exception as e:
        import traceback
        emit_progress("evaluate", "error", f"{type(e).__name__}: {e}",
                      percent=0, trace=traceback.format_exc()[-300:])
        # 重新抛出异常，让调用方处理（不再静默返回 error dict）
        raise


def run_streaming_with_timeout(cmd_args, timeout=300):
    """简化版流式执行，返回 (stdout, returncode)。"""
    import subprocess
    import threading
    import os

    _ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    _CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

    proc = subprocess.Popen(
        [config.PYTHON_EXE, *cmd_args],
        cwd=str(config.pipeline_cwd("evaluate")),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        env=_ENV, creationflags=_CREATE_NO_WINDOW,
    )
    captured = []
    stop_event = threading.Event()

    def reader():
        try:
            while not stop_event.is_set():
                line = proc.stdout.readline()
                if not line:
                    break
                captured.append(line)
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    try:
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            captured.append(f"\n[timeout after {timeout}s, killed]\n")
        stop_event.set()
        reader_thread.join(timeout=2)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return "".join(captured), proc.returncode