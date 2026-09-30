export interface CpdvLLMConfig {
  backend: string;
  apiKey: string;
  baseUrl: string;
  model: string;
  temperature: number;
  systemPrompt: string;
}

const STORAGE_KEY = 'cpdv_llm_config';

/** 默认大模型配置：key 从 VITE_API_KEY 环境变量读取，留空走运行时用户填写。
 *  本地开发：复制 frontend/.env.local.example → .env.local 后填入真 key。
 *  生产部署：通过部署平台 secret 注入 VITE_API_KEY。
 */
const env = (import.meta as any).env ?? {};
const DEFAULT_API_KEY: string = (env.VITE_API_KEY as string) || '';
const DEFAULT_BASE_URL: string = (env.VITE_API_BASE_URL as string) || 'https://api.agnes-ai.cn/v1';
const DEFAULT_MODEL: string = (env.VITE_API_MODEL as string) || 'agnes-2.5-flash';

export const DEFAULT_LLM_CONFIG: CpdvLLMConfig = {
  backend: 'openai',
  apiKey: DEFAULT_API_KEY,
  baseUrl: DEFAULT_BASE_URL,
  model: DEFAULT_MODEL,
  temperature: 0.4,
  systemPrompt: '',
};

export function getLLMConfig(): CpdvLLMConfig {
  try {
    const s = localStorage.getItem(STORAGE_KEY);
    if (s) {
      const parsed = JSON.parse(s) as Partial<CpdvLLMConfig>;
      return {
        ...DEFAULT_LLM_CONFIG,
        ...parsed,
        temperature: Number(parsed.temperature ?? DEFAULT_LLM_CONFIG.temperature),
      };
    }
  } catch {
    /* ignore */
  }
  return { ...DEFAULT_LLM_CONFIG };
}

export function saveLLMConfig(c: CpdvLLMConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
}
