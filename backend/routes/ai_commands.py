"""
AI Command Routes - FastAPI endpoints for AI conversation commands
POST /api/ai/command - Execute AI command
WS /api/ai/ws - WebSocket for progress updates
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Body, HTTPException
from pydantic import BaseModel, Field

from services.pipeline_executor import executor as pipeline_executor
from services.data_registry import registry as data_registry
from ws import emit as emit_progress, progress as ws_progress

router = APIRouter(prefix="/api/ai", tags=["ai-commands"])


# ─────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────

class AICommandRequest(BaseModel):
    """AI Command request following JSON-RPC 2.0 style"""
    jsonrpc: str = "2.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    meta: Optional[Dict[str, Any]] = None


class AICommandResponse(BaseModel):
    """AI Command response"""
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None


class DashboardSyncRequest(BaseModel):
    widgets: List[str] = [
        "cpdv_timeseries", "model_scorecard", 
        "peak_vs_position", "cv_analysis"
    ]
    force_refresh: bool = False


# ─────────────────────────────────────────────────────────────────────
# Command Handlers
# ─────────────────────────────────────────────────────────────────────

async def handle_pipeline_execute(params: Dict, command_id: str) -> Dict:
    """Execute pipeline(s)"""
    pipelines = params.get("pipelines", [])
    mode = params.get("mode", "quick")
    stages = params.get("stages")
    async_mode = params.get("async", True)
    auto_sync = params.get("auto_sync_dashboard", True)
    
    if not pipelines:
        raise ValueError("pipelines parameter is required")
    
    # Progress callback for WebSocket updates
    def progress_cb(task_id, stage, msg, percent):
        emit_progress("pipeline", stage, msg, percent, task_id=task_id, command_id=command_id)
    
    task_id = await pipeline_executor.run_pipeline(
        pipelines=pipelines,
        mode=mode,
        stages=stages,
        progress_callback=progress_cb,
        auto_sync_dashboard=auto_sync
    )
    
    if async_mode:
        return {"task_id": task_id, "status": "started", "message": f"Started {len(pipelines)} pipeline(s)"}
    else:
        # Wait for completion
        while True:
            await asyncio.sleep(1)
            status = pipeline_executor.get_task_status(task_id)
            if status and status["status"] in ("completed", "failed"):
                return {"task_id": task_id, **status}
            if status is None:
                return {"task_id": task_id, "status": "not_found"}


async def handle_pipeline_status(params: Dict, command_id: str) -> Dict:
    """Get pipeline task status"""
    task_id = params.get("task_id")
    if not task_id:
        raise ValueError("task_id is required")
    
    status = pipeline_executor.get_task_status(task_id)
    if not status:
        raise ValueError(f"Task {task_id} not found")
    
    return status


async def handle_pipeline_cancel(params: Dict, command_id: str) -> Dict:
    """Cancel pipeline task"""
    task_id = params.get("task_id")
    if not task_id:
        raise ValueError("task_id is required")
    
    cancelled = await pipeline_executor.cancel_task(task_id)
    return {"cancelled": cancelled, "task_id": task_id}


async def handle_pipeline_list(params: Dict, command_id: str) -> Dict:
    """List available pipelines"""
    # Load from ai_commands.yaml
    import yaml
    from pathlib import Path
    
    ai_commands_path = Path(__file__).parent.parent / "ai_commands.yaml"
    with open(ai_commands_path, 'r', encoding='utf-8') as f:
        ai_config = yaml.safe_load(f)
    
    pipelines = []
    for pid, stage_info in ai_config.get("pipeline_stages", {}).items():
        pipelines.append({
            "id": pid,
            "name": pid.replace("_", " ").title(),
            "stages": [s["id"] for s in stage_info.get("stages", [])],
            "critical_stages": [s["id"] for s in stage_info.get("stages", []) if s.get("critical")]
        })
    
    return {"pipelines": pipelines}


async def handle_data_query(params: Dict, command_id: str) -> Dict:
    """Query data artifact"""
    artifact = params.get("artifact")
    filters = params.get("filters", {})
    limit = params.get("limit", 100)
    offset = params.get("offset", 0)
    
    if not artifact:
        raise ValueError("artifact is required")
    
    # Map artifact to registry method
    artifact_methods = {
        "dashboard_summary": lambda: data_registry.load_dashboard_summary(filters.get("force_refresh", False)),
        "dashboard_data": lambda: data_registry.load_dashboard_data(filters.get("force_refresh", False)),
        "cpdv_signals": lambda: data_registry.load_cpdv_signals(
            depth=filters.get("depth", 0.2),
            positions=filters.get("positions"),
            downsample=filters.get("downsample", 400),
            force_refresh=filters.get("force_refresh", False)
        ),
        "peak_analysis": lambda: data_registry.load_peak_analysis(
            depths=filters.get("depths"),
            distances=filters.get("distances"),
            force_refresh=filters.get("force_refresh", False)
        ),
        "cv_analysis": lambda: data_registry.load_cv_analysis(
            n_samples=filters.get("n_samples", 50),
            crack_pos=filters.get("crack_pos", 15.0),
            crack_depth=filters.get("crack_depth", 0.2),
            mode=filters.get("mode", "single"),
            positions=filters.get("positions"),
            force_refresh=filters.get("force_refresh", False)
        ),
        "model_metrics": lambda: data_registry.load_model_metrics(
            model_type=filters.get("model_type"),
            bridge_id=filters.get("bridge_id"),
            force_refresh=filters.get("force_refresh", False)
        ),
        "multi_crack_predictions": lambda: data_registry.load_multi_crack_predictions(
            bridge_id=filters.get("bridge_id"),
            force_refresh=filters.get("force_refresh", False)
        ),
        "training_history": lambda: data_registry.load_training_history(
            model_type=filters.get("model_type"),
            limit=limit,
            force_refresh=filters.get("force_refresh", False)
        ),
        "road_profiles": lambda: data_registry.load_road_profiles(
            force_refresh=filters.get("force_refresh", False)
        ),
        "error_distribution": lambda: data_registry.load_error_distribution(
            model_type=filters.get("model_type", "multi_crack_dual"),
            force_refresh=filters.get("force_refresh", False)
        ),
    }
    
    if artifact not in artifact_methods:
        raise ValueError(f"Unknown artifact: {artifact}")
    
    data = artifact_methods[artifact]()
    
    # Apply pagination if data is a list
    if isinstance(data, list):
        total = len(data)
        data = data[offset:offset+limit]
    else:
        total = 1
    
    return {
        "data": data,
        "meta": {
            "artifact": artifact,
            "total_count": total,
            "generated_at": datetime.now().isoformat()
        }
    }


async def handle_data_export(params: Dict, command_id: str) -> Dict:
    """Export data artifact to file"""
    artifact = params.get("artifact")
    format = params.get("format", "json")
    output_path = params.get("output_path")
    filters = params.get("filters", {})
    
    if not artifact:
        raise ValueError("artifact is required")
    
    # First query the data
    query_result = await handle_data_query({"artifact": artifact, "filters": filters}, command_id)
    data = query_result["data"]
    
    # Determine output path
    if not output_path:
        output_path = str(config.DATA_DIR / f"{artifact}.{format}")
    
    # Write file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "json":
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif format == "js":
        with open(output, 'w', encoding='utf-8') as f:
            f.write(f"window.DASHBOARD_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};\n")
    elif format == "csv":
        import csv
        if isinstance(data, list) and data:
            with open(output, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        else:
            raise ValueError("CSV export requires list of objects")
    
    return {
        "file_path": str(output),
        "size_bytes": output.stat().st_size,
        "format": format
    }


async def handle_data_preview(params: Dict, command_id: str) -> Dict:
    """Preview data structure"""
    artifact = params.get("artifact")
    limit = params.get("limit", 5)
    
    if not artifact:
        raise ValueError("artifact is required")
    
    query_result = await handle_data_query({"artifact": artifact, "limit": limit}, command_id)
    data = query_result["data"]
    
    # Generate schema from sample
    schema = {}
    if isinstance(data, dict):
        schema = {k: type(v).__name__ for k, v in data.items()}
    elif isinstance(data, list) and data:
        schema = {k: type(v).__name__ for k, v in data[0].items()}
    
    samples = data if isinstance(data, list) else [data]
    samples = samples[:limit]
    
    return {
        "schema": schema,
        "samples": samples,
        "field_descriptions": {}
    }


async def handle_dashboard_sync(params: Dict, command_id: str) -> Dict:
    """Sync all dashboard widget data"""
    widgets = params.get("widgets", [
        "cpdv_timeseries", "model_scorecard", 
        "peak_vs_position", "cv_analysis"
    ])
    force_refresh = params.get("force_refresh", False)
    
    widget_data = {}
    
    # Load data for each widget
    for widget_id in widgets:
        try:
            if widget_id == "cpdv_timeseries":
                widget_data[widget_id] = data_registry.load_cpdv_signals(force_refresh=force_refresh)
            elif widget_id == "model_scorecard":
                widget_data[widget_id] = data_registry.load_model_metrics(force_refresh=force_refresh)
            elif widget_id == "peak_vs_position":
                widget_data[widget_id] = data_registry.load_peak_analysis(force_refresh=force_refresh)
            elif widget_id == "peak_vs_depth":
                widget_data[widget_id] = data_registry.load_peak_analysis(force_refresh=force_refresh)
            elif widget_id == "cv_analysis":
                widget_data[widget_id] = data_registry.load_cv_analysis(force_refresh=force_refresh)
            elif widget_id == "multi_position_boxplot":
                widget_data[widget_id] = data_registry.load_cv_analysis(
                    mode="multi_pos", force_refresh=force_refresh
                )
            elif widget_id == "road_profile":
                widget_data[widget_id] = data_registry.load_road_profiles(force_refresh=force_refresh)
            elif widget_id == "error_distribution":
                widget_data[widget_id] = data_registry.load_error_distribution(force_refresh=force_refresh)
            elif widget_id == "multi_crack_comparison":
                widget_data[widget_id] = data_registry.load_multi_crack_predictions(force_refresh=force_refresh)
        except Exception as e:
            widget_data[widget_id] = {"error": str(e)}
    
    return {
        "widget_data": widget_data,
        "timestamp": datetime.now().isoformat(),
        "source": "data_registry"
    }


async def handle_analysis_run(params: Dict, command_id: str) -> Dict:
    """Run specific analysis"""
    analysis_type = params.get("type")
    a_params = params.get("params", {})
    
    if not analysis_type:
        raise ValueError("type is required")
    
    emit_progress("analysis", "started", f"Running {analysis_type} analysis", 10, command_id=command_id)
    
    if analysis_type == "cv":
        result = data_registry.load_cv_analysis(**a_params, force_refresh=True)
    elif analysis_type == "peak_vs_pos":
        result = data_registry.load_peak_analysis(**a_params, force_refresh=True)
    elif analysis_type == "peak_vs_depth":
        result = data_registry.load_peak_analysis(**a_params, force_refresh=True)
    elif analysis_type == "signal_waveform":
        result = data_registry.load_cpdv_signals(**a_params, force_refresh=True)
    elif analysis_type == "road_profile":
        result = data_registry.load_road_profiles(force_refresh=True)
    elif analysis_type == "error_distribution":
        result = data_registry.load_error_distribution(**a_params, force_refresh=True)
    else:
        raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    emit_progress("analysis", "completed", f"{analysis_type} analysis done", 100, command_id=command_id)
    
    # Determine chart paths
    charts = []
    if analysis_type in ("cv", "peak_vs_pos", "peak_vs_depth"):
        charts.append(str(config.OUTPUTS_DIR / "figures" / "cpdv" / f"random_cpdv_*.png"))
    elif analysis_type == "signal_waveform":
        charts.append(str(config.OUTPUTS_DIR / "figures" / "cpdv" / "cpdv_signal_waveforms.png"))
    elif analysis_type == "road_profile":
        charts.append(str(config.OUTPUTS_DIR / "figures" / "cpdv" / "road_profile_ABC.png"))
    elif analysis_type == "error_distribution":
        charts.append(str(config.OUTPUTS_DIR / "figures" / "cpdv" / "dual_head_error_distribution.png"))
    
    return {
        "result": result,
        "charts": charts,
        "interpretation": None
    }


async def handle_analysis_interpret(params: Dict, command_id: str) -> Dict:
    """AI interpretation of analysis results"""
    artifact = params.get("artifact")
    question = params.get("question")
    
    if not artifact or not question:
        raise ValueError("artifact and question are required")
    
    # Load the artifact data
    query_result = await handle_data_query({"artifact": artifact}, command_id)
    data = query_result["data"]
    
    # Simple rule-based interpretation (replace with LLM call in production)
    interpretation = ""
    recommendations = []
    
    if artifact == "cv_analysis":
        cv = data.get("cv", 0)
        if cv >= 0.30:
            interpretation = f"CV={cv:.1%} ≥ 30%: Operating conditions significantly affect CPDV. Multi-condition training is REQUIRED."
            recommendations = [
                "Enable Pipeline 1 multi-condition data generation (stage_1b)",
                "Use Pipeline 4 multi-crack model with dual-head architecture",
                "Increase training data diversity with random vehicle/bridge parameters"
            ]
        else:
            interpretation = f"CV={cv:.1%} < 30%: Operating conditions have limited effect. Single-condition training may suffice."
            recommendations = [
                "Pipeline 2 (BP) or Pipeline 3 (LSTM) may be sufficient",
                "Consider simpler model for faster inference"
            ]
    
    elif artifact == "model_metrics":
        # Find best model
        best_model = None
        best_f1 = 0
        for key, metrics in data.items():
            if isinstance(metrics, dict) and "f1" in metrics:
                if metrics["f1"] > best_f1:
                    best_f1 = metrics["f1"]
                    best_model = key
        
        if best_model:
            interpretation = f"Best performing model: {best_model} with F1={best_f1:.3f}"
            recommendations = [
                f"Deploy {best_model} for production inference",
                "Monitor model drift with periodic re-evaluation"
            ]
    
    elif artifact == "peak_analysis":
        interpretation = "CPDV peak values show linear relationship with crack depth and position-dependent sensitivity."
        recommendations = [
            "Use peak-depth calibration for depth estimation",
            "Position sensitivity varies - place sensors at high-sensitivity locations"
        ]
    
    return {
        "interpretation": interpretation,
        "recommendations": recommendations,
        "confidence": 0.85
    }


async def handle_analysis_compare(params: Dict, command_id: str) -> Dict:
    """Compare models or scenarios"""
    models = params.get("models", [])
    metrics = params.get("metrics", ["f1", "mae_pos", "mae_depth"])
    scenarios = params.get("scenarios", [])
    
    if len(models) < 2:
        raise ValueError("At least 2 models required for comparison")
    
    # Load metrics for each model
    all_metrics = data_registry.load_model_metrics()
    
    comparison = {}
    for model in models:
        model_data = {}
        for key, metrics_data in all_metrics.items():
            if model in key:
                model_data[key] = {m: metrics_data.get(m) for m in metrics if m in metrics_data}
        comparison[model] = model_data
    
    # Determine winner based on first metric
    primary_metric = metrics[0] if metrics else "f1"
    winner = None
    best_value = -1
    
    for model, data in comparison.items():
        for key, vals in data.items():
            val = vals.get(primary_metric)
            if val is not None and val > best_value:
                best_value = val
                winner = model
    
    return {
        "comparison": comparison,
        "winner": winner,
        "summary": f"Best {primary_metric}: {winner} ({best_value:.4f})" if winner else "No data available"
    }


# ─────────────────────────────────────────────────────────────────────
# Method Router
# ─────────────────────────────────────────────────────────────────────

COMMAND_HANDLERS = {
    "pipeline.execute": handle_pipeline_execute,
    "pipeline.status": handle_pipeline_status,
    "pipeline.cancel": handle_pipeline_cancel,
    "pipeline.list": handle_pipeline_list,
    "data.query": handle_data_query,
    "data.export": handle_data_export,
    "data.preview": handle_data_preview,
    "dashboard.sync": handle_dashboard_sync,
    "analysis.run": handle_analysis_run,
    "analysis.interpret": handle_analysis_interpret,
    "analysis.compare": handle_analysis_compare,
}


# ─────────────────────────────────────────────────────────────────────
# REST Endpoint
# ─────────────────────────────────────────────────────────────────────

@router.post("/command")
async def execute_ai_command(request: AICommandRequest) -> AICommandResponse:
    """Execute AI command"""
    method = request.method
    params = request.params
    command_id = request.id
    
    handler = COMMAND_HANDLERS.get(method)
    if not handler:
        return AICommandResponse(
            id=command_id,
            error={"code": -32601, "message": f"Method not found: {method}"}
        )
    
    try:
        result = await handler(params, command_id)
        return AICommandResponse(id=command_id, result=result)
    except ValueError as e:
        return AICommandResponse(
            id=command_id,
            error={"code": -32602, "message": str(e)}
        )
    except Exception as e:
        return AICommandResponse(
            id=command_id,
            error={"code": -32603, "message": f"Internal error: {type(e).__name__}: {e}"}
        )


# ─────────────────────────────────────────────────────────────────────
# WebSocket for Progress
# ─────────────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def ai_ws(ws: WebSocket, tags: str = Query(default="pipeline,analysis,dashboard")):
    """WebSocket for AI command progress updates"""
    if tags == "*" or not tags.strip():
        tag_set = {"*"}
    else:
        tag_set = {t.strip() for t in tags.split(",") if t.strip()}
    
    # Add ai-commands tag
    tag_set.add("ai-commands")
    
    await ws_progress.connect(ws, tag_set)
    
    try:
        await ws.send_json({
            "type": "connected",
            "tags": list(tag_set),
            "message": "AI command WebSocket connected"
        })
        
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
                elif msg.get("type") == "filter":
                    new_tags = set(msg.get("tags", [])) | {"ai-commands"}
                    ws_progress.active = [
                        (w, new_tags) if w is ws else (w, t) 
                        for (w, t) in ws_progress.active
                    ]
                    await ws.send_json({"type": "filter_ack", "tags": list(new_tags)})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_progress.disconnect(ws)


# ─────────────────────────────────────────────────────────────────────
# Command Metadata Endpoint
# ─────────────────────────────────────────────────────────────────────

@router.get("/commands/meta")
async def get_command_meta():
    """Get command metadata for frontend dynamic UI generation"""
    import yaml
    from pathlib import Path
    
    ai_commands_path = Path(__file__).parent.parent / "ai_commands.yaml"
    with open(ai_commands_path, 'r', encoding='utf-8') as f:
        ai_config = yaml.safe_load(f)
    
    return {
        "version": ai_config.get("version", "1.0"),
        "categories": ai_config.get("categories", {}),
        "commands": ai_config.get("commands", {}),
        "widgets": ai_config.get("widgets", {}),
        "pipeline_stages": ai_config.get("pipeline_stages", {})
    }


# Need to import config
import config