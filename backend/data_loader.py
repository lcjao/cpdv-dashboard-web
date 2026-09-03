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
    if js_path.exists():
        text = js_path.read_text(encoding="utf-8")
        m = re.search(r"window\.DASHBOARD_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$", text)
        if m:
            return json.loads(m.group(1))
    return {"meta": {"metrics": {}}, "bridges": []}
