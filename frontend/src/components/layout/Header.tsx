import type { DashboardMeta } from '../../lib/types';

export default function Header({
  meta,
  onOpenSettings,
}: {
  meta: DashboardMeta;
  onOpenSettings?: () => void;
}) {
  const m = meta.metrics;
  const ok = (cond: boolean) => (cond ? 'green' : 'red');
  const items: [string, string, string][] = [
    ['位置 MAE', m.pos_mae.toFixed(2) + ' m', ok(m.pos_mae < 1.0) + ' (目标<1.0)'],
    ['深度 MAE', (m.depth_mae * 100).toFixed(2) + ' %', ok(m.depth_mae < 0.05) + ' (目标<5%)'],
    ['F1', m.f1.toFixed(3), ok(m.f1 > 0.87) + ' (目标>0.87)'],
    ['Recall', (m.recall * 100).toFixed(1) + ' %', m.recall > 0.8 ? 'green' : 'amber'],
    ['Precision', (m.precision * 100).toFixed(1) + ' %', m.precision > 0.8 ? 'green' : 'amber'],
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
