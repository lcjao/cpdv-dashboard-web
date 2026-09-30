import { useState } from 'react';

export default function ChatInput({
  onSend,
  onStop,
  disabled,
  busy,
}: {
  onSend: (t: string) => void;
  onStop: () => void;
  disabled: boolean;
  busy: boolean;
}) {
  const [text, setText] = useState('');
  return (
    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
      <input
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') {
            e.preventDefault();
            if (text.trim()) {
              onSend(text.trim());
              setText('');
            }
          }
        }}
        placeholder="如：预测损伤 / 看板总览 / 计算CPDV"
        disabled={disabled || busy}
        style={{
          flex: 1,
          background: '#1b2740',
          border: '1px solid #2c3b5c',
          color: '#e8eef8',
          borderRadius: 8,
          padding: '8px 12px',
          fontSize: 13,
          fontFamily: 'var(--mono)',
        }}
      />
      {busy ? (
        <button
          onClick={onStop}
          aria-label="停止当前执行"
          style={{
            padding: '8px 18px',
            background: '#e04444',
            borderRadius: 8,
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          停止
        </button>
      ) : (
        <button
          onClick={() => {
            if (text.trim()) {
              onSend(text.trim());
              setText('');
            }
          }}
          disabled={disabled}
          style={{
            padding: '8px 18px',
            background: '#2f6fed',
            borderRadius: 8,
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          发送
        </button>
      )}
    </div>
  );
}
