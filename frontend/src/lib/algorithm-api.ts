/** 算法代码库看板 - API 客户端扩展 */

import type {
  LibrariesResponse,
  PipelineRunRequest,
  PipelineRunResponse,
  PipelineStatusResponse,
  PipelineListResponse,
  TopologyData,
  TopologyQueryParams,
  SymbolSearchResponse,
  SymbolSearchParams,
  ContractsResponse,
  DiffRequest,
  DiffResponse,
  SyncRequest,
  SyncResponse,
  TimelineResponse,
  TrainRequest,
  TrainResponse,
  EvaluateRequest,
  EvaluateResponse,
  RecordExperimentRequest,
  RecordExperimentResponse,
  RecordsListResponse,
  CompareRequest,
  CompareResponse,
  CompareModelsRequest,
  CompareModelsResponse,
  SyncLibrariesRequest,
  SyncLibrariesResponse,
  AICommandRequest,
  AICommandResponse,
  PipelineTaskStatus,
  CommandMeta,
  PipelineRunsResponse,
  PipelineRunRecord,
  ModelComparisonRequest,
  ModelComparisonResult,
  DashboardSyncResult,
  ExperimentDoc,
  ImportExperimentResponse,
  CreateExperimentRequest,
  UpdateMetricsRequest,
  SetExperimentDirRequest,
} from './algorithm-types';

// Re-export types that other modules import from here
export type {
  LibrariesResponse,
  PipelineRunRequest,
  PipelineRunResponse,
  PipelineStatusResponse,
  PipelineListResponse,
  TopologyData,
  TopologyQueryParams,
  SymbolSearchResponse,
  SymbolSearchParams,
  ContractsResponse,
  DiffRequest,
  DiffResponse,
  SyncRequest,
  SyncResponse,
  TimelineResponse,
  TrainRequest,
  TrainResponse,
  EvaluateRequest,
  EvaluateResponse,
  RecordExperimentRequest,
  RecordExperimentResponse,
  RecordsListResponse,
  CompareRequest,
  CompareResponse,
  CompareModelsRequest,
  CompareModelsResponse,
  SyncLibrariesRequest,
  SyncLibrariesResponse,
  AICommandRequest,
  AICommandResponse,
  PipelineTaskStatus,
  CommandMeta,
  PipelineRunsResponse,
  PipelineRunRecord,
  ModelComparisonRequest,
  ModelComparisonResult,
  DashboardSyncResult,
  ExperimentRecord,
  TimelineCommit,
  TimelineExperiment,
  ExperimentDoc,
  ImportExperimentResponse,
  CreateExperimentRequest,
  UpdateMetricsRequest,
  SetExperimentDirRequest,
} from './algorithm-types';

const BASE = '/api/algorithm';

async function getJSON<T>(path: string, params?: Record<string, any>): Promise<T> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null).map(([k, v]) => [k, String(v)])
  ).toString() : '';
  const res = await fetch(`${BASE}${path}${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

/** 获取代码库列表及同步状态 */
export async function fetchAlgorithmLibraries(): Promise<LibrariesResponse> {
  return getJSON<LibrariesResponse>('/libraries');
}

/** 获取拓扑图数据 */
export async function fetchTopology(params: TopologyQueryParams = {}): Promise<TopologyData> {
  return getJSON<TopologyData>('/topology', params);
}

/** 符号搜索 */
export async function searchSymbols(params: SymbolSearchParams): Promise<SymbolSearchResponse> {
  return getJSON<SymbolSearchResponse>('/symbols', params);
}

/** 获取 Protocol 契约详情 */
export async function fetchContract(protocol: string): Promise<ContractsResponse> {
  return getJSON<ContractsResponse>(`/contract/${encodeURIComponent(protocol)}`);
}

/** 版本语义对比 */
export async function diffVersions(request: DiffRequest): Promise<DiffResponse> {
  return postJSON<DiffResponse>('/diff', request);
}

/** 获取时间轴数据 */
export async function fetchTimeline(library?: string, since?: string, until?: string): Promise<TimelineResponse> {
  return getJSON<TimelineResponse>('/timeline', { library, since, until });
}

/** 触发同步 */
export async function triggerSync(request: SyncRequest = { full: false }): Promise<SyncResponse> {
  return postJSON<SyncResponse>('/sync', request);
}

/** 查询同步状态 */
export async function fetchSyncStatus(pid: number): Promise<SyncResponse> {
  return getJSON<SyncResponse>(`/sync/status/${pid}`);
}

/** 获取所有库的元数据（用于导航栏） */
export async function fetchAllLibrariesMeta(): Promise<LibrariesResponse> {
  return fetchAlgorithmLibraries();
}

/** 触发流水线执行 */
export async function triggerPipelineRun(request: PipelineRunRequest): Promise<PipelineRunResponse> {
  return postJSON<PipelineRunResponse>('/pipeline/run', request);
}

/** 查询流水线执行状态 */
export async function fetchPipelineStatus(taskId: string): Promise<PipelineStatusResponse> {
  return getJSON<PipelineStatusResponse>(`/pipeline/status/${taskId}`);
}

/** 列出所有流水线任务 */
export async function fetchPipelines(): Promise<PipelineListResponse> {
  return getJSON<PipelineListResponse>('/pipelines');
}

/** 触发模型训练 */
export async function triggerTrain(request: TrainRequest): Promise<TrainResponse> {
  return postJSON<TrainResponse>('/train', request);
}

/** 查询训练状态（轮询备选） */
export async function fetchTrainStatus(taskId: string): Promise<TrainResponse> {
  return getJSON<TrainResponse>(`/train/status/${taskId}`);
}

// ─────────────────────────────────────────────────────────────────────
// 模型评估
// ─────────────────────────────────────────────────────────────────────

/** 触发模型评估 */
export async function triggerEvaluate(request: EvaluateRequest): Promise<EvaluateResponse> {
  return postJSON<EvaluateResponse>('/evaluate', request);
}

/** 查询评估状态 */
export async function fetchEvaluateStatus(taskId: string): Promise<EvaluateResponse> {
  return getJSON<EvaluateResponse>(`/evaluate/status/${taskId}`);
}

// ─────────────────────────────────────────────────────────────────────
// 实验记录
// ─────────────────────────────────────────────────────────────────────

/** 记录实验 */
export async function recordExperiment(request: RecordExperimentRequest): Promise<RecordExperimentResponse> {
  return postJSON<RecordExperimentResponse>('/record', request);
}

/** 获取实验记录列表 */
export async function fetchExperimentRecords(limit = 50, offset = 0): Promise<RecordsListResponse> {
  const data: any = await getJSON<any>('/records', { limit, offset });
  // 后端 /records 返回 { total, filter, items: [...] }，item 字段为
  // { bridge_id, action, params, result, note?, timestamp }（无 id/type/metrics）。
  // 前端 RecordsListResponse 期望 { records: ExperimentRecord[], total }，记录字段为
  // { id, timestamp, type, protocol?, bridge?, params, metrics?, note, name? }。
  // 这里在 API 层做一次性归一化，作为 ExperimentRecordPanel 与 useAlgorithmDashboard
  // 两个消费方的唯一来源，避免 res.records 为 undefined 导致 records[0] 崩溃。
  const rawItems: any[] = data?.items ?? data?.records ?? [];
  const records: any[] = rawItems.map((it: any, i: number) => ({
    id: it.id ?? `${it.params?.experiment_id ?? it.action ?? 'record'}-${i}`,
    timestamp: it.timestamp ?? '',
    type: it.type ?? it.params?.template ?? it.action ?? 'train',
    protocol: it.protocol,
    bridge: it.bridge ?? it.bridge_id,
    params: it.params ?? {},
    metrics: it.result ?? it.metrics ?? {},
    note: it.note ?? '',
    name: it.params?.name,
  }));
  return { records, total: data?.total ?? records.length };
}

// ─────────────────────────────────────────────────────────────────────
// 模型对比
// ─────────────────────────────────────────────────────────────────────

/** 对比两个版本/协议 (架构/损失/训练器/配置) */
export async function compareVersions(request: CompareRequest): Promise<CompareResponse> {
  return postJSON<CompareResponse>('/diff', request);
}

/** 对比两个模型的指标 */
export async function compareModels(request: CompareModelsRequest): Promise<CompareModelsResponse> {
  return postJSON<CompareModelsResponse>('/compare', request);
}

// ─────────────────────────────────────────────────────────────────────
// 同步代码库
// ─────────────────────────────────────────────────────────────────────

/** 触发代码库同步 */
export async function triggerSyncLibraries(request: SyncLibrariesRequest = { full: false }): Promise<SyncLibrariesResponse> {
  return postJSON<SyncLibrariesResponse>('/sync', request);
}

/** 查询同步状态 */
export async function fetchSyncLibrariesStatus(pid: number): Promise<SyncLibrariesResponse> {
  return getJSON<SyncLibrariesResponse>(`/sync/status/${pid}`);
}

// ─────────────────────────────────────────────────────────────────────
// Pipeline 运行记录
// ─────────────────────────────────────────────────────────────────────

/** 获取 Pipeline 运行历史 */
export async function fetchPipelineRuns(limit = 50, offset = 0): Promise<PipelineRunsResponse> {
  return getJSON<PipelineRunsResponse>('/pipeline-runs', { limit, offset });
}

/** 获取单个 Pipeline 运行详情 */
export async function fetchPipelineRun(runId: string): Promise<PipelineRunRecord> {
  return getJSON<PipelineRunRecord>(`/pipeline-runs/${runId}`);
}

// ─────────────────────────────────────────────────────────────────────
// 模型对比
// ─────────────────────────────────────────────────────────────────────

/** 对比两个模型 */
export async function compareModelsApi(request: ModelComparisonRequest): Promise<ModelComparisonResult> {
  return postJSON<ModelComparisonResult>('/compare-models', request);
}

// ─────────────────────────────────────────────────────────────────────
// AI Command System
// ─────────────────────────────────────────────────────────────────────

const AI_API_BASE = '/api/ai';

async function aiFetch(endpoint: string, body: AICommandRequest): Promise<AICommandResponse> {
  const res = await fetch(`${AI_API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

/** 执行 AI 命令 */
export async function executeAICommand(request: AICommandRequest): Promise<AICommandResponse> {
  return aiFetch('/command', request);
}

/** 获取 AI 命令元数据（用于动态生成 UI） */
export async function fetchAICommandMeta(): Promise<CommandMeta> {
  const res = await fetch(`${AI_API_BASE}/commands/meta`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

/** 同步看板数据 */
export async function syncDashboard(widgets: string[] = [
  'cpdv_timeseries', 'model_scorecard', 'peak_vs_position', 'cv_analysis'
], forceRefresh = false): Promise<DashboardSyncResult> {
  const response = await executeAICommand({
    jsonrpc: '2.0',
    id: `sync_${Date.now()}`,
    method: 'dashboard.sync',
    params: { widgets, force_refresh: forceRefresh },
  });
  if (response.error) throw new Error(response.error.message);
  return response.result as DashboardSyncResult;
}

/** 查询数据产物 */
export async function queryDataArtifact(
  artifact: string, 
  filters: Record<string, any> = {},
  limit = 100,
  offset = 0
): Promise<{ data: any; meta: any }> {
  const response = await executeAICommand({
    jsonrpc: '2.0',
    id: `query_${Date.now()}`,
    method: 'data.query',
    params: { artifact, filters, limit, offset },
  });
  if (response.error) throw new Error(response.error.message);
  return response.result as { data: any; meta: any };
}

/** 执行分析 */
export async function runAnalysis(
  type: string, 
  params: Record<string, any> = {}
): Promise<{ result: any; charts: string[]; interpretation: string | null }> {
  const response = await executeAICommand({
    jsonrpc: '2.0',
    id: `analysis_${Date.now()}`,
    method: 'analysis.run',
    params: { type, params },
  });
  if (response.error) throw new Error(response.error.message);
  return response.result as { result: any; charts: string[]; interpretation: string | null };
}

/** AI 解读分析结果 */
export async function interpretAnalysis(
  artifact: string,
  question: string
): Promise<{ interpretation: string; recommendations: string[]; confidence: number }> {
  const response = await executeAICommand({
    jsonrpc: '2.0',
    id: `interpret_${Date.now()}`,
    method: 'analysis.interpret',
    params: { artifact, question },
  });
  if (response.error) throw new Error(response.error.message);
  return response.result as { interpretation: string; recommendations: string[]; confidence: number };
}

/** 对比模型 */
export async function compareModelsAI(
  models: string[],
  metrics: string[] = ['f1', 'mae_pos', 'mae_depth'],
  scenarios?: string[]
): Promise<{ comparison: any; winner: string; summary: string }> {
  const response = await executeAICommand({
    jsonrpc: '2.0',
    id: `compare_${Date.now()}`,
    method: 'analysis.compare',
    params: { models, metrics, scenarios },
  });
  if (response.error) throw new Error(response.error.message);
  return response.result as { comparison: any; winner: string; summary: string };
}

/** 执行 Pipeline */
export async function executePipeline(
  pipelines: string[],
  mode: 'quick' | 'full' = 'quick',
  stages?: string[],
  asyncMode = true
): Promise<{ task_id: string; status: string; message: string }> {
  const response = await executeAICommand({
    jsonrpc: '2.0',
    id: `pipeline_${Date.now()}`,
    method: 'pipeline.execute',
    params: { pipelines, mode, stages, async: asyncMode },
  });
  if (response.error) throw new Error(response.error.message);
  return response.result as { task_id: string; status: string; message: string };
}

/** 查询 Pipeline 状态 */
export async function fetchPipelineTaskStatus(taskId: string): Promise<PipelineTaskStatus> {
  const response = await executeAICommand({
    jsonrpc: '2.0',
    id: `status_${Date.now()}`,
    method: 'pipeline.status',
    params: { task_id: taskId },
  });
  if (response.error) throw new Error(response.error.message);
  return response.result as PipelineTaskStatus;
}

// ─────────────────────────────────────────────────────────────────────
// 实验记录管理（Obsidian集成）
// ─────────────────────────────────────────────────────────────────────

/** 扫描实验文档目录 */
export async function scanExperimentDocs(experimentDir?: string): Promise<ExperimentDoc[]> {
  const params = new URLSearchParams();
  if (experimentDir) params.set('experiment_dir', experimentDir);
  const qs = params.toString() ? `?${params}` : '';
  const res = await fetch(`${BASE}/experiment/docs${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return data.experiments || [];
}

/** 导入实验文档到records */
export async function importExperimentDocs(experimentDir?: string): Promise<ImportExperimentResponse> {
  const params = new URLSearchParams();
  if (experimentDir) params.set('experiment_dir', experimentDir);
  const qs = params.toString() ? `?${params}` : '';
  const res = await fetch(`${BASE}/experiment/import${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

/** 创建新实验 */
export async function createExperiment(request: CreateExperimentRequest): Promise<any> {
  return postJSON(`${BASE}/experiment/create`, request);
}

/** 更新实验指标 */
export async function updateExperimentMetrics(request: UpdateMetricsRequest): Promise<any> {
  return postJSON(`${BASE}/experiment/metrics`, request);
}

/** 设置实验文档目录 */
export async function setExperimentDir(request: SetExperimentDirRequest): Promise<{ experiment_dir: string }> {
  return postJSON(`${BASE}/experiment/dir`, request);
}

