/** PipelineStatusNode - 单个pipeline状态节点（可点击执行） */

import { type PipelineFlowState } from '../../lib/algorithm-types';

interface PipelineStatusNodeProps {
  pipeline: PipelineFlowState;
  isSelected: boolean;
  onClick: (pipeline: PipelineFlowState) => void;
  onExecute?: (pipelineId: string) => void;
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
  onExecute,
}: PipelineStatusNodeProps) {
  const statusConfig = STATUS_CONFIG[pipeline.status];
  const isRunning = pipeline.status === 'running';
  const isPending = pipeline.status === 'pending';
  const canExecute = isPending;

  const handleExecute = (e: React.MouseEvent) => {
    e.stopPropagation();
    onExecute?.(pipeline.id);
  };

  return (
    <div
      onClick={() => onClick(pipeline)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 6,
        padding: '10px 12px',
        background: isSelected ? 'var(--blue-bg)' : isRunning ? 'rgba(255,152,0,0.08)' : 'var(--card)',
        border: `2px solid ${isSelected ? 'var(--blue)' : isRunning ? 'rgba(255,152,0,0.4)' : 'var(--line)'}`,
        borderRadius: 10,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        minWidth: 130,
        maxWidth: 160,
        position: 'relative',
        boxShadow: isSelected ? '0 0 0 3px var(--blue-bg)' : '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      {/* Pipeline编号 */}
      <div style={{
        position: 'absolute',
        top: -8,
        left: -8,
        width: 22,
        height: 22,
        borderRadius: '50%',
        background: isRunning ? '#FF9800' : isSelected ? 'var(--blue)' : 'var(--bg)',
        border: `2px solid ${isRunning ? '#FF9800' : isSelected ? 'var(--blue)' : 'var(--line)'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 10,
        fontWeight: 700,
        color: '#fff',
      }}>
        {pipeline.pipelineIndex}
      </div>

      {/* Pipeline名称 */}
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        color: 'var(--ink)',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        maxWidth: 140,
        paddingTop: 8,
      }}>
        {pipeline.name}
      </div>

      {/* 状态图标 */}
      <div style={{ fontSize: 20, lineHeight: 1 }}>
        {statusConfig.icon}
      </div>

      {/* 状态标签 */}
      <div style={{
        fontSize: 9,
        fontWeight: 600,
        color: statusConfig.color,
        textTransform: 'uppercase',
      }}>
        {statusConfig.label}
      </div>

      {/* 进度条 */}
      {isRunning && (
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
      {isRunning && (
        <div style={{
          fontSize: 9,
          color: 'var(--sub)',
          fontFamily: 'var(--mono)',
        }}>
          {Math.round(pipeline.progress)}%
        </div>
      )}

      {/* 执行按钮 */}
      {canExecute && (
        <button
          onClick={handleExecute}
          style={{
            position: 'absolute',
            bottom: -8,
            right: -8,
            width: 24,
            height: 24,
            borderRadius: '50%',
            background: 'var(--green)',
            border: '2px solid var(--card)',
            color: '#fff',
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
          }}
          title="执行此 Pipeline"
        >
          ▶
        </button>
      )}
    </div>
  );
}
