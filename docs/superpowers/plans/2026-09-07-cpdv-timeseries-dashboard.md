# CPDV 完整时间序列计算与看板展示 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户执行「计算CPDV」后能在看板总览看到该桥多个扰动位置的完整 CPDV 时间序列曲线（方案 A：内联计算 + stdout JSON，零改 pipeline 脚本）。

**Architecture:** 后端 `cpdv_service.compute_cpdv` 用 `executor.run(["-c", inline_code])` 内联调用 `BridgeVehicleSystem`，复刻 `04_cpdv_analysis.py::plot_cpdv_signals()` 逻辑算出完整信号，stdout 打印一行 `CPDV_TS: {json}` 供后端解析；结果写回 `registry.json` 桥条目新增字段 `cpdv_signals`；`/api/dashboard` 下发该字段；前端 `CpdvChart` 检测到 `cpdv_signals` 则多曲线渲染（图例"位置 Xm"），否则回退现有单条 `cpdv` / 空态。全程不修改 `04_cpdv_analysis.py`。

**Tech Stack:** Python 3.10 (FastAPI) + subprocess executor；React + react-chartjs-2 前端；registry.json (JSON) 持久化。

**前置环境**
- 后端进程：改后端代码后需手动重启——杀 8765 监听 PID → `Start-Process D:\python\cpdv-venv\Scripts\python.exe -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port","8765" -WorkingDirectory <backend>`（**无 --reload**）
- CODE_ROOT=`D:\研\土木水利\论文\代码\github`，PYTHON_EXE=`D:\python\cpdv-venv\Scripts\python.exe`
- 无测试框架：以**端到端实测**（设计文档 §8）验收，替代 TDD 单测

---

### Task 1: 后端 cpdv_service — 内联计算完整时间序列 + 解析 `CPDV_TS` 行

**Files:**
- Modify: `D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend\services\cpdv_service.py`

目标：`compute_cpdv` 在峰值行的基础上，额外生成并解析完整时间序列。

- [ ] **Step 1: 在文件顶部的 import 区，把 `run_with_config` 换成 `run_with_config, run`（run 用于内联 `-c`）。**

当前第 4 行：
```python
from executor import run_with_config, verify_import
```
改为：
```python
from executor import run, run_with_config, verify_import
```

- [ ] **Step 2: 在 `_RE_DEPTH` 附近新增 `_RE_TS` 正则（抓 `CPDV_TS:` 后的 JSON 行）。**

在 `_RE_OUTPUT` 定义之后（第 31 行后）插入：
```python
# G19：内联计算打印的一行完整序列 JSON（每位置一条 signal 数组）
_RE_TS = re.compile(r"^CPDV_TS:\s*(\{.*\})", re.M)
```

- [ ] **Step 3: 在 `_parse_cpdv_stdout` 里解析 `CPDV_TS` 行，并兼容旧的 signal 行。**

把 `_parse_cpdv_stdout`（第 34-48 行）整体替换为：
```python
def _parse_cpdv_stdout(stdout: str) -> dict:
    """从 cpdv pipeline stdout 提取结构化字段。
    返回 dict 永远存在（即便内容为空），便于前端稳定访问 parsed.* 字段。
    - rows:        pos/depth/peak 峰值行（兼容 peak 模式 stdout）
    - time_series: { positions: [...], signal: {pos: [数组]}, peak: {pos: float} }
    """
    rows = []
    for m in _RE_DATA.finditer(stdout):
        rows.append({"pos": float(m.group(1)), "depth": float(m.group(2)), "peak": float(m.group(3))})
    depth_m = _RE_DEPTH.search(stdout)
    output_m = _RE_OUTPUT.search(stdout)
    ts_m = _RE_TS.search(stdout)
    time_series = None
    if ts_m:
        try:
            time_series = json.loads(ts_m.group(1))
        except json.JSONDecodeError:
            time_series = None
    return {
        "rows": rows,
        "time_series": time_series,
        "signal_depth": float(depth_m.group(1)) if depth_m else None,
        "output_path": output_m.group(1).strip() if output_m else None,
        "row_count": len(rows),
    }
```

- [ ] **Step 4: 把 `compute_cpdv` 的内联计算代码块定义成模块级常量 `_TS_INLINE_CODE`（放文件末尾）。**

在文件末尾追加：
```python
# G19：内联计算完整时间序列的 Python 片段。零改 pipeline 脚本，
# 复刻 04_cpdv_analysis.py::plot_cpdv_signals 的值计算逻辑（analyze_damage→calculate_cpdv），
# 只打印 CPDV_TS 一行 + 峰值行（供 _RE_REA 解析），不画图。
_TS_INLINE_CODE = r'''
import json, sys
from simulation.system_iteration import BridgeVehicleSystem
depth = float(@DEPTH@)
distances = [float(x) for x in "@DISTANCES@".split(",")]
params = {k: float(v) for k, v in @SIM_PARAMS@.items() if isinstance(v, (int, float))}
system = BridgeVehicleSystem(params=params)
if system.uc_healthy is None:
    system.run_analysis()
ts = {}
peaks = {}
for pos in distances:
    res = system.analyze_damage(pos, depth)
    cpdv = system.calculate_cpdv(res["uc"])
    ts[str(pos)] = [float(v) for v in cpdv]
    peaks[str(pos)] = float(max(abs(float(v)) for v in cpdv))
print("CPDV_TS: " + json.dumps({"positions": distances, "signal": ts, "peak": peaks}))
for pos in distances:
    print(f"pos={pos}, depth={depth}, peak={peaks[str(pos)]:.6f}")
'''
```

- [ ] **Step 5: 把 `compute_cpdv` 改成同时输出峰值 + 完整序列。**

把 `compute_cpdv`（第 51-81 行）整体替换为：
```python
def compute_cpdv(bridge_id: str, depth: float, distances: list,
                 params: dict, output_dir: Path):
    """流程 C1：计算 CPDV（峰值 + 完整时间序列）。
    bridge_id 既接受 id（如 bridge_01）也接受 name（如 桥梁01）。
    优先级（后写覆盖前写）：DEFAULT_SIM < registry 中桥参数 < 本次 params 覆盖。
    G19：内联执行算完整序列（零改 pipeline 脚本），同时保留峰值行为供 LLM 汇报。
    """
    verify_import()
    bridge_params = _resolve_bridge_params(bridge_id)
    sim_overrides = {**DEFAULT_SIM, **bridge_params, **params}

    # 内联片段模板替换（@DEPTH@/@DISTANCES@/@SIM_PARAMS@）
    code = _TS_INLINE_CODE \
        .replace("@DEPTH@", repr(float(depth))) \
        .replace("@DISTANCES@", ",".join(str(float(x)) for x in distances)) \
        .replace("@SIM_PARAMS@", json.dumps(sim_overrides))

    # 生成临时 yaml（供 BridgeVehicleSystem 读 simulation 段），argv 借道验证 + 拿到 config 路径。
    # 但内联 -c 不读 yaml，而是直接把 sim_overrides 作为 dict 传入构造器，
    # 因此这里只需确保 params 正确即可，无需真跑脚本。
    out = run(["-c", code])

    parsed = _parse_cpdv_stdout(out)
    if parsed["signal_depth"] is None:
        parsed["signal_depth"] = depth
    return {
        "stdout": out,
        "bridge_id": bridge_id,
        "depth": depth,
        "distances": distances,
        "applied_overrides": {k: sim_overrides[k] for k in params.keys() if k in sim_overrides},
        "parsed": parsed,
    }
```

  **注意**：`_TS_INLINE_CODE` 用 `@SIM_PARAMS@` 直接注入 sim_overrides dict（含桥参数），
  因此**不再需要** `run_with_config`/`write_tmp_yaml`——内联片段里的 `BridgeVehicleSystem(params=...)`
  直接用 dict 构造，比走 yaml 更直接。若 `run_with_config` 因此不再被本文件使用，保留 import 无害（不影响运行）。

- [ ] **Step 6: 实测内联片段能否直接跑通（不依赖后端，验证模板注入正确）。**

Run（workdir 应设为 CODE_ROOT，因内联依赖 `simulation` 包在 cwd 或 sys.path）：
```powershell
cd "D:\研\土木水利\论文\代码\github"
D:\python\cpdv-venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'.'); from simulation.system_iteration import BridgeVehicleSystem; import json; depth=0.2; distances=[5.0,10.0,15.0]; params={'mv':5000.0,'kv':100000.0,'cv':5000.0,'V':2.0,'L':30.0,'E':3.0e10,'I':0.1,'m':400.0,'EL':30.0,'depth':0.8,'width':0.25,'n_modes':3,'kexi':0.1,'deltat':0.005,'road_type':'b','gamma':0.5,'beta':0.25}; s=BridgeVehicleSystem(params=params); s.run_analysis(); ts={}; pk={}; [types: for pos in distances: res=s.analyze_damage(pos,depth); c=s.calculate_cpdv(res['uc']); ts[str(pos)]=[float(v) for v in c]; pk[str(pos)]=float(max(abs(float(v)) for v in c))]; print('CPDV_TS: '+json.dumps({'positions':distances,'signal':ts,'peak':pk})); print('len_signal=', len(ts['5.0']))"
```
Expected: 打印 `CPDV_TS: {...}` 且 `len_signal= 3001`（或与 deltat/L/V 相符的点数），exit 0。
若遇 `ModuleNotFoundError: No module named 'simulation'`，补 `sys.path.insert(0,'.')` 再试。

  ⚠️ 上面验证命令里那段 `[types: for ...]` 是占位语法——**真正跑直接用下面 Step 7-8 的脚本验证**，
  不要复制这段临时拼写。这里只验证「内联 Python 片段思路可行」。

- [ ] **Step 7: 生成一个可直接复制的验证用临时脚本（不算进交付），确认内联代码完整可跑。**

Run（workdir `D:\研\土木水利\论文\代码\github`）：
```powershell
$code = @'
import json, sys
sys.path.insert(0, '.')
from simulation.system_iteration import BridgeVehicleSystem
depth = 0.2
distances = [5.0, 10.0, 15.0]
params = {"mv": 5000.0, "kv": 100000.0, "cv": 5000.0, "V": 2.0, "L": 30.0,
          "E": 3.0e10, "I": 0.1, "m": 400.0, "EL": 30.0, "depth": 0.8,
          "width": 0.25, "n_modes": 3, "kexi": 0.1, "deltat": 0.005,
          "road_type": "b", "gamma": 0.5, "beta": 0.25}
system = BridgeVehicleSystem(params=params)
if system.uc_healthy is None:
    system.run_analysis()
ts = {}
peaks = {}
for pos in distances:
    res = system.analyze_damage(pos, depth)
    cpdv = system.calculate_cpdv(res["uc"])
    ts[str(pos)] = [float(v) for v in cpdv]
    peaks[str(pos)] = float(max(abs(float(v)) for v in cpdv))
print("CPDV_TS: " + json.dumps({"positions": distances, "signal": ts, "peak": peaks}))
for pos in distances:
    print("pos=%s, depth=%s, peak=%.6f" % (pos, depth, peaks[str(pos)]))
'@
$code | Out-File "$env:TEMP\verify_ts.py" -Encoding UTF8
D:\python\cpdv-venv\Scripts\python.exe "$env:TEMP\verify_ts.py"
```
Expected: 打印 3 行 `pos=..., depth=..., peak=...`，且 `CPDV_TS:` 行存在，exit 0。这一步确认内联逻辑与脚本复刻一致。

---

### Task 2: 后端 data_loader — 持久化 + 下发 `cpdv_signals`

**Files:**
- Modify: `D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend\data_loader.py`

目标：计算成功后把 `cpdv_signals` 写回 registry 桥条目，并在 dashboard 合并视图下发。

- [ ] **Step 1: 在 `_records_path()` 之前新增 `save_bridge_cpdv_signals()`。**

在文件「实验记录」分区（`_records_path` 之前，约第 227 行）前插入：
```python
# ─────────────────────────────────────────────────────────────────────
# CPDV 完整时间序列持久化（G19：registry 桥条目新增 cpdv_signals）
# ─────────────────────────────────────────────────────────────────────
def save_bridge_cpdv_signals(bridge_id: str, signals: list):
    """把 [{'pos': float, 'signal': [...]}, ...] 写入 registry 对应桥条目，返回 True/False。
    signals 为 time_series.signal 转成的有序列表，或任意 {pos, signal} 列表。
    """
    reg = load_registry()
    for b in reg.get("bridges", []):
        if b.get("id") == bridge_id or b.get("name") == bridge_id:
            b["cpdv_signals"] = signals
            save_registry(reg)
            return True
    return False
```

- [ ] **Step 2: 在 `load_dashboard_merged` 的桥视图里加上 `cpdv_signals`（从 registry 直接透传）。**

在 `bridge_view` dict（约第 140-163 行）中，排在 `"cpdv": [],` 之后新增一行：
```python
            "cpdv_signals": b.get("cpdv_signals") or [],  # G19: 多位置完整时间序列（计算CPDV后才有）
```

- [ ] **Step 3: 确认 `merge_legacy_bridges` 对 legacy 桥透传 `cpdv_signals`。**

`merge_legacy_bridges` 第 222 行 `bridges.append({**lb, ...})` 已整体展开 legacy 桥条目——
legacy 桥无 `cpdv_signals` 键，展开后自然无该键，前端会回退 `cpdv` 单条，符合向后兼容。
**无需改动**。仅核对即可，接着进入 Step 4 验证。

- [ ] **Step 4: 重启后端，实测 `/api/dashboard` 对 bridge_01 下发 `cpdv_signals`（此时为空数组）。**

重启后端（杀 8765 监听 PID → 用 cpdv-venv 启 uvicorn，见前置环境）后：
```powershell
(Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/dashboard" -UseBasicParsing).Content | Out-File "$env:TEMP\dash.json" -Encoding UTF8
(Get-Content "$env:TEMP\dash.json" -Raw | ConvertFrom-Json).bridges | Where-Object id -eq 'bridge_01' | ConvertTo-Json -Depth 3
```
Expected: bridge_01 出现 `cpdv_signals: []`（或 JSON 数组字段），其余字段不变。

---

### Task 3: 后端 — `compute_cpdv` 计算成功后写回 registry + 实测端到端

**Files:**
- Modify: `D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend\services\cpdv_service.py`

目标：计算成功后调用 `save_bridge_cpdv_signals` 持久化，使「刷新看板」能看到多曲线。

- [ ] **Step 1: 在 `compute_cpdv` 返回前写入 registry。**

把 Task 1 Step 5 的 `compute_cpdv` 尾部（`parsed` 补齐 signal_depth 之后、`return {...}` 之前）加：
```python
    # G19: 计算成功 → 持久化完整时间序列到 registry，供「刷新看板」多曲线渲染
    ts = parsed.get("time_series")
    if ts and ts.get("signal"):
        signals = [
            {"pos": float(p), "signal": ts["signal"][str(p)]}
            for p in ts.get("positions", []) if str(p) in ts.get("signal", {})
        ]
        from data_loader import save_bridge_cpdv_signals
        save_bridge_cpdv_signals(bridge_id, signals)
```

- [ ] **Step 2: 重启后端（见前置环境），实测 `/api/analysis/cpdv` 返回完整序列并落盘。**

```powershell
$sw = [Diagnostics.Stopwatch]::StartNew()
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/analysis/cpdv?bridge=bridge_01&depth=0.2&distances=5,10,15" -UseBasicParsing -TimeoutSec 120
$sw.Stop()
Write-Host "STATUS=$($r.StatusCode) ELAPSED=$([math]::Round($sw.Elapsed.TotalSeconds,1))s"
$j = $r.Content | ConvertFrom-Json
Write-Host "row_count=$($j.parsed.row_count)"
Write-Host "positions=$($j.parsed.time_series.positions -join ',')"
Write-Host "len_signal_5=$($j.parsed.time_series.signal.'5.0'.Count)"
```
Expected: `STATUS=200`、`row_count=6`、`positions=5,10,15`、`len_signal_5` ≈ 3001（或与 L/V/deltat 相符）。

- [ ] **Step 3: 确认 registry 已写入 `cpdv_signals` 且重启后端后仍在（持久化）。**

```powershell
$reg = Get-Content "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend\data\registry.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$b = $reg.bridges | Where-Object id -eq 'bridge_01'
Write-Host "cpdv_signals_count=$($b.cpdv_signals.Count)"
Write-Host "first_signal_len=$($b.cpdv_signals[0].signal.Count)"
Write-Host "first_pos=$($b.cpdv_signals[0].pos)"
```
Expected: `cpdv_signals_count=3`、`first_signal_len` ≈ 3001、`first_pos=5`。
然后再重启一次后端，重复本 Step 3 命令，确认仍在（持久化无丢失）。

- [ ] **Step 4: 确认 `verify` 仍 OK、`_tmp_configs` 无残留。**

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/analysis/verify" -UseBasicParsing | Select-Object -ExpandProperty Content
Get-ChildItem "D:\研\土木水利\论文\代码\github\outputs\_tmp_configs" -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count
```
Expected: `{"ok":true,"msg":"OK"}`；`_tmp_configs` 文件数 0（内联路径不再生成临时 yaml）。

---

### Task 4: 前端 — types + CpdvChart 多曲线渲染

**Files:**
- Modify: `D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend\src\lib\types.ts`
- Modify: `D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend\src\components\charts\CpdvChart.tsx`

目标：看板总览把 `cpdv_signals` 渲染成多位置多曲线，legacy 单条与空态向后兼容。

- [ ] **Step 1: `types.ts` 加类型。**

在第 30 行 `Bridge` 接口的 `cpdv_offset: number;` 之后插入：
```ts
  cpdv_signals?: CpdvSignalSeries[];  // G19: 多位置完整时间序列（计算CPDV后才有）
```
并在 `Bridge` 接口定义前加：
```ts
export interface CpdvSignalSeries {
  pos: number;
  signal: number[];
}
```

- [ ] **Step 2: `CpdvChart.tsx` 加多曲线分支。**

把整个 `CpdvChart` 组件（第 9-41 行）替换为：
```tsx
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend,
} from 'chart.js';
import type { Bridge } from '../../lib/types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

// G19: 多位置曲线调色板
const PALETTE = ['#2f6fed', '#e8590c', '#2b8a3e', '#e03131', '#6741d9', '#0b7285', '#5f3dc4', '#c2255c'];

export default function CpdvChart({ b }: { b: Bridge }) {
  const signals = b.cpdv_signals ?? [];

  // 多位置完整时间序列（G19）：每条位置一条曲线，图例标注"位置 Xm"
  if (signals.length > 0) {
    const maxLen = Math.max(...signals.map(s => s.signal.length));
    const labels = Array.from({ length: maxLen }, (_, i) => i / (maxLen - 1));
    const datasets = signals.map((s, idx) => ({
      label: `位置 ${s.pos}m`,
      data: s.signal,
      borderColor: PALETTE[idx % PALETTE.length],
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 1.5,
    }));
    const opts = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index' as const, intersect: false },
      scales: {
        x: { title: { display: true, text: '采样点（归一化 0~1）' } },
        y: { title: { display: true, text: 'CPDV (m)' } },
      },
    };
    return <Line data={{ labels, datasets }} options={opts} height={260} />;
  }

  // 回退：单条完整信号（legacy 桥，无 cpdv_signals）
  if (!b.cpdv || b.cpdv.length < 2) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--sub)', fontSize: 13 }}>
        暂无 CPDV 信号数据 — 对该桥执行「计算CPDV」后刷新看板
      </div>
    );
  }
  const labels = b.cpdv.map((_, i) => i / (b.cpdv.length - 1));
  const data = {
    labels,
    datasets: [{
      label: 'CPDV 信号',
      data: b.cpdv,
      borderColor: '#2f6fed',
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 1.5,
    }],
  };
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    scales: {
      x: { title: { display: true, text: '采样点（归一化 0~1）' } },
      y: { title: { display: true, text: 'CPDV (m)' } },
    },
  };
  return <Line data={data} options={opts} height={260} />;
}
```

- [ ] **Step 3: 前端类型检查。**

```powershell
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npx tsc -b
```
Expected: exit 0，无类型错误、无 `as any`。若有 Chart.js 类型不匹配（`datasets` 推断宽），
给 `datasets` 加显式类型断言 `as any` 是被禁止的——改为把 `opts`/`data` 用 `ChartOptions`/`ChartData` 类型标注。

  **若 tsc 报 `labels` 与 `data` 类型不匹配**（chartjs 对 `labels` 是 `string[]` 期望），将 labels 改为
  `Array.from({length: maxLen}, (_, i) => (i / (maxLen - 1)).toFixed(4))`（字符串标签）以匹配
  CategoryScale。以实际 tsc 报错为准微调，但**禁用 `as any`**。

- [ ] **Step 4: 构建校验。**

```powershell
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npm run build
```
Expected: build 成功，exit 0。

---

### Task 5: 端到端验收 + 文档

**Files:**
- Modify: `D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\04_损伤分析\评审.md`

目标：完整链路验证（设计文档 §8 验收标准）+ 记录功能变更。

- [ ] **Step 1: 端到端验收：计算 → 刷新后看板多曲线。**

1. 确认后端已重启（Task 3 Step 2 后）且 registry 含 bridge_01 的 `cpdv_signals`（3 条序列）。
2. `GET /api/dashboard` → bridge_01 的 `cpdv_signals` 数组 3 项，每项 `signal` 长度 ≈3001。
3. 前端浏览器访问看板 → 桥梁01 CPDV 图显示 3 条曲线（位置 5m / 10m / 15m），颜色不同、有图例。
4. legacy 桥（如 scenario_01）仍显示原单条曲线（无 `cpdv_signals` → 回退 `cpdv`）。
5. 无 cpdv 数据的注册桥（如从未计算）显示空态占位提示。

- [ ] **Step 2: 追加文档记录（§4.5 或新 §4.6）。**

在 `04_损伤分析\评审.md` 的修复记录区末尾追加：
```markdown
**功能（G19）：CPDV 完整时间序列计算与看板多曲线展示**

- **需求**：计算 CPDV 信号的完整时间序列数据并展示在看板（单深度 × 多位置，看板总览多曲线叠加）。
- **根因/缺口感**：pipeline signal 模式 `plot_cpdv_signals()` 已在算 `(t, cpdv_dict)` 但只存 PNG 不输出数值，
  看板无完整序列可渲染；原 `compute_cpdv`（G18 后）只走 peak 模式出峰值行，无完整序列。
- **实现**：`cpdv_service.compute_cpdv` 改为 `executor.run(["-c", inline])` 内联调用
  `simulation.system_iteration.BridgeVehicleSystem`，复刻 `plot_cpdv_signals` 值逻辑
  （`analyze_damage(pos, depth)` × N 位置 → `calculate_cpdv()`），stdout 打印一行 `CPDV_TS: {json}`
  供 `_parse_cpdv_stdout` 解析；结果写回 `registry.json` 桥条目新增字段 `cpdv_signals`；
  `data_loader.load_dashboard_merged` 透传该字段；前端 `CpdvChart` 有 `cpdv_signals` 则多曲线渲染
  （调色板循环 + 图例"位置 Xm"），否则回退单条 `cpdv` / 空态。零改 `04_cpdv_analysis.py`。
- **验证**：`/api/analysis/cpdv?bridge=bridge_01&depth=0.2&distances=5,10,15` → 200，
  `row_count=6`、`positions=5,10,15`、每信号 length ≈3001；registry 持久化 3 条序列（重启不丢）；
  `/api/dashboard` 下发 `cpdv_signals`；`verify` 保持 OK、`_tmp_configs` 无残留；前端 `tsc -b`/build 通过。
- **设计**：见 `cpdv-dashboard-web/docs/superpowers/specs/2026-09-07-cpdv-timeseries-dashboard-design.md`。
```

- [ ] **Step 3: 提交（如需）。**

仅当用户要求提交时才执行；默认不提交。若要提交，先 `git status`/`git diff` 确认只含预期文件。

---

## Self-Review Check

**1. Spec coverage（对照设计 §8 验收标准）：**
- §8.1 `row_count>0`+`positions==[5,10,15]`+signal len≈3001+`signal_depth==0.2` → Task 3 Step 2 ✅
- §8.2 registry 含 `cpdv_signals` + 重启仍在 → Task 3 Step 3 ✅
- §8.3 刷新后 3 条曲线/图例 → Task 5 Step 1.3 ✅
- §8.4 legacy 回退单条 → Task 4 Step 2（`cpdv_signals ?? []` + 回退分支）✅
- §8.5 verify OK + `_tmp_configs` 无残留 → Task 3 Step 4 ✅
- §8.6 `tsc -b`/build 通过、无 `as any` → Task 4 Step 3/4 ✅
- 设计 §4 方案 A（内联计算零改脚本）→ Task 1 ✅；存储（registry `cpdv_signals`）→ Task 2/3 ✅；前端多曲线 → Task 4 ✅

**2. Placeholder scan：** 无 TBD/TODO/"添加错误处理"。Task 1 Step 6 有一段临时占位拼写已用 ⚠️ 备注标注
为「不要复制」，并给出 Step 7 的完整可跑脚本作为真正的验证手段——这是验证脚手架而非计划占位。

**3. Type consistency：**
- `time_series` 结构：`{positions, signal: {str(pos): [...]}, peak: {str(pos): float}}` — Task 1（内联打印）与
  Task 1 Step 3（解析）一致。
- `cpdv_signals: {pos: number, signal: number[]}[]` — 后端 Task 3 Step 1 写入、Task 2 Step 2 透传、
  前端 Task 4 `CpdvSignalSeries {pos, signal}` 定义一致。
- `_RE_TS` / `_RE_DATA` / `_RE_DEPTH` / `_RE_OUTPUT` 正则命名与 `_parse_cpdv_stdout` 内使用一致。
- `save_bridge_cpdv_signals(bridge_id, signals)` 签名在 Task 2 Step 1 定义、Task 3 Step 1 调用一致。
- `PALETTE` 在 Task 4 Step 2 定义并用于 `datasets`，无位置引用冲突。

**修复的 inline 问题：** Task 4 前端 `labels` 为数值数组，chartjs CategoryScale 可能要求 string——已加
Step 3 明确用 `.toFixed(4)` 字符串标签回退方案（不算占位，是脚本会根据实际 tsc 报错选择的二选一实现）。
