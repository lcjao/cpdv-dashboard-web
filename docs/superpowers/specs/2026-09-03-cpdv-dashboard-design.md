# CPDV 多桥梁损伤交互式看板 · 设计文档

**日期**: 2026-09-03
**状态**: Approved
**范围**: 全新项目构建（新建独立文件夹 `cpdv-dashboard-web`）

## 1. 背景与目标

### 1.1 背景

用户已有一个静态 HTML 看板原型（`dashboard_prototype.html` + `dashboard_data.js`），用于展示多桥梁 CPDV（接触点位移变化）损伤监测结果。同时有一个 `cpdv-dashboard` 调度 Skill（SKILL.md），定义了完整的命令表（看板总览、注册桥梁、计算CPDV、预测损伤、多裂缝预测、随机工况分析、对比、训练模型、刷新看板、记录实验），底层调用 `bridge_crack_id` 项目的 Python pipeline。

用户希望构建一个**与AI交互的看板**，参考 `exam-workflow-web`（Next.js 备考教练应用）的 AI 交互模式，将静态看板升级为可交互、可由自然语言驱动的智能看板。

### 1.2 目标

- 展示多桥梁损伤监测数据（CPDV 曲线、多裂缝纵断面、桥梁参数、全局指标）
- 通过自然语言命令驱动 CPDV 计算、损伤预测、多裂缝识别、随机工况分析
- 复用 exam-workflow-web 的 AI 交互架构（LLM 客户端、工具调用、流式响应）
- 底层调用 bridge_crack_id 项目的 Python pipeline（不自己计算 CPDV）
- 兼顾性能（"用不卡的框架"）与功能完整性
- 支持本地运行与服务器部署

### 1.3 成功标准

- 功能完整：命令表所有能力可用
- 性能良好：响应速度快，不卡顿
- 用户满意度高：易于使用，交互体验好

## 2. 技术选型

### 2.1 前端

| 项 | 选型 | 理由 |
|----|------|------|
| 构建工具 | **Vite** | 轻量、启动快、HMR 快，满足"不卡" |
| 框架 | **React 19 + TypeScript** | 复用 exam-workflow-web 代码、组件化 |
| 样式 | **Tailwind CSS v4** | 快速开发、视觉一致 |
| 图表 | **Chart.js (react-chartjs-2)**（CPDV 曲线）+ **Canvas 自绘**（多裂缝纵断面） | 轻量、无需重依赖；纵断面自绘更可控 |
| AI 交互 | 复用 exam-workflow-web 的 `llm-client.ts` 逻辑（移植） | 保持一致的流式 + 工具调用机制 |

### 2.2 后端

| 项 | 选型 | 理由 |
|----|------|------|
| 框架 | **Python FastAPI** | 轻量、异步、高性能 |
| 进程执行 | `subprocess` 调用 bridge_crack_id Python 脚本 | 与 Skill 命令表一致 |
| 数据存储 | JSON 文件（registry.json + 各桥 JSON） | 与现有看板一致，便于交接 |
| 实时推送 | **WebSocket**（训练进度等长任务） | 提供实时反馈 |

### 2.3 通信

- RESTful API：常规数据请求（桥梁列表、详情、分析结果）
- WebSocket：长任务进度（训练模型、批量计算）
- LLM 代理：复用 `/api/llm/proxy` 思路（避免 CORS）

## 3. 系统架构

```
┌───────────────────────────────────────────────┐
│                  前端 (Vite + React)          │
├───────────────────────────────────────────────┤
│  看板 UI  │  AI 对话面板  │  图表组件        │
└───────────────┬───────────────────────────────┘
                │  REST + WebSocket
┌───────────────▼───────────────────────────────┐
│            后端 (Python FastAPI)              │
├───────────────────────────────────────────────┤
│  路由层  →  调度层(scheduler)  →  执行层(exec)│
└───────────────┬───────────────────────────────┘
                │  subprocess (cd CODE_ROOT)
┌───────────────▼───────────────────────────────┐
│        bridge_crack_id Python pipeline        │
└───────────────────────────────────────────────┘
```

## 4. 前端设计

### 4.1 布局（三栏）

```
┌─────────────────────────────────────────────────┐
│                 顶部导航栏                      │
├──────────┬──────────────────────┬──────────────┤
│ 左侧栏    │      中间主区域      │   右侧栏    │
│ (290px)  │      (自适应)        │  (320px)    │
│ 桥梁工况  │ • CPDV 时间序列图    │  AI 对话面板│
│ 列表(可  │ • 多裂缝纵断面图     │  - 命令输入 │
│ 折叠)    │ • 桥梁参数表         │  - 快捷命令 │
│          │                      │  - 对话历史 │
└──────────┴──────────────────────┴──────────────┘
```

### 4.2 组件结构

```
src/
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── BridgeSidebar.tsx      # 桥梁工况列表（左侧）
│   │   └── ChatPanel.tsx          # AI对话（右侧）
│   ├── charts/
│   │   ├── CpdvChart.tsx          # CPDV 曲线（Chart.js）
│   │   └── ProfileChart.tsx       # 多裂缝纵断面（Canvas 自绘）
│   ├── bridge/
│   │   ├── BridgeCard.tsx
│   │   └── ParamTable.tsx
│   └── chat/
│       ├── ChatInput.tsx
│       ├── ChatMessage.tsx
│       └── QuickCommands.tsx
├── lib/
│   ├── llm-client.ts              # 移植自 exam-workflow-web（精简）
│   ├── cpdv-tools.ts              # 桥梁损伤工具定义
│   ├── api-client.ts              # 后端 API 客户端
│   └── types.ts
├── pages/
│   └── Dashboard.tsx
└── styles/globals.css
```

### 4.3 视觉设计

- **配色**：工程蓝主色调（#2f6fed），绿色/琥珀/红色状态指示，深色 AI 对话区（#101826）
- **字体**：Microsoft YaHei / PingFang SC；数据用 Consolas monospace
- **卡片**：圆角、浅阴影、hover 高亮
- **响应式**：宽屏三栏；<1100px 堆叠为单栏

## 5. 后端设计

### 5.1 目录结构

```
backend/
├── main.py               # FastAPI 入口
├── scheduler.py          # 命令解析 → 意图
├── executor.py           # subprocess 执行 pipeline
├── config.py             # 代码库路径、Python 路径等
├── data_loader.py        # JSON 读写
├── routes/
│   ├── bridges.py        # 注册/列表/详情
│   ├── analysis.py       # CPDV/预测/多裂缝/随机工况/对比/训练
│   └── dashboard.py      # 看板数据
├── services/
│   ├── cpdv_service.py
│   ├── predict_service.py
│   ├── multi_crack_service.py
│   ├── random_service.py
│   ├── compare_service.py
│   └── train_service.py
└── data/
    └── registry.json
```

### 5.2 API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/bridges` | 所有桥梁列表 |
| GET | `/api/bridges/{id}` | 单个桥梁详情（含 CPDV、裂缝） |
| POST | `/api/bridges/register` | 注册桥梁 |
| GET | `/api/analysis/cpdv` | 计算 CPDV |
| GET | `/api/analysis/predict` | 单裂缝预测 |
| GET | `/api/analysis/multi-crack` | 多裂缝预测 |
| GET | `/api/analysis/random` | 随机工况分析 |
| GET | `/api/analysis/compare` | 双桥对比 |
| POST | `/api/analysis/train` | 训练模型（长任务，WS 推送进度） |
| GET | `/api/dashboard` | 读取看板数据 |
| POST | `/api/dashboard/refresh` | 刷新看板 |
| WS | `/ws/status` | 长任务进度推送 |

### 5.3 调度层（scheduler.py）

命令映射（与 SKILL.md 命令表一致）：

```python
COMMANDS = {
    "看板总览": "overview",
    "注册桥梁": "register",
    "列出桥梁": "list",
    "计算CPDV": "cpdv",
    "预测损伤": "predict",
    "多裂缝预测": "multi_crack",
    "随机工况分析": "random_condition",
    "对比": "compare",
    "训练模型": "train",
    "刷新看板": "refresh",
    "记录实验": "record",
}
```

### 5.4 执行层（executor.py）

调用 bridge_crack_id 脚本，工作目录必须为 CODE_ROOT：

```python
def run(cmd_args, cwd=CODE_ROOT, timeout=None):
    """执行子进程，采集 stdout/stderr"""
    result = subprocess.run(
        [PYTHON_EXE, *cmd_args],
        cwd=cwd,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:])
    return result.stdout
```

## 6. AI 交互设计

### 6.1 命令解析

用户输入自然语言命令 → LLM 工具调用 → 后端执行 → 结果回填。

### 6.2 系统提示词

基于 SKILL.md 构建系统提示词，**明确告知 AI 不自己计算 CPDV**，只负责解析命令并调用工具，所有数值来自底层 pipeline 真实输出。汇报规范：数值带单位；预测必附模型标签 + MAE + 达标判断。

### 6.3 工具定义（cpdv-tools.ts）

复用 exam-workflow-web 的 `ToolDefinition` 模式：

```typescript
const tools: ToolDefinition[] = [
  { name: 'cb_list_bridges',        desc: '列出所有桥梁', params: {} },
  { name: 'cb_register_bridge',    desc: '注册桥梁', ... },
  { name: 'cb_cpdv_compute',       desc: '计算CPDV', ... },
  { name: 'cb_predict_single',     desc: '单裂缝预测', ... },
  { name: 'cb_predict_multi',      desc: '多裂缝预测', ... },
  { name: 'cb_random_condition',   desc: '随机工况分析', ... },
  { name: 'cb_compare_bridges',    desc: '双桥对比', ... },
  { name: 'cb_train_model',        desc: '训练模型', ... },
  { name: 'cb_refresh_dashboard',  desc: '刷新看板', ... },
];
```

### 6.4 交互流程

1. 用户在命令输入框输入「计算CPDV 桥梁01 depth=0.2」
2. LLM 解析意图，识别为 `cb_cpdv_compute` 工具
3. 前端调用后端 API 异步执行计算（长任务走 WebSocket 推进度）
4. 计算完成 → 后端返回结果（图表路径、峰值统计、JSON）
5. AI 生成文字汇报，前端格式化显示
6. 看板图表实时更新为最新结果

## 7. 数据模型

### 7.1 registry.json

```json
{
  "bridges": [
    {
      "id": "bridge_01",
      "name": "桥梁01",
      "params": { "mv": 5000, "kv": 100000, "cv": 5000, "V": 2,
                  "L": 30, "E": 3.0e10, "I": 0.1, "m": 400,
                  "EL": 30, "depth": 0.8, "width": 0.25,
                  "n_modes": 3, "kexi": 0.1, "deltat": 0.005,
                  "road_type": "b" },
      "status": "healthy",
      "last_updated": "2026-09-03T..."
    }
  ]
}
```

### 7.2 看板数据（兼容 dashboard_data.js 结构）

`/api/dashboard` 返回 `{ meta, bridges[] }`：
- `meta`: model, checkpoint, metrics{pos_mae, depth_mae, recall, precision, f1, n_matched, n_gt, n_pred}, test_size
- `bridges[]`: id, name, params{...}, true_cracks[], pred_cracks[], cpdv[], cpdv_len, n_true/n_pred/n_hit/n_miss/n_false

## 8. 实施阶段（phases）

### Phase 1：项目脚手架 + 静态数据展示
- 初始化 Vite + React + TS + Tailwind 项目
- 实现三栏布局（Header / BridgeSidebar / 中间图表 / ChatPanel）
- 读取 `/api/dashboard`（先用现有 dashboard_data.js 数据渲染）
- 实现 CpdvChart、ProfileChart、ParamTable、BridgeCard

### Phase 2：后端 API + Python pipeline 接线
- FastAPI 骨架 + 配置
- 实现 scheduler + executor（调用 bridge_crack_id）
- 实现分类服务：cpdv / predict / multi_crack / random / compare / train
- 实现 dashboard 读取 / refresh

### Phase 3：AI 对话集成
- 移植 llm-client.ts（精简）+ 配置界面
- 定义 cpdv-tools.ts 工具
- 系统提示词（基于 SKILL.md）
- 命令 → 工具 → 后端执行 → 结果回填闭环

### Phase 4：长任务 + 打磨
- WebSocket 训练进度推送
- 错误处理、边界情况、响应式优化
- 视觉打磨、性能优化

## 9. 关键约束（Hard Blocks）

- **AI 绝不自己计算 CPDV**：所有数值必须来自底层 pipeline 真实输出
- 工作目录必须是 CODE_ROOT（`cd CODE_ROOT` 后执行）
- 参数注入方式是"动态改写 yaml"，不是命令行参数（04_cpdv_analysis.py 仅覆盖 bridge_length）
- 单位换算：km/h→m/s(÷3.6)、kN→N、GPa→Pa、t→kg、mm→m
- 合理性校验：越界必须向用户确认后再执行
- 训练模型必须**先报告预计耗时并确认**
- 汇报规范：数值带单位；预测必附模型 + MAE + 达标判断

## 10. 未决事项 / 备注

- 默认模型：`outputs/models/cracknet.json`（BP）、`multi_crack_dual_retrained.pth`（多裂缝，唯一达标）
- 环境已知问题：`D:\python\Python310\python.exe` 的 matplotlib 与 numpy 2.x 有 `_ARRAY_API` 冲突，绘图脚本可能报错（纯计算不含 `--plot` 不受影响）
- 后端需在部署机器上配置 bridge_crack_id 代码库路径与 Python 路径（config.py）
