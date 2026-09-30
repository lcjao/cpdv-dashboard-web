# 发现与决策

## 需求
- 原始 Pipeline（`D:\研\土木水利\论文\代码\github`）保持只读、零侵入
- 支持模块级热插拔：DataLoader/Model/Loss/Optimizer/Trainer/Evaluator 可独立替换
- 运行时通过配置/CLI 无缝切换后端版本
- 开发时通过 Git 隔离不同后端实现
- 内置 A/B 测试框架：多版本并行、多轮重复、统计显著性检验、自动生成对比报告
- 最终训练得分（MAE/F1/Recall/Precision 等）自动排名，选出最优方案

## 研究发现
- 原始 Pipeline 核心脚本：`scripts/04_train_multi_crack.py`（三阶段训练）、`scripts/05_infer_multi_crack.py`（评估）
- 模型定义在 `model/multi_crack.py`：MultiCrackPredictor（基础）、MultiCrackDualHead（双头）
- 损失函数：`weighted_multi_crack_loss`、 `MultiCrackDualHeadLoss`
- 评估函数：`evaluate_multi_crack`（匈牙利匹配 + F1/Recall/Precision/MAE）
- 数据加载：`scripts/01_generate_data.py` 生成 NPZ，`scripts/data_loader.py` 加载
- 后端当前通过 `executor.py` 以 subprocess 方式调用 pipeline 脚本
- config.py 管理环境变量覆盖：CODE_ROOT, PYTHON_EXE, DATA_DIR 等

## 技术决策
| 决策 | 理由 |
|------|------|
| 采用策略模式 + 插件注册表 | 模块级热插拔，运行时组装，声明式配置 |
| Protocol 定义在 backend_framework/protocols/ | 集中管理契约，便于新后端实现参考 |
| Registry 使用装饰器 @register 自动注册 | 零配置发现，Python 导入即注册 |
| Legacy 适配器放在 adapters/ 而非 backends/legacy/ | 复用原始代码，backends/legacy/ 仅做注册绑定 |
| 实验结果按时间戳归档 experiments/results/ | 可追溯，便于对比和回溯 |
| A/B 测试内置统计检验 | 科学决策，避免人工主观判断 |
| 复用 executor.py 的 _ENV 和 CREATE_NO_WINDOW | 解决 Windows subprocess 编码和超时问题 |

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| 原始 Pipeline 使用 subprocess 调用，如何转为 in-process 调用？ | 适配器层直接 import model/multi_crack.py 等模块，复用 train_three_phase 和 evaluate_multi_crack 函数 |
| 多后端共享同一数据格式如何保证？ | DataLoaderProtocol 标准化返回格式，适配器统一转换 |
| 训练过程实时进度如何传递？ | TrainerProtocol 返回 TrainResult，包含 history；CLI 层可选回调 |

## 资源
- 原始 Pipeline: `D:\研\土木水利\论文\代码\github`
- 当前后端: `D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend`
- 设计文档: `D:\python\pythonProject\AI\AI agent\docs\superpowers\specs\2026-09-09-pluggable-backend-design.md`
- 评审文档: `D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\01_看板展示\评审.md`

## 视觉/浏览器发现
- 已阅读原始 Pipeline 核心代码：04_train_multi_crack.py, model/multi_crack.py, executor.py, config.py, train_service.py
- 理解了三阶段训练流程、双头模型架构、匈牙利匹配评估、subprocess 执行机制

---
*每执行2次查看/浏览器/搜索操作后更新此文件*
*防止视觉信息丢失*