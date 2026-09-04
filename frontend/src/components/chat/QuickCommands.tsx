const QUICK = ['看板总览', '预测损伤', '多裂缝预测', '随机工况分析', '对比工况', '刷新看板'];

export default function QuickCommands({ onCmd }: { onCmd: (t: string) => void }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
      {QUICK.map(q => (
        <button
          key={q}
          onClick={() => onCmd(q)}
          style={{
            padding: '4px 12px',
            fontSize: 11,
            background: '#1b2740',
            color: '#9fb6dc',
            border: '1px solid #2c3b5c',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          {q}
        </button>
      ))}
    </div>
  );
}
