# 任务计划：算法代码库看板展示（评审.md 第8节落实）

将此文件作为任务的持久化路线图。在开始复杂工作前创建，并在阶段变化时及时更新。

## 目标

实现评审.md 第8节设计的算法代码库看板展示：两套代码库（原始Pipeline + 整理版算法库）的拓扑可视化、Protocol契约详情、版本语义对比、Git时间轴，集成到现有 cpdv-dashboard-web 前端。

## 下一步

创建后端数据管线：`scripts/sync_algorithm_code.py` AST解析器、符号表生成、JSON输出到 `frontend/public/algorithm-map/`

## 当前阶段

阶段 1

## 各阶段

### 阶段 1：后端数据管线（M1）— AST解析、符号提取、同步脚本
- [ ] 创建 `scripts/sync_algorithm_code.py` 主同步脚本
- [ ] 创建 `scripts/ast_parser.py` 通用Python AST解析器（基于 ast/astroid）
- [ ] 创建 `scripts/symbol_extractor.py` 符号提取器：类、函数、导入、装饰器、类型注解
- [ ] 创建 `scripts/contract_parser.py` Protocol契约解析器：从 backend_framework/protocols/ 提取契约规范
- [ ] 创建 `scripts/implementation_mapper.py` 实现映射器：扫描 backends/ 关联 Protocol → 实现
- [ ] 生成输出：`symbols.json`、`contracts.json`、`implementations.json`、拓扑图 `topology.json`
- [ ] 输出目录：`cpdv-dashboard-web/frontend/public/algorithm-map/`
- [ ] 支持增量更新：文件哈希缓存、只解析变更文件
- **状态：** pending

### 阶段 2：后端 API（M2）— 7个REST端点
- [ ] 在 `backend/routes/` 新增 `algorithm.py` 路由模块
- [ ] 实现 `GET /api/algorithm/libraries` — 列出代码库、同步状态
- [ ] 实现 `GET /api/algorithm/topology` — 拓扑图数据（参数：library, focus_node, depth）
- [ ] 实现 `GET /api/algorithm/symbols` — 符号搜索（q, type, library）
- [ ] 实现 `GET /api/algorithm/contract/:protocol` — 契约详情（含所有实现对比表）
- [ ] 实现 `POST /api/algorithm/diff` — 版本语义对比（body: {base, target, dimension}）
- [ ] 实现 `GET /api/algorithm/timeline` — 时间轴数据（library, since, until）
- [ ] 实现 `POST /api/algorithm/sync` — 触发同步（库、增量/全量）
- [ ] 注册路由到 `backend/main.py`
- [ ] 添加缓存层（内存 LRU + 文件修改时间校验）
- **状态：** pending

### 阶段 3：前端核心组件（M3）— Navigator + ModuleTree + TopologyCanvas
- [ ] 创建 `frontend/src/components/algorithm/CodeLibraryNavigator.tsx` — 顶部导航栏
- [ ] 创建 `frontend/src/components/algorithm/ModuleTree.tsx` — 左侧虚拟滚动树
- [ ] 创建 `frontend/src/components/algorithm/TopologyCanvas.tsx` — 中间拓扑图
- [ ] 集成 `cytoscape.js` + `cytoscape-cose-bilkent` 布局引擎
- [ ] 实现节点交互：点击→详情面板、悬浮→依赖高亮、右键→上下文菜单
- [ ] 实现缩放/平移/重置视图、自适应容器尺寸
- [ ] 创建 `frontend/src/hooks/useAlgorithmData.ts` — 数据获取/缓存 Hook
- [ ] 创建 `frontend/src/types/algorithm.ts` — 完整 TypeScript 类型定义
- **状态：** pending

### 阶段 4：前端详情/对比组件（M4）— ContractPanel + DiffView + TimelineBar
- [ ] 创建 `frontend/src/components/algorithm/ContractPanel.tsx` — 右侧契约详情
- [ ] 创建 `frontend/src/components/algorithm/DiffView.tsx` — 双栏语义对比
- [ ] 创建 `frontend/src/components/algorithm/TimelineBar.tsx` — 底部时间轴热力图
- [ ] 创建 `frontend/src/components/algorithm/SymbolSearch.tsx` — 全局搜索弹窗
- [ ] 实现 Mermaid 类图渲染（契约面板）
- [ ] 实现语义差异高亮：架构变更/参数变更/新增删除分类着色
- [ ] 实现时间轴：提交热力图、标签里程碑、实验关联点击跳转
- [ ] 创建 `frontend/src/pages/AlgorithmDashboard.tsx` — 算法看板主页面
- [ ] 接入路由：`App.tsx` 新增 `/algorithm` 路由、侧边栏入口
- **状态：** pending

### 阶段 5：集成联调与交付（M5）
- [ ] 运行同步脚本生成初始数据：`python scripts/sync_algorithm_code.py --full`
- [ ] 启动后端验证 7 个 API 端点响应正确
- [ ] 启动前端验证算法看板页面加载、交互流程
- [ ] 修复 TypeScript 类型错误、ESLint 警告
- [ ] 性能验证：拓扑图首屏 <3s、搜索 <200ms、对比渲染 <1s
- [ ] 错误边界、加载骨架屏、空状态处理
- [ ] 更新 `评审.md` 标记实施完成、记录已知限制
- **状态：** pending

## 关键问题

1. **AST 解析器选择**：`ast` (标准库) vs `astroid` (更强大) vs `tree-sitter` (跨语言)？→ 先用 `ast` + `astroid` 混合，后续可迁移
2. **拓扑图布局引擎**：`cytoscape-cose-bilkent` (JS) vs `dagre` (JS) vs 服务端 Graphviz？→ 客户端 `cose-bilkent` 交互最好
3. **大文件增量解析**：如何检测变更？→ 文件 mtime + 内容哈希双重校验
4. **前端状态管理**：用现有 React Context 还是引入 Zustand？→ 复用现有模式，Context + useReducer
5. **代码跳转协议**：`vscode://file/` vs `vscode://open/`？→ `vscode://file/{path}:{line}`

## 已做决策

| 决策 | 理由 |
|------|------|
| AST 用 ast + astroid | 标准库无依赖，astroid 提供推断、装饰器解析 |
| 拓扑图用 cytoscape.js | 生态成熟、布局引擎丰富、TypeScript 支持好 |
| 输出静态 JSON 到 public/ | 免后端实时解析、前端直加载、CDN 友好 |
| 同步脚本独立运行 | 解耦构建流程、可 CI 集成、手动触发灵活 |
| 契约作为单一真相源 | Protocol 定义在 backend_framework/，自动汇总实现 |

## 遇到的错误

| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
|      | 1       |         |

## 备注
- 随着工作推进，将阶段状态从 `pending` 更新为 `in_progress`，再更新为 `complete`。
- 做重大决策前，重新读取目标和下一步。
- 及时记录错误，避免重复失败的方法。