import { useState } from 'react';
import ChatInput from '../chat/ChatInput';
import ChatMessage, { type Msg } from '../chat/ChatMessage';
import QuickCommands from '../chat/QuickCommands';
import { callLLM, buildSystemPrompt } from '../../lib/llm-client';
import { buildCpdvTools } from '../../lib/cpdv-tools';
import type { Bridge } from '../../lib/types';

export default function ChatPanel({
  bridges,
  cur,
  onRefresh,
}: {
  bridges: Bridge[];
  cur: number;
  onRefresh: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: 'ai', text: 'AI 命令控制台就绪。输入命令如「预测损伤」「看板总览」。' },
  ]);
  const [busy, setBusy] = useState(false);

  async function send(raw: string) {
    setMsgs(m => [...m, { role: 'user', text: raw }]);
    setBusy(true);
    setMsgs(m => [...m, { role: 'ai', text: '…' }]); // placeholder
    try {
      const history = msgs
        .map(x => ({ role: x.role === 'user' ? 'user' : 'assistant', content: x.text }))
        .concat({ role: 'user', content: raw });
      const curBridge = bridges[cur]?.name;
      const tools = buildCpdvTools();
      let acc = '';
      const res = await callLLM(
        [{ role: 'system', content: buildSystemPrompt(curBridge) }, ...history],
        chunk => {
          acc += chunk;
          patchAi(acc);
        },
        undefined,
        tools
      );
      // 工具调用后需要二次调用（把工具结果喂回）；此处为骨架，实际需 executeToolCalls 循环
      patchAi(res.text || '（命令已执行）');
      onRefresh();
    } catch (e: any) {
      patchAi('⚠ 错误: ' + String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }

  function patchAi(t: string) {
    setMsgs(m => {
      const c = [...m];
      c[c.length - 1] = { role: 'ai', text: t };
      return c;
    });
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 720,
        background: '#101826',
        border: '1px solid var(--line)',
        borderRadius: 12,
        padding: 16,
      }}
    >
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: '#fff' }}>
        ⑤ AI 命令控制台
      </h3>
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: 4 }}>
        {msgs.map((m, i) => (
          <ChatMessage key={i} msg={m} />
        ))}
      </div>
      <QuickCommands onCmd={send} />
      <ChatInput onSend={send} disabled={busy} />
    </div>
  );
}
