# -*- coding: utf-8 -*-
"""流程 C3：多裂缝推理。

方案A（2026-09）：predict_multi_crack 支持 bridge_id —— 读注册桥 cpdv_signals 的
(位置, 深度) 列表 → 用训练数据生成路径（fresh 实例 + uc_healthy 复制）重新生成多裂缝
组合信号 → 标准化 → 双头推理 → 解码 pred_cracks → greedy_match 匹配 → 写回 registry
（true/pred_cracks + n_* 字段）。load_dashboard_merged 同步读取 → 前端看板 ③ 区不再空白。
无 bridge_id 时保持原行为（跑 05_infer 测试集评估）。
"""
import json
import re
import config
from executor import run
from services.stdout_parser import parse as _parse

# 与仓库 export_dashboard_data.py / 05_infer_multi_crack.py 保持一致
CLS_THRESHOLD = 0.15
MATCH_COST = 5.0
MAX_CPDV_LENGTH = 5000
# 绝对路径（对齐 train_service.py）：子进程 cwd 是 pipeline-4 子目录，相对路径会解析到
# pipeline-4/outputs/models/（无 retrained 模型），实际模型在 backend/data/models/
DEFAULT_MODEL = str(config.DATA_DIR / "models" / "multi_crack_dual_retrained.pth")
DEFAULT_INPUT = "outputs/data/multi_condition.npz"


def _sanitize_model_path(s: str) -> str:
    """修复 JSON 转义破坏的 Windows 路径（实现统一放 config.sanitize_path，多服务共用）。"""
    return config.sanitize_path(s)


def resolve_model(model: str, cmd: str = "multi_crack") -> str:
    """模型路径兜底：先修复 JSON 转义破坏（_sanitize_model_path），再按规则解析。

    LLM 常传裸文件名（multi_crack_dual_retrained.pth），子进程 cwd 是 pipeline-4，
    相对路径会解析到 pipeline-4/outputs/models/（不存在）。优先按原路径找；
    找不到则回退到 backend/data/models/<文件名>（train 产出位置）。
    绝对路径也不存在时同样按文件名回退；最后原样返回保持报错可读。"""
    from pathlib import Path as _P
    p = _P(_sanitize_model_path(model))
    if p.is_absolute():
        if p.exists():
            return str(p)
        fallback = config.DATA_DIR / "models" / p.name
        if fallback.exists():
            return str(fallback)
        return str(p)
    cand1 = config.pipeline_cwd(cmd) / p
    if cand1.exists():
        return str(cand1)
    fallback = config.DATA_DIR / "models" / p.name
    if fallback.exists():
        return str(fallback)
    # 都找不到：返回原样（让子进程报错信息保持可读）
    return model


# 单桥推理结果行（PRED_CRACKS: {json}，供本模块解析）
_RE_PRED = re.compile(r"^PRED_CRACKS:\s*(\{.*\})", re.M)

# 内联推理代码：复刻 generator.py 训练数据生成路径（L489-491，
# fresh 实例 + uc_healthy.copy() + analyze_multi_cracks + calculate_cpdv），
# 与 05_infer_multi_crack.py 的标准化/反标准化/解码口径一致。
# 占位符：@MODEL_PATH@ / @SIGNAL_FILE@ / @PARAMS@ / @CRACK_LIST@ / @CLS_THRESHOLD@ / @MATCH_COST@ / @MAX_LEN@
# @SIGNAL_FILE@ 非空且文件存在时走快速路径：直接复用预计算组合 CPDV，跳过完整 FEM 仿真（>300s→~2s）。
_INFER_INLINE_CODE = r'''
import json, sys, os
sys.path.insert(0, ".")
import config
import numpy as np
import torch
from simulation.system_iteration import EnhancedBridgeVehicleSystem
from model.multi_crack import MultiCrackDualHead

MODEL_PATH = @MODEL_PATH@
SIGNAL_FILE = @SIGNAL_FILE@
PARAMS = @PARAMS@
CRACK_LIST = @CRACK_LIST@
CLS_THRESHOLD = 0.15
MATCH_COST = @MATCH_COST@
MAX_LEN = @MAX_LEN@

# 1) 加载模型与统计量
ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
ck = ckpt
input_dim = ck["input_dim"]
hidden_dim = ck.get("hidden_dim", 256)
num_layers = ck.get("num_layers", 3)
max_cracks = ck.get("max_cracks", 5)
model = MultiCrackDualHead(
    input_dim=input_dim, hidden_dim=hidden_dim,
    num_layers=num_layers, max_cracks=max_cracks,
)
model.load_state_dict(ck["model_state_dict"])
model.eval()
X_mean = ck["X_mean"].flatten()
X_std = ck["X_std"].flatten()
y_mean = ck["y_mean"].flatten()
y_std = ck["y_std"].flatten()

# 2) 组合 CPDV 信号：优先复用预计算缓存（快速路径，跳过 FEM 仿真）；无缓存才重仿真
cpdv_raw = None
if SIGNAL_FILE and str(SIGNAL_FILE).strip():
    if os.path.exists(SIGNAL_FILE):
        with open(SIGNAL_FILE, "r", encoding="utf-8") as _sf:
            _data = json.load(_sf)
        cpdv_raw = _data
        if isinstance(_data, dict):
            if "cpdv" in _data:
                cpdv_raw = _data["cpdv"]
            elif "combined_cpdv" in _data:
                _inner = _data["combined_cpdv"]
                cpdv_raw = _inner.get("cpdv") if isinstance(_inner, dict) else _inner
        if isinstance(cpdv_raw, dict):
            cpdv_raw = cpdv_raw.get("cpdv", [])
        cpdv_raw = [float(v) for v in cpdv_raw]
        print(f"[fast] Reused precomputed CPDV from {os.path.basename(SIGNAL_FILE)} "
              f"({len(cpdv_raw)} pts); FEM simulation skipped")
    else:
        print(f"[fast] SIGNAL_FILE missing ({SIGNAL_FILE}); falling back to FEM simulation")

if cpdv_raw is None or len(cpdv_raw) == 0:
    # 训练路径：健康分析实例A → fresh 实例B 复制 uc_healthy
    sc_sys = EnhancedBridgeVehicleSystem(params=PARAMS)
    sc_sys.road_type = PARAMS.get("road_type", "b")
    if sc_sys.uc_healthy is None:
        sc_sys.run_analysis()
    uc_healthy = sc_sys.uc_healthy.copy()
    sample_sys = EnhancedBridgeVehicleSystem(params=PARAMS)
    sample_sys.uc_healthy = uc_healthy
    sample_sys.road_type = PARAMS.get("road_type", "b")
    results = sample_sys.analyze_multi_cracks(CRACK_LIST)
    cpdv_raw = sample_sys.calculate_cpdv(results["uc"])

if cpdv_raw is None or len(cpdv_raw) == 0 or not np.all(np.isfinite(cpdv_raw)):
    raise RuntimeError("组合 CPDV 信号生成失败")

# 3) padding + 逐特征归一化（精度修复 2026-09）
# checkpoint X_std 含 ~2108 个近零 std（<1e-3，39 个 ~1e-7），直接相除使
# max_abs_x≈5e5、输入彻底脱离训练分布，回归头被污染（深度误差 0.19~0.23m）。
# 实测对比（3 座注册桥 × 多阈值，按真值 greedy 打分）：
#   逐特征 + floor=0.05*median(|X_std|)：命中 6、深度误差 0.04m、max_abs_x≈25（最优）
#   行标准化（05_infer 口径）：0 命中 —— 5000 维 checkpoint 按逐特征训练，不适用
#   floor≥5e-3：压掉 1e-3~1e-2 段有效小 std 特征，0 命中
sig = np.zeros(MAX_LEN)
sig[: min(len(cpdv_raw), MAX_LEN)] = cpdv_raw[:MAX_LEN]
_STD_FLOOR = 0.05 * float(np.median(np.abs(X_std)))
x = (sig - X_mean) / np.maximum(X_std, _STD_FLOOR)
print(f"[norm] per-feature std floor={_STD_FLOOR:.3e} (0.05*median); max_abs_x={np.abs(x).max():.4g}")

# 4) 推理
with torch.no_grad():
    cls_logits, reg_pred = model(torch.FloatTensor(x.reshape(1, -1)))
probs = torch.sigmoid(cls_logits).numpy()
reg_raw = reg_pred.numpy() * y_std + y_mean

# 5) 解码 true/pred cracks
true_cracks = [{"pos": float(p), "depth": float(d)} for p, d in CRACK_LIST]
true_cracks.sort(key=lambda c: c["pos"])
BRIDGE_L = float(PARAMS.get("L", 30.0))
pred_raw = []
for j in range(max_cracks):
    if probs[0, j] > CLS_THRESHOLD and reg_raw[0, j*2+1] > 0:
        _pos = float(reg_raw[0, j*2])
        _dep = float(reg_raw[0, j*2+1])
        # 物理合理性过滤：裂缝位置必须在梁上 [0, L]；
        # 超训练分布的输入（如 depth=0.8>0.3）会导致 logits 爆炸、解出 pos 数百米，
        # 画布/坐标轴无法承载，直接丢弃（note 已说明输入超分布风险）
        if 0.0 <= _pos <= BRIDGE_L:
            pred_raw.append({
                "pos": _pos,
                "depth": _dep,
                "conf": float(probs[0, j]),
            })
pred_raw.sort(key=lambda c: c["pos"])

# 6) greedy_match（同 export_dashboard_data.py）
def greedy_match(true_cracks, pred_cracks):
    matched = []
    used_p = set()
    for ti, t in enumerate(true_cracks):
        best = None
        for pi, p in enumerate(pred_cracks):
            if pi in used_p:
                continue
            d = abs(t["pos"] - p["pos"])
            if d <= MATCH_COST and (best is None or d < best[0]):
                best = (d, pi)
        if best:
            matched.append((ti, best[1]))
            used_p.add(best[1])
    unmatched_t = [i for i in range(len(true_cracks)) if i not in {m[0] for m in matched}]
    unmatched_p = [i for i in range(len(pred_cracks)) if i not in {m[1] for m in matched}]
    return matched, unmatched_t, unmatched_p

matched, unm_t, unm_p = greedy_match(true_cracks, pred_raw)
pred_cracks = []
for pi, p in enumerate(pred_raw):
    p2 = dict(p)
    p2["match"] = next((ti for ti, mpi in matched if mpi == pi), None)
    p2["hit"] = p2["match"] is not None
    pred_cracks.append(p2)

out = {
    "signal_len": int(len(cpdv_raw)),
    "max_abs_x": float(np.abs(x).max()),
    "true_cracks": true_cracks,
    "pred_cracks": pred_cracks,
    "n_true": len(true_cracks),
    "n_pred": len(pred_raw),
    "n_hit": len(matched),
    "n_miss": len(unm_t),
    "n_false": len(unm_p),
    "cls_logits": [float(v) for v in cls_logits[0].numpy()],
    # 多裂缝组合 CPDV 信号（推理实际使用的输入，去 padding 0，看板 ② 区单曲线展示，
    # 语义与模型输入一致 —— 而非 cpdv_signals 的逐位置单裂缝探针）
    "combined_cpdv": [float(v) for v in cpdv_raw[:MAX_LEN]],
}
print("PRED_CRACKS: " + json.dumps(out, ensure_ascii=False))
'''


def _resolve_bridge(bridge_id: str):
    """按 id/名称找注册桥，找不到抛 ValueError。"""
    from data_loader import load_registry
    reg = load_registry()
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            return b
    raise ValueError(f"桥梁 '{bridge_id}' 未注册，请先用「注册桥梁」命令注册")


def _read_crack_list(bridge: dict, default_depth: float = 0.2) -> list:
    """从注册桥 cpdv_signals 提取 [(pos, depth), ...]。

    支持两种数据来源：
    1. registry 中直接存储的 cpdv_signals（旧格式）
    2. signal_files 指向的独立 JSON 文件（新格式）
    """
    # 先尝试从 registry 直接读取
    signals = bridge.get("cpdv_signals") or []
    
    # 如果 registry 中没有，尝试从 signal_files 加载
    if not signals:
        from data_loader import load_bridge_signals
        sf = bridge.get("signal_files") or {}
        if sf.get("has_signals"):
            sig_data = load_bridge_signals(bridge["id"])
            if sig_data:
                signals = sig_data.get("cpdv_signals") or []
    
    if not signals:
        raise ValueError("该桥尚未计算 CPDV（registry 无 cpdv_signals），请先运行「计算CPDV」")
    params = bridge.get("params") or {}
    fallback = params.get("depth", default_depth)
    cracks = []
    for s in signals:
        try:
            pos = float(s["pos"])
        except (KeyError, TypeError, ValueError):
            continue
        dep = float(s.get("depth", fallback))
        cracks.append([pos, dep])
    if not cracks:
        raise ValueError("cpdv_signals 中没有有效的位置字段（pos）")
    return cracks


def _merge_params(bridge: dict) -> dict:
    """DEFAULT_SIM < 注册桥 params，构造仿真参数。"""
    from services.cpdv_service import DEFAULT_SIM
    return {**DEFAULT_SIM, **(bridge.get("params") or {})}


def _predict_bridge(model: str, bridge_id: str, cls_threshold: float, match_cost: float):
    """单桥推理：读注册桥 → 组合信号 → 推理 → 解码 → 写回 registry。"""
    bridge = _resolve_bridge(bridge_id)
    params = _merge_params(bridge)
    crack_list = _read_crack_list(bridge)

    sig_file = (bridge.get("signal_files") or {}).get("combined_cpdv") or ""
    code = _INFER_INLINE_CODE \
        .replace("@MODEL_PATH@", json.dumps(model)) \
        .replace("@SIGNAL_FILE@", json.dumps(sig_file)) \
        .replace("@PARAMS@", json.dumps(params, ensure_ascii=False)) \
        .replace("@CRACK_LIST@", json.dumps(crack_list)) \
        .replace("@CLS_THRESHOLD@", repr(float(cls_threshold))) \
        .replace("@MATCH_COST@", repr(float(match_cost))) \
        .replace("@MAX_LEN@", str(int(MAX_CPDV_LENGTH)))

    out = run(["-c", code], cmd="multi_crack")
    m = _RE_PRED.search(out)
    if not m:
        raise RuntimeError("内联推理未输出 PRED_CRACKS 结果行")
    prediction = json.loads(m.group(1))

    # 稳健性备注：信号严重超出训练分布时（标准化 max|x| 巨大），预测不可靠
    note = None
    max_abs = prediction.get("max_abs_x", 0.0)
    if max_abs > 50:
        note = ("输入信号大幅超出训练分布（标准化 max|x|=%.1f），可能原因：裂缝深度超训练范围 "
                "[0.05, 0.3]；预测结果仅供参考。" % max_abs)

    # 写回 registry（true/pred_cracks + n_* 统计）
    from data_loader import save_bridge_multi_crack_result
    save_bridge_multi_crack_result(bridge_id, prediction)

    return {
        "bridge_id": bridge_id,
        "model": model,
        "input_data": None,
        "stdout": out,
        "parsed": _parse(out),
        "prediction": prediction,
        "written_back": True,
        "note": note,
    }


def predict_multi_crack(model: str = DEFAULT_MODEL, input_data: str = DEFAULT_INPUT,
                        bridge_id: str = None, cls_threshold: float = CLS_THRESHOLD,
                        match_cost: float = MATCH_COST):
    """流程 C3：多裂缝推理。默认 multi_crack_dual_retrained.pth。

    - bridge_id 为空：保持原行为 —— 跑 05_infer 评估测试集，返回 stdout/parsed。
    - bridge_id 指定（方案A）：读注册桥 → 组合信号单样本推理 → 解码+匹配 → 写回 registry。
    """
    model = resolve_model(model, "multi_crack")
    if bridge_id:
        return _predict_bridge(model, bridge_id, cls_threshold, match_cost)

    argv = [
        "scripts/05_infer_multi_crack.py",
        "--model", model,
        "--input", input_data,
    ]
    out = run(argv, cmd="multi_crack")
    return {
        "stdout": out,
        "model": model,
        "input_data": input_data,
        "parsed": _parse(out),  # G11
    }
