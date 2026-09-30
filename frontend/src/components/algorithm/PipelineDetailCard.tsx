/** PipelineDetailCard - pipeline详细信息卡片（含stages和独立执行） */

import { type PipelineFlowState } from '../../lib/algorithm-types';

interface PipelineDetailCardProps {
  pipeline: PipelineFlowState;
  onClose: () => void;
  onExecute?: (pipelineId: string) => void;
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
  onExecute,
}: PipelineDetailCardProps) {
  const statusConfig = STATUS_CONFIG[pipeline.status];
  const stages = pipeline.spec?.stages || [];

  const handleExecute = () => {
    onExecute?.(pipeline.id);
  };

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
              {pipeline.spec?.category && ` | ${pipeline.spec.category}`}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {(pipeline.status === 'pending' || pipeline.status === 'failed') && (
            <button
              onClick={handleExecute}
              style={{
                padding: '6px 14px',
                fontSize: 11,
                fontWeight: 600,
                background: 'var(--green)',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
              }}
            >
              ▶ 执行
            </button>
          )}
          {pipeline.status === 'running' && (
            <button
              disabled
              style={{
                padding: '6px 14px',
                fontSize: 11,
                fontWeight: 600,
                background: 'var(--amber)',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'not-allowed',
                opacity: 0.7,
              }}
            >
              执行中...
            </button>
          )}
          <button
            onClick={onClose}
            style={{
              padding: '6px 10px',
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

      {/* Content */}
      <div style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        maxHeight: '60vh',
        overflow: 'auto',
      }}>
        {/* Description */}
        {pipeline.spec?.description && (
          <div style={{
            fontSize: 12,
            color: 'var(--ink)',
            lineHeight: 1.5,
            padding: '10px 12px',
            background: 'var(--bg)',
            borderRadius: 8,
            border: '1px solid var(--line)',
          }}>
            {pipeline.spec.description}
          </div>
        )}

        {/* Status & Progress */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <div style={{
            padding: '8px 12px',
            background: 'var(--bg)',
            borderRadius: 8,
            border: '1px solid var(--line)',
            flex: 1,
            minWidth: 100,
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
            minWidth: 100,
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
              minWidth: 100,
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
        </div>

        {/* Current Stage */}
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

        {/* Stages List */}
        {stages.length > 0 && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 8 }}>
              执行阶段 ({stages.length})
            </div>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              maxHeight: 200,
              overflow: 'auto',
              padding: '8px',
              background: 'var(--bg)',
              borderRadius: 8,
              border: '1px solid var(--line)',
            }}>
              {stages.map((stage: any, idx: number) => (
                <div key={stage.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 8px',
                  background: pipeline.currentStage === stage.id 
                    ? 'rgba(255,152,0,0.1)' 
                    : 'transparent',
                  borderRadius: 6,
                  border: pipeline.currentStage === stage.id
                    ? '1px solid rgba(255,152,0,0.3)'
                    : '1px solid transparent',
                }}>
                  <span style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: 'var(--sub)',
                    minWidth: 24,
                  }}>
                    {idx + 1}
                  </span>
                  <span style={{
                    fontSize: 11,
                    fontWeight: 500,
                    color: 'var(--ink)',
                    flex: 1,
                  }}>
                    {stage.name}
                  </span>
                  {stage.critical && (
                    <span style={{
                      fontSize: 9,
                      padding: '2px 6px',
                      background: 'rgba(47,111,237,0.1)',
                      color: 'var(--blue)',
                      borderRadius: 4,
                      fontWeight: 600,
                    }}>
                      关键
                    </span>
                  )}
                  {stage.estimated_time && (
                    <span style={{
                      fontSize: 9,
                      color: 'var(--sub)',
                      fontFamily: 'var(--mono)',
                    }}>
                      {stage.estimated_time}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Outputs */}
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
              {pipeline.outputs.map((output: string, idx: number) => (
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

        {/* Error */}
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
