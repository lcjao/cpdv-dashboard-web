import { useState } from 'react';
import { getLLMConfig, saveLLMConfig } from '../../lib/config';

export default function SettingsDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [cfg, setCfg] = useState(getLLMConfig());
  if (!open) return null;
  const set = (k: string, v: string) => setCfg(c => ({ ...c, [k]: v }));
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: '#fff',
          borderRadius: 12,
          padding: 24,
          width: 480,
          maxHeight: '90vh',
          overflowY: 'auto',
        }}
      >
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>AI 配置</h2>
        {(['backend', 'baseUrl', 'model', 'apiKey', 'systemPrompt'] as const).map(k => (
          <div key={k} style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--sub)', marginBottom: 4 }}>
              {k}
            </label>
            <textarea
              rows={k === 'systemPrompt' ? 6 : 1}
              value={cfg[k] as string}
              onChange={e => set(k, e.target.value)}
              style={{
                width: '100%',
                padding: 8,
                border: '1px solid var(--line)',
                borderRadius: 8,
                fontFamily: 'var(--mono)',
                fontSize: 13,
              }}
            />
          </div>
        ))}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button
            onClick={() => {
              saveLLMConfig(cfg);
              onClose();
            }}
            style={{
              padding: '8px 18px',
              background: 'var(--blue)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
            }}
          >
            保存
          </button>
          <button
            onClick={onClose}
            style={{
              padding: '8px 18px',
              background: 'var(--gray-bg)',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
            }}
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
