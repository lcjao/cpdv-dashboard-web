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
  n_true: number;
  n_pred: number;
  n_hit: number;
  n_miss: number;
  n_false: number;
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
  test_size: number;
  n_scenarios?: number;
  generated?: string;
  note?: string;
}

export interface DashboardData {
  meta: DashboardMeta;
  bridges: Bridge[];
}
