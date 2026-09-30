import { useState } from 'react';
import type { Bridge } from '../../lib/types';

export default function BridgeCard({ b, active, onClick, onDelete, isRegistered }: {
  b: Bridge; active: boolean; onClick: () => void; onDelete?: (id: string) => Promise<void>;
  isRegistered?: boolean;  // 仅 registry 桥可删
}) {
  const [deleting, setDeleting] = useState(false);
  const [confirm, setConfirm] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm) {
      setDeleting(true);
      try {
        await onDelete?.(b.id);
      } catch (err: any) {
        // 404 等错误静默处理（legacy 场景不可删）
        console.warn('删除失败:', err?.message || err);
      } finally {
        setDeleting(false);
        setConfirm(false);
      }
    } else {
      setConfirm(true);
      setTimeout(() => setConfirm(false), 2000);
    }
  };

  // 仅 registry 桥显示删除按钮
  const showDelete = isRegistered !== false;

  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--card)',
        border: `1px solid ${active ? 'var(--blue)' : 'var(--line)'}`,
        borderRadius: 12,
        padding: '12px 14px',
        cursor: 'pointer',
        position: 'relative',
        boxShadow: active ? '0 4px 14px rgba(47,111,237,.18)' : 'none',
        transition: 'border-color .15s, box-shadow .15s, background .15s',
      }}
    >
      {showDelete && (
        <button
          onClick={handleDelete}
          disabled={deleting}
          aria-label={confirm ? '确认删除' : '删除桥梁'}
          title={confirm ? '再次点击确认删除' : '删除此桥梁'}
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            width: 24,
            height: 24,
            borderRadius: 6,
            border: 'none',
            background: confirm ? 'var(--red)' : 'transparent',
            color: confirm ? '#fff' : 'var(--sub)',
            opacity: confirm ? 1 : 0,
            transform: confirm ? 'scale(1)' : 'scale(0.8)',
            cursor: deleting ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'opacity .15s ease, transform .15s ease, background .15s ease, color .15s ease',
            zIndex: 1,
          }}
          onMouseEnter={() => !confirm && setConfirm(true)}
          onMouseLeave={() => !confirm && setConfirm(false)}
        >
          {deleting ? (
            <svg width="14" height="14" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4 31.4" strokeLinecap="round" />
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </svg>
          ) : confirm ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          )}
        </button>
      )}

      <div style={{ fontSize: 15, fontWeight: 700, paddingRight: showDelete ? 36 : 0 }}>{b.name}</div>
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
