import { useEffect, useRef, useState } from 'react';
import ChatInput from '../chat/ChatInput';
import ChatMessage, { type Msg } from '../chat/ChatMessage';
import QuickCommands from '../chat/QuickCommands';
import {
  callLLM,
  buildSystemPrompt,
  MAX_TOOL_CALLS,
  type LLMMessage,
} from '../../lib/llm-client';
import { buildCpdvTools } from '../../lib/cpdv-tools';
import { api, fetchCommandMeta } from '../../lib/api-client';
import type { CommandMeta } from '../../lib/api-client';
import type { Bridge } from '../../lib/types';
import { useTagProgress } from '../../lib/progress-context';

export default function ChatPanel({
  bridges,
  cur,
  onRefresh,
  onClose,
}: {
  bridges: Bridge[];
  cur: number;
  onRefresh: () => void;
  onClose?: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>(() => {
    // Load from localStorage with key based on bridge context if available
    try {
      const saved = localStorage.getItem(`cpdv-chat-history-${cur}`);
      if (saved) {
        const parsed = JSON.parse(saved) as Msg[];
        if (parsed.length > 0) return parsed;
      }
    } catch {
      // ignore parse errors
    }
    return [{ role: 'ai', text: 'AI 命令控制台就绪。输入命令如「预测损伤」「看板总览」。' }];
  });
  const [busy, setBusy] = useState(false);
  // G9: 启动时拉 command-meta（模块级 cache 保证不重复网络往返）
  const [meta, setMeta] = useState<CommandMeta[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);
  const abortCtrlRef = useRef<AbortController | null>(null);
  // G7: 订阅长任务进度（train/cpdv/random）
  const trainProgress = useTagProgress('train');
  const cpdvProgress = useTagProgress('cpdv');
  const randomProgress = useTagProgress('random');
  const [currentToolTag, setCurrentToolTag] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchCommandMeta()
      .then(m => { if (mounted) setMeta(m); })
      .catch(() => { if (mounted) { /* 保留 meta 为空，不覆盖；用户可重试 */ } })
      .finally(() => { if (mounted) setMetaLoading(false); });
    return () => { mounted = false; };
  }, []);

  // Persist messages to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(`cpdv-chat-history-${cur}`, JSON.stringify(msgs));
    } catch {
      // ignore storage errors
    }
  }, [msgs]);

  function patchAi(t: string) {
    setMsgs(m => {
      const c = [...m];
      c[c.length - 1] = { role: 'ai', text: t };
      return c;
    });
  }

  function appendExecutionStatus(toolName: string, status: 'executing' | 'success' | 'error', detail?: string) {
    const icons = { executing: '⏳', success: '✅', error: '❌' };
    const labels = { executing: '执行中…', success: '执行完成', error: '执行失败' };
    const icon = icons[status];
    const label = labels[status];
    
    let text = `${icon} **${toolName}** ${label}`;
    if (detail) {
      text += `\n\`\`\`json\n${detail}\n\`\`\``;
    }
    setMsgs(m => [...m, { role: 'ai', text }]);
  }

  function abort() {
    abortCtrlRef.current?.abort();
  }

  async function runToolLoop(
    history: LLMMessage[],
    curBridge: string | undefined,
    acc: { text: string },
    signal: AbortSignal,
  ): Promise<{ text: string; executed: number }> {
    // 循环执行 LLM 工具调用：拿到 tool_calls → 调 API → 回喂 → 再来一轮。
    const messages: LLMMessage[] = [...history];
    // G9: tools 从 meta 动态生成（之前 buildCpdvTools() 写死 9 条）
    const tools = buildCpdvTools(meta);
    let executed = 0;
    let finalText = '';
    // 检测历史中是否有幻觉回复，如果有则强制使用tool_calls
    const lastUserMsg = history.filter(m => m.role === 'user').pop();
    const userText = typeof lastUserMsg?.content === 'string' ? lastUserMsg.content : '';
    const shouldForceToolCall = /计算|执行|调用|运行|训练|预测|分析|随机|对比|刷新|评估/i.test(userText);
    
    for (let round = 0; round < MAX_TOOL_CALLS; round++) {
      if (signal.aborted) break;
      const sysPrompt = buildSystemPrompt(curBridge);
      // 如果用户明确要求执行操作，强制LLM使用tool_calls
      const toolChoice = shouldForceToolCall && round === 0 ? 'auto' : undefined;
      const res = await callLLM(
        [{ role: 'system', content: sysPrompt }, ...messages],
        chunk => {
          if (signal.aborted) return;
          acc.text += chunk;
          patchAi(acc.text);
        },
        signal,
        tools,
        toolChoice,
      );
      finalText = res.text || finalText;
      messages.push({ role: 'assistant', content: res.text || null, tool_calls: res.toolCalls.length ? res.toolCalls.map(t => ({
        id: t.id, type: 'function', function: { name: t.name, arguments: t.arguments },
      })) : undefined });
      if (!res.toolCalls.length) {
        // 幻觉回复检测：只在用户明确要求执行操作时检测
        // 检测用户输入是否包含执行意图
        const lastUserMsg = history.filter(m => m.role === 'user').pop();
        const userText = typeof lastUserMsg?.content === 'string' ? lastUserMsg.content : '';
        const hasExecutionIntent = /计算|执行|调用|运行|训练|预测|分析|随机|对比|刷新|评估|列出|注册|查看|检查|加载/i.test(userText);
        
        if (hasExecutionIntent) {
          // 用户明确要求执行操作，但LLM没有返回tool_calls
          const hallucinationPatterns = [
            /(?:我将|正在|已经|已|将要|准备|计划)\s*(?:调用|执行|运行|启动)\s*cb_/i,
            /(?:已发出|发出|发送|调用)\s*(?:cb_|.*调用)/i,
            /cb_\w+\s*(?:调用|执行|运行)/i,
            /(?:调用|执行)\s*(?:cb_\w+|.*工具)/i,
            /(?:好的|立即|马上|现在)\s*[！!]?\s*(?:执行|调用|运行|启动)/i,
            /(?:让我|我来)\s*(?:检查|查看|执行|调用|运行)/i,
          ];
          const hasHallucinationText = hallucinationPatterns.some(p => p.test(finalText));
          if (hasHallucinationText) {
            // 注入系统消息提醒LLM
            messages.push({ role: 'system', content: '【紧急提醒】上一轮你没有使用 tool_calls，导致工具没有执行。请在下一轮回复中必须使用 tool_calls 调用工具。' });
          }
        }
        break;
      }
      // 执行每个 tool，结果作为 tool 角色回喂
      for (const tc of res.toolCalls) {
        if (signal.aborted) break;
        executed++;
        let argsObj: any = {};
        // 修复 LLM 生成的工具参数 JSON：Windows 路径里的裸反斜杠是非法 JSON 转义，
        // 直接 JSON.parse 会抛错而丢失全部参数；先做一次"补齐转义"的修复解析，仍失败则退回 {}（后端有默认值兜底）
        const rawArgs = tc.arguments || '{}';
        try { argsObj = JSON.parse(rawArgs); }
        catch {
          try { argsObj = JSON.parse(rawArgs.replace(/\\(?!["\\/bfnrtu])/g, '\\\\')); } catch { argsObj = {}; }
        }
        // 值级修复：若 LLM 把路径里的 \b 当成合法 JSON 退格转义，JSON.parse 会成功但值里带退格符；
        // 把字符串值中的退格还原为反斜杠、折叠连续双反斜杠（Windows 路径被 JSON 二次转义的情况）
        const _sanitizeArgVal = (v: unknown): unknown => {
          if (typeof v === 'string') {
            let s = v.replace(/\u0008/g, '\\');
            s = s.replace(/\\\\/g, '\\');
            return s;
          }
          if (Array.isArray(v)) return v.map(_sanitizeArgVal);
          if (v && typeof v === 'object') {
            const o: Record<string, unknown> = {};
            for (const k of Object.keys(v as Record<string, unknown>)) o[k] = _sanitizeArgVal((v as Record<string, unknown>)[k]);
            return o;
          }
          return v;
        };
        argsObj = _sanitizeArgVal(argsObj);
        // 工具调用自动注入当前选中桥（若未显式指定）
        // 实际工具名来自 COMMAND_META 的 action 字段：cb_<action>
        if ((tc.name === 'cb_cpdv' || tc.name === 'cb_predict' || tc.name === 'cb_multi_crack') && !argsObj.bridge && curBridge) {
          argsObj.bridge = curBridge;
        }
        // Map tool name to WS tag for progress subscription
        const toolTag = tc.name === 'cb_train' ? 'train'
          : tc.name === 'cb_train_and_evaluate' ? 'train'
          : tc.name === 'cb_cpdv' ? 'cpdv'
          : tc.name === 'cb_random_condition' ? 'random'
          : null;
        if (toolTag) setCurrentToolTag(toolTag);
        // 显示执行开始状态
        appendExecutionStatus(tc.name, 'executing', JSON.stringify(argsObj, null, 2));
        try {
          const result = await api.executeToolCall(tc.name, argsObj);
          // P0 修复：任何返回 need_refresh=true 的工具，自动刷新看板
          if (result && typeof result === 'object' && result.need_refresh === true) {
            onRefresh();
          }
          messages.push({ role: 'tool', tool_call_id: tc.id, content: JSON.stringify(result, null, 2).slice(0, 8000) });
          // 显示执行完成状态，包含关键结果摘要
          const resultSummary = typeof result === 'object' ? JSON.stringify(result, null, 2).slice(0, 2000) : String(result);
          appendExecutionStatus(tc.name, 'success', resultSummary);
        } catch (e: any) {
          const errMsg = String(e?.message || e);
          messages.push({ role: 'tool', tool_call_id: tc.id, content: `ERROR: ${errMsg}` });
          appendExecutionStatus(tc.name, 'error', errMsg);
        } finally {
          if (toolTag) setCurrentToolTag(null);
        }
      }
    }
    return { text: finalText, executed };
  }

  async function send(raw: string) {
    // 自然语言停止触发：用户输入「暂停执行」「停止」「中止」
    const stopKeywords = ['暂停执行', '停止', '中止', '取消'];
    if (stopKeywords.some(k => raw.includes(k))) {
      abort();
      setMsgs(m => [...m, { role: 'user', text: raw }]);
      setMsgs(m => [...m, { role: 'ai', text: '⏹ 已中断执行。' }]);
      setBusy(false);
      return;
    }

    abortCtrlRef.current = new AbortController();
    const signal = abortCtrlRef.current.signal;
    setMsgs(m => [...m, { role: 'user', text: raw }]);
    setBusy(true);
    setMsgs(m => [...m, { role: 'ai', text: '…' }]);
    const acc = { text: '' };
    const history: LLMMessage[] = msgs
      .filter(x => x.text !== '…')
      .map(x => ({ role: x.role === 'user' ? 'user' : 'assistant', content: x.text }));
    history.push({ role: 'user', content: raw });
    const curBridge = bridges[cur]?.name;
    try {
      const { text, executed } = await runToolLoop(history, curBridge, acc, signal);
      if (signal.aborted) {
        patchAi((acc.text || '（已中断）') + '\n\n⏹ 执行已中断');
        return;
      }
      // 幻觉回复检测：只在用户明确要求执行操作时检测
      const lastUserMsg = history.filter(m => m.role === 'user').pop();
      const userText = typeof lastUserMsg?.content === 'string' ? lastUserMsg.content : '';
      const hasExecutionIntent = /计算|执行|调用|运行|训练|预测|分析|随机|对比|刷新|评估|列出|注册|查看|检查|加载/i.test(userText);
      
      let finalText = text || '（命令已执行）';
      if (executed > 0 && !text.trim()) {
        finalText += `\n\n（已执行 ${executed} 次工具调用）`;
      }
      
      // 如果用户明确要求执行操作但没有真正执行，添加警告
      if (hasExecutionIntent && executed === 0) {
        // 检测是否有工具调用的文本描述
        const hallucinationPatterns = [
          /(?:我将|正在|已经|已|将要|准备|计划)\s*(?:调用|执行|运行|启动)\s*cb_/i,
          /(?:已发出|发出|发送|调用)\s*(?:cb_|.*调用)/i,
          /cb_\w+\s*(?:调用|执行|运行)/i,
          /(?:调用|执行)\s*(?:cb_\w+|.*工具)/i,
          /(?:好的|立即|马上|现在)\s*[！!]?\s*(?:执行|调用|运行|启动)/i,
          /(?:让我|我来)\s*(?:检查|查看|执行|调用|运行)/i,
        ];
        const hasHallucinationText = hallucinationPatterns.some(p => p.test(finalText));
        if (hasHallucinationText) {
          finalText += '\n\n⚠️ **错误**：你只生成了文本，没有使用 tool_calls。请在下一条回复中直接使用 tool_calls 调用工具，不要用文字描述。';
        }
      }
      
      patchAi(finalText);
      onRefresh();
    } catch (e: any) {
      if (e.name === 'AbortError' || e.name === 'TimeoutError' || String(e).includes('aborted')) {
        patchAi((acc.text || '（已中断）') + '\n\n⏹ 执行已中断');
      } else {
        patchAi('⚠ 错误: ' + String(e?.message || e));
      }
    } finally {
      setBusy(false);
      abortCtrlRef.current = null;
    }
  }

  function handleStop() {
    abort();
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#101826',
        borderLeft: '1px solid var(--line)',
        padding: 16,
        boxShadow: '-8px 0 24px rgba(0,0,0,.25)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <h3 style={{ fontSize: 14, fontWeight: 700, color: '#fff', margin: 0 }}>
          ⑤ AI 命令控制台
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            aria-label="关闭 AI 命令控制台"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#8b98a9',
              fontSize: 18,
              lineHeight: 1,
              cursor: 'pointer',
              padding: '2px 6px',
            }}
          >
            ✕
          </button>
        )}
        <button
          onClick={() => {
            localStorage.removeItem(`cpdv-chat-history-${cur}`);
            setMsgs([{ role: 'ai', text: 'AI 命令控制台就绪。输入命令如「预测损伤」「看板总览」。' }]);
          }}
          aria-label="清空对话历史"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#8b98a9',
            fontSize: 16,
            lineHeight: 1,
            cursor: 'pointer',
            padding: '2px 6px',
            marginLeft: 8,
          }}
          title="清空对话历史 (Ctrl+Shift+X)"
        >
          🗑️
        </button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: 4 }}>
        {msgs.map((m, i) => (
          <ChatMessage key={i} msg={m} />
        ))}
      </div>
      {/* Progress indicator for long-running tasks */}
      {currentToolTag && (() => {
        const getPercent = () => {
          if (currentToolTag === 'train') return trainProgress?.percent ?? 0;
          if (currentToolTag === 'cpdv') return cpdvProgress?.percent ?? 0;
          if (currentToolTag === 'random') return randomProgress?.percent ?? 0;
          return 0;
        };
        const getStage = () => {
          if (currentToolTag === 'train') return trainProgress?.stage ?? '';
          if (currentToolTag === 'cpdv') return cpdvProgress?.stage ?? '';
          if (currentToolTag === 'random') return randomProgress?.stage ?? '';
          return '';
        };
        const getMessage = () => {
          if (currentToolTag === 'train') return trainProgress?.message ?? '';
          if (currentToolTag === 'cpdv') return cpdvProgress?.message ?? '';
          if (currentToolTag === 'random') return randomProgress?.message ?? '';
          return '';
        };
        const percent = getPercent();
        return (
          <div
            style={{
              padding: '10px 12px',
              background: 'rgba(47, 111, 237, 0.15)',
              border: '1px solid rgba(47, 111, 237, 0.3)',
              borderRadius: 8,
              marginBottom: 10,
              fontSize: 12,
              fontFamily: 'var(--mono)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>
                {currentToolTag}
              </span>
              <span style={{ color: 'var(--muted)' }}>
                {currentToolTag === 'train' ? '训练模型中…'
                 : currentToolTag === 'cpdv' ? '计算 CPDV 中…'
                 : currentToolTag === 'random' ? '随机工况分析中…'
                 : '处理中…'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ flex: 1, height: 5, background: 'rgba(255,255,255,.1)', borderRadius: 2.5, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${Math.min(100, Math.max(0, percent))}%`,
                    height: '100%',
                    background: 'var(--accent)',
                    transition: 'width .3s ease',
                  }}
                />
              </div>
              <span style={{ color: 'var(--muted)', minWidth: '36px', textAlign: 'right' }}>
                {Math.round(percent)}%
              </span>
            </div>
            <div style={{ marginTop: 6, color: 'var(--muted)', fontSize: 11 }}>
              {getStage() + ': ' + getMessage()}
            </div>
          </div>
        );
      })()}
      {metaLoading ? (
        <div style={{ padding: 12, textAlign: 'center', color: '#8b98a9', fontSize: 12 }}>
          正在加载命令元数据…
        </div>
      ) : meta.length === 0 ? (
        <div style={{ padding: 12, textAlign: 'center', color: '#e04444', fontSize: 12 }}>
          命令元数据加载失败（后端未就绪？）
          <button
            onClick={() => { setMetaLoading(true); fetchCommandMeta().then(setMeta).finally(() => setMetaLoading(false)); }}
            style={{ marginLeft: 8, padding: '2px 8px', fontSize: 11, background: '#2f6fed', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
          >
            重试
          </button>
        </div>
      ) : (
        <>
          <QuickCommands onCmd={send} meta={meta} />
          <ChatInput onSend={send} onStop={handleStop} disabled={busy} busy={busy} />
        </>
      )}
    </div>
  );
}