"""algorithm.py - 算法代码库看板 API 路由

提供 9 个 REST 端点：
- GET /api/algorithm/libraries - 列出代码库、同步状态
- GET /api/algorithm/topology - 拓扑图数据
- GET /api/algorithm/symbols - 符号搜索
- GET /api/algorithm/contract/:protocol - 契约详情
- POST /api/algorithm/diff - 版本语义对比
- GET /api/algorithm/timeline - 时间轴数据（集成 git log）
- POST /api/algorithm/sync - 触发同步
- POST /api/algorithm/train - 触发模型训练（异步）
- GET /api/algorithm/train/status/:task_id - 查询训练状态
"""
import asyncio
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel

router = APIRouter(prefix="/api/algorithm", tags=["algorithm"])

# 数据文件目录
DATA_DIR = Path(__file__).parent.parent.parent / "frontend" / "public" / "algorithm-map"
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 代码库 git 仓库路径映射
GIT_REPOS = {
    "github": r"D:\研\土木水利\论文\代码\github",
    "backend_framework": str(PROJECT_ROOT / "backend_framework"),
    "backends": str(PROJECT_ROOT / "backends"),
}


class SyncRequest(BaseModel):
    """同步请求模型"""
    full: bool = False
    only: Optional[List[str]] = None


class DiffRequest(BaseModel):
    """对比请求模型"""
    base: str
    target: str
    dimension: str = "all"  # all, architecture, loss, trainer, config


class TrainRequest(BaseModel):
    """训练请求模型"""
    model_type: str = "multi_crack"
    n_samples: int = 10000
    data: Optional[str] = None
    model: Optional[str] = None
    epochs: int = 30
    phase1_epochs: Optional[int] = None
    phase2_epochs: Optional[int] = None
    regenerate: bool = False
    bridge: Optional[str] = None


# 训练任务存储（内存，生产环境应改用数据库）
_train_tasks: Dict[str, Dict[str, Any]] = {}


def _load_json(filename: str) -> Dict[str, Any]:
    """加载 JSON 文件"""
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_git_commits(repo_path: str, max_commits: int = 50) -> List[Dict[str, Any]]:
    """从 git 仓库获取提交记录"""
    if not Path(repo_path).exists():
        return []
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", 
             f"--max-count={max_commits}",
             "--pretty=format:%H|%ai|%an|%s"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=10
        )
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "short_hash": parts[0][:8],
                    "date": parts[1],
                    "author": parts[2],
                    "message": parts[3],
                })
        return commits
    except Exception:
        return []


@router.get("/libraries")
async def list_libraries() -> Dict[str, Any]:
    """列出所有代码库及同步状态"""
    data = _load_json("libraries.json")
    stats = _load_json("sync_stats.json")
    return {
        "libraries": data,
        "last_sync": stats.get("end_time", 0),
        "status": "ok" if data else "no_data",
    }


@router.get("/topology")
async def get_topology(
    library: Optional[str] = Query(None, description="代码库名称"),
    focus_node: Optional[str] = Query(None, description="聚焦节点 qualified_name"),
    depth: int = Query(2, ge=1, le=5, description="展开深度"),
) -> Dict[str, Any]:
    """获取拓扑图数据，支持聚焦节点和深度过滤"""
    data = _load_json("topology.json")
    if not data:
        return {"nodes": [], "edges": []}

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # 按库过滤
    if library:
        nodes = [n for n in nodes if n.get("module", "").startswith(library)]
        node_ids = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    # 聚焦节点：只保留指定深度内的子图
    if focus_node and focus_node in {n["id"] for n in nodes}:
        # BFS 获取指定深度内的节点
        from collections import deque
        adj = {}
        for e in edges:
            adj.setdefault(e["source"], []).append(e["target"])
            adj.setdefault(e["target"], []).append(e["source"])

        visited = {focus_node}
        queue = deque([(focus_node, 0)])
        while queue:
            node, d = queue.popleft()
            if d >= depth:
                continue
            for nei in adj.get(node, []):
                if nei not in visited:
                    visited.add(nei)
                    queue.append((nei, d + 1))

        nodes = [n for n in nodes if n["id"] in visited]
        node_ids = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    return {"nodes": nodes, "edges": edges, "focus_node": focus_node, "depth": depth}


@router.get("/symbols")
async def search_symbols(
    q: str = Query("", description="搜索关键词"),
    type: Optional[str] = Query(None, description="符号类型过滤"),
    library: Optional[str] = Query(None, description="代码库过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
) -> Dict[str, Any]:
    """符号搜索：支持模糊匹配、类型/库过滤"""
    data = _load_json("search_index.json")
    if not data:
        return {"symbols": [], "total": 0}

    symbols = data.get("symbols", [])

    # 关键词过滤
    if q:
        q_lower = q.lower()
        symbols = [s for s in symbols if q_lower in s.get("n", "").lower() or q_lower in s.get("q", "").lower()]

    # 类型过滤
    if type:
        symbols = [s for s in symbols if s.get("t") == type]

    # 库过滤
    if library:
        symbols = [s for s in symbols if s.get("m", "").startswith(library)]

    total = len(symbols)
    symbols = symbols[:limit]

    return {"symbols": symbols, "total": total, "limit": limit}


@router.get("/contract/{protocol}")
async def get_contract(protocol: str) -> Dict[str, Any]:
    """获取 Protocol 契约详情，包含所有实现对比表"""
    contracts = _load_json("contracts.json")
    impls = _load_json("implementations.json")

    if protocol not in contracts:
        raise HTTPException(status_code=404, detail=f"Protocol not found: {protocol}")

    contract = contracts[protocol]
    implementations = impls.get(protocol, [])

    # 计算每个实现的符合度摘要
    for impl in implementations:
        impl["compliance"] = {
            "score": impl.get("score", 0),
            "fully_compliant": impl.get("implements_all_required", False),
            "missing_attrs": len(impl.get("missing_attributes", [])),
            "missing_methods": len(impl.get("missing_methods", [])),
        }

    return {
        "protocol": contract,
        "implementations": implementations,
        "summary": {
            "total_implementations": len(implementations),
            "fully_compliant": sum(1 for i in implementations if i.get("implements_all_required", False)),
            "avg_score": sum(i.get("score", 0) for i in implementations) / len(implementations) if implementations else 0,
        },
    }


@router.post("/diff")
async def compare_versions(request: DiffRequest) -> Dict[str, Any]:
    """版本语义对比：对比两个后端实现的差异"""
    comps = _load_json("component_index.json")
    backends = _load_json("backends.json")

    base_comps = comps.get(request.base, {}) if request.dimension in ("all", "config") else {}
    target_comps = comps.get(request.target, {}) if request.dimension in ("all", "config") else {}

    # 简化版对比：返回两个版本的组件配置差异
    all_types = set(base_comps.keys()) | set(target_comps.keys())
    diff_result = {}

    for comp_type in all_types:
        base_names = set(base_comps.get(comp_type, {}).keys())
        target_names = set(target_comps.get(comp_type, {}).keys())

        diff_result[comp_type] = {
            "only_in_base": list(base_names - target_names),
            "only_in_target": list(target_names - base_names),
            "common": list(base_names & target_names),
            "config_diff": {},
        }

    return {
        "base": request.base,
        "target": request.target,
        "dimension": request.dimension,
        "diff": diff_result,
    }


@router.get("/timeline")
async def get_timeline(
    library: Optional[str] = Query(None, description="代码库名称"),
    since: Optional[str] = Query(None, description="起始时间 ISO 格式"),
    until: Optional[str] = Query(None, description="结束时间 ISO 格式"),
) -> Dict[str, Any]:
    """获取时间轴数据：从 git 仓库读取提交历史"""
    commits = []
    
    # 确定要查询的仓库
    repos_to_query = {}
    if library:
        repo_path = GIT_REPOS.get(library)
        if repo_path:
            repos_to_query[library] = repo_path
    else:
        repos_to_query = GIT_REPOS
    
    # 获取每个仓库的提交
    for repo_name, repo_path in repos_to_query.items():
        repo_commits = _get_git_commits(repo_path, max_commits=50)
        for commit in repo_commits:
            commit["repo"] = repo_name
        commits.extend(repo_commits)
    
    # 按日期排序
    commits.sort(key=lambda c: c["date"], reverse=True)
    
    # 生成热力图数据（近30天）
    heatmap: Dict[str, int] = {}
    now = datetime.now()
    for i in range(30):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        count = sum(1 for c in commits if c["date"].startswith(date))
        if count > 0:
            heatmap[date] = count
    
    return {
        "commits": commits[:30],
        "heatmap": heatmap,
        "tags": [],
        "experiments": [],
    }

# ───────────────────────────────────────────────────────────────────
# 实验记录端点
# ───────────────────────────────────────────────────────────────────
class CreateExperimentRequest(BaseModel):
    name: str
    purpose: str = ""
    experiment_dir: Optional[str] = None
    template: str = "basic"

class UpdateMetricsRequest(BaseModel):
    experiment_id: str
    metrics: Dict[str, Any]
    note: str = ""
    experiment_dir: Optional[str] = None

class SetExperimentDirRequest(BaseModel):
    experiment_dir: str




class RecordExperimentRequest(BaseModel):
    """记录实验请求模型"""
    note: str
    type: str = "train"
    protocol: Optional[str] = None
    bridge: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


@router.post("/record")
async def record_experiment(request: RecordExperimentRequest = Body(...)) -> Dict[str, Any]:
    """记录实验到 records.jsonl"""
    try:
        from services.record_service import record_experiment
        record = record_experiment(
            bridge_id=request.bridge or request.protocol or "unknown",
            action=request.type,
            params=request.params or {},
            result=request.metrics or {},
            note=request.note,
        )
        return {
            "record_id": record.get("id"),
            "message": f"实验已记录: {record.get('id')}",
            "record": record,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records")
async def get_experiment_records(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    bridge: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """获取实验记录列表"""
    try:
        from services.record_service import list_records
        result = list_records(bridge_id=bridge, action=action, limit=limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ───────────────────────────────────────────────────────────────────
# 模型对比端点
# ───────────────────────────────────────────────────────────────────

class CompareModelsRequest(BaseModel):
    """对比模型请求模型"""
    modelA: str
    modelB: str
    bridgeA: Optional[str] = None
    bridgeB: Optional[str] = None


@router.post("/compare-models")
async def compare_models(request: CompareModelsRequest = Body(...)) -> Dict[str, Any]:
    """对比两个模型的指标与配置"""
    try:
        from services.compare_service import compare_bridges
        
        # 如果提供了 bridge，使用 bridge 对比
        if request.bridgeA and request.bridgeB:
            result = compare_bridges(request.bridgeA, request.bridgeB)
            return result
        
        # 否则返回基础对比结构（需要实际模型评估支持）
        return {
            "modelA": {
                "path": request.modelA,
                "metrics": {},
                "config": {},
            },
            "modelB": {
                "path": request.modelB,
                "metrics": {},
                "config": {},
            },
            "comparison": {
                "f1_diff": 0,
                "precision_diff": 0,
                "recall_diff": 0,
                "position_mae_diff": 0,
                "depth_mae_diff": 0,
                "winner": "tie",
                "summary": "模型对比需要实际评估指标，请先分别评估两个模型",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def trigger_sync(request: SyncRequest = Body(...)) -> Dict[str, Any]:
    """触发代码库同步（异步执行）"""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "sync_algorithm_code.py"),
    ]
    if request.full:
        cmd.append("--full")
    if request.only:
        cmd.extend(["--only"] + request.only)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        return {
            "status": "started",
            "pid": proc.pid,
            "message": "Sync started in background",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {e}")


@router.get("/sync/status/{pid}")
async def sync_status(pid: int) -> Dict[str, Any]:
    """查询同步进程状态"""
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
        )
        running = str(pid) in proc.stdout
        return {"pid": pid, "running": running}
    except Exception:
        return {"pid": pid, "running": False, "error": "Unable to check status"}


@router.post("/train")
async def trigger_train(request: TrainRequest = Body(...)) -> Dict[str, Any]:
    """触发模型训练（异步执行）"""
    task_id = str(uuid.uuid4())[:8]
    
    # 存储任务信息
    _train_tasks[task_id] = {
        "status": "started",
        "request": request.dict(),
        "progress": 0,
        "stage": "preparing",
        "message": "准备训练...",
    }
    
    # 异步执行训练
    async def run_training():
        try:
            # 导入训练服务
            backend_path = str(PROJECT_ROOT / "backend")
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
            
            from services import train_service
            
            # 执行训练
            result = train_service.train_model(
                bridge_id=request.bridge,
                model_type=request.model_type,
                n_samples=request.n_samples,
                data=request.data,
                model=request.model,
                epochs=request.epochs,
                phase1_epochs=request.phase1_epochs,
                phase2_epochs=request.phase2_epochs,
                regenerate=request.regenerate,
            )
            
            # 更新任务状态
            if "error" in result:
                _train_tasks[task_id]["status"] = "failed"
                _train_tasks[task_id]["error"] = result["error"]
            else:
                _train_tasks[task_id]["status"] = "completed"
                _train_tasks[task_id]["metrics"] = result.get("metrics", {})
                _train_tasks[task_id]["model_path"] = result.get("model", "")
                _train_tasks[task_id]["duration_s"] = result.get("duration_s", 0)
                
        except Exception as e:
            _train_tasks[task_id]["status"] = "failed"
            _train_tasks[task_id]["error"] = str(e)
    
    # 启动异步任务
    asyncio.get_event_loop().create_task(run_training())
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "训练任务已启动",
    }


@router.get("/train/status/{task_id}")
async def train_status(task_id: str) -> Dict[str, Any]:
    """查询训练任务状态"""
    if task_id not in _train_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return _train_tasks[task_id]

# ───────────────────────────────────────────────────────────────────
# Pipeline 执行端点
# ───────────────────────────────────────────────────────────────────

from services.pipeline_service import (
    create_pipeline_task,
    get_pipeline_task,
    list_pipeline_tasks,
    run_pipeline_async,
    save_pipeline_version,
    list_pipeline_versions,
    get_pipeline_version,
    load_pipeline_version,
)


class PipelineRunRequest(BaseModel):
    name: str
    description: str = ""
    nodes: list
    connections: list


@router.post("/pipeline/run")
async def run_pipeline(request: PipelineRunRequest) -> Dict[str, Any]:
    """触发流水线执行，返回 task_id"""
    task = create_pipeline_task(
        name=request.name,
        description=request.description,
        nodes=request.nodes,
        connections=request.connections,
    )
    
    async def _run():
        await run_pipeline_async(task)
    
    asyncio.create_task(_run())
    
    return {
        "task_id": task.task_id,
        "status": task.status,
        "message": f"流水线 '{request.name}' 已启动",
    }


@router.get("/pipeline/status/{task_id}")
async def pipeline_status(task_id: str) -> Dict[str, Any]:
    """查询流水线执行状态"""
    task = get_pipeline_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "task_id": task.task_id,
        "name": task.name,
        "status": task.status,
        "progress": task.progress,
        "result": task.result,
        "error": task.error,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "duration_s": task.duration_s,
    }


@router.get("/pipelines")
async def list_pipelines() -> Dict[str, Any]:
    """列出所有流水线任务"""
    tasks = list_pipeline_tasks()
    return {"pipelines": tasks, "total": len(tasks)}


from services.git_service import (
    get_recent_commits,
    get_file_history,
    compare_commits,
    get_all_repo_statuses,
    GIT_REPOS as GIT_REPO_PATHS,
)

# ───────────────────────────────────────────────────────────────────
# Git 追踪端点
# ───────────────────────────────────────────────────────────────────

class FileHistoryRequest(BaseModel):
    repo: str
    file_path: str
    max_commits: int = 10


@router.get("/git/repos")
async def list_git_repos() -> Dict[str, Any]:
    """列出可追踪的 Git 仓库"""
    repos = []
    for name, path in GIT_REPO_PATHS.items():
        exists = os.path.exists(path)
        repos.append({
            "name": name,
            "path": path,
            "exists": exists,
        })
    return {"repos": repos, "count": len(repos)}


@router.get("/git/commits/{repo}")
async def get_git_commits(repo: str, max_commits: int = 20) -> Dict[str, Any]:
    """获取指定仓库的最近提交"""
    if repo not in GIT_REPO_PATHS:
        raise HTTPException(status_code=404, detail=f"Repo {repo} not found")
    
    commits = get_recent_commits(GIT_REPO_PATHS[repo], max_commits=max_commits)
    return {"repo": repo, "commits": commits, "count": len(commits)}


@router.post("/git/file-history")
async def get_file_history_endpoint(request: FileHistoryRequest) -> Dict[str, Any]:
    """获取文件的历史提交"""
    if request.repo not in GIT_REPO_PATHS:
        raise HTTPException(status_code=404, detail=f"Repo {request.repo} not found")
    
    history = get_file_history(GIT_REPO_PATHS[request.repo], request.file_path, max_commits=request.max_commits)
    return {"repo": request.repo, "file": request.file_path, "history": history, "count": len(history)}


@router.post("/git/compare")
async def git_compare(request: DiffRequest) -> Dict[str, Any]:
    """比较两个提交的差异"""
    if request.base not in GIT_REPO_PATHS:
        raise HTTPException(status_code=404, detail=f"Base repo {request.base} not found")
    
    # Get latest commits from both repos for comparison
    base_commits = get_recent_commits(GIT_REPO_PATHS[request.base], max_commits=1)
    target_commits = get_recent_commits(GIT_REPO_PATHS.get(request.target, request.base), max_commits=1)
    
    if not base_commits or not target_commits:
        return {"error": "Could not get commits for comparison"}
    
    comparison = compare_commits(
        GIT_REPO_PATHS[request.base],
        base_commits[0]["sha"],
        target_commits[0]["sha"]
    )
    return comparison


@router.get("/git/status")
async def get_git_status() -> Dict[str, Any]:
    """获取所有仓库的状态"""
    return get_all_repo_statuses()

# ───────────────────────────────────────────────────────────────────
# Pipeline 版本管理端点
# ───────────────────────────────────────────────────────────────────

class SaveVersionRequest(BaseModel):
    task_id: str
    name: str
    metadata: Dict[str, Any] = {}


@router.post("/pipeline/version/save")
async def save_pipeline_version_endpoint(request: SaveVersionRequest) -> Dict[str, Any]:
    """保存流水线配置为版本快照"""
    task = get_pipeline_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found")
    
    version_id = save_pipeline_version(
        task_id=request.task_id,
        name=request.name,
        instance={
            "nodes": task.nodes,
            "connections": task.connections,
            "name": task.name,
            "description": task.description,
        },
        metadata=request.metadata,
    )
    return {"version_id": version_id, "message": "版本已保存"}


@router.get("/pipeline/versions/{task_id}")
async def list_pipeline_versions_endpoint(task_id: str) -> Dict[str, Any]:
    """列出流水线的版本历史"""
    versions = list_pipeline_versions(task_id=task_id)
    return {"versions": versions, "count": len(versions)}


@router.get("/pipeline/version/{version_id}")
async def get_pipeline_version_endpoint(version_id: str) -> Dict[str, Any]:
    """获取版本详情"""
    version = get_pipeline_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
    return version


@router.post("/pipeline/version/load/{version_id}")
async def load_pipeline_version_endpoint(version_id: str) -> Dict[str, Any]:
    """加载版本配置创建新流水线"""
    instance = load_pipeline_version(version_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
    
    # Create a new task from the loaded version
    new_task = create_pipeline_task(
        name=f"{instance.get('name', 'Pipeline')} (复制)",
        description=instance.get("description", ""),
        nodes=instance.get("nodes", []),
        connections=instance.get("connections", []),
    )
    
    return {
        "task_id": new_task.task_id,
        "name": new_task.name,
        "message": "已从版本创建新流水线"
    }

# ───────────────────────────────────────────────────────────────────
# Pipeline 运行记录端点
# ───────────────────────────────────────────────────────────────────

@router.get("/pipeline-runs")
async def list_pipeline_runs(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """获取 Pipeline 运行历史"""
    tasks = list_pipeline_tasks()
    # 按开始时间倒序
    tasks_sorted = sorted(tasks, key=lambda t: t.started_at or '', reverse=True)
    paginated = tasks_sorted[offset:offset + limit]
    
    runs = []
    for task in paginated:
        runs.append({
            "id": task.task_id,
            "name": task.name,
            "description": task.description,
            "status": task.status,
            "startTime": task.started_at,
            "endTime": task.completed_at,
            "durationMs": task.duration_s * 1000 if task.duration_s else None,
            "stages": task.progress.get('stages', []) if task.progress else [],
            "metrics": task.result.get('metrics', {}) if task.result else {},
            "error": task.error,
            "config": task.progress.get('config', {}) if task.progress else {},
        })
    
    return {
        "runs": runs,
        "total": len(tasks_sorted),
    }


@router.get("/pipeline-runs/{run_id}")
async def get_pipeline_run(run_id: str) -> Dict[str, Any]:
    """获取单个 Pipeline 运行详情"""
    task = get_pipeline_task(run_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    
    return {
        "id": task.task_id,
        "name": task.name,
        "description": task.description,
        "status": task.status,
        "startTime": task.started_at,
        "endTime": task.completed_at,
        "durationMs": task.duration_s * 1000 if task.duration_s else None,
        "stages": task.progress.get('stages', []) if task.progress else [],
        "metrics": task.result.get('metrics', {}) if task.result else {},
        "error": task.error,
        "config": task.progress.get('config', {}) if task.progress else {},
    }

# ───────────────────────────────────────────────────────────────────
# 模型对比端点
# ───────────────────────────────────────────────────────────────────

from services.compare_service import compare_bridges
from services.train_service import train_model

class CompareModelsRequest(BaseModel):
    modelA: str
    modelB: str
    bridgeA: Optional[str] = None
    bridgeB: Optional[str] = None


@router.post("/compare-models")
async def compare_models_endpoint(request: CompareModelsRequest) -> Dict[str, Any]:
    """对比两个模型的指标与配置"""
    try:
        # 如果提供了 bridge，从 registry 获取模型路径和指标
        # 否则直接使用提供的模型路径
        
        # 这里简化处理：使用 compare_service 对比两个桥梁的指标
        # 实际应该加载模型并运行评估
        
        # 尝试从 bridge 获取模型信息
        model_a_path = request.modelA
        model_b_path = request.modelB
        
        if request.bridgeA:
            result = compare_bridges(request.bridgeA, request.bridgeB or request.bridgeA)
            if "error" not in result:
                # 使用 bridge 的模型路径和指标
                pass
        
        # 简化返回：构造对比结果
        # 实际应调用 evaluate_service 对两个模型分别评估
        return {
            "modelA": {
                "path": model_a_path,
                "metrics": {},
                "config": {},
            },
            "modelB": {
                "path": model_b_path,
                "metrics": {},
                "config": {},
            },
            "comparison": {
                "f1_diff": 0,
                "precision_diff": 0,
                "recall_diff": 0,
                "position_mae_diff": 0,
                "depth_mae_diff": 0,
                "winner": "tie",
                "summary": "模型对比功能待完善，请使用评估服务分别评估两个模型",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ───────────────────────────────────────────────────────────────────
# Pipeline 规格端点
# ───────────────────────────────────────────────────────────────────

PIPELINE_YAMLS = {
    "pipeline_1_cpdv_simulation": "pipeline_1_cpdv_simulation.yaml",
    "pipeline_2_single_crack_bp": "pipeline_2_single_crack_bp.yaml",
    "pipeline_3_lstm_sequence": "pipeline_3_lstm_sequence.yaml",
    "pipeline_4_multi_crack": "pipeline_4_multi_crack.yaml",
    "pipeline_5_pinn": "pipeline_5_pinn.yaml",
    "pipeline_6_cpdv_analysis": "pipeline_6_cpdv_analysis.yaml",
}

ALGORITHM_CODE_DIR = Path(__file__).parent.parent.parent / "algorithm-code"


@router.get("/pipelines")
async def get_pipeline_specs() -> Dict[str, Any]:
    """返回所有 pipeline 的规格（名称、描述、stages、依赖等）。"""
    import yaml
    result = []
    for pid, yml_name in PIPELINE_YAMLS.items():
        yml_path = ALGORITHM_CODE_DIR / yml_name
        if not yml_path.exists():
            continue
        with open(yml_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        pipe = spec.get('pipeline', {})
        stages = pipe.get('stages', [])
        result.append({
            "id": pid,
            "name": pipe.get('name', pid),
            "description": pipe.get('description', ''),
            "category": pipe.get('category', ''),
            "version": pipe.get('version', ''),
            "depends_on": spec.get('depends_on_pipelines', []),
            "stages": [
                {
                    "id": s['id'],
                    "name": s.get('name', s['id']),
                    "description": s.get('description', ''),
                    "script": s.get('script', ''),
                    "estimated_time": s.get('estimated_time', ''),
                    "outputs": s.get('outputs', []),
                    "critical": s.get('critical', True),
                }
                for s in stages
            ],
        })
    return {"pipelines": result}


# ───────────────────────────────────────────────────────────────────
# 实验记录管理（Obsidian集成）
# ───────────────────────────────────────────────────────────────────

@router.get("/experiment/docs")
async def get_experiment_docs(
    experiment_dir: Optional[str] = Query(None, description="实验文档目录"),
) -> Dict[str, Any]:
    """扫描实验文档目录，返回实验列表"""
    try:
        from services.experiment_records_service import scan_experiment_dir
        experiments = scan_experiment_dir(experiment_dir)
        return {
            "experiments": experiments,
            "total": len(experiments),
            "experiment_dir": experiment_dir or r"D:\Documents\Obsidian\O1\桥梁健康系统\Resource\R4_实验文档",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiment/import")
async def import_experiment_docs(
    experiment_dir: Optional[str] = Query(None, description="实验文档目录"),
) -> Dict[str, Any]:
    """导入实验文档到records.jsonl"""
    try:
        from services.experiment_records_service import import_experiment
        result = import_experiment(experiment_dir)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiment/create")
async def create_experiment_endpoint(
    request: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """创建新实验文档"""
    try:
        from services.experiment_records_service import create_experiment
        result = create_experiment(
            name=request.name,
            purpose=getattr(request, "purpose", "") or "",
            experiment_dir=getattr(request, "experiment_dir", None),
            template=getattr(request, "template", "basic") or "basic",
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiment/metrics")
async def update_experiment_metrics_endpoint(
    request: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """更新实验指标"""
    try:
        from services.experiment_records_service import update_experiment_metrics
        result = update_experiment_metrics(
            experiment_id=request.experiment_id,
            metrics=request.metrics,
            note=getattr(request, "note", "") or "",
            experiment_dir=getattr(request, "experiment_dir", None),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiment/dir")
async def set_experiment_dir_endpoint(
    request: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """设置当前实验文档目录"""
    return {"experiment_dir": request.experiment_dir}
