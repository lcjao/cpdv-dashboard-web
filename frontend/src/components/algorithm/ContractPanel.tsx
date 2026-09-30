/** ContractPanel - Protocol 契约详情面板 (TypeScript 兼容版) */

import { useState } from 'react';
import type { ContractDetail, ContractImplementation, ContractAttribute } from '../../lib/algorithm-types';

interface ContractPanelProps {
  contract: ContractDetail | null;
  onImplementationClick?: (impl: ContractImplementation) => void;
  onClose?: () => void;
}

const cellStyle: React.CSSProperties = {
  padding: '10px 12px',
  fontSize: 12,
  verticalAlign: 'top',
  borderBottom: '1px solid var(--line)',
};

export default function ContractPanel({
  contract,
  onImplementationClick,
  onClose,
}: ContractPanelProps) {
  const [showOnlyMissing, setShowOnlyMissing] = useState(false);

  if (!contract) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--sub)',
        padding: 40,
      }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>📋</div>
        <div style={{ fontSize: 14, fontWeight: 500 }}>未选择 Protocol</div>
        <div style={{ fontSize: 12, marginTop: 4 }}>从拓扑图点击 ◆ 节点，或在搜索结果中选择 Protocol 查看详情</div>
      </div>
    );
  }

  const requiredMethods = contract.required_methods || [];
  const optionalMethods = contract.optional_methods || [];
  const allMethods = [...requiredMethods.map(m => ({ ...m, _required: true })), ...optionalMethods.map(m => ({ ...m, _required: false }))];

  const compliantImpls = contract.implementations.filter(i => i.compliance?.fully_compliant).length;
  const partialImpls = contract.implementations.filter(i => i.compliance && !i.compliance.fully_compliant && i.compliance.score > 0).length;
  const nonCompliantImpls = contract.implementations.filter(i => !i.compliance || i.compliance.score === 0).length;

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--card)',
      borderRadius: 12,
      overflow: 'hidden',
      border: '1px solid var(--line)',
    }}>
      <div style={{
        padding: '16px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 16,
        background: 'linear-gradient(180deg, rgba(47,111,237,0.03) 0%, rgba(255,255,255,0) 100%)',
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
            <span style={{
              display: 'inline-flex',
              width: 36,
              height: 36,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 10,
              background: 'var(--blue-bg)',
              color: 'var(--blue)',
              fontSize: 18,
            }}>
              ◆
            </span>
            <div style={{ minWidth: 0 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                marginBottom: 4,
              }}>
                <span style={{
                  fontSize: 16,
                  fontWeight: 700,
                  color: 'var(--ink)',
                  letterSpacing: 0.3,
                }}>{contract.name}</span>
                <span style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: '#2F6FED',
                  background: 'var(--blue-bg)',
                  padding: '2px 8px',
                  borderRadius: 4,
                }}>Protocol</span>
              </div>
              <div style={{
                fontSize: 12,
                color: 'var(--sub)',
                fontFamily: 'var(--mono)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>{contract.qualified_name}</div>
            </div>
          </div>
          {contract.docstring && (
            <div style={{
              fontSize: 12,
              color: 'var(--ink)',
              lineHeight: 1.6,
              marginTop: 8,
              padding: '8px 12px',
              background: 'var(--bg)',
              borderRadius: 6,
              border: '1px solid var(--line)',
              maxWidth: 400,
            }}>
              {contract.docstring}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                padding: '6px 10px',
                fontSize: 11,
                background: 'var(--line)',
                color: 'var(--sub)',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
              }}
            >
              关闭
            </button>
          )}
        </div>
      </div>

      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--line)',
        background: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: '#00C853',
            }} />
            <span style={{ fontSize: 12, color: 'var(--ink)' }}>{compliantImpls} 完全符合</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: '#FF9800',
            }} />
            <span style={{ fontSize: 12, color: 'var(--ink)' }}>{partialImpls} 部分符合</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: '#FF3D00',
            }} />
            <span style={{ fontSize: 12, color: 'var(--ink)' }}>{nonCompliantImpls} 不符合</span>
          </div>
        </div>
        <div style={{ flex: 1 }} />
        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          fontSize: 12,
          color: 'var(--sub)',
          cursor: 'pointer',
        }}>
          <input
            type="checkbox"
            checked={showOnlyMissing}
            onChange={e => setShowOnlyMissing(e.target.checked)}
            style={{ width: 16, height: 16, accentColor: 'var(--blue)' }}
          />
          仅显示缺失项
        </label>
      </div>

      {contract.required_attributes && contract.required_attributes.length > 0 && (
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)', marginBottom: 8 }}>
            必需属性 ({contract.required_attributes.length})
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg)' }}>
                <th style={cellStyle}>属性名</th>
                <th style={cellStyle}>类型</th>
                <th style={cellStyle}>说明</th>
              </tr>
            </thead>
            <tbody>
              {contract.required_attributes.map((attr: ContractAttribute) => (
                <tr key={attr.name} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={cellStyle}>
                    <code style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{attr.name}</code>
                  </td>
                  <td style={cellStyle}>
                    <code style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{attr.type}</code>
                  </td>
                  <td style={{ ...cellStyle, color: 'var(--sub)', fontSize: 11 }}>
                    {attr.docstring || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>
            方法 ({allMethods.length}) — 必需: {requiredMethods.length} | 可选: {optionalMethods.length}
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ background: 'var(--bg)' }}>
                <th style={cellStyle}>方法签名</th>
                <th style={{ ...cellStyle, width: 80 }}>类型</th>
                <th style={cellStyle}>说明</th>
              </tr>
            </thead>
            <tbody>
              {allMethods.map((method: any) => {
                const params = method.parameters.map((p: any) =>
                  `${p.name}${p.required ? '' : '?'}: ${p.type}${p.default !== undefined ? ` = ${JSON.stringify(p.default)}` : ''}`
                ).join(', ');
                return (
                  <tr key={method.name} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={cellStyle}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      fontFamily: 'var(--mono)',
                      fontSize: 12,
                    }}>
                      {method.is_async && <span style={{color: '#FF9800', fontSize: 10}}>async</span>}
                      {method.is_staticmethod && <span style={{color: '#9C27B0', fontSize: 10}}>static</span>}
                      {method.is_classmethod && <span style={{color: '#673AB7', fontSize: 10}}>classmethod</span>}
                      {method.is_property && <span style={{color: '#00BCD4', fontSize: 10}}>property</span>}
                      <span style={{fontWeight: 600, color: method._required ? '#2F6FED' : '#FF9800'}}>{method.name}</span>
                      <span style={{color: 'var(--sub)'}}>(</span>
                      <span style={{color: 'var(--ink)'}}>{params}</span>
                      <span style={{color: 'var(--sub)'}}>)</span>
                      <span style={{color: 'var(--sub)'}}>: </span>
                      <span style={{color: 'var(--ink)'}}>{method.return_type || 'void'}</span>
                    </span>
                  </td>
                  <td style={cellStyle}>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      fontSize: 10,
                      fontWeight: 600,
                      borderRadius: 4,
                      background: method._required ? 'var(--blue-bg)' : 'var(--amber-bg)',
                      color: method._required ? '#2F6FED' : '#FF9800',
                    }}>
                      {method._required ? '必需' : '可选'}
                    </span>
                  </td>
                  <td style={cellStyle}>
                    <div style={{
                      fontSize: 11,
                      color: 'var(--ink)',
                      maxWidth: 300,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {method.docstring || '—'}
                    </div>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>
            实现对比 ({contract.implementations.length} 个实现)
          </span>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            color: 'var(--sub)',
            cursor: 'pointer',
          }}>
            <input
              type="checkbox"
              checked={showOnlyMissing}
              onChange={e => setShowOnlyMissing(e.target.checked)}
              style={{ width: 14, height: 14, accentColor: 'var(--blue)' }}
            />
            仅显示缺失
          </label>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, minWidth: 800 }}>
            <thead>
              <tr style={{ background: 'var(--bg)', position: 'sticky', top: 0, zIndex: 1 }}>
                <th style={{ ...cellStyle, width: 180 }}>实现</th>
                <th style={{ ...cellStyle, width: 80 }}>符合度</th>
                <th style={{ ...cellStyle, width: 100 }}>缺失属性</th>
                <th style={{ ...cellStyle, width: 100 }}>缺失方法</th>
                <th style={{ ...cellStyle, width: 100 }}>配置差异</th>
                <th style={cellStyle}>操作</th>
              </tr>
            </thead>
            <tbody>
              {contract.implementations
                .filter(impl => !showOnlyMissing || (impl.compliance && (!impl.compliance.fully_compliant || (impl.compliance.missing_attrs || 0) > 0 || (impl.compliance.missing_methods || 0) > 0)))
                .map((impl: ContractImplementation) => (
                  <tr key={impl.qualified_name} style={{ cursor: 'pointer' }} onClick={() => onImplementationClick?.(impl)}>
                    <td style={cellStyle}>
                      <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--ink)', fontFamily: 'var(--mono)' }}>
                        {impl.class_name}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                        {impl.backend_name} / {impl.component_type}
                      </div>
                    </td>
                    <td style={cellStyle}>
                      {impl.compliance && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{
                            display: 'inline-block',
                            width: 40,
                            height: 6,
                            background: 'var(--line)',
                            borderRadius: 3,
                            overflow: 'hidden',
                          }}>
                            <div style={{
                              width: `${impl.compliance.score * 100}%`,
                              height: '100%',
                              background: impl.compliance.fully_compliant ? '#00C853' :
                                        impl.compliance.score > 0.5 ? '#FF9800' : '#FF3D00',
                              borderRadius: 3,
                              transition: 'width 0.3s ease',
                            }} />
                          </div>
                          <span style={{
                            fontSize: 10,
                            fontWeight: 600,
                            color: impl.compliance.fully_compliant ? '#00C853' :
                                   impl.compliance.score > 0.5 ? '#FF9800' : '#FF3D00',
                          }}>
                            {impl.compliance.fully_compliant ? '✓ 完全' : `${Math.round(impl.compliance.score * 100)}%`}
                          </span>
                        </div>
                      )}
                    </td>
                    <td style={cellStyle}>
                      <span style={{
                        fontSize: 11,
                        color: (impl.compliance?.missing_attrs || 0) > 0 ? '#FF3D00' : '#00C853',
                        fontWeight: 600,
                      }}>
                        {impl.compliance?.missing_attrs || 0}
                      </span>
                    </td>
                    <td style={cellStyle}>
                      <span style={{
                        fontSize: 11,
                        color: (impl.compliance?.missing_methods || 0) > 0 ? '#FF3D00' : '#00C853',
                        fontWeight: 600,
                      }}>
                        {impl.compliance?.missing_methods || 0}
                      </span>
                    </td>
                    <td style={cellStyle}>
                      <span style={{ fontSize: 10, color: 'var(--sub)' }}>
                        {Object.keys(impl.config_schema?.properties || {}).length} 参数
                      </span>
                    </td>
                    <td style={cellStyle}>
                      <button
                        onClick={(e) => { e.stopPropagation(); onImplementationClick?.(impl); }}
                        style={{
                          padding: '4px 10px',
                          fontSize: 10,
                          fontWeight: 600,
                          background: 'var(--blue)',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 4,
                          cursor: 'pointer',
                        }}
                      >
                        详情
                      </button>
                    </td>
                  </tr>
                ))}
              {contract.implementations.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ ...cellStyle, textAlign: 'center', color: 'var(--sub)', padding: '40px' }}>
                    暂无实现
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}