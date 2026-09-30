/** NodeEditor - 右侧节点配置面板：替换实现、修改参数、验证 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import type { PipelineNode, PipelineNodeImpl, PipelineNodeConfig } from '../../lib/algorithm-types';
import { PIPELINE_NODE_CATEGORIES } from '../../lib/algorithm-types';

interface NodeEditorProps {
  node: PipelineNode | null;
  onNodeUpdate: (nodeId: string, updates: Partial<PipelineNode>) => void;
  onClose: () => void;
}

function ConfigField({ key, schema, value, onChange, path = '' }: {
  key: string;
  schema: any;
  value: any;
  onChange: (path: string, value: any) => void;
  path?: string;
}) {
  const fullPath = path ? `${path}.${key}` : key;
  const type = schema?.type || 'string';
  const defaultVal = schema?.default;

  switch (type) {
    case 'boolean':
      return (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={value ?? defaultVal ?? false}
            onChange={e => onChange(fullPath, e.target.checked)}
            style={{ width: 16, height: 16, accentColor: 'var(--blue)' }}
          />
          <span style={{ fontSize: 12, color: 'var(--ink)' }}>{key}</span>
        </label>
      );
    case 'integer':
    case 'number':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 120 }}>
          <label style={{ fontSize: 11, color: 'var(--sub)' }}>{key}</label>
          <input
            type="number"
            value={value ?? defaultVal ?? ''}
            onChange={e => onChange(fullPath, type === 'integer' ? parseInt(e.target.value) || 0 : parseFloat(e.target.value) || 0)}
            step={type === 'integer' ? 1 : 0.001}
            style={{
              padding: '6px 10px',
              fontSize: 12,
              background: 'var(--bg)',
              border: '1px solid var(--line)',
              borderRadius: 4,
              color: 'var(--ink)',
              fontFamily: 'var(--mono)',
            }}
          />
        </div>
      );
    case 'array':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 150 }}>
          <label style={{ fontSize: 11, color: 'var(--sub)' }}>{key}</label>
          <input
            type="text"
            value={Array.isArray(value) ? value.join(', ') : (value || defaultVal || []).join(', ')}
            onChange={e => onChange(fullPath, e.target.value.split(',').map(v => v.trim()).filter(Boolean))}
            placeholder="逗号分隔"
            style={{
              padding: '6px 10px',
              fontSize: 11,
              background: 'var(--bg)',
              border: '1px solid var(--line)',
              borderRadius: 4,
              color: 'var(--ink)',
              fontFamily: 'var(--mono)',
            }}
          />
        </div>
      );
    case 'string':
    default:
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 150 }}>
          <label style={{ fontSize: 11, color: 'var(--sub)' }}>{key}</label>
          <input
            type="text"
            value={value ?? defaultVal ?? ''}
            onChange={e => onChange(fullPath, e.target.value)}
            placeholder={schema?.default ? `默认: ${schema.default}` : ''}
            style={{
              padding: '6px 10px',
              fontSize: 12,
              background: 'var(--bg)',
              border: '1px solid var(--line)',
              borderRadius: 4,
              color: 'var(--ink)',
            }}
          />
        </div>
      );
  }
}

export default function NodeEditor({ node, onNodeUpdate, onClose }: NodeEditorProps) {
  const [activeTab, setActiveTab] = useState<'config' | 'impl' | 'ports' | 'validation'>('config');
  const [localConfig, setLocalConfig] = useState<PipelineNodeConfig>({});
  const [searchImpl, setSearchImpl] = useState('');

  // 同步节点配置
  useEffect(() => {
    if (node) {
      setLocalConfig({ ...node.config });
    }
  }, [node]);

  const handleConfigChange = useCallback((path: string, value: any) => {
    if (!node) return;
    setLocalConfig(prev => {
      const next = { ...prev };
      const keys = path.split('.');
      let curr: any = next;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!curr[keys[i]]) curr[keys[i]] = {};
        curr = curr[keys[i]];
      }
      curr[keys[keys.length - 1]] = value;
      return next;
    });
  }, [node]);

  const saveConfig = useCallback(() => {
    if (node) {
      onNodeUpdate(node.id, { config: localConfig });
    }
  }, [node, localConfig, onNodeUpdate]);

  const handleImplChange = useCallback((impl: PipelineNodeImpl | null) => {
    if (!node) return;
    const newConfig = impl?.default_config || {};
    onNodeUpdate(node.id, {
      selected_impl: impl,
      config: newConfig,
    });
    setLocalConfig(newConfig);
  }, [node, onNodeUpdate]);

  if (!node) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--sub)',
        padding: 40,
      }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>🔧</div>
        <div style={{ fontSize: 16, fontWeight: 500 }}>未选择节点</div>
        <div style={{ fontSize: 12, textAlign: 'center', marginTop: 4 }}>
          在画布中点击或双击节点查看配置
        </div>
      </div>
    );
  }

  const categoryInfo = PIPELINE_NODE_CATEGORIES[node.metadata.category] || { label: node.metadata.category, color: '#888', icon: '📦' };
  const alternativeImpls = node.alternative_impls;
  const filteredImpls = alternativeImpls.filter(impl =>
    impl.name.toLowerCase().includes(searchImpl.toLowerCase()) ||
    impl.description.toLowerCase().includes(searchImpl.toLowerCase())
  );

  // 验证节点
  const validationErrors = useMemo(() => {
    const errors: string[] = [];
    if (!node.selected_impl) {
      errors.push('⚠️ 未选择实现，请在"实现"标签页选择');
    }
    // 检查必填配置
    if (node.selected_impl?.config_schema) {
      Object.entries(node.selected_impl.config_schema).forEach(([key, schema]) => {
        if (schema?.required && (localConfig[key] === undefined || localConfig[key] === '' || localConfig[key] === null)) {
          errors.push(`⚠️ 配置缺失: ${key} (必填)`);
        }
      });
    }
    // 检查连接
    return errors;
  }, [node, localConfig]);

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--card)',
      borderLeft: '1px solid var(--line)',
      overflow: 'hidden',
    }}>
      {/* 头部 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        background: 'var(--bg)',
        borderBottom: '1px solid var(--line)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            background: categoryInfo.color + '20',
            color: categoryInfo.color,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
          }}>
            {categoryInfo.icon}
          </span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>{node.label}</div>
            <div style={{ fontSize: 11, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
              {node.name} • {node.id.slice(0, 8)}
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

      {/* 标签页 */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--line)',
        background: 'var(--bg)',
        padding: '0 8px',
      }}>
        {[
          { id: 'config', label: '⚙️ 配置', badge: Object.keys(node.selected_impl?.config_schema || {}).length },
          { id: 'impl', label: '🔄 实现', badge: alternativeImpls.length },
          { id: 'ports', label: '🔌 端口', badge: node.inputs.length + node.outputs.length },
          { id: 'validation', label: '✅ 验证', badge: validationErrors.length, alert: validationErrors.length > 0 },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              padding: '8px 16px',
              fontSize: 11,
              fontWeight: 600,
              background: activeTab === tab.id ? 'var(--card)' : 'transparent',
              color: activeTab === tab.id ? 'var(--blue)' : 'var(--sub)',
              border: 'none',
              borderBottom: `2px solid ${activeTab === tab.id ? 'var(--blue)' : 'transparent'}`,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              borderRadius: '6px 6px 0 0',
              marginBottom: -1,
            }}
          >
            {tab.label}
            {tab.badge > 0 && (
              <span style={{
                fontSize: 9,
                fontWeight: 700,
                padding: '1px 5px',
                borderRadius: 10,
                background: activeTab === tab.id
                  ? (tab.alert ? 'var(--red)' : 'var(--blue)')
                  : (tab.alert ? 'var(--red)' : 'var(--line)'),
                color: activeTab === tab.id ? '#fff' : (tab.alert ? '#fff' : 'var(--sub)'),
              }}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>

        {/* 配置标签页 */}
        {activeTab === 'config' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>运行时配置</span>
              <button
                onClick={saveConfig}
                disabled={JSON.stringify(localConfig) === JSON.stringify(node.config)}
                style={{
                  padding: '6px 14px',
                  fontSize: 11,
                  fontWeight: 600,
                  background: JSON.stringify(localConfig) === JSON.stringify(node.config) ? 'var(--line)' : 'var(--blue)',
                  color: JSON.stringify(localConfig) === JSON.stringify(node.config) ? 'var(--sub)' : '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: JSON.stringify(localConfig) === JSON.stringify(node.config) ? 'not-allowed' : 'pointer',
                }}
              >
                保存配置
              </button>
            </div>

            {node.selected_impl?.config_schema ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Object.entries(node.selected_impl.config_schema).map(([key, schema]) => (
                  <ConfigField
                    key={key}
                    schema={schema}
                    value={localConfig[key]}
                    onChange={handleConfigChange}
                  />
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--sub)', fontSize: 12, textAlign: 'center', padding: 40 }}>
                该实现无可配置参数
              </div>
            )}

            {JSON.stringify(localConfig) !== JSON.stringify(node.config) && (
              <div style={{
                marginTop: 8,
                padding: '10px 12px',
                background: 'rgba(255,152,0,0.1)',
                border: '1px solid rgba(255,152,0,0.3)',
                borderRadius: 6,
                fontSize: 11,
                color: 'var(--amber)',
              }}>
                ⚠️ 配置已修改，点击"保存配置"应用更改
              </div>
            )}
          </div>
        )}

        {/* 实现替换标签页 */}
        {activeTab === 'impl' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>可选实现</span>
              <input
                type="text"
                placeholder="搜索实现..."
                value={searchImpl}
                onChange={e => setSearchImpl(e.target.value)}
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  fontSize: 11,
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 6,
                  color: 'var(--ink)',
                }}
              />
            </div>

            {node.selected_impl && (
              <div style={{
                padding: '12px',
                background: 'rgba(0,200,83,0.08)',
                border: '1px solid rgba(0,200,83,0.3)',
                borderRadius: 8,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ fontWeight: 700, color: '#00C853', fontSize: 12 }}>✅ 当前选中</span>
                  <span style={{ fontSize: 11, color: 'var(--sub)' }}>合规分: {((node.selected_impl.compliance_score ?? 1) * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>{node.selected_impl.name}</div>
                <div style={{ fontSize: 11, color: 'var(--sub)', marginTop: 2 }}>{node.selected_impl.description}</div>
                <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)', marginTop: 4 }}>
                  {node.selected_impl.qualified_name}
                </div>
                <div style={{ fontSize: 10, color: 'var(--sub)', marginTop: 4 }}>
                  协议: {node.selected_impl.protocol || '无'}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 400, overflowY: 'auto' }}>
              {filteredImpls.map(impl => (
                <button
                  key={impl.id}
                  onClick={() => handleImplChange(impl)}
                  disabled={node.selected_impl?.id === impl.id}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    padding: '10px 12px',
                    background: node.selected_impl?.id === impl.id ? 'var(--blue-bg)' : 'var(--bg)',
                    border: `1px solid ${node.selected_impl?.id === impl.id ? 'var(--blue)' : 'var(--line)'}`,
                    borderRadius: 8,
                    cursor: node.selected_impl?.id === impl.id ? 'not-allowed' : 'pointer',
                    textAlign: 'left',
                    width: '100%',
                    transition: 'all 0.1s',
                  }}
                  onMouseEnter={e => { if (node.selected_impl?.id !== impl.id) e.currentTarget.style.background = 'var(--hover-bg, var(--blue-bg))'; }}
                  onMouseLeave={e => { if (node.selected_impl?.id !== impl.id) e.currentTarget.style.background = 'var(--bg)'; }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{impl.name}</span>
                      {(impl.compliance_score || 1) < 1 && (
                        <span style={{
                          fontSize: 9,
                          color: 'var(--amber)',
                          background: 'rgba(255,152,0,0.1)',
                          padding: '1px 5px',
                          borderRadius: 3,
                        }}>
                          合规 {(impl.compliance_score! * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--sub)', marginBottom: 2 }}>{impl.description}</div>
                    <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                      {impl.qualified_name}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--sub)', marginTop: 2 }}>
                      协议: {impl.protocol || '无'} | 文件: {impl.file_path.split('/').pop()}
                    </div>
                  </div>
                  {node.selected_impl?.id !== impl.id && (
                    <span style={{
                      padding: '4px 10px',
                      fontSize: 11,
                      fontWeight: 600,
                      background: 'var(--blue)',
                      color: '#fff',
                      borderRadius: 4,
                    }}>
                      选择
                    </span>
                  )}
                </button>
              ))}
              {filteredImpls.length === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--sub)', padding: 20 }}>
                  {searchImpl ? '无匹配实现' : '该节点类别暂无可选实现'}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 端口标签页 */}
        {activeTab === 'ports' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--blue)', marginBottom: 8 }}>
                📥 输入端口 ({node.inputs.length})
              </div>
              {node.inputs.length === 0 ? (
                <div style={{ color: 'var(--sub)', fontSize: 11, padding: '8px 12px', background: 'var(--bg)', borderRadius: 6 }}>
                  无输入端口（源节点）
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {node.inputs.map((port) => (
                    <div
                      key={port.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '8px 12px',
                        background: 'var(--bg)',
                        border: '1px solid var(--line)',
                        borderRadius: 6,
                        fontSize: 11,
                      }}
                    >
                      <div style={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: 'var(--blue)',
                        flexShrink: 0,
                      }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, color: 'var(--ink)' }}>{port.name}</div>
                        <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                          {port.dataType} {port.required ? '• 必填' : '• 可选'}
                        </div>
                        {port.description && <div style={{ fontSize: 10, color: 'var(--sub)', marginTop: 2 }}>{port.description}</div>}
                      </div>
                      <span style={{
                        fontSize: 9,
                        color: 'var(--blue)',
                        background: 'var(--blue-bg)',
                        padding: '1px 6px',
                        borderRadius: 3,
                      }}>
                        {port.id}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--green)', marginBottom: 8 }}>
                📤 输出端口 ({node.outputs.length})
              </div>
              {node.outputs.length === 0 ? (
                <div style={{ color: 'var(--sub)', fontSize: 11, padding: '8px 12px', background: 'var(--bg)', borderRadius: 6 }}>
                  无输出端口（汇节点）
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {node.outputs.map((port) => (
                    <div
                      key={port.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '8px 12px',
                        background: 'var(--bg)',
                        border: '1px solid var(--line)',
                        borderRadius: 6,
                        fontSize: 11,
                      }}
                    >
                      <div style={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: 'var(--green)',
                        flexShrink: 0,
                      }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, color: 'var(--ink)' }}>{port.name}</div>
                        <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                          {port.dataType} {port.required ? '• 必填' : '• 可选'}
                        </div>
                        {port.description && <div style={{ fontSize: 10, color: 'var(--sub)', marginTop: 2 }}>{port.description}</div>}
                      </div>
                      <span style={{
                        fontSize: 9,
                        color: 'var(--green)',
                        background: 'rgba(0,200,83,0.1)',
                        padding: '1px 6px',
                        borderRadius: 3,
                      }}>
                        {port.id}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 验证标签页 */}
        {activeTab === 'validation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {validationErrors.length > 0 ? (
              <div style={{
                padding: '12px',
                background: 'rgba(255,61,0,0.08)',
                border: '1px solid rgba(255,61,0,0.3)',
                borderRadius: 8,
              }}>
                <div style={{ fontWeight: 700, color: '#FF3D00', fontSize: 12, marginBottom: 8 }}>
                  ❌ 发现 {validationErrors.length} 个问题
                </div>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 11, color: 'var(--sub)', lineHeight: 1.8 }}>
                  {validationErrors.map((err, i) => <li key={i}>{err}</li>)}
                </ul>
              </div>
            ) : (
              <div style={{
                padding: '12px',
                background: 'rgba(0,200,83,0.08)',
                border: '1px solid rgba(0,200,83,0.3)',
                borderRadius: 8,
                textAlign: 'center',
              }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>✅</div>
                <div style={{ fontWeight: 700, color: '#00C853', fontSize: 13 }}>验证通过</div>
                <div style={{ fontSize: 11, color: 'var(--sub)', marginTop: 4 }}>
                  节点配置完整，可以连接执行
                </div>
              </div>
            )}

            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)', marginTop: 8 }}>节点元信息</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--bg)', borderRadius: 4 }}>
                <span style={{ color: 'var(--sub)' }}>分类</span>
                <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{categoryInfo.label}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--bg)', borderRadius: 4 }}>
                <span style={{ color: 'var(--sub)' }}>阶段</span>
                <span style={{ color: 'var(--ink)', fontWeight: 500, textTransform: 'capitalize' }}>{node.type.replace('_', ' ')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--bg)', borderRadius: 4 }}>
                <span style={{ color: 'var(--sub)' }}>必需</span>
                <span style={{ color: node.metadata.is_required ? '#00C853' : 'var(--amber)' }}>
                  {node.metadata.is_required ? '是' : '否'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--bg)', borderRadius: 4 }}>
                <span style={{ color: 'var(--sub)' }}>执行顺序</span>
                <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{node.metadata.order}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--bg)', borderRadius: 4 }}>
                <span style={{ color: 'var(--sub)' }}>标签</span>
                <span style={{ color: 'var(--ink)', fontWeight: 500 }}>
                  {node.metadata.tags.join(', ') || '无'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}