/** DiffView - 版本语义对比视图 */

import { useState } from 'react';
import type { DiffResponse } from '../../lib/algorithm-types';

interface DiffViewProps {
  diff: DiffResponse | null;
  baseName: string;
  targetName: string;
  onClose?: () => void;
}

type Dimension = 'all' | 'architecture' | 'loss' | 'trainer' | 'config';

const DIMENSION_LABELS: Record<Dimension, string> = {
  all: '全部',
  architecture: '模型架构',
  loss: '损失函数',
  trainer: '训练器',
  config: '配置参数',
};

const DIFF_COLORS = {
  added: '#00C853',
  removed: '#FF3D00',
  modified: '#FF9800',
  same: '#90A4AE',
};

function ConfigDiffRow({ key, baseVal, targetVal, type }: {
  key: string;
  baseVal: any;
  targetVal: any;
  type: 'added' | 'removed' | 'modified' | 'same';
}) {
  const formatValue = (v: any) => {
    if (v === undefined || v === null) return '—';
    if (typeof v === 'object') return JSON.stringify(v, null, 2);
    return String(v);
  };

  return (
    <tr style={{ borderBottom: '1px solid var(--line)' }}>
      <td style={cellStyle}>
        <code style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{key}</code>
      </td>
      <td style={cellStyle}>
        <pre style={preStyle}>{formatValue(baseVal)}</pre>
      </td>
      <td style={cellStyle}>
        <pre style={preStyle}>{formatValue(targetVal)}</pre>
      </td>
      <td style={cellStyle}>
        <span style={{
          display: 'inline-block',
          padding: '2px 8px',
          fontSize: 10,
          fontWeight: 600,
          borderRadius: 4,
          background: type === 'added' ? '#00C85320' : type === 'removed' ? '#FF3D0020' : type === 'modified' ? '#FF980020' : 'var(--line)',
          color: DIFF_COLORS[type],
        }}>
          {type === 'added' && '新增'}
          {type === 'removed' && '删除'}
          {type === 'modified' && '修改'}
          {type === 'same' && '相同'}
        </span>
      </td>
    </tr>
  );
}

const cellStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: 11,
  verticalAlign: 'top',
  borderBottom: '1px solid var(--line)',
};

const preStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 11,
  fontFamily: 'var(--mono)',
  color: 'var(--ink)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  maxHeight: 120,
  overflow: 'auto',
};

export default function DiffView({
  diff,
  baseName,
  targetName,
  onClose,
}: DiffViewProps) {
  const [selectedDimension, setSelectedDimension] = useState<Dimension>('all');

  if (!diff) {
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
        <div style={{ fontSize: 32, marginBottom: 12 }}>⚖️</div>
        <div style={{ fontSize: 14, fontWeight: 500 }}>请选择两个版本进行对比</div>
        <div style={{ fontSize: 12, marginTop: 4 }}>从导航栏选择基准版本和目标版本</div>
      </div>
    );
  }

  const dimensions = Object.keys(diff.diff) as Dimension[];

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
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        background: 'linear-gradient(180deg, rgba(47,111,237,0.03) 0%, rgba(255,255,255,0) 100%)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span style={{
            display: 'inline-flex',
            width: 36,
            height: 36,
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 10,
            background: 'var(--amber-bg)',
            color: '#FF9800',
            fontSize: 18,
          }}>
            ⚖️
          </span>
          <div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 4,
            }}>
              <span style={{
                fontSize: 16,
                fontWeight: 700,
                color: 'var(--ink)',
              }}>版本对比</span>
              <span style={{
                fontSize: 10,
                fontWeight: 600,
                color: '#FF9800',
                background: 'var(--amber-bg)',
                padding: '2px 8px',
                borderRadius: 4,
              }}>
                {DIMENSION_LABELS[selectedDimension] || '全部'}
              </span>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              fontSize: 12,
              color: 'var(--sub)',
              fontFamily: 'var(--mono)',
            }}>
              <span style={{ color: '#FF3D00' }}>基准: {baseName}</span>
              <span>→</span>
              <span style={{ color: '#00C853' }}>目标: {targetName}</span>
            </div>
          </div>
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
        padding: '0 16px 12px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        flexWrap: 'wrap',
      }}>
        {(['all', 'architecture', 'loss', 'trainer', 'config'] as Dimension[]).map(dim => (
          <button
            key={dim}
            onClick={() => setSelectedDimension(dim)}
            disabled={!dimensions.includes(dim)}
            style={{
              padding: '8px 14px',
              fontSize: 12,
              fontWeight: selectedDimension === dim ? 600 : 400,
              color: selectedDimension === dim ? '#fff' : 'var(--ink)',
              background: selectedDimension === dim ? 'var(--amber)' : 'transparent',
              border: '1px solid var(--line)',
              borderRadius: 6,
              cursor: dimensions.includes(dim) ? 'pointer' : 'not-allowed',
              opacity: dimensions.includes(dim) ? 1 : 0.4,
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {DIMENSION_LABELS[dim]}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
        {dimensions.includes(selectedDimension) && diff.diff[selectedDimension] ? (
          <>
            {Object.entries(diff.diff[selectedDimension] as any).map(([compType, compDiff]: any) => {
              const configDiff = (compDiff.config_diff ?? {}) as any;
              return (
                <div key={compType} style={{ marginBottom: 20 }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: 8,
                    padding: '8px 12px',
                    background: 'var(--bg)',
                    borderRadius: 6,
                    border: '1px solid var(--line)',
                  }}>
                    <span style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: 'var(--ink)',
                      textTransform: 'capitalize',
                    }}>
                      {compType}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 11, color: 'var(--sub)' }}>
                      <span style={{ color: '#00C853' }}>➕ {compDiff.only_in_target.length} 新增</span>
                      <span style={{ color: '#FF3D00' }}>➖ {compDiff.only_in_base.length} 删除</span>
                      <span style={{ color: '#FF9800' }}>🔄 {compDiff.common.length} 共同</span>
                    </div>
                  </div>

                  <div style={{ overflowX: 'auto', marginTop: 8 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, minWidth: 600 }}>
                      <thead>
                        <tr style={{ background: 'var(--bg)', position: 'sticky', top: 0, zIndex: 1 }}>
                          <th style={cellStyle}>配置项</th>
                          <th style={cellStyle}>基准版 ({baseName})</th>
                          <th style={cellStyle}>目标版 ({targetName})</th>
                          <th style={{ ...cellStyle, width: 100 }}>状态</th>
                        </tr>
                      </thead>
                      <tbody>
                        {compDiff.only_in_base.map((key: string) => (
                          <ConfigDiffRow
                            key={`removed-${compType}-${key}`}
                            baseVal={configDiff[key]?.base}
                            targetVal={undefined}
                            type="removed"
                          />
                        ))}
                        {compDiff.only_in_target.map((key: string) => (
                          <ConfigDiffRow
                            key={`added-${compType}-${key}`}
                            baseVal={undefined}
                            targetVal={configDiff[key]?.target}
                            type="added"
                          />
                        ))}
                        {compDiff.common.map((key: string) => {
                          const baseVal = configDiff[key]?.base;
                          const targetVal = configDiff[key]?.target;
                          const isModified = JSON.stringify(baseVal) !== JSON.stringify(targetVal);
                          return (
                            <ConfigDiffRow
                              key={`common-${compType}-${key}`}
                              baseVal={baseVal}
                              targetVal={targetVal}
                              type={isModified ? 'modified' : 'same'}
                            />
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </>
        ) : null}
      </div>
    </div>
  );
}