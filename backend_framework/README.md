# backend_framework - 可插拔后端执行框架

## 概述

这是一个基于**策略模式 + 插件注册表**的可插拔后端执行框架，专为桥梁健康系统的 CPDV 多裂缝损伤预测模型训练设计。

### 核心特性

- ✅ **原始 Pipeline 零侵入** - `D:\研\土木水利\论文\代码\github` 保持只读
- ✅ **模块级热插拔** - DataLoader/Model/Loss/Optimizer/Trainer/Evaluator 可独立替换
- ✅ **声明式配置** - YAML 文件驱动组装，运行时无需改代码
- ✅ **运行时切换** - CLI 一键切换后端版本
- ✅ **开发时隔离** - Git 子模块/独立目录管理不同后端实现
- ✅ **内置 A/B 测试** - 多版本并行、多轮重复、统计显著性检验、自动生成对比报告

## 快速开始

### 1. 列出所有可用组件

```bash
python -m backend_framework.cli list-components
```

### 2. 运行单实验（使用 baseline 配置）

```bash
python -m backend_framework.cli run --config experiments/configs/baseline.yaml
```

### 3. 运行 A/B 测试（对比 baseline, exp_v1, exp_v2）

```bash
python -m backend_framework.cli ab-test --config experiments/configs/ab_test.yaml
```

### 4. 交互式选择组件并运行

```bash
python -m backend_framework.cli interactive
```

## 架构设计

```
project_root/
├── pipeline_core/                 # 原始 Pipeline（只读，git submodule）
│   ├── scripts/04_train_multi_crack.py
│   ├── model/multi_crack.py
│   └── ...
│
├── backend_framework/             # 框架核心
│   ├── protocols/                 # 6 个 Protocol 契约定义
│   ├── registry/                  # 插件注册表
│   ├── adapters/                  # 原始 Pipeline 适配器
│   ├── composition/               # 管线组装 + 实验运行器
│   └── cli.py                     # 统一 CLI 入口
│
├── backends/                      # 后端实现（可无限扩展）
│   ├── legacy/                    # 原始 Pipeline 适配版（baseline）
│   ├── custom_v1/                 # 新方案 v1
│   └── custom_v2/                 # 新方案 v2
│
├── experiments/                   # 实验配置与结果
│   ├── configs/
│   │   ├── baseline.yaml
│   │   ├── exp_v1.yaml
│   │   ├── exp_v2.yaml
│   │   └── ab_test.yaml
│   └── results/
│       ├── baseline_20260909_1430/
│       ├── exp_v1_20260909_1430/
│       └── ab_test_20260909_1430/
│           ├── metrics.csv
│           ├── statistical_test.json
│           └── report.md
│
└── config.yaml                    # 全局默认配置
```

## 核心概念

### Protocol 契约

每个组件类型定义标准接口：

| 组件类型 | Protocol | 核心方法 |
|---------|----------|---------|
| DataLoader | `DataLoaderProtocol` | `get_train_loader()`, `get_val_loader()`, `get_test_loader()`, `get_data_arrays()` |
| Model | `ModelProtocol` | `forward()`, `state_dict()`, `load_state_dict()`, `save()`, `decode_output()` |
| Loss | `LossProtocol` | `forward(pred, target)` → loss 或 (loss, loss_dict) |
| Optimizer | `OptimizerProtocol` | `step()`, `zero_grad()`, `get_lr()`, `state_dict()` |
| Trainer | `TrainerProtocol` | `train()` → `TrainResult`, `evaluate()` |
| Evaluator | `EvaluatorProtocol` | `evaluate()` → `EvaluationResult`, `compute_metrics()` |

### 注册表机制

使用装饰器自动注册：

```python
from backend_framework.registry import register

@register("model", "my_custom_model")
class MyModel:
    # 必须实现 ModelProtocol
    ...
```

导入即注册，无需手动调用。

### 配置驱动组装

YAML 配置示例：

```yaml
experiment:
  name: "my_experiment"
  seed: 42

components:
  data_loader:
    type: "legacy"
    params:
      data_path: "outputs/data/multi_condition.npz"
  
  model:
    type: "legacy_dual_head"
    params:
      hidden_dim: 256
      num_layers: 3
  
  loss:
    type: "legacy_dual_head"
    params:
      miss_weight: 5.0
  
  optimizer:
    type: "legacy_adamw"
    params:
      lr: 1e-3
  
  trainer:
    type: "legacy_three_phase"
    params:
      phase1_epochs: 20
      phase3_epochs: 100
  
  evaluator:
    type: "legacy_hungarian"

output:
  save_dir: "experiments/results/${experiment.name}_${timestamp}"
```

支持变量插值：`${experiment.name}`, `${timestamp}`, `${date}`, `${time}`

## 新增后端开发指南

### 1. 创建后端目录

```bash
mkdir -p backends/my_new_backend
```

### 2. 实现组件（参考 adapters/legacy_*.py）

```python
# backends/my_new_backend/model.py
from backend_framework.protocols import ModelProtocol
from backend_framework.registry.models import register_model

@register_model("my_new_backend")
class MyNewModel:
    def __init__(self, input_dim, hidden_dim=256, ...):
        # 实现 ModelProtocol 所有方法
        ...
    
    def forward(self, x):
        ...
    
    # 必须实现的其他方法...
```

### 3. 创建 `__init__.py` 触发注册

```python
# backends/my_new_backend/__init__.py
from .model import MyNewModel
from .loss import MyNewLoss
# ... 其他组件

def register_all():
    pass  # 导入即自动通过 @register 装饰器注册
```

### 4. 在配置中使用

```yaml
components:
  model:
    type: "my_new_backend"
    params:
      hidden_dim: 512
```

## A/B 测试详解

### 配置格式

```yaml
ab_test:
  name: "my_comparison"
  seed: 42
  n_runs: 5
  statistical_test: "wilcoxon"
  alpha: 0.05
  
  variants:
    - name: "baseline"
      config: "baseline.yaml"
    - name: "new_approach"
      config: "exp_v1.yaml"
  
  primary_metric: "f1"
  secondary_metrics: ["pos_mae", "depth_mae", "recall", "precision"]
```

### 输出结果

运行后生成：

```
experiments/results/my_comparison_20260909_1430/
├── metrics.csv              # 所有运行的指标汇总
├── statistical_test.json    # 统计检验详细结果
└── report.md                # Markdown 对比报告
```

### 报告内容

- 排名表（按主指标排序）
- 两两统计显著性检验（Wilcoxon/Mann-Whitney/t-test）
- 均值±标准差对比
- 详细实验数据表

## 与现有系统集成

### 看板数据对接

实验结果的 `metrics.csv` 可直接作为 `/api/dashboard` 的数据源。

### AI 命令扩展

可在 `backend/config.py` 的 `COMMAND_META` 中新增命令：

```python
{
    "action": "switch_backend",
    "name": "切换后端",
    "description": "切换训练后端版本",
    "category": "model",
    "quick": True,
    "llm_tool": True,
    ...
}
```

## 环境要求

- Python 3.8+
- PyTorch 1.13+ (CPU 或 CUDA)
- NumPy, SciPy, PyYAML
- 原始 Pipeline 环境（`D:\研\土木水利\论文\代码\github`）

## 目录结构说明

```
backend_framework/
├── protocols/          # 契约定义（不可修改，新后端参考实现）
├── registry/           # 注册表核心
├── adapters/           # Legacy 适配器（只读，参考原始 Pipeline 接口）
├── composition/        # 组装器 + 运行器
├── cli.py              # CLI 入口
└── __init__.py

backends/
├── legacy/             # Baseline（已实现）
├── custom_v1/          # 示例：新方案 v1（待实现）
└── custom_v2/          # 示例：新方案 v2（待实现）
```

## 常见问题

### Q: 如何调试新后端组件？

A: 使用 `interactive` 模式逐步选择组件，或直接在 Python 中实例化测试：

```python
from backend_framework.registry import get
from backend_framework.composition.pipeline_builder import PipelineBuilder

# 直接获取类
MyModel = get("model", "my_backend")
model = MyModel(input_dim=100, hidden_dim=256)
```

### Q: 原始 Pipeline 接口变更怎么办？

A: 只需修改 `adapters/legacy_*.py` 中的适配代码，不影响其他后端和上层框架。

### Q: Windows 下 subprocess 编码问题？

A: 框架复用 `executor.py` 的 `_ENV` 和 `CREATE_NO_WINDOW`，适配器层直接 in-process 调用避免了 subprocess 问题。

## 许可证

内部项目，仅供桥梁健康系统团队使用。