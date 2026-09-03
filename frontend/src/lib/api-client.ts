import type { DashboardData, Bridge } from './types';

const BASE = '/api';

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

/** 读取看板数据（优先后端 /api/dashboard，失败回退到 sample_data） */
export async function fetchDashboard(): Promise<DashboardData> {
  try {
    return await getJSON<DashboardData>('/dashboard');
  } catch (e) {
    // 后端未启动时回退到本地示例数据
    const mod = await import('../../../sample_data/dashboard_data.ts');
    return mod.SAMPLE_DASHBOARD;
  }
}

export async function fetchBridges(): Promise<Bridge[]> {
  return getJSON<Bridge[]>('/bridges');
}

export const api = { fetchDashboard, fetchBridges };
