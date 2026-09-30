import type { ToolDefinition } from './llm-client';
import type { CommandMeta } from './api-client';

/** 危险命令黑名单：前端拦截，不发送到后端。
 *  对应 COMMAND_META 中的 action 字段（前缀 cb_ 已去除）。
 *  包含：删除所有数据、重置模型、关机等破坏性操作。
 */
export const DANGEROUS_COMMANDS = new Set<string>([
  'delete_all_data',
  'reset_model',
  'shutdown',
  'purge_registry',
  'factory_reset',
]);

/** 检查工具名是否为危险命令（去掉 cb_ 前缀后匹配） */
export function isDangerousTool(toolName: string): boolean {
  const action = toolName.startsWith('cb_') ? toolName.slice(3) : toolName;
  return DANGEROUS_COMMANDS.has(action);
}

/** G9: 从后端 COMMAND_META 生成 OpenAI function-calling tool 列表。
 *  输入：CommandMeta[]（fetchCommandMeta() 的结果）。
 *  输出：ToolDefinition[]，可直接传给 buildSystemPrompt → LLM。
 *  危险命令不会注册为 function-calling 工具（llm_tool=false 或被过滤）。
 */
export function buildCpdvTools(meta: CommandMeta[]): ToolDefinition[] {
  return meta
    .filter((m) => m.llm_tool && !isDangerousTool('cb_' + m.action))  // 过滤危险命令
    .map((m) => {
      const name = 'cb_' + m.action;
      const properties: Record<string, any> = {};
      for (const k of m.inputs) {
        // 输入字段类型启发式：bridge / name / model 等字符串，depth/n_samples/epochs 等 number
        const isNum = /depth|n_samples|epochs|L|mv|V|cv|kv/.test(k);
        properties[k] = {
          type: isNum ? 'number' : 'string',
          description: m.inputs_desc?.[k] || k,
        };
      }
      const parameters: any = { type: 'object', properties };
      // 使用 required_inputs（若有），否则回退到 inputs（旧行为）
      const required = m.required_inputs && m.required_inputs.length > 0 ? m.required_inputs : m.inputs;
      if (required.length > 0) parameters.required = required;
      return {
        type: 'function',
        function: {
          name,
          description: m.description,
          parameters,
        },
      };
    });
}