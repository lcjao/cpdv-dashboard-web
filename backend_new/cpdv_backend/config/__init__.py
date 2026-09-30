"""
Configuration module for CPDV Backend.

All settings are loaded from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from typing import Optional


def _env_str(key: str, default: str) -> str:
    """Read environment variable; empty string or None treated as unset."""
    v = os.environ.get(key)
    if v is None or str(v).strip() == "":
        return default
    return str(v)


def _env_int(key: str, default: int) -> int:
    """Read environment variable as integer."""
    v = os.environ.get(key)
    if v is None or str(v).strip() == "":
        return default
    return int(v)


def _env_float(key: str, default: float) -> float:
    """Read environment variable as float."""
    v = os.environ.get(key)
    if v is None or str(v).strip() == "":
        return default
    return float(v)


def _env_bool(key: str, default: bool) -> bool:
    """Read environment variable as boolean."""
    v = os.environ.get(key)
    if v is None or str(v).strip() == "":
        return default
    return str(v).lower() in ("1", "true", "yes", "on")


def _candidate_path(*paths: str) -> Path:
    """Return the first existing candidate path, or the first candidate if none exist."""
    for value in paths:
        candidate = Path(value).expanduser()
        if candidate.exists():
            return candidate.resolve()
    return Path(paths[0]).expanduser().resolve()


# =============================================================================
# Core Paths
# =============================================================================

# Original pipeline scripts repository (authoritative source for subprocess execution)
CODE_ROOT = _candidate_path(
    _env_str("CPDV_CODE_ROOT", r"D:\研\土木水利\论文\代码\github"),
    r"D:\研\土木水利\论文\代码\github",
)

# Cleaned algorithm library (importable, for frontend browsing and algorithm reuse)
ALGORITHM_CODE_ROOT = _candidate_path(
    _env_str("CPDV_ALGORITHM_CODE_ROOT", str(CODE_ROOT / "simulation")),
    str(CODE_ROOT / "simulation"),
    str(CODE_ROOT / "data_pipeline"),
    str(CODE_ROOT),
)

# Python interpreter (cpdv venv with numpy<2 + torch 1.13+cpu)
PYTHON_EXE = _env_str(
    "CPDV_PYTHON_EXE",
    r"D:\python\cpdv-venv\Scripts\python.exe",
)

# Dashboard workspace (registry, bridge JSON, dashboard prototype data)
DASHBOARD_WORKSPACE = Path(_env_str(
    "CPDV_DASHBOARD_WORKSPACE",
    r"D:\Documents\Obsidian\O1\桥梁健康系统\Area\多桥梁损伤看板",
))

# Backend data directory
DATA_DIR = Path(_env_str(
    "CPDV_DATA_DIR",
    str(Path(__file__).parent.parent.parent / "data"),
))

# Subprocess default timeout (seconds)
DEFAULT_TIMEOUT = _env_int("CPDV_DEFAULT_TIMEOUT", 300)

# CORS allowed origins
ALLOW_ORIGINS = _env_str(
    "CPDV_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
).split(",")

# =============================================================================
# Dashboard Thresholds (G13)
# =============================================================================

DEFAULT_THRESHOLDS = {
    "pos_mae_max": 1.0,      # m
    "depth_mae_max": 0.05,   # 5%
    "f1_min": 0.87,
    "recall_min": 0.80,
    "precision_min": 0.80,
}


def get_thresholds() -> dict:
    """Get dashboard thresholds, with env override."""
    raw = os.environ.get("CPDV_THRESHOLDS_JSON", "").strip()
    if not raw:
        return dict(DEFAULT_THRESHOLDS)
    try:
        import json
        override = json.loads(raw)
        return {**DEFAULT_THRESHOLDS, **override}
    except json.JSONDecodeError:
        return dict(DEFAULT_THRESHOLDS)


# =============================================================================
# Default Simulation Parameters
# =============================================================================

DEFAULT_SIM_PARAMS = {
    # Vehicle parameters (1/4 car model)
    "mv": 5000.0,      # Vehicle mass (kg)
    "kv": 100000.0,    # Suspension stiffness (N/m)
    "cv": 5000.0,      # Suspension damping (N/(m/s))
    "k_a": 170000.0,   # Axle stiffness (N/m)
    "V": 2.0,          # Vehicle speed (m/s)

    # Bridge parameters
    "L": 30.0,         # Bridge length (m)
    "E": 3.0e10,       # Elastic modulus (Pa)
    "I": 0.1,          # Moment of inertia (m^4)
    "m": 400.0,        # Mass per unit length (kg/m)
    "EL": 30,          # Number of finite elements
    "depth": 0.8,      # Beam depth (m)
    "width": 0.25,     # Beam width (m)

    # Modal parameters
    "n_modes": 3,      # Number of modes
    "kexi": 0.1,       # Damping ratio

    # Analysis parameters
    "deltat": 0.005,   # Time step (s)
    "gamma": 0.5,      # Newmark gamma
    "beta": 0.25,      # Newmark beta

    # Road roughness
    "road_type": "b",  # ISO 8608 road class
}


# =============================================================================
# Command Metadata (G9 - Single Source of Truth)
# =============================================================================

COMMAND_META = [
    {
        "action": "overview",
        "name": "看板总览",
        "description": "读取看板 meta 数据 + 所有桥的当前状态",
        "category": "view",
        "quick": True,
        "llm_tool": False,
        "phases": ["short"],
        "inputs": [],
        "inputs_desc": {},
        "route": {"method": "GET", "path": "/dashboard"},
        "output_keys": ["meta", "bridges"],
    },
    {
        "action": "register",
        "name": "注册桥梁",
        "description": "注册一座新桥梁，可指定初始参数",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": ["name", "V", "L", "mv", "kv", "cv", "E", "I", "m"],
        "inputs_desc": {
            "name": "桥梁名称，如 桥梁01",
            "V": "车速(m/s)，或传 V_kmh(km/h)",
            "L": "跨长(m)",
            "mv": "车辆质量(kg)",
        },
        "route": {
            "method": "POST", "path": "/bridges/register",
            "map": "lambda a: {'name': a.get('name'), 'params': a}",
        },
        "output_keys": ["id", "name", "params"],
    },
    {
        "action": "list",
        "name": "列出桥梁",
        "description": "列出所有已注册桥梁及其参数和状态",
        "category": "view",
        "quick": False,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": [],
        "inputs_desc": {},
        "route": {"method": "GET", "path": "/bridges"},
        "output_keys": [],
    },
    {
        "action": "cpdv",
        "name": "计算CPDV",
        "description": "计算某桥梁的 CPDV（流程C1），需指定裂缝深度和扰动位置列表。支持多裂缝模式：depths 与 distances 一一对应。",
        "category": "analysis",
        "quick": False,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": ["bridge", "depth", "distances", "depths", "mv", "kv", "cv", "V", "L", "E", "I", "m", "EL", "width", "n_modes", "kexi", "deltat", "road_type"],
        "required_inputs": ["bridge", "distances"],
        "inputs_desc": {
            "bridge": "桥梁名或 id",
            "depth": "信号裂缝深度(m)，未传 depths 时作用于所有位置；默认 0.2",
            "distances": "扰动位置列表，逗号分隔，如 '5,10,15'",
            "depths": "多裂缝模式：与 distances 一一对应的深度列表，逗号分隔，如 '0.2,0.3,0.25'",
            "mv": "车辆质量(kg)，默认 5000",
            "kv": "车辆悬挂刚度(N/m)，默认 100000",
            "cv": "车辆悬挂阻尼(N·s/m)，默认 5000",
            "V": "车速(m/s)，默认 2",
            "L": "跨长(m)，默认 30",
            "E": "弹性模量(Pa)，默认 3e10",
            "I": "惯性矩(m^4)，默认 0.1",
            "m": "单位长度质量(kg/m)，默认 400",
            "EL": "单元数，默认 30",
            "width": "裂缝宽度(m)，默认 0.25",
            "n_modes": "模态数，默认 3",
            "kexi": "阻尼比，默认 0.1",
            "deltat": "时间步(s)，默认 0.005",
            "road_type": "路面等级(a/b/c...)，默认 b",
        },
        "route": {
            "method": "GET", "path": "/analysis/cpdv",
            "map": "lambda a: {'bridge': a.get('bridge'), 'depth': a.get('depth'), 'distances': a.get('distances'), 'depths': a.get('depths'), 'mv': a.get('mv'), 'kv': a.get('kv'), 'cv': a.get('cv'), 'V': a.get('V'), 'L': a.get('L'), 'E': a.get('E'), 'I': a.get('I'), 'm': a.get('m'), 'EL': a.get('EL'), 'width': a.get('width'), 'n_modes': a.get('n_modes'), 'kexi': a.get('kexi'), 'deltat': a.get('deltat'), 'road_type': a.get('road_type')}",
        },
        "output_keys": ["parsed", "applied_overrides"],
    },
    {
        "action": "predict",
        "name": "预测损伤",
        "description": "单裂缝损伤预测（流程C2），默认 cracknet.json",
        "category": "model",
        "quick": True,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": ["model", "input_data"],
        "inputs_desc": {
            "model": "模型路径，默认 cracknet.json",
            "input_data": "输入数据路径，默认 outputs/data/verify_data.npz",
        },
        "route": {
            "method": "GET", "path": "/analysis/predict",
            "map": "lambda a: {'model': a.get('model'), 'input_data': a.get('input_data')}",
        },
        "output_keys": ["parsed"],
    },
    {
        "action": "multi_crack",
        "name": "多裂缝预测",
        "description": "多裂缝损伤预测（流程C3），默认 multi_crack_dual_retrained.pth",
        "category": "model",
        "quick": True,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": ["bridge", "model", "input_data", "cls_threshold", "match_cost"],
        "inputs_desc": {
            "bridge": "注册桥 id/名称（如 bridge_01）；指定后预测该桥并将结果写回看板",
            "model": "模型路径，默认 multi_crack_dual_retrained.pth",
            "input_data": "输入数据路径，默认 outputs/data/multi_condition.npz",
            "cls_threshold": "分类阈值，默认 0.3",
            "match_cost": "匹配代价，默认 5.0",
        },
        "route": {
            "method": "GET", "path": "/analysis/multi-crack",
            "map": "lambda a: {'bridge': a.get('bridge'), 'model': a.get('model'), 'input_data': a.get('input_data'), 'cls_threshold': a.get('cls_threshold'), 'match_cost': a.get('match_cost')}",
        },
        "output_keys": ["parsed"],
    },
    {
        "action": "random_condition",
        "name": "随机工况分析",
        "description": "随机多工况分析（流程C4），判定车重/车速/跨长对CPDV影响大小（CV变异系数）",
        "category": "analysis",
        "quick": True,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": ["mode", "n_samples", "positions"],
        "inputs_desc": {
            "mode": "single 或 multi_pos",
            "n_samples": "采样数，默认50",
            "positions": "位置列表，逗号分隔，如 '5,10,15,20'",
        },
        "route": {
            "method": "GET", "path": "/analysis/random",
            "map": "lambda a: {'mode': a.get('mode'), 'n_samples': a.get('n_samples'), 'positions': a.get('positions')}",
        },
        "output_keys": ["parsed"],
    },
    {
        "action": "compare",
        "name": "对比",
        "description": "对比两座桥梁的损伤预测质量",
        "category": "view",
        "quick": True,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": ["a", "b"],
        "inputs_desc": {"a": "桥梁A 名或 id", "b": "桥梁B 名或 id"},
        "route": {
            "method": "POST", "path": "/command",
            "map": "lambda a: {'text': f'对比 {a.get(\"a\")} {a.get(\"b\")}', 'params': {'a': a.get('a'), 'b': a.get('b')}}",
        },
        "output_keys": ["summary", "diff"],
    },
    {
        "action": "train",
        "name": "训练模型",
        "description": "训练多裂缝损伤模型（流程T1，长任务约2分钟CPU）。默认产出 multi_crack_dual_retrained.pth",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["long"],
        "inputs": ["model_type", "n_samples", "epochs", "phase1_epochs", "phase2_epochs", "regenerate"],
        "inputs_desc": {
            "model_type": "模型类型，当前仅支持 multi_crack",
            "n_samples": "样本数（regenerate=true 重新生成数据时生效）",
            "epochs": "端到端微调轮数，默认30",
            "phase1_epochs": "阶段1轮数，默认 epochs//3",
            "phase2_epochs": "阶段2轮数，默认 epochs//3",
            "regenerate": "是否重新生成训练数据（耗时长），默认 false 复用已有数据",
        },
        "route": {"method": "POST", "path": "/analysis/train", "map": "lambda a: a"},
        "output_keys": ["stages", "metrics"],
    },
    {
        "action": "evaluate",
        "name": "评估模型",
        "description": "运行完整评估脚本计算所有指标：F1/Recall/Precision/位置MAE/深度MAE/匹配数等，并写回 registry meta",
        "category": "model",
        "quick": True,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": ["model", "input_data", "cls_threshold", "match_cost"],
        "inputs_desc": {
            "model": "模型路径，默认 multi_crack_dual_retrained.pth",
            "input_data": "评估数据路径，默认 multi_condition.npz",
            "cls_threshold": "分类阈值，默认 0.3",
            "match_cost": "匹配代价，默认 5.0",
        },
        "route": {
            "method": "GET", "path": "/analysis/evaluate",
            "map": "lambda a: {'model': a.get('model'), 'input_data': a.get('input_data'), 'cls_threshold': a.get('cls_threshold'), 'match_cost': a.get('match_cost')}",
        },
        "output_keys": ["metrics", "meta_written"],
    },
    {
        "action": "train_and_evaluate",
        "name": "训练并评估",
        "description": "一条龙：先训练模型，训练完成后自动运行完整评估，得到全部 7 项指标并写回 registry meta",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["long"],
        "inputs": ["model_type", "n_samples", "epochs", "phase1_epochs", "phase2_epochs", "regenerate", "model", "cls_threshold", "match_cost", "pos_threshold"],
        "inputs_desc": {
            "model_type": "模型类型，当前仅支持 multi_crack",
            "n_samples": "样本数（regenerate=true 重新生成数据时生效）",
            "epochs": "端到端微调轮数，默认 30",
            "phase1_epochs": "阶段1轮数，默认 epochs//3",
            "phase2_epochs": "阶段2轮数，默认 epochs//3",
            "regenerate": "是否重新生成训练数据（耗时长），默认 false 复用已有数据",
            "model": "模型输出路径，默认 outputs/models/multi_crack_dual_retrained.pth",
            "cls_threshold": "评估分类阈值，默认 0.3",
            "match_cost": "评估匹配代价，默认 5.0",
            "pos_threshold": "评估位置阈值，默认 0.0",
        },
        "route": {"method": "POST", "path": "/command", "map": "lambda a: a"},
        "output_keys": ["train_result", "eval_result", "meta_written"],
    },
    {
        "action": "refresh",
        "name": "刷新看板",
        "description": "刷新看板数据",
        "category": "view",
        "quick": True,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": [],
        "inputs_desc": {},
        "route": {"method": "GET", "path": "/dashboard"},
        "output_keys": ["meta", "bridges"],
    },
    {
        "action": "record",
        "name": "记录实验",
        "description": "把当前实验的参数和结果写入 records.jsonl，方便后续对比和回溯",
        "category": "utility",
        "quick": False,
        "llm_tool": False,
        "phases": ["short"],
        "inputs": ["note"],
        "inputs_desc": {"note": "备注（中文支持）"},
        "route": {"method": "POST", "path": "/command", "map": "lambda a: a"},
        "output_keys": ["record_id"],
    },
]


def get_command_meta() -> list:
    """Return command metadata list (for /api/command-meta endpoint)."""
    return COMMAND_META