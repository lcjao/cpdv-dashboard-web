# 任务计划：可插拔后端执行框架（策略模式 + 插件注册表）

将此文件作为任务的持久化路线图。在开始复杂工作前创建，并在阶段变化时及时更新。

## 目标

构建一个可插拔后端执行框架，保持原始 Pipeline（`D:\研\土木水利\论文\代码\github`）零侵入，支持模块级热插拔、运行时配置切换、开发时 Git 隔离、内置 A/B 测试框架，实现训练指标自动对比排名。

## 下一步

创建 `backend_framework/protocols/` 目录及 6 个 Protocol 定义文件（DataLoaderProtocol, ModelProtocol, LossProtocol, OptimizerProtocol, TrainerProtocol, EvaluatorProtocol）

## 当前阶段

阶段 1

## 各阶段

将任务拆分为可验证的阶段。状态只能使用 `pending`、`in_progress` 或 `complete`，并在工作推进时更新。

### 阶段 1：协议层（Protocols）—— 定义组件契约
- [ ] 创建 `backend_framework/protocols/__init__.py`
- [ ] 创建 `backend_framework/protocols/data_loader.py` - DataLoaderProtocol
- [ ] 创建 `backend_framework/protocols/model.py` - ModelProtocol
- [ ] 创建 `backend_framework/protocols/loss.py` - LossProtocol
- [ ] 创建 `backend_framework/protocols/optimizer.py` - OptimizerProtocol
- [ ] 创建 `backend_framework/protocols/trainer.py` - TrainerProtocol
- [ ] 创建 `backend_framework/protocols/evaluator.py` - EvaluatorProtocol
- [ ] 运行 mypy --strict 验证类型
- **状态：** in_progress

### 阶段 2：注册表（Registry）—— 动态插件发现与注册
- [ ] 创建 `backend_framework/registry/__init__.py` - 核心注册函数 register/get/list_all
- [ ] 创建 `backend_framework/registry/data_loaders.py` - 数据加载器注册表
- [ ] 创建 `backend_framework/registry/models.py` - 模型注册表
- [ ] 创建 `backend_framework/registry/losses.py` - 损失函数注册表
- [ ] 创建 `backend_framework/registry/optimizers.py` - 优化器注册表
- [ ] 创建 `backend_framework/registry/trainers.py` - 训练器注册表
- [ ] 创建 `backend_framework/registry/evaluators.py` - 评估器注册表
- [ ] 编写单元测试验证注册/获取/列举功能
- **状态：** pending

### 阶段 3：适配层—— 适配原始 Pipeline 组件
- [ ] 创建 `backend_framework/adapters/__init__.py`
- [ ] 创建 `backend_framework/adapters/legacy_data_loader.py` - 适配原始数据加载
- [ ] 创建 `backend_framework/adapters/legacy_model.py` - 适配 MultiCrackPredictor/DualHead
- [ ] 创建 `backend_framework/adapters/legacy_loss.py` - 适配 weighted_multi_crack_loss, MultiCrackDualHeadLoss
- [ ] 创建 `backend_framework/adapters/legacy_optimizer.py` - 适配 Adam/AdamW
- [ ] 创建 `backend_framework/adapters/legacy_trainer.py` - 适配 train_three_phase 流程
- [ ] 创建 `backend_framework/adapters/legacy_evaluator.py` - 适配 evaluate_multi_crack
- [ ] 在 `backends/legacy/__init__.py` 注册所有 legacy 组件
- [ ] 验证 legacy 后端能完整跑通训练+评估
- **状态：** pending

### 阶段 4：组装器—— Pipeline 构建与实验运行器
- [ ] 创建 `backend_framework/composition/pipeline_builder.py` - 从 YAML 配置构建完整 Pipeline
- [ ] 创建 `backend_framework/composition/experiment_runner.py` - A/B 测试运行器（多版本、多轮、统计检验）
- [ ] 支持配置中的变量插值 `${experiment.name}_${timestamp}`
- [ ] 实现 `run_single_experiment(config)` 和 `run_ab_test(ab_config)`
- [ ] 输出标准化结果：metrics.csv, statistical_test.json, report.md
- **状态：** pending

### 阶段 5：CLI 统一入口—— 运行时切换
- [ ] 创建 `backend_framework/cli.py` - 统一命令行入口
- [ ] 实现 `run` 子命令：单实验运行
- [ ] 实现 `ab-test` 子命令：A/B 测试
- [ ] 实现 `list-components` 子命令：列出所有可用组件
- [ ] 实现 `interactive` 子命令：交互式选择
- [ ] 支持 `--config` 参数指定 YAML 配置文件
- **状态：** pending

### 阶段 6：实验配置与验证
- [ ] 创建 `experiments/configs/baseline.yaml` - 原始 Pipeline 配置
- [ ] 创建 `experiments/configs/exp_v1.yaml` - 新方案 v1 配置（示例）
- [ ] 创建 `experiments/configs/exp_v2.yaml` - 新方案 v2 配置（示例）
- [ ] 创建 `experiments/configs/ab_test.yaml` - A/B 测试配置
- [ ] 运行完整 A/B 测试验证框架端到端
- [ ] 生成对比报告验证统计检验正确性
- **状态：** pending

### 阶段 7：文档同步与收尾
- [ ] 更新 `D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\01_看板展示\评审.md` 追加第 7 节
- [ ] 创建 `backend_framework/README.md` 使用文档
- [ ] 更新项目根目录 README.md 添加框架介绍
- [ ] 验收检查：原始 Pipeline 零修改、模块级替换、运行时切换、A/B 自动化、结果可追溯
- **状态：** pending

## 关键问题

1. 原始 Pipeline 的 CODE_ROOT 路径是否需要作为环境变量注入框架？→ 是，通过 config.py 的 CPDV_CODE_ROOT
2. PyTorch 模型的 state_dict 加载/保存接口如何统一？→ ModelProtocol 定义 save/load_state_dict
3. 训练历史如何标准化收集？→ TrainResult.history 字段
4. Windows 下 subprocess 编码问题如何处理？→ 复用 executor.py 的 _ENV 和 CREATE_NO_WINDOW

## 已做决策

| 决策 | 理由 |
|------|------|
| 采用策略模式 + 插件注册表 | 模块级热插拔，运行时组装，声明式配置 |
| Protocol 定义在 backend_framework/protocols/ | 集中管理契约，便于新后端实现参考 |
| Registry 使用装饰器 @register 自动注册 | 零配置发现，Python 导入即注册 |
| Legacy 适配器放在 adapters/ 而非 backends/legacy/ | 复用原始代码，backends/legacy/ 仅做注册绑定 |
| 实验结果按时间戳归档 experiments/results/ | 可追溯，便于对比和回溯 |
| A/B 测试内置统计检验 | 科学决策，避免人工主观判断 |

## 遇到的错误

| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
|      | 1       |         |

## 备注
- 随着工作推进，将阶段状态从 `pending` 更新为 `in_progress`，再更新为 `complete`。
- 做重大决策前，重新读取目标和下一步。
- 及时记录错误，避免重复失败的方法。