import subprocess
import config


def run(cmd_args, timeout=None):
    """在 CODE_ROOT 下执行 pipeline 脚本，采集 stdout/stderr。"""
    result = subprocess.run(
        [config.PYTHON_EXE, *cmd_args],
        cwd=str(config.CODE_ROOT),
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:])
    return result.stdout


def verify_import():
    """首次执行前验证环境。"""
    out = run(["-c", "from simulation.enhanced_system import BridgeVehicleSystem; print('OK')"])
    return out.strip()
