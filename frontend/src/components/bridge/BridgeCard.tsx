import type { Bridge } from '../../lib/types';

export default function BridgeCard({ b, active, onClick }: {
  b: Bridge; active: boolean; onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--card)', border: `1px solid ${active ? 'var(--blue)' : 'var(--line)'}`,
        borderRadius: 12, padding: '12px 14px', cursor: 'pointer',
        boxShadow: active ? '0 4px 14px rgba(47,111,237,.18)' : 'none',
      }}
    >
      <div style={{ fontSize: 15, fontWeight: 700 }}>{b.name}</div>
      <div style={{ color: 'var(--sub)', fontSize: 12, marginTop: 5 }}>
        跨长 {b.params.L.toFixed(1)} m · 车速 {b.params.V.toFixed(1)} m/s
      </div>
      <div style={{ marginTop: 7, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        <span style={{ background: 'var(--green-bg)', color: 'var(--green)', borderRadius: 9, padding: '2px 7px', fontSize: 11 }}>
          真 {b.n_true}
        </span>
        <span style={{ background: 'var(--blue-bg)', color: 'var(--blue)', borderRadius: 9, padding: '2px 7px', fontSize: 11 }}>
          预 {b.n_pred}
        </span>
        {b.n_miss > 0 && (
          <span style={{ background: 'var(--red-bg)', color: 'var(--red)', borderRadius: 9, padding: '2px 7px', fontSize: 11 }}>
            漏 {b.n_miss}
          </span>
        )}
      </div>
    </div>
  );
}
