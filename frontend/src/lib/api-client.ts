import type { DashboardData, Bridge } from './types';

const BASE = '/api';

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

// ─────────────────────────────────────────────────────────────────────
// G9: 命令元数据（启动时拉一次，缓存到模块级）
// ─────────────────────────────────────────────────────────────────────
export interface CommandMeta {
  action: string;
  name: string;
  description: string;
  category: 'view' | 'analysis' | 'model' | 'utility';
  quick: boolean;
  llm_tool: boolean;
  phases: Array<'short' | 'medium' | 'long'>;
  inputs: string[];
  required_inputs?: string[];  // G1: 必填参数（默认全部 inputs），用于区分可选仿真参数
  inputs_desc: Record<string, string>;
  route: {
    method: 'GET' | 'POST';
    path: string;
    map?: string;  // 后端返回的是字符串化的 lambda，前端再 eval
  };
  output_keys: string[];
}

export interface CommandMetaResponse {
  version: number;
  source: string;
  commands: CommandMeta[];
}

let _metaCache: CommandMeta[] | null = null;
let _metaPromise: Promise<CommandMeta[]> | null = null;

/** 带重试的 command-meta 获取（最多 3 次，指数退避）。失败不缓存空数组，保留重试机会。 */
export async function fetchCommandMeta(retries = 3): Promise<CommandMeta[]> {
  if (_metaCache) return _metaCache;
  if (_metaPromise) return _metaPromise;

  const attemptFetch = async (attempt: number): Promise<CommandMeta[]> => {
    try {
      const r = await getJSON<CommandMetaResponse>('/command-meta');
      _metaCache = r.commands;
      return _metaCache;
    } catch (e) {
      if (attempt < retries) {
        const delay = 500 * 2 ** (attempt - 1); // 500ms, 1s, 2s...
        await new Promise(res => setTimeout(res, delay));
        return attemptFetch(attempt + 1);
      }
      // 彻底失败：不缓存空数组，保留下次调用重试机会
      throw e;
    }
  };

  _metaPromise = attemptFetch(1).finally(() => { _metaPromise = null; });
  return _metaPromise;
}

/** 同步版（前提是已 await fetchCommandMeta()）。用于组件 mount 后立即渲染。 */
export function getCommandMetaSync(): CommandMeta[] {
  return _metaCache || [];
}

/** 清除 command-meta 缓存，下次调用 fetchCommandMeta() 会重新拉取。 */
export function resetCommandMeta(): void {
  _metaCache = null;
  _metaPromise = null;
}

// ─────────────────────────────────────────────────────────────────────
// /api/dashboard + bridges
// ─────────────────────────────────────────────────────────────────────
export async function fetchDashboard(): Promise<DashboardData> {
  try {
    return await getJSON<DashboardData>('/dashboard');
  } catch (e) {
    const mod = await import('../../../sample_data/dashboard_data');
    return mod.SAMPLE_DASHBOARD;
  }
}

export async function fetchBridgeSignals(bridgeId: string): Promise<{cpdv_signals?: any[], combined_cpdv?: any[]}> {
  return getJSON(`/signals/${bridgeId}`);
}

export async function fetchBridges(): Promise<Bridge[]> {
  return getJSON<Bridge[]>('/bridges');
}

// ─────────────────────────────────────────────────────────────────────
// G9: TOOL_ROUTE 从 meta 动态生成。
// 不再硬编码 cb_list_bridges → /bridges 等映射，所有信息来自 /api/command-meta。
// cb_* 命名规则：cb_<action>（如 action=cpdv → cb_cpdv）
// ─────────────────────────────────────────────────────────────────────
function actionToToolName(action: string): string {
  return 'cb_' + action;
}

function buildRouteFromMeta(meta: CommandMeta): {
  name: string;
  method: 'GET' | 'POST';
  path: string;
  map?: (a: Record<string, any>) => Record<string, any>;
} {
  const route = meta.route;
  let mapFn: ((a: Record<string, any>) => Record<string, any>) | undefined;
  if (route.map) {
    // 后端返回的是字符串化的 lambda，这里用 Function 构造（仅 meta 来自可信后端，安全）
    try {
      // route.map 形如 "lambda a: {'key': a.get('x')}" —— Python 风格，前端转箭头函数
      mapFn = pythonLambdaToFn(route.map);
    } catch {
      mapFn = (a) => a;
    }
  }
  return {
    name: actionToToolName(meta.action),
    method: route.method,
    path: route.path,
    map: mapFn,
  };
}

/** 把后端的 Python lambda 字符串转成 JS 箭头函数。
 *  支持的语法："lambda a: {'key': a.get('x'), 'y': a.get('y')}"
 *  简易解析：识别 a.get('xxx') / a.get("xxx") 并替换为 a?.xxx ?? null
 */
function pythonLambdaToFn(src: string): (a: Record<string, any>) => Record<string, any> {
  // 1. 去掉 lambda a:
  const body = src.replace(/^lambda\s+\w+\s*:\s*/, '');
  // 2. 找 dict 字面量 {...}，逐 key 解析
  const dictMatch = body.match(/^\{(.*)\}$/s);
  if (!dictMatch) {
    // 恒等 lambda（"lambda a: a"）：原样透传 LLM 参数，避免被整体丢弃导致 422
    return (a) => ({ ...(a ?? {}) });
  }
  const inner = dictMatch[1];
  // 简易 split: 按 ', ' 分割，但需要处理嵌套 dict/str
  const items = splitTopLevelCommas(inner);
  const keys: Array<{ key: string; expr: string }> = [];
  for (const it of items) {
    const kv = it.match(/^\s*['"]?(\w+)['"]?\s*:\s*(.+)$/s);
    if (!kv) continue;
    const pyKey = kv[1];
    const pyExpr = kv[2].trim();
    // 把 a.get('xxx') 转成 a?.xxx
    const jsExpr = pyExpr.replace(/(\w+)\.get\(['"]([\w_]+)['"]\)/g, '$1?.$2');
    keys.push({ key: pyKey, expr: jsExpr });
  }
  // 3. 构造 JS 箭头函数
  const fnBody = `const out = {}; ${keys.map((k) => `out[${JSON.stringify(k.key)}] = (${k.expr});`).join(' ')} return out;`;
  return new Function('a', fnBody) as (a: Record<string, any>) => Record<string, any>;
}

function splitTopLevelCommas(s: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let inStr: string | null = null;
  let buf = '';
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inStr) {
        buf += c;
        if (c === inStr && s[i - 1] !== '\\') inStr = null;
        continue;
    }
    if (c === '"' || c === "'") { inStr = c; buf += c; continue; }
    if (c === '{' || c === '[' || c === '(') depth++;
    if (c === '}' || c === ']' || c === ')') depth--;
    if (c === ',' && depth === 0) { out.push(buf); buf = ''; continue; }
    buf += c;
  }
  if (buf.trim()) out.push(buf);
  return out;
}

/** 生成 TOOL_ROUTE（name → {method, path, map}） */
export function buildToolRoute(meta?: CommandMeta[]): Record<string, {
  method: 'GET' | 'POST';
  path: string;
  map?: (a: any) => any;
}> {
  const list = meta || _metaCache || [];
  const out: Record<string, any> = {};
  for (const m of list) {
    if (!m.llm_tool) continue;
    const route = buildRouteFromMeta(m);
    out[route.name] = { method: route.method, path: route.path, map: route.map };
  }
  return out;
}

import { isDangerousTool } from './cpdv-tools';

/** 执行一个工具调用。返回 JSON 结果；route 不存在则抛错。
 *  G9：route 从 meta 动态生成（首次调用会自动 loadCommandMeta）。
 *  安全：危险命令在前端直接拦截，不发送到后端。 */
export async function executeToolCall(name: string, args: any): Promise<any> {
  // 安全检查：危险命令前端拦截
  if (isDangerousTool(name)) {
    throw new Error(`⚠️ 安全拦截：${name} 为危险命令，已禁止执行。如需执行请联系管理员。`);
  }
  // 确保 meta 已加载
  const meta = await fetchCommandMeta();
  const toolRoute = buildToolRoute(meta);
  const route = toolRoute[name];
  if (!route) throw new Error(`未知工具: ${name}`);
  const mapped = route.map ? route.map(args ?? {}) : (args ?? {});
  if (route.method === 'GET') {
    const qs = new URLSearchParams(
      Object.entries(mapped).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v]) => [k, String(v)])
    ).toString();
    return getJSON<any>(`${route.path}?${qs}`);
  }
  return postJSON<any>(route.path, mapped);
}

export async function fetchAllBridgeSignals(): Promise<Record<string, {cpdv_signals?: any[], combined_cpdv?: any[]}>> {
  return getJSON('/signals/batch');
}

export async function refreshDashboard(): Promise<{
  dashboard: any;
  signals: Record<string, any>;
  records: any[];
  bridge_count: number;
  record_count: number;
  generated: string;
}> {
  const resp = await fetch(BASE + '/signals/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
  return resp.json();
}

export const api = { fetchDashboard, fetchBridgeSignals, fetchAllBridgeSignals, refreshDashboard, fetchBridges, executeToolCall, fetchCommandMeta, deleteBridge };

async function deleteJSON<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path, { method: 'DELETE' });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function deleteBridge(id: string): Promise<{ ok: boolean; deleted: { id: string; name: string } }> {
  return deleteJSON(`/bridges/${id}`);
}