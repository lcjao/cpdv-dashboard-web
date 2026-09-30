/** 算法代码库看板 - 类型定义 */

// ─────────────────────────────────────────────────────────────────────
// 工具函数
// ─────────────────────────────────────────────────────────────────────

export function genId(prefix = 'id'): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 9)}`;
}

// ─────────────────────────────────────────────────────────────────────
// 代码库与拓扑图
// ─────────────────────────────────────────────────────────────────────

export interface AlgorithmLibrary {
  id: string;
  name: string;
  path: string;
  file_count: number;
  last_sync: number;
  status: 'ok' | 'no_data' | 'syncing';
}

export interface TopologyNode {
  id: string;              // qualified_name
  label: string;           // 短名称
  type: 'class' | 'function' | 'method' | 'protocol' | 'variable' | 'import';
  module: string;          // 所属库/模块
  file: string;            // 文件路径
  line: number;            // 行号
  docstring?: string;      // 文档字符串
  metadata?: Record<string, any>;  // 扩展信息
}

export interface TopologyEdge {
  source: string;          // 源节点 qualified_name
  target: string;          // 目标节点 qualified_name
  type: 'calls' | 'inherits' | 'implements' | 'imports' | 'decorates' | 'returns' | 'uses_type';
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  focus_node?: string;
  depth: number;
}

export interface TopologyQueryParams {
  library?: string;
  focus_node?: string;
  depth?: number;  // 1-5
}

// ─────────────────────────────────────────────────────────────────────
// 符号搜索
// ─────────────────────────────────────────────────────────────────────

export interface SymbolSearchResult {
  q: string;               // qualified_name
  n: string;               // name (短名称)
  t: 'class' | 'function' | 'method' | 'protocol' | 'variable' | 'import';
  m: string;               // module (github, algorithm, backend_framework, backends)
  f: string;               // file path
  l: number;               // line number
}

export interface SymbolSearchResponse {
  symbols: SymbolSearchResult[];
  total: number;
  limit: number;
}

export interface SymbolSearchParams {
  q: string;
  type?: string;
  library?: string;
  limit?: number;
}

// ─────────────────────────────────────────────────────────────────────
// Protocol 契约
// ─────────────────────────────────────────────────────────────────────

export interface ContractMethod {
  name: string;
  parameters: Array<{
    name: string;
    type: string;
    default?: any;
    required: boolean;
  }>;
  return_type: string | null;
  is_async: boolean;
  is_classmethod: boolean;
  is_staticmethod: boolean;
  is_property: boolean;
  docstring?: string;
}

export interface ContractAttribute {
  name: string;
  type: string;
  required: boolean;
  docstring?: string;
}

export interface ContractImplementation {
  backend_name: string;
  component_type: string;
  registered_name: string;
  class_name: string;
  qualified_name: string;
  file_path: string;
  protocol: string;
  config_schema: Record<string, any>;
  metadata: Record<string, any>;
  compliance?: {
    score: number;
    fully_compliant: boolean;
    missing_attrs: number;
    missing_methods: number;
  };
}

export interface ContractDetail {
  name: string;
  qualified_name: string;
  file_path: string;
  docstring?: string;
  required_attributes: ContractAttribute[];
  required_methods: ContractMethod[];
  optional_methods: ContractMethod[];
  implementations: ContractImplementation[];
  summary: {
    total_implementations: number;
    fully_compliant: number;
    avg_score: number;
  };
}

export interface ContractsResponse {
  protocol: ContractDetail;
  implementations: ContractImplementation[];
  summary: {
    total_implementations: number;
    fully_compliant: number;
    avg_score: number;
  };
}

// ─────────────────────────────────────────────────────────────────────
// 版本对比
// ─────────────────────────────────────────────────────────────────────

export interface DiffRequest {
  base: string;
  target: string;
  dimension: 'all' | 'architecture' | 'loss' | 'trainer' | 'config';
}

export interface ComponentConfigDiff {
  only_in_base: string[];
  only_in_target: string[];
  common: string[];
  config_diff: Record<string, any>;
}

export interface DiffResponse {
  base: string;
  target: string;
  dimension: string;
  diff: Record<string, ComponentConfigDiff>;
}

// ─────────────────────────────────────────────────────────────────────
// 时间轴
// ─────────────────────────────────────────────────────────────────────

export interface TimelineCommit {
  hash: string;
  short_hash: string;
  message: string;
  author: string;
  date: string;           // ISO 8601
  files_changed: number;
  lines_added: number;
  lines_deleted: number;
  is_tag: boolean;
  tag_name?: string;
}

export interface TimelineHeatmap {
  [date: string]: number;  // date -> commit count
}

export interface TimelineExperiment {
  id: string;
  name: string;
  variant: string;
  date: string;
  metrics: Record<string, number>;
  params?: Record<string, any>;
}

export interface TimelineResponse {
  commits: TimelineCommit[];
  heatmap: TimelineHeatmap;
  tags: Array<{ name: string; date: string; commit: string }>;
  experiments: TimelineExperiment[];
}

// ─────────────────────────────────────────────────────────────────────
// 同步触发
// ─────────────────────────────────────────────────────────────────────

export interface SyncRequest {
  full: boolean;
  only?: string[];
}

export interface SyncResponse {
  status: 'started' | 'running' | 'completed' | 'failed';
  pid?: number;
  message?: string;
  error?: string;
}

// ─────────────────────────────────────────────────────────────────────
// 代码库列表
// ─────────────────────────────────────────────────────────────────────

export interface LibrariesResponse {
  libraries: AlgorithmLibrary[];
  last_sync: number;
  status: 'ok' | 'no_data' | 'syncing';
}

// ─────────────────────────────────────────────────────────────────────
// 导航/视图模式
// ─────────────────────────────────────────────────────────────────────

export type ViewMode = 'topology' | 'list' | 'compare';

export interface NavigatorState {
  currentLibrary: string;
  viewMode: ViewMode;
  searchQuery: string;
  showSearch: boolean;
}

export interface ModuleTreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  module: string;
  children?: ModuleTreeNode[];
  expanded?: boolean;
  symbolCount?: number;
  hasProtocol?: boolean;
  file?: string;
}

// ─────────────────────────────────────────────────────────────────────
// 模型训练
// ─────────────────────────────────────────────────────────────────────

export interface TrainRequest {
  model_type: string;
  n_samples: number;
  data?: string;
  model?: string;
  epochs: number;
  phase1_epochs?: number;
  phase2_epochs?: number;
  regenerate: boolean;
  bridge?: string;
}

export interface TrainResponse {
  status: 'started' | 'running' | 'completed' | 'failed';
  task_id?: string;
  message?: string;
  model_path?: string;
  metrics?: Record<string, number>;
  error?: string;
}

export interface TrainProgressEvent {
  tag: 'train';
  stage: 'data_gen' | 'phase1' | 'phase2' | 'phase3' | 'eval' | 'save' | 'done' | 'error';
  message: string;
  percent: number;
  meta?: {
    bridge_id?: string;
    model_type?: string;
    epoch?: number;
    total_epochs?: number;
    loss?: number;
  };
}

// ─────────────────────────────────────────────────────────────────────
// 模型评估
// ─────────────────────────────────────────────────────────────────────

export interface EvaluateRequest {
  model: string;
  input_data?: string;
  cls_threshold?: number;
  match_cost?: number;
  pos_threshold?: number;
}

export interface EvaluateResponse {
  status: 'started' | 'running' | 'completed' | 'failed';
  task_id?: string;
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
  error?: string;
}

// ─────────────────────────────────────────────────────────────────────
// 实验记录
// ─────────────────────────────────────────────────────────────────────

export interface ExperimentRecord {
  id: string;
  timestamp: string;
  type: 'train' | 'evaluate' | 'predict' | 'compare' | 'multi_crack_train';
  protocol?: string;
  bridge?: string;
  params: Record<string, any>;
  metrics?: Record<string, number>;
  note: string;
  name?: string;
}

export interface RecordExperimentRequest {
  note: string;
  type?: string;
  protocol?: string;
  bridge?: string;
  params?: Record<string, any>;
  metrics?: Record<string, number>;
}

export interface RecordExperimentResponse {
  record_id: string;
  message: string;
}

export interface RecordsListResponse {
  records: ExperimentRecord[];
  total: number;
}

// ─────────────────────────────────────────────────────────────────────
// 模型对比
// ─────────────────────────────────────────────────────────────────────

export interface CompareRequest {
  base: string;
  target: string;
  dimension: 'all' | 'architecture' | 'loss' | 'trainer' | 'config';
  bridge_a?: string;
  bridge_b?: string;
}

export interface CompareResponse {
  base: string;
  target: string;
  dimension: string;
  diff: Record<string, any>;
  summary?: string;
}

export interface CompareModelsRequest {
  model_a: string;
  model_b: string;
  bridge_a?: string;
  bridge_b?: string;
}

export interface CompareModelsResponse {
  model_a: {
    path: string;
    metrics: Record<string, number>;
  };
  model_b: {
    path: string;
    metrics: Record<string, number>;
  };
  comparison: {
    f1_diff: number;
    precision_diff: number;
    recall_diff: number;
    position_mae_diff: number;
    depth_mae_diff: number;
    winner: 'a' | 'b' | 'tie';
  };
}

// ─────────────────────────────────────────────────────────────────────
// 同步代码库
// ─────────────────────────────────────────────────────────────────────

export interface SyncLibrariesRequest {
  full: boolean;
  only?: string[];
}

export interface SyncLibrariesResponse {
  status: 'started' | 'running' | 'completed' | 'failed';
  pid?: number;
  message?: string;
  error?: string;
}

// ─────────────────────────────────────────────────────────────────────
// Pipeline 运行记录
// ─────────────────────────────────────────────────────────────────────

export interface PipelineStage {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  progress?: number;
  logs?: string[];
  meta?: Record<string, any>;
}



// Pipeline 完整规格（含stages）
export interface PipelineSpec {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  depends_on: string[];
  stages: PipelineStage[];
}
export interface PipelineRunRecord {
  id: string;
  name: string;
  description?: string;
  status: 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  durationMs?: number;
  stages: PipelineStage[];
  metrics?: Record<string, number>;
  error?: string;
  config?: Record<string, any>;
}

export interface PipelineRunsResponse {
  runs: PipelineRunRecord[];
  total: number;
}

// ─────────────────────────────────────────────────────────────────────
// 模型对比
// ─────────────────────────────────────────────────────────────────────

export interface ModelComparisonRequest {
  modelA: string;
  modelB: string;
  bridgeA?: string;
  bridgeB?: string;
}

export interface ModelComparisonResult {
  modelA: {
    path: string;
    metrics: Record<string, number>;
    config: Record<string, any>;
  };
  modelB: {
    path: string;
    metrics: Record<string, number>;
    config: Record<string, any>;
  };
  comparison: {
    f1_diff: number;
    precision_diff: number;
    recall_diff: number;
    position_mae_diff: number;
    depth_mae_diff: number;
    winner: 'a' | 'b' | 'tie';
    summary: string;
  };
}

export interface PipelineProgressEvent {
  tag: 'pipeline';
  stage: string;
  message: string;
  percent?: number;
  [k: string]: unknown;
}

export interface PipelineRunResult {
  config: Record<string, any>;
  components: Record<string, string>;
  metrics: Record<string, any>;
  duration_s: number;
}

export interface PipelineRunRequest {
  name: string;
  description?: string;
  nodes: any[];
  connections: any[];
}

export interface PipelineRunResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface PipelineStatusResponse {
  task_id: string;
  name: string;
  status: string;
  progress: Record<string, any>;
  result: Record<string, any> | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_s: number | null;
}

export interface PipelineListResponse {
  pipelines: Array<{
    task_id: string;
    name: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    error: string | null;
  }>;
  total: number;
}



// ─────────────────────────────────────────────────────────────────────
// 可视化流水线构建器
// ─────────────────────────────────────────────────────────────────────

export type PipelineStageType = 'data_generation' | 'training' | 'inference' | 'evaluation' | 'preprocessing' | 'postprocessing';

export interface PipelineNodePort {
  id: string;
  name: string;
  type: 'input' | 'output';
  dataType: string;  // e.g., 'np.ndarray', 'DataLoader', 'Model', 'Dict', 'Config'
  required: boolean;
  description?: string;
}

export interface PipelineNodeConfig {
  [key: string]: any;  // 可序列化的配置参数
}

export interface PipelineNodeImpl {
  id: string;
  name: string;
  description: string;
  qualified_name: string;
  file_path: string;
  module: string;
  config_schema: Record<string, any>;
  default_config: PipelineNodeConfig;
  compliance_score?: number;
  protocol?: string;
}

export interface PipelineNode {
  id: string;                    // 唯一实例 ID
  template_id: string;           // 引用模板节点 ID
  type: PipelineStageType;
  name: string;
  label: string;                 // 显示名称
  description: string;
  position: { x: number; y: number };
  
  // 输入输出端口
  inputs: PipelineNodePort[];
  outputs: PipelineNodePort[];
  
  // 当前选中的实现
  selected_impl: PipelineNodeImpl | null;
  // 可选的替代实现列表
  alternative_impls: PipelineNodeImpl[];
  
  // 运行时配置（用户可修改）
  config: PipelineNodeConfig;
  
  // 元数据
  metadata: {
    category: PipelineNodeCategory;  // e.g., 'data_loader', 'model', 'loss', 'trainer', 'evaluator'
    is_required: boolean;        // 是否为必选节点
    order: number;               // 在阶段内的执行顺序
    tags: string[];
  };
}

export interface PipelineConnection {
  id: string;
  source: { node_id: string; port_id: string };
  target: { node_id: string; port_id: string };
}

export interface PipelineTemplate {
  id: string;
  name: string;
  description: string;
  category: PipelineStageType;
  version: string;
  nodes: Omit<PipelineNode, 'id' | 'position' | 'selected_impl' | 'config' | 'alternative_impls'>[];
  connections: Omit<PipelineConnection, 'id'>[];
  metadata: {
    author: string;
    created_at: string;
    tags: string[];
    estimated_time: string;
    difficulty: 'beginner' | 'intermediate' | 'advanced';
  };
}

export interface PipelineInstance {
  id: string;
  name: string;
  description: string;
  template_ids: string[];        // 组合的模板 ID
  nodes: PipelineNode[];
  connections: PipelineConnection[];
  created_at: string;
  updated_at: string;
  metadata: {
    version: string;
    author: string;
    tags: string[];
    is_valid: boolean;
    validation_errors: string[];
  };
}

// 节点分类配置
export const PIPELINE_NODE_CATEGORIES: Record<string, { label: string; color: string; icon: string }> & {
  readonly data_loader: { readonly label: '数据加载器'; readonly color: '#3B82F6'; readonly icon: '📥' };
  readonly model: { readonly label: '模型'; readonly color: '#8B5CF6'; readonly icon: '🧠' };
  readonly loss: { readonly label: '损失函数'; readonly color: '#EC4899'; readonly icon: '📉' };
  readonly optimizer: { readonly label: '优化器'; readonly color: '#F59E0B'; readonly icon: '⚙️' };
  readonly trainer: { readonly label: '训练器'; readonly color: '#10B981'; readonly icon: '🏋️' };
  readonly evaluator: { readonly label: '评估器'; readonly color: '#EF4444'; readonly icon: '📊' };
  readonly preprocessor: { readonly label: '预处理'; readonly color: '#06B6D4'; readonly icon: '🔧' };
  readonly postprocessor: { readonly label: '后处理'; readonly color: '#84CC16'; readonly icon: '✨' };
  readonly data_generator: { readonly label: '数据生成'; readonly color: '#6366F1'; readonly icon: '🎲' };
} = {
  data_loader: { label: '数据加载器', color: '#3B82F6', icon: '📥' },
  model: { label: '模型', color: '#8B5CF6', icon: '🧠' },
  loss: { label: '损失函数', color: '#EC4899', icon: '📉' },
  optimizer: { label: '优化器', color: '#F59E0B', icon: '⚙️' },
  trainer: { label: '训练器', color: '#10B981', icon: '🏋️' },
  evaluator: { label: '评估器', color: '#EF4444', icon: '📊' },
  preprocessor: { label: '预处理', color: '#06B6D4', icon: '🔧' },
  postprocessor: { label: '后处理', color: '#84CC16', icon: '✨' },
  data_generator: { label: '数据生成', color: '#6366F1', icon: '🎲' },
};

export type PipelineNodeCategory = keyof typeof PIPELINE_NODE_CATEGORIES;

// ─────────────────────────────────────────────────────────────────────
// AI Command System Types
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
// Pipeline 流程可视化
// ─────────────────────────────────────────────────────────────────────

export type PipelineFlowStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface PipelineFlowState {
  id: string;
  name: string;
  status: PipelineFlowStatus;
  progress: number; // 0-100
  startTime?: string;
  duration?: string;
  outputs?: string[];
  error?: string | null;
  currentStage?: string;
  pipelineIndex: number; // 1-6 对应pipeline_1到pipeline_6
  spec?: PipelineSpec;  // 完整规格信息
}

export interface PipelineFlowEvent {
  type: 'pipeline_started' | 'pipeline_progress' | 'pipeline_completed' | 'pipeline_failed';
  pipelineId: string;
  data: {
    status: PipelineFlowStatus;
    progress?: number;
    message?: string;
    outputs?: string[];
    error?: string | null;
  };
}

export interface PipelineFlowVisualizationProps {
  onBack?: () => void;
  onRefresh?: () => void;
}

// ─────────────────────────────────────────────────────────────────────
// 实验记录管理（Obsidian集成）
// ─────────────────────────────────────────────────────────────────────

export interface ExperimentDoc {
  id: string;                // EXP-001 等
  name: string;
  date: string;
  purpose: string;
  related_docs: string[];
  metrics: Record<string, number>;
  file_path: string;         // 绝对路径
  relative_path: string;     // 相对Obsidian vault的路径
  content_preview: string;
  word_count: number;
}

export interface ExperimentRecordExtended extends ExperimentRecord {
  experiment_id?: string;    // Obsidian实验编号
  experiment_doc?: ExperimentDoc;
  experiment_dir?: string;   // 当前实验文档目录
}

export interface ExperimentListResponse {
  experiments: ExperimentDoc[];
  total: number;
  experiment_dir: string;
}

export interface ImportExperimentResponse {
  total: number;
  imported: number;
  experiments: ExperimentDoc[];
  imported_records: Array<{
    experiment_id: string;
    record_id: string;
    message: string;
  }>;
}

export interface CreateExperimentRequest {
  name: string;
  purpose?: string;
  experiment_dir?: string;
  template?: 'basic' | 'train' | 'evaluate';
}

export interface UpdateMetricsRequest {
  experiment_id: string;
  metrics: Record<string, number>;
  note?: string;
  experiment_dir?: string;
}

export interface SetExperimentDirRequest {
  experiment_dir: string;
}

