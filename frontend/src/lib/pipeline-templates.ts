/** 预定义流水线模板数据 */

import type {
  PipelineTemplate,
  PipelineNode,
  PipelineNodeImpl,
  PipelineNodePort,
  PipelineConnection,
} from './algorithm-types';

// 辅助函数：创建端口
const createPort = (id: string, name: string, type: 'input' | 'output', dataType: string, required = true, description = ''): PipelineNodePort => ({
  id, name, type, dataType, required, description,
});

// 辅助函数：创建实现
const createImpl = (
  id: string,
  name: string,
  description: string,
  qualified_name: string,
  file_path: string,
  module: string,
  config_schema: Record<string, any>,
  default_config: Record<string, any>,
  compliance_score = 1.0,
  protocol?: string
): PipelineNodeImpl => ({
  id,
  name,
  description,
  qualified_name,
  file_path,
  module,
  config_schema,
  default_config,
  compliance_score,
  protocol,
});

// ─────────────────────────────────────────────────────────────────────
// 预定义实现库（基于后端扫描的契约实现）
// ─────────────────────────────────────────────────────────────────────

const DATA_LOADER_IMPLS: PipelineNodeImpl[] = [
  createImpl(
    'legacy_data_loader',
    'LegacyDataLoader',
    '原始桥梁数据加载器，支持单/多裂缝数据生成',
    'backend_framework.adapters.legacy_data_loader.LegacyDataLoader',
    'backend_framework/adapters/legacy_data_loader.py',
    'backend_framework',
    {
      data_dir: { type: 'string', default: 'data/processed' },
      bridge_id: { type: 'string', default: 'bridge_01' },
      batch_size: { type: 'integer', default: 32 },
      train_ratio: { type: 'number', default: 0.7 },
      val_ratio: { type: 'number', default: 0.15 },
      normalize: { type: 'boolean', default: true },
    },
    { data_dir: 'data/processed', bridge_id: 'bridge_01', batch_size: 32, train_ratio: 0.7, val_ratio: 0.15, normalize: true },
    1.0,
    'backend_framework.protocols.data_loader.DataLoaderProtocol'
  ),
];

const MODEL_IMPLS: PipelineNodeImpl[] = [
  createImpl(
    'legacy_model',
    'LegacyModel (单头)',
    '基础多裂缝预测模型，仅回归输出位置和深度',
    'backend_framework.adapters.legacy_model.LegacyModel',
    'backend_framework/adapters/legacy_model.py',
    'backend_framework',
    {
      input_dim: { type: 'integer', default: 100 },
      hidden_dim: { type: 'integer', default: 256 },
      num_layers: { type: 'integer', default: 4 },
      max_cracks: { type: 'integer', default: 5 },
      dropout: { type: 'number', default: 0.1 },
    },
    { input_dim: 100, hidden_dim: 256, num_layers: 4, max_cracks: 5, dropout: 0.1 },
    1.0,
    'backend_framework.protocols.model.ModelProtocol'
  ),
  createImpl(
    'legacy_dual_head_model',
    'LegacyDualHeadModel (双头)',
    '分类+回归双头模型，支持裂缝存在性分类',
    'backend_framework.adapters.legacy_model.LegacyDualHeadModel',
    'backend_framework/adapters/legacy_model.py',
    'backend_framework',
    {
      input_dim: { type: 'integer', default: 100 },
      hidden_dim: { type: 'integer', default: 256 },
      num_layers: { type: 'integer', default: 4 },
      max_cracks: { type: 'integer', default: 5 },
      dropout: { type: 'number', default: 0.1 },
    },
    { input_dim: 100, hidden_dim: 256, num_layers: 4, max_cracks: 5, dropout: 0.1 },
    1.0,
    'backend_framework.protocols.model.ModelProtocol'
  ),
];

const LOSS_IMPLS: PipelineNodeImpl[] = [
  createImpl(
    'legacy_weighted_loss',
    'LegacyWeightedLoss',
    '加权回归损失，位置权重 + 深度权重',
    'backend_framework.adapters.legacy_loss.LegacyWeightedLoss',
    'backend_framework/adapters/legacy_loss.py',
    'backend_framework',
    {
      pos_weight: { type: 'number', default: 1.0 },
      depth_weight: { type: 'number', default: 1.0 },
      miss_weight: { type: 'number', default: 0.5 },
    },
    { pos_weight: 1.0, depth_weight: 1.0, miss_weight: 0.5 },
    1.0,
    'backend_framework.protocols.loss.LossProtocol'
  ),
  createImpl(
    'legacy_dual_head_loss',
    'LegacyDualHeadLoss',
    '双头损失：分类交叉熵 + 回归加权损失',
    'backend_framework.adapters.legacy_loss.LegacyDualHeadLoss',
    'backend_framework/adapters/legacy_loss.py',
    'backend_framework',
    {
      cls_weight: { type: 'number', default: 1.0 },
      reg_weight: { type: 'number', default: 1.0 },
      pos_weight: { type: 'number', default: 1.0 },
      depth_weight: { type: 'number', default: 1.0 },
    },
    { cls_weight: 1.0, reg_weight: 1.0, pos_weight: 1.0, depth_weight: 1.0 },
    1.0,
    'backend_framework.protocols.loss.LossProtocol'
  ),
];

const OPTIMIZER_IMPLS: PipelineNodeImpl[] = [
  createImpl(
    'legacy_adamw',
    'LegacyAdamW',
    'AdamW 优化器，权重衰减',
    'backend_framework.adapters.legacy_optimizer.LegacyAdamW',
    'backend_framework/adapters/legacy_optimizer.py',
    'backend_framework',
    {
      lr: { type: 'number', default: 1e-3 },
      weight_decay: { type: 'number', default: 1e-4 },
      betas: { type: 'array', default: [0.9, 0.999] },
      eps: { type: 'number', default: 1e-8 },
    },
    { lr: 1e-3, weight_decay: 1e-4, betas: [0.9, 0.999], eps: 1e-8 },
    1.0,
    'backend_framework.protocols.optimizer.OptimizerProtocol'
  ),
  createImpl(
    'legacy_adam',
    'LegacyAdam',
    'Adam 优化器',
    'backend_framework.adapters.legacy_optimizer.LegacyAdam',
    'backend_framework/adapters/legacy_optimizer.py',
    'backend_framework',
    {
      lr: { type: 'number', default: 1e-3 },
      betas: { type: 'array', default: [0.9, 0.999] },
      eps: { type: 'number', default: 1e-8 },
    },
    { lr: 1e-3, betas: [0.9, 0.999], eps: 1e-8 },
    1.0,
    'backend_framework.protocols.optimizer.OptimizerProtocol'
  ),
];

const TRAINER_IMPLS: PipelineNodeImpl[] = [
  createImpl(
    'legacy_three_phase_trainer',
    'LegacyThreePhaseTrainer',
    '三阶段训练：冻结backbone → 部分解冻 → 全网微调',
    'backend_framework.adapters.legacy_trainer.LegacyThreePhaseTrainer',
    'backend_framework/adapters/legacy_trainer.py',
    'backend_framework',
    {
      max_epochs: { type: 'integer', default: 100 },
      phase1_epochs: { type: 'integer', default: 30 },
      phase2_epochs: { type: 'integer', default: 30 },
      phase3_epochs: { type: 'integer', default: 40 },
      early_stopping_patience: { type: 'integer', default: 15 },
      gradient_accumulation_steps: { type: 'integer', default: 1 },
      clip_grad: { type: 'number', default: 1.0 },
      lr_finetune: { type: 'number', default: 1e-4 },
      device: { type: 'string', default: 'auto' },
      save_dir: { type: 'string', default: 'outputs/models' },
      seed: { type: 'integer', default: 42 },
    },
    { max_epochs: 100, phase1_epochs: 30, phase2_epochs: 30, phase3_epochs: 40, early_stopping_patience: 15, gradient_accumulation_steps: 1, clip_grad: 1.0, lr_finetune: 1e-4, device: 'auto', save_dir: 'outputs/models', seed: 42 },
    1.0,
    'backend_framework.protocols.trainer.TrainerProtocol'
  ),
];

const EVALUATOR_IMPLS: PipelineNodeImpl[] = [
  createImpl(
    'legacy_hungarian_evaluator',
    'LegacyHungarianEvaluator',
    '匈牙利算法匹配 + 多指标评估',
    'backend_framework.adapters.legacy_evaluator.LegacyHungarianEvaluator',
    'backend_framework/adapters/legacy_evaluator.py',
    'backend_framework',
    {
      cls_threshold: { type: 'number', default: 0.3 },
      pos_threshold: { type: 'number', default: 0.0 },
      match_cost: { type: 'number', default: 5.0 },
      device: { type: 'string', default: 'auto' },
      save_details: { type: 'boolean', default: false },
    },
    { cls_threshold: 0.3, pos_threshold: 0.0, match_cost: 5.0, device: 'auto', save_details: false },
    1.0,
    'backend_framework.protocols.evaluator.EvaluatorProtocol'
  ),
];

// ─────────────────────────────────────────────────────────────────────
// 模板节点定义
// ─────────────────────────────────────────────────────────────────────

// 数据生成阶段节点
const DATA_GEN_NODES: Omit<PipelineNode, 'id' | 'position' | 'selected_impl' | 'config' | 'alternative_impls'>[] = [
  {
    template_id: 'data_generator',
    type: 'data_generation',
    name: 'DataGenerator',
    label: '数据生成器',
    description: '生成合成桥梁振动信号和裂缝标签',
    inputs: [],
    outputs: [
      createPort('signals_out', 'signals', 'output', 'np.ndarray', false, '生成的振动信号 (n_samples, n_channels, seq_len)'),
      createPort('labels_out', 'labels', 'output', 'np.ndarray', false, '裂缝标签 (n_samples, max_cracks*2)'),
      createPort('config_out', 'config', 'output', 'Dict', false, '生成配置参数'),
    ],
    metadata: { category: 'data_generator', is_required: true, order: 0, tags: ['synthetic', 'bridge'] },
  },
  {
    template_id: 'data_loader',
    type: 'data_generation',
    name: 'DataLoader',
    label: '数据加载器',
    description: '加载并预处理训练/验证/测试数据',
    inputs: [
      createPort('data_path', 'data_path', 'input', 'str', true, '数据文件路径'),
    ],
    outputs: [
      createPort('train_loader', 'train_loader', 'output', 'DataLoader', true, '训练集 DataLoader'),
      createPort('val_loader', 'val_loader', 'output', 'DataLoader', true, '验证集 DataLoader'),
      createPort('test_loader', 'test_loader', 'output', 'DataLoader', true, '测试集 DataLoader'),
      createPort('data_arrays', 'data_arrays', 'output', 'Dict[str, np.ndarray]', false, '原始数组'),
      createPort('stats', 'stats', 'output', 'Dict[str, np.ndarray]', false, '归一化统计量'),
    ],
    metadata: { category: 'data_loader', is_required: true, order: 1, tags: ['pytorch', 'bridge'] },
  },
];

// 训练阶段节点
const TRAINING_NODES: Omit<PipelineNode, 'id' | 'position' | 'selected_impl' | 'config' | 'alternative_impls'>[] = [
  {
    template_id: 'model',
    type: 'training',
    name: 'Model',
    label: '模型',
    description: '神经网络模型定义',
    inputs: [
      createPort('input_dim', 'input_dim', 'input', 'int', true, '输入特征维度'),
      createPort('max_cracks', 'max_cracks', 'input', 'int', true, '最大裂缝数'),
    ],
    outputs: [
      createPort('model_out', 'model', 'output', 'ModelProtocol', true, '模型实例'),
      createPort('model_info', 'model_info', 'output', 'Dict', false, '模型元信息'),
    ],
    metadata: { category: 'model', is_required: true, order: 0, tags: ['pytorch', 'multi_crack'] },
  },
  {
    template_id: 'loss',
    type: 'training',
    name: 'Loss',
    label: '损失函数',
    description: '计算训练损失',
    inputs: [
      createPort('pred', 'pred', 'input', 'Union[Tensor, Tuple]', true, '模型预测'),
      createPort('target', 'target', 'input', 'Tensor', true, '真实标签'),
    ],
    outputs: [
      createPort('loss_out', 'loss', 'output', 'Union[Tensor, Tuple[Tensor, Dict]]', true, '总损失或(总损失, 损失字典)'),
    ],
    metadata: { category: 'loss', is_required: true, order: 1, tags: ['pytorch'] },
  },
  {
    template_id: 'optimizer',
    type: 'training',
    name: 'Optimizer',
    label: '优化器',
    description: '参数优化器',
    inputs: [
      createPort('model_params', 'model_params', 'input', 'Iterator[Parameter]', true, '模型参数'),
    ],
    outputs: [
      createPort('optimizer_out', 'optimizer', 'output', 'OptimizerProtocol', true, '优化器实例'),
    ],
    metadata: { category: 'optimizer', is_required: true, order: 2, tags: ['pytorch'] },
  },
  {
    template_id: 'trainer',
    type: 'training',
    name: 'Trainer',
    label: '训练器',
    description: '执行完整训练流程',
    inputs: [
      createPort('model', 'model', 'input', 'ModelProtocol', true, '模型'),
      createPort('train_loader', 'train_loader', 'input', 'DataLoader', true, '训练数据'),
      createPort('val_loader', 'val_loader', 'input', 'DataLoader', true, '验证数据'),
      createPort('loss_fn', 'loss_fn', 'input', 'LossProtocol', true, '损失函数'),
      createPort('optimizer', 'optimizer', 'input', 'OptimizerProtocol', true, '优化器'),
      createPort('config', 'config', 'input', 'Dict', true, '训练配置'),
    ],
    outputs: [
      createPort('train_result', 'train_result', 'output', 'TrainResult', true, '训练结果'),
      createPort('model_path', 'model_path', 'output', 'str', true, '保存的模型路径'),
    ],
    metadata: { category: 'trainer', is_required: true, order: 3, tags: ['training', 'three_phase'] },
  },
];

// 推理阶段节点
const INFERENCE_NODES: Omit<PipelineNode, 'id' | 'position' | 'selected_impl' | 'config' | 'alternative_impls'>[] = [
  {
    template_id: 'model_loader',
    type: 'inference',
    name: 'ModelLoader',
    label: '模型加载器',
    description: '从检查点加载训练好的模型',
    inputs: [
      createPort('model_path', 'model_path', 'input', 'str', true, '模型文件路径'),
      createPort('device', 'device', 'input', 'str', false, '目标设备'),
    ],
    outputs: [
      createPort('model', 'model', 'output', 'ModelProtocol', true, '加载的模型'),
    ],
    metadata: { category: 'model', is_required: true, order: 0, tags: ['inference'] },
  },
  {
    template_id: 'inference_engine',
    type: 'inference',
    name: 'InferenceEngine',
    label: '推理引擎',
    description: '批量推理 + 解码输出',
    inputs: [
      createPort('model', 'model', 'input', 'ModelProtocol', true, '模型'),
      createPort('data_loader', 'data_loader', 'input', 'DataLoader', true, '测试数据'),
      createPort('cls_threshold', 'cls_threshold', 'input', 'float', false, '分类阈值(双头)'),
      createPort('pos_threshold', 'pos_threshold', 'input', 'float', false, '位置阈值(单头)'),
    ],
    outputs: [
      createPort('predictions', 'predictions', 'output', 'List[List[Dict]]', true, '解码后的裂缝列表'),
      createPort('raw_outputs', 'raw_outputs', 'output', 'Dict', false, '原始网络输出'),
    ],
    metadata: { category: 'postprocessor', is_required: true, order: 1, tags: ['inference', 'decode'] },
  },
];

// 评估阶段节点
const EVALUATION_NODES: Omit<PipelineNode, 'id' | 'position' | 'selected_impl' | 'config' | 'alternative_impls'>[] = [
  {
    template_id: 'evaluator',
    type: 'evaluation',
    name: 'Evaluator',
    label: '评估器',
    description: '完整评估流程：推理 + 匈牙利匹配 + 指标计算',
    inputs: [
      createPort('model', 'model', 'input', 'ModelProtocol', true, '模型'),
      createPort('test_loader', 'test_loader', 'input', 'DataLoader', true, '测试数据'),
      createPort('loss_fn', 'loss_fn', 'input', 'LossProtocol', false, '损失函数(可选)'),
      createPort('config', 'config', 'input', 'Dict', true, '评估配置'),
    ],
    outputs: [
      createPort('eval_result', 'eval_result', 'output', 'EvaluationResult', true, '评估结果'),
      createPort('metrics', 'metrics', 'output', 'Dict[str, float]', true, '指标字典'),
      createPort('details', 'details', 'output', 'List[Dict]', false, '逐样本详情'),
    ],
    metadata: { category: 'evaluator', is_required: true, order: 0, tags: ['evaluation', 'hungarian'] },
  },
];

// ─────────────────────────────────────────────────────────────────────
// 模板连接定义
// ─────────────────────────────────────────────────────────────────────

const DATA_GEN_CONNECTIONS: Omit<PipelineConnection, 'id'>[] = [
  { source: { node_id: 'data_generator', port_id: 'signals_out' }, target: { node_id: 'data_loader', port_id: 'data_path' } },
];

const TRAINING_CONNECTIONS: Omit<PipelineConnection, 'id'>[] = [
  { source: { node_id: 'data_loader', port_id: 'train_loader' }, target: { node_id: 'trainer', port_id: 'train_loader' } },
  { source: { node_id: 'data_loader', port_id: 'val_loader' }, target: { node_id: 'trainer', port_id: 'val_loader' } },
  { source: { node_id: 'model', port_id: 'model_out' }, target: { node_id: 'trainer', port_id: 'model' } },
  { source: { node_id: 'loss', port_id: 'loss_out' }, target: { node_id: 'trainer', port_id: 'loss_fn' } },
  { source: { node_id: 'optimizer', port_id: 'optimizer_out' }, target: { node_id: 'trainer', port_id: 'optimizer' } },
];

const INFERENCE_CONNECTIONS: Omit<PipelineConnection, 'id'>[] = [
  { source: { node_id: 'model_loader', port_id: 'model' }, target: { node_id: 'inference_engine', port_id: 'model' } },
  { source: { node_id: 'data_loader', port_id: 'test_loader' }, target: { node_id: 'inference_engine', port_id: 'data_loader' } },
];

const EVALUATION_CONNECTIONS: Omit<PipelineConnection, 'id'>[] = [
  { source: { node_id: 'model_loader', port_id: 'model' }, target: { node_id: 'evaluator', port_id: 'model' } },
  { source: { node_id: 'data_loader', port_id: 'test_loader' }, target: { node_id: 'evaluator', port_id: 'test_loader' } },
  { source: { node_id: 'loss', port_id: 'loss_out' }, target: { node_id: 'evaluator', port_id: 'loss_fn' } },
];

// ─────────────────────────────────────────────────────────────────────
// 导出的模板注册表
// ─────────────────────────────────────────────────────────────────────

export const PIPELINE_TEMPLATES: Record<string, PipelineTemplate> = {
  data_generation: {
    id: 'data_generation',
    name: '数据生成流程',
    description: '生成合成桥梁振动数据并加载为 PyTorch DataLoader',
    category: 'data_generation',
    version: '1.0.0',
    nodes: DATA_GEN_NODES,
    connections: DATA_GEN_CONNECTIONS,
    metadata: {
      author: 'CPDV Team',
      created_at: '2026-01-01',
      tags: ['synthetic', 'data_generation', 'bridge'],
      estimated_time: '5-10 min',
      difficulty: 'beginner',
    },
  },
  training: {
    id: 'training',
    name: '模型训练流程',
    description: '完整三阶段训练：数据加载 → 模型定义 → 损失/优化器 → 训练',
    category: 'training',
    version: '1.0.0',
    nodes: TRAINING_NODES,
    connections: TRAINING_CONNECTIONS,
    metadata: {
      author: 'CPDV Team',
      created_at: '2026-01-01',
      tags: ['training', 'three_phase', 'multi_crack'],
      estimated_time: '30-60 min',
      difficulty: 'intermediate',
    },
  },
  inference: {
    id: 'inference',
    name: '模型推理流程',
    description: '加载模型 → 批量推理 → 解码输出裂缝列表',
    category: 'inference',
    version: '1.0.0',
    nodes: INFERENCE_NODES,
    connections: INFERENCE_CONNECTIONS,
    metadata: {
      author: 'CPDV Team',
      created_at: '2026-01-01',
      tags: ['inference', 'decode', 'multi_crack'],
      estimated_time: '1-5 min',
      difficulty: 'beginner',
    },
  },
  evaluation: {
    id: 'evaluation',
    name: '模型评估流程',
    description: '加载模型 → 测试集评估 → 匈牙利匹配 → 多指标报告',
    category: 'evaluation',
    version: '1.0.0',
    nodes: EVALUATION_NODES,
    connections: EVALUATION_CONNECTIONS,
    metadata: {
      author: 'CPDV Team',
      created_at: '2026-01-01',
      tags: ['evaluation', 'hungarian', 'metrics'],
      estimated_time: '5-15 min',
      difficulty: 'intermediate',
    },
  },
};

// 实现替代方案映射
export const NODE_ALTERNATIVE_IMPLS: Record<string, PipelineNodeImpl[]> = {
  data_loader: DATA_LOADER_IMPLS,
  model: MODEL_IMPLS,
  loss: LOSS_IMPLS,
  optimizer: OPTIMIZER_IMPLS,
  trainer: TRAINER_IMPLS,
  evaluator: EVALUATOR_IMPLS,
  // 推理阶段复用训练阶段的实现
  model_loader: MODEL_IMPLS,
  inference_engine: [],
};

// 默认实现选择
export const DEFAULT_IMPL_BY_CATEGORY: Record<string, string> = {
  data_loader: 'legacy_data_loader',
  model: 'legacy_dual_head_model',
  loss: 'legacy_dual_head_loss',
  optimizer: 'legacy_adamw',
  trainer: 'legacy_three_phase_trainer',
  evaluator: 'legacy_hungarian_evaluator',
  preprocessor: '',
  postprocessor: '',
  data_generator: '',
};