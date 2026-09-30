/** 算法代码库看板 - React Hooks */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  fetchAlgorithmLibraries,
  fetchTopology,
  searchSymbols,
  fetchContract,
  compareVersions,
  fetchTimeline,
  triggerSync,
  fetchSyncStatus,
  triggerTrain,
  triggerPipelineRun,
  fetchPipelineStatus,
  triggerEvaluate,
  fetchEvaluateStatus,
  recordExperiment,
  fetchExperimentRecords,
  compareModels,
  triggerSyncLibraries,
  fetchSyncLibrariesStatus,
} from '../lib/algorithm-api';
import type {
  AlgorithmLibrary,
  PipelineRunResult,
  EvaluateRequest,
  RecordExperimentRequest,
  CompareModelsRequest,
  CompareModelsResponse,
  SyncLibrariesRequest,
} from '../lib/algorithm-types';

// ─────────────────────────────────────────────────────────────────────
// 库列表 Hook
// ─────────────────────────────────────────────────────────────────────

export function useAlgorithmLibraries() {
  const [libraries, setLibraries] = useState<AlgorithmLibrary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<number>(0);
  const [status, setStatus] = useState<'ok' | 'no_data' | 'syncing'>('no_data');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAlgorithmLibraries();
      setLibraries(res.libraries);
      setLastSync(res.last_sync);
      setStatus(res.status);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { libraries, loading, error, lastSync, status, refresh: load };
}

// ─────────────────────────────────────────────────────────────────────
// 拓扑图 Hook
// ─────────────────────────────────────────────────────────────────────

interface UseTopologyOptions {
  library?: string;
  focusNode?: string;
  depth?: number;
  autoRefresh?: boolean;
}

export function useTopology(options: UseTopologyOptions = {}) {
  const [data, setData] = useState<{
    nodes: any[];
    edges: any[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchTopology({
        library: options.library,
        focus_node: options.focusNode,
        depth: options.depth,
      });
      setData({ nodes: res.nodes, edges: res.edges });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [options.library, options.focusNode, options.depth]);

  useEffect(() => { load(); }, [load]);

  // 派生数据：按类型分组节点
  const nodesByType = useMemo(() => {
    if (!data) return {};
    const groups: Record<string, any[]> = {};
    data.nodes.forEach(node => {
      const type = node.type || 'unknown';
      if (!groups[type]) groups[type] = [];
      groups[type].push(node);
    });
    return groups;
  }, [data]);

  // 派生数据：按模块分组节点
  const nodesByModule = useMemo(() => {
    if (!data) return {};
    const groups: Record<string, any[]> = {};
    data.nodes.forEach(node => {
      const mod = node.module || 'unknown';
      if (!groups[mod]) groups[mod] = [];
      groups[mod].push(node);
    });
    return groups;
  }, [data]);

  return { data, nodesByType, nodesByModule, loading, error, refresh: load };
}

// ─────────────────────────────────────────────────────────────────────
// 符号搜索 Hook
// ─────────────────────────────────────────────────────────────────────

export function useSymbolSearch() {
  const [results, setResults] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (params: { q: string; type?: string; library?: string; limit?: number }) => {
    if (!params.q.trim()) {
      setResults([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    try {
      const res = await searchSymbols(params);
      setResults(res.symbols);
      setTotal(res.total);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, total, loading, error, search };
}

// ─────────────────────────────────────────────────────────────────────
// 契约详情 Hook
// ─────────────────────────────────────────────────────────────────────

export function useContract(protocol?: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (p: string) => {
    if (!p) return;
    setLoading(true);
    try {
      const res = await fetchContract(p);
      setData(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (protocol) load(protocol); }, [protocol, load]);

  return { data, loading, error, refresh: load };
}

// ─────────────────────────────────────────────────────────────────────
// 版本对比 Hook
// ─────────────────────────────────────────────────────────────────────

export function useVersionDiff() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compare = useCallback(async (request: { base: string; target: string; dimension: 'all' | 'architecture' | 'loss' | 'trainer' | 'config' }) => {
    setLoading(true);
    try {
      const res = await compareVersions({ base: request.base, target: request.target, dimension: request.dimension });
      setData(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, compare };
}

// ─────────────────────────────────────────────────────────────────────
// 时间轴 Hook
// ─────────────────────────────────────────────────────────────────────

export function useTimeline(library?: string, since?: string, until?: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchTimeline(library, since, until);
      setData(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [library, since, until]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refresh: load };
}

// ─────────────────────────────────────────────────────────────────────
// 同步触发 Hook
// ─────────────────────────────────────────────────────────────────────

export function useSync() {
  const [syncState, setSyncState] = useState<{
    status: 'idle' | 'started' | 'running' | 'completed' | 'failed';
    pid?: number;
    message?: string;
    error?: string;
  }>({ status: 'idle' });

  const startSync = useCallback(async (request = { full: false }) => {
    setSyncState({ status: 'started' });
    try {
      const res = await triggerSync(request);
      setSyncState({ status: 'started', pid: res.pid, message: res.message });
      // 轮询状态
      if (res.pid) pollStatus(res.pid);
    } catch (e) {
      setSyncState({ status: 'failed', error: String(e) });
    }
  }, []);

  const pollStatus = useCallback(async (pid: number) => {
    const check = async () => {
      try {
        const res = await fetchSyncStatus(pid);
        if (res.status === 'running') {
          setSyncState(prev => ({ ...prev, status: 'running' }));
          setTimeout(check, 2000);
        } else {
          setSyncState({ status: 'completed', message: '同步完成' });
        }
      } catch {
        setSyncState({ status: 'failed', error: '状态查询失败' });
      }
    };
    check();
  }, []);

  return { syncState, startSync };
}

// ─────────────────────────────────────────────────────────────────────
// 模型训练 Hook
// ─────────────────────────────────────────────────────────────────────

export interface TrainState {
  status: 'idle' | 'started' | 'running' | 'completed' | 'failed';
  taskId?: string;
  message?: string;
  error?: string;
  modelPath?: string;
  metrics?: Record<string, number>;
  progress?: {
    stage: string;
    message: string;
    percent: number;
    epoch?: number;
    totalEpochs?: number;
    loss?: number;
  };
}

export function useTraining() {
  const [trainState, setTrainState] = useState<TrainState>({ status: 'idle' });

  const startTrain = useCallback(async (request: {
    model_type: string;
    n_samples: number;
    epochs: number;
    bridge?: string;
    regenerate: boolean;
    data?: string;
    model?: string;
  }) => {
    setTrainState({ status: 'started', message: '启动训练...' });
    try {
      const res = await triggerTrain(request);
      if (res.task_id) {
        setTrainState({ status: 'running', taskId: res.task_id, message: res.message || '训练已启动' });
      } else if (res.status === 'completed') {
        setTrainState({
          status: 'completed',
          message: '训练完成',
          modelPath: res.model_path,
          metrics: res.metrics,
        });
      } else {
        setTrainState({ status: 'failed', error: res.error || '训练启动失败' });
      }
    } catch (e) {
      setTrainState({ status: 'failed', error: String(e) });
    }
  }, []);

  const reset = useCallback(() => {
    setTrainState({ status: 'idle' });
  }, []);

  return { trainState, startTrain, reset };
}


// ─────────────────────────────────────────────────────────────────────
// Pipeline 执行 Hook
// ─────────────────────────────────────────────────────────────────────

export interface PipelineState {
  status: 'idle' | 'running' | 'completed' | 'failed';
  taskId?: string;
  message?: string;
  error?: string;
  progress?: {
    stage: string;
    message: string;
    percent: number;
  };
  result?: PipelineRunResult;
}

export function usePipeline() {
  const [pipelineState, setPipelineState] = useState<PipelineState>({ status: 'idle' });

  const startPipeline = useCallback(async (request: {
    name: string;
    description?: string;
    nodes: any[];
    connections: any[];
  }) => {
    setPipelineState({ status: 'running', message: '启动流水线...' });
    try {
      const res = await triggerPipelineRun(request);
      setPipelineState({ 
        status: 'running', 
        taskId: res.task_id, 
        message: res.message || '流水线已启动' 
      });
    } catch (e) {
      setPipelineState({ status: 'failed', error: String(e) });
    }
  }, []);

  const checkStatus = useCallback(async (taskId: string) => {
    try {
      const res = await fetchPipelineStatus(taskId);
      if (res.status === 'completed') {
        setPipelineState({
          status: 'completed',
          taskId,
          message: '流水线完成',
          result: res.result as PipelineRunResult,
        });
      } else if (res.status === 'failed') {
        setPipelineState({
          status: 'failed',
          taskId,
          error: res.error || '执行失败',
        });
      } else {
        setPipelineState(prev => ({
          ...prev,
          status: res.status as any,
          progress: res.progress as any,
        }));
        // 继续轮询
        setTimeout(() => checkStatus(taskId), 2000);
      }
    } catch (e) {
      setPipelineState({ status: 'failed', error: String(e) });
    }
  }, []);

  const reset = useCallback(() => {
    setPipelineState({ status: 'idle' });
  }, []);

  return { pipelineState, startPipeline, checkStatus, reset };
}

// ─────────────────────────────────────────────────────────────────────
// 模型评估 Hook
// ─────────────────────────────────────────────────────────────────────

export interface EvaluateState {
  status: 'idle' | 'started' | 'running' | 'completed' | 'failed';
  taskId?: string;
  message?: string;
  error?: string;
  metrics?: {
    f1: number;
    precision: number;
    recall: number;
    position_mae: number;
    depth_mae: number;
    matches: number;
    n_gt: number;
    n_pred: number;
  };
}

export function useEvaluate() {
  const [evalState, setEvalState] = useState<EvaluateState>({ status: 'idle' });

  const startEvaluate = useCallback(async (request: EvaluateRequest) => {
    setEvalState({ status: 'started', message: '启动评估...' });
    try {
      const res = await triggerEvaluate(request);
      if (res.task_id) {
        setEvalState({ status: 'running', taskId: res.task_id, message: '评估已启动' });
        // 轮询评估状态
        pollEvaluateStatus(res.task_id);
      } else if (res.status === 'completed') {
        setEvalState({
          status: 'completed',
          message: '评估完成',
          metrics: res.metrics,
        });
      } else {
        setEvalState({ status: 'failed', error: res.error || '评估启动失败' });
      }
    } catch (e) {
      setEvalState({ status: 'failed', error: String(e) });
    }
  }, []);

  const pollEvaluateStatus = useCallback(async (taskId: string) => {
    const check = async () => {
      try {
        const res = await fetchEvaluateStatus(taskId);
        if (res.status === 'running') {
          setEvalState(prev => ({ ...prev, status: 'running' }));
          setTimeout(check, 3000);
        } else if (res.status === 'completed') {
          setEvalState({
            status: 'completed',
            message: '评估完成',
            metrics: res.metrics,
          });
        } else {
          setEvalState({ status: 'failed', error: res.error || '评估失败' });
        }
      } catch {
        setEvalState({ status: 'failed', error: '状态查询失败' });
      }
    };
    check();
  }, []);

  const reset = useCallback(() => {
    setEvalState({ status: 'idle' });
  }, []);

  return { evalState, startEvaluate, reset };
}

// ─────────────────────────────────────────────────────────────────────
// 实验记录 Hook
// ─────────────────────────────────────────────────────────────────────

export interface RecordState {
  status: 'idle' | 'started' | 'completed' | 'failed';
  recordId?: string;
  message?: string;
  error?: string;
  records?: ExperimentRecord[];
  total?: number;
  loading?: boolean;
}

export interface ExperimentRecord {
  id: string;
  timestamp: string;
  type: 'train' | 'evaluate' | 'predict' | 'compare' | 'multi_crack_train';
  protocol?: string;
  bridge?: string;
  params: Record<string, any>;
  metrics?: Record<string, number>;
  note: string;
}

export function useRecord() {
  const [recordState, setRecordState] = useState<RecordState>({ status: 'idle' });

  const addRecord = useCallback(async (request: RecordExperimentRequest) => {
    setRecordState({ status: 'started', message: '记录实验...' });
    try {
      const res = await recordExperiment(request);
      setRecordState({ status: 'completed', recordId: res.record_id, message: res.message });
      // 刷新列表
      await refreshRecords();
    } catch (e) {
      setRecordState({ status: 'failed', error: String(e) });
    }
  }, []);

  const refreshRecords = useCallback(async (limit = 50, offset = 0) => {
    setRecordState(prev => ({ ...prev, loading: true }));
    try {
      const res = await fetchExperimentRecords(limit, offset);
      setRecordState(prev => ({ ...prev, records: res.records, total: res.total, loading: false }));
    } catch (e) {
      setRecordState(prev => ({ ...prev, error: String(e), loading: false }));
    }
  }, []);

  const getRecordsByProtocol = useCallback((protocol: string) => {
    return recordState.records?.filter(r => r.protocol === protocol) || [];
  }, [recordState.records]);

  const getLatestRecord = useCallback((protocol?: string) => {
    const records = protocol ? getRecordsByProtocol(protocol) : recordState.records;
    if (!records || records.length === 0) return null;
    return records[0]; // 已按时间倒序
  }, [recordState.records, getRecordsByProtocol]);

  useEffect(() => {
    refreshRecords();
  }, [refreshRecords]);

  return { recordState, addRecord, refreshRecords, getRecordsByProtocol, getLatestRecord };
}

// ─────────────────────────────────────────────────────────────────────
// 模型对比 Hook
// ─────────────────────────────────────────────────────────────────────

export interface CompareState {
  status: 'idle' | 'started' | 'completed' | 'failed';
  taskId?: string;
  message?: string;
  error?: string;
  result?: CompareModelsResponse;
}

export function useCompare() {
  const [compareState, setCompareState] = useState<CompareState>({ status: 'idle' });

  const compareModelsFn = useCallback(async (request: CompareModelsRequest) => {
    setCompareState({ status: 'started', message: '对比模型...' });
    try {
      const res = await compareModels(request);
      setCompareState({ status: 'completed', result: res, message: '对比完成' });
    } catch (e) {
      setCompareState({ status: 'failed', error: String(e) });
    }
  }, []);

  const compareVersionsFn = useCallback(async (request: { base: string; target: string; dimension: 'all' | 'architecture' | 'loss' | 'trainer' | 'config' }) => {
    setCompareState({ status: 'started', message: '对比版本...' });
    try {
      const res = await compareVersions(request);
      setCompareState({ status: 'completed', message: '对比完成' });
      return res;
    } catch (e) {
      setCompareState({ status: 'failed', error: String(e) });
    }
  }, []);

  const reset = useCallback(() => {
    setCompareState({ status: 'idle' });
  }, []);

  return { compareState, compareModels: compareModelsFn, compareVersions: compareVersionsFn, reset };
}

// ─────────────────────────────────────────────────────────────────────
// 代码库同步 Hook
// ─────────────────────────────────────────────────────────────────────

export interface SyncLibrariesState {
  status: 'idle' | 'started' | 'running' | 'completed' | 'failed';
  pid?: number;
  message?: string;
  error?: string;
}

export function useSyncLibraries() {
  const [syncState, setSyncState] = useState<SyncLibrariesState>({ status: 'idle' });

  const startSync = useCallback(async (request: SyncLibrariesRequest = { full: false }) => {
    setSyncState({ status: 'started' });
    try {
      const res = await triggerSyncLibraries(request);
      setSyncState({ status: 'started', pid: res.pid, message: res.message });
      if (res.pid) pollSyncStatus(res.pid);
    } catch (e) {
      setSyncState({ status: 'failed', error: String(e) });
    }
  }, []);

  const pollSyncStatus = useCallback(async (pid: number) => {
    const check = async () => {
      try {
        const res = await fetchSyncLibrariesStatus(pid);
        if (res.status === 'running') {
          setSyncState(prev => ({ ...prev, status: 'running' }));
          setTimeout(check, 2000);
        } else if (res.status === 'completed') {
          setSyncState({ status: 'completed', message: '同步完成' });
        } else {
          setSyncState({ status: 'failed', error: res.error || '同步失败' });
        }
      } catch {
        setSyncState({ status: 'failed', error: '状态查询失败' });
      }
    };
    check();
  }, []);

  return { syncState, startSync };
}

// Re-export AI Command hooks
export {
  useAICommand,
  useDashboardSync,
  usePipelineMonitor,
  useCommandMeta,
  DataTransformers,
  type UseAICommandState,
  type UseAICommandActions,
  type UseDashboardSyncState,
  type DashboardWidgetData,
} from './useAICommand';

// Re-export AI Command components
export {
  DashboardSync,
  DashboardStatusIndicator,
  WidgetDataBadges,
  useCpdvTimeseries,
  useModelScorecard,
  usePeakAnalysis,
  useCvAnalysis,
  useMultiCrackComparison,
  useErrorDistribution,
  useRoadProfile,
} from '../components/DashboardSync';

export {
  QuickAICommands,
  PipelineStageSelector,
} from '../components/QuickAICommands';

