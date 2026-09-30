/** AlgorithmDashboard - 算法看板主页面（合并顶栏） */

import PipelineFlowVisualization from './PipelineFlowVisualization';
import { useSync } from '../../hooks/useAlgorithmDashboard';

export default function AlgorithmDashboard({
  onBack,
}: {
  onBack?: () => void;
}) {
  const { syncState, startSync } = useSync();

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      overflow: 'hidden',
    }}>
      {/* 单一顶栏 - 合并所有操作 */}
      <div style={{
        height: 48,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        background: 'var(--card)',
        borderBottom: '1px solid var(--line)',
        gap: 12,
        flexShrink: 0,
      }}>
        {/* 左侧：返回按钮 + 标题（已移除额外一层容器） */}
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="btn btn-secondary"
            style={{ padding: '5px 10px' }}
          >
            ← 返回
          </button>
        )}
        <div className="font-semibold text-lg" style={{ color: 'var(--ink)', marginLeft: onBack ? 12 : 0 }}>
          算法看板
        </div>

        {/* 右侧：操作按钮 */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            onClick={() => startSync({ full: true })}
            disabled={syncState.status === 'started' || syncState.status === 'running'}
            className="btn btn-primary"
            style={{ opacity: (syncState.status === 'started' || syncState.status === 'running') ? 0.6 : 1 }}
          >
            {syncState.status === 'running' ? '◈ 同步中...' : syncState.status === 'started' ? '◈ 启动中...' : '◈ 同步代码库'}
          </button>
        </div>
      </div>

      {/* 主内容区 */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <PipelineFlowVisualization />
      </div>
    </div>
  );
}
