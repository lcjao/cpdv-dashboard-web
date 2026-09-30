"""config.py — 环境变量覆盖版（G12）。

所有路径与环境变量都可被同名 os.environ 覆盖，避免换机必改源码。
不依赖 python-dotenv：直接读 os.environ，运维友好。
"""
import os
from pathlib import Path


def _env_str(key: str, default: str) -> str:
    """读环境变量；空字符串或 None 都视为未设置。"""
    v = os.environ.get(key)
    if v is None or str(v).strip() == "":
        return default
    return str(v)


def _candidate_path(*paths: str) -> Path:
    """返回第一个存在的候选路径，否则返回首个候选。"""
    for value in paths:
        candidate = Path(value).expanduser()
        if candidate.exists():
            return candidate.resolve()
    return Path(paths[0]).expanduser().resolve()


# bridge_crack_id 权威代码库（原始 pipeline 脚本目录，后端 subprocess 实际执行）
# ⚠️ 必须指向仓库根（含 simulation/ 包与 scripts/ 子目录），executor 的 cmd_args
#    以 "scripts/xxx.py" 相对路径调用；指向 github\scripts 会导致
#    ModuleNotFoundError: No module named 'simulation'（2026-09-07 修复）。
CODE_ROOT = _candidate_path(
    _env_str("CPDV_CODE_ROOT", r"D:\研\土木水利\论文\代码\github"),
    r"D:\研\土木水利\论文\代码\github",
)
# 整理后的纯算法代码库（去脚本化、可 import、供前端浏览/算法复用）
# 若环境变量未配置，优先选择项目内统一算法库；如果不存在，退回到 CODE_ROOT/simulation。
ALGORITHM_CODE_ROOT = _candidate_path(
    _env_str("CPDV_ALGORITHM_CODE_ROOT", r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\algorithm-code"),
    r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\algorithm-code",
    str(CODE_ROOT / "simulation"),
    str(CODE_ROOT / "data_pipeline"),
    str(CODE_ROOT),
)

# 保护：两套根目录不能指向同一位置；否则前端切换会出现“两个路径却看起来一样”的 bug。
try:
    if CODE_ROOT.resolve() == ALGORITHM_CODE_ROOT.resolve():
        fallback = CODE_ROOT / "simulation"
        if fallback.exists():
            ALGORITHM_CODE_ROOT = fallback.resolve()
        elif (CODE_ROOT / "data_pipeline").exists():
            ALGORITHM_CODE_ROOT = (CODE_ROOT / "data_pipeline").resolve()
except Exception:
    pass


# ---- 执行命令 -> algorithm-code 子目录（自包含可运行根）映射 ----
# 旧 CODE_ROOT(github) 已废弃。每个 pipeline 子目录已补全为可独立运行（simulation/model/
# visualization 齐全），legacy 命令与其内联 -c 推理代码按命令定位到对应子目录作 cwd。
PIPELINE_CWD = {
    "cpdv": "pipeline-1-cpdv-simulation",
    "random": "pipeline-1-cpdv-simulation",
    "predict": "pipeline-2-single-crack-bp",
    "train": "pipeline-4-multi-crack",
    "evaluate": "pipeline-4-multi-crack",
    "multi_crack": "pipeline-4-multi-crack",
    "pinn": "pipeline-5-pinn",
    "dashboard": "pipeline-6-cpdv-analysis",
}


def pipeline_cwd(cmd: str) -> Path:
    """命令对应的可运行根目录（algorithm-code 下的 pipeline 子目录）。"""
    rel = PIPELINE_CWD.get(cmd, PIPELINE_CWD["cpdv"])
    p = ALGORITHM_CODE_ROOT / rel
    return p if p.exists() else ALGORITHM_CODE_ROOT


def sanitize_path(s: str) -> str:
    """修复 LLM 工具调用参数里被 JSON 转义破坏的 Windows 路径（工具链兜底）。

    LLM 写 JSON 时若把路径的反斜杠写少一层，JSON 解析器会把"反斜杠+b"这类
    片段当成退格符转义（0x08）；偶尔还会残留双反斜杠。这里：退格符还原为
    反斜杠+b、折叠连续双反斜杠；正常路径原样返回。"""
    BS = chr(92)
    s = (s or "").replace(chr(8), BS + "b")
    while BS + BS in s:
        s = s.replace(BS + BS, BS)
    return s


# 输出/模型/图表根目录（脚本内相对 outputs/ 解析到各 pipeline 子目录；此处默认指向
# 看板导出目录，前端 chart_path 用）。可被 CPDV_OUTPUTS_DIR 覆盖。
OUTPUTS_DIR = Path(_env_str(
    "CPDV_OUTPUTS_DIR",
    str(ALGORITHM_CODE_ROOT / "pipeline-6-cpdv-analysis" / "outputs"),
))


# 临时 yaml 注入目录（executor.run_with_config 用，绝对路径，任意 cwd 均可解析）。
# 放到后端数据目录下（纯 ASCII 路径），避免中文仓库路径影响。
TMP_CONFIG_DIR = Path(_env_str(
    "CPDV_TMP_CONFIG_DIR",
    str(Path(__file__).parent / "data" / "tmp_configs"),
))
# Python 解释器（cpdv venv，numpy<2 + torch 1.13+cpu，环境隔离）
PYTHON_EXE = _env_str(
    "CPDV_PYTHON_EXE",
    r"D:\python\cpdv-venv\Scripts\python.exe",
)
# 看板工作区（registry / 各桥 JSON / 看板原型数据）
DASHBOARD_WORKSPACE = Path(_env_str(
    "CPDV_DASHBOARD_WORKSPACE",
    r"D:\Documents\Obsidian\O1\桥梁健康系统\Area\多桥梁损伤看板",
))
# 本后端数据目录
DATA_DIR = Path(_env_str(
    "CPDV_DATA_DIR",
    str(Path(__file__).parent / "data"),
))

# 子进程默认超时（G10，单位秒）；可被 CPDV_DEFAULT_TIMEOUT 覆盖
DEFAULT_TIMEOUT = int(_env_str("CPDV_DEFAULT_TIMEOUT", "300"))

# 命令映射（与 SKILL.md 一致）—— 简短版（向后兼容旧调用）
COMMANDS = {
    "看板总览": "overview", "注册桥梁": "register", "列出桥梁": "list",
    "计算CPDV": "cpdv", "预测损伤": "predict", "多裂缝预测": "multi_crack",
    "随机工况分析": "random_condition", "对比": "compare",
    "训练模型": "train", "训练并评估": "train_and_evaluate", "评估模型": "evaluate", "刷新看板": "refresh", "记录实验": "record",
    "执行Pipeline": "pipeline.execute",
}

# G9: 命令单一来源 —— 11 条命令的全 schema 配置。
# 这是前端三处（cpdv-tools.ts / api-client.ts TOOL_ROUTE / QuickCommands.tsx）的
# 唯一真相源。新增/修改命令只需改这里即可。
#
# 字段说明：
#   action:      命令 ID（与 COMMANDS 值同步）
#   name:        命令中文名（与 COMMANDS 键同步）
#   description: 一句话描述（给 LLM 看的 tool description）
#   category:    view / analysis / model / utility 四类之一
#   quick:       是否在 ChatPanel QuickCommands 显示（True 的 6 条）
#   llm_tool:    True 时注册为 OpenAI function-calling 工具
#   phases:      short(<10s) / medium(10-60s) / long(>60s)，前端用来提示耗时
#   inputs:      命令接受的参数名（bridge/depth/...），对应 LLM tool.parameters
#   inputs_desc: 每个参数的中文描述（用于 tool.parameters.properties）
#   route:       后端路由描述 { method, path, map }
#                map 函数可选：把 LLM args 转成后端 query/body
#   output_keys: 命令返回结构里的关键字段（前端从 result 里读取的提示）
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
        "description": "注册一座新桥梁，可指定初始参数（单位：km/h→m/s、kN→N、GPa→Pa、t→kg、mm→m）",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": ["name"],
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
        "description": "计算桥梁 CPDV 信号。两种模式：(1) 多组单裂缝：传 distances 和 depth（单一深度作用于所有位置），每个位置产生独立信号；(2) 多裂缝组合：传 distances 和 depths（一一对应），所有裂缝同时存在于同一信号中。可选覆盖仿真参数：mv/kv/cv/V/L/E/I/m/EL/width/n_modes/kexi/deltat/road_type",
        "category": "analysis",
        "quick": False,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": ["bridge", "depth", "distances", "depths", "mv", "kv", "cv", "V", "L", "E", "I", "m", "EL", "width", "n_modes", "kexi", "deltat", "road_type"],
        "required_inputs": ["bridge", "distances"],
        "inputs_desc": {
            "bridge": "桥梁名或 id",
            "depth": "单裂缝深度(m)。用于模式1：所有位置共用此深度；模式2时忽略（用depths）",
            "distances": "扰动位置列表(m)，逗号分隔，如 '5,10,15'",
            "depths": "多裂缝组合模式：与 distances 一一对应的深度列表，逗号分隔，如 '0.2,0.3,0.25'。传此参数时启用组合模式，所有裂缝同时作用于同一信号；不传则为多组单裂缝模式，每位置独立计算",
            "mv": "车辆质量(kg)，默认 5000",
            "kv": "车辆悬挂刚度(N/m)，默认 100000",
            "cv": "车辆悬挂阻尼(N·s/m)，默认 5000",
            "V": "车速(m/s)，默认 2",
            "L": "跨长(m)，默认 30",
            "E": "弹性模量(Pa)，默认 3e10",
            "I": "惯性矩(m^4)，默认 0.1",
            "m": "单位长度质量(kg/m)，默认 400",
            "EL": "等效跨长(m)，默认 30",
            "width": "裂缝宽度(m)，默认 0.25",
            "n_modes": "模态数，默认 3",
            "kexi": "荷载分布系数，默认 0.1",
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
        "description": "单裂缝损伤预测（流程C2），默认 cracknet_aligned.json + training_data.npz（维度已对齐）",
        "category": "model",
        "quick": True,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": ["model", "input_data"],
        "inputs_desc": {
            "model": "模型路径，默认 cracknet_aligned.json（与 training_data.npz 的 3001 维特征对齐）",
            "input_data": "输入数据路径，默认 outputs/data/training_data.npz（自带验证集，维度与模型一致）",
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
        "inputs": ["bridge", "model", "input_data"],
        "inputs_desc": {
            "bridge": "注册桥 id/名称（如 bridge_01）；指定后预测该桥并将结果写回看板（true/pred_cracks）",
            "model": "模型文件名，默认 multi_crack_dual_retrained.pth；只传文件名或省略即可（勿传 Windows 绝对路径，JSON 转义会破坏路径反斜杠）",
            "input_data": "输入数据路径，默认 outputs/data/multi_condition.npz",
        },
        "route": {
            "method": "GET", "path": "/analysis/multi-crack",
            "map": "lambda a: {'bridge': a.get('bridge'), 'model': a.get('model'), 'input_data': a.get('input_data')}",
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
        "description": "对比两座桥梁的损伤预测质量（仅在两桥都已注册且有训练结果时生效）",
        "category": "view",
        "quick": True,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": ["a", "b"],
        "inputs_desc": {"a": "桥梁A 名或 id", "b": "桥梁B 名或 id"},
        "route": {
            "method": "POST", "path": "/command",
            "map": "lambda a: {'text': '对比', 'params': {'a': a.get('a'), 'b': a.get('b')}}",
        },
        "output_keys": ["summary", "diff"],
    },
    {
        "action": "train",
        "name": "训练模型",
        "description": "训练多裂缝损伤模型（流程T1，长任务约2分钟CPU）。训练前必须先向用户报告预计耗时并确认。默认产出 multi_crack_dual_retrained.pth（即看板多裂缝预测所用模型）",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["long"],
        "inputs": [],
        "inputs_desc": {
            "model_type": "模型类型，当前仅支持 multi_crack",
            "n_samples": "样本数（regenerate=true 重新生成数据时生效）",
            "epochs": "端到端微调轮数，默认100",
            "regenerate": "是否重新生成训练数据（耗时长），默认 false 复用已有数据",
        },
        "route": {"method": "POST", "path": "/analysis/train", "map": "lambda a: a"},
        "output_keys": ["stages", "metrics"],
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
        "action": "evaluate",
        "name": "评估模型",
        "description": "运行完整评估脚本（05_infer_multi_crack.py）计算所有指标：F1/Recall/Precision/位置MAE/深度MAE/匹配数等，并写回 registry meta",
        "category": "model",
        "quick": True,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": [],
        "inputs_desc": {
            "model": "模型文件名，默认 multi_crack_dual_retrained.pth；只传文件名或省略即可（勿传 Windows 绝对路径，JSON 转义会破坏路径反斜杠）",
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
        "description": "一条龙：先训练模型（multi_crack），训练完成后自动运行完整评估，得到全部 7 项指标（F1/Recall/Precision/位置MAE/深度MAE/匹配数/n_gt/n_pred）并写回 registry meta。长任务，预计耗时 = 训练耗时 + 评估耗时。",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["long"],
        "inputs": [],
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
        "route": {"method": "POST", "path": "/command", "map": "lambda a: {'text': '训练并评估', 'params': a}"},
        "output_keys": ["train_result", "eval_result", "meta_written"],
    },
    {
        "action": "record",
        "name": "记录实验",
        "description": "把当前实验的参数和结果写入 records.jsonl，方便后续对比和回溯。支持自动记录训练/评估/预测/对比/Pipeline运行等类型的实验。",
        "category": "utility",
        "quick": False,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": [],
        "inputs_desc": {
            "note": "备注（中文支持）",
            "type": "实验类型: train/evaluate/predict/compare/multi_crack_train/pipeline_run",
            "protocol": "关联的协议名称",
            "bridge": "关联的桥梁 id",
            "params": "实验参数(JSON)",
            "metrics": "实验指标(JSON)",
        },
        "route": {"method": "POST", "path": "/command", "map": "lambda a: {'text': '记录实验', 'params': a}"},
        "output_keys": ["record_id"],
    },
    {
        "action": "record_experiment",
        "name": "记录实验(详细)",
        "description": "完整记录实验，包含类型、协议、桥梁、参数、指标、备注。用于 AI 自动记录训练/评估/对比/Pipeline运行结果。",
        "category": "utility",
        "quick": False,
        "llm_tool": True,
        "phases": ["short"],
        "inputs": [],
        "inputs_desc": {
            "note": "备注说明",
            "type": "实验类型: train | evaluate | predict | compare | multi_crack_train | pipeline_run",
            "protocol": "关联协议名",
            "bridge": "关联桥梁 id",
            "params": "参数配置(JSON对象)",
            "metrics": "指标结果(JSON对象)",
        },
        "route": {"method": "POST", "path": "/api/algorithm/record", "map": "lambda a: a"},
        "output_keys": ["record_id", "message"],
    },
    {
        "action": "pipeline.execute",
        "name": "执行Pipeline",
        "description": "执行选定的Pipeline（数据生成/模型训练/推理/分析），可指定模式(quick/full)和阶段。结果自动记录到实验文档。",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["long"],
        "inputs": ["pipelines", "mode", "stages"],
        "inputs_desc": {
            "pipelines": "要执行的pipeline ID列表，如 pipeline_2_single_crack_bp",
            "mode": "执行模式: quick(快速)或full(完整)",
            "stages": "可选，指定要执行的阶段ID列表",
            "record_experiment": "是否在完成后自动创建实验记录文档（默认true）",
        },
        "route": {"method": "POST", "path": "/command", "map": "lambda a: {'text': '执行Pipeline', 'params': a}"},
        "output_keys": ["task_id", "pipelines", "status"],
    },
    {
        "action": "compare_models",
        "name": "对比模型",
        "description": "对比两个模型的指标与配置差异，返回胜出模型及详细差异表。支持指定桥梁关联的模型路径。",
        "category": "model",
        "quick": False,
        "llm_tool": True,
        "phases": ["medium"],
        "inputs": [],
        "inputs_desc": {
            "model_a": "模型A路径",
            "model_b": "模型B路径",
            "bridge_a": "模型A关联桥梁(可选)",
            "bridge_b": "模型B关联桥梁(可选)",
        },
        "route": {"method": "POST", "path": "/api/algorithm/compare-models", "map": "lambda a: a"},
        "output_keys": ["comparison", "winner", "summary"],
    },
]


def get_command_meta() -> list:
    """对外暴露命令元数据列表（前端 /api/command-meta 调用）。"""
    return COMMAND_META
