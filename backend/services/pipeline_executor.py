
"""
PipelineExecutor - Async pipeline execution with progress callbacks
Maps to pipeline_master.yaml phases and stages
"""
import asyncio
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import yaml

# Import WebSocket progress emitter
from ws import emit as emit_progress

# Import config for paths and Python interpreter
import config

# Load pipeline configuration
CONFIG_DIR = Path(__file__).parent.parent.parent / "algorithm-code"
PIPELINE_MASTER = CONFIG_DIR / "pipeline_master.yaml"

# Pipeline ID to subdirectory mapping
PIPELINE_SUBDIR_MAP = {
    "pipeline_1_cpdv_simulation": "pipeline-1-cpdv-simulation",
    "pipeline_2_single_crack_bp": "pipeline-2-single-crack-bp",
    "pipeline_3_lstm_sequence": "pipeline-3-lstm-sequence",
    "pipeline_4_multi_crack": "pipeline-4-multi-crack",
    "pipeline_5_pinn": "pipeline-5-pinn",
    "pipeline_6_cpdv_analysis": "pipeline-6-cpdv-analysis",
}


class PipelineExecutor:
    """Execute pipelines with stage-level progress tracking"""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._load_config()

    def _load_config(self):
        """Load pipeline_master.yaml configuration"""
        with open(PIPELINE_MASTER, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def get_pipeline_spec(self, pipeline_id: str) -> Dict[str, Any]:
        """Get pipeline specification from config"""
        yaml_map = {
            "pipeline_1_cpdv_simulation": "pipeline_1_cpdv_simulation.yaml",
            "pipeline_2_single_crack_bp": "pipeline_2_single_crack_bp.yaml",
            "pipeline_3_lstm_sequence": "pipeline_3_lstm_sequence.yaml",
            "pipeline_4_multi_crack": "pipeline_4_multi_crack.yaml",
            "pipeline_5_pinn": "pipeline_5_pinn.yaml",
            "pipeline_6_cpdv_analysis": "pipeline_6_cpdv_analysis.yaml",
        }
        yaml_file = yaml_map.get(pipeline_id)
        if not yaml_file:
            return {}

        path = CONFIG_DIR / yaml_file
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def get_pipeline_cwd(self, pipeline_id: str) -> Path:
        """Get the working directory for a pipeline (its subdirectory in algorithm-code)"""
        subdir = PIPELINE_SUBDIR_MAP.get(pipeline_id)
        if subdir:
            p = CONFIG_DIR / subdir
            if p.exists():
                return p
        return CONFIG_DIR

    def get_stages_for_pipeline(self, pipeline_id: str, requested_stages: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get stages to execute for a pipeline"""
        spec = self.get_pipeline_spec(pipeline_id)
        # Stages are under spec['pipeline']['stages'], NOT spec['stages']
        all_stages = spec.get('pipeline', {}).get('stages', [])

        if requested_stages:
            return [s for s in all_stages if s['id'] in requested_stages]
        # Return only critical stages by default
        return [s for s in all_stages if s.get('critical', True)]

    def build_command(self, pipeline_id: str, stage: Dict[str, Any], mode: str = "quick") -> List[str]:
        """Build command to execute a pipeline stage with proper argparse flags"""
        script = stage.get('script', '')
        if not script:
            return []

        # Get pipeline working directory
        pipeline_cwd = self.get_pipeline_cwd(pipeline_id)
        script_path = pipeline_cwd / script
        if not script_path.exists():
            # Fallback: try relative to CONFIG_DIR
            script_path = CONFIG_DIR / script
            if not script_path.exists():
                return []

        # Base command with CPDV venv Python
        python_exe = config.PYTHON_EXE
        cmd = [python_exe, str(script_path)]

        # Convert stage parameters to argparse flags
        params = stage.get('parameters', {}).copy()
        
        # Apply quick mode overrides to params before building command
        if mode == "quick":
            script_name = Path(script).name
            if "generate_data" in script_name:
                # Override n_samples for quick mode
                params['n_samples'] = 1000
            elif "train" in script_name:
                # Override epochs for quick mode if not explicitly set
                if 'epochs' not in params:
                    params['epochs'] = 50

        if params:
            for key, value in params.items():
                flag = f"--{key}"
                if isinstance(value, bool):
                    if value:
                        cmd.append(flag)
                    # Skip False boolean flags
                elif isinstance(value, list):
                    # List parameters: --flag val1 val2 val3
                    cmd.append(flag)
                    for v in value:
                        cmd.append(str(v))
                else:
                    # Scalar parameters: --flag value
                    cmd.append(flag)
                    cmd.append(str(value))

        return cmd

    async def run_pipeline(
        self,
        pipelines: List[str],
        mode: str = "quick",
        stages: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, str, str, float], None]] = None,
        auto_sync_dashboard: bool = True
    ) -> str:
        """Execute pipelines and return task_id"""
        task_id = str(uuid.uuid4())[:8]

        # Initialize task state
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "pipelines": pipelines,
            "mode": mode,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "current_pipeline": None,
            "current_stage": None,
            "progress": 0.0,
            "logs": [],
            "outputs": [],
            "error": None,
            "results": {}
        }

        # Start execution in background
        asyncio.create_task(self._execute_task(task_id, pipelines, mode, stages, progress_callback, auto_sync_dashboard))

        return task_id

    async def _execute_task(
        self,
        task_id: str,
        pipelines: List[str],
        mode: str,
        stages: Optional[List[str]],
        progress_callback: Optional[Callable],
        auto_sync_dashboard: bool
    ):
        """Background task execution"""
        task = self.tasks[task_id]

        try:
            total_stages = 0
            pipeline_stages = {}

            # Calculate total stages for progress
            for pid in pipelines:
                p_stages = self.get_stages_for_pipeline(pid, stages)
                pipeline_stages[pid] = p_stages
                total_stages += len(p_stages)

            completed_stages = 0

            for pid in pipelines:
                task["current_pipeline"] = pid
                p_stages = pipeline_stages[pid]

                for stage in p_stages:
                    task["current_stage"] = stage['id']
                    task["progress"] = (completed_stages / total_stages) * 100 if total_stages > 0 else 0

                    # Log stage start
                    log_msg = f"[{pid}] {stage['name']} started"
                    task["logs"].append(log_msg)
                    if progress_callback:
                        progress_callback(task_id, stage['id'], log_msg, task["progress"])

                    # Execute stage
                    cmd = self.build_command(pid, stage, mode)
                    if cmd:
                        result = await self._run_command(cmd, task_id, stage['id'], progress_callback, self.get_pipeline_cwd(pid))
                        task["outputs"].extend(result.get("outputs", []))
                        task["logs"].extend(result.get("logs", []))

                        if result.get("error"):
                            raise RuntimeError(f"Stage {stage['id']} failed: {result['error']}")

                    completed_stages += 1
                    task["progress"] = (completed_stages / total_stages) * 100 if total_stages > 0 else 100

                    log_msg = f"[{pid}] {stage['name']} completed"
                    task["logs"].append(log_msg)
                    if progress_callback:
                        progress_callback(task_id, stage['id'], log_msg, task["progress"])

            # Auto sync dashboard if requested
            if auto_sync_dashboard:
                task["logs"].append("Syncing dashboard data...")
                if progress_callback:
                    progress_callback(task_id, "dashboard_sync", "Syncing dashboard data...", 95)
                await self._sync_dashboard()
                task["logs"].append("Dashboard sync completed")
                if progress_callback:
                    progress_callback(task_id, "dashboard_sync", "Dashboard sync completed", 100)

            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            task["progress"] = 100.0

            # Emit final completion event with pipeline ID
            primary_pipeline = pipelines[0] if pipelines else None
            emit_progress("pipeline", "done",
                          f"Pipeline 执行完成: {', '.join(pipelines)}", percent=100,
                          pipeline_id=primary_pipeline,
                          metrics={"stages_completed": completed_stages, "total_stages": total_stages})

            # Auto-record experiment
            try:
                from services.experiment_records_service import create_experiment
                exp = create_experiment(
                    name=f"Pipeline {primary_pipeline or 'run'} 执行",
                    purpose=f"通过看板执行 pipeline: {', '.join(pipelines)} (模式: {mode})",
                    template="train",
                )
                emit_progress("pipeline", "experiment_created",
                              f"实验文档已创建: {exp.get('experiment_id')}", percent=100,
                              experiment_id=exp.get("experiment_id"))
            except Exception as e:
                emit_progress("pipeline", "experiment_error",
                              f"实验记录失败: {str(e)[:100]}", percent=100)

        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            task["completed_at"] = datetime.now().isoformat()
            task["logs"].append(f"ERROR: {e}")
            if progress_callback:
                progress_callback(task_id, "error", str(e), task["progress"])

    async def _run_command(
        self,
        cmd: List[str],
        task_id: str,
        stage_id: str,
        progress_callback: Optional[Callable],
        cwd: Path
    ) -> Dict[str, Any]:
        """Run a single command and capture output"""
        result = {"outputs": [], "logs": [], "error": None}

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(cwd)
            )

            # Read output line by line for progress
            async for line in proc.stdout:
                line = line.decode('utf-8', errors='replace').strip()
                if line:
                    result["logs"].append(line)
                    # Try to extract progress from output
                    if "epoch" in line.lower() or "%" in line:
                        if progress_callback:
                            progress_callback(task_id, stage_id, line, None)

            await proc.wait()

            if proc.returncode != 0:
                result["error"] = f"Command failed with code {proc.returncode}"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def _sync_dashboard(self):
        """Trigger dashboard data export"""
        # Run export_dashboard_data.py from pipeline-6-cpdv-analysis
        pipeline_cwd = self.get_pipeline_cwd("pipeline_6_cpdv_analysis")
        script_path = pipeline_cwd / "scripts" / "export_dashboard_data.py"
        if not script_path.exists():
            # Fallback
            script_path = CONFIG_DIR / "pipeline-6-cpdv-analysis" / "scripts" / "export_dashboard_data.py"

        cmd = [config.PYTHON_EXE, str(script_path)]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(pipeline_cwd)
        )
        await proc.wait()

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks"""
        return list(self.tasks.values())

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        task = self.tasks.get(task_id)
        if task and task["status"] == "running":
            task["status"] = "cancelled"
            task["error"] = "Cancelled by user"
            task["completed_at"] = datetime.now().isoformat()
            return True
        return False


# Global executor instance
executor = PipelineExecutor()
