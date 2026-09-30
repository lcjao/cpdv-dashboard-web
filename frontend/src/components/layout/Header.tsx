import type { DashboardMeta } from '../../lib/types';

// G13: 阈值默认（后端没下发时用）。和 backend/data_loader._DEFAULT_THRESHOLDS 同步。
const DEFAULT_THRESHOLDS = {
  pos_mae_max: 1.0,
  depth_mae_max: 0.05,
  f1_min: 0.87,
  recall_min: 0.80,
  precision_min: 0.80,
};

export default function Header({
  meta,
  showConsole,
  onToggleConsole,
  onOpenSettings,
  showAlgorithmSidebar,
  onToggleAlgorithmSidebar,
  showAlgorithmDashboard,
  onToggleAlgorithmDashboard,
}: {
  meta: DashboardMeta;
  showConsole?: boolean;
  onToggleConsole?: () => void;
  onOpenSettings?: () => void;
  showAlgorithmSidebar?: boolean;
  onToggleAlgorithmSidebar?: () => void;
  showAlgorithmDashboard?: boolean;
  onToggleAlgorithmDashboard?: () => void;
}) {
  const m = (meta.metrics ?? {}) as Record<string, number>;
  const t = { ...DEFAULT_THRESHOLDS, ...(meta.thresholds || {}) };
  const ok = (cond: boolean) => (cond ? 'green' : 'red');
  // 防御性：后端缺字段时显示 0，不让 toFixed() 炸（之前就是因为 metrics={} 全白屏）
  const num = (k: string) => Number(m[k] ?? 0);
  const items: [string, string, string][] = [
    ['位置 MAE', num('pos_mae').toFixed(2) + ' m', ok(num('pos_mae') < t.pos_mae_max!) + ` (目标<${t.pos_mae_max})`],
    ['深度 MAE', (num('depth_mae') * 100).toFixed(2) + ' %', ok(num('depth_mae') < t.depth_mae_max!) + ` (目标<${(t.depth_mae_max! * 100).toFixed(0)}%)`],
    ['F1', num('f1').toFixed(3), ok(num('f1') > t.f1_min!) + ` (目标>${t.f1_min})`],
    ['Recall', (num('recall') * 100).toFixed(1) + ' %', num('recall') > t.recall_min! ? 'green' : 'amber'],
    ['Precision', (num('precision') * 100).toFixed(1) + ' %', num('precision') > t.precision_min! ? 'green' : 'amber'],
  ];
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '14px 4px',
        flexWrap: 'wrap',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>
          🌉 多桥梁损伤监测看板 <span style={{ color: 'var(--blue)' }}>CPDV</span>
        </h1>
        {onToggleConsole && (
          <button
            onClick={onToggleConsole}
            title="AI 命令控制台"
            style={{
              padding: '6px 14px',
              fontSize: 12,
              background: showConsole ? 'var(--blue)' : 'var(--card)',
              color: showConsole ? '#fff' : 'var(--sub)',
              border: '1px solid var(--blue)',
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            🤖 AI 控制台
          </button>
        )}
        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            title="AI 配置"
            style={{
              padding: '6px 14px',
              fontSize: 12,
              background: 'var(--card)',
              color: 'var(--sub)',
              border: '1px solid var(--line)',
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            ⚙ 设置
          </button>
        )}
        {onToggleAlgorithmSidebar && (
          <button
            onClick={onToggleAlgorithmSidebar}
            title={showAlgorithmSidebar ? '隐藏算法代码' : '显示算法代码'}
            style={{
              padding: '6px 14px',
              fontSize: 12,
              background: showAlgorithmSidebar ? 'var(--green)' : 'var(--card)',
              color: showAlgorithmSidebar ? '#fff' : 'var(--sub)',
              border: '1px solid var(--green)',
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            🔬 算法代码
          </button>
        )}
        {onToggleAlgorithmDashboard && (
          <button
            onClick={onToggleAlgorithmDashboard}
            title={showAlgorithmDashboard ? '返回看板' : '打开算法看板'}
            style={{
              padding: '6px 14px',
              fontSize: 12,
              background: showAlgorithmDashboard ? 'var(--purple, var(--blue))' : 'var(--card)',
              color: showAlgorithmDashboard ? '#fff' : 'var(--sub)',
              border: '1px solid var(--purple, var(--blue))',
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            🔬 算法看板
          </button>
        )}
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))',
          gap: 10,
          width: '55%',
        }}
      >
        {items.map(([k, v, s]) => (
          <div
            key={k}
            style={{
              background: 'var(--card)',
              border: '1px solid var(--line)',
              borderRadius: 12,
              padding: '8px 12px',
            }}
          >
            <div style={{ fontSize: 12, color: 'var(--sub)' }}>{k}</div>
            <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--mono)' }}>{v}</div>
            <div style={{ fontSize: 10, color: 'var(--sub)' }}>{s}</div>
          </div>
        ))}
      </div>
    </div>
  );
}