/** PipelineFlowVisualization - 白底浅色风格 Pipeline 流程可视化 */

import { useState, useEffect, useCallback, useRef } from 'react';
import PipelineDetailCard from './PipelineDetailCard';
import ExperimentRecordPanel from './ExperimentRecordPanel';
import ModelComparisonPanel from './ModelComparisonPanel';
import { useAICommand, usePipelineMonitor } from '../../hooks/useAICommand';
import type { PipelineFlowState, PipelineSpec } from '../../lib/algorithm-types';

// 状态配置
type StatusConfig = {
  icon: string;
  color: string;
  label: string;
  badge: string;
  dot: string;
  pulse?: boolean;
};

const STATUS_CONFIG: Record<string, StatusConfig> = {
  pending: { icon: '◷', color: '#94a3b8', label: '待执行', badge: 'badge-amber', dot: 'pending' },
  running: { icon: '◈', color: '#2563eb', label: '执行中', badge: 'badge-blue', dot: 'running', pulse: true },
  completed: { icon: '◉', color: '#059669', label: '完成', badge: 'badge-green', dot: 'active' },
  failed: { icon: '✕', color: '#dc2626', label: '失败', badge: 'badge-red', dot: 'error' },
};

// 默认 pipeline 列表
const DEFAULT_PIPELINES: PipelineFlowState[] = [
  { id: 'pipeline_1_cpdv_simulation', name: 'Pipeline 1: CPDV仿真', status: 'pending', progress: 0, pipelineIndex: 1 },
  { id: 'pipeline_2_single_crack_bp', name: 'Pipeline 2: BP基线', status: 'pending', progress: 0, pipelineIndex: 2 },
  { id: 'pipeline_3_lstm_sequence', name: 'Pipeline 3: LSTM', status: 'pending', progress: 0, pipelineIndex: 3 },
  { id: 'pipeline_4_multi_crack', name: 'Pipeline 4: 多裂缝', status: 'pending', progress: 0, pipelineIndex: 4 },
  { id: 'pipeline_5_pinn', name: 'Pipeline 5: PINN', status: 'pending', progress: 0, pipelineIndex: 5 },
  { id: 'pipeline_6_cpdv_analysis', name: 'Pipeline 6: CPDV分析', status: 'pending', progress: 0, pipelineIndex: 6 },
];

type TabType = 'pipeline' | 'experiment' | 'comparison';

export default function PipelineFlowVisualization() {
  const [pipelines, setPipelines] = useState<PipelineFlowState[]>(DEFAULT_PIPELINES);
  const [selectedPipeline, setSelectedPipeline] = useState<PipelineFlowState | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('pipeline');
  
  const [, aiActions] = useAICommand();
  const { status: pipelineStatus } = usePipelineMonitor(activeTaskId);
  const wsRef = useRef<WebSocket | null>(null);

  // 从后端加载 pipeline 规格
  useEffect(() => {
    async function loadPipelines() {
      try {
        const res = await fetch('/api/algorithm/pipelines');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        if (data.pipelines && data.pipelines.length > 0) {
          const specMap = new Map<string, PipelineSpec>();
          data.pipelines.forEach((p: PipelineSpec) => {
            specMap.set(p.id, p);
          });
          
          setPipelines(prev => prev.map(p => {
            const spec = specMap.get(p.id);
            if (spec) {
              return {
                ...p,
                spec,
                name: spec.name.replace(/_/g, ' ').replace(/^[a-z]/, (c: string) => c.toUpperCase()),
              };
            }
            return p;
          }));
        }
      } catch (e) {
        console.error('Failed to load pipeline specs:', e);
      } finally {
        setLoading(false);
      }
    }
    loadPipelines();
  }, []);

  // 更新 pipeline 状态
  const updatePipelineStatus = useCallback((event: any) => {
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

  // 监听 WebSocket 进度事件
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    wsRef.current = new WebSocket(`${protocol}//${window.location.host}/ws/progress?tags=pipeline,random,cpdv`);
    
    wsRef.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        const stage = msg.stage || '';
        const tag = msg.tag || '';
        const taskId = msg.task_id || '';
        let pipelineId = null;
        
        // 优先使用 task_id 匹配（后端执行时会关联 task_id）
        if (taskId) {
          const runningPipeline = pipelines.find(p => p.status === 'running');
          if (runningPipeline) {
            pipelineId = runningPipeline.id;
          }
        }
        
        // 如果没有 task_id 映射，则使用关键词匹配
        if (!pipelineId) {
          if (tag === 'random' || stage.includes('random') || stage.includes('工况')) {
            pipelineId = 'pipeline_6_cpdv_analysis';
          } else if (tag === 'cpdv' || stage.includes('cpdv') || stage.includes('模拟')) {
            pipelineId = 'pipeline_1_cpdv_simulation';
          } else if (tag === 'pipeline') {
            if (stage.includes('train') || stage.includes('训练')) {
              pipelineId = 'pipeline_2_single_crack_bp';
            } else if (stage.includes('multi_crack')) {
              pipelineId = 'pipeline_4_multi_crack';
            } else if (stage.includes('lstm')) {
              pipelineId = 'pipeline_3_lstm_sequence';
            } else if (stage.includes('pinn')) {
              pipelineId = 'pipeline_5_pinn';
            } else if (stage.includes('analysis') || stage.includes('分析') || stage.includes('dashboard_sync')) {
              pipelineId = 'pipeline_6_cpdv_analysis';
            }
          }
        }
        
        if (pipelineId) {
          let status: 'pending' | 'running' | 'completed' | 'failed' = 'running';
          if (stage.includes('done') || stage.includes('完成') || stage.includes('success')) {
            status = 'completed';
          } else if (stage.includes('error') || stage.includes('失败')) {
            status = 'failed';
          }
          
          updatePipelineStatus({
            pipelineId,
            data: {
              status,
              progress: msg.percent ?? 0,
              message: msg.message,
              outputs: [],
              error: status === 'failed' ? msg.message : null,
            },
          });
        }
      } catch (e) {
        console.warn('WS message parse error:', e);
      }
    };
    
    wsRef.current.onerror = (err) => {
      console.warn('Pipeline WS error:', err);
    };
    
    return () => {
      wsRef.current?.close();
    };
  }, [updatePipelineStatus]);

  // 监听 pipeline 状态变化
  useEffect(() => {
    if (pipelineStatus) {
      setPipelines(prev => prev.map(p => {
        if (pipelineStatus.pipelines.includes(p.id)) {
          return {
            ...p,
            status: pipelineStatus.status as 'pending' | 'running' | 'completed' | 'failed',
            progress: pipelineStatus.progress,
            error: pipelineStatus.error,
            currentStage: pipelineStatus.current_stage ?? undefined,
            outputs: pipelineStatus.outputs,
            task_id: pipelineStatus.task_id,
          };
        }
        return p;
      }));
      
      if (pipelineStatus.status === 'completed' || pipelineStatus.status === 'failed') {
        setTimeout(() => setActiveTaskId(null), 3000);
      }
    }
  }, [pipelineStatus]);

  // 执行单个 pipeline
  const handleExecutePipeline = useCallback(async (pipelineId: string) => {
    try {
      const response = await aiActions.execute('pipeline.execute', {
        pipelines: [pipelineId],
        mode: 'quick',
        async: true,
        record_experiment: true,
      });
      
      if (response.result?.task_id) {
        setActiveTaskId(response.result.task_id);
        
        setPipelines(prev => prev.map(p => {
          if (p.id === pipelineId) {
            return {
              ...p,
              status: 'running',
              progress: 5,  // Start at 5% to show it's running
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

  // 点击 pipeline 节点
  const handlePipelineClick = useCallback((pipeline: PipelineFlowState) => {
    setSelectedPipeline(prev => prev?.id === pipeline.id ? null : pipeline);
  }, []);

  // 停止所有执行
  if (loading) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        fontFamily: 'var(--font-mono)',
      }}>
        <div className="text-secondary" style={{ fontSize: 'var(--text-sm)', letterSpacing: 'var(--tracking-wider)' }}>
          LOADING PIPELINE CONFIGURATION...
        </div>
      </div>
    );
  }

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      overflow: 'hidden',
    }}>
      {/* Tab Navigation */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--line)',
        background: 'var(--card)',
        padding: '0 20px',
      }}>
        {([
          { id: 'pipeline' as TabType, label: 'Pipeline 流程', icon: '◈' },
          { id: 'experiment' as TabType, label: '实验记录', icon: '◫' },
          { id: 'comparison' as TabType, label: '模型对比', icon: '⚖' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="font-medium"
            style={{
              padding: '12px 16px',
              fontSize: 'var(--text-sm)',
              color: activeTab === tab.id ? 'var(--blue)' : 'var(--ink-secondary)',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid var(--blue)' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.15s',
              letterSpacing: 'var(--tracking-wide)',
            }}
          >
            <span style={{ fontSize: 'var(--text-base)' }}>{tab.icon}</span>
            {tab.label}
          </button>
        )))}
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'pipeline' && (
          <PipelineTab
            pipelines={pipelines}
            selectedPipeline={selectedPipeline}
            onPipelineClick={handlePipelineClick}
            onExecutePipeline={handleExecutePipeline}
          />
        )}
        {activeTab === 'experiment' && (
          <ExperimentRecordPanel
            onClose={() => setActiveTab('pipeline')}
            onViewHistory={() => {}}
            onPipelineResult={undefined}
          />
        )}
        {activeTab === 'comparison' && (
          <ModelComparisonPanel
            onClose={() => setActiveTab('pipeline')}
          />
        )}
      </div>
    </div>
  );
}

// Pipeline Tab 组件
function PipelineTab({
  pipelines,
  selectedPipeline,
  onPipelineClick,
  onExecutePipeline,
}: {
  pipelines: PipelineFlowState[];
  selectedPipeline: PipelineFlowState | null;
  onPipelineClick: (pipeline: PipelineFlowState) => void;
  onExecutePipeline: (pipelineId: string) => void;
}) {
  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      padding: 20,
      gap: 16,
      overflow: 'auto',
    }}>
      {/* Pipeline Flow Chart */}
      <div className="card" style={{ padding: 20 }}>
        <div className="section-title">
          Pipeline 执行状态
        </div>

        {/* Pipeline Nodes Container */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
          overflowX: 'auto',
          padding: '12px 0',
        }}>
          {pipelines.map((pipeline, index) => (
            <div key={pipeline.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <PipelineStatusNode
                pipeline={pipeline}
                isSelected={selectedPipeline?.id === pipeline.id}
                onClick={onPipelineClick}
                onExecute={onExecutePipeline}
              />
              {index < pipelines.length - 1 && (
                <div style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--ink-tertiary)',
                  marginTop: 28,
                  flexShrink: 0,
                }}>
                  {'->'}
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
          onClose={() => onPipelineClick(selectedPipeline)}
          onExecute={onExecutePipeline}
        />
      )}

      {/* Empty State */}
      {!selectedPipeline && (
        <div className="card fade-in" style={{
          padding: 40,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          flex: 1,
          minHeight: 200,
        }}>
          <div 
            className="font-mono font-semibold"
            style={{ 
              fontSize: 'var(--text-2xl)', 
              marginBottom: 16,
              color: 'var(--ink-tertiary)',
              opacity: 0.5,
            }}
          >
            ◈
          </div>
          <div className="font-semibold text-lg" style={{ marginBottom: 8, color: 'var(--ink)' }}>
            选择 Pipeline 查看详情
          </div>
          <div className="text-secondary" style={{ 
            fontSize: 'var(--text-sm)', 
            textAlign: 'center', 
            lineHeight: 'var(--leading-relaxed)',
            maxWidth: 320,
          }}>
            <div>点击上方 Pipeline 节点查看详细执行信息</div>
            <div style={{ marginTop: 4 }}>点击 ▶ 按钮可独立执行单个 Pipeline</div>
          </div>
        </div>
      )}
    </div>
  );
}

// Pipeline Status Node 组件
function PipelineStatusNode({
  pipeline,
  isSelected,
  onClick,
  onExecute,
}: {
  pipeline: PipelineFlowState;
  isSelected: boolean;
  onClick: (pipeline: PipelineFlowState) => void;
  onExecute?: (pipelineId: string) => void;
}) {
  const statusConfig = STATUS_CONFIG[pipeline.status];
  const isRunning = pipeline.status === 'running';
  const canExecute = pipeline.status === 'pending';

  const handleExecute = (e: React.MouseEvent) => {
    e.stopPropagation();
    onExecute?.(pipeline.id);
  };

  return (
    <div
      onClick={() => onClick(pipeline)}
      className="card card-hover"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
        padding: '14px 12px',
        minWidth: 120,
        maxWidth: 140,
        position: 'relative',
        cursor: 'pointer',
        borderColor: isSelected ? 'var(--blue)' : isRunning ? 'var(--blue-border)' : 'var(--line)',
        boxShadow: isSelected ? 'var(--shadow-md)' : 'var(--shadow)',
      }}
    >
      {/* Pipeline 编号 */}
      <div style={{
        position: 'absolute',
        top: -10,
        left: -10,
        width: 24,
        height: 24,
        borderRadius: '50%',
        background: isRunning ? 'var(--blue)' : isSelected ? 'var(--blue)' : 'var(--card)',
        border: `2px solid ${isRunning ? 'var(--blue)' : isSelected ? 'var(--blue)' : 'var(--line)'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 'var(--text-xs)',
        fontWeight: 'var(--weight-bold)',
        color: '#fff',
        fontFamily: 'var(--font-mono)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        {pipeline.pipelineIndex}
      </div>

      {/* Status Icon */}
      <div 
        className="font-mono"
        style={{ 
          fontSize: 'var(--text-xl)', 
          marginTop: 4,
          color: statusConfig.color,
          ...(statusConfig.pulse ? { animation: 'pulse 1.5s ease-in-out infinite' } : {}),
        }}
      >
        {statusConfig.icon}
      </div>

      {/* Name */}
      <div className="font-medium text-truncate" style={{
        fontSize: 'var(--text-sm)',
        color: 'var(--ink)',
        textAlign: 'center',
        lineHeight: 'var(--leading-tight)',
        maxWidth: 120,
      }}>
        {pipeline.name}
      </div>

      {/* Status Label */}
      <div className="font-mono text-xs" style={{
        color: statusConfig.color,
        fontWeight: 'var(--weight-medium)',
        letterSpacing: 'var(--tracking-wider)',
      }}>
        {statusConfig.label}
      </div>

      {/* Progress Bar */}
      {isRunning && (
        <div className="progress-bar" style={{ width: '100%', marginTop: 4 }}>
          <div 
            className="progress-bar-fill"
            style={{ width: `${pipeline.progress || 0}%` }}
          />
        </div>
      )}

      {/* Execute Button */}
      {canExecute && (
        <button
          onClick={handleExecute}
          className="font-mono"
          style={{
            position: 'absolute',
            bottom: -10,
            right: -10,
            width: 26,
            height: 26,
            borderRadius: '50%',
            background: 'var(--green)',
            border: '2px solid var(--card)',
            color: '#fff',
            fontSize: 11,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow)',
          }}
          title="执行此 Pipeline"
        >
          ▶
        </button>
      )}
    </div>
  );
}
