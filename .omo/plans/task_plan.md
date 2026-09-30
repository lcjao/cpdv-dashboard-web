# Pipeline Builder - 可视化流水线构建器

## 目标
在算法看板中实现一个可视化流水线构建器：
- 左侧展示预定义的流程模板文件夹（生成数据、训练、推理、评估）
- 每个模板包含可替换的代码节点（数据加载器、模型、损失函数、优化器、训练器、评估器等）
- 右侧画布组装成新的自定义流程
- 支持拖拽节点、替换实现、配置参数、导出为可运行的代码文件夹

## 阶段

### 阶段 1: 类型定义与模板数据 ✅
- [x] 扩展 algorithm-types.ts 添加 PipelineNode、PipelineTemplate、PipelineInstance 等类型
- [ ] 创建预定义模板数据：data_generation、training、inference、evaluation
- [ ] 基于现有 Protocol 契约和实现映射生成节点替代方案

### 阶段 2: 核心组件开发
- [ ] PipelineCanvas - 可视化画布（React Flow 或自定义 SVG/Canvas）
- [ ] NodePalette - 左侧节点调色板（按模板分组展示）
- [ ] NodeEditor - 右侧节点配置面板（替换实现、修改参数）
- [ ] PipelineValidator - 验证连接合法性、类型匹配

### 阶段 3: 拖拽交互
- [ ] 从调色板拖拽节点到画布
- [ ] 节点间连线（端口类型匹配验证）
- [ ] 节点替换（点击节点显示可选实现列表）
- [ ] 撤销/重做历史

### 阶段 4: 代码生成与导出
- [ ] 生成 pipeline_config.json（可被后端执行）
- [ ] 生成 Python 运行脚本
- [ ] 导出为文件夹结构（含 requirements.txt、README.md）

### 阶段 5: 集成到 AlgorithmDashboard
- [ ] 新增 "Pipeline Builder" 视图模式
- [ ] 顶栏切换按钮
- [ ] 保存/加载自定义流程

## 已完成工作
- 类型定义已添加到 algorithm-types.ts
- 后端已有 Protocol 契约解析、实现映射扫描

## 待解决问题
1. 前端拖拽库选择：React Flow vs dnd-kit vs 原生 HTML5 Drag API
2. 节点布局算法：自动布局 vs 手动定位
3. 后端执行引擎：如何将生成的配置转为可运行任务