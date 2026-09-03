from pathlib import Path

# bridge_crack_id 权威代码库（用户验证过）
CODE_ROOT = Path(r"D:\研\土木水利\论文\代码\github")
# Python 解释器
PYTHON_EXE = r"D:\python\Python310\python.exe"
# 看板工作区（registry / 各桥 JSON / 看板原型数据）
DASHBOARD_WORKSPACE = Path(r"D:\Documents\Obsidian\O1\桥梁健康系统\Area\多桥梁损伤看板")
# 本后端数据目录
DATA_DIR = Path(__file__).parent / "data"

# 命令映射（与 SKILL.md 一致）
COMMANDS = {
    "看板总览": "overview", "注册桥梁": "register", "列出桥梁": "list",
    "计算CPDV": "cpdv", "预测损伤": "predict", "多裂缝预测": "multi_crack",
    "随机工况分析": "random_condition", "对比": "compare",
    "训练模型": "train", "刷新看板": "refresh", "记录实验": "record",
}
