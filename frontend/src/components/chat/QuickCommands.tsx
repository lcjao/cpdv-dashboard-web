import type { CommandMeta } from '../../lib/api-client';

// G9: 按钮列表从 command-meta 动态生成（之前是写死 6 条）。
// 显示 quick=true 的命令，按原 config.COMMAND_META 顺序排（无需排序）。
export default function QuickCommands({
  onCmd,
  meta,
}: {
  onCmd: (t: string) => void;
  meta: CommandMeta[];
}) {
  const items = meta.filter((m) => m.quick);
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
      {items.map((m) => (
        <button
          key={m.action}
          onClick={() => onCmd(m.name)}
          title={m.description}
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
          {m.name}
        </button>
      ))}
    </div>
  );
}