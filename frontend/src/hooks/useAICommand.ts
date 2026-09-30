/** AI Command System - Frontend Hooks
 * 
 * Provides React hooks for executing AI commands with progress tracking
 * and automatic dashboard synchronization.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// ─────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────

export interface AICommandRequest {
  jsonrpc: '2.0';
  id: string;
  method: string;
  params: Record<string, any>;
  meta?: {
    source?: 'chat' | 'dashboard' | 'auto';
    correlation_id?: string;
  };
}

export interface AICommandResponse {
  jsonrpc: '2.0';
  id: string;
  result?: any;
  error?: { code: number; message: string; data?: any };
  progress?: {
    stage: string;
    percent: number;
    message: string;
    eta_seconds?: number;
  };
}

export interface PipelineTaskStatus {
  task_id: string;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';
  pipelines: string[];
  mode: string;
  started_at: string;
  completed_at: string | null;
  current_pipeline: string | null;
  current_stage: string | null;
  progress: number;
  logs: string[];
  outputs: string[];
  error: string | null;
  results: Record<string, any>;
}

export interface DashboardWidgetData {
  cpdv_timeseries?: {
    t: number[];
    signals: Record<string, number[]>;
    depth: number;
    positions: number[];
  };
  model_scorecard?: Record<string, any>;
  peak_vs_position?: {
    peak_vs_position: Record<string, number[]>;
    peak_vs_depth: Record<string, number[]>;
    depths: number[];
    distances: number[];
  };
  peak_vs_depth?: any;
  cv_analysis?: any;
  multi_position_boxplot?: any;
  road_profile?: any;
  error_distribution?: any;
  multi_crack_comparison?: any;
}

export interface DashboardSyncResult {
  widget_data: DashboardWidgetData;
  timestamp: string;
  source: string;
}

export interface CommandMeta {
  version: string;
  categories: Record<string, { label: string; description: string; color: string; icon: string }>;
  commands: Record<string, any>;
  widgets: Record<string, any>;
  pipeline_stages: Record<string, any>;
}

// ─────────────────────────────────────────────────────────────────────
// API Base
// ─────────────────────────────────────────────────────────────────────

const AI_API_BASE = '/api/ai';

async function aiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${AI_API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

// ─────────────────────────────────────────────────────────────────────
// useAICommand - Main command execution hook
// ─────────────────────────────────────────────────────────────────────

export interface UseAICommandState {
  loading: boolean;
  error: string | null;
  lastResponse: AICommandResponse | null;
  progress: AICommandResponse['progress'] | null;
  taskId: string | null;
}

export interface UseAICommandActions {
  execute: (method: string, params: Record<string, any>, options?: {
    onProgress?: (progress: AICommandResponse['progress']) => void;
    onResult?: (result: any) => void;
    onError?: (error: Error) => void;
  }) => Promise<AICommandResponse>;
  cancel: (taskId: string) => Promise<void>;
  getPipelineStatus: (taskId: string) => Promise<PipelineTaskStatus>;
  clear: () => void;
}

export function useAICommand(): [UseAICommandState, UseAICommandActions] {
  const [state, setState] = useState<UseAICommandState>({
    loading: false,
    error: null,
    lastResponse: null,
    progress: null,
    taskId: null,
  });

  const pendingRequests = useRef<Map<string, {
    resolve: (value: AICommandResponse) => void;
    reject: (error: Error) => void;
    onProgress?: (progress: AICommandResponse['progress']) => void;
  }>>(new Map()) as React.MutableRefObject<Map<string, {
    resolve: (value: AICommandResponse) => void;
    reject: (error: Error) => void;
    onProgress?: (progress: AICommandResponse['progress']) => void;
  }>>;

  // WebSocket for progress updates
  useEffect(() => {
    const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/progress?tags=pipeline,train,cpdv,random,analysis`);
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        // Handle progress updates
        if (msg.progress) {
          setState(prev => ({ ...prev, progress: msg.progress }));
          
          // Call request-specific progress callback
          const req = pendingRequests.current.get(msg.command_id || '');
          if (req?.onProgress) {
            req.onProgress(msg.progress);
          }
        }
        
        // Handle command responses
        if (msg.id && pendingRequests.current.has(msg.id)) {
          const req = pendingRequests.current.get(msg.id)!;
          pendingRequests.current.delete(msg.id);
          
          if (msg.error) {
            req.reject(new Error(msg.error.message));
          } else {
            req.resolve(msg);
          }
        }
      } catch (e) {
        console.warn('WS message parse error:', e);
      }
    };
    
    ws.onerror = (err) => {
      console.warn('AI Command WS error:', err);
    };
    
    return () => ws.close();
  }, []);

  const execute = useCallback((
    method: string,
    params: Record<string, any>,
    options?: {
      onProgress?: (progress: AICommandResponse['progress']) => void;
      onResult?: (result: any) => void;
      onError?: (error: Error) => void;
    }
  ) => {
    const id = `cmd_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 9)}`;
    
    setState(prev => ({ ...prev, loading: true, error: null, taskId: null }));
    
    const request: AICommandRequest = {
      jsonrpc: '2.0',
      id,
      method,
      params,
      meta: { source: 'dashboard' },
    };
    
    return new Promise<AICommandResponse>((resolve, reject) => {
      pendingRequests.current.set(id, { resolve, reject, onProgress: options?.onProgress });
      
      // Send via fetch (REST) - WebSocket will deliver response
      fetch(`${AI_API_BASE}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      }).catch(reject);
      
      // Timeout fallback
      setTimeout(() => {
        if (pendingRequests.current.has(id)) {
          pendingRequests.current.delete(id);
          reject(new Error('Command timeout'));
        }
      }, 30000);
    }).then(response => {
      setState(prev => ({
        ...prev,
        loading: false,
        lastResponse: response,
        progress: null,
        taskId: response.result?.task_id || null,
        error: response.error ? response.error.message : null,
      }));
      
      if (response.error) {
        options?.onError?.(new Error(response.error.message));
      } else {
        options?.onResult?.(response.result);
      }
      
      return response;
    }).catch(err => {
      setState(prev => ({ ...prev, loading: false, error: err.message }));
      options?.onError?.(err);
      throw err;
    });
  }, []);

  const cancel = useCallback(async (taskId: string) => {
    await execute('pipeline.cancel', { task_id: taskId });
  }, []);

  const getPipelineStatus = useCallback(async (taskId: string) => {
    const response = await execute('pipeline.status', { task_id: taskId });
    return response.result as PipelineTaskStatus;
  }, []);

  const clear = useCallback(() => {
    setState({ loading: false, error: null, lastResponse: null, progress: null, taskId: null });
  }, []);

  return [state, { execute, cancel, getPipelineStatus, clear }];
}

// ─────────────────────────────────────────────────────────────────────
// useDashboardSync - Dashboard data synchronization hook
// ─────────────────────────────────────────────────────────────────────

export interface UseDashboardSyncState {
  loading: boolean;
  error: string | null;
  widgetData: DashboardWidgetData | null;
  lastSync: string | null;
}

export function useDashboardSync(widgets?: string[]) {
  const [state, setState] = useState<UseDashboardSyncState>({
    loading: false,
    error: null,
    widgetData: null,
    lastSync: null,
  });

  const sync = useCallback(async (forceRefresh = false) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await aiFetch<DashboardSyncResult>('/command', {
        method: 'POST',
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: `sync_${Date.now()}`,
          method: 'dashboard.sync',
          params: { widgets: widgets || [
            'cpdv_timeseries', 'model_scorecard', 
            'peak_vs_position', 'cv_analysis'
          ], force_refresh: forceRefresh },
        }),
      });
      
      setState({
        loading: false,
        error: null,
        widgetData: result.widget_data,
        lastSync: result.timestamp,
      });
      
      return result;
    } catch (e) {
      setState(prev => ({ ...prev, loading: false, error: String(e) }));
      throw e;
    }
  }, [widgets]);

  // Auto-sync on mount
  useEffect(() => {
    sync();
  }, [sync]);

  return { ...state, sync, refresh: () => sync(true) };
}

// ─────────────────────────────────────────────────────────────────────
// usePipelineMonitor - Pipeline execution monitoring hook
// ─────────────────────────────────────────────────────────────────────

export function usePipelineMonitor(taskId: string | null, enabled = true) {
  const [status, setStatus] = useState<PipelineTaskStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!taskId || !enabled) return;
    
    let cancelled = false;
    
    const poll = async () => {
      setLoading(true);
      try {
        const response = await aiFetch<any>('/command', {
          method: 'POST',
          body: JSON.stringify({
            jsonrpc: '2.0',
            id: `status_${Date.now()}`,
            method: 'pipeline.status',
            params: { task_id: taskId },
          }),
        });
        
        if (!cancelled) {
          setStatus(response.result);
          if (response.result?.status === 'running') {
            setTimeout(poll, 2000);
          }
        }
      } catch (e) {
        console.error('Pipeline status poll error:', e);
        if (!cancelled) setTimeout(poll, 5000);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    
    poll();
    
    return () => { cancelled = true; };
  }, [taskId, enabled]);

  return { status, loading };
}

// ─────────────────────────────────────────────────────────────────────
// useCommandMeta - Fetch command metadata for dynamic UI
// ─────────────────────────────────────────────────────────────────────

export function useCommandMeta() {
  const [meta, setMeta] = useState<CommandMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    
    aiFetch<CommandMeta>('/commands/meta')
      .then(data => {
        if (!cancelled) {
          setMeta(data);
          setLoading(false);
        }
      })
      .catch(e => {
        if (!cancelled) {
          setError(String(e));
          setLoading(false);
        }
      });
    
    return () => { cancelled = true; };
  }, []);

  return { meta, loading, error };
}

// ─────────────────────────────────────────────────────────────────────
// Helper: Data transformers for widgets
// ─────────────────────────────────────────────────────────────────────

export const DataTransformers = {
  /** Downsample CPDV signals for chart rendering */
  downsampleCpdv: (data: any, targetPoints = 400) => {
    if (!data?.signals) return data;
    
    const result = { ...data };
    for (const [key, signal] of Object.entries(data.signals)) {
      const arr = signal as number[];
      if (arr.length > targetPoints) {
        const idx = Array.from({ length: targetPoints }, (_, i) => 
          Math.floor(i * (arr.length - 1) / (targetPoints - 1))
        );
        result.signals[key] = idx.map(i => arr[i]);
      }
    }
    return result;
  },

  /** Normalize model metrics for scorecard display */
  normalizeMetrics: (data: any) => {
    if (!data) return {};
    
    const models = ['cracknet', 'lstm', 'multi_crack_dual', 'pinn'];
    const result: Record<string, any> = {};
    
    for (const model of models) {
      // Find model data in various possible locations
      let metrics = data[model] || data[`${model}`] || 
        Object.values(data).find((v: any) => v?.model_type === model);
      
      if (metrics) {
        result[model] = {
          mae_pos: metrics.mae_pos ?? metrics.position_mae ?? 0,
          mae_depth: metrics.mae_depth ?? metrics.depth_mae ?? 0,
          f1: metrics.f1 ?? 0,
          precision: metrics.precision ?? 0,
          recall: metrics.recall ?? 0,
          r2: metrics.r2 ?? 0,
          pde_residual: metrics.pde_residual ?? 0,
          data_mse: metrics.data_mse ?? 0,
        };
      }
    }
    
    return result;
  },

  /** Format CV analysis for boxplot */
  formatCvForBoxplot: (data: any) => {
    if (!data?.position_results) return { labels: [], datasets: [] };
    
    const labels: string[] = [];
    const datasets: number[][] = [];
    const cvLabels: string[] = [];
    
    for (const [pos, result] of Object.entries(data.position_results)) {
      labels.push(`pos=${pos}m`);
      datasets.push((result as any).peaks || []);
      cvLabels.push(`CV=${((result as any).cv * 100).toFixed(1)}%`);
    }
    
    return { labels, datasets, cvLabels };
  },
};