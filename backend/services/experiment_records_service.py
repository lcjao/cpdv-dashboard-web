"""实验记录服务 - 从 Obsidian 扫描/导入/管理实验文档"""

import json
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# 默认实验文档目录
DEFAULT_EXPERIMENT_DIR = Path(r"D:\Documents\Obsidian\O1\桥梁健康系统\Resource\R4_实验文档")


def _parse_frontmatter(content: str) -> Dict[str, str]:
    """解析 Markdown 文件的 YAML frontmatter"""
    fm = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if m:
        for line in m.group(1).strip().split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                fm[key.strip()] = val.strip()
    return fm


def _extract_metrics(text: str) -> Dict[str, Any]:
    """从实验文档正文中提取指标数据"""
    metrics = {}
    patterns = {
        "f1": r"F1[:\s]*([\d.]+)",
        "pos_mae": r"pos[_-]?MAE[:\s]*([\d.]+)\s*m?",
        "depth_mae": r"depth[_-]?MAE[:\s]*([\d.]+)",
        "recall": r"Recall[:\s]*([\d.]+)",
        "precision": r"Precision[:\s]*([\d.]+)",
        "cv": r"变异系数\s*CV[:\s]*([\d.]+)%?",
    }
    for k, p in patterns.items():
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                metrics[k] = float(m.group(1))
            except ValueError:
                pass
    return metrics


def scan_experiment_dir(experiment_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """扫描实验文档目录，返回实验列表"""
    exp_dir = Path(experiment_dir or DEFAULT_EXPERIMENT_DIR)
    if not exp_dir.exists():
        return []

    experiments = []
    for f in sorted(exp_dir.glob("*.md")):
        if f.name.startswith("未命名") or f.name.startswith("."):
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue

        fm = _parse_frontmatter(content)
        metrics = _extract_metrics(content)

        related_docs = []
        for m in re.finditer(r"\[\[([^\]|]+?)(?:\|[^]]+?)?\]\]", content):
            related_docs.append(m.group(1))

        exp = {
            "id": fm.get("实验编号", f.stem),
            "name": fm.get("实验名称", f.stem),
            "date": fm.get("实验日期", ""),
            "purpose": fm.get("实验目的", ""),
            "related_docs": related_docs,
            "metrics": metrics,
            "file_path": str(f),
            "relative_path": str(f.relative_to(exp_dir.parent.parent)) if exp_dir in f.parents else str(f.name),
            "content_preview": content[500:1500].strip() if len(content) > 500 else content,
            "word_count": len(content),
        }
        experiments.append(exp)

    return experiments


def import_experiment(experiment_dir: Optional[str] = None, sync_records: bool = True) -> Dict[str, Any]:
    """导入实验文档，同时更新 records.jsonl"""
    from services.record_service import record_experiment

    experiments = scan_experiment_dir(experiment_dir)
    imported = []

    if sync_records:
        for exp in experiments:
            from data_loader import load_records
            existing = load_records(limit=200)
            already_exists = any(
                r.get("id") == exp["id"] or r.get("experiment_id") == exp["id"]
                for r in existing
            )

            if not already_exists:
                record = record_experiment(
                    bridge_id="experiment",
                    action="import",
                    params={
                        "experiment_id": exp["id"],
                        "name": exp["name"],
                        "file_path": exp["file_path"],
                    },
                    result=exp["metrics"],
                    note=exp["purpose"],
                )
                imported.append({
                    "experiment_id": exp["id"],
                    "record_id": record.get("id"),
                    "message": "已导入",
                })

    return {
        "total": len(experiments),
        "imported": len(imported),
        "experiments": experiments,
        "imported_records": imported,
    }


def create_experiment(
    name: str,
    purpose: str = "",
    experiment_dir: Optional[str] = None,
    template: str = "basic",
) -> Dict[str, Any]:
    """创建新的实验记录"""
    exp_dir = Path(experiment_dir or DEFAULT_EXPERIMENT_DIR)
    exp_dir.mkdir(parents=True, exist_ok=True)

    existing = scan_experiment_dir(exp_dir)
    max_num = 0
    for exp in existing:
        m = re.match(r"EXP-(\d+)", exp["id"])
        if m:
            max_num = max(max_num, int(m.group(1)))
    exp_num = max_num + 1
    exp_id = f"EXP-{exp_num:03d}"

    filename = f"{exp_id}_{name}.md"
    filepath = exp_dir / filename

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    templates = {
        "basic": f"""---
实验编号: {exp_id}
实验名称: {name}
实验日期: {now}
实验目的: {purpose}
关联文档:
---

## 一、实验方法

### 分析流程
```
[实验流程描述]
```

### 脚本
[相关脚本路径]

## 二、实验结果

### 2.1 结果数据

| 指标 | 值 |
|------|------|
| F1 | |
| pos_MAE | |
| depth_MAE | |

## 三、分析结论

### 核心发现

### 建议措施
""",
        "train": f"""---
实验编号: {exp_id}
实验名称: {name}
实验日期: {now}
实验目的: {purpose}
关联文档:
---

## 一、实验方法

### 训练配置

| 参数 | 值 |
|------|------|
| 模型类型 | |
| 训练轮数 | |
| 学习率 | |
| 批次大小 | |
| 数据量 | |

### 训练流程
```
数据加载 → 模型初始化 → 阶段1训练 → 阶段2训练 → 评估
```

## 二、实验结果

| 指标 | 训练集 | 测试集 |
|------|--------|--------|
| F1 | | |
| pos_MAE | | |
| depth_MAE | | |
| Recall | | |
| Precision | | |

## 三、分析结论

### 核心发现

### 改进方向
""",
        "evaluate": f"""---
实验编号: {exp_id}
实验名称: {name}
实验日期: {now}
实验目的: {purpose}
关联文档:
---

## 一、实验方法

### 评估配置

| 参数 | 值 |
|------|------|
| 模型路径 | |
| 数据路径 | |
| 分类阈值 | |
| 匹配代价 | |

## 二、实验结果

| 指标 | 值 |
|------|------|
| F1 | |
| Recall | |
| Precision | |
| pos_MAE (m) | |
| depth_MAE | |
| n_matched | |
| n_gt | |
| n_pred | |

## 三、分析结论

### 达标情况

### 改进建议
""",
    }

    content = templates.get(template, templates["basic"])
    filepath.write_text(content, encoding="utf-8")

    from services.record_service import record_experiment
    record = record_experiment(
        bridge_id="experiment",
        action="create",
        params={"experiment_id": exp_id, "name": name, "template": template},
        note=purpose,
    )

    return {
        "experiment_id": exp_id,
        "name": name,
        "date": now,
        "file_path": str(filepath),
        "record_id": record.get("id"),
        "message": f"实验 {exp_id} 已创建",
    }


def update_experiment_metrics(
    experiment_id: str,
    metrics: Dict[str, Any],
    note: str = "",
    experiment_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """更新实验指标"""
    exp_dir = Path(experiment_dir or DEFAULT_EXPERIMENT_DIR)
    found = None

    for f in exp_dir.glob("*.md"):
        if f.name.startswith(experiment_id):
            found = f
            break

    if not found:
        return {"error": f"实验 {experiment_id} 未找到"}

    content = found.read_text(encoding="utf-8")
    fm = _parse_frontmatter(content)

    if "指标结果" in fm:
        try:
            existing_metrics = json.loads(fm["指标结果"])
            existing_metrics.update(metrics)
            fm["指标结果"] = json.dumps(existing_metrics, ensure_ascii=False)
        except json.JSONDecodeError:
            fm["指标结果"] = json.dumps(metrics, ensure_ascii=False)
    else:
        fm["指标结果"] = json.dumps(metrics, ensure_ascii=False)

    if note:
        fm["备注"] = note

    new_fm = "---\n"
    for k, v in fm.items():
        new_fm += f"{k}: {v}\n"
    new_fm += "---\n"

    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if m:
        new_content = new_fm + content[m.end():]
    else:
        new_content = new_fm + content

    found.write_text(new_content, encoding="utf-8")

    from services.record_service import record_experiment
    record = record_experiment(
        bridge_id="experiment",
        action="update_metrics",
        params={"experiment_id": experiment_id, "metrics": metrics},
        note=note,
    )

    return {
        "experiment_id": experiment_id,
        "record_id": record.get("id"),
        "metrics": metrics,
        "message": "实验指标已更新",
    }
