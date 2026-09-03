import { getLLMConfig } from './config';

/* ═══════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════ */

/** Image URL input block for vision support */
export interface ContentBlock {
  type: 'text' | 'image_url';
  text?: string;
  image_url?: { url: string };
}

/** Tool definition for function calling */
export interface ToolDefinition {
  type: 'function';
  function: {
    name: string;
    description: string;
    parameters: {
      type: 'object';
      properties: Record<string, { type: string; description: string; enum?: string[] }>;
      required?: string[];
    };
  };
}

/** A tool call requested by the model during a streaming chat completion */
export interface ToolCall {
  id: string;
  name: string;
  arguments: string;
}

/** Result of a single callLLM invocation (text + any tool calls) */
export interface LLMResponse {
  text: string;
  toolCalls: ToolCall[];
}

/** Message shape accepted by callLLM, including tool-loop messages */
export interface LLMMessage {
  role: string;
  content: string | ContentBlock[] | null;
  tool_calls?: { id: string; type: string; function: { name: string; arguments: string } }[];
  tool_call_id?: string;
}

/** Result message fed back to the LLM after executing a tool call */
export interface ToolResult {
  role: 'tool';
  tool_call_id: string;
  content: string;
}

/** Parsed AI response after stripping structured markers */
export interface ParsedResponse {
  text: string;
  commands: string[];
  writes: { path: string; content: string }[];
  panels: string[];
  loopAction: 'continue' | 'finish' | 'none';
}

/** Upper bound on tool-call rounds per user turn (guard against runaway loops) */
export const MAX_TOOL_CALLS = 8;

/** Hard per-attempt timeout (ms) for a single LLM stream */
export const LLM_TIMEOUT_MS = 120_000;

/** Number of exponential-backoff retries for transient failures */
export const LLM_MAX_RETRIES = 3;

/** Cap on output tokens per call */
export const LLM_MAX_TOKENS = 4096;

/** HTTP statuses considered transient & worth retrying */
export const RETRYABLE_STATUS = new Set([408, 429, 500, 502, 503, 504]);

const sleep = (ms: number) => new Promise(res => setTimeout(res, ms));
const isAbort = (e: unknown) =>
  e instanceof Error && (e.name === 'AbortError' || e.name === 'TimeoutError');

/* ═══════════════════════════════════════════════════════════
   Compression
   ═══════════════════════════════════════════════════════════ */

/** Hard per-message content cap (chars). */
const PER_MSG_CHARS = 12_000;
/** Absolute cap on the sum of all message content chars. */
const TOTAL_MSG_CHARS = 60_000;

function compressMessages(messages: LLMMessage[]): LLMMessage[] {
  const capped = messages.map(m => {
    if (Array.isArray(m.content)) return { ...m, content: m.content };
    const s = typeof m.content === 'string' ? m.content : String(m.content ?? '');
    return { ...m, content: s.length > PER_MSG_CHARS ? s.slice(0, PER_MSG_CHARS) : s };
  });

  let total = capped.reduce((n, m) => n + (typeof m.content === 'string' ? m.content.length : 0), 0);
  if (total <= TOTAL_MSG_CHARS) return capped;

  const systemMsg = capped[0];
  const tail = capped[capped.length - 1];
  const middle = capped.slice(1, -1);

  const keep: LLMMessage[] = [systemMsg];
  let budget =
    TOTAL_MSG_CHARS -
    (typeof systemMsg.content === 'string' ? systemMsg.content.length : 0) -
    (typeof tail.content === 'string' ? tail.content.length : 0);

  for (let i = middle.length - 1; i >= 0 && budget > 0; i--) {
    const len = typeof middle[i].content === 'string' ? middle[i].content.length : 0;
    if (len <= budget) {
      budget -= len;
      keep.push(middle[i]);
    }
  }
  keep.sort((a, b) => {
    const ai = (capped as unknown[]).indexOf(a);
    const bi = (capped as unknown[]).indexOf(b);
    return ai - bi;
  });
  keep.push(tail);
  return keep;
}

/* ═══════════════════════════════════════════════════════════
   Retryable fetch
   ═══════════════════════════════════════════════════════════ */

async function retryFetch(
  doFetch: (sig: AbortSignal) => Promise<Response>,
  signal: AbortSignal | undefined,
  holder: { signal: AbortSignal; cleanup: () => void }
): Promise<{ res: Response }> {
  const ctrl = new AbortController();
  const onOuter = () => ctrl.abort();
  if (signal) {
    if (signal.aborted) ctrl.abort();
    else signal.addEventListener('abort', onOuter, { once: true });
  }
  const timer = setTimeout(() => ctrl.abort(new Error('Request timed out')), LLM_TIMEOUT_MS);
  const baseWait = 500;
  let attempt = 0;
  try {
    while (true) {
      try {
        const r = await doFetch(ctrl.signal);
        if (r.ok) {
          holder.signal = ctrl.signal;
          holder.cleanup = () => {
            clearTimeout(timer);
            signal?.removeEventListener('abort', onOuter);
          };
          return { res: r };
        }
        if (RETRYABLE_STATUS.has(r.status) && attempt < LLM_MAX_RETRIES) {
          try {
            r.body?.cancel();
          } catch {
            /* ignore */
          }
          attempt++;
          await sleep(baseWait * 2 ** (attempt - 1));
          continue;
        }
        holder.signal = ctrl.signal;
        holder.cleanup = () => {
          clearTimeout(timer);
          signal?.removeEventListener('abort', onOuter);
        };
        return { res: r };
      } catch (e) {
        if (isAbort(e)) throw e;
        if (attempt >= LLM_MAX_RETRIES) throw e;
        attempt++;
        await sleep(baseWait * 2 ** (attempt - 1));
      }
    }
  } catch (e) {
    ctrl.abort();
    return Promise.reject(e);
  }
}

/* ═══════════════════════════════════════════════════════════
   callLLM
   ═══════════════════════════════════════════════════════════ */

export async function callLLM(
  messages: LLMMessage[],
  onChunk: (text: string) => void,
  signal?: AbortSignal,
  tools?: ToolDefinition[],
  toolChoice?: string | { type: 'function'; function: { name: string } }
): Promise<LLMResponse> {
  const cfg = getLLMConfig();

  // Ollama doesn't require API key; others do
  if (cfg.backend !== 'ollama' && !cfg.apiKey) {
    throw new Error('API_KEY_MISSING');
  }

  const baseUrl = cfg.baseUrl.replace(/\/+$/, '');

  const normalizedMessages = messages.map(m => ({
    ...m,
    role: m.role === 'ai' ? 'assistant' : m.role,
  }));

  const allowedRoles = new Set(['system', 'user', 'assistant', 'tool']);
  for (const m of normalizedMessages) {
    if (!allowedRoles.has(m.role)) {
      console.warn('[LLM Client] Coercing unexpected role', m.role, '-> user');
      m.role = 'user';
    }
    if (Array.isArray(m.content)) {
      try {
        m.content = (m.content as ContentBlock[])
          .map(b => {
            if (b.type === 'image_url') return `[图片: ${b.image_url?.url || ''}]`;
            return b.text || '';
          })
          .join('\n');
      } catch {
        m.content = String(m.content);
      }
    }
    if (typeof m.content !== 'string') {
      m.content = String(m.content ?? '');
    }
  }

  const body: Record<string, unknown> = {
    model: cfg.model,
    messages: compressMessages(normalizedMessages),
    temperature: 0.4,
    max_tokens: LLM_MAX_TOKENS,
    stream: true,
  };

  if (tools && tools.length > 0) {
    body.tools = tools;
    if (toolChoice) {
      body.tool_choice = toolChoice;
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (cfg.apiKey) {
    headers['Authorization'] = `Bearer ${cfg.apiKey}`;
  }

  // 使用服务端代理避免 CORS；本地 ollama 保留直连
  const isLocalOllama = cfg.backend === 'ollama';
  const doFetch = (sig: AbortSignal) =>
    isLocalOllama
      ? fetch(`${baseUrl}/chat/completions`, {
          method: 'POST',
          headers,
          body: JSON.stringify(body),
          signal: sig,
        })
      : fetch('/api/llm/proxy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ baseUrl, apiKey: cfg.apiKey || '', payload: body }),
          signal: sig,
        });

  const streamCtrl: { signal: AbortSignal; cleanup: () => void } = {
    signal: new AbortController().signal,
    cleanup: () => {},
  };
  let res: Response;
  try {
    ({ res } = await retryFetch(doFetch, signal, streamCtrl));
  } catch (e) {
    streamCtrl.cleanup();
    if (isAbort(e) && signal?.aborted) {
      throw new DOMException('The request was aborted', 'AbortError');
    }
    throw new Error(`LLM_TIMEOUT: ${e instanceof Error ? e.message : String(e)}`);
  }

  if (!res.ok) {
    streamCtrl.cleanup();
    const errText = await res.text().catch(() => '');
    if (res.status === 401) throw new Error('API_KEY_INVALID');
    if (res.status === 429) throw new Error('RATE_LIMITED');
    const clean = errText.replace(/<[^>]+>/g, '').trim().slice(0, 300) || '';
    throw new Error(`LLM_API_${res.status}${clean ? ': ' + clean : ''}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let fullText = '';
  let buf = '';

  const toolCallsMap = new Map<number, ToolCall>();
  const announcedToolNames = new Set<string>();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    const lines = buf.split('\n');
    buf = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data: ')) continue;
      const data = trimmed.slice(6);
      if (data === '[DONE]') break;
      try {
        const json = JSON.parse(data);
        const delta = json.choices?.[0]?.delta;
        const chunk = delta?.content || '';
        if (chunk) {
          fullText += chunk;
          onChunk(chunk);
        }
        if (delta?.tool_calls) {
          for (const tc of delta.tool_calls) {
            const idx = tc?.index ?? 0;
            const existing = toolCallsMap.get(idx) || { id: '', name: '', arguments: '' };
            if (tc?.id) existing.id = tc.id;
            if (tc?.function?.name) existing.name = tc.function.name;
            if (tc?.function?.arguments) existing.arguments += tc.function.arguments;
            toolCallsMap.set(idx, existing);
            if (existing.name && !announcedToolNames.has(existing.name)) {
              announcedToolNames.add(existing.name);
              const toolMsg = `\n⚙️ [tool] ${existing.name} ...\n`;
              onChunk(toolMsg);
            }
          }
        }
      } catch {
        /* ignore */
      }
    }
  }

  const toolCalls = [...toolCallsMap.values()]
    .filter(tc => tc.name)
    .map(tc => ({ ...tc, arguments: tc.arguments || '{}' }));

  return { text: fullText, toolCalls };
}

/* ═══════════════════════════════════════════════════════════
   parseAIResponse
   ═══════════════════════════════════════════════════════════ */

export function parseAIResponse(raw: string): ParsedResponse {
  const commands: string[] = [];
  const writes: { path: string; content: string }[] = [];
  const panels: string[] = [];
  let loopAction: 'continue' | 'finish' | 'none' = 'none';

  const cmdRegex = /\[CMD:([^\]]+)\]/g;
  let match: RegExpExecArray | null;
  while ((match = cmdRegex.exec(raw)) !== null) {
    commands.push(match[1].trim());
  }

  const writeRegex = /\[WRITE:([^\]]+)\]([\s\S]*?)\[\/WRITE\]/g;
  while ((match = writeRegex.exec(raw)) !== null) {
    writes.push({ path: match[1].trim(), content: match[2].trim() });
  }

  const panelRegex = /\[UPDATE_PANEL\]([\s\S]*?)\[\/UPDATE_PANEL\]/g;
  while ((match = panelRegex.exec(raw)) !== null) {
    panels.push(match[1].trim());
  }

  if (/\[LOOP:continue\]/i.test(raw)) {
    loopAction = 'continue';
  } else if (/\[LOOP:finish\]/i.test(raw)) {
    loopAction = 'finish';
  }

  const text = raw
    .replace(cmdRegex, '')
    .replace(/\[WRITE:[^\]]+\][\s\S]*?\[\/WRITE\]/g, '')
    .replace(/\[UPDATE_PANEL\][\s\S]*?\[\/UPDATE_PANEL\]/g, '')
    .replace(/\[GENERATE_MODULE:[^\]]*\][\s\S]*?\[\/GENERATE_MODULE\]/g, '')
    .replace(/\[LOOP:continue\]/gi, '')
    .replace(/\[LOOP:finish\]/gi, '')
    .trim();

  return { text, commands, writes, panels, loopAction };
}

/* ═══════════════════════════════════════════════════════════
   System prompt
   ═══════════════════════════════════════════════════════════ */

export function buildSystemPrompt(curBridge?: string): string {
  return [
    '你是多桥梁CPDV损伤看板的调度层。',
    '你绝不自己计算CPDV，所有数值必须来自底层pipeline的真实输出。',
    '解析用户命令 → 调用相应工具执行计算 → 将结果回填看板。',
    '',
    '核心命令：',
    '| 命令 | 动作 |',
    '|------|------|',
    '| 「看板总览」 | 汇总各桥状态 |',
    '| 「注册桥梁 <名>」[参数] | 注册桥梁（单位: km/h→m/s、kN→N、GPa→Pa、t→kg、mm→m） |',
    '| 「计算CPDV」[桥名][参数] | 运行CPDV计算 |',
    '| 「预测损伤」[桥名][模型] | 单裂缝预测 |',
    '| 「多裂缝预测」[桥名] | 多裂缝推理 |',
    '| 「随机工况分析」[裂纹参数] | 随机工况分析 |',
    '| 「对比 <桥A> <桥B>」 | 双桥对比 |',
    '| 「刷新看板」 | 重新汇总数据 |',
    '',
    '汇报规范：数值永远带单位（m、m/s、%、Pa）；预测结果必附模型标签 + MAE指标 + 是否达标。',
    '训练模型或耗时操作必须先报告预计耗时并请求确认。',
    curBridge ? `当前选中的桥梁: ${curBridge}` : '',
  ].join('\n');
}
