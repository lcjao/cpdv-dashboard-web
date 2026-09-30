/** PipelineProgressPanel - 实时 Pipeline/训练进度面板 */

import { useEffect } from 'react';
import { useTagProgress } from '../../lib/progress-context';
import { usePipelineMonitor, useAICommand } from '../../hooks/useAICommand';

interface PipelineProgressPanelProps {
  /** 当前运行的 pipeline/train 任务 ID */
  activeRunId?: string;
  /** 运行名称 */
  runName?: string;
  /** 关闭回调 */
  onClose: () => void;
  /** 取消回调 */
  onCancel?: () => void;
  /** 完成回调 - 触发 dashboard 同步 */
  onComplete?: () => void;
}

export default function PipelineProgressPanel({
  activeRunId,
  runName = 'Pipeline 执行中',
  onClose,
  onCancel,
  onComplete,
}: PipelineProgressPanelProps) {
  const [, { cancel: aiCancel }] = useAICommand();
  // 订阅 train 和 pipeline 两类进度事件（原有 progress-context）
  const trainProgress = useTagProgress('train');
  const pipelineProgress = useTagProgress('pipeline');
  
  // 同时监听 AI Command WebSocket（用于 pipeline.execute 等命令触发的 pipeline）
  const { status: aiPipelineStatus } = usePipelineMonitor(activeRunId || null);

  // 触发 onComplete 回调（用于 dashboard sync）
  useEffect(() => {
    if (onComplete && aiPipelineStatus && 
        (aiPipelineStatus.status === 'completed' || aiPipelineStatus.status === 'failed')) {
      onComplete();
    }
  }, [aiPipelineStatus?.status, onComplete]);

  // 优先显示 pipeline 进度，其次 train 进度，最后 AI Command pipeline 状态
  // 合并进度信息：如果 AI Command 有运行中的 pipeline，优先使用
  let progress = pipelineProgress ?? trainProgress;
  let isRunning = progress && progress.stage !== 'done' && progress.stage !== 'error';
  
  // 如果 AI Command pipeline 正在运行，使用它的状态
  if (aiPipelineStatus && aiPipelineStatus.status === 'running') {
    // 将 AI Command PipelineTaskStatus 转换为兼容格式
    progress = {
      id: `pipeline-${aiPipelineStatus.task_id}`,
      tag: 'pipeline',
      stage: aiPipelineStatus.current_stage || 'running',
      message: aiPipelineStatus.logs?.[aiPipelineStatus.logs.length - 1] || 'Pipeline running...',
      percent: aiPipelineStatus.progress,
      timestamp: Date.now(),
      meta: {
        task_id: aiPipelineStatus.task_id,
        pipelines: aiPipelineStatus.pipelines,
        mode: aiPipelineStatus.mode,
        ...aiPipelineStatus.results,
      },
    };
    isRunning = true;
  }

  if (!progress) {
    return null;
  }

  if (!progress) {
    return null;
  }

  const stageLabels: Record<string, string> = {
    preparing: '准备中',
    data_gen: '数据生成',
    data_generating: '数据生成中',
    data_generating_done: '数据生成完成',
    data_ready: '数据就绪',
    phase1: '阶段1 训练',
    phase2: '阶段2 训练',
    phase3: '阶段3 训练',
    evaluating: '评估中',
    eval: '评估中',
    metrics_parsed: '指标解析',
    writing_meta: '写回元数据',
    writing_meta_skipped: '跳过元数据写回',
    best_model_restored: '恢复最佳模型',
    early_stop: '早停',
    starting: '启动中',
    done: '完成',
    error: '错误',
    // pipeline stages
    pending: '等待中',
    running: '运行中',
    completed: '完成',
    failed: '失败',
  };

  const getStageLabel = (stage: string) => stageLabels[stage] || stage;

  const getStageColor = (stage: string) => {
    if (stage === 'done' || stage === 'completed') return '#00C853';
    if (stage === 'error' || stage === 'failed') return '#FF3D00';
    if (stage === 'running' || stage === 'phase1' || stage === 'phase2' || stage === 'phase3' || stage === 'data_generating' || stage === 'evaluating') return '#FF9800';
    return '#2F6FED';
  };

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--card)',
      borderRadius: 12,
      border: '1px solid var(--line)',
      overflow: 'hidden',
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
            background: 'var(--amber-bg)',
            color: '#FF9800',
            fontSize: 16,
          }}>
            ⚙️
          </span>
          <div>
            <div style={{
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--ink)',
            }}>{runName}</div>
            {(activeRunId || (progress.meta as any)?.task_id) && (
              <div style={{
                fontSize: 10,
                color: 'var(--sub)',
                fontFamily: 'var(--mono)',
              }}>
                ID: {activeRunId || String((progress.meta as any)?.task_id)}
                {(progress.meta as any)?.task_id && activeRunId !== (progress.meta as any)?.task_id && (
                  <span style={{ marginLeft: 8, color: '#2F6FED' }}> (AI: {String((progress.meta as any).task_id)})</span>
                )}
              </div>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 10px',
            fontSize: 10,
            fontWeight: 700,
            borderRadius: 4,
            background: `${getStageColor(progress.stage)}20`,
            color: getStageColor(progress.stage),
            textTransform: 'uppercase',
          }}>
            {isRunning ? '🔄' : progress.stage === 'done' || progress.stage === 'completed' ? '✅' : '❌'}
            {getStageLabel(progress.stage)}
          </span>
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
      </div>

      {/* Progress Content */}
      <div style={{
        flex: 1,
        padding: '16px',
        overflow: 'auto',
      }}>
        {/* Progress Bar */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontWeight: 700, color: getStageColor(progress.stage), fontSize: 11, textTransform: 'uppercase' }}>
              {getStageLabel(progress.stage)}
            </span>
            <span style={{ color: 'var(--sub)', fontSize: 11 }}>
              {progress.message}
            </span>
            {progress.percent !== undefined && (
              <span style={{ color: 'var(--sub)', minWidth: '40px', textAlign: 'right', fontSize: 11, fontFamily: 'var(--mono)' }}>
                {Math.round(progress.percent)}%
              </span>
            )}
          </div>
          <div style={{ height: 8, background: 'rgba(255,255,255,.1)', borderRadius: 4, overflow: 'hidden' }}>
            <div
              style={{
                width: `${Math.min(100, Math.max(0, progress.percent ?? 0))}%`,
                height: '100%',
                background: getStageColor(progress.stage),
                transition: 'width .3s ease',
              }}
            />
          </div>
        </div>

        {/* Epoch / Loss Info */}
        {((progress.meta as any)?.epoch !== undefined || (progress.meta as any)?.loss !== undefined || (progress.meta as any)?.totalEpochs !== undefined) && (
          <div style={{
            marginBottom: 16,
            padding: '10px 12px',
            background: 'rgba(47,111,237,0.05)',
            border: '1px solid rgba(47,111,237,0.2)',
            borderRadius: 8,
            fontSize: 11,
            color: 'var(--ink)',
            fontFamily: 'var(--mono)',
          }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
              {(progress.meta as any)?.epoch !== undefined && (progress.meta as any)?.totalEpochs !== undefined && (
                <span>Epoch: {String((progress.meta as any).epoch)}/{String((progress.meta as any).totalEpochs)}</span>
              )}
              {(progress.meta as any)?.loss !== undefined && (
                <span>Loss: {Number((progress.meta as any).loss).toFixed(4)}</span>
              )}
              {(progress.meta as any)?.bridge_id && (
                <span>桥梁: {String((progress.meta as any).bridge_id)}</span>
              )}
              {(progress.meta as any)?.model_type && (
                <span>模型: {String((progress.meta as any).model_type)}</span>
              )}
            </div>
          </div>
        )}

        {/* Stage Timeline */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            阶段进度
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              { key: 'preparing', label: '准备', icon: '⚙️' },
              { key: 'data_gen', label: '数据生成', icon: '📊' },
              { key: 'phase1', label: '阶段1', icon: '🧠' },
              { key: 'phase2', label: '阶段2', icon: '🧠' },
              { key: 'phase3', label: '阶段3', icon: '🧠' },
              { key: 'evaluating', label: '评估', icon: '📈' },
              { key: 'done', label: '完成', icon: '✅' },
            ].map((stageDef, _idx) => {
              const isCurrent = progress.stage === stageDef.key || 
                (progress.stage === 'data_generating' && stageDef.key === 'data_gen') ||
                (progress.stage === 'eval' && stageDef.key === 'evaluating');
              const isCompleted = [
                'preparing', 'data_gen', 'data_generating', 'data_generating_done', 'data_ready',
                'phase1', 'phase2', 'phase3', 'evaluating', 'eval', 'metrics_parsed', 'writing_meta', 'writing_meta_skipped', 'best_model_restored', 'early_stop'
              ].indexOf(progress.stage) > [
                'preparing', 'data_gen', 'data_generating', 'data_generating_done', 'data_ready',
                'phase1', 'phase2', 'phase3', 'evaluating', 'eval', 'metrics_parsed', 'writing_meta', 'writing_meta_skipped', 'best_model_restored', 'early_stop'
              ].indexOf(stageDef.key);
              
              const stageStatus = isCurrent ? 'current' : (isCompleted || (progress.stage === 'done' || progress.stage === 'completed')) ? 'completed' : 'pending';
              
              return (
                <div key={stageDef.key} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 10px',
                  background: stageStatus === 'current' ? 'rgba(255,152,0,0.08)' : stageStatus === 'completed' ? 'rgba(0,200,83,0.05)' : 'transparent',
                  border: stageStatus === 'current' ? '1px solid rgba(255,152,0,0.3)' : stageStatus === 'completed' ? '1px solid rgba(0,200,83,0.2)' : '1px solid var(--line)',
                  borderRadius: 6,
                  transition: 'all 0.2s ease',
                }}>
                  <span style={{ fontSize: 14 }}>{stageDef.icon}</span>
                  <span style={{
                    flex: 1,
                    fontSize: 12,
                    fontWeight: stageStatus === 'current' ? 600 : 400,
                    color: stageStatus === 'current' ? '#FF9800' : stageStatus === 'completed' ? '#00C853' : 'var(--ink)',
                  }}>
                    {stageDef.label}
                  </span>
                  {stageStatus === 'completed' && (
                    <span style={{
                      fontSize: 10,
                      color: '#00C853',
                      fontWeight: 600,
                    }}>
                      ✓
                    </span>
                  )}
                  {stageStatus === 'current' && (
                    <span style={{
                      fontSize: 10,
                      color: '#FF9800',
                      fontWeight: 600,
                      animation: 'pulse 1.5s infinite',
                    }}>
                      ⟳
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Cancel Button */}
        {isRunning && (onCancel || ((progress.meta as any)?.task_id && typeof aiCancel === 'function')) && (
          <button
            onClick={() => {
              if ((progress.meta as any)?.task_id && typeof aiCancel === 'function') {
                aiCancel(String((progress.meta as any).task_id));
              } else if (onCancel) {
                onCancel();
              }
            }}
            style={{
              width: '100%',
              padding: '10px 16px',
              fontSize: 12,
              fontWeight: 600,
              background: 'rgba(255,61,0,0.1)',
              color: '#FF3D00',
              border: '1px solid rgba(255,61,0,0.3)',
              borderRadius: 8,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,61,0,0.2)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,61,0,0.1)'; }}
          >
            {progress.meta?.task_id ? '停止 AI Pipeline' : '停止执行'}
          </button>
        )}

        {/* Completed Metrics */}
        {(progress.stage === 'done' || progress.stage === 'completed') && progress.meta && (
          <div style={{
            marginTop: 16,
            padding: '12px',
            background: 'rgba(0,200,83,0.08)',
            border: '1px solid rgba(0,200,83,0.3)',
            borderRadius: 8,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#00C853', marginBottom: 8 }}>
              训练完成 · 最终指标
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 8 }}>
              {Object.entries(progress.meta).map(([k, v]) => {
                if (typeof v !== 'number') return null;
                return (
                  <div key={k} style={{
                    padding: '8px',
                    background: 'var(--bg)',
                    borderRadius: 6,
                    border: '1px solid var(--line)',
                  }}>
                    <div style={{ fontSize: 9, color: 'var(--sub)', marginBottom: 2 }}>{k}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--ink)' }}>
                      {v.toFixed(4)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Display */}
        {progress.stage === 'error' || progress.stage === 'failed' ? (
          <div style={{
            marginTop: 16,
            padding: '12px',
            background: 'rgba(255,61,0,0.08)',
            border: '1px solid rgba(255,61,0,0.3)',
            borderRadius: 8,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#FF3D00', marginBottom: 4 }}>
              ❌ 执行失败
            </div>
            <div style={{ fontSize: 11, color: 'var(--sub)', fontFamily: 'var(--mono)', wordBreak: 'break-all' }}>
              {progress.message}
            </div>
            {(progress.meta as any)?.trace && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ fontSize: 10, color: 'var(--sub)', cursor: 'pointer' }}>
                  查看错误堆栈
                </summary>
                <pre style={{ marginTop: 8, fontSize: 9, color: 'var(--sub)', fontFamily: 'var(--mono)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {String((progress.meta as any).trace)}
                </pre>
              </details>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}