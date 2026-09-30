# CPDV 完整时间序列计算与看板展示 — 设计

> 日期：2026-09-07 ｜ 状态：待用户审阅 ｜ 关联功能域：[[04_损伤分析]]（流程 C1 计算 CPDV）

## 1. 目标

用户需求：**计算 CPDV 信号的完整时间序列数据，并展示在看板上**。

当前缺口：pipeline 的 signal 模式 `plot_cpdv_signals()` **已经在算**完整时间序列 `(t, cpdv_dict)`，
但只把它画成 PNG 图、**不输出数值**——数据"算得出来但拿不出来"，看板无法渲染。

## 2. 已确认的需求语义

- **每条 CPDV 信号曲线 = 一个（位置, 深度）组合**：`analyze_damage(pos, depth)` 在 pos 位置放
  一个深度为 depth 的裂缝，计算该损伤工况下的整条 CPDV 信号响应（默认参数下 ~3001 点）。
- **本次范围 = 单深度 × 多位置**：指定 1 个深度 + N 个位置（distances），生成 N 条曲线
  （如 `depth=0.2, distances=5,10,15` → 位置5/10/15m 各一条）。与 pipeline 现有 signal 模式语义一致。
- **展示形态 = 看板总览直接多曲线叠加**：不同位置不同颜色 + 图例标注位置。

## 3. 现状盘点（约束）

| 项 | 现状 | 影响 |
|----|------|------|
| pipeline 计算 | `04_cpdv_analysis.py::plot_cpdv_signals()` 返回 `(t, cpdv_dict)`，只存图 | 数据在子进程内，未传出 |
| pipeline 脚本 | 用户已要求"恢复成原来的计算"，`04_cpdv_analysis.py` 已 `git restore` 至 HEAD | **不宜再改脚本本体** |
| 后端调用 | `cpdv_service.compute_cpdv` 现走 `--mode peak`（G18 修复：signal 不打印可解析行） | peak 只出峰值行，非完整序列 |
| executor | `executor.run(["-c", ...])` 已有先例（`verify_import` 就是这么干的） | 可内联计算，零改脚本 |
| 数据格式 | `Bridge.cpdv: number[]`（单条数组）；legacy 桥 400~5000 点 | 需向后兼容单条 + 新增多曲线 |
| 前端渲染 | `CpdvChart` 用归一化 0~1 索引（`i/(len-1)`）画单条线 | 不依赖真实 t，只需信号数组 |
| 看板时长 | 实测 peak 模式 3 位置 10.6s | signal 同量级，可接受（<300s 超时） |

## 4. 方案选型

### 方案 A（采用）：内联计算 + stdout JSON，零改 pipeline 脚本

1. **计算**：`cpdv_service.compute_cpdv()` 改用 `executor.run(["-c", _INLINE_CODE])`，
   内联 Python 片段（与 `verify_import` 同款姿势）：
   - 读临时 yaml 参数（`write_tmp_yaml` 注入桥参数，沿用现有机制）
   - `sys.path` 指向 `CODE_ROOT`，`from simulation.system_iteration import BridgeVehicleSystem`
   - 复刻 `plot_cpdv_signals()` 逻辑：`analyze_damage(pos, depth)` × N 位置 → `calculate_cpdv()`
   - **打印一行** `CPDV_TS: {json}` 到 stdout（含 `positions` 与每位置信号数组），
     同时**打印** `pos=X, depth=Y, peak=Z` 行（峰值 = `max(|signal|)`）保持 `_RE_DATA` 兼容
2. **解析**：`_parse_cpdv_stdout()` 增加 `_RE_TS` 正则抓 `CPDV_TS:` 行 → `parsed.time_series`
3. **存储**：计算成功后将 `[{pos, signal: [...]}]` 写入 registry 桥条目新增字段
   `cpdv_signals`（`data_loader` 新增 `save_bridge_cpdv_signals(bridge_id, data)`）
4. **下发**：`load_dashboard_merged()` / `merge_legacy_bridges()` 的桥结构携带 `cpdv_signals`
   （registry 有则下发；legacy 桥无此字段则前端回退单条 `cpdv`）
5. **前端**：
   - `types.ts`：`Bridge` 加可选 `cpdv_signals?: { pos: number; signal: number[] }[]`
   - `CpdvChart.tsx`：有 `cpdv_signals` → 每条位置一条 dataset（调色板循环 + 图例"位置 Xm"）；
     否则回退现有单条 `cpdv`；否则空态占位

权衡：⚠️ 3001×N 点 JSON 走 stdout（N=3~5 → ~100KB，可接受）；✅ 零改脚本、链路最短、复用 executor/registry 机制。

### 方案 B（备选）：新增 `04_cpdv_export.py` 输出 JSON 文件
数据落文件 `outputs/cpdv/*.json`，后端读文件。优点：不占 stdout；缺点：新增脚本与
`04_cpdv_analysis.py` 逻辑重复（需维护两份），且引入文件清理问题。**不采用**。

### 方案 C（否决）：改原脚本 signal 模式加打印
违背用户"脚本恢复成原样"要求。**否决**。

## 5. 数据流（端到端）

```
AI/前端「计算CPDV 桥梁01 depth=0.2 distances=5,10,15」
  → GET /api/analysis/cpdv?bridge=bridge_01&depth=0.2&distances=5,10,15
  → cpdv_service.compute_cpdv():
      verify_import()
      _resolve_bridge_params()           # registry 桥参数
      write_tmp_yaml(sim_overrides)      # 注入临时 yaml
      executor.run(["-c", inline_code])  # 内联计算，零改脚本
      _parse_cpdv_stdout()               # rows(峰值行) + time_series(CPDV_TS 行)
  → 成功：data_loader.save_bridge_cpdv_signals(bridge_01, [...] )  # 写回 registry
  → 返回 { stdout, parsed: { rows, time_series, signal_depth, row_count } }
AI 汇报峰值 → 用户「刷新看板」
  → GET /api/dashboard → merged 桥结构带 cpdv_signals → CpdvChart 多曲线渲染
```

## 6. 数据结构变更

### registry.json 桥条目（新增字段，向后兼容）
```json
{
  "id": "bridge_01",
  "name": "桥梁01",
  "params": { "...": "..." },
  "cpdv_signals": [
    { "pos": 5.0,  "signal": [0.0, 0.0002, "...", 3001 点] },
    { "pos": 10.0, "signal": ["...", 3001 点] },
    { "pos": 15.0, "signal": ["...", 3001 点] }
  ]
}
```

### /api/dashboard 桥视图（新增字段）
```json
{
  "id": "bridge_01",
  "cpdv": [],                     // 保持现状（注册桥占位空）
  "cpdv_signals": [               // 新增：多位置完整信号
    { "pos": 5.0,  "signal": [ ... ] },
    { "pos": 10.0, "signal": [ ... ] },
    { "pos": 15.0, "signal": [ ... ] }
  ]
}
```

### 前端

```ts
// types.ts
export interface CpdvSignalSeries { pos: number; signal: number[] }
export interface Bridge {
  // ... 现有字段
  cpdv_signals?: CpdvSignalSeries[];  // 新增，可选；缺省回退 cpdv 单条
}
```

## 7. 变更文件清单

| 文件 | 变更 |
|------|------|
| `backend/services/cpdv_service.py` | `compute_cpdv` 加内联计算路径；`_parse_cpdv_stdout` 加 `_RE_TS` 解析 |
| `backend/data_loader.py` | 新增 `save_bridge_cpdv_signals()`；`load_dashboard_merged`/`merge_legacy_bridges` 携带 `cpdv_signals` |
| `frontend/src/lib/types.ts` | `Bridge` 加可选 `cpdv_signals` |
| `frontend/src/components/charts/CpdvChart.tsx` | 多曲线渲染（调色板 + 图例）+ 回退单条/空态 |
| `04_损伤分析/评审.md`（obsidian） | 补 §4.5 或新 §4.6 记录本次功能 |

**不改**：`04_cpdv_analysis.py`（恢复原样）、executor.py、routes/analysis.py 签名。

## 8. 验收标准

1. `GET /api/analysis/cpdv?bridge=bridge_01&depth=0.2&distances=5,10,15` → 200，
   `parsed.rows` 非空（6 行峰值）、`parsed.time_series.positions == [5,10,15]`、
   每条 signal 长度 ≈3001、`parsed.signal_depth == 0.2`
2. `registry.json` 中 bridge_01 出现 `cpdv_signals`（3 条序列）且重启后端后仍在（持久化）
3. 刷新看板 → 桥梁01 CPDV 图显示 3 条曲线，图例标注"位置 5m / 10m / 15m"，颜色区分
4. legacy 桥仍显示原有单曲线（无 `cpdv_signals` → 回退 `cpdv`），不受影响
5. `verify` 保持 `{"ok":true,"msg":"OK"}`；`_tmp_configs` 无残留
6. 前端 `tsc -b` / build 通过；无类型错误、无 `as any`

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| stdout 3001×N 点 JSON 较大 | N 默认 ≤5 → ~100KB，executor 内存捕获无压力 |
| 内联代码与脚本逻辑重复（analyze_damage 调用序列） | 内联片段短小（~20 行），并注释指向脚本来源；若未来脚本需改语义，再评估方案 B |
| registry.json 体积增长（3001×N 浮点/桥） | 本地看板规模（≤10 桥）可接受；为大桥数据可后续加降采样字段 |
| LLM 汇报链路 | `parsed.time_series` 不喂 LLM（过大），只喂 `rows` 峰值；`time_series` 仅供看板存储/渲染 |