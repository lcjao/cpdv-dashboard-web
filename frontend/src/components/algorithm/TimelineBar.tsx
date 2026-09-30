/** TimelineBar - 底部时间轴（Git 历史 + 实验里程碑 + 训练进度） */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { fetchTimeline } from '../../lib/algorithm-api';
import type { TimelineResponse, TimelineCommit, TimelineExperiment } from '../../lib/algorithm-types';
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

interface TimelineBarProps {
  library?: string;
  height?: number;
  onCommitClick?: (commit: TimelineCommit) => void;
  onExperimentClick?: (exp: TimelineExperiment) => void;
  /** 当前训练中的实验 ID（用于在列表中高亮显示进度） */
  activeTrainExperimentId?: string;
  /** 训练进度（来自 WS，覆盖列表中对应实验的进度） */
  trainProgress?: {
    stage: string;
    message: string;
    percent: number;
    epoch?: number;
    totalEpochs?: number;
    loss?: number;
  } | null;
}

export default function TimelineBar({
  library,
  height = 220,
  onCommitClick,
  onExperimentClick,
  activeTrainExperimentId,
  trainProgress,
}: TimelineBarProps) {
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'heatmap' | 'commits' | 'experiments'>('experiments');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [localCommits, setLocalCommits] = useState<TimelineCommit[]>([]);
  const [localExperiments, setLocalExperiments] = useState<TimelineExperiment[]>([]);
  const [expandedExperiments, setExpandedExperiments] = useState<Set<string>>(new Set());
  
  // 订阅 WS 训练进度
  const wsTrainProgress = useTagProgress('train');

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchTimeline(library)
      .then(res => { if (mounted) setData(res); })
      .catch(e => mounted && setError(String(e)))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [library]);

  useEffect(() => {
    if (data) {
      setLocalCommits(data.commits ?? []);
      setLocalExperiments(data.experiments ?? []);
    }
  }, [data]);

  // 合并服务端实验 + 本地新增实验
  const displayExperiments = useMemo(() => {
    const merged = [...localExperiments];
    // 如果有活跃训练实验且不在列表中，添加到顶部
    if (activeTrainExperimentId && !merged.some(e => e.id === activeTrainExperimentId)) {
      merged.unshift({
        id: activeTrainExperimentId,
        name: 'training...',
        variant: 'multi_crack',
        date: new Date().toISOString(),
        metrics: {},
      });
    }
    return merged;
  }, [localExperiments, activeTrainExperimentId]);

  const displayCommits = localCommits.length > 0 ? localCommits : data?.commits ?? [];

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

  const handleToggleExperiment = useCallback((id: string) => {
    setExpandedExperiments(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const heatmapData = useMemo(() => {
    if (!data?.heatmap) return [];
    const today = new Date();
    const startDate = new Date(today);
    startDate.setFullYear(today.getFullYear() - 1);
    startDate.setDate(1);
    startDate.setHours(0, 0, 0, 0);

    const cells: Array<{ date: string; count: number; day: number; week: number }> = [];
    const heatmap = data.heatmap;

    for (let d = new Date(startDate); d <= today; d.setDate(d.getDate() + 1)) {
      const dateStr = formatDate(d.toISOString().split('T')[0]);
      const count = heatmap[dateStr] || 0;
      const day = d.getDay();
      const week = Math.floor((d.getTime() - startDate.getTime()) / (7 * 24 * 60 * 60 * 1000));
      cells.push({ date: dateStr, count, day, week });
    }
    return cells;
  }, [data]);

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

  // 当前显示的进度：优先使用传入的 trainProgress，其次使用 WS 进度
  const currentProgress = trainProgress ?? wsTrainProgress;

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

  // 判断某个实验是否正在训练中
  const isExperimentTraining = (expId: string) => {
    return activeTrainExperimentId === expId && currentProgress && (currentProgress.stage !== 'done' && currentProgress.stage !== 'error');
  };

  // 获取实验的进度信息
  const getExperimentProgress = (expId: string) => {
    if (isExperimentTraining(expId)) {
      return currentProgress;
    }
    return null;
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
            background: 'var(--amber-bg)',
            color: '#FF9800',
            fontSize: 14,
          }}>
            📅
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
            {displayCommits.length} 次提交 · {data?.tags?.length || 0} 个标签 · {displayExperiments.length} 个实验
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {(['heatmap', 'commits', 'experiments'] as const).map(mode => (
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
                background: viewMode === mode ? 'var(--amber)' : 'transparent',
                border: '1px solid var(--line)',
                borderRadius: 6,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {mode === 'heatmap' && '🔥 热力图'}
              {mode === 'commits' && '📝 提交'}
              {mode === 'experiments' && '🧪 实验'}
            </button>
          ))}
        </div>
      </div>

      <div style={{
        flex: 1,
        overflow: 'hidden',
        position: 'relative',
      }}>
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
                        const isTraining = isExperimentTraining(exp.id);
                        const progress = getExperimentProgress(exp.id);
                        const isExpanded = expandedExperiments.has(exp.id);
                        const hasMetrics = exp.metrics && Object.keys(exp.metrics).length > 0;

                        return (
                          <div
                            key={exp.id}
                            onClick={() => { handleToggleExperiment(exp.id); onExperimentClick?.(exp); }}
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
                            {isTraining && progress && (
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
                                {(progress as any).epoch !== undefined || (progress as any).loss !== undefined ? (
                                  <div style={{ marginTop: 6, fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                                    {(progress as any).epoch !== undefined && (progress as any).totalEpochs !== undefined && (
                                      <span>Epoch: {String((progress as any).epoch)}/{String((progress as any).totalEpochs)}</span>
                                    )}
                                    {(progress as any).loss !== undefined && (
                                      <span style={{ marginLeft: 12 }}>Loss: {Number((progress as any).loss).toFixed(4)}</span>
                                    )}
                                  </div>
                                ) : null}
                              </div>
                            )}

                            {/* 指标展开/折叠 */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 11 }}>
                              {hasMetrics && (
                                <>
                                  <span
                                    onClick={e => { e.stopPropagation(); handleToggleExperiment(exp.id); }}
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
            </div>
          </div>
        )}
      </div>
    </div>
  );
}