/** UnifiedTimelineBar - 统一时间轴（Pipeline运行 + 实验里程碑 + Git提交） */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { fetchTimeline, fetchPipelineRuns, PipelineRunRecord, TimelineResponse, TimelineCommit, TimelineExperiment } from '../../lib/algorithm-api';
import { useTagProgress } from '../../lib/progress-context';

const HEATMAP_COLORS = [
  '#ebedf0',
  '#9be9a8',
  '#40c463',
  '#30a14e',
  '#216e39',
];

function getHeatmapColor(count: number): string {
  if (count === 0) return HEATMAP_COLORS[0];
  if (count <= 3) return HEATMAP_COLORS[1];
  if (count <= 6) return HEATMAP_COLORS[2];
  if (count <= 9) return HEATMAP_COLORS[3];
  return HEATMAP_COLORS[4];
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function formatRelativeTime(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins}分钟前`;
  if (diffHours < 24) return `${diffHours}小时前`;
  if (diffDays < 7) return `${diffDays}天前`;
  return formatDate(dateStr);
}

interface UnifiedTimelineBarProps {
  library?: string;
  height?: number;
  onCommitClick?: (commit: TimelineCommit) => void;
  onExperimentClick?: (exp: TimelineExperiment) => void;
  onPipelineRunClick?: (run: PipelineRunRecord) => void;
  /** 当前训练中的实验/任务 ID */
  activeTrainId?: string;
  /** 训练进度（来自 WS，覆盖列表中对应项的进度） */
  trainProgress?: {
    stage: string;
    message: string;
    percent: number;
    epoch?: number;
    totalEpochs?: number;
    loss?: number;
  } | null;
}

export default function UnifiedTimelineBar({
  library,
  height = 220,
  onCommitClick,
  onExperimentClick,
  onPipelineRunClick,
  activeTrainId,
  trainProgress,
}: UnifiedTimelineBarProps) {
  const [timelineData, setTimelineData] = useState<TimelineResponse | null>(null);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'pipeline_runs' | 'experiments' | 'commits' | 'heatmap'>('pipeline_runs');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [localCommits, setLocalCommits] = useState<TimelineCommit[]>([]);
  const [localExperiments, setLocalExperiments] = useState<TimelineExperiment[]>([]);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  
  // 订阅 WS 训练进度
  const wsTrainProgress = useTagProgress('train');
  const wsPipelineProgress = useTagProgress('pipeline');

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.all([
      fetchTimeline(library),
      fetchPipelineRuns(50, 0),
    ]).then(([tl, pr]) => {
      if (mounted) {
        setTimelineData(tl);
        setPipelineRuns(pr.runs);
      }
    }).catch(e => mounted && setError(String(e)))
    .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [library]);

  // 合并服务端实验 + 本地新增实验
  const displayExperiments = useMemo(() => {
    const merged = [...(timelineData?.experiments ?? []), ...localExperiments];
    // 如果有活跃训练实验且不在列表中，添加到顶部
    if (activeTrainId && !merged.some(e => e.id === activeTrainId)) {
      merged.unshift({
        id: activeTrainId,
        name: 'training...',
        variant: 'multi_crack',
        date: new Date().toISOString(),
        metrics: {},
      });
    }
    // 按时间倒序
    return merged.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }, [timelineData, localExperiments, activeTrainId]);

  // 合并 pipeline runs + 正在运行的
  const displayPipelineRuns = useMemo(() => {
    const runs = [...pipelineRuns];
    if (activeTrainId && !runs.some(r => r.id === activeTrainId)) {
      // 正在运行的会通过 WS 进度显示，这里不重复添加
    }
    return runs.sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime());
  }, [pipelineRuns, activeTrainId]);

  const displayCommits = localCommits.length > 0 ? localCommits : timelineData?.commits ?? [];

  const handleCreateCommit = useCallback(() => {
    const now = new Date();
    const iso = now.toISOString();
    const commit: TimelineCommit = {
      hash: `local-${Date.now()}`,
      short_hash: `local-${String(Date.now()).slice(-6)}`,
      message: `chore: manual snapshot ${now.toLocaleString('zh-CN', { hour12: false })}`,
      author: 'local-user',
      date: iso,
      files_changed: 1,
      lines_added: 3,
      lines_deleted: 0,
      is_tag: false,
    };
    setLocalCommits(prev => [commit, ...prev]);
    setViewMode('commits');
    onCommitClick?.(commit);
  }, [onCommitClick]);

  const handleCreateExperiment = useCallback(() => {
    const now = new Date();
    const experiment: TimelineExperiment = {
      id: `exp-${Date.now()}`,
      name: 'manual-experiment',
      variant: 'baseline',
      date: now.toISOString(),
      metrics: {
        accuracy: Number((0.8 + Math.random() * 0.15).toFixed(4)),
        loss: Number((0.2 + Math.random() * 0.12).toFixed(4)),
      },
    };
    setLocalExperiments(prev => [experiment, ...prev]);
    setViewMode('experiments');
    onExperimentClick?.(experiment);
  }, [onExperimentClick]);

  const handleToggleItem = useCallback((id: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const heatmapData = useMemo(() => {
    if (!timelineData?.heatmap) return [];
    const today = new Date();
    const startDate = new Date(today);
    startDate.setFullYear(today.getFullYear() - 1);
    startDate.setDate(1);
    startDate.setHours(0, 0, 0, 0);

    const cells: Array<{ date: string; count: number; day: number; week: number }> = [];
    const heatmap = timelineData.heatmap;

    for (let d = new Date(startDate); d <= today; d.setDate(d.getDate() + 1)) {
      const dateStr = formatDate(d.toISOString().split('T')[0]);
      const count = heatmap[dateStr] || 0;
      const day = d.getDay();
      const week = Math.floor((d.getTime() - startDate.getTime()) / (7 * 24 * 60 * 60 * 1000));
      cells.push({ date: dateStr, count, day, week });
    }
    return cells;
  }, [timelineData]);

  const experimentsByDate = useMemo(() => {
    const experiments = displayExperiments;
    if (!experiments.length) return {};
    const map: Record<string, typeof experiments> = {};
    experiments.forEach(exp => {
      const date = formatDate(exp.date);
      if (!map[date]) map[date] = [];
      map[date].push(exp);
    });
    return map;
  }, [displayExperiments]);

  const pipelineRunsByDate = useMemo(() => {
    const runs = displayPipelineRuns;
    if (!runs.length) return {};
    const map: Record<string, typeof runs> = {};
    runs.forEach(run => {
      const date = formatDate(run.startTime);
      if (!map[date]) map[date] = [];
      map[date].push(run);
    });
    return map;
  }, [displayPipelineRuns]);

  // 当前显示的进度：优先使用传入的 trainProgress，其次使用 WS 进度
  const currentProgress = trainProgress ?? wsTrainProgress ?? wsPipelineProgress;

  if (loading) {
    return (
      <div style={{
        height: height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--sub)',
        background: 'var(--card)',
        borderRadius: 12,
        border: '1px solid var(--line)',
      }}>
        加载时间轴...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ height: height, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, padding: 20, color: 'var(--red)', background: 'var(--card)', borderRadius: 12, border: '1px solid var(--line)' }}>
        <div>加载失败: {error}</div>
      </div>
    );
  }

  // 判断某项是否正在运行中
  const isItemRunning = (itemId: string, _itemType: 'experiment' | 'pipeline') => {
    if (!currentProgress) return false;
    if (currentProgress.stage === 'done' || currentProgress.stage === 'completed' || currentProgress.stage === 'error' || currentProgress.stage === 'failed') return false;
    return activeTrainId === itemId;
  };

  const getItemProgress = (itemId: string) => {
    if (isItemRunning(itemId, 'experiment') || isItemRunning(itemId, 'pipeline')) {
      return currentProgress;
    }
    return null;
  };

  const renderProgressBar = (progress: any) => {
    if (!progress) return null;
    return (
      <div style={{
        marginTop: 8,
        padding: '10px 12px',
        background: 'rgba(255,152,0,0.08)',
        border: '1px solid rgba(255,152,0,0.3)',
        borderRadius: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ fontWeight: 700, color: 'var(--amber)', fontSize: 11, textTransform: 'uppercase' }}>
            {progress.stage}
          </span>
          <span style={{ color: 'var(--sub)', fontSize: 11 }}>
            {progress.message}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,.1)', borderRadius: 3, overflow: 'hidden' }}>
            <div
              style={{
                width: `${Math.min(100, Math.max(0, progress.percent ?? 0))}%`,
                height: '100%',
                background: 'var(--amber)',
                transition: 'width .3s ease',
              }}
            />
          </div>
          <span style={{ color: 'var(--sub)', minWidth: '40px', textAlign: 'right', fontSize: 11, fontFamily: 'var(--mono)' }}>
            {Math.round(progress.percent ?? 0)}%
          </span>
        </div>
        {(progress.epoch !== undefined || progress.loss !== undefined) && (
          <div style={{ marginTop: 6, fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
            {progress.epoch !== undefined && progress.totalEpochs !== undefined && (
              <span>Epoch: {String(progress.epoch)}/{String(progress.totalEpochs)}</span>
            )}
            {progress.loss !== undefined && (
              <span style={{ marginLeft: 12 }}>Loss: {Number(progress.loss).toFixed(4)}</span>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{
      height: height,
      background: 'var(--card)',
      borderRadius: 12,
      border: '1px solid var(--line)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            display: 'inline-flex',
            width: 28,
            height: 28,
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 8,
            background: viewMode === 'pipeline_runs' ? 'var(--purple-bg, rgba(156,39,176,0.15))' : 
                       viewMode === 'experiments' ? 'var(--amber-bg)' :
                       viewMode === 'commits' ? 'var(--blue-bg)' : 'var(--green-bg, rgba(0,200,83,0.15))',
            color: viewMode === 'pipeline_runs' ? '#9C27B0' :
                   viewMode === 'experiments' ? '#FF9800' :
                   viewMode === 'commits' ? 'var(--blue)' : '#00C853',
            fontSize: 14,
          }}>
            {viewMode === 'pipeline_runs' && '⚙️'}
            {viewMode === 'experiments' && '🧪'}
            {viewMode === 'commits' && '📝'}
            {viewMode === 'heatmap' && '🔥'}
          </span>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>
            时间轴
          </span>
          <span style={{
            fontSize: 11,
            color: 'var(--sub)',
            padding: '2px 8px',
            background: 'var(--bg)',
            borderRadius: 4,
            border: '1px solid var(--line)',
          }}>
            {viewMode === 'pipeline_runs' && `${displayPipelineRuns.length} 次运行`}
            {viewMode === 'experiments' && `${displayExperiments.length} 个实验 · ${timelineData?.tags?.length || 0} 标签`}
            {viewMode === 'commits' && `${displayCommits.length} 次提交`}
            {viewMode === 'heatmap' && '年度热力图'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {(['pipeline_runs', 'experiments', 'commits', 'heatmap'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => {
                if (mode === 'commits') {
                  handleCreateCommit();
                  return;
                }
                if (mode === 'experiments') {
                  handleCreateExperiment();
                  return;
                }
                setViewMode(mode);
              }}
              style={{
                padding: '6px 12px',
                fontSize: 11,
                fontWeight: viewMode === mode ? 600 : 400,
                color: viewMode === mode ? '#fff' : 'var(--ink)',
                background: viewMode === mode 
                  ? (mode === 'pipeline_runs' ? '#9C27B0' : mode === 'experiments' ? 'var(--amber)' : mode === 'commits' ? 'var(--blue)' : '#00C853')
                  : 'transparent',
                border: '1px solid var(--line)',
                borderRadius: 6,
                cursor: 'pointer',
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
              }}
            >
              {mode === 'pipeline_runs' && '⚙️ Pipeline'}
              {mode === 'experiments' && '🧪 实验'}
              {mode === 'commits' && '📝 提交'}
              {mode === 'heatmap' && '🔥 热力图'}
            </button>
          ))}
        </div>
      </div>

      <div style={{
        flex: 1,
        overflow: 'hidden',
        position: 'relative',
      }}>
        {/* Heatmap View */}
        {viewMode === 'heatmap' && (
          <div style={{
            width: '100%',
            height: '100%',
            padding: '16px',
            overflowX: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 11,
              color: 'var(--sub)',
              paddingBottom: 8,
            }}>
              <span>少</span>
              {HEATMAP_COLORS.map((color, i) => (
                <div key={i} style={{
                  width: 14,
                  height: 14,
                  borderRadius: 3,
                  background: color,
                  border: i === 0 ? '1px solid var(--line)' : 'none',
                }} />
              ))}
              <span>多</span>
            </div>

            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              fontFamily: 'var(--mono)',
              fontSize: 10,
            }}>
              <div style={{ display: 'flex', height: 14 }}>
                {['周日', '周一', '周二', '周三', '周四', '周五', '周六'].map((day, i) => (
                  <div key={i} style={{
                    width: 14,
                    height: 14,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 9,
                    color: 'var(--sub)',
                    borderRight: '1px solid var(--line)',
                  }}>
                    {day[0]}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {(() => {
                  const maxWeek = Math.max(...heatmapData.map(c => c.week), 0);
                  const weeks: number[][] = Array.from({ length: maxWeek + 1 }, () => Array(7).fill(-1));
                  heatmapData.forEach(cell => {
                    if (cell.week <= maxWeek) weeks[cell.week][cell.day] = heatmapData.indexOf(cell);
                  });
                  return weeks.map((week, w) => (
                    <div key={w} style={{ display: 'flex', height: 14 }}>
                      {week.map((cellIdx, d) => (
                        <div key={`${w}-${d}`} style={{
                          width: 14,
                          height: 14,
                          borderRadius: 3,
                          border: '1px solid var(--line)',
                          marginRight: 2,
                          cursor: cellIdx >= 0 ? 'pointer' : 'default',
                          background: cellIdx >= 0 ? getHeatmapColor(heatmapData[cellIdx].count) : 'transparent',
                          transition: 'transform 0.1s, box-shadow 0.1s',
                          transform: selectedDate === heatmapData[cellIdx]?.date ? 'scale(1.3)' : 'scale(1)',
                          boxShadow: selectedDate === heatmapData[cellIdx]?.date ? '0 0 0 2px var(--amber)' : 'none',
                          zIndex: selectedDate === heatmapData[cellIdx]?.date ? 10 : 0,
                        }}
                          onClick={cellIdx >= 0 ? () => {
                            const date = heatmapData[cellIdx].date;
                            setSelectedDate(date === selectedDate ? null : date);
                          } : undefined}
                        />
                      ))}
                    </div>
                  ));
                })()}
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Runs View */}
        {viewMode === 'pipeline_runs' && (
          <div style={{
            width: '100%',
            height: '100%',
            overflowY: 'auto',
            padding: '16px',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(pipelineRunsByDate)
                .sort(([a], [b]) => b.localeCompare(a))
                .map(([date, runs]) => (
                  <div key={date} style={{ marginBottom: 16 }}>
                    <div style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: 'var(--sub)',
                      marginBottom: 8,
                      padding: '4px 10px',
                      background: 'var(--bg)',
                      borderRadius: 4,
                      display: 'inline-block',
                    }}>
                      ⚙️ {date} · {runs.length} 次运行
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {runs.map((run: PipelineRunRecord) => {
                        const isRunning = isItemRunning(run.id, 'pipeline');
                        const progress = getItemProgress(run.id);
                        const isExpanded = expandedItems.has(run.id);
                        const hasMetrics = run.metrics && Object.keys(run.metrics).length > 0;
                        const statusColor = run.status === 'completed' ? '#00C853' : run.status === 'failed' ? '#FF3D00' : '#FF9800';
                        const statusLabel = run.status === 'completed' ? '✅ 完成' : run.status === 'failed' ? '❌ 失败' : '🔄 运行中';

                        return (
                          <div
                            key={run.id}
                            onClick={() => { handleToggleItem(run.id); onPipelineRunClick?.(run); }}
                            style={{
                              padding: '12px 16px',
                              background: isRunning ? 'rgba(156,39,176,0.05)' : 'var(--bg)',
                              border: isRunning ? '2px solid #9C27B0' : '1px solid var(--line)',
                              borderRadius: 8,
                              cursor: 'pointer',
                              transition: 'all 0.15s',
                            }}
                            onMouseEnter={e => { if (!isRunning) e.currentTarget.style.borderColor = '#9C27B0'; }}
                            onMouseLeave={e => { if (!isRunning) e.currentTarget.style.borderColor = 'var(--line)'; }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span style={{
                                  fontSize: 13,
                                  fontWeight: 600,
                                  color: 'var(--ink)',
                                }}>
                                  {run.name}
                                </span>
                                {isRunning && (
                                  <span style={{
                                    fontSize: 9,
                                    fontWeight: 700,
                                    color: '#fff',
                                    background: '#9C27B0',
                                    padding: '2px 8px',
                                    borderRadius: 4,
                                    animation: 'pulse 1.5s infinite',
                                  }}>
                                    🔄 运行中
                                  </span>
                                )}
                                {!isRunning && (
                                  <span style={{
                                    fontSize: 9,
                                    fontWeight: 700,
                                    color: statusColor,
                                    background: `${statusColor}15`,
                                    padding: '2px 8px',
                                    borderRadius: 4,
                                  }}>
                                    {statusLabel}
                                  </span>
                                )}
                              </div>
                              <span style={{
                                fontSize: 10,
                                color: 'var(--sub)',
                                fontFamily: 'var(--mono)',
                              }}>
                                {formatRelativeTime(run.startTime)}
                                {run.durationMs && ` · ${(run.durationMs / 1000).toFixed(1)}s`}
                              </span>
                            </div>

                            {/* 训练进度条（实时） */}
                            {isRunning && progress && renderProgressBar(progress)}

                            {/* 阶段进度 */}
                            {run.stages && run.stages.length > 0 && (
                              <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
                                {run.stages.map((stage, idx) => (
                                  <div key={idx} style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 8,
                                    fontSize: 10,
                                    padding: '4px 8px',
                                    background: 'var(--bg)',
                                    borderRadius: 4,
                                    border: '1px solid var(--line)',
                                  }}>
                                    <span style={{
                                      width: 8,
                                      height: 8,
                                      borderRadius: '50%',
                                      background: stage.status === 'completed' ? '#00C853' : stage.status === 'running' ? '#FF9800' : stage.status === 'failed' ? '#FF3D00' : 'var(--line)',
                                      animation: stage.status === 'running' ? 'pulse 1.5s infinite' : 'none',
                                    }} />
                                    <span style={{ color: 'var(--ink)', flex: 1 }}>{stage.name}</span>
                                    {stage.progress !== undefined && (
                                      <span style={{ fontFamily: 'var(--mono)', color: 'var(--sub)' }}>
                                        {stage.progress}%
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* 指标展开/折叠 */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 11, marginTop: 8 }}>
                              {hasMetrics && (
                                <>
                                  <span
                                    onClick={e => { e.stopPropagation(); handleToggleItem(run.id); }}
                                    style={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: 4,
                                      padding: '4px 10px',
                                      background: isExpanded ? 'var(--purple-bg, rgba(156,39,176,0.15))' : 'var(--card)',
                                      border: '1px solid var(--line)',
                                      borderRadius: 4,
                                      cursor: 'pointer',
                                      color: isExpanded ? '#9C27B0' : 'var(--ink)',
                                      fontWeight: 600,
                                      transition: 'all 0.15s',
                                    }}
                                  >
                                    {isExpanded ? '▼' : '▶'} 指标详情
                                  </span>
                                  {Object.entries(run.metrics!).map(([k, v]) => (
                                    <span key={k} style={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: 4,
                                      padding: '2px 8px',
                                      background: 'var(--card)',
                                      border: '1px solid var(--line)',
                                      borderRadius: 4,
                                      fontSize: 10,
                                    }}>
                                      <span style={{ color: 'var(--sub)' }}>{k}:</span>
                                      <span style={{ fontWeight: 600, fontFamily: 'var(--mono)' }}>
                                        {typeof v === 'number' ? v.toFixed(4) : v}
                                      </span>
                                    </span>
                                  ))}
                                </>
                              )}
                            </div>

                            {/* 展开后的详细信息 */}
                            {isExpanded && (
                              <div style={{
                                marginTop: 10,
                                padding: '12px',
                                background: 'var(--card)',
                                border: '1px solid var(--line)',
                                borderRadius: 8,
                                animation: 'slideDown 0.2s ease',
                              }}>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
                                  {Object.entries(run.metrics || {}).map(([k, v]) => (
                                    <div key={k} style={{
                                      padding: '8px',
                                      background: 'var(--bg)',
                                      borderRadius: 6,
                                      border: '1px solid var(--line)',
                                    }}>
                                      <div style={{ fontSize: 9, color: 'var(--sub)', marginBottom: 2 }}>{k}</div>
                                      <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--ink)' }}>
                                        {typeof v === 'number' ? v.toFixed(4) : v}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                                {run.config && Object.keys(run.config).length > 0 && (
                                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
                                    <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--sub)', marginBottom: 6 }}>配置参数</div>
                                    <div style={{ fontSize: 10, color: 'var(--ink)', fontFamily: 'var(--mono)', maxHeight: 120, overflow: 'auto' }}>
                                      {JSON.stringify(run.config, null, 2)}
                                    </div>
                                  </div>
                                )}
                                {run.error && (
                                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line)', color: '#FF3D00' }}>
                                    <div style={{ fontSize: 10, fontWeight: 600, marginBottom: 4 }}>错误信息</div>
                                    <div style={{ fontSize: 10, fontFamily: 'var(--mono)', wordBreak: 'break-all' }}>{run.error}</div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              {Object.keys(pipelineRunsByDate).length === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--sub)', padding: 40 }}>
                  <div style={{ fontSize: 24, marginBottom: 8 }}>⚙️</div>
                  <div style={{ fontSize: 13 }}>暂无 Pipeline 运行记录</div>
                  <div style={{ fontSize: 11, marginTop: 4 }}>通过 AI 控制面板执行训练或 Pipeline 任务</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Experiments View */}
        {viewMode === 'experiments' && (
          <div style={{
            width: '100%',
            height: '100%',
            overflowY: 'auto',
            padding: '16px',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(experimentsByDate)
                .sort(([a], [b]) => b.localeCompare(a))
                .map(([date, exps]) => (
                  <div key={date} style={{ marginBottom: 16 }}>
                    <div style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: 'var(--sub)',
                      marginBottom: 8,
                      padding: '4px 10px',
                      background: 'var(--bg)',
                      borderRadius: 4,
                      display: 'inline-block',
                    }}>
                      📅 {date} · {exps.length} 个实验
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {exps.map((exp: TimelineExperiment) => {
                        const isTraining = isItemRunning(exp.id, 'experiment');
                        const progress = getItemProgress(exp.id);
                        const isExpanded = expandedItems.has(exp.id);
                        const hasMetrics = exp.metrics && Object.keys(exp.metrics).length > 0;

                        return (
                          <div
                            key={exp.id}
                            onClick={() => { handleToggleItem(exp.id); onExperimentClick?.(exp); }}
                            style={{
                              padding: '12px 16px',
                              background: isTraining ? 'rgba(255,152,0,0.05)' : 'var(--bg)',
                              border: isTraining ? '2px solid var(--amber)' : '1px solid var(--line)',
                              borderRadius: 8,
                              cursor: 'pointer',
                              transition: 'all 0.15s',
                            }}
                            onMouseEnter={e => { if (!isTraining) e.currentTarget.style.borderColor = 'var(--blue)'; }}
                            onMouseLeave={e => { if (!isTraining) e.currentTarget.style.borderColor = 'var(--line)'; }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span style={{
                                  fontSize: 13,
                                  fontWeight: 600,
                                  color: 'var(--ink)',
                                }}>
                                  {exp.name} ({exp.variant})
                                </span>
                                {isTraining && (
                                  <span style={{
                                    fontSize: 9,
                                    fontWeight: 700,
                                    color: '#fff',
                                    background: 'var(--amber)',
                                    padding: '2px 8px',
                                    borderRadius: 4,
                                    animation: 'pulse 1.5s infinite',
                                  }}>
                                    🔄 训练中
                                  </span>
                                )}
                                {exp.id.startsWith('exp-') && !isTraining && hasMetrics && (
                                  <span style={{
                                    fontSize: 9,
                                    fontWeight: 700,
                                    color: '#00C853',
                                    background: 'rgba(0,200,83,0.1)',
                                    padding: '2px 8px',
                                    borderRadius: 4,
                                  }}>
                                    ✅ 完成
                                  </span>
                                )}
                              </div>
                              <span style={{
                                fontSize: 10,
                                color: 'var(--sub)',
                                fontFamily: 'var(--mono)',
                              }}>
                                {formatRelativeTime(exp.date)}
                              </span>
                            </div>

                            {/* 训练进度条（实时） */}
                            {isTraining && progress && renderProgressBar(progress)}

                            {/* 指标展开/折叠 */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 11 }}>
                              {hasMetrics && (
                                <>
                                  <span
                                    onClick={e => { e.stopPropagation(); handleToggleItem(exp.id); }}
                                    style={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: 4,
                                      padding: '4px 10px',
                                      background: isExpanded ? 'var(--blue-bg)' : 'var(--card)',
                                      border: '1px solid var(--line)',
                                      borderRadius: 4,
                                      cursor: 'pointer',
                                      color: isExpanded ? 'var(--blue)' : 'var(--ink)',
                                      fontWeight: 600,
                                      transition: 'all 0.15s',
                                    }}
                                  >
                                    {isExpanded ? '▼' : '▶'} 指标详情
                                  </span>
                                  {Object.entries(exp.metrics).map(([k, v]) => (
                                    <span key={k} style={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: 4,
                                      padding: '2px 8px',
                                      background: 'var(--card)',
                                      border: '1px solid var(--line)',
                                      borderRadius: 4,
                                      fontSize: 10,
                                    }}>
                                      <span style={{ color: 'var(--sub)' }}>{k}:</span>
                                      <span style={{ fontWeight: 600, fontFamily: 'var(--mono)' }}>
                                        {typeof v === 'number' ? v.toFixed(4) : v}
                                      </span>
                                    </span>
                                  ))}
                                </>
                              )}
                            </div>

                            {/* 展开后的详细指标卡片 */}
                            {isExpanded && hasMetrics && (
                              <div style={{
                                marginTop: 10,
                                padding: '12px',
                                background: 'var(--card)',
                                border: '1px solid var(--line)',
                                borderRadius: 8,
                                animation: 'slideDown 0.2s ease',
                              }}>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
                                  {Object.entries(exp.metrics).map(([k, v]) => (
                                    <div key={k} style={{
                                      padding: '8px',
                                      background: 'var(--bg)',
                                      borderRadius: 6,
                                      border: '1px solid var(--line)',
                                    }}>
                                      <div style={{ fontSize: 9, color: 'var(--sub)', marginBottom: 2 }}>{k}</div>
                                      <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--ink)' }}>
                                        {typeof v === 'number' ? v.toFixed(4) : v}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                                {exp.params && Object.keys(exp.params).length > 0 && (
                                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
                                    <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--sub)', marginBottom: 6 }}>参数配置</div>
                                    <div style={{ fontSize: 10, color: 'var(--ink)', fontFamily: 'var(--mono)', maxHeight: 120, overflow: 'auto' }}>
                                      {JSON.stringify(exp.params, null, 2)}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              {Object.keys(experimentsByDate).length === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--sub)', padding: 40 }}>
                  <div style={{ fontSize: 24, marginBottom: 8 }}>🧪</div>
                  <div style={{ fontSize: 13 }}>暂无实验记录</div>
                  <div style={{ fontSize: 11, marginTop: 4 }}>训练完成后自动记录，或手动点击「记录实验」</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Commits View */}
        {viewMode === 'commits' && (
          <div style={{
            width: '100%',
            height: '100%',
            overflowY: 'auto',
            padding: '16px',
          }}>
            {displayCommits.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {displayCommits.slice(0, 50).map((commit: TimelineCommit) => (
                  <div
                    key={commit.hash}
                    onClick={() => onCommitClick?.(commit)}
                    style={{
                      padding: '12px 16px',
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 12,
                    }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--blue)'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
                  >
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                      minWidth: 120,
                    }}>
                      <span style={{
                        fontSize: 10,
                        fontFamily: 'var(--mono)',
                        color: 'var(--sub)',
                        background: 'var(--card)',
                        padding: '2px 6px',
                        borderRadius: 4,
                        border: '1px solid var(--line)',
                      }}>
                        {commit.short_hash}
                      </span>
                      {commit.is_tag && (
                        <span style={{
                          fontSize: 9,
                          fontWeight: 700,
                          color: '#FF9800',
                          background: 'var(--amber-bg)',
                          padding: '1px 6px',
                          borderRadius: 3,
                        }}>
                          🏷️ {commit.tag_name}
                        </span>
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: 'var(--ink)',
                        marginBottom: 4,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {commit.message.split('\n')[0]}
                      </div>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 16,
                        fontSize: 10,
                        color: 'var(--sub)',
                      }}>
                        <span>👤 {commit.author}</span>
                        <span>🕐 {formatDate(commit.date)} {formatTime(commit.date)}</span>
                        <span>📁 {commit.files_changed} 文件</span>
                        <span style={{ color: '#00C853' }}>+{commit.lines_added}</span>
                        <span style={{ color: '#FF3D00' }}>−{commit.lines_deleted}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: 'var(--sub)', padding: 40 }}>
                暂无提交记录
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}