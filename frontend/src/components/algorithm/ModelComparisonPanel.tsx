/** ModelComparisonPanel - 模型对比面板 */

import { useState, useCallback } from 'react';
import { compareModelsApi, ModelComparisonRequest, ModelComparisonResult } from '../../lib/algorithm-api';

interface ModelComparisonPanelProps {
  /** 当前选中的协议 */
  protocol?: string;
  /** 关闭回调 */
  onClose: () => void;
  /** 记录对比结果回调 */
  onRecordComparison?: (result: ModelComparisonResult) => void;
}

export default function ModelComparisonPanel({
  protocol,
  onClose,
  onRecordComparison,
}: ModelComparisonPanelProps) {
  const [modelA, setModelA] = useState('');
  const [modelB, setModelB] = useState('');
  const [bridgeA, setBridgeA] = useState('');
  const [bridgeB, setBridgeB] = useState('');
  const [result, setResult] = useState<ModelComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = useCallback(async () => {
    if (!modelA || !modelB) {
      setError('请选择两个模型进行对比');
      return;
    }
    if (modelA === modelB) {
      setError('不能对比同一个模型');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const req: ModelComparisonRequest = {
        modelA,
        modelB,
        bridgeA: bridgeA || undefined,
        bridgeB: bridgeB || undefined,
      };
      const res = await compareModelsApi(req);
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [modelA, modelB, bridgeA, bridgeB]);

  const handleRecord = useCallback(() => {
    if (result && onRecordComparison) {
      onRecordComparison(result);
    }
  }, [result, onRecordComparison]);

  const getWinnerBadge = (winner: 'a' | 'b' | 'tie') => {
    if (winner === 'a') return { label: '模型 A 胜出', color: '#00C853', bg: 'rgba(0,200,83,0.15)' };
    if (winner === 'b') return { label: '模型 B 胜出', color: '#00C853', bg: 'rgba(0,200,83,0.15)' };
    return { label: '平局', color: '#FF9800', bg: 'rgba(255,152,0,0.15)' };
  };

  const formatMetricDiff = (diff: number, higherIsBetter: boolean = true) => {
    const sign = diff > 0 ? '+' : '';
    const color = (diff > 0) === higherIsBetter ? '#00C853' : (diff < 0 ? '#FF3D00' : 'var(--sub)');
    return <span style={{ color, fontWeight: 600 }}>{sign}{diff.toFixed(4)}</span>;
  };

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--card)',
      borderRadius: 12,
      border: '1px solid var(--line)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'linear-gradient(180deg, rgba(156,39,176,0.03) 0%, rgba(255,255,255,0) 100%)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            display: 'inline-flex',
            width: 32,
            height: 32,
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 8,
            background: 'var(--purple-bg, rgba(156,39,176,0.15))',
            color: '#9C27B0',
            fontSize: 16,
          }}>
            ⚖️
          </span>
          <div>
            <div style={{
              fontSize: 14,
              fontWeight: 700,
              color: 'var(--ink)',
            }}>模型对比</div>
            <div style={{ fontSize: 10, color: 'var(--sub)' }}>
              选择两个模型对比指标与配置差异
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            padding: '4px 10px',
            fontSize: 11,
            background: 'transparent',
            border: '1px solid var(--line)',
            borderRadius: 6,
            color: 'var(--sub)',
            cursor: 'pointer',
          }}
        >
          关闭
        </button>
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '16px',
      }}>
        {/* Model Selectors */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {/* Model A */}
            <div style={{
              padding: '16px',
              background: 'rgba(47,111,237,0.05)',
              border: '1px solid rgba(47,111,237,0.2)',
              borderRadius: 10,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{
                  display: 'inline-flex',
                  width: 24,
                  height: 24,
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 6,
                  background: 'var(--blue-bg)',
                  color: 'var(--blue)',
                  fontSize: 12,
                  fontWeight: 700,
                }}>
                  A
                </span>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>基准模型</span>
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 10, color: 'var(--sub)', marginBottom: 4, textTransform: 'uppercase' }}>
                  模型路径
                </label>
                <input
                  type="text"
                  value={modelA}
                  onChange={e => setModelA(e.target.value)}
                  placeholder="outputs/models/multi_crack_dual_retrained.pth"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    fontSize: 11,
                    fontFamily: 'var(--mono)',
                    background: 'var(--bg)',
                    border: '1px solid var(--line)',
                    borderRadius: 6,
                    color: 'var(--ink)',
                  }}
                />
              </div>
              {protocol && (
                <div>
                  <label style={{ display: 'block', fontSize: 10, color: 'var(--sub)', marginBottom: 4, textTransform: 'uppercase' }}>
                    桥梁 (可选)
                  </label>
                  <input
                    type="text"
                    value={bridgeA}
                    onChange={e => setBridgeA(e.target.value)}
                    placeholder="bridge_01"
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      fontSize: 11,
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 6,
                      color: 'var(--ink)',
                    }}
                  />
                </div>
              )}
            </div>

            {/* Model B */}
            <div style={{
              padding: '16px',
              background: 'rgba(0,200,83,0.05)',
              border: '1px solid rgba(0,200,83,0.2)',
              borderRadius: 10,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{
                  display: 'inline-flex',
                  width: 24,
                  height: 24,
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 6,
                  background: 'rgba(0,200,83,0.15)',
                  color: '#00C853',
                  fontSize: 12,
                  fontWeight: 700,
                }}>
                  B
                </span>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>目标模型</span>
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 10, color: 'var(--sub)', marginBottom: 4, textTransform: 'uppercase' }}>
                  模型路径
                </label>
                <input
                  type="text"
                  value={modelB}
                  onChange={e => setModelB(e.target.value)}
                  placeholder="outputs/models/multi_crack_dual_v2.pth"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    fontSize: 11,
                    fontFamily: 'var(--mono)',
                    background: 'var(--bg)',
                    border: '1px solid var(--line)',
                    borderRadius: 6,
                    color: 'var(--ink)',
                  }}
                />
              </div>
              {protocol && (
                <div>
                  <label style={{ display: 'block', fontSize: 10, color: 'var(--sub)', marginBottom: 4, textTransform: 'uppercase' }}>
                    桥梁 (可选)
                  </label>
                  <input
                    type="text"
                    value={bridgeB}
                    onChange={e => setBridgeB(e.target.value)}
                    placeholder="bridge_02"
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      fontSize: 11,
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                      borderRadius: 6,
                      color: 'var(--ink)',
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
            <button
              onClick={handleCompare}
              disabled={loading || !modelA || !modelB}
              style={{
                padding: '10px 20px',
                fontSize: 12,
                fontWeight: 600,
                background: loading ? 'var(--line)' : '#9C27B0',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? '对比中...' : '开始对比'}
            </button>
          </div>

          {error && (
            <div style={{ marginTop: 12, padding: '10px', background: 'rgba(255,61,0,0.1)', border: '1px solid rgba(255,61,0,0.3)', borderRadius: 6, color: '#FF3D00', fontSize: 11 }}>
              {error}
            </div>
          )}
        </div>

        {/* Comparison Result */}
        {result && (
          <div style={{ borderTop: '1px solid var(--line)', paddingTop: 20 }}>
            {/* Winner Badge */}
            <div style={{ marginBottom: 20 }}>
              {(() => {
                const wb = getWinnerBadge(result.comparison.winner);
                return (
                  <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 16px',
                    background: wb.bg,
                    border: `1px solid ${wb.color}`,
                    borderRadius: 8,
                  }}>
                    <span style={{ fontSize: 16 }}>{result.comparison.winner === 'tie' ? '⚖️' : '🏆'}</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: wb.color }}>{wb.label}</span>
                    <span style={{ fontSize: 11, color: 'var(--sub)' }}>
                      {result.comparison.summary}
                    </span>
                  </div>
                );
              })()}
            </div>

            {/* Metrics Comparison Table */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                核心指标对比
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, minWidth: 500 }}>
                  <thead>
                    <tr style={{ background: 'var(--bg)', borderBottom: '1px solid var(--line)' }}>
                      <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--ink)' }}>指标</th>
                      <th style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, color: 'var(--blue)', width: 120 }}>模型 A</th>
                      <th style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, color: '#00C853', width: 120 }}>模型 B</th>
                      <th style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, color: 'var(--ink)', width: 100 }}>差值 (B-A)</th>
                      <th style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, color: 'var(--sub)', width: 80 }}>优势</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { key: 'f1', label: 'F1 Score', higherBetter: true },
                      { key: 'precision', label: 'Precision', higherBetter: true },
                      { key: 'recall', label: 'Recall', higherBetter: true },
                      { key: 'position_mae', label: 'Position MAE', higherBetter: false },
                      { key: 'depth_mae', label: 'Depth MAE', higherBetter: false },
                      { key: 'matches', label: 'Matches', higherBetter: true },
                    ].map(({ key, label, higherBetter }) => {
                      const valA = result.modelA.metrics[key];
                      const valB = result.modelB.metrics[key];
                      const diff = result.comparison[`${key}_diff` as keyof typeof result.comparison] as number;
                      
                      if (valA === undefined && valB === undefined) return null;

                      return (
                        <tr key={key} style={{ borderBottom: '1px solid var(--line)' }}>
                          <td style={{ padding: '10px 12px', color: 'var(--ink)' }}>{label}</td>
                          <td style={{ padding: '10px 12px', textAlign: 'center', fontFamily: 'var(--mono)', fontWeight: 600, color: valA !== undefined ? 'var(--blue)' : 'var(--sub)' }}>
                            {valA !== undefined ? valA.toFixed(4) : '—'}
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'center', fontFamily: 'var(--mono)', fontWeight: 600, color: valB !== undefined ? '#00C853' : 'var(--sub)' }}>
                            {valB !== undefined ? valB.toFixed(4) : '—'}
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'center', fontFamily: 'var(--mono)', fontWeight: 600 }}>
                            {diff !== undefined ? formatMetricDiff(diff, higherBetter) : '—'}
                          </td>
                          <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                            {valA !== undefined && valB !== undefined && (
                              <span style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                                padding: '2px 8px',
                                fontSize: 9,
                                fontWeight: 700,
                                borderRadius: 4,
                                background: (diff > 0) === higherBetter ? 'rgba(0,200,83,0.15)' : diff < 0 ? 'rgba(255,61,0,0.15)' : 'var(--line)',
                                color: (diff > 0) === higherBetter ? '#00C853' : diff < 0 ? '#FF3D00' : 'var(--sub)',
                              }}>
                                {(diff > 0) === higherBetter ? 'B ✓' : diff < 0 ? 'A ✓' : '—'}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Config Comparison */}
            {(Object.keys(result.modelA.config).length > 0 || Object.keys(result.modelB.config).length > 0) && (
              <details style={{ marginBottom: 20 }}>
                <summary style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', cursor: 'pointer', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  配置参数对比
                </summary>
                <div style={{ marginTop: 12, maxHeight: 300, overflow: 'auto' }}>
                  <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--ink)', background: 'var(--bg)', padding: '12px', borderRadius: 6, border: '1px solid var(--line)', whiteSpace: 'pre-wrap' }}>
                    {(() => {
                      const allKeys = new Set([...Object.keys(result.modelA.config), ...Object.keys(result.modelB.config)]);
                      return Array.from(allKeys).map(k => {
                        const a = result.modelA.config[k];
                        const b = result.modelB.config[k];
                        const same = JSON.stringify(a) === JSON.stringify(b);
                        return `${k}: ${same ? '✓' : '✗'} A=${JSON.stringify(a)} B=${JSON.stringify(b)}`;
                      }).join('\n');
                    })()}
                  </div>
                </div>
              </details>
            )}

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', paddingTop: 16, borderTop: '1px solid var(--line)' }}>
              <button
                onClick={handleRecord}
                style={{
                  padding: '8px 16px',
                  fontSize: 12,
                  fontWeight: 600,
                  background: 'var(--amber)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
              >
                记录对比结果
              </button>
              <button
                onClick={() => setResult(null)}
                style={{
                  padding: '8px 16px',
                  fontSize: 12,
                  background: 'var(--line)',
                  color: 'var(--ink)',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
              >
                重新对比
              </button>
            </div>
          </div>
        )}

        {!result && !loading && !error && (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--sub)',
            padding: 40,
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚖️</div>
            <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>模型对比</div>
            <div style={{ fontSize: 13, textAlign: 'center', lineHeight: 1.6, color: 'var(--sub)' }}>
              输入两个模型路径，点击「开始对比」查看详细指标差异
            </div>
          </div>
        )}
      </div>
    </div>
  );
}