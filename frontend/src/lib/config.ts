export interface CpdvLLMConfig {
  backend: string;
  apiKey: string;
  baseUrl: string;
  model: string;
  systemPrompt: string;
}

const STORAGE_KEY = 'cpdv_llm_config';

export function getLLMConfig(): CpdvLLMConfig {
  try {
    const s = localStorage.getItem(STORAGE_KEY);
    if (s) {
      return {
        backend: 'openai',
        apiKey: '',
        baseUrl: '',
        model: '',
        systemPrompt: '',
        ...JSON.parse(s),
      };
    }
  } catch {
    /* ignore */
  }
  return { backend: 'openai', apiKey: '', baseUrl: '', model: '', systemPrompt: '' };
}

export function saveLLMConfig(c: CpdvLLMConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
}
