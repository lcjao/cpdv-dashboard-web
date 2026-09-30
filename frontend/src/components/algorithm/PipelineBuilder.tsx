/** PipelineBuilder - 可视化流水线构建器主组件 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import PipelineCanvas from './PipelineCanvas';
import NodePalette from './NodePalette';
import NodeEditor from './NodeEditor';
import type { PipelineNode, PipelineConnection, PipelineInstance, PipelineNodeCategory } from '../../lib/algorithm-types';
import { PIPELINE_TEMPLATES, NODE_ALTERNATIVE_IMPLS, DEFAULT_IMPL_BY_CATEGORY } from '../../lib/pipeline-templates';
import { genId } from '../../lib/algorithm-types';

interface PipelineBuilderProps {
  onBack?: () => void;
  initialPipeline?: PipelineInstance;
}

export default function PipelineBuilder({ onBack, initialPipeline }: PipelineBuilderProps) {
  const [nodes, setNodes] = useState<PipelineNode[]>([]);
  const [connections, setConnections] = useState<PipelineConnection[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'category' | 'template'>('category');
  const [pipelineName, setPipelineName] = useState('我的自定义流程');
  const [pipelineDescription, setPipelineDescription] = useState('');

  // 加载初始流程
  useEffect(() => {
    if (initialPipeline) {
      setNodes(initialPipeline.nodes);
      setConnections(initialPipeline.connections);
      setPipelineName(initialPipeline.name);
      setPipelineDescription(initialPipeline.description || '');
    }
  }, [initialPipeline]);

  // 更新节点
  const handleNodeUpdate = useCallback((nodeId: string, updates: Partial<PipelineNode>) => {
    setNodes(prev => prev.map(n => n.id === nodeId ? { ...n, ...updates } : n));
  }, []);

  // 处理节点双击 - 打开编辑器
  const handleNodeDoubleClick = useCallback((node: PipelineNode) => {
    setSelectedNodeId(node.id);
  }, []);

  // 验证整个流程
  const validationErrors = useMemo(() => {
    const errors: string[] = [];

    // 检查是否有节点
    if (nodes.length === 0) {
      errors.push('流程为空，请添加节点');
      return errors;
    }

    // 检查每个节点
    nodes.forEach(node => {
      if (!node.selected_impl) {
        errors.push(`节点 "${node.label}" (${node.name}) 未选择实现`);
      }
      // 检查必填配置
      if (node.selected_impl?.config_schema) {
        Object.entries(node.selected_impl.config_schema).forEach(([key, schema]) => {
          if (schema?.required && (node.config[key] === undefined || node.config[key] === '' || node.config[key] === null)) {
            errors.push(`节点 "${node.label}" 缺少必填配置: ${key}`);
          }
        });
      }
    });

    // 检查连接完整性（可选：检查是否有孤立节点）
    const connectedNodeIds = new Set<string>();
    connections.forEach(c => {
      connectedNodeIds.add(c.source.node_id);
      connectedNodeIds.add(c.target.node_id);
    });
    nodes.forEach(node => {
      if (!connectedNodeIds.has(node.id) && nodes.length > 1) {
        errors.push(`节点 "${node.label}" 未连接到流程中`);
      }
    });

    return errors;
  }, [nodes, connections]);

  // 导出配置
  const exportPipeline = useCallback(() => {
    const instance: PipelineInstance = {
      id: genId(),
      name: pipelineName,
      description: pipelineDescription,
      template_ids: [...new Set(nodes.map(n => n.template_id))],
      nodes,
      connections,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: {
        version: '1.0.0',
        author: 'User',
        tags: ['custom', 'pipeline'],
        is_valid: validationErrors.length === 0,
        validation_errors: validationErrors,
      },
    };

    // 生成 JSON
    const json = JSON.stringify(instance, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${pipelineName.replace(/\s+/g, '_')}_pipeline.json`;
    a.click();
    URL.revokeObjectURL(url);

    // 同时生成 Python 运行脚本
    const pythonScript = generatePythonScript(instance);
    const pyBlob = new Blob([pythonScript], { type: 'text/x-python' });
    const pyUrl = URL.createObjectURL(pyBlob);
    const pyA = document.createElement('a');
    pyA.href = pyUrl;
    pyA.download = `run_${pipelineName.replace(/\s+/g, '_')}.py`;
    setTimeout(() => {
      pyA.click();
      URL.revokeObjectURL(pyUrl);
    }, 100);
  }, [nodes, connections, pipelineName, pipelineDescription, validationErrors]);

  // 生成 Python 运行脚本
  const generatePythonScript = (instance: PipelineInstance): string => {
    const lines = [
      '#!/usr/bin/env python',
      '# -*- coding: utf-8 -*-',
      `"""${instance.name} - 自动生成的流水线运行脚本""`,
      `生成时间: ${instance.created_at}`,
      `描述: ${instance.description}`,
      `"""\n`,
      'import sys',
      'import json',
      'from pathlib import Path',
      '',
      '# 添加项目路径',
      'PROJECT_ROOT = Path(__file__).parent.parent.parent',
      'sys.path.insert(0, str(PROJECT_ROOT))',
      '',
      'from backend_framework.composition.pipeline_builder import PipelineBuilder, build_pipeline_from_config',
      '',
      'def main():',
      '    # 加载流程配置',
      `    config = ${JSON.stringify(instance, null, 4).replace(/\n/g, '\n    ')}`,
      '',
      '    # 构建并运行流程',
      '    try:',
      '        data_loader, model, loss_fn, optimizer, trainer, evaluator = build_pipeline_from_config(config)',
      '        print("✅ 流程构建成功")',
      '        print(f"数据加载器: {type(data_loader).__name__}")',
      '        print(f"模型: {type(model).__name__}")',
      '        print(f"损失函数: {type(loss_fn).__name__}")',
      '        print(f"优化器: {type(optimizer).__name__}")',
      '        print(f"训练器: {type(trainer).__name__}")',
      '        print(f"评估器: {type(evaluator).__name__}")',
      '',
      '        # 执行训练（示例）',
      '        # result = trainer.train(model, train_loader, val_loader, loss_fn, optimizer, config.get("trainer_config", {}))',
      '        # print(f"训练完成: {result}")',
      '',
      '    except Exception as e:',
      '        print(f"❌ 流程执行失败: {e}")',
      '        import traceback',
      '        traceback.print_exc()',
      '        return 1',
      '    return 0',
      '',
      'if __name__ == "__main__":',
      '    sys.exit(main())',
    ];
    return lines.join('\n');
  };

  // 从模板快速创建
  const createFromTemplate = useCallback((templateId: string) => {
    const template = PIPELINE_TEMPLATES[templateId];
    if (!template) return;

    // 清空当前流程
    setNodes([]);
    setConnections([]);
    setSelectedNodeId(null);

    // 计算起始位置
    const startX = 100;
    const startY = 100;
    const spacingX = 280;
    const spacingY = 160;

    // 添加模板节点
    const newNodes: PipelineNode[] = [];
    template.nodes.forEach((nodeTemplate, idx) => {
      const category = nodeTemplate.metadata.category;
      const alternativeImpls = NODE_ALTERNATIVE_IMPLS[category] || [];
      const defaultImplId = DEFAULT_IMPL_BY_CATEGORY[category as PipelineNodeCategory];
      const defaultImpl = alternativeImpls.find(i => i.id === defaultImplId) || alternativeImpls[0] || null;

      const col = idx % 3;
      const row = Math.floor(idx / 3);
      const newNode: PipelineNode = {
        ...nodeTemplate,
        id: genId(),
        template_id: templateId,
        position: {
          x: startX + col * spacingX,
          y: startY + row * spacingY,
        },
        selected_impl: defaultImpl || null,
        alternative_impls: alternativeImpls || [],
        config: defaultImpl?.default_config || {},
      };
      newNodes.push(newNode);
    });

    // 添加连接
    const newConnections: PipelineConnection[] = template.connections.map((conn) => {
      // 需要映射到新的节点 ID
      // 这里简化：按顺序匹配
      return { ...conn, id: genId() };
    });

    setNodes(newNodes);
    setConnections(newConnections);
    setPipelineName(template.name);
    setPipelineDescription(template.description);
  }, []);

  // 当前选中的节点
  const selectedNode = useMemo(() => nodes.find(n => n.id === selectedNodeId) || null, [nodes, selectedNodeId]);

  // 布局计算
  const leftWidth = 300;
  const rightWidth = 380;
  const centerWidth = `calc(100% - ${leftWidth + rightWidth}px)`;

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      overflow: 'hidden',
      fontFamily: 'inherit',
    }}>
      {/* 顶栏 */}
      <div style={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        background: 'var(--card)',
        borderBottom: '1px solid var(--line)',
        gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button
            onClick={onBack}
            style={{
              padding: '7px 14px',
              fontSize: 11,
              fontWeight: 700,
              background: 'var(--line)',
              color: 'var(--ink)',
              border: '1px solid var(--line)',
              borderRadius: 8,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--blue)'; e.currentTarget.style.color = '#fff'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--line)'; e.currentTarget.style.color = 'var(--ink)'; }}
          >
            ← 返回算法看板
          </button>
          <span style={{
            display: 'inline-flex',
            width: 32,
            height: 32,
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 8,
            background: 'var(--purple-bg, var(--blue-bg))',
            color: 'var(--purple, var(--blue))',
            fontSize: 16,
          }}>
            🔗
          </span>
          <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>
            流水线构建器
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* 流程名称 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="text"
              value={pipelineName}
              onChange={e => setPipelineName(e.target.value)}
              placeholder="流程名称"
              style={{
                padding: '6px 12px',
                fontSize: 13,
                background: 'var(--bg)',
                border: '1px solid var(--line)',
                borderRadius: 6,
                color: 'var(--ink)',
                minWidth: 180,
              }}
            />
          </div>

          {/* 搜索 */}
          <div style={{ position: 'relative', width: 200 }}>
            <input
              type="text"
              placeholder="搜索节点... (⌘K)"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 12px',
                paddingRight: 32,
                fontSize: 12,
                background: 'var(--bg)',
                border: '1px solid var(--line)',
                borderRadius: 6,
                color: 'var(--ink)',
              }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  position: 'absolute',
                  right: 8,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  padding: '2px 6px',
                  fontSize: 11,
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--sub)',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            )}
          </div>

          {/* 视图切换 */}
          <div style={{ display: 'flex', gap: 4, background: 'var(--bg)', padding: 4, borderRadius: 6, border: '1px solid var(--line)' }}>
            <button
              onClick={() => setViewMode('category')}
              style={{
                padding: '6px 12px',
                fontSize: 11,
                background: viewMode === 'category' ? 'var(--blue)' : 'transparent',
                color: viewMode === 'category' ? '#fff' : 'var(--ink)',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              按类别
            </button>
            <button
              onClick={() => setViewMode('template')}
              style={{
                padding: '6px 12px',
                fontSize: 11,
                background: viewMode === 'template' ? 'var(--blue)' : 'transparent',
                color: viewMode === 'template' ? '#fff' : 'var(--ink)',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              按模板
            </button>
          </div>

          {/* 快速创建按钮 */}
          <div style={{ display: 'flex', gap: 4 }}>
            {Object.entries(PIPELINE_TEMPLATES).map(([id, tmpl]) => (
              <button
                key={id}
                onClick={() => createFromTemplate(id)}
                title={`创建 ${tmpl.name} (${tmpl.nodes.length} 个节点)}`}
                style={{
                  padding: '6px 10px',
                  fontSize: 11,
                  background: 'var(--bg)',
                  color: 'var(--ink)',
                  border: '1px solid var(--line)',
                  borderRadius: 6,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {tmpl.category === 'data_generation' && '🎲 数据生成'}
                {tmpl.category === 'training' && '🏋️ 训练'}
                {tmpl.category === 'inference' && '🔮 推理'}
                {tmpl.category === 'evaluation' && '📊 评估'}
              </button>
            ))}
          </div>

          {/* 导出按钮 */}
          <button
            onClick={exportPipeline}
            disabled={nodes.length === 0}
            style={{
              padding: '8px 16px',
              fontSize: 13,
              fontWeight: 600,
              background: nodes.length === 0 ? 'var(--line)' : 'var(--purple, var(--blue))',
              color: nodes.length === 0 ? 'var(--sub)' : '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: nodes.length === 0 ? 'not-allowed' : 'pointer',
              opacity: nodes.length === 0 ? 0.6 : 1,
            }}
          >
            💾 导出流程
          </button>

          {/* 验证状态 */}
          {validationErrors.length > 0 && (
            <span style={{
              padding: '6px 12px',
              fontSize: 11,
              fontWeight: 600,
              background: 'rgba(255,61,0,0.1)',
              color: '#FF3D00',
              border: '1px solid rgba(255,61,0,0.3)',
              borderRadius: 6,
            }}>
              ⚠️ {validationErrors.length} 个问题
            </span>
          )}
        </div>
      </div>

      {/* 主布局 */}
      <div style={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',
      }}>
        {/* 左侧：节点调色板 */}
        <div style={{
          width: leftWidth,
          minWidth: leftWidth,
          maxWidth: leftWidth,
          borderRight: '1px solid var(--line)',
          background: 'var(--card)',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <NodePalette
            selectedTemplateId={viewMode === 'template' ? selectedTemplateId : undefined}
            onTemplateSelect={setSelectedTemplateId}
            searchQuery={searchQuery}
          />
        </div>

        {/* 中间：画布 */}
        <div style={{
          width: centerWidth,
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}>
          <PipelineCanvas
            nodes={nodes}
            connections={connections}
            selectedNodeId={selectedNodeId}
            onNodesChange={setNodes}
            onConnectionsChange={setConnections}
            onNodeSelect={setSelectedNodeId}
            onNodeDoubleClick={handleNodeDoubleClick}
            showGrid={true}
            readOnly={false}
          />
        </div>

        {/* 右侧：节点编辑器 */}
        <div style={{
          width: rightWidth,
          minWidth: rightWidth,
          maxWidth: rightWidth,
          borderLeft: '1px solid var(--line)',
          background: 'var(--card)',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <NodeEditor
            node={selectedNode}
            onNodeUpdate={handleNodeUpdate}
            onClose={() => setSelectedNodeId(null)}
          />
        </div>
      </div>
    </div>
  );
}