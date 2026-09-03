import type { ToolDefinition } from './llm-client';

export function buildCpdvTools(): ToolDefinition[] {
  return [
    {
      type: 'function',
      function: {
        name: 'cb_list_bridges',
        description: '列出所有已注册桥梁及其参数和状态',
        parameters: { type: 'object', properties: {} },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_register_bridge',
        description: '注册一座新桥梁，可指定初始参数（单位：km/h→m/s、kN→N、GPa→Pa、t→kg、mm→m）',
        parameters: {
          type: 'object',
          properties: {
            name: { type: 'string', description: '桥梁名称，如 桥梁01' },
            V: { type: 'number', description: '车速(m/s)，或传 V_kmh(km/h)' },
            L: { type: 'number', description: '跨长(m)' },
            mv: { type: 'number', description: '车辆质量(kg)' },
          },
          required: ['name'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_cpdv_compute',
        description: '计算某桥梁的 CPDV（流程C1），需指定裂缝深度和扰动位置列表',
        parameters: {
          type: 'object',
          properties: {
            bridge: { type: 'string', description: '桥梁名，如 桥梁01' },
            depth: { type: 'number', description: '信号裂缝深度(m)' },
            distances: { type: 'string', description: '扰动位置列表，逗号分隔，如 "5,10,15"' },
          },
          required: ['bridge', 'depth'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_predict_single',
        description: '单裂缝损伤预测（流程C2）',
        parameters: {
          type: 'object',
          properties: {
            model: { type: 'string', description: '模型路径，默认 cracknet.json' },
          },
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_predict_multi',
        description: '多裂缝损伤预测（流程C3），默认 multi_crack_dual_retrained.pth',
        parameters: {
          type: 'object',
          properties: {
            model: { type: 'string', description: '模型路径' },
          },
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_random_condition',
        description: '随机多工况分析（流程C4），判定车重/车速/跨长对CPDV影响大小（CV变异系数）',
        parameters: {
          type: 'object',
          properties: {
            mode: { type: 'string', description: 'single 或 multi_pos' },
            n_samples: { type: 'number', description: '采样数，默认50' },
          },
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_compare_bridges',
        description: '对比两座桥梁的损伤预测质量',
        parameters: {
          type: 'object',
          properties: {
            a: { type: 'string', description: '桥梁A' },
            b: { type: 'string', description: '桥梁B' },
          },
          required: ['a', 'b'],
        },
      },
    },
    {
      type: 'function',
      function: {
        name: 'cb_refresh_dashboard',
        description: '刷新看板数据',
        parameters: { type: 'object', properties: {} },
      },
    },
  ];
}
