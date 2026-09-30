# CPDV 多桥梁损伤交互式看板

基于 Vite + React + FastAPI 构建，通过 AI 自然语言命令驱动桥梁损伤监测分析
（复用 cpdv-dashboard Skill 命令表，底层调用 bridge_crack_id pipeline）。

## 算法代码库

| 库 | 路径 | 用途 |
|----|------|------|
| **整理后算法库** | `D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\算法代码\` | 📚 前端代码浏览/编辑（AlgorithmSidebar），结构清晰、分类完整 |
| **原始 Pipeline** | `D:\研\土木水利\论文\代码\github\` | ⚙️ 后端 subprocess 执行，包含可运行的训练/推理脚本 |

> 前端 AlgorithmSidebar 默认指向「整理后算法库」，可在右上角下拉切换到「原始 Pipeline」。

## 启动
- **一键（推荐）**: 双击 `start_all.bat`，自动清残留 + 调起 `start_backend.bat` 和 `start_frontend.bat` 两个独立终端窗口。窗口不关就一直在。
- 后端（手动）: `cd backend && python -m uvicorn main:app --reload --port 8765`
  （端口与 `frontend/vite.config.ts` 的 proxy `VITE_API_TARGET` 默认一致；若改端口请同步设置 `VITE_API_TARGET=http://127.0.0.1:新端口`）
- 前端: `cd frontend && npm run dev` → http://localhost:5173
- 验证: 浏览器访问 http://localhost:5173，看板应显示 3 座桥 + Header 指标卡（哪怕都是 0 也算通）；如空白/红字看浏览器 DevTools Console
- **如果看到 `connect ECONNREFUSED 127.0.0.1:8000`**：vite.config.ts 的 proxy 没读到 8765，立刻 `cat frontend/vite.config.ts | findstr "API_TARGET"` 确认是 8765 而不是 8000；或全局搜 `localhost:8000` 检查有没有别处又写错了。
- **如果 `start_all.bat` 双击后窗口瞬间关闭**：可能是 PowerShell 权限问题，右键 `start_all.bat` → "以管理员身份运行"。或手动分别双击 `start_backend.bat` + `start_frontend.bat`。

## 配置
- LLM：在右上角 ⚙ 设置中填入 LLM 配置（baseUrl/model/apiKey/systemPrompt）。
- CORS：后端默认白名单 `http://localhost:5173` 等 Vite 端口；如部署到其他 origin，设 `CPDV_ALLOW_ORIGINS=https://your.domain`。
- LLM baseUrl 白名单：默认含 OpenAI/Anthropic/Moonshot/Deepseek 官方域；自定义 baseUrl 设 `CPDV_LLM_ALLOWED_BASES=https://your.api/v1,...`。
- 看板阈值：默认 5 个指标阈值；自定义设 `CPDV_THRESHOLDS_JSON='{"f1_min":0.92}'`。
- 默认超时：默认 300s；自定义设 `CPDV_DEFAULT_TIMEOUT=600`。

## 架构
前端(Vite+React) → /api 代理 → 后端(FastAPI, 8765) → subprocess → bridge_crack_id pipeline

## 已修复的关键 bug
- **Vite proxy 端口对齐**：之前硬编码 `localhost:8000`，实际后端跑 8765 → 看板 fetch 失败。
- **CORS 非法组合**：之前 `allow_origins=* + credentials=True`，浏览器会拒；改为显式白名单 + env。
- **Windows subprocess hang**：`subprocess.run(timeout=...)` 在 c10.dll 已加载的 Python 子进程上会 hang；改用 `Popen + communicate + CREATE_NO_WINDOW`。
- **parse_params 4 个隐藏 bug**：科学计数法、负数、列表、字符串值全部修复。
- **registry 数据污染**：bridge_01.name 早期 GBK 污染成 `"??01"`，服务端 `_label()` 自动降级显示 id，人工修正数据。

## 测试
所有测试散落 `D:\WorkbuddySpace\test_*.py`（test_p0/4/5/6/7/8 + test_p2_v1/2/3/4），对应评审 18 项缺口。