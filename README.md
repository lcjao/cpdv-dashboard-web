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