"""Pipeline 执行服务 — 从前端 PipelineInstance 到 backend_framework 执行"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_framework.composition.pipeline_builder import PipelineBuilder, build_pipeline_from_config
from ws import emit as emit_progress


@dataclass
class PipelineTask:
    task_id: str
    name: str
    description: str
    nodes: list
    connections: list
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_s: Optional[float] = None


# 任务存储（内存，生产环境应改用 Redis/数据库）
_pipeline_tasks: Dict[str, PipelineTask] = {}


def _pipeline_instance_to_config(instance: Dict[str, Any]) -> Dict[str, Any]:
    """将前端 PipelineInstance 转换为 backend_framework 配置字典。"""
    nodes = instance.get("nodes", [])
    connections = instance.get("connections", [])
    
    # 提取各组件配置
    data_loader_cfg = None
    model_cfg = None
    loss_cfg = None
    optimizer_cfg = None
    trainer_cfg = None
    evaluator_cfg = None
    
    for node in nodes:
        category = node.get("category", "")
        impl = node.get("selected_impl") or {}
        config = node.get("config", {})
        
        if category == "data_loader":
            data_loader_cfg = {
                "type": impl.get("name", "SimulatedDataLoader"),
                "params": config
            }
        elif category == "model":
            model_cfg = {
                "type": impl.get("name", "DualHeadNetwork"),
                "params": config
            }
        elif category == "loss":
            loss_cfg = {
                "type": impl.get("name", "CombinedLoss"),
                "params": config
            }
        elif category == "optimizer":
            optimizer_cfg = {
                "type": impl.get("name", "Adam"),
                "params": config
            }
        elif category == "trainer":
            trainer_cfg = {
                "type": impl.get("name", "StandardTrainer"),
                "params": config
            }
        elif category == "evaluator":
            evaluator_cfg = {
                "type": impl.get("name", "CrackEvaluator"),
                "params": config
            }
    
    # 构建完整配置
    config = {
        "experiment": {
            "name": instance.get("name", "Pipeline Run"),
            "description": instance.get("description", ""),
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        },
        "components": {
            "data_loader": data_loader_cfg or {"type": "SimulatedDataLoader"},
            "model": model_cfg or {"type": "DualHeadNetwork"},
            "loss": loss_cfg or {"type": "CombinedLoss"},
            "optimizer": optimizer_cfg or {"type": "Adam"},
            "trainer": trainer_cfg or {"type": "StandardTrainer"},
            "evaluator": evaluator_cfg or {"type": "CrackEvaluator"},
        },
        "output": {
            "save_dir": "outputs/pipeline_results",
            "save_interval_epochs": 5,
        }
    }
    
    return config


async def run_pipeline_async(
    task: PipelineTask,
    abort_check: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """异步执行 Pipeline，通过 emit_progress 推送进度事件。"""
    config = _pipeline_instance_to_config({
        "name": task.name,
        "description": task.description,
        "nodes": task.nodes,
        "connections": task.connections,
    })
    
    task.status = "running"
    task.started_at = datetime.now().isoformat(timespec="seconds")
    emit_progress("pipeline", "starting", f"启动流水线: {task.name}", percent=5)
    
    try:
        # 阶段 1: 构建管线
        emit_progress("pipeline", "building", "构建组件...", percent=10)
        builder = PipelineBuilder(config)
        data_loader, model, loss_fn, optimizer, trainer, evaluator = builder.build()
        emit_progress("pipeline", "built", "组件构建完成", percent=25,
                      data_loader=type(data_loader).__name__,
                      model=type(model).__name__,
                      loss=type(loss_fn).__name__,
                      optimizer=type(optimizer).__name__,
                      trainer=type(trainer).__name__,
                      evaluator=type(evaluator).__name__)
        
        # 阶段 2: 准备数据
        emit_progress("pipeline", "data_prep", "准备数据...", percent=30)
        if hasattr(data_loader, 'prepare') and asyncio.iscoroutinefunction(data_loader.prepare):
            await data_loader.prepare()
        elif hasattr(data_loader, 'prepare'):
            data_loader.prepare()
        emit_progress("pipeline", "data_ready", "数据准备完成", percent=40)
        
        # 阶段 3: 训练（如果训练器存在）
        if trainer is not None:
            emit_progress("pipeline", "training_start", "开始训练...", percent=50)
            
            if hasattr(trainer, 'train') and asyncio.iscoroutinefunction(trainer.train):
                result = await trainer.train(
                    model=model,
                    data_loader=data_loader,
                    loss_fn=loss_fn,
                    optimizer=optimizer,
                    config=config.get("trainer_config", {})
                )
            elif hasattr(trainer, 'train'):
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: trainer.train(
                    model=model,
                    data_loader=data_loader,
                    loss_fn=loss_fn,
                    optimizer=optimizer,
                    config=config.get("trainer_config", {})
                ))
            else:
                result = None
            
            if result is not None:
                metrics = getattr(result, 'metrics', {}) if hasattr(result, 'metrics') else {}
                emit_progress("pipeline", "training_done", "训练完成", percent=75, metrics=metrics)
            else:
                emit_progress("pipeline", "training_skipped", "跳过训练（无训练器）", percent=60)
        
        # 阶段 4: 评估
        if evaluator is not None:
            emit_progress("pipeline", "evaluating", "开始评估...", percent=80)
            if hasattr(evaluator, 'evaluate') and asyncio.iscoroutinefunction(evaluator.evaluate):
                eval_result = await evaluator.evaluate(model=model, data_loader=data_loader)
            elif hasattr(evaluator, 'evaluate'):
                loop = asyncio.get_event_loop()
                eval_result = await loop.run_in_executor(None, lambda: evaluator.evaluate(
                    model=model, data_loader=data_loader
                ))
            else:
                eval_result = None
            
            if eval_result is not None:
                eval_metrics = getattr(eval_result, 'metrics', {}) if hasattr(eval_result, 'metrics') else {}
                emit_progress("pipeline", "evaluated", "评估完成", percent=90, metrics=eval_metrics)
            else:
                emit_progress("pipeline", "eval_skipped", "跳过评估（无评估器）", percent=85)
        
        # 完成
        task.status = "completed"
        task.completed_at = datetime.now().isoformat(timespec="seconds")
        task.result = {
            "config": config,
            "components": {
                "data_loader": type(data_loader).__name__,
                "model": type(model).__name__,
                "loss": type(loss_fn).__name__,
                "optimizer": type(optimizer).__name__,
                "trainer": type(trainer).__name__ if trainer else None,
                "evaluator": type(evaluator).__name__ if evaluator else None,
            },
            "metrics": {},
        }
        emit_progress("pipeline", "done", f"流水线完成: {task.name}", percent=100)
        
    except Exception as e:
        import traceback
        task.status = "failed"
        task.error = f"{type(e).__name__}: {e}"
        task.completed_at = datetime.now().isoformat(timespec="seconds")
        emit_progress("pipeline", "error", task.error, percent=0,
                      trace=traceback.format_exc()[-500:])
    
    return task.result or {}


def create_pipeline_task(
    name: str,
    description: str,
    nodes: list,
    connections: list,
) -> PipelineTask:
    """创建新的流水线任务。"""
    task_id = f"pipeline_{uuid.uuid4().hex[:8]}"
    task = PipelineTask(
        task_id=task_id,
        name=name,
        description=description,
        nodes=nodes,
        connections=connections,
    )
    _pipeline_tasks[task_id] = task
    return task


def get_pipeline_task(task_id: str) -> Optional[PipelineTask]:
    """获取流水线任务状态。"""
    return _pipeline_tasks.get(task_id)


def list_pipeline_tasks() -> list:
    """列出所有流水线任务。"""
    return [
        {
            "task_id": t.task_id,
            "name": t.name,
            "status": t.status,
            "started_at": t.started_at,
            "completed_at": t.completed_at,
            "error": t.error,
        }
        for t in _pipeline_tasks.values()
    ]


# ───────────────────────────────────────────────────────────────────
# Pipeline 版本管理
# ───────────────────────────────────────────────────────────────────

_PIPELINE_VERSIONS_DIR = Path(__file__).parent.parent / "data" / "pipeline_versions"
_PIPELINE_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_pipeline_version(
    task_id: str,
    name: str,
    instance: Dict[str, Any],
    metadata: Dict[str, Any] = None,
) -> str:
    """保存流水线配置为版本快照"""
    version_id = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{task_id[-4:]}"
    version_data = {
        "version_id": version_id,
        "task_id": task_id,
        "name": name,
        "instance": instance,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "metadata": metadata or {},
    }
    
    version_file = _PIPELINE_VERSIONS_DIR / f"{version_id}.json"
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(version_data, f, ensure_ascii=False, indent=2)
    
    return version_id


def list_pipeline_versions(task_id: str = None) -> List[Dict[str, Any]]:
    """列出流水线版本"""
    versions = []
    for version_file in _PIPELINE_VERSIONS_DIR.glob("*.json"):
        with open(version_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if task_id and data.get("task_id") != task_id:
            continue
        
        versions.append({
            "version_id": data["version_id"],
            "task_id": data["task_id"],
            "name": data["name"],
            "created_at": data["created_at"],
            "node_count": len(data["instance"].get("nodes", [])),
            "connection_count": len(data["instance"].get("connections", [])),
        })
    
    versions.sort(key=lambda x: x["created_at"], reverse=True)
    return versions


def get_pipeline_version(version_id: str) -> Optional[Dict[str, Any]]:
    """获取指定版本的详细信息"""
    version_file = _PIPELINE_VERSIONS_DIR / f"{version_id}.json"
    if not version_file.exists():
        return None
    
    with open(version_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_pipeline_version(version_id: str) -> Optional[Dict[str, Any]]:
    """加载版本配置到 PipelineInstance 格式"""
    version_data = get_pipeline_version(version_id)
    if not version_data:
        return None
    
    return version_data.get("instance")


def delete_pipeline_version(version_id: str) -> bool:
    """删除版本快照"""
    version_file = _PIPELINE_VERSIONS_DIR / f"{version_id}.json"
    if version_file.exists():
        version_file.unlink()
        return True
    return False
