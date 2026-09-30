# 发现与决策

## 需求
- 落实评审.md 第8节：算法代码库看板展示
- 两套代码库：原始 Pipeline (D:\研\土木水利\论文\代码\github) + 整理版算法库 (D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\算法代码)
- 核心功能：代码拓扑图、Protocol契约详情、版本语义对比、Git时间轴
- 集成到现有 cpdv-dashboard-web 前端

## 研究发现
- 现有前端：React + TypeScript + Chart.js + Canvas，组件化结构清晰
- 现有后端：FastAPI + 子进程执行原始脚本，配置驱动
- backend_framework 已定义 6 个 Protocol，backends/legacy 已注册
- 原始 Pipeline 核心文件：scripts/04_train_multi_crack.py, model/multi_crack.py, simulation/
- 需要解析：类、函数、导入、装饰器、类型注解、docstring

## 技术决策
| 决策 | 理由 |
|------|------|
| AST 用 ast + astroid | 标准库无依赖，astroid 提供推断、装饰器解析 |
| 拓扑图用 cytoscape.js | 生态成熟、布局引擎丰富、TypeScript 支持好 |
| 输出静态 JSON 到 public/ | 免后端实时解析、前端直加载、CDN 友好 |
| 同步脚本独立运行 | 解耦构建流程、可 CI 集成、手动触发灵活 |
| 契约作为单一真相源 | Protocol 定义在 backend_framework/，自动汇总实现 |

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| AST 解析器选择 | 先用 ast + astroid 混合，后续可迁移 tree-sitter |
| 拓扑图布局引擎 | 客户端 cytoscape-cose-bilkent 交互最好 |
| 大文件增量解析 | 文件 mtime + 内容哈希双重校验 |
| 前端状态管理 | 复用现有 React Context + useReducer 模式 |
| 代码跳转协议 | vscode://file/{path}:{line} |

## 资源
- 原始 Pipeline: `D:\研\土木水利\论文\代码\github`
- 整理版算法库: `D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\算法代码`
- 后端框架: `cpdv-dashboard-web/backend_framework/`
- 前端源码: `cpdv-dashboard-web/frontend/src/`
- 评审文档: `D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\01_看板展示\评审.md`

## 视觉/浏览器发现
- 已阅读评审.md 第8节完整设计
- 理解四栏式布局、7个API端点、6个前端组件
- 明确数据流：同步脚本 → 静态JSON → 前端加载 → 交互调用API

---
*每执行2次查看/浏览器/搜索操作后更新此文件*
*防止视觉信息丢失*