/** QuickAICommands - Predefined AI command buttons for common operations */
import { useState } from 'react';
import { useAICommand } from '../hooks/useAICommand';

interface QuickAICommandsProps {
  onCommandComplete?: () => void;
  bridgeId?: string;
}

export function QuickAICommands({ onCommandComplete, bridgeId }: QuickAICommandsProps) {
  const [{ loading, error, taskId }, { execute }] = useAICommand();
  const [activeTask, setActiveTask] = useState<string | null>(null);

  const commands = [
    // Pipeline Execution
    {
      group: '流水线执行',
      items: [
        {
          label: '快速 CPDV 分析',
          description: '运行 Pipeline 6 快速模式 (~2分钟)',
          method: 'pipeline.execute',
          params: { pipelines: ['pipeline_6_cpdv_analysis'], mode: 'quick' },
        },
        {
          label: '完整数据生成',
          description: 'Pipeline 1 生成仿真数据 (~10分钟)',
          method: 'pipeline.execute',
          params: { pipelines: ['pipeline_1_cpdv_simulation'], mode: 'quick' },
        },
        {
          label: '多裂缝模型训练',
          description: 'Pipeline 4 双头模型训练 (~30分钟)',
          method: 'pipeline.execute',
          params: { pipelines: ['pipeline_4_multi_crack'], mode: 'quick' },
        },
        {
          label: '完整生产流程',
          description: '所有 Pipeline 全阶段 (~2-4小时)',
          method: 'pipeline.execute',
          params: { 
            pipelines: [
              'pipeline_1_cpdv_simulation',
              'pipeline_2_single_crack_bp',
              'pipeline_3_lstm_sequence',
              'pipeline_4_multi_crack',
              'pipeline_5_pinn',
              'pipeline_6_cpdv_analysis'
            ], 
            mode: 'full' 
          },
        },
      ],
    },
    // Data Analysis
    {
      group: '数据分析',
      items: [
        {
          label: 'CPDV 时间序列',
          description: '获取看板2所需的 CPDV 信号波形',
          method: 'data.query',
          params: { artifact: 'cpdv_signals', filters: { depth: 0.2, downsample: 400 } },
        },
        {
          label: '模型性能对比',
          description: '获取所有模型的评分卡数据',
          method: 'data.query',
          params: { artifact: 'model_metrics' },
        },
        {
          label: 'CV 变异系数分析',
          description: '判定是否需要多工况训练',
          method: 'analysis.run',
          params: { type: 'cv', params: { n_samples: 50, crack_pos: 15, crack_depth: 0.2 } },
        },
        {
          label: '峰值-位置/深度关系',
          description: 'CPDV 峰值随裂纹位置和深度的变化',
          method: 'analysis.run',
          params: { type: 'peak_vs_pos', params: {} },
        },
        {
          label: '多位置箱线图',
          description: '不同裂纹位置的 CPDV 分布对比',
          method: 'analysis.run',
          params: { type: 'peak_vs_pos', params: { mode: 'multi_pos' } },
        },
      ],
    },
    // Dashboard Operations
    {
      group: '看板操作',
      items: [
        {
          label: '全量同步看板',
          description: '刷新所有看板组件数据',
          method: 'dashboard.sync',
          params: { 
            widgets: ['cpdv_timeseries', 'model_scorecard', 'peak_vs_position', 'cv_analysis', 'multi_crack_comparison'],
            force_refresh: true 
          },
        },
        {
          label: '导出看板数据',
          description: '导出 dashboard_summary.json',
          method: 'data.export',
          params: { artifact: 'dashboard_summary', format: 'json' },
        },
      ],
    },
    // AI Interpretation
    {
      group: 'AI 解读',
      items: [
        {
          label: '解读 CV 分析',
          description: 'AI 解释随机工况分析结果',
          method: 'analysis.interpret',
          params: { artifact: 'cv_analysis', question: 'CV值意味着什么？是否需要多工况训练？' },
        },
        {
          label: '对比模型性能',
          description: '对比所有模型的 F1、MAE 等指标',
          method: 'analysis.compare',
          params: { models: ['cracknet', 'lstm', 'multi_crack_dual', 'pinn'], metrics: ['f1', 'mae_pos', 'mae_depth'] },
        },
      ],
    },
  ];

  const handleExecute = async (method: string, params: Record<string, any>) => {
    // Add bridge_id if provided
    const finalParams = bridgeId ? { ...params, bridge_id: bridgeId } : params;
    
    setActiveTask(method);
    try {
      await execute(method, finalParams, {
        onProgress: (progress) => {
          console.log(`[${method}]`, progress?.stage, progress?.percent);
        },
        onResult: (result) => {
          console.log(`[${method}] completed`, result);
          onCommandComplete?.();
        },
        onError: (err) => {
          console.error(`[${method}] failed`, err);
        },
      });
    } finally {
      setActiveTask(null);
    }
  };

  return (
    <div className="space-y-4">
      {commands.map(({ group, items }) => (
        <div key={group} className="space-y-2">
          <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
            {group}
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {items.map((cmd) => (
              <button
                key={cmd.label}
                onClick={() => handleExecute(cmd.method, cmd.params)}
                disabled={loading && activeTask === cmd.method}
                className={`p-3 text-left rounded-lg border transition-colors ${
                  loading && activeTask === cmd.method
                    ? 'bg-blue-50 border-blue-200 cursor-wait'
                    : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-gray-900">{cmd.label}</div>
                <div className="text-xs text-gray-500 mt-1">{cmd.description}</div>
                {loading && activeTask === cmd.method && (
                  <div className="mt-2 flex items-center gap-2 text-blue-600">
                    <span className="animate-spin text-sm">⟳</span>
                    <span className="text-sm">执行中...</span>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}
      
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          错误: {error}
        </div>
      )}
      
      {taskId && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-sm">
          任务 ID: <code>{taskId}</code>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Pipeline Stage Selector - For granular pipeline control
// ─────────────────────────────────────────────────────────────────────

interface PipelineStageSelectorProps {
  pipelineId: string;
  onExecute: (pipelineId: string, stages: string[]) => void;
  availableStages: Array<{ id: string; name: string; critical: boolean }>;
}

export function PipelineStageSelector({ pipelineId, onExecute, availableStages }: PipelineStageSelectorProps) {
  const [selectedStages, setSelectedStages] = useState<string[]>(
    availableStages.filter(s => s.critical).map(s => s.id)
  );
  const [mode, setMode] = useState<'quick' | 'full'>('quick');

  const toggleStage = (stageId: string) => {
    setSelectedStages(prev => 
      prev.includes(stageId) 
        ? prev.filter(s => s !== stageId) 
        : [...prev, stageId]
    );
  };

  const handleExecute = () => {
    if (selectedStages.length === 0) return;
    onExecute(pipelineId, selectedStages);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2">
          <input
            type="radio"
            value="quick"
            checked={mode === 'quick'}
            onChange={() => setMode('quick')}
            className="text-blue-600"
          />
          <span className="text-sm">快速模式</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            value="full"
            checked={mode === 'full'}
            onChange={() => setMode('full')}
            className="text-blue-600"
          />
          <span className="text-sm">完整模式</span>
        </label>
      </div>

      <div className="space-y-2 max-h-60 overflow-y-auto">
        {availableStages.map(stage => (
          <label key={stage.id} className="flex items-center gap-2 p-2 rounded border hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={selectedStages.includes(stage.id)}
              onChange={() => toggleStage(stage.id)}
              className="text-blue-600"
            />
            <span className="text-sm font-medium">{stage.name}</span>
            {stage.critical && (
              <span className="ml-auto px-1.5 py-0.5 text-xs bg-red-100 text-red-700 rounded">关键</span>
            )}
          </label>
        ))}
      </div>

      <button
        onClick={handleExecute}
        disabled={selectedStages.length === 0}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        执行选中阶段 ({selectedStages.length})
      </button>
    </div>
  );
}