# Pipeline 流程可视化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在算法看板主界面中添加独立的Pipeline流程图组件，实时显示pipeline各阶段的执行状态，并通过WebSocket与AI命令控制台同步。

**Architecture:** 创建新的PipelineFlowVisualization组件，包含PipelineStatusNode和PipelineDetailCard子组件。修改AlgorithmDashboard移除模块树和右侧面板，集成新的流程可视化组件。利用现有的useAICommand hooks和WebSocket实现状态同步。

**Tech Stack:** React, TypeScript, WebSocket, 现有useAICommand hooks

---

### Task 1: 添加Pipeline状态类型定义

**Files:**
- Modify: `frontend/src/lib/algorithm-types.ts:491-541`

- [ ] **Step 1: 在algorithm-types.ts中添加Pipeline流程可视化相关类型**

在文件末尾（第541行后）添加以下类型定义：

```typescript
// ─────────────────────────────────────────────────────────────────────
// Pipeline 流程可视化
// ─────────────────────────────────────────────────────────────────────

export type PipelineFlowStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface PipelineFlowState {
  id: string;
  name: string;
  status: PipelineFlowStatus;
  progress: number; // 0-100
  startTime?: string;
  duration?: string;
  outputs?: string[];
  error?: string;
  currentStage?: string;
  pipelineIndex: number; // 1-6 对应pipeline_1到pipeline_6
}

export interface PipelineFlowEvent {
  type: 'pipeline_started' | 'pipeline_progress' | 'pipeline_completed' | 'pipeline_failed';
  pipelineId: string;
  data: {
    status: PipelineFlowStatus;
    progress?: number;
    message?: string;
    outputs?: string[];
    error?: string;
  };
}

export interface PipelineFlowVisualizationProps {
  onBack?: () => void;
  onRefresh?: () => void;
}
```

- [ ] **Step 2: 验证类型定义**

运行TypeScript检查确保类型定义正确：
```bash
cd D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend
npx tsc --noEmit
```

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/lib/algorithm-types.ts
git commit -m "feat: add pipeline flow visualization types"
```

### Task 2: 创建PipelineStatusNode组件

**Files:**
- Create: `frontend/src/components/algorithm/PipelineStatusNode.tsx`

- [ ] **Step 1: 创建PipelineStatusNode组件**

```tsx
/** PipelineStatusNode - 单个pipeline状态节点 */

import { type PipelineFlowState } from '../../lib/algorithm-types';

interface PipelineStatusNodeProps {
  pipeline: PipelineFlowState;
  isSelected: boolean;
  onClick: (pipeline: PipelineFlowState) => void;
}

const STATUS_CONFIG = {
  pending: { icon: '⏳', color: 'var(--sub)', label: '待执行' },
  running: { icon: '🔄', color: '#FF9800', label: '执行中' },
  completed: { icon: '✅', color: '#00C853', label: '完成' },
  failed: { icon: '❌', color: '#FF3D00', label: '失败' },
};

export default function PipelineStatusNode({
  pipeline,
  isSelected,
  onClick,
}: PipelineStatusNodeProps) {
  const statusConfig = STATUS_CONFIG[pipeline.status];

  return (
    <div
      onClick={() => onClick(pipeline)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
        padding: '12px 16px',
        background: isSelected ? 'var(--blue-bg)' : 'var(--card)',
        border: `2px solid ${isSelected ? 'var(--blue)' : 'var(--line)'}`,
        borderRadius: 12,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        minWidth: 140,
        boxShadow: isSelected ? '0 0 0 3px var(--blue-bg)' : '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      {/* Pipeline名称 */}
      <div style={{
        fontSize: 12,
        fontWeight: 600,
        color: 'var(--ink)',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        maxWidth: 120,
      }}>
        {pipeline.name}
      </div>

      {/* 状态图标 */}
      <div style={{
        fontSize: 24,
        lineHeight: 1,
      }}>
        {statusConfig.icon}
      </div>

      {/* 状态标签 */}
      <div style={{
        fontSize: 10,
        fontWeight: 600,
        color: statusConfig.color,
        textTransform: 'uppercase',
      }}>
        {statusConfig.label}
      </div>

      {/* 进度条 */}
      {pipeline.status === 'running' && (
        <div style={{
          width: '100%',
          height: 4,
          background: 'rgba(255,255,255,.1)',
          borderRadius: 2,
          overflow: 'hidden',
        }}>
          <div
            style={{
              width: `${Math.min(100, Math.max(0, pipeline.progress))}%`,
              height: '100%',
              background: statusConfig.color,
              transition: 'width .3s ease',
            }}
          />
        </div>
      )}

      {/* 进度百分比 */}
      {pipeline.status === 'running' && (
        <div style={{
          fontSize: 10,
          color: 'var(--sub)',
          fontFamily: 'var(--mono)',
        }}>
          {Math.round(pipeline.progress)}%
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 验证组件**

运行TypeScript检查确保组件类型正确：
```bash
cd D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend
npx tsc --noEmit
```

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/components/algorithm/PipelineStatusNode.tsx
git commit -m "feat: add PipelineStatusNode component"
```

### Task 3: 创建PipelineDetailCard组件

**Files:**
- Create: `frontend/src/components/algorithm/PipelineDetailCard.tsx`

- [ ] **Step 1: 创建PipelineDetailCard组件**

```tsx
/** PipelineDetailCard - pipeline详细信息卡片 */

import { type PipelineFlowState } from '../../lib/algorithm-types';

interface PipelineDetailCardProps {
  pipeline: PipelineFlowState;
  onClose: () => void;
}

const STATUS_CONFIG = {
  pending: { icon: '⏳', color: 'var(--sub)', label: '待执行' },
  running: { icon: '🔄', color: '#FF9800', label: '执行中' },
  completed: { icon: '✅', color: '#00C853', label: '完成' },
  failed: { icon: '❌', color: '#FF3D00', label: '失败' },
};

export default function PipelineDetailCard({
  pipeline,
  onClose,
}: PipelineDetailCardProps) {
  const statusConfig = STATUS_CONFIG[pipeline.status];

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'linear-gradient(180deg, rgba(47,111,237,0.03) 0%, rgba(255,255,255,0) 100%)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            display: 'inline-flex',
            width: 32,
            height: 32,
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 8,
            background: `${statusConfig.color}20`,
            color: statusConfig.color,
            fontSize: 16,
          }}>
            {statusConfig.icon}
          </span>
          <div>
            <div style={{
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--ink)',
            }}>{pipeline.name}</div>
            <div style={{
              fontSize: 10,
              color: 'var(--sub)',
              fontFamily: 'var(--mono)',
            }}>
              ID: {pipeline.id}
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            padding: '4px 10px',
            fontSize: 11,
            background: 'transparent',
            border: '1px solid var(--line)',
            borderRadius: 6,
            color: 'var(--sub)',
            cursor: 'pointer',
          }}
        >
          关闭
        </button>
      </div>

      {/* Content */}
      <div style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}>
        {/* 状态信息 */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <div style={{
            padding: '8px 12px',
            background: 'var(--bg)',
            borderRadius: 8,
            border: '1px solid var(--line)',
            flex: 1,
            minWidth: 120,
          }}>
            <div style={{ fontSize: 10, color: 'var(--sub)', marginBottom: 4 }}>状态</div>
            <div style={{
              fontSize: 13,
              fontWeight: 600,
              color: statusConfig.color,
            }}>
              {statusConfig.label}
            </div>
          </div>

          <div style={{
            padding: '8px 12px',
            background: 'var(--bg)',
            borderRadius: 8,
            border: '1px solid var(--line)',
            flex: 1,
            minWidth: 120,
          }}>
            <div style={{ fontSize: 10, color: 'var(--sub)', marginBottom: 4 }}>进度</div>
            <div style={{
              fontSize: 13,
              fontWeight: 600,
              fontFamily: 'var(--mono)',
              color: 'var(--ink)',
            }}>
              {Math.round(pipeline.progress)}%
            </div>
          </div>

          {pipeline.startTime && (
            <div style={{
              padding: '8px 12px',
              background: 'var(--bg)',
              borderRadius: 8,
              border: '1px solid var(--line)',
              flex: 1,
              minWidth: 120,
            }}>
              <div style={{ fontSize: 10, color: 'var(--sub)', marginBottom: 4 }}>开始时间</div>
              <div style={{
                fontSize: 13,
                color: 'var(--ink)',
                fontFamily: 'var(--mono)',
              }}>
                {new Date(pipeline.startTime).toLocaleTimeString()}
              </div>
            </div>
          )}

          {pipeline.duration && (
            <div style={{
              padding: '8px 12px',
              background: 'var(--bg)',
              borderRadius: 8,
              border: '1px solid var(--line)',
              flex: 1,
              minWidth: 120,
            }}>
              <div style={{ fontSize: 10, color: 'var(--sub)', marginBottom: 4 }}>耗时</div>
              <div style={{
                fontSize: 13,
                color: 'var(--ink)',
                fontFamily: 'var(--mono)',
              }}>
                {pipeline.duration}
              </div>
            </div>
          )}
        </div>

        {/* 当前阶段 */}
        {pipeline.currentStage && (
          <div style={{
            padding: '10px 12px',
            background: 'rgba(255,152,0,0.08)',
            border: '1px solid rgba(255,152,0,0.3)',
            borderRadius: 8,
            fontSize: 12,
            color: 'var(--ink)',
          }}>
            <span style={{ fontWeight: 600, color: '#FF9800' }}>当前阶段: </span>
            {pipeline.currentStage}
          </div>
        )}

        {/* 输出文件 */}
        {pipeline.outputs && pipeline.outputs.length > 0 && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 8 }}>
              输出文件
            </div>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              maxHeight: 120,
              overflow: 'auto',
              padding: '8px',
              background: 'var(--bg)',
              borderRadius: 8,
              border: '1px solid var(--line)',
            }}>
              {pipeline.outputs.map((output, idx) => (
                <div key={idx} style={{
                  fontSize: 11,
                  color: 'var(--ink)',
                  fontFamily: 'var(--mono)',
                  wordBreak: 'break-all',
                }}>
                  {output}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 错误信息 */}
        {pipeline.error && (
          <div style={{
            padding: '12px',
            background: 'rgba(255,61,0,0.08)',
            border: '1px solid rgba(255,61,0,0.3)',
            borderRadius: 8,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#FF3D00', marginBottom: 4 }}>
              ❌ 错误信息
            </div>
            <div style={{
              fontSize: 11,
              color: 'var(--sub)',
              fontFamily: 'var(--mono)',
              wordBreak: 'break-all',
            }}>
              {pipeline.error}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证组件**

运行TypeScript检查确保组件类型正确：
```bash
cd D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend
npx tsc --noEmit
```

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/components/algorithm/PipelineDetailCard.tsx
git commit -m "feat: add PipelineDetailCard component"
```

### Task 4: 创建PipelineFlowVisualization主组件

**Files:**
- Create: `frontend/src/components/algorithm/PipelineFlowVisualization.tsx`

- [ ] **Step 1: 创建PipelineFlowVisualization主组件**

```tsx
/** PipelineFlowVisualization - Pipeline流程可视化主组件 */

import { useState, useEffect, useCallback } from 'react';
import PipelineStatusNode from './PipelineStatusNode';
import PipelineDetailCard from './PipelineDetailCard';
import { useAICommand, usePipelineMonitor } from '../../hooks/useAICommand';
import type { PipelineFlowState, PipelineFlowEvent } from '../../lib/algorithm-types';

// 默认pipeline列表
const DEFAULT_PIPELINES: PipelineFlowState[] = [
  { id: 'pipeline_1_cpdv_simulation', name: 'Pipeline 1', status: 'pending', progress: 0, pipelineIndex: 1 },
  { id: 'pipeline_2_single_crack_bp', name: 'Pipeline 2', status: 'pending', progress: 0, pipelineIndex: 2 },
  { id: 'pipeline_3_lstm_sequence', name: 'Pipeline 3', status: 'pending', progress: 0, pipelineIndex: 3 },
  { id: 'pipeline_4_multi_crack', name: 'Pipeline 4', status: 'pending', progress: 0, pipelineIndex: 4 },
  { id: 'pipeline_5_pinn', name: 'Pipeline 5', status: 'pending', progress: 0, pipelineIndex: 5 },
  { id: 'pipeline_6_cpdv_analysis', name: 'Pipeline 6', status: 'pending', progress: 0, pipelineIndex: 6 },
];

export default function PipelineFlowVisualization({
  onBack,
  onRefresh,
}: {
  onBack?: () => void;
  onRefresh?: () => void;
}) {
  const [pipelines, setPipelines] = useState<PipelineFlowState[]>(DEFAULT_PIPELINES);
  const [selectedPipeline, setSelectedPipeline] = useState<PipelineFlowState | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  
  const [aiState, aiActions] = useAICommand();
  const { status: pipelineStatus } = usePipelineMonitor(activeTaskId);

  // 更新pipeline状态
  const updatePipelineStatus = useCallback((event: PipelineFlowEvent) => {
    setPipelines(prev => prev.map(p => {
      if (p.id === event.pipelineId) {
        return {
          ...p,
          status: event.data.status,
          progress: event.data.progress ?? p.progress,
          error: event.data.error,
          currentStage: event.data.message,
          outputs: event.data.outputs ?? p.outputs,
        };
      }
      return p;
    }));
  }, []);

  // 监听WebSocket事件
  useEffect(() => {
    const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ai/ws?tags=pipeline`);
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type && msg.pipelineId) {
          updatePipelineStatus(msg as PipelineFlowEvent);
        }
      } catch (e) {
        console.warn('WS message parse error:', e);
      }
    };
    
    return () => ws.close();
  }, [updatePipelineStatus]);

  // 监听pipeline状态变化
  useEffect(() => {
    if (pipelineStatus) {
      setPipelines(prev => prev.map(p => {
        if (p.id === pipelineStatus.task_id || 
            pipelineStatus.pipelines.includes(p.id)) {
          return {
            ...p,
            status: pipelineStatus.status as any,
            progress: pipelineStatus.progress,
            error: pipelineStatus.error,
            currentStage: pipelineStatus.current_stage,
            outputs: pipelineStatus.outputs,
          };
        }
        return p;
      }));
    }
  }, [pipelineStatus]);

  // 执行pipeline
  const handleExecutePipeline = useCallback(async (pipelineIds: string[]) => {
    try {
      const response = await aiActions.execute('pipeline.execute', {
        pipelines: pipelineIds,
        mode: 'quick',
        async: true,
      });
      
      if (response.result?.task_id) {
        setActiveTaskId(response.result.task_id);
        
        // 更新pipeline状态为running
        setPipelines(prev => prev.map(p => {
          if (pipelineIds.includes(p.id)) {
            return {
              ...p,
              status: 'running',
              progress: 0,
              startTime: new Date().toISOString(),
            };
          }
          return p;
        }));
      }
    } catch (error) {
      console.error('Execute pipeline error:', error);
    }
  }, [aiActions]);

  // 点击pipeline节点
  const handlePipelineClick = useCallback((pipeline: PipelineFlowState) => {
    setSelectedPipeline(prev => prev?.id === pipeline.id ? null : pipeline);
  }, []);

  // 刷新状态
  const handleRefresh = useCallback(async () => {
    if (activeTaskId) {
      try {
        const status = await aiActions.getPipelineStatus(activeTaskId);
        if (status) {
          setPipelines(prev => prev.map(p => {
            if (status.pipelines.includes(p.id)) {
              return {
                ...p,
                status: status.status as any,
                progress: status.progress,
                error: status.error,
                currentStage: status.current_stage,
                outputs: status.outputs,
              };
            }
            return p;
          }));
        }
      } catch (error) {
        console.error('Refresh status error:', error);
      }
    }
    onRefresh?.();
  }, [activeTaskId, aiActions, onRefresh]);

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        background: 'var(--card)',
        borderBottom: '1px solid var(--line)',
        gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
          {/* Back Button */}
          <button
            type="button"
            onClick={onBack}
            style={{
              width: 28,
              height: 28,
              padding: 0,
              fontSize: 12,
              fontWeight: 700,
              background: 'var(--bg)',
              color: 'var(--ink)',
              border: '1px solid var(--line)',
              borderRadius: 7,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ↩
          </button>

          {/* Title */}
          <div style={{
            fontSize: 16,
            fontWeight: 700,
            color: 'var(--ink)',
          }}>
            Pipeline 流程可视化
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => handleExecutePipeline(pipelines.filter(p => p.status === 'pending').map(p => p.id))}
            disabled={aiState.loading || pipelines.every(p => p.status === 'running')}
            style={{
              padding: '7px 12px',
              fontSize: 11,
              fontWeight: 600,
              background: 'var(--green)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: aiState.loading ? 'not-allowed' : 'pointer',
              opacity: aiState.loading ? 0.6 : 1,
            }}
          >
            {aiState.loading ? '执行中...' : '执行全部'}
          </button>
          <button
            onClick={handleRefresh}
            style={{
              padding: '7px 12px',
              fontSize: 11,
              fontWeight: 600,
              background: 'var(--blue)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
            }}
          >
            刷新状态
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        padding: 20,
        gap: 20,
        overflow: 'auto',
      }}>
        {/* Pipeline Flow Chart */}
        <div style={{
          background: 'var(--card)',
          border: '1px solid var(--line)',
          borderRadius: 12,
          padding: 20,
        }}>
          <div style={{
            fontSize: 14,
            fontWeight: 700,
            color: 'var(--ink)',
            marginBottom: 16,
          }}>
            Pipeline 执行状态
          </div>

          {/* Pipeline Nodes Container */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            overflowX: 'auto',
            padding: '10px 0',
          }}>
            {pipelines.map((pipeline, index) => (
              <div key={pipeline.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <PipelineStatusNode
                  pipeline={pipeline}
                  isSelected={selectedPipeline?.id === pipeline.id}
                  onClick={handlePipelineClick}
                />
                {index < pipelines.length - 1 && (
                  <div style={{
                    fontSize: 16,
                    color: 'var(--sub)',
                    flexShrink: 0,
                  }}>
                    →
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline Detail Card */}
        {selectedPipeline && (
          <PipelineDetailCard
            pipeline={selectedPipeline}
            onClose={() => setSelectedPipeline(null)}
          />
        )}

        {/* Empty State */}
        {!selectedPipeline && (
          <div style={{
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: 12,
            padding: 40,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--sub)',
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📊</div>
            <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>
              选择Pipeline查看详情
            </div>
            <div style={{ fontSize: 13, textAlign: 'center', lineHeight: 1.6 }}>
              <div>点击上方Pipeline节点查看详细执行信息</div>
              <div style={{ marginTop: 4 }}>或点击"执行全部"开始运行所有Pipeline</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证组件**

运行TypeScript检查确保组件类型正确：
```bash
cd D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend
npx tsc --noEmit
```

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/components/algorithm/PipelineFlowVisualization.tsx
git commit -m "feat: add PipelineFlowVisualization main component"
```

### Task 5: 修改AlgorithmDashboard集成Pipeline流程可视化

**Files:**
- Modify: `frontend/src/components/algorithm/AlgorithmDashboard.tsx:1-777`

- [ ] **Step 1: 修改AlgorithmDashboard组件**

替换AlgorithmDashboard.tsx的全部内容为以下代码：

```tsx
/** AlgorithmDashboard - 算法代码库看板主页面（Pipeline流程可视化版） */

import { useState, useCallback } from 'react';
import PipelineFlowVisualization from './PipelineFlowVisualization';
import { useSync } from '../../hooks/useAlgorithmDashboard';

export default function AlgorithmDashboard({
  onBack,
}: {
  onBack?: () => void;
}) {
  const [refreshKey, setRefreshKey] = useState(0);
  const { syncState, startSync } = useSync();

  const handleRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
  }, []);

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      overflow: 'hidden',
    }}>
      {/* Top Bar */}
      <div style={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        background: 'var(--card)',
        borderBottom: '1px solid var(--line)',
        gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
          {/* Back Button */}
          <button
            type="button"
            onClick={onBack}
            style={{
              width: 28,
              height: 28,
              padding: 0,
              fontSize: 12,
              fontWeight: 700,
              background: 'var(--bg)',
              color: 'var(--ink)',
              border: '1px solid var(--line)',
              borderRadius: 7,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ↩
          </button>

          {/* Title */}
          <div style={{
            fontSize: 16,
            fontWeight: 700,
            color: 'var(--ink)',
          }}>
            算法看板
          </div>
        </div>

        {/* Sync Button */}
        <button
          onClick={() => startSync({ full: true })}
          disabled={syncState.status === 'started' || syncState.status === 'running'}
          style={{
            padding: '7px 10px',
            fontSize: 11,
            fontWeight: 600,
            background: 'var(--blue)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            cursor: syncState.status === 'started' || syncState.status === 'running' ? 'not-allowed' : 'pointer',
            opacity: syncState.status === 'started' || syncState.status === 'running' ? 0.6 : 1,
            whiteSpace: 'nowrap',
          }}
        >
          {syncState.status === 'running' ? '同步中' : syncState.status === 'started' ? '启动中' : '同步代码库'}
        </button>
      </div>

      {/* Main Content - Pipeline Flow Visualization */}
      <div style={{
        flex: 1,
        overflow: 'hidden',
      }}>
        <PipelineFlowVisualization
          key={refreshKey}
          onBack={onBack}
          onRefresh={handleRefresh}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证修改**

运行TypeScript检查确保修改正确：
```bash
cd D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend
npx tsc --noEmit
```

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/components/algorithm/AlgorithmDashboard.tsx
git commit -m "refactor: simplify AlgorithmDashboard to show PipelineFlowVisualization"
```

### Task 6: 测试和验证

**Files:**
- None (testing only)

- [ ] **Step 1: 启动开发服务器**

```bash
cd D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend
npm run dev
```

- [ ] **Step 2: 测试Pipeline流程可视化**

1. 访问算法看板页面
2. 验证Pipeline流程图正确显示6个pipeline节点
3. 点击pipeline节点验证详情卡片显示
4. 点击"执行全部"按钮测试pipeline执行
5. 验证WebSocket实时更新pipeline状态

- [ ] **Step 3: 测试错误处理**

1. 模拟pipeline执行失败
2. 验证错误状态正确显示
3. 验证错误信息正确显示

- [ ] **Step 4: 提交最终更改**

```bash
git add .
git commit -m "feat: complete Pipeline flow visualization implementation"
```

## 完成标准

1. ✅ Pipeline流程图正确显示所有6个pipeline
2. ✅ WebSocket实时更新pipeline状态
3. ✅ 点击pipeline节点显示详细信息
4. ✅ 错误状态正确显示
5. ✅ 界面布局符合设计草图
6. ✅ 移除原有的模块树和右侧面板
7. ✅ 所有TypeScript类型检查通过
8. ✅ 功能测试通过