import json
import re
from pathlib import Path
from executor import run, run_with_config, verify_import


# simulation 段默认值（与 executor.write_tmp_yaml 默认值保持一致）
DEFAULT_SIM = {
    "mv": 5000, "kv": 100000, "cv": 5000, "V": 2, "L": 30,
    "E": 3.0e10, "I": 0.1, "m": 400, "EL": 30, "depth": 0.8,
    "width": 0.25, "n_modes": 3, "kexi": 0.1, "deltat": 0.005,
    "road_type": "b", "gamma": 0.5, "beta": 0.25,
}


def _resolve_bridge_params(bridge_id: str):
    """从 registry.json 读桥梁参数，找不到则抛 ValueError。"""
    from data_loader import load_registry
    reg = load_registry()
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            return b.get("params") or {}
    raise ValueError(f"桥梁 '{bridge_id}' 未注册，请先用「注册桥梁」命令注册")


# G11：从 stdout 抓关键指标。04_cpdv_analysis.py 的可识别行：
#   "pos=X, depth=Y, peak=Z.XXXXXX"
#   "signal_depth: X" / "positions: [...]"
#   "图表已保存至: <path>"
_RE_DATA = re.compile(r"pos\s*=\s*([+-]?\d+(?:\.\d+)?)\s*,\s*depth\s*=\s*([+-]?\d+(?:\.\d+)?)\s*,\s*peak\s*=\s*([+-]?\d+(?:\.\d+)?)")
_RE_DEPTH = re.compile(r"signal_depth:\s*([+-]?\d+(?:\.\d+)?)")
_RE_OUTPUT = re.compile(r"图表已保存至:\s*(.+)")
# G19：内联计算打印的一行完整序列 JSON（每位置一条 signal 数组）
_RE_TS = re.compile(r"^CPDV_TS:\s*(\{.*\})", re.M)


def _parse_cpdv_stdout(stdout: str) -> dict:
    """从 cpdv pipeline stdout 提取结构化字段。
    返回 dict 永远存在（即便内容为空），便于前端稳定访问 parsed.* 字段。
    - rows:        pos/depth/peak 峰值行（兼容 peak 模式 stdout）
    - time_series: { positions: [...], signal: {pos: [数组]}, peak: {pos: float} }
    """
    rows = []
    for m in _RE_DATA.finditer(stdout):
        rows.append({"pos": float(m.group(1)), "depth": float(m.group(2)), "peak": float(m.group(3))})
    depth_m = _RE_DEPTH.search(stdout)
    output_m = _RE_OUTPUT.search(stdout)
    ts_m = _RE_TS.search(stdout)
    time_series = None
    if ts_m:
        try:
            time_series = json.loads(ts_m.group(1))
        except json.JSONDecodeError:
            time_series = None
    return {
        "rows": rows,
        "time_series": time_series,
        "signal_depth": float(depth_m.group(1)) if depth_m else None,
        "output_path": output_m.group(1).strip() if output_m else None,
        "row_count": len(rows),
    }


# G19/G20：内联计算完整时间序列的 Python 片段。零改 pipeline 脚本（04_cpdv_analysis.py 已 git restore 至 HEAD），
# 复刻 04_cpdv_analysis.py::plot_cpdv_signals 的值计算逻辑（analyze_damage→calculate_cpdv），
# 只打印 CPDV_TS 一行 + 峰值行（供 _RE_DATA 解析），不画图。
# G20：@DEPTHS@ 为与 distances 一一对应的深度数组（多裂缝模式），
# 每个位置用各自深度计算；单深度模式由 compute_cpdv 填充为 [depth]*N，行为与 G19 一致。
_TS_INLINE_CODE = r'''
import json, sys
sys.path.insert(0, ".")
from simulation.system_iteration import BridgeVehicleSystem
distances = [float(x) for x in "@DISTANCES@".split(",")]
depths = @DEPTHS@  # list[float]，与 distances 一一对应
params = @SIM_PARAMS@
system = BridgeVehicleSystem(params=params)
if system.uc_healthy is None:
    system.run_analysis()
ts = {}
peaks = {}
for i, pos in enumerate(distances):
    dep = depths[i]
    res = system.analyze_damage(pos, dep)
    cpdv = system.calculate_cpdv(res["uc"])
    ts[str(pos)] = [float(v) for v in cpdv]
    peaks[str(pos)] = float(max(abs(float(v)) for v in cpdv))
# G21: 多裂缝组合模式 - 生成组合信号
if len(depths) > 1:
    combined = None
    for i, pos in enumerate(distances):
        dep = depths[i]
        res = system.analyze_damage(pos, dep)
        cpdv = system.calculate_cpdv(res["uc"])
        cpdv_list = [float(v) for v in cpdv]
        if combined is None:
            combined = cpdv_list
        else:
            combined = [a + b for a, b in zip(combined, cpdv_list)]
    result = {"positions": distances, "depths": depths, "signal": ts, "peak": peaks, "combined_signal": combined}
else:
    result = {"positions": distances, "depths": depths, "signal": ts, "peak": peaks}
print("CPDV_TS: " + json.dumps(result))
for i, pos in enumerate(distances):
    print("pos=%s, depth=%s, peak=%.6f" % (pos, depths[i], peaks[str(pos)]))
'''


def _compute_cpdv_via_pipeline(bridge_id: str, depth: float, distances: list,
                                sim_overrides: dict, eff_depths: list) -> dict:
    """G3: 使用 pipeline 脚本 + YAML 注入计算 CPDV（峰值模式）。
    通过 executor.run_with_config 自动生成临时 yaml 并注入 --config。
    返回与 _parse_cpdv_stdout 兼容的结果结构。
    """
    # 构建 pipeline 脚本参数
    argv = [
        "scripts/04_cpdv_analysis.py",
        "--mode", "peak",  # 峰值模式：仅输出 pos/depth/peak 行
        "--distances", ",".join(str(float(x)) for x in distances),
    ]
    # 多裂缝模式：传递 depths（与 distances 一一对应）
    if len(eff_depths) > 1 or (len(eff_depths) == 1 and abs(eff_depths[0] - depth) > 1e-9):
        argv += ["--depths", ",".join(str(float(d)) for d in eff_depths)]
    else:
        argv += ["--depth", str(depth)]

    # 使用 run_with_config 自动注入 simulation 段 yaml（含 mv/kv/cv 等参数）
    out = run_with_config(argv, sim_overrides=sim_overrides, timeout=config.DEFAULT_TIMEOUT, cmd="cpdv")
    return out


def _compute_cpdv_time_series_inline(bridge_id: str, distances: list,
                                      eff_depths: list, sim_overrides: dict) -> dict:
    """G19/G20: 内联计算完整时间序列（复用原有逻辑），用于看板多曲线渲染。"""
    code = _TS_INLINE_CODE \
        .replace("@DISTANCES@", ",".join(str(float(x)) for x in distances)) \
        .replace("@DEPTHS@", json.dumps(eff_depths)) \
        .replace("@SIM_PARAMS@", json.dumps(sim_overrides))

    out = run(["-c", code], cmd="cpdv")
    return _parse_cpdv_stdout(out)


def compute_cpdv(bridge_id: str, depth: float, distances: list,
                 params: dict, output_dir: Path, depths: list = None):
    """流程 C1：计算 CPDV（峰值 + 完整时间序列）。
    bridge_id 既接受 id（如 bridge_01）也接受 name（如 桥梁01）。
    优先级（后写覆盖前写）：DEFAULT_SIM < registry 中桥参数 < 本次 params 覆盖。
    G3: 使用 pipeline 脚本 + YAML 注入计算峰值（mv/kv/cv 等参数生效）。
    G19/G20: 内联计算完整时间序列，持久化到 registry 供看板渲染。
    """
    verify_import(cmd="cpdv")
    bridge_params = _resolve_bridge_params(bridge_id)
    sim_overrides = {**DEFAULT_SIM, **bridge_params, **params}

    eff_depths = [float(d) for d in (depths or [depth] * len(distances))]
    if len(eff_depths) != len(distances):
        raise ValueError(f"depths({len(eff_depths)}) 数量必须与 distances({len(distances)}) 一致")

    # G3: 优先使用 pipeline 脚本 + YAML 注入（mv/kv/cv 等参数通过 yaml 生效）
    try:
        pipeline_stdout = _compute_cpdv_via_pipeline(bridge_id, depth, distances, sim_overrides, eff_depths)
        parsed = _parse_cpdv_stdout(pipeline_stdout)
        used_pipeline = True
    except Exception as e:
        # 回退到内联计算（兼容旧行为）
        parsed = _compute_cpdv_time_series_inline(bridge_id, distances, eff_depths, sim_overrides)
        pipeline_stdout = f"[fallback to inline] {parsed.get('stdout', '')}"
        used_pipeline = False

    if parsed["signal_depth"] is None:
        parsed["signal_depth"] = eff_depths[0]

    # G19/G20: 计算成功 → 持久化完整时间序列到 registry，供「刷新看板」多曲线渲染。
    # 如果 pipeline 成功但没有 time_series，尝试内联补全
    ts = parsed.get("time_series")
    if not (ts and ts.get("signal")):
        # 无 time_series 时，内联补全
        inline_parsed = _compute_cpdv_time_series_inline(bridge_id, distances, eff_depths, sim_overrides)
        ts = inline_parsed.get("time_series")

    if ts and ts.get("signal"):
        ts_depths = ts.get("depths") or eff_depths
        signals = []
        for i, p in enumerate(ts.get("positions", [])):
            key = str(p)
            if key in ts.get("signal", {}):
                signals.append({
                    "pos": float(p),
                    "depth": float(ts_depths[i]) if i < len(ts_depths) else eff_depths[0],
                    "signal": ts["signal"][key],
                })
        from data_loader import save_bridge_cpdv_signals, save_bridge_combined_cpdv
        save_bridge_cpdv_signals(bridge_id, signals)
        # G21: 保存组合信号（多裂缝模式）
        if ts and ts.get("combined_signal"):
            save_bridge_combined_cpdv(bridge_id, ts["combined_signal"])

    return {
        "stdout": pipeline_stdout,
        "bridge_id": bridge_id,
        "depth": eff_depths[0],
        "depths": eff_depths,
        "distances": distances,
        "applied_overrides": {k: sim_overrides[k] for k in params.keys() if k in sim_overrides},
        "parsed": parsed,  # G11: 结构化字段
        "used_pipeline": used_pipeline,
    }
