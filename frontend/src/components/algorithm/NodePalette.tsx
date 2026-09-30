/** NodePalette - 左侧节点调色板，按模板分组展示 */

import { useState, useCallback, useMemo } from 'react';
import type { PipelineNodeCategory } from '../../lib/algorithm-types';
import { PIPELINE_NODE_CATEGORIES } from '../../lib/algorithm-types';
import { PIPELINE_TEMPLATES, NODE_ALTERNATIVE_IMPLS, DEFAULT_IMPL_BY_CATEGORY } from '../../lib/pipeline-templates';

interface NodePaletteProps {
  selectedTemplateId?: string;
  onTemplateSelect?: (templateId: string) => void;
  searchQuery?: string;
}

const CATEGORY_ORDER: PipelineNodeCategory[] = [
  'data_generator',
  'data_loader',
  'preprocessor',
  'model',
  'loss',
  'optimizer',
  'trainer',
  'evaluator',
  'postprocessor',
];

export default function NodePalette({
  selectedTemplateId,
  onTemplateSelect,
  searchQuery = '',
}: NodePaletteProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<PipelineNodeCategory>>(
    new Set(CATEGORY_ORDER)
  );
  const [expandedTemplates, setExpandedTemplates] = useState<Set<string>>(
    new Set(Object.keys(PIPELINE_TEMPLATES))
  );

  const toggleCategory = useCallback((cat: PipelineNodeCategory) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  const toggleTemplate = useCallback((templateId: string) => {
    setExpandedTemplates(prev => {
      const next = new Set(prev);
      if (next.has(templateId)) next.delete(templateId);
      else next.add(templateId);
      return next;
    });
  }, []);

  const handleNodeDragStart = useCallback((
    e: React.DragEvent,
    template: any,
    category: PipelineNodeCategory
  ) => {
    const alternativeImpls = NODE_ALTERNATIVE_IMPLS[category] || [];
    const defaultImplId = DEFAULT_IMPL_BY_CATEGORY[category];
    const defaultImpl = alternativeImpls.find(i => i.id === defaultImplId) || alternativeImpls[0] || null;

    e.dataTransfer.setData('application/json', JSON.stringify({
      template,
      category,
      alternativeImpls,
      defaultImpl,
    }));
    e.dataTransfer.effectAllowed = 'copy';
  }, []);

  // 按类别分组模板节点
  const templatesByCategory = useMemo(() => {
    const grouped: Record<PipelineNodeCategory, any[]> = {} as any;
    CATEGORY_ORDER.forEach(cat => grouped[cat] = []);

    Object.values(PIPELINE_TEMPLATES).forEach(template => {
      template.nodes.forEach(node => {
        const category = node.metadata?.category as PipelineNodeCategory;
        if (!category) return;
        if (!searchQuery || node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
            template.name.toLowerCase().includes(searchQuery.toLowerCase())) {
          grouped[category].push({ ...node, template_id: template.id, template_name: template.name });
        }
      });
    });
    return grouped;
  }, [searchQuery]);

  // 渲染类别
  const renderCategory = (cat: PipelineNodeCategory) => {
    const categoryInfo = PIPELINE_NODE_CATEGORIES[cat];
    const nodes = templatesByCategory[cat] || [];
    const isExpanded = expandedCategories.has(cat);
    const hasResults = nodes.length > 0;

    if (!hasResults && searchQuery) return null;

    return (
      <div key={cat} style={{ marginBottom: 8 }}>
        <button
          onClick={() => toggleCategory(cat)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 12px',
            background: 'var(--bg)',
            border: '1px solid var(--line)',
            borderRadius: 8,
            color: 'var(--ink)',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <span style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 0.15s' }}>
            ▸
          </span>
          <span style={{ fontSize: 16 }}>{categoryInfo.icon}</span>
          <span>{categoryInfo.label}</span>
          <span style={{
            marginLeft: 'auto',
            fontSize: 10,
            color: 'var(--sub)',
            background: 'var(--card)',
            padding: '1px 6px',
            borderRadius: 4,
          }}>
            {nodes.length}
          </span>
        </button>

        {isExpanded && (
          <div style={{ marginTop: 4, marginLeft: 8, paddingLeft: 8, borderLeft: '1px solid var(--line)' }}>
            {nodes.map(node => (
              <div
                key={`${node.template_id}-${node.template_id}`}
                draggable={true}
                onDragStart={e => handleNodeDragStart(e, node, cat)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 10px',
                  marginBottom: 4,
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: 6,
                  cursor: 'grab',
                  fontSize: 12,
                  transition: 'all 0.1s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--blue-bg)'}
                onMouseLeave={e => e.currentTarget.style.background = 'var(--card)'}
                title={`${node.template_name} › ${node.label}\n${node.description}`}
              >
                <span style={{ fontSize: 14 }}>{categoryInfo.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, color: 'var(--ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {node.label}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                    {node.template_name}
                  </div>
                </div>
                <span style={{
                  fontSize: 9,
                  color: 'var(--blue)',
                  background: 'var(--blue-bg)',
                  padding: '1px 6px',
                  borderRadius: 4,
                }}>
                  {cat}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // 渲染模板视图
  const renderTemplateView = () => {
    return Object.values(PIPELINE_TEMPLATES).map(template => {
      const isExpanded = expandedTemplates.has(template.id);
      const isSelected = selectedTemplateId === template.id;
      const filteredNodes = template.nodes.filter(node =>
        !searchQuery || node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase())
      );

      if (filteredNodes.length === 0 && searchQuery) return null;

      return (
        <div key={template.id} style={{ marginBottom: 8 }}>
          <button
            onClick={() => { toggleTemplate(template.id); onTemplateSelect?.(template.id); }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 12px',
              background: isSelected ? 'var(--blue-bg)' : 'var(--bg)',
              border: `1px solid ${isSelected ? 'var(--blue)' : 'var(--line)'}`,
              borderRadius: 8,
              color: 'var(--ink)',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <span style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 0.15s' }}>
              ▸
            </span>
            <span style={{ fontSize: 18 }}>
              {template.category === 'data_generation' && '🎲'}
              {template.category === 'training' && '🏋️'}
              {template.category === 'inference' && '🔮'}
              {template.category === 'evaluation' && '📊'}
            </span>
            <div style={{ flex: 1 }}>
              <div>{template.name}</div>
              <div style={{ fontSize: 10, color: 'var(--sub)' }}>{template.description}</div>
            </div>
            <span style={{
              fontSize: 10,
              color: 'var(--sub)',
              background: 'var(--card)',
              padding: '1px 6px',
              borderRadius: 4,
            }}>
              {filteredNodes.length} 节点
            </span>
          </button>

          {isExpanded && (
            <div style={{ marginTop: 4, marginLeft: 8, paddingLeft: 8, borderLeft: '1px solid var(--line)' }}>
              {filteredNodes.map(node => {
                const categoryInfo = PIPELINE_NODE_CATEGORIES[node.metadata.category];
                const alternativeImpls = NODE_ALTERNATIVE_IMPLS[node.metadata.category] || [];
                const defaultImplId = DEFAULT_IMPL_BY_CATEGORY[node.metadata.category];
                const defaultImpl = alternativeImpls.find(i => i.id === defaultImplId) || alternativeImpls[0] || null;

                return (
                  <div
                    key={`${template.id}-${node.template_id}`}
                    draggable={true}
                    onDragStart={e => handleNodeDragStart(e, { ...node, template_id: template.id }, node.metadata.category)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 10px',
                      marginBottom: 4,
                      background: 'var(--card)',
                      border: '1px solid var(--line)',
                      borderRadius: 6,
                      cursor: 'grab',
                      fontSize: 12,
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--blue-bg)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'var(--card)'}
                    title={`${node.label}\n${node.description}`}
                  >
                    <span style={{ fontSize: 14 }}>{categoryInfo.icon}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: 'var(--ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {node.label}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                        {node.name}
                      </div>
                    </div>
                    {defaultImpl && (
                      <span style={{
                        fontSize: 9,
                        color: 'var(--green)',
                        background: 'rgba(0,200,83,0.1)',
                        padding: '1px 6px',
                        borderRadius: 4,
                      }}>
                        默认: {defaultImpl.name}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--card)',
      borderRight: '1px solid var(--line)',
      overflow: 'hidden',
    }}>
      {/* 顶部工具栏 */}
      <div style={{
        padding: '12px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>🧩</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>节点调色板</span>
        </div>
        {searchQuery && (
          <div style={{
            fontSize: 11,
            color: 'var(--amber)',
            background: 'rgba(255,152,0,0.1)',
            padding: '4px 8px',
            borderRadius: 4,
          }}>
            筛选中: "{searchQuery}" - {Object.values(templatesByCategory).flat().length} 个节点
          </div>
        )}
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            onClick={() => setExpandedCategories(new Set(CATEGORY_ORDER))}
            style={{ flex: 1, padding: '4px 8px', fontSize: 10, background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 4, cursor: 'pointer' }}
          >
            全部展开
          </button>
          <button
            onClick={() => setExpandedCategories(new Set())}
            style={{ flex: 1, padding: '4px 8px', fontSize: 10, background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 4, cursor: 'pointer' }}
          >
            全部折叠
          </button>
        </div>
      </div>

      {/* 视图切换 */}
      <div style={{
        padding: '0 12px 8px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        gap: 4,
      }}>
        <button
          onClick={() => onTemplateSelect?.('')}
          style={{
            flex: 1,
            padding: '6px 8px',
            fontSize: 11,
            background: selectedTemplateId ? 'var(--bg)' : 'var(--blue-bg)',
            color: selectedTemplateId ? 'var(--ink)' : 'var(--blue)',
            border: `1px solid ${selectedTemplateId ? 'var(--line)' : 'var(--blue)'}`,
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          按类别
        </button>
        <button
          onClick={() => onTemplateSelect?.('__all__')}
          style={{
            flex: 1,
            padding: '6px 8px',
            fontSize: 11,
            background: selectedTemplateId === '__all__' ? 'var(--blue-bg)' : 'var(--bg)',
            color: selectedTemplateId === '__all__' ? 'var(--blue)' : 'var(--ink)',
            border: `1px solid ${selectedTemplateId === '__all__' ? 'var(--blue)' : 'var(--line)'}`,
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          按流程模板
        </button>
      </div>

      {/* 内容列表 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
        {selectedTemplateId && selectedTemplateId !== '__all__' ? (
          <div>
            {renderTemplateView()}
          </div>
        ) : (
          <div>
            {CATEGORY_ORDER.map(renderCategory)}
          </div>
        )}

        {Object.values(templatesByCategory).flat().length === 0 && !searchQuery && (
          <div style={{ textAlign: 'center', color: 'var(--sub)', padding: 40 }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
            <div>暂无可用节点</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>请先同步代码库或检查契约解析</div>
          </div>
        )}
      </div>

      {/* 底部说明 */}
      <div style={{
        padding: '12px',
        borderTop: '1px solid var(--line)',
        fontSize: 11,
        color: 'var(--sub)',
        lineHeight: 1.6,
      }}>
        <div style={{ fontWeight: 600, color: 'var(--ink)', marginBottom: 4 }}>使用提示</div>
        <div>• 拖拽节点到右侧画布</div>
        <div>• 点击节点端口连线（输出→输入）</div>
        <div>• 双击节点替换实现</div>
        <div>• Ctrl+Z 撤销 / Ctrl+Y 重做</div>
      </div>
    </div>
  );
}