/** ExperimentRecordPanel - 实验记录面板（支持Obsidian文档管理） */

import { useState, useEffect, useCallback } from 'react';
import { 
  fetchExperimentRecords, 
  recordExperiment, 
  RecordExperimentRequest, 
  ExperimentRecord,
  scanExperimentDocs,
  importExperimentDocs,
  createExperiment,
  ExperimentDoc,
} from '../../lib/algorithm-api';

interface ExperimentRecordPanelProps {
  /** 当前选中的协议/桥梁 */
  protocol?: string;
  /** 关闭回调 */
  onClose: () => void;
  /** 切换到时间轴实验视图 */
  onViewHistory: () => void;
  /** Pipeline 执行结果回调 */
  onPipelineResult?: (result: { experiment_id?: string; message?: string; timestamp?: string } | null) => void;
}

const DEFAULT_EXPERIMENT_DIR = 'D:\\Documents\\Obsidian\\O1\\桥梁健康系统\\Resource\\R4_实验文档';

export default function ExperimentRecordPanel({
  protocol,
  onClose,
  onViewHistory,
}: ExperimentRecordPanelProps) {
  const [records, setRecords] = useState<ExperimentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [showRecordModal, setShowRecordModal] = useState(false);
  const [recordNote, setRecordNote] = useState('');
  const [recordType, setRecordType] = useState<'train' | 'evaluate' | 'predict' | 'compare' | 'multi_crack_train' | 'pipeline_run' | 'import' | 'create'>('train');
  const [recording, setRecording] = useState(false);
  
  // 实验文档相关状态
  const [experimentDocs, setExperimentDocs] = useState<ExperimentDoc[]>([]);
  const [experimentDir, setExperimentDir] = useState(DEFAULT_EXPERIMENT_DIR);
  const [showDocPanel, setShowDocPanel] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [newExpName, setNewExpName] = useState('');
  const [newExpPurpose, setNewExpPurpose] = useState('');
  const [creating, setCreating] = useState(false);
  
  // Pipeline execution result display
  const [lastPipelineResult] = useState<{
    experiment_id?: string;
    message?: string;
    timestamp?: string;
  } | null>(null);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchExperimentRecords(50, 0);
      setRecords(res.records);
      setTotal(res.total);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const scanDocs = useCallback(async (dir?: string) => {
    setScanning(true);
    try {
      const docs = await scanExperimentDocs(dir || experimentDir);
      setExperimentDocs(docs);
      if (!dir) setExperimentDir(docs.length > 0 ? DEFAULT_EXPERIMENT_DIR : '');
    } catch (e) {
      console.error('Scan failed:', e);
    } finally {
      setScanning(false);
    }
  }, [experimentDir]);

  useEffect(() => {
    loadRecords();
    scanDocs();
  }, [loadRecords, scanDocs]);
  
  // Watch for pipeline results from parent
  useEffect(() => {
    // This is handled via onPipelineResult prop if provided
    // For now, we rely on auto-refresh after pipeline completion
  }, []);

  const handleRecord = async () => {
    if (!recordNote.trim()) return;
    setRecording(true);
    try {
      const req: RecordExperimentRequest = {
        note: recordNote,
        type: recordType,
        protocol,
        params: {},
        metrics: {},
      };
      await recordExperiment(req);
      setShowRecordModal(false);
      setRecordNote('');
      loadRecords();
    } catch (e) {
      setError(`记录失败: ${e}`);
    } finally {
      setRecording(false);
    }
  };

  const handleImport = async () => {
    setScanning(true);
    try {
      const result = await importExperimentDocs();
      setExperimentDocs(result.experiments);
      loadRecords();
    } catch (e) {
      setError(`导入失败: ${e}`);
    } finally {
      setScanning(false);
    }
  };

  const handleCreate = async () => {
    if (!newExpName.trim()) return;
    setCreating(true);
    try {
      await createExperiment({
        name: newExpName,
        purpose: newExpPurpose,
        experiment_dir: experimentDir,
        template: 'basic',
      });
      setNewExpName('');
      setNewExpPurpose('');
      setShowDocPanel(false);
      await scanDocs();
      await loadRecords();
    } catch (e) {
      setError(`创建失败: ${e}`);
    } finally {
      setCreating(false);
    }
  };


  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      train: '🏋️',
      evaluate: '📊',
      predict: '🔮',
      compare: '⚖️',
      multi_crack_train: '🧠',
      pipeline_run: '⚙️',
      import: '📥',
      create: '➕',
    };
    return icons[type] || '📝';
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      train: '#FF9800',
      evaluate: '#2F6FED',
      predict: '#9C27B0',
      compare: '#FF9800',
      multi_crack_train: '#EC4899',
      pipeline_run: '#06B6D4',
      import: '#10B981',
      create: '#8B5CF6',
    };
    return colors[type] || '#90A4AE';
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
            {/* Pipeline Result Display */}
      {lastPipelineResult && (
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--line)',
          background: 'linear-gradient(180deg, rgba(5,150,105,0.05) 0%, rgba(255,255,255,0) 100%)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              display: 'inline-flex',
              width: 28,
              height: 28,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 6,
              background: 'var(--green-bg)',
              color: 'var(--green)',
              fontSize: 14,
            }}>
              ✓
            </span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>
                Pipeline 执行完成
              </div>
              <div style={{ fontSize: 10, color: 'var(--sub)', marginTop: 2 }}>
                {lastPipelineResult.experiment_id && `实验文档: ${lastPipelineResult.experiment_id}`}
                {lastPipelineResult.message && ` · ${lastPipelineResult.message}`}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'linear-gradient(180deg, rgba(47,111,237,0.03) 0%, rgba(255,255,255,0) 100%)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            display: 'inline-flex',
            width: 32,
            height: 32,
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 8,
            background: 'var(--amber-bg)',
            color: '#FF9800',
            fontSize: 16,
          }}>
            📝
          </span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>
              实验记录
            </div>
            <div style={{ fontSize: 10, color: 'var(--sub)' }}>
              {experimentDocs.length} 个文档 · 共 {total} 条记录
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={() => setShowDocPanel(!showDocPanel)}
            style={{
              padding: '4px 10px',
              fontSize: 11,
              background: showDocPanel ? 'var(--blue-bg)' : 'transparent',
              color: showDocPanel ? 'var(--blue)' : 'var(--sub)',
              border: `1px solid ${showDocPanel ? 'var(--blue)' : 'var(--line)'}`,
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            📁 文档
          </button>
          <button
            onClick={onViewHistory}
            style={{
              padding: '4px 10px',
              fontSize: 11,
              background: 'var(--blue-bg)',
              color: 'var(--blue)',
              border: '1px solid var(--blue)',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            查看历史
          </button>
          <button
            onClick={() => setShowRecordModal(true)}
            style={{
              padding: '4px 10px',
              fontSize: 11,
              background: 'var(--amber)',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            记录实验
          </button>
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
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
        {/* 文档管理面板 */}
        {showDocPanel && (
          <div style={{
            marginBottom: 16,
            padding: 12,
            background: 'var(--bg)',
            borderRadius: 8,
            border: '1px solid var(--line)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>📁 实验文档管理</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => scanDocs()}
                  disabled={scanning}
                  style={{
                    padding: '4px 10px',
                    fontSize: 11,
                    background: 'var(--line)',
                    color: 'var(--ink)',
                    border: 'none',
                    borderRadius: 4,
                    cursor: scanning ? 'not-allowed' : 'pointer',
                  }}
                >
                  {scanning ? '扫描中...' : '刷新文档'}
                </button>
                <button
                  onClick={handleImport}
                  disabled={scanning}
                  style={{
                    padding: '4px 10px',
                    fontSize: 11,
                    background: 'var(--green)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 4,
                    cursor: scanning ? 'not-allowed' : 'pointer',
                  }}
                >
                  导入Obsidian
                </button>
              </div>
            </div>
            
            {/* 文档目录显示 */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: 'var(--sub)', marginBottom: 4 }}>当前目录</div>
              <div style={{ 
                fontSize: 11, 
                color: 'var(--ink)', 
                padding: '6px 10px',
                background: 'var(--card)',
                borderRadius: 4,
                fontFamily: 'monospace',
                wordBreak: 'break-all',
              }}>
                {experimentDir || '未设置'}
              </div>
            </div>

            {/* 新建实验表单 */}
            <div style={{ 
              padding: 12, 
              background: 'var(--card)', 
              borderRadius: 6,
              border: '1px dashed var(--line)',
              marginTop: 8,
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 8 }}>新建实验</div>
              <div style={{ marginBottom: 8 }}>
                <input
                  type="text"
                  placeholder="实验名称"
                  value={newExpName}
                  onChange={e => setNewExpName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 10px',
                    fontSize: 12,
                    background: 'var(--bg)',
                    border: '1px solid var(--line)',
                    borderRadius: 4,
                    color: 'var(--ink)',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <div style={{ marginBottom: 8 }}>
                <textarea
                  placeholder="实验目的（可选）"
                  value={newExpPurpose}
                  onChange={e => setNewExpPurpose(e.target.value)}
                  rows={2}
                  style={{
                    width: '100%',
                    padding: '6px 10px',
                    fontSize: 12,
                    background: 'var(--bg)',
                    border: '1px solid var(--line)',
                    borderRadius: 4,
                    color: 'var(--ink)',
                    resize: 'vertical',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <button
                onClick={handleCreate}
                disabled={creating || !newExpName.trim()}
                style={{
                  padding: '6px 12px',
                  fontSize: 11,
                  background: creating ? 'var(--line)' : 'var(--purple)',
                  color: creating ? 'var(--sub)' : '#fff',
                  border: 'none',
                  borderRadius: 4,
                  cursor: creating ? 'not-allowed' : 'pointer',
                }}
              >
                {creating ? '创建中...' : '创建实验'}
              </button>
            </div>

            {/* 文档列表 */}
            {experimentDocs.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 8 }}>
                  已发现 {experimentDocs.length} 个实验文档
                </div>
                {experimentDocs.map(doc => (
                  <div
                    key={doc.id}
                    style={{
                      padding: '8px 10px',
                      background: 'var(--card)',
                      borderRadius: 4,
                      border: '1px solid var(--line)',
                      marginBottom: 6,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>{doc.id}</span>
                      <span style={{ fontSize: 10, color: 'var(--sub)' }}>{formatDate(doc.date)}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--ink)', marginTop: 2 }}>{doc.name}</div>
                    {Object.keys(doc.metrics).length > 0 && (
                      <div style={{ fontSize: 10, color: 'var(--blue)', marginTop: 4, fontFamily: 'monospace' }}>
                        {Object.entries(doc.metrics).map(([k, v]) => `${k}:${(v as number).toFixed(4)}`).join(' | ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 主要记录区域 */}
        {/* Latest Record Card */}
        {(() => {
          const protocolRecords = protocol 
            ? records.filter(r => r.protocol === protocol || r.bridge === protocol)
            : records;
          return protocolRecords[0] || null;
        })() && (
          <div style={{
            marginBottom: 16,
            padding: '16px',
            background: 'linear-gradient(135deg, rgba(47,111,237,0.05) 0%, rgba(255,152,0,0.05) 100%)',
            border: '1px solid var(--line)',
            borderRadius: 10,
          }}>
            {(() => {
              const latest = protocol
                ? records.find(r => r.protocol === protocol || r.bridge === protocol) || records[0]
                : records[0];
              if (!latest) return null;
              return (
                <>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{
                        display: 'inline-flex',
                        width: 36,
                        height: 36,
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: 10,
                        background: `${getTypeColor(latest.type)}20`,
                        color: getTypeColor(latest.type),
                        fontSize: 16,
                      }}>
                        {getTypeIcon(latest.type)}
                      </span>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
                          {latest.name || latest.type}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                          {latest.timestamp}
                        </div>
                      </div>
                    </div>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '4px 10px',
                      fontSize: 10,
                      fontWeight: 700,
                      borderRadius: 4,
                      background: 'rgba(0,200,83,0.15)',
                      color: '#00C853',
                      textTransform: 'uppercase',
                    }}>
                      ✅ 最新
                    </span>
                  </div>

                  {latest.note && (
                    <div style={{ marginBottom: 12, padding: '8px 12px', background: 'var(--bg)', borderRadius: 6, border: '1px solid var(--line)' }}>
                      <div style={{ fontSize: 10, color: 'var(--sub)', marginBottom: 4 }}>备注</div>
                      <div style={{ fontSize: 12, color: 'var(--ink)', lineHeight: 1.5 }}>{latest.note}</div>
                    </div>
                  )}

                  {(latest.metrics && Object.keys(latest.metrics).length > 0) && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: 8 }}>
                      {Object.entries(latest.metrics).map(([k, v]) => (
                        <div key={k} style={{
                          padding: '10px',
                          background: 'var(--bg)',
                          borderRadius: 6,
                          border: '1px solid var(--line)',
                          textAlign: 'center',
                        }}>
                          <div style={{ fontSize: 9, color: 'var(--sub)', marginBottom: 2, textTransform: 'uppercase' }}>{k}</div>
                          <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--ink)' }}>
                            {typeof v === 'number' ? (v as number).toFixed(4) : v}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}

        {/* Records List */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--sub)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              历史记录 ({records.length})
            </span>
            {records.length > 0 && (
              <button
                onClick={onViewHistory}
                style={{
                  padding: '4px 10px',
                  fontSize: 10,
                  background: 'transparent',
                  color: 'var(--blue)',
                  border: '1px solid var(--blue)',
                  borderRadius: 4,
                  cursor: 'pointer',
                }}
              >
                查看全部 →
              </button>
            )}
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', color: 'var(--sub)', padding: 20 }}>加载中...</div>
          ) : error ? (
            <div style={{ textAlign: 'center', color: 'var(--red)', padding: 20 }}>加载失败: {error}</div>
          ) : records.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--sub)', padding: 40 }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>📝</div>
              <div style={{ fontSize: 13 }}>暂无实验记录</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>点击「记录实验」创建第一条记录</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {records.slice(0, 10).map((record) => (
                <div
                  key={record.id}
                  style={{
                    padding: '10px 12px',
                    background: 'var(--bg)',
                    border: '1px solid var(--line)',
                    borderRadius: 6,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--blue)'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--line)'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 14 }}>{getTypeIcon(record.type)}</span>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink)' }}>
                          {record.name || record.type}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                          {record.timestamp}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {(record.metrics?.f1 !== undefined || record.metrics?.position_mae !== undefined) && (
                        <span style={{
                          fontSize: 10,
                          fontFamily: 'var(--mono)',
                          color: 'var(--ink)',
                        }}>
                          {record.metrics.f1 !== undefined ? `F1: ${record.metrics.f1.toFixed(3)}` : ''}
                          {record.metrics.position_mae !== undefined ? ` · PosMAE: ${record.metrics.position_mae.toFixed(3)}` : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  {record.note && (
                    <div style={{ marginTop: 4, fontSize: 10, color: 'var(--sub)', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {record.note}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Record Modal */}
      {showRecordModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }} onClick={() => setShowRecordModal(false)}>
          <div style={{
            background: 'var(--card)',
            borderRadius: 12,
            border: '1px solid var(--line)',
            padding: '20px',
            width: '100%',
            maxWidth: 480,
            boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>记录实验</span>
              <button onClick={() => setShowRecordModal(false)} style={{ background: 'none', border: 'none', fontSize: 20, color: 'var(--sub)', cursor: 'pointer' }}>×</button>
            </div>
            
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 6, textTransform: 'uppercase' }}>
                实验类型
              </label>
              <select
                value={recordType}
                onChange={e => setRecordType(e.target.value as any)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  fontSize: 12,
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 6,
                  color: 'var(--ink)',
                }}
              >
                <option value="train">🏋️ 训练</option>
                <option value="evaluate">📊 评估</option>
                <option value="predict">🔮 预测</option>
                <option value="compare">⚖️ 对比</option>
                <option value="multi_crack_train">🧠 多裂缝训练</option>
                <option value="pipeline_run">⚙️ Pipeline运行</option>
                <option value="import">📥 导入Obsidian文档</option>
                <option value="create">➕ 新建实验</option>
              </select>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--sub)', marginBottom: 6, textTransform: 'uppercase' }}>
                备注说明
              </label>
              <textarea
                value={recordNote}
                onChange={e => setRecordNote(e.target.value)}
                placeholder="例如: 多裂缝v2 F1=0.89, 数据增强后效果提升"
                rows={3}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  fontSize: 12,
                  fontFamily: 'inherit',
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 6,
                  color: 'var(--ink)',
                  resize: 'vertical',
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowRecordModal(false)}
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
                取消
              </button>
              <button
                onClick={handleRecord}
                disabled={recording || !recordNote.trim()}
                style={{
                  padding: '8px 16px',
                  fontSize: 12,
                  fontWeight: 600,
                  background: recording ? 'var(--line)' : 'var(--amber)',
                  color: recording ? 'var(--sub)' : '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: recording ? 'not-allowed' : 'pointer',
                }}
              >
                {recording ? '记录中...' : '确认记录'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
