export interface Crack {
  pos: number;      // 位置 m
  depth: number;    // 深度比 0~1
  conf?: number;    // 置信度（预测）
  match?: number | null; // 匹配的真实裂缝索引
  hit?: boolean;
}

export interface BridgeParams {
  mv: number; kv: number; cv: number; V: number; L: number;
  E: number; I: number; m: number;
  [k: string]: number;
}

export interface CpdvSignalSeries {
  pos: number;        // 位置 m
  depth?: number;     // 深度比 0~1（G20 多裂缝模式后存在；G19 老数据无此字段）
  signal: number[];   // 完整时间序列（len = 3001 @ deltat=0.005）
}

export interface Bridge {
  id: string;
  name: string;
  sample?: number;
  params: BridgeParams;
  true_cracks: Crack[];
  pred_cracks: Crack[];
  cpdv: number[];
  cpdv_len: number;
  cpdv_offset: number;
  cpdv_signals?: CpdvSignalSeries[];  // G19/G20: 单裂缝×多位置探针信号（计算CPDV后才有）
  combined_cpdv?: number[];           // G21: 多裂缝组合 CPDV（multi_crack 预测写回，② 区优先渲单条）
  signal_files?: { has_signals: boolean; [k: string]: any };
  n_true: number;
  n_pred: number;
  n_hit: number;
  n_miss: number;
  n_false: number;
  // 数据来源标识（merged dashboard 注入）
  status?: 'registered' | 'legacy';
  source?: string;
}

export interface DashboardMeta {
  model: string;
  checkpoint: string;
  input_dim?: number;
  max_cracks?: number;
  cls_threshold?: number;
  match_cost?: number;
  metrics: {
    pos_mae: number; depth_mae: number; recall: number;
    precision: number; f1: number; n_matched: number;
    n_gt: number; n_pred: number;
  };
  // G13: 指标阈值随 meta 下发（前端 Header.tsx 用），后端 dashboard.py 注入默认值
  thresholds?: {
    pos_mae_max?: number;   // 默认 1.0 (m)
    depth_mae_max?: number;  // 默认 0.05
    f1_min?: number;        // 默认 0.87
    recall_min?: number;    // 默认 0.80
    precision_min?: number; // 默认 0.80
  };
  test_size: number;
  n_scenarios?: number;
  generated?: string;
  note?: string;
}

export interface DashboardData {
  meta: DashboardMeta;
  bridges: Bridge[];
}
