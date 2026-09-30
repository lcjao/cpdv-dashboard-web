# Pipeline 流程可视化设计文档

## 概述

在算法看板主界面中添加独立的Pipeline流程图组件，用于实时显示pipeline各阶段的执行状态。当AI命令控制台执行pipeline时，通过WebSocket实时更新状态。

## 需求分析

### 用户需求
1. 在算法看板主界面中添加一个独立的Pipeline流程图组件
2. 显示所有pipeline的执行状态（待执行、执行中、完成、失败）
3. 通过WebSocket实时同步AI命令控制台的执行指令
4. 采用水平流程图布局
5. 显示完整信息：pipeline名称、当前状态、执行进度百分比、开始时间、持续时间、输出文件、错误信息
6. 移除原有的模块树和右侧面板

### 技术需求
1. 前端组件：创建新的PipelineFlowVisualization组件
2. 后端支持：利用现有的AI命令系统和WebSocket
3. 数据流：AI命令控制台 → 后端WebSocket → 前端Pipeline流程图

## 设计方案

### 布局设计

```
┌─────────────────────────────────────────────────────────────┐
│ 算法看板主界面                                              │
├─────────────────────────────────────────────────────────────┤
│ [返回] [同步代码库] [搜索...]           [Pipeline流程可视化] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Pipeline 执行状态                                     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │  [Pipeline 1] → [Pipeline 2] → [Pipeline 3] → ...   │  │
│  │     ✅           🔄           ⏳           ...     │  │
│  │   完成         执行中       待执行                   │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Pipeline 详细信息                                     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Pipeline 1: CPDV仿真与数据生成                        │  │
│  │ 状态: ✅ 完成 | 进度: 100% | 耗时: 5分钟             │  │
│  │ 输出: data/cpdv_signals.csv, figures/cpdv/*.png      │  │
│  │                                                       │  │
│  │ Pipeline 2: 单裂缝BP神经网络                          │  │
│  │ 状态: 🔄 执行中 | 进度: 45% | 耗时: 2分钟            │  │
│  │ 当前阶段: 模型训练中...                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 组件结构

1. **PipelineFlowVisualization** - 主组件
   - 管理pipeline状态数据
   - 处理WebSocket连接
   - 渲染流程图和详细信息

2. **PipelineStatusNode** - 单个pipeline状态节点
   - 显示pipeline名称和状态图标
   - 显示进度条和基本信息

3. **PipelineDetailCard** - pipeline详细信息卡片
   - 显示完整的pipeline执行信息
   - 包括状态、进度、时间、输出文件、错误信息

### 数据流

```
AI命令控制台 → 后端pipeline执行 → WebSocket事件 → 前端PipelineFlowVisualization
```

### 状态定义

```typescript
type PipelineStatus = 'pending' | 'running' | 'completed' | 'failed';

interface PipelineState {
  id: string;
  name: string;
  status: PipelineStatus;
  progress: number; // 0-100
  startTime?: string;
  duration?: string;
  outputs?: string[];
  error?: string;
  currentStage?: string;
}
```

### WebSocket事件

```typescript
// 事件类型
interface PipelineEvent {
  type: 'pipeline_started' | 'pipeline_progress' | 'pipeline_completed' | 'pipeline_failed';
  pipelineId: string;
  data: {
    status: PipelineStatus;
    progress?: number;
    message?: string;
    outputs?: string[];
    error?: string;
  };
}
```

### 交互逻辑

1. **实时更新**：通过WebSocket接收pipeline执行状态更新
2. **点击查看详情**：点击pipeline节点显示详细信息
3. **手动刷新**：提供刷新按钮手动获取最新状态
4. **错误处理**：pipeline失败时显示错误信息和重试选项

## 实现步骤

### 1. 创建PipelineFlowVisualization组件
- 定义组件接口和状态管理
- 实现WebSocket连接和事件处理
- 渲染流程图和详细信息

### 2. 修改AlgorithmDashboard
- 移除模块树和右侧面板
- 集成PipelineFlowVisualization组件
- 调整布局为全屏显示

### 3. 后端支持
- 确保现有的AI命令系统支持pipeline状态事件
- 验证WebSocket事件格式

### 4. 测试和调试
- 测试WebSocket连接和事件接收
- 验证状态更新和UI渲染
- 处理错误情况

## 文件结构

```
frontend/src/
├── components/
│   └── algorithm/
│       ├── PipelineFlowVisualization.tsx  # 新组件
│       ├── PipelineStatusNode.tsx         # 新组件
│       └── PipelineDetailCard.tsx         # 新组件
├── hooks/
│   └── useAICommand.ts                   # 已有，需要验证WebSocket支持
└── lib/
    └── algorithm-types.ts                # 需要添加Pipeline状态类型
```

## 验证标准

1. ✅ Pipeline流程图正确显示所有pipeline
2. ✅ WebSocket实时更新pipeline状态
3. ✅ 点击pipeline节点显示详细信息
4. ✅ 错误状态正确显示
5. ✅ 界面布局符合设计草图

## 后续优化

1. 添加pipeline执行历史记录
2. 支持pipeline执行控制（暂停、取消）
3. 添加pipeline依赖关系可视化
4. 支持自定义pipeline视图