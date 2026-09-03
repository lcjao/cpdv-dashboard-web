export default function ChatPanel({ disabled }: { disabled: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 720, background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>⑤ AI 命令控制台</h3>
      {disabled ? (
        <p style={{ color: 'var(--sub)', fontSize: 12 }}>AI 对话将在 Phase 3 集成</p>
      ) : (
        <p style={{ color: 'var(--sub)', fontSize: 12 }}>加载中…</p>
      )}
    </div>
  );
}
