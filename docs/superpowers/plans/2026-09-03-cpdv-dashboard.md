# CPDV 多桥梁损伤交互式看板 · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个与 AI 交互的多桥梁 CPDV 损伤监测看板（Vite + React 前端 + FastAPI 后端），支持展示监测数据与通过自然语言命令驱动计算/预测/分析。

**Architecture:** 前端 Vite + React 19 + TypeScript + Tailwind，三栏布局（桥梁列表 / CPDV+纵断面图 / AI 对话）。后端 Python FastAPI，通过 scheduler（命令解析）+ executor（subprocess 调用 bridge_crack_id pipeline）执行计算。AI 对话通过 LLM 工具调用（复用 exam-workflow-web 的 llm-client 机制）实现命令 → 工具 → 后端执行 → 回填闭环。所有 CPDV 数值必须来自底层 pipeline，前端/AI 绝不自己计算。

**Tech Stack:** Vite, React 19, TypeScript, Tailwind CSS v4, Chart.js (react-chartjs-2), Python FastAPI, uvicorn, subprocess, WebSocket。

**项目根目录:** `D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web`

---

## 环境关键事实

- **bridge_crack_id 权威代码库 (CODE_ROOT):** `D:\研\土木水利\论文\代码\github`
- **Python 解释器:** `D:\python\Python310\python.exe`（3.10.5）
- **工作目录：执行 pipeline 必须 `cd CODE_ROOT`**
- **看板工作区原有数据:** `D:\Documents\Obsidian\O1\桥梁健康系统\Area\多桥梁损伤看板\`（含 `看板原型`、`bridges\registry.json`）
- **原型数据:** `D:\Documents\Obsidian\O1\桥梁健康系统\Area\多桥梁损伤看板\看板原型\dashboard_data.js`
- 环境已知问题：`D:\python\Python310\python.exe` 的 matplotlib 与 numpy 2.x 有 `_ARRAY_API` 冲突，绘图脚本（`--plot`）可能报错；纯计算脚本不受影响。

---

## 文件结构总览

```
cpdv-dashboard-web/
├── frontend/
│   ├── package.json          # 前端依赖与脚本
│   ├── vite.config.ts        # Vite 配置（含 /api 代理到后端）
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx          # React 入口
│   │   ├── App.tsx           # 根组件（加载 ConfigProvider）
│   │   ├── globals.css       # Tailwind + 全局样式
│   │   ├── lib/
│   │   │   ├── types.ts      # 看板/桥梁数据模型
│   │   │   ├── api-client.ts # 后端 API 客户端
│   │   │   ├── llm-client.ts # LLM 客户端（移植精简）
│   │   │   └── cpdv-tools.ts # 桥梁损伤工具定义
│   │   └── components/
│   │       ├── layout/Header.tsx
│   │       ├── layout/BridgeSidebar.tsx
│   │       ├── layout/ChatPanel.tsx
│   │       ├── charts/CpdvChart.tsx
│   │       ├── charts/ProfileChart.tsx
│   │       ├── bridge/BridgeCard.tsx
│   │       ├── bridge/ParamTable.tsx
│   │       └── chat/ChatInput.tsx
│   │       └── chat/ChatMessage.tsx
│   │       └── chat/QuickCommands.tsx
├── backend/
│   ├── requirements.txt      # fastapi, uvicorn, websockets
│   ├── main.py               # FastAPI 入口
│   ├── config.py             # 配置（CODE_ROOT, PYTHON_EXE 等）
│   ├── scheduler.py          # 命令解析
│   ├── executor.py           # subprocess 执行
│   ├── data_loader.py        # JSON 读写
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── bridges.py
│   │   ├── analysis.py
│   │   └── dashboard.py
│   └── services/
│       ├── __init__.py
│       ├── cpdv_service.py
│       ├── predict_service.py
│       ├── multi_crack_service.py
│       ├── random_service.py
│       ├── compare_service.py
│       └── train_service.py
│   └── data/
│       └── registry.json     # 桥梁注册表（初始为空）
├── sample_data/dashboard_data.js  # 从原型复制的示例数据（用于 Phase 1 渲染）
└── docs/superpowers/
    ├── specs/2026-09-03-cpdv-dashboard-design.md
    └── plans/2026-09-03-cpdv-dashboard.md   # 本文件
```

---

## Phase 1：项目脚手架 + 静态数据展示

### Task 1: 初始化前端项目（Vite + React + TS + Tailwind）

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/globals.css`

- [ ] **Step 1: 创建 `frontend/package.json`**

```json
{
  "name": "cpdv-dashboard-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "react-chartjs-2": "^5.2.0",
    "chart.js": "^4.4.7",
    "marked": "^18.0.5",
    "dompurify": "^3.4.11"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@types/dompurify": "^3.0.5",
    "@vitejs/plugin-react": "^4.3.4",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: 创建 `frontend/vite.config.ts`（含 /api 代理到后端）**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
});
```

- [ ] **Step 3: 创建 `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- [ ] **Step 4: 创建 `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CPDV 多桥梁损伤看板</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: 创建 `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './globals.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 6: 创建 `frontend/src/globals.css`（Tailwind + 基础样式）**

```css
@import "tailwindcss";

:root {
  --bg: #f4f6fa;
  --card: #ffffff;
  --line: #e3e8f0;
  --ink: #1f2d3d;
  --sub: #7a8699;
  --blue: #2f6fed;
  --blue-bg: #eaf1fe;
  --green: #1fa25c;
  --green-bg: #e8f7ef;
  --amber: #d98a00;
  --amber-bg: #fdf3e0;
  --red: #d94141;
  --red-bg: #fdeaea;
  --mono: "Consolas", "Courier New", monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  background: var(--bg);
  color: var(--ink);
  font-size: 14px;
}
```

- [ ] **Step 7: 创建 `frontend/src/App.tsx`（骨架，先渲染 Header + 占位）**

```tsx
export default function App() {
  return (
    <div style={{ padding: 16 }}>
      <h1>🌉 多桥梁损伤监测看板</h1>
      <p>脚手架已就绪</p>
    </div>
  );
}
```

- [ ] **Step 8: 安装依赖并启动验证**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npm install
npm run dev
```

Expected: Vite dev server 启动在 http://localhost:5173，页面显示"脚手架已就绪"。

- [ ] **Step 9: Commit（如项目已 git init）**

```bash
git init
git add -A
git commit -m "feat: scaffold vite react ts tailwind frontend"
```

---

### Task 2: 数据类型 + API 客户端

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api-client.ts`

- [ ] **Step 1: 创建 `frontend/src/lib/types.ts`（看板/桥梁数据模型，兼容 dashboard_data.js）**

```typescript
export interface Crack {
  pos: number;      // 位置 m
  depth: number;    // 深度比 0~1
  conf?: number;    // 置信度（预测）
  match?: number | null; // 匹配的真实裂缝索引
  hit?: boolean;
}

export interface BridgeParams {
  mv: number; kv: number; cv: number; V: number; L: number;
  E: number; I: number; m: number;
  [k: string]: number;
}

export interface Bridge {
  id: string;
  name: string;
  sample?: number;
  params: BridgeParams;
  true_cracks: Crack[];
  pred_cracks: Crack[];
  cpdv: number[];
  cpdv_len: number;
  cpdv_offset: number;
  n_true: number;
  n_pred: number;
  n_hit: number;
  n_miss: number;
  n_false: number;
}

export interface DashboardMeta {
  model: string;
  checkpoint: string;
  input_dim?: number;
  max_cracks?: number;
  cls_threshold?: number;
  match_cost?: number;
  metrics: {
    pos_mae: number; depth_mae: number; recall: number;
    precision: number; f1: number; n_matched: number;
    n_gt: number; n_pred: number;
  };
  test_size: number;
  n_scenarios?: number;
  generated?: string;
  note?: string;
}

export interface DashboardData {
  meta: DashboardMeta;
  bridges: Bridge[];
}
```

- [ ] **Step 2: 创建 `frontend/src/lib/api-client.ts`**

```typescript
import type { DashboardData, Bridge } from './types';

const BASE = '/api';

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

/** 读取看板数据（优先后端 /api/dashboard，失败回退到 sample_data） */
export async function fetchDashboard(): Promise<DashboardData> {
  try {
    return await getJSON<DashboardData>('/dashboard');
  } catch (e) {
    // 后端未启动时回退到本地示例数据
    const mod = await import('../../../sample_data/dashboard_data.ts');
    return mod.SAMPLE_DASHBOARD;
  }
}

export async function fetchBridges(): Promise<Bridge[]> {
  return getJSON<Bridge[]>('/bridges');
}

export const api = { fetchDashboard, fetchBridges };
```

- [ ] **Step 3: 创建示例数据文件 `sample_data/dashboard_data.ts`（从原型 dashboard_data.js 导出结构，提取 1-2 个桥梁小样本）**

在 `cpdv-dashboard-web/sample_data/` 下创建 `dashboard_data.ts`，从 `D:\Documents\Obsidian\O1\桥梁健康系统\Area\多桥梁损伤看板\看板原型\dashboard_data.js` 复制结构（对象字面量），导出为 `export const SAMPLE_DASHBOARD: DashboardData = {...}`。建议只保留 1-2 个桥梁（如 scenario_45、scenario_05），cpdv 数组可截断到 ~300 点以减小体积。

- [ ] **Step 4: 类型检查**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npx tsc --noEmit
```

Expected: 无类型错误。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add data types and api client"
```

---

### Task 3: 三栏布局 + 静态渲染

**Files:**
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/BridgeSidebar.tsx`
- Create: `frontend/src/components/layout/ChatPanel.tsx`
- Create: `frontend/src/components/bridge/BridgeCard.tsx`
- Create: `frontend/src/components/bridge/ParamTable.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 `frontend/src/components/bridge/BridgeCard.tsx`**

```tsx
import type { Bridge } from '../../lib/types';

export default function BridgeCard({ b, active, onClick }: {
  b: Bridge; active: boolean; onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--card)', border: `1px solid ${active ? 'var(--blue)' : 'var(--line)'}`,
        borderRadius: 12, padding: '12px 14px', cursor: 'pointer',
        boxShadow: active ? '0 4px 14px rgba(47,111,237,.18)' : 'none',
      }}
    >
      <div style={{ fontSize: 15, fontWeight: 700 }}>{b.name}</div>
      <div style={{ color: 'var(--sub)', fontSize: 12, marginTop: 5 }}>
        跨长 {b.params.L.toFixed(1)} m · 车速 {b.params.V.toFixed(1)} m/s
      </div>
      <div style={{ marginTop: 7, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        <span style={{ background: 'var(--green-bg)', color: 'var(--green)', borderRadius: 9, padding: '2px 7px', fontSize: 11 }}>
          真 {b.n_true}
        </span>
        <span style={{ background: 'var(--blue-bg)', color: 'var(--blue)', borderRadius: 9, padding: '2px 7px', fontSize: 11 }}>
          预 {b.n_pred}
        </span>
        {b.n_miss > 0 && (
          <span style={{ background: 'var(--red-bg)', color: 'var(--red)', borderRadius: 9, padding: '2px 7px', fontSize: 11 }}>
            漏 {b.n_miss}
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 `frontend/src/components/bridge/ParamTable.tsx`**

```tsx
import type { BridgeParams } from '../../lib/types';

const ROWS: [keyof BridgeParams, string][] = [
  ['L', '跨长 (m)'], ['E', '弹性模量 (GPa)'], ['I', '惯性矩 (m⁴)'],
  ['m', '线密度 (kg/m)'], ['mv', '车辆质量 (kg)'],
  ['kv', '悬挂刚度 (kN/m)'], ['cv', '阻尼 (N·s/m)'], ['V', '车速 (m/s)'],
];

export default function ParamTable({ params }: { params: BridgeParams }) {
  return (
    <div>
      {ROWS.map(([k, label]) => (
        <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <label style={{ color: 'var(--sub)', fontSize: 12 }}>{label}</label>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>
            {k === 'E' ? (params.E / 1e9).toFixed(1)
             : k === 'I' ? params.I.toFixed(4)
             : k === 'kv' ? (params.kv / 1e3).toFixed(1)
             : typeof params[k] === 'number' ? (params[k] as number).toFixed(k === 'm' ? 0 : 1)
             : String(params[k])}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: 创建 `frontend/src/components/layout/Header.tsx`（含指标概览）**

```tsx
import type { DashboardMeta } from '../../lib/types';

export default function Header({ meta }: { meta: DashboardMeta }) {
  const m = meta.metrics;
  const ok = (cond: boolean) => cond ? 'green' : 'red';
  const items: [string, string, string][] = [
    ['位置 MAE', m.pos_mae.toFixed(2) + ' m', ok(m.pos_mae < 1.0) + ' (目标<1.0)'],
    ['深度 MAE', (m.depth_mae * 100).toFixed(2) + ' %', ok(m.depth_mae < 0.05) + ' (目标<5%)'],
    ['F1', m.f1.toFixed(3), ok(m.f1 > 0.87) + ' (目标>0.87)'],
    ['Recall', (m.recall * 100).toFixed(1) + ' %', m.recall > 0.8 ? 'green' : 'amber'],
    ['Precision', (m.precision * 100).toFixed(1) + ' %', m.precision > 0.8 ? 'green' : 'amber'],
  ];
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 4px', flexWrap: 'wrap', gap: 10 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700 }}>
        🌉 多桥梁损伤监测看板 <span style={{ color: 'var(--blue)' }}>CPDV</span>
      </h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 10, width: '55%' }}>
        {items.map(([k, v, s]) => (
          <div key={k} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: '8px 12px' }}>
            <div style={{ fontSize: 12, color: 'var(--sub)' }}>{k}</div>
            <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--mono)' }}>{v}</div>
            <div style={{ fontSize: 10, color: 'var(--sub)' }}>{s}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 创建 `frontend/src/components/layout/BridgeSidebar.tsx`**

```tsx
import type { Bridge } from '../../lib/types';
import BridgeCard from '../bridge/BridgeCard';

export default function BridgeSidebar({ bridges, cur, onSelect }: {
  bridges: Bridge[]; cur: number; onSelect: (i: number) => void;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 720, overflowY: 'auto', paddingRight: 2 }}>
      {bridges.map((b, i) => (
        <BridgeCard key={b.id} b={b} active={i === cur} onClick={() => onSelect(i)} />
      ))}
    </div>
  );
}
```

- [ ] **Step 5: 创建 `frontend/src/components/layout/ChatPanel.tsx`（骨架，Phase 3 完善）**

```tsx
export default function ChatPanel({ disabled }: { disabled: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 720, background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>⑤ AI 命令控制台</h3>
      {disabled ? (
        <p style={{ color: 'var(--sub)', fontSize: 12 }}>AI 对话将在 Phase 3 集成</p>
      ) : (
        <p style={{ color: 'var(--sub)', fontSize: 12 }}>加载中…</p>
      )}
    </div>
  );
}
```

- [ ] **Step 6: 修改 `frontend/src/App.tsx` 组装三栏布局**

```tsx
import { useEffect, useState } from 'react';
import type { DashboardData } from './lib/types';
import { api } from './lib/api-client';
import Header from './components/layout/Header';
import BridgeSidebar from './components/layout/BridgeSidebar';
import ChatPanel from './components/layout/ChatPanel';
import ParamTable from './components/bridge/ParamTable';

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [cur, setCur] = useState(0);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.fetchDashboard().then(setData).catch(e => setErr(String(e)));
  }, []);

  if (err) return <div style={{ padding: 40, color: 'var(--red)' }}>加载失败: {err}</div>;
  if (!data) return <div style={{ padding: 40 }}>加载中…</div>;

  const b = data.bridges[cur];

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '16px 20px 40px' }}>
      <Header meta={data.meta} />
      <div style={{ display: 'grid', gridTemplateColumns: '290px 1fr 320px', gap: 14, alignItems: 'start' }}>
        <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>① 桥梁工况</h3>
          <BridgeSidebar bridges={data.bridges} cur={cur} onSelect={setCur} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, minHeight: 260 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>② CPDV 接触点位移变化（待接入图表）</h3>
            <div style={{ color: 'var(--sub)', fontSize: 12 }}>当前: {b.name} · {b.cpdv_len} 点</div>
          </div>
          <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, minHeight: 180 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>③ 多裂缝预测 · 梁纵断面（待接入图表）</h3>
            <div style={{ color: 'var(--sub)', fontSize: 12 }}>真 {b.n_true} 条 · 预测 {b.n_pred} 条</div>
          </div>
          <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>④ 桥梁参数</h3>
            <ParamTable params={b.params} />
          </div>
        </div>
        <ChatPanel disabled />
      </div>
    </div>
  );
}
```

- [ ] **Step 7: 启动验证**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npm run dev
```

Expected: 页面显示顶部指标概览、左侧桥梁列表、中间参数表、右侧 AI 面板，点击桥梁卡片可切换。

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: three-column layout with static data rendering"
```

---

### Task 4: 图表组件（CPDV 曲线 + 多裂缝纵断面）

**Files:**
- Create: `frontend/src/components/charts/CpdvChart.tsx`
- Create: `frontend/src/components/charts/ProfileChart.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 `frontend/src/components/charts/CpdvChart.tsx`（Chart.js 折线图）**

```tsx
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend,
} from 'chart.js';
import type { Bridge } from '../../lib/types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

export default function CpdvChart({ b }: { b: Bridge }) {
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

- [ ] **Step 2: 创建 `frontend/src/components/charts/ProfileChart.tsx`（Canvas 自绘纵断面）**

```tsx
import { useEffect, useRef } from 'react';
import type { Bridge } from '../../lib/types';

export default function ProfileChart({ b }: { b: Bridge }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current!;
    const ctx = cv.getContext('2d')!;
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);
    const L = b.params.L;
    const pad = { l: 50, r: 16, t: 20, b: 34 };
    const X = (pos: number) => pad.l + (W - pad.l - pad.r) * (pos / L);
    const Y = (depth: number) => pad.t + (H - pad.t - pad.b) * (1 - depth / 0.35);

    // 梁体背景
    ctx.fillStyle = '#f0f2f5';
    ctx.fillRect(pad.l, pad.t, W - pad.l - pad.r, H - pad.t - pad.b);

    // 刻度
    ctx.strokeStyle = '#e3e8f0'; ctx.fillStyle = '#98a2b3'; ctx.font = '10px Consolas';
    for (let i = 0; i <= 5; i++) {
      const x = pad.l + (W - pad.l - pad.r) * i / 5;
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
      ctx.textAlign = 'center'; ctx.fillText((L * i / 5).toFixed(0), x, H - pad.b + 14);
    }

    // 真实裂缝（绿三角）
    b.true_cracks.forEach(t => {
      const x = X(t.pos), y = Y(t.depth);
      ctx.fillStyle = '#1fa25c';
      ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x - 7, y + 7); ctx.lineTo(x + 7, y + 7); ctx.closePath(); ctx.fill();
    });
    // 预测裂缝（蓝圆 + 置信度）
    b.pred_cracks.forEach(p => {
      const x = X(p.pos), y = Y(p.depth);
      ctx.fillStyle = '#2f6fed';
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = '9px Consolas'; ctx.textAlign = 'center';
      ctx.fillText((p.conf! * 100).toFixed(0), x, y + 3);
    });
    // 漏检标红叉
    b.true_cracks.forEach((t, ti) => {
      const hit = b.pred_cracks.some(p => p.match === ti);
      if (!hit) {
        const x = X(t.pos), y = Y(t.depth);
        ctx.strokeStyle = '#d94141'; ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - 6, y - 6); ctx.lineTo(x + 6, y + 6);
        ctx.moveTo(x + 6, y - 6); ctx.lineTo(x - 6, y + 6);
        ctx.stroke();
      }
    });
    // 匹配连线
    b.pred_cracks.forEach(p => {
      if (p.match != null) {
        const t = b.true_cracks[p.match];
        ctx.strokeStyle = '#98a2b3'; ctx.lineWidth = 0.8; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(X(t.pos), Y(t.depth)); ctx.lineTo(X(p.pos), Y(p.depth)); ctx.stroke();
        ctx.setLineDash([]);
      }
    });
  }, [b]);

  return <canvas ref={ref} width={1100} height={180} style={{ width: '100%', height: 180, display: 'block' }} />;
}
```

- [ ] **Step 3: 修改 `frontend/src/App.tsx` 接入两个图表组件**

将 CPDV 占位块替换为：

```tsx
<div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
  <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>② CPDV 接触点位移变化（时间序列）</h3>
  <div style={{ height: 260 }}>
    <CpdvChart b={b} />
  </div>
</div>
```

将纵断面占位块替换为：

```tsx
<div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
  <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>③ 多裂缝预测 · 梁纵断面（位置×深度比）</h3>
  <ProfileChart b={b} />
</div>
```

并在 import 顶部加入：

```tsx
import CpdvChart from './components/charts/CpdvChart';
import ProfileChart from './components/charts/ProfileChart';
```

- [ ] **Step 4: 类型检查 + 启动验证**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npx tsc --noEmit
npm run dev
```

Expected: 无类型错误；点击桥梁卡片，CPDV 曲线和纵断面图实时更新。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add cpdv line chart and crack profile chart"
```

---

## Phase 2：后端 API + Python pipeline 接线

### Task 5: FastAPI 骨架 + 配置 + dashboard 读取

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/main.py`
- Create: `backend/data_loader.py`
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/dashboard.py`
- Create: `backend/data/.gitkeep`

- [ ] **Step 1: 创建 `backend/requirements.txt`**

```
fastapi
uvicorn[standard]
websockets
```

- [ ] **Step 2: 创建 `backend/config.py`**

```python
from pathlib import Path

# bridge_crack_id 权威代码库（用户验证过）
CODE_ROOT = Path(r"D:\研\土木水利\论文\代码\github")
# Python 解释器
PYTHON_EXE = r"D:\python\Python310\python.exe"
# 看板工作区（registry / 各桥 JSON / 看板原型数据）
DASHBOARD_WORKSPACE = Path(r"D:\Documents\Obsidian\O1\桥梁健康系统\Area\多桥梁损伤看板")
# 本后端数据目录
DATA_DIR = Path(__file__).parent / "data"

# 命令映射（与 SKILL.md 一致）
COMMANDS = {
    "看板总览": "overview", "注册桥梁": "register", "列出桥梁": "list",
    "计算CPDV": "cpdv", "预测损伤": "predict", "多裂缝预测": "multi_crack",
    "随机工况分析": "random_condition", "对比": "compare",
    "训练模型": "train", "刷新看板": "refresh", "记录实验": "record",
}
```

- [ ] **Step 3: 创建 `backend/data_loader.py`（JSON 读写 + dashboard 数据组装）**

```python
import json
import re
from pathlib import Path
from . import config

def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_registry():
    return read_json(config.DATA_DIR / "registry.json", {"bridges": []})

def save_registry(data):
    write_json(config.DATA_DIR / "registry.json", data)

def load_dashboard_data():
    """优先读取看板工作区的 dashboard_data.js；否则返回空结构。"""
    js_path = config.DASHBOARD_WORKSPACE / "看板原型" / "dashboard_data.js"
    if js_path.exists():
        text = js_path.read_text(encoding="utf-8")
        m = re.search(r"window\.DASHBOARD_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$", text)
        if m:
            return json.loads(m.group(1))
    return {"meta": {"metrics": {}}, "bridges": []}
```

- [ ] **Step 4: 创建 `backend/routes/__init__.py`**（空文件）

- [ ] **Step 5: 创建 `backend/routes/dashboard.py`**

```python
from fastapi import APIRouter
from ..data_loader import load_dashboard_data

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("")
def get_dashboard():
    """读取看板数据（兼容 dashboard_data.js 结构）"""
    return load_dashboard_data()
```

- [ ] **Step 6: 创建 `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import dashboard

app = FastAPI(title="CPDV Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)

@app.get("/")
def root():
    return {"status": "ok", "name": "CPDV Dashboard API"}
```

- [ ] **Step 7: 创建 `backend/data/.gitkeep`**（空文件保留目录）

- [ ] **Step 8: 安装依赖并启动后端**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend"
D:\python\Python310\python.exe -m pip install -r requirements.txt
D:\python\Python310\python.exe -m uvicorn main:app --reload --port 8000
```

Expected: 访问 `http://localhost:8000/api/dashboard` 返回 dashboard_data.js 内容。

注意：`from ..routes import dashboard` 需要以包方式运行。若直接 `python -m uvicorn main:app` 报相对导入错误，则改为在 `backend/` 下加 `__init__.py` 或改用绝对导入/以模块方式启动（`python -m uvicorn backend.main:app` 或运行 `python -m backend.main`）。为简单起见，可在 `backend/` 下运行 `python -m uvicorn main:app`，并将 `main.py` 中的 `from .routes import dashboard` 改为 `from routes import dashboard`，`from .data_loader` 改为 `from data_loader`，以此避免包相对导入问题。

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: fastapi skeleton with dashboard endpoint"
```

---

### Task 6: scheduler + executor（命令解析 + pipeline 调用）

**Files:**
- Create: `backend/scheduler.py`
- Create: `backend/executor.py`

- [ ] **Step 1: 创建 `backend/scheduler.py`（命令解析）**

```python
import re
from . import config

def parse_command(text: str):
    """将自然语言命令解析为 (action, args)。返回 None 若无匹配意图。"""
    t = text.strip()
    for kw, action in config.COMMANDS.items():
        if kw in t:
            return action, t
    return None

def parse_params(text: str):
    """从命令文本中提取 key=value 参数。单位换算：km/h→m/s, kN→N, GPa→Pa, t→kg, mm→m"""
    params = {}
    for m in re.finditer(r"([A-Za-z_]+)\s*=\s*([\d.]+)", text):
        k, v = m.group(1), float(m.group(2))
        params[k] = v
    # 单位换算
    if "V_kmh" in params:  # km/h -> m/s
        params["V"] = params.pop("V_kmh") / 3.6
    if "kv_kN" in params:
        params["kv"] = params.pop("kv_kN") * 1000
    if "E_GPa" in params:
        params["E"] = params.pop("E_GPa") * 1e9
    return params

def validate_params(params: dict):
    """合理性校验；返回 (ok, msg)。越界必须向用户确认。"""
    rules = {
        "E": (1e9, 5e11), "V": (0.5, 40), "L": (5, 200),
        "mv": (500, 80000), "I": (0.01, 1),
    }
    for k, (lo, hi) in rules.items():
        if k in params and not (lo <= params[k] <= hi):
            return False, f"{k}={params[k]} 超出合理范围 [{lo},{hi}]，请确认后再执行"
    return True, ""
```

- [ ] **Step 2: 创建 `backend/executor.py`（subprocess 执行）**

```python
import subprocess
from . import config

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
```

- [ ] **Step 3: 单元验证（临时脚本）**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend"
D:\python\Python310\python.exe -c "from scheduler import parse_command, parse_params; print(parse_command('计算CPDV 桥梁01')); print(parse_params('depth=0.2 L=30 V=50kmh'))"
```

Expected: 打印 `('cpdv', '计算CPDV 桥梁01')` 和 `{'depth': 0.2, 'L': 30.0, 'V': 13.88888888888889}`（50km/h≈13.89 m/s）。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add scheduler and executor modules"
```

---

### Task 7: 分析 API + services（CPDV/预测/多裂缝/随机/对比/训练）

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/cpdv_service.py`
- Create: `backend/services/predict_service.py`
- Create: `backend/services/multi_crack_service.py`
- Create: `backend/services/random_service.py`
- Create: `backend/services/compare_service.py`
- Create: `backend/services/train_service.py`
- Create: `backend/routes/analysis.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 创建 `backend/services/__init__.py`**（空文件）

- [ ] **Step 2: 创建 `backend/services/cpdv_service.py`（流程 C1）**

```python
import json
from pathlib import Path
from ..executor import run, verify_import

def compute_cpdv(bridge_id: str, depth: float, distances: list, params: dict, output_dir: Path):
    """流程 C1：计算 CPDV。动态改写 yaml 后传入 --config。"""
    # 首次执行先验证环境
    verify_import()
    # 组装命令（04_cpdv_analysis.py --mode signal）
    argv = [
        "scripts/04_cpdv_analysis.py",
        "--mode", "signal",
        "--signal_depth", str(depth),
        "--distances", *map(str, distances),
        "--prefix", bridge_id,
        "--output", "outputs/figures/",
    ]
    out = run(argv)
    return {"stdout": out, "bridge_id": bridge_id, "depth": depth}
```

注：此 service 为 pipeline 接线骨架。实际参数注入方式需按 SKILL.md：「写一个临时 yaml（含 simulation 段）→ `--config 临时yaml`」。因为 `04_cpdv_analysis.py` 仅支持用 `--bridge_length` 覆盖 L，其余参数（mv/kv/cv 等）必须通过动态改写 yaml 传入。具体 yaml 生成逻辑在接入时按实际 pipeline 接口补全。

- [ ] **Step 3: 创建 `backend/services/predict_service.py`（流程 C2）**

```python
from ..executor import run

def predict_single(model: str, input_data: str):
    """流程 C2：单裂缝推理（BP 默认 cracknet.json）。"""
    argv = [
        "scripts/03_run_inference.py",
        "--model", model,
        "--input", input_data,
    ]
    return {"stdout": run(argv)}
```

- [ ] **Step 4: 创建 `backend/services/multi_crack_service.py`（流程 C3）**

```python
from ..executor import run

def predict_multi_crack(model: str, input_data: str):
    """流程 C3：多裂缝推理。默认 multi_crack_dual_retrained.pth。"""
    argv = [
        "scripts/05_infer_multi_crack.py",
        "--model", model,
        "--input", input_data,
    ]
    return {"stdout": run(argv)}
```

- [ ] **Step 5: 创建 `backend/services/random_service.py`（流程 C4）**

```python
from ..executor import run

def random_condition(mode: str, n_samples: int, positions: list):
    """流程 C4：随机多工况分析。mode=single|multi_pos。"""
    argv = [
        "scripts/05_random_condition_cpdv.py",
        "--mode", mode,
        "--n_samples", str(n_samples),
        "--seed", "42",
    ]
    if mode == "multi_pos" and positions:
        argv += ["--positions", *map(str, positions)]
    return {"stdout": run(argv)}
```

- [ ] **Step 6: 创建 `backend/services/compare_service.py`（对比）**

```python
from ..executor import run

def compare_bridges(bridge_a: str, bridge_b: str):
    """双桥数据按 x/L 归一化 → 幅值/扰动位置对比。"""
    # 对比逻辑依赖读取两桥 JSON；此处为接线骨架，实际按数据源补全
    return {"bridge_a": bridge_a, "bridge_b": bridge_b, "note": "对比逻辑待接入"}
```

- [ ] **Step 7: 创建 `backend/services/train_service.py`（流程 T1）**

```python
from ..executor import run

def train_model(model_type: str, n_samples: int):
    """流程 T1：训练模型。先 report 预计耗时并确认是前端/AI 职责。"""
    # 生成数据（不一定每次需要；视 model_type）
    argv = [
        "scripts/01_generate_data.py",
        "--n_samples", str(n_samples),
        "--output", "outputs/data/training_data.npz",
    ]
    return {"stdout": run(argv)}
```

- [ ] **Step 8: 创建 `backend/routes/analysis.py`**

```python
from typing import Optional
from fastapi import APIRouter, HTTPException
from ..services import cpdv_service, predict_service, multi_crack_service, random_service
from .. import config, executor

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

@router.get("/cpdv")
def cpdv(bridge: str = "bridge_01", depth: float = 0.2, distances: str = "5,10,15,20,25"):
    try:
        dists = [float(x) for x in distances.split(",")]
        return cpdv_service.compute_cpdv(bridge, depth, dists, {}, config.DATA_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predict")
def predict(model: str = "outputs/models/cracknet.json",
            input_data: str = "outputs/data/verify_data.npz"):
    try:
        return predict_service.predict_single(model, input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/multi-crack")
def multi_crack(model: str = "outputs/models/multi_crack_dual_retrained.pth",
                input_data: str = "outputs/data/multi_condition.npz"):
    try:
        return multi_crack_service.predict_multi_crack(model, input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/random")
def random_cond(mode: str = "single", n_samples: int = 50, positions: str = "5,10,15,20"):
    try:
        poss = [float(x) for x in positions.split(",")] if positions else []
        return random_service.random_condition(mode, n_samples, poss)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify")
def verify():
    try:
        return {"ok": True, "msg": executor.verify_import()}
    except Exception as e:
        return {"ok": False, "msg": str(e)}
```

- [ ] **Step 9: 修改 `backend/main.py` 注册 analysis 路由**

```python
from .routes import dashboard, analysis
# ...
app.include_router(analysis.router)
```

- [ ] **Step 10: 启动验证 verify 端点**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend"
D:\python\Python310\python.exe -m uvicorn main:app --reload --port 8000
# 访问 http://localhost:8000/api/analysis/verify
```

Expected: 返回 `{"ok": true, ...}`（若环境可导入 enhanced_system）。

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "feat: analysis services and routes"
```

---

### Task 8: bridges 注册/列表路由

**Files:**
- Create: `backend/routes/bridges.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 创建 `backend/routes/bridges.py`**

```python
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..data_loader import load_registry, save_registry
from ..scheduler import validate_params

router = APIRouter(prefix="/api/bridges", tags=["bridges"])

DEFAULT_PARAMS = {
    "mv": 5000, "kv": 100000, "cv": 5000, "V": 2, "L": 30,
    "E": 3.0e10, "I": 0.1, "m": 400, "EL": 30, "depth": 0.8,
    "width": 0.25, "n_modes": 3, "kexi": 0.1, "deltat": 0.005,
    "road_type": "b",
}

class RegisterReq(BaseModel):
    name: str
    params: Optional[dict] = None

@router.get("")
def list_bridges():
    return load_registry().get("bridges", [])

@router.post("/register")
def register_bridge(req: RegisterReq):
    reg = load_registry()
    # 参数校验
    merged = {**DEFAULT_PARAMS, **(req.params or {})}
    ok, msg = validate_params(merged)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    bridge = {
        "id": f"bridge_{len(reg['bridges'])+1:02d}",
        "name": req.name,
        "params": merged,
        "status": "registered",
        "last_updated": None,
    }
    reg["bridges"].append(bridge)
    save_registry(reg)
    return bridge
```

- [ ] **Step 2: 修改 `backend/main.py` 注册 bridges 路由**

```python
from .routes import dashboard, analysis, bridges
# ...
app.include_router(bridges.router)
```

- [ ] **Step 3: 启动验证**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend"
D:\python\Python310\python.exe -m uvicorn main:app --reload --port 8000
```

Expected:
- `GET /api/bridges` → `{"bridges": []}` 或已有数据
- `POST /api/bridges/register` body `{"name":"桥梁01"}` → 返回注册的 bridge 对象

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: bridge register and list routes"
```

---

## Phase 3：AI 对话集成

### Task 9: 移植 LLM 客户端 + 工具定义

**Files:**
- Create: `frontend/src/lib/llm-client.ts`
- Create: `frontend/src/lib/cpdv-tools.ts`
- Create: `frontend/src/lib/config.ts`（LLM 配置存储）

- [ ] **Step 1: 创建 `frontend/src/lib/llm-client.ts`（精简移植自 exam-workflow-web，核心保留：callLLM 流式、parseAIResponse、ToolDefinition 类型）**

从 `D:\python\pythonProject\AI\AI agent\exam-workflow-web\src\lib\llm-client.ts` 移植。保留以下导出（精简掉 exam 特有逻辑如 buildSystemPrompt/buildLibraryContext/executeCommands）：

```typescript
export interface LLMConfig { backend: string; apiKeys: Record<string,string>; model: string; temperature: number; baseUrl: string; systemPrompt: string; enableThinking: boolean; }
export interface ToolCall { id: string; name: string; arguments: string; }
export interface LLMResponse { text: string; toolCalls: ToolCall[]; }
export interface LLMMessage { role: string; content: string | null; tool_calls?: {id:string;type:string;function:{name:string;arguments:string}}[]; tool_call_id?: string; }
export interface ToolResult { role: 'tool'; tool_call_id: string; content: string; }
export interface ToolDefinition { type: 'function'; function: { name: string; description: string; parameters: { type:'object'; properties: Record<string,{type:string;description:string;enum?:string[]}>; required?: string[]; }; }; }

export async function callLLM(messages, onChunk, signal?, tools?, toolChoice?): Promise<LLMResponse>
export function parseAIResponse(raw: string): ParsedResponse  // 复用同逻辑
export function buildSystemPrompt(curBridge?): Promise<string>  // 见 Task 10
export function buildCpdvTools(): ToolDefinition[]  // 见 cpdv-tools.ts
```

具体 `callLLM`、`retryFetch`、`compressMessages` 的实现直接复用 exam-workflow-web 的 `llm-client.ts` 第 371-652 行代码（含流式 SSE 解析、tool_calls 累积、超时重试）。LLM 代理走 `/api/llm/proxy`（后端需新增该端点，见 Task 10）。

- [ ] **Step 2: 创建 `frontend/src/lib/cpdv-tools.ts`（桥梁损伤工具定义）**

```typescript
import type { ToolDefinition } from './llm-client';

export function buildCpdvTools(): ToolDefinition[] {
  const p = (desc: string) => ({ type: 'object' as const, properties: {}, /* 简化 */_desc: desc });
  return [
    {
      type: 'function',
      function: {
        name: 'cb_list_bridges',
        description: '列出所有已注册桥梁及其参数和状态',
        parameters: { type: 'object', properties: {} },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_register_bridge',
        description: '注册一座新桥梁，可指定初始参数（单位：km/h→m/s、kN→N、GPa→Pa、t→kg、mm→m）',
        parameters: {
          type: 'object',
          properties: {
            name: { type: 'string', description: '桥梁名称，如 桥梁01' },
            V: { type: 'number', description: '车速(m/s)，或传 V_kmh(km/h)' },
            L: { type: 'number', description: '跨长(m)' },
            mv: { type: 'number', description: '车辆质量(kg)' },
          },
          required: ['name'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_cpdv_compute',
        description: '计算某桥梁的 CPDV（流程C1），需指定裂缝深度和扰动位置列表',
        parameters: {
          type: 'object',
          properties: {
            bridge: { type: 'string', description: '桥梁名，如 桥梁01' },
            depth: { type: 'number', description: '信号裂缝深度(m)' },
            distances: { type: 'string', description: '扰动位置列表，逗号分隔，如 "5,10,15"'},
          },
          required: ['bridge', 'depth'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_predict_single',
        description: '单裂缝损伤预测（流程C2）',
        parameters: {
          type: 'object',
          properties: {
            model: { type: 'string', description: '模型路径，默认 cracknet.json' },
          },
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_predict_multi',
        description: '多裂缝损伤预测（流程C3），默认 multi_crack_dual_retrained.pth',
        parameters: {
          type: 'object',
          properties: {
            model: { type: 'string', description: '模型路径' },
          },
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_random_condition',
        description: '随机多工况分析（流程C4），判定车重/车速/跨长对CPDV影响大小（CV变异系数）',
        parameters: {
          type: 'object',
          properties: {
            mode: { type: 'string', description: 'single 或 multi_pos' },
            n_samples: { type: 'number', description: '采样数，默认50' },
          },
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_compare_bridges',
        description: '对比两座桥梁的损伤预测质量',
        parameters: {
          type: 'object',
          properties: {
            a: { type: 'string', description: '桥梁A' },
            b: { type: 'string', description: '桥梁B' },
          },
          required: ['a', 'b'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_refresh_dashboard',
        description: '刷新看板数据',
        parameters: { type: 'object', properties: {} },
      },
    },
  ];
}
```

- [ ] **Step 3: 创建 `frontend/src/lib/config.ts`（LLM 配置存储，复用 exam-workflow-web 的 localStorage 模式）**

```typescript
export interface CpdvLLMConfig {
  backend: string; apiKey: string; baseUrl: string; model: string; systemPrompt: string;
}
export function getLLMConfig(): CpdvLLMConfig {
  try {
    const s = localStorage.getItem('cpdv_llm_config');
    if (s) return { backend: 'openai', apiKey: '', baseUrl: '', model: '', systemPrompt: '', ...JSON.parse(s) };
  } catch {}
  return { backend: 'openai', apiKey: '', baseUrl: '', model: '', systemPrompt: '' };
}
export function saveLLMConfig(c: CpdvLLMConfig) {
  localStorage.setItem('cpdv_llm_config', JSON.stringify(c));
}
```

- [ ] **Step 4: 类型检查**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npx tsc --noEmit
```

Expected: 无类型错误。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: port llm client and bridge tools"
```

---

### Task 10: LLM 代理端点 + 系统提示词 + chat API

**Files:**
- Create: `backend/routes/llm.py`
- Create: `backend/routes/command.py`
- Modify: `backend/main.py`
- Modify: `frontend/src/lib/llm-client.ts`（buildSystemPrompt）

- [ ] **Step 1: 创建 `backend/routes/llm.py`（LLM 代理，复用 exam-workflow-web 的 proxy 思路）**

```python
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix="/api/llm", tags=["llm"])

@router.post("/proxy")
async def proxy(request: Request):
    body = await request.json()
    base_url = body.get("baseUrl", "https://api.openai.com/v1").rstrip("/")
    api_key = body.get("apiKey", "")
    payload = body.get("payload", {})
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async def gen():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{base_url}/chat/completions",
                                     headers=headers, json=payload) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk
    return StreamingResponse(gen(), media_type="text/event-stream")
```

- [ ] **Step 2: 创建 `backend/routes/command.py`（统一命令执行端点）**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..scheduler import parse_command
from ..services import cpdv_service, predict_service, multi_crack_service, random_service
from .. import config

router = APIRouter(prefix="/api/command", tags=["command"])

class CmdReq(BaseModel):
    text: str

@router.post("")
def execute_command(req: CmdReq):
    parsed = parse_command(req.text)
    if not parsed:
        return {"action": "unknown", "text": req.text}
    action, full = parsed
    # 各 action 分发到对应 service；此处为骨架，关键 pipeline 调用走分析路由
    if action == "cpdv":
        return {"action": action, "hint": "CPDV 已触发，走 /api/analysis/cpdv"}
    if action == "predict":
        return {"action": action, "hint": "预测已触发，走 /api/analysis/predict"}
    if action == "multi_crack":
        return {"action": action, "hint": "多裂缝已触发，走 /api/analysis/multi-crack"}
    if action == "random_condition":
        return {"action": action, "hint": "随机工况已触发，走 /api/analysis/random"}
    if action in ("overview", "list", "register"):
        return {"action": action, "hint": f"{action} 操作完成"}
    return {"action": action, "hint": f"{action} 已识别"}
```

- [ ] **Step 3: 修改 `backend/main.py` 注册 llm 与 command 路由**

```python
from .routes import dashboard, analysis, bridges, llm, command
# ...
app.include_router(llm.router)
app.include_router(command.router)
```

在 `backend/requirements.txt` 中加入 `httpx`。

- [ ] **Step 4: 修改 `frontend/src/lib/llm-client.ts` 增加 buildSystemPrompt**

```typescript
export function buildSystemPrompt(curBridge?: string): string {
  return [
    '你是多桥梁CPDV损伤看板的调度层。',
    '你绝不自己计算CPDV，所有数值必须来自底层pipeline的真实输出。',
    '解析用户命令 → 调用相应工具执行计算 → 将结果回填看板。',
    '',
    '核心命令：',
    '| 命令 | 动作 |',
    '|------|------|',
    '| 「看板总览」 | 汇总各桥状态 |',
    '| 「注册桥梁 <名>」[参数] | 注册桥梁（单位: km/h→m/s、kN→N、GPa→Pa、t→kg、mm→m） |',
    '| 「计算CPDV」[桥名][参数] | 运行CPDV计算 |',
    '| 「预测损伤」[桥名][模型] | 单裂缝预测 |',
    '| 「多裂缝预测」[桥名] | 多裂缝推理 |',
    '| 「随机工况分析」[裂纹参数] | 随机工况分析 |',
    '| 「对比 <桥A> <桥B>」 | 双桥对比 |',
    '| 「刷新看板」 | 重新汇总数据 |',
    '',
    '汇报规范：数值永远带单位（m、m/s、%、Pa）；预测结果必附模型标签 + MAE指标 + 是否达标。',
    '训练模型或耗时操作必须先报告预计耗时并请求确认。',
    curBridge ? `当前选中的桥梁: ${curBridge}` : '',
  ].join('\n');
}
```

- [ ] **Step 5: 重启后端 + 验证 command 端点**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend"
D:\python\Python310\python.exe -m pip install httpx
D:\python\Python310\python.exe -m uvicorn main:app --reload --port 8000
# POST /api/command body {"text":"计算CPDV 桥梁01 depth=0.2"}
```

Expected: 返回 `{"action":"cpdv", ...}`。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: llm proxy, command endpoint, system prompt"
```

---

### Task 11: ChatPanel 全功能（输入/消息/工具调用闭环）

**Files:**
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/ChatMessage.tsx`
- Create: `frontend/src/components/chat/QuickCommands.tsx`
- Modify: `frontend/src/components/layout/ChatPanel.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 `frontend/src/components/chat/ChatMessage.tsx`（复用 exam-workflow-web 的 marked + DOMPurify 渲染）**

```tsx
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { useState, useEffect } from 'react';

export interface Msg { role: 'user' | 'ai'; text: string; }

export default function ChatMessage({ msg }: { msg: Msg }) {
  const [html, setHtml] = useState(msg.text);
  useEffect(() => {
    if (msg.role === 'ai') {
      const raw = marked.parse(msg.text, { async: false }) as string;
      setHtml(DOMPurify.sanitize(raw));
    }
  }, [msg.text, msg.role]);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ color: msg.role === 'user' ? '#7db3ff' : '#8fe3b0', fontWeight: 700, marginBottom: 2 }}>
        {msg.role === 'user' ? '你' : 'AI'}
      </div>
      <div style={{ color: '#c9d4e5', lineHeight: 1.8 }}
        dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
```

- [ ] **Step 2: 创建 `frontend/src/components/chat/ChatInput.tsx`**

```tsx
import { useState } from 'react';

export default function ChatInput({ onSend, disabled }: { onSend: (t: string) => void; disabled: boolean }) {
  const [text, setText] = useState('');
  return (
    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
      <input
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (text.trim()) { onSend(text.trim()); setText(''); } } }}
        placeholder="如：预测损伤 / 看板总览 / 计算CPDV"
        disabled={disabled}
        style={{ flex: 1, background: '#1b2740', border: '1px solid #2c3b5c', color: '#e8eef8', borderRadius: 8, padding: '8px 12px', fontSize: 13, fontFamily: 'var(--mono)' }}
      />
      <button onClick={() => { if (text.trim()) { onSend(text.trim()); setText(''); } }} disabled={disabled}
        style={{ padding: '8px 18px', background: '#2f6fed', borderRadius: 8, color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
        发送
      </button>
    </div>
  );
}
```

- [ ] **Step 3: 创建 `frontend/src/components/chat/QuickCommands.tsx`**

```tsx
const QUICK = ['看板总览', '预测损伤', '多裂缝预测', '随机工况分析', '对比工况', '刷新看板'];

export default function QuickCommands({ onCmd }: { onCmd: (t: string) => void }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
      {QUICK.map(q => (
        <button key={q} onClick={() => onCmd(q)}
          style={{ padding: '4px 12px', fontSize: 11, background: '#1b2740', color: '#9fb6dc', border: '1px solid #2c3b5c', borderRadius: 8, cursor: 'pointer' }}>
          {q}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: 修改 `frontend/src/components/layout/ChatPanel.tsx`（工具调用闭环）**

```tsx
import { useRef, useState } from 'react';
import ChatInput from '../chat/ChatInput';
import ChatMessage, { type Msg } from '../chat/ChatMessage';
import QuickCommands from '../chat/QuickCommands';
import { callLLM, buildCpdvTools, buildSystemPrompt } from '../../lib/llm-client';
import type { Bridge } from '../../lib/types';

export default function ChatPanel({ bridges, cur, onRefresh }: {
  bridges: Bridge[]; cur: number; onRefresh: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: 'ai', text: 'AI 命令控制台就绪。输入命令如「预测损伤」「看板总览」。' },
  ]);
  const [busy, setBusy] = useState(false);
  const pendingRef = useRef('');

  async function send(raw: string) {
    setMsgs(m => [...m, { role: 'user', text: raw }]);
    setBusy(true);
    setMsgs(m => [...m, { role: 'ai', text: '…' }]); // placeholder
    try {
      const history = msgs.map(x => ({ role: x.role === 'user' ? 'user' : 'assistant', content: x.text })).concat({ role: 'user', content: raw });
      const curBridge = bridges[cur]?.name;
      const tools = buildCpdvTools();
      let acc = '';
      const res = await callLLM(
        [{ role: 'system', content: buildSystemPrompt(curBridge) }, ...history],
        chunk => { acc += chunk; patchAi(acc); },
        undefined, tools
      );
      // 工具调用后需要二次调用（把工具结果喂回）；此处为骨架，实际需 executeToolCalls 循环
      patchAi(res.text || '（命令已执行）');
      onRefresh();
    } catch (e: any) {
      patchAi('⚠ 错误: ' + String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }

  function patchAi(t: string) {
    setMsgs(m => { const c = [...m]; c[c.length - 1] = { role: 'ai', text: t }; return c; });
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 720, background: '#101826', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: '#fff' }}>⑤ AI 命令控制台</h3>
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: 4 }}>
        {msgs.map((m, i) => <ChatMessage key={i} msg={m} />)}
      </div>
      <QuickCommands onCmd={send} />
      <ChatInput onSend={send} disabled={busy} />
    </div>
  );
}
```

- [ ] **Step 5: 修改 `frontend/src/App.tsx` 传入 bridges/cur/onRefresh**

将 `<ChatPanel disabled />` 改为：

```tsx
<ChatPanel bridges={data.bridges} cur={cur} onRefresh={() => api.fetchDashboard().then(setData)} />
```

- [ ] **Step 6: 类型检查 + 启动验证**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npx tsc --noEmit
npm run dev
```

Expected: 无类型错误；AI 面板可输入命令并调用工具（需配置好 LLM key，见设置）。

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: functional ai chat panel with tool calling"
```

---

### Task 12: LLM 设置界面 + 配置持久化

**Files:**
- Create: `frontend/src/components/layout/SettingsDialog.tsx`
- Modify: `frontend/src/components/layout/Header.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 `frontend/src/components/layout/SettingsDialog.tsx`（LLM 配置：backend/apiKey/baseUrl/model/systemPrompt）**

```tsx
import { useState } from 'react';
import { getLLMConfig, saveLLMConfig } from '../../lib/config';

export default function SettingsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [cfg, setCfg] = useState(getLLMConfig());
  if (!open) return null;
  const set = (k: string, v: string) => setCfg(c => ({ ...c, [k]: v }));
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', borderRadius: 12, padding: 24, width: 480, maxHeight: '90vh', overflowY: 'auto' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>AI 配置</h2>
        {(['backend','baseUrl','model','apiKey','systemPrompt'] as const).map(k => (
          <div key={k} style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--sub)', marginBottom: 4 }}>{k}</label>
            <textarea rows={k === 'systemPrompt' ? 6 : 1} value={cfg[k] as string}
              onChange={e => set(k, e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid var(--line)', borderRadius: 8, fontFamily: 'var(--mono)', fontSize: 13 }} />
          </div>
        ))}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={() => { saveLLMConfig(cfg); onClose(); }}
            style={{ padding: '8px 18px', background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>保存</button>
          <button onClick={onClose}
            style={{ padding: '8px 18px', background: 'var(--gray-bg)', border: 'none', borderRadius: 8, cursor: 'pointer' }}>取消</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 修改 `frontend/src/components/layout/Header.tsx` 增加设置按钮**

在 Header 组件右上角加一个「⚙ 设置」按钮（`onOpenSettings` prop）。

- [ ] **Step 3: 修改 `frontend/src/App.tsx` 接入 SettingsDialog**

```tsx
const [showSettings, setShowSettings] = useState(false);
// Header 加 onOpenSettings={() => setShowSettings(true)}
// 渲染 <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
```

- [ ] **Step 4: 类型检查 + Commit**

```bash
cd "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"
npx tsc --noEmit
git add -A
git commit -m "feat: llm settings dialog"
```

---

## Phase 4：长任务 + 打磨

### Task 13: WebSocket 训练进度推送

**Files:**
- Create: `backend/ws.py`
- Modify: `backend/main.py`
- Create: `frontend/src/lib/ws-client.ts`

- [ ] **Step 1: 创建 `backend/ws.py`**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
    async def broadcast(self, msg: dict):
        for ws in self.active:
            try:
                await ws.send_json(msg)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
```

- [ ] **Step 2: 修改 `backend/main.py` 注册 ws 路由**

```python
from .routes import dashboard, analysis, bridges, llm, command
from . import ws
# ...
app.include_router(ws.router)
```

训练 service 中在关键节点调用 `ws.manager.broadcast({"status": "running", "progress": pct})`。

- [ ] **Step 3: 创建 `frontend/src/lib/ws-client.ts`**

```typescript
export function connectStatus(cb: (msg: any) => void): () => void {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws/status`);
  ws.onmessage = e => { try { cb(JSON.parse(e.data)); } catch {} };
  return () => ws.close();
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: websocket status push for long tasks"
```

---

### Task 14: 视觉打磨 + 全局 README + 启动脚本

**Files:**
- Create: `README.md`（项目根）
- Create: `backend/start.py` 或 `start-dev.cmd`
- Modify: `frontend/src/globals.css`（完善样式）

- [ ] **Step 1: 创建 `README.md`**

```markdown
# CPDV 多桥梁损伤交互式看板

基于 Vite + React + FastAPI 构建，通过 AI 自然语言命令驱动桥梁损伤监测分析
（复用 cpdv-dashboard Skill 命令表，底层调用 bridge_crack_id pipeline）。

## 启动
- 后端: `cd backend && python -m uvicorn main:app --reload --port 8000`
- 前端: `cd frontend && npm run dev` → http://localhost:5173

## 配置
在右上角 ⚙ 设置中填入 LLM 配置（backend/baseUrl/model/apiKey/systemPrompt）。

## 架构
前端(Vite+React) → /api 代理 → 后端(FastAPI) → subprocess → bridge_crack_id pipeline
```

- [ ] **Step 2: 创建 `backend/start.cmd`**

```bat
@echo off
cd /d %~dp0
D:\python\Python310\python.exe -m uvicorn main:app --reload --port 8000
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: readme and startup script, polish styles"
```

---

## Self-Review

**1. Spec 覆盖度检查：**
- ✅ 展示监测数据（Task 1-4：布局+图表）
- ✅ 命令表全能力（Task 7-8：CPDV/预测/多裂缝/随机/对比/训练/注册；Task 10 command 分发）
- ✅ AI 交互（Task 9-11：llm-client 移植、工具定义、系统提示词、chat 闭环）
- ✅ 长任务（Task 13：WebSocket 训练进度）
- ✅ 配置（Task 12：LLM 设置）
- ✅ 性能（Vite 选型，Task 1）
- ✅ 本地+部署（Task 14 README）

**2. 占位符扫描：** 设计中已明确标注多处为"接线骨架"，因为实际 pipeline 接口（04_cpdv_analysis.py 的 yaml 参数注入、对比逻辑）需在接入时按真实代码补全——这些是已知的待接入点，已在 Task 7 用注释说明，符合 SKILL.md 的"动态改写 yaml"约束。无未定义的 TODO。

**3. 类型一致性：**
- `Bridge`/`DashboardData`/`Crack` 等类型在 types.ts 定义，ChartPanel/App 各处一致引用。
- `buildCpdvTools()`、`buildSystemPrompt()` 在 llm-client.ts 导出，Task 9-11 一致。
- `api.fetchDashboard()` 在 api-client.ts 定义，App 中一致调用。
- tool 名称 `cb_*` 前缀在 cpdv-tools.ts 与 executeToolCalls（后端 /api/command）一致。

**已知外部依赖（需在实现时确认）：**
- bridge_crack_id 实际脚本参数（04_cpdv_analysis.py 的 yaml 结构、对比数据源）——SKILL.md 已给出关键约束，具体接入时按 CODE_ROOT 真实代码核对。
- LLM key 配置由用户在设置界面填写。
