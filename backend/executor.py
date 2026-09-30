import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
import yaml
import config

# 默认子进程超时（G10）：300s = 5 分钟。
# 短任务（cpdv 预测 < 1 分钟）会自然更快返回；长任务（train 5 epochs ≈ 20s、
# 长 train 5 分钟一轮）超过会被 kill 并抛 TimeoutError。
DEFAULT_TIMEOUT = 300

# Windows 防止 subprocess.run(timeout=...) hang 在 pipe 不关闭。
# CREATE_NO_WINDOW 让子进程不创建 console，kill 后 stdio pipe 立刻关闭。
#（曾验证：subprocess.run + capture_output + timeout 在 c10.dll 已加载的
# Python 子进程上，kill 后 read 永久阻塞——必须显式 CREATE_NO_WINDOW）
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# 子进程 stdout 强制 UTF-8：Windows GBK 管道会让 ✓/✗ 等字符 print 时
# UnicodeEncodeError 崩溃（04_train_multi_crack.py 末尾的达标打印即如此）。
# 过滤掉 os.environ 中的 None 值，避免 subprocess 报错
_ENV = {**{k: v for k, v in os.environ.items() if v is not None}, "PYTHONIOENCODING": "utf-8"}

# 临时 yaml 注入目录（绝对路径，纯 ASCII，任意 cwd 均可被脚本 os.path.join 解析）。
# 旧实现建在 CODE_ROOT/outputs/_tmp_configs（CODE_ROOT 已废弃）；现改到后端数据目录下。
_TMP_YAML_DIR = config.TMP_CONFIG_DIR
_TMP_YAML_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_cwd(cmd: str) -> Path:
    """命令对应的可运行根目录（algorithm-code 下的 pipeline 子目录）。

    旧 CODE_ROOT(github 单一根) 已废弃：legacy 命令与其内联 -c 推理代码都
    依赖 cwd 里可 import 到 simulation/model/visualization 等包。补齐后每个
    pipeline 子目录自包含，按命令定位到对应子目录作 cwd。
    """
    return config.pipeline_cwd(cmd)


def run(cmd_args, timeout=DEFAULT_TIMEOUT, cmd: str = "cpdv"):
    """在命令对应的 pipeline 目录下执行 pipeline 脚本，采集 stdout/stderr。

    G10：默认 5 分钟超时；显式传 None 表示不超时（仅在内部分支用）。
    超时会抛 TimeoutError，建议上层 try/except 后给用户友好提示。
    cmd: 命令名（cpdv/predict/random/train/evaluate/multi_crack/pinn/dashboard），
         决定子进程 cwd。默认 cpdv。
    """
    cwd = _resolve_cwd(cmd)
    proc = subprocess.Popen(
        [config.PYTHON_EXE, *cmd_args],
        cwd=str(cwd),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        env=_ENV, creationflags=_CREATE_NO_WINDOW,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        raise TimeoutError(
            f"子进程超时（>{timeout}s）: {' '.join(cmd_args[:3])}..."
        )
    if proc.returncode != 0:
        raise RuntimeError(stderr[-3000:])
    return stdout


def run_streaming(cmd_args, on_line=None, timeout=DEFAULT_TIMEOUT, abort_check=None,
                  cmd: str = "cpdv"):
    """流式执行 — 每读出一行回调 on_line(line)，最后返回 (完整 stdout, returncode)。

    适用场景：长时训练任务需要实时进度（→ ws.emit），不能等全跑完才报。
    G10：默认 5 分钟超时，到点 kill 进程（不等它自然结束）。
    返回 stdout 即使 returncode 非 0——上层自己决定是否 raise。

    abort_check: 可选的 callable，定期调用检查是否应中断（如 request.is_disconnected()）。
                 若返回 True，则 kill 子进程并返回已捕获输出。
    cmd: 命令名，决定子进程 cwd（见 run）。
    """
    cwd = _resolve_cwd(cmd)
    proc = subprocess.Popen(
        [config.PYTHON_EXE, *cmd_args],
        cwd=str(cwd),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        env=_ENV, creationflags=_CREATE_NO_WINDOW,
    )
    captured = []
    stop_event = threading.Event()

    def reader():
        """后台读线程：行级读 stdout 直到 EOF 或 stop_event 触发。"""
        try:
            while not stop_event.is_set():
                line = proc.stdout.readline()
                if not line:
                    break
                captured.append(line)
                if on_line is not None:
                    try:
                        on_line(line.rstrip("\n"))
                    except Exception:
                        pass
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    try:
        if timeout is None:
            # 不超时（仅在显式传 None 时）
            while proc.poll() is None:
                if abort_check and abort_check():
                    proc.kill()
                    captured.append("\n[aborted by client disconnect]\n")
                    break
                time.sleep(0.1)
        else:
            deadline = time.time() + timeout
            while proc.poll() is None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    proc.kill()
                    captured.append(f"\n[timeout after {timeout}s, killed]\n")
                    break
                if abort_check and abort_check():
                    proc.kill()
                    captured.append("\n[aborted by client disconnect]\n")
                    break
                time.sleep(min(0.1, remaining))
        # 给 reader 一个 flush 窗口把残留的输出读完
        stop_event.set()
        reader_thread.join(timeout=2)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return "".join(captured), proc.returncode


def write_tmp_yaml(sim_overrides: dict) -> Path:
    """生成临时 yaml（含 simulation 段），返回 yaml 文件路径。

    sim_overrides 中任意 key 会覆盖默认值。yaml 落在 TMP_CONFIG_DIR（绝对路径），
    pipeline 脚本用 os.path.join(project_root, args.config) 解析——绝对路径时
    join 会直接返回该绝对路径，故任意 cwd 下都能被找到。
    """
    base = {
        # 来自 config/params.yaml 的默认值（保持与仓库一致）
        "simulation": {
            "mv": 5000, "kv": 100000, "cv": 5000, "V": 2, "L": 30,
            "E": 3.0e10, "I": 0.1, "m": 400, "EL": 30, "depth": 0.8,
            "width": 0.25, "n_modes": 3, "kexi": 0.1, "deltat": 0.005,
            "road_type": "b",
            "gamma": 0.5, "beta": 0.25,
        }
    }
    if sim_overrides:
        base["simulation"].update({k: float(v) for k, v in sim_overrides.items()
                                   if isinstance(v, (int, float))})
    fd, name = tempfile.mkstemp(prefix="cpdv_", suffix=".yaml", dir=str(_TMP_YAML_DIR))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        yaml.safe_dump(base, f, allow_unicode=True, sort_keys=False)
    return Path(name)


def run_with_config(cmd_args, sim_overrides: dict = None, timeout=None, cmd: str = "cpdv"):
    """执行 pipeline 脚本，自动注入 simulation 段 yaml。
    cmd_args 形如 ["scripts/04_cpdv_analysis.py", "--mode", "signal", ...]，
    函数会替换或追加 --config 指向新生成的临时 yaml。
    cmd: 命令名，决定子进程 cwd。默认 cpdv。
    """
    sim_overrides = sim_overrides or {}
    tmp_yaml = write_tmp_yaml(sim_overrides)
    # 若 cmd_args 已含 --config，则替换；否则追加
    new_argv = []
    replaced = False
    it = iter(cmd_args)
    for tok in it:
        if tok == "--config":
            new_argv += [tok, str(tmp_yaml)]
            next(it, None)  # 跳过旧 value
            replaced = True
        else:
            new_argv.append(tok)
    if not replaced:
        new_argv += ["--config", str(tmp_yaml)]
    try:
        return run(new_argv, timeout=timeout, cmd=cmd)
    finally:
        try:
            tmp_yaml.unlink(missing_ok=True)
        except Exception:
            pass


def verify_import(cmd: str = "cpdv"):
    """首次执行前验证环境。

    在命令对应的 pipeline 目录下验证 simulation.system_iteration 可导入。
    旧仓库以 system_iteration.py 为权威实现（system_coupling.py 已弃用）。
    """
    out = run(["-c", "from simulation.system_iteration import BridgeVehicleSystem; print('OK')"],
              cmd=cmd)
    return out.strip()
