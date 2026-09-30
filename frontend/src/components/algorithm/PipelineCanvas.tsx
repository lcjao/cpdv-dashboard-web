/** PipelineCanvas - 可视化流水线画布 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import type {
  PipelineNode,
  PipelineConnection,
  PipelineNodeCategory,
} from '../../lib/algorithm-types';
import { PIPELINE_NODE_CATEGORIES } from '../../lib/algorithm-types';

// 简单的 UUID 生成（避免依赖 uuid 包）
const genId = () => Math.random().toString(36).substring(2, 15) + Date.now().toString(36);

interface PipelineCanvasProps {
  nodes: PipelineNode[];
  connections: PipelineConnection[];
  selectedNodeId: string | null;
  onNodesChange: (nodes: PipelineNode[]) => void;
  onConnectionsChange: (connections: PipelineConnection[]) => void;
  onNodeSelect: (nodeId: string | null) => void;
  onNodeDoubleClick?: (node: PipelineNode) => void;
  showGrid?: boolean;
  readOnly?: boolean;
}

const NODE_WIDTH = 220;
const NODE_HEIGHT = 120;
const PORT_RADIUS = 6;
const PORT_GAP = 28;

export default function PipelineCanvas({
  nodes,
  connections,
  selectedNodeId,
  onNodesChange,
  onConnectionsChange,
  onNodeSelect,
  onNodeDoubleClick,
  showGrid = true,
  readOnly = false,
}: PipelineCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [connecting, setConnecting] = useState<{ nodeId: string; portId: string; type: 'input' | 'output' } | null>(null);
  const [connectionPreview, setConnectionPreview] = useState<{ x: number; y: number } | null>(null);
  const [draggedNode, setDraggedNode] = useState<{ nodeId: string; offsetX: number; offsetY: number } | null>(null);
  const [history, setHistory] = useState<{ nodes: PipelineNode[]; connections: PipelineConnection[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // 保存历史
  const saveHistory = useCallback((newNodes: PipelineNode[], newConnections: PipelineConnection[]) => {
    setHistory(prev => {
      const next = prev.slice(0, historyIndex + 1);
      next.push({ nodes: newNodes, connections: newConnections });
      if (next.length > 50) next.shift();
      return next;
    });
    setHistoryIndex(prev => Math.min(prev + 1, 49));
  }, [historyIndex]);

  // 撤销/重做
  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const prev = history[historyIndex - 1];
      onNodesChange(prev.nodes);
      onConnectionsChange(prev.connections);
      setHistoryIndex(i => i - 1);
    }
  }, [history, historyIndex, onNodesChange, onConnectionsChange]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const next = history[historyIndex + 1];
      onNodesChange(next.nodes);
      onConnectionsChange(next.connections);
      setHistoryIndex(i => i + 1);
    }
  }, [history, historyIndex, onNodesChange, onConnectionsChange]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) redo(); else undo();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        redo();
      }
      if (e.key === 'Delete' && selectedNodeId && !readOnly) {
        const filteredNodes = nodes.filter(n => n.id !== selectedNodeId);
        const filteredConnections = connections.filter(
          c => c.source.node_id !== selectedNodeId && c.target.node_id !== selectedNodeId
        );
        onNodesChange(filteredNodes);
        onConnectionsChange(filteredConnections);
        onNodeSelect(null);
        saveHistory(filteredNodes, filteredConnections);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodeId, nodes, connections, readOnly, undo, redo, saveHistory, onNodesChange, onConnectionsChange, onNodeSelect]);

  // 获取节点端口位置
  const getPortPosition = useCallback((
    node: PipelineNode,
    port: { id: string; type: 'input' | 'output' },
    index: number,
    total: number
  ) => {
    const nodeRect = canvasRef.current?.querySelector(`[data-node-id="${node.id}"]`)?.getBoundingClientRect();
    const canvasRect = canvasRef.current?.getBoundingClientRect();
    if (!nodeRect || !canvasRect) return { x: 0, y: 0 };

    const startY = (NODE_HEIGHT - (total - 1) * PORT_GAP) / 2;
    const y = nodeRect.top - canvasRect.top + startY + index * PORT_GAP;
    const x = port.type === 'input'
      ? nodeRect.left - canvasRect.left
      : nodeRect.right - canvasRect.left;

    return { x, y };
  }, []);

  // 处理画布拖拽平移
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target !== canvasRef.current) return;
    e.preventDefault();
    const startX = e.clientX - pan.x;
    const startY = e.clientY - pan.y;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      setPan({ x: moveEvent.clientX - startX, y: moveEvent.clientY - startY });
    };
    const handleMouseUp = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }, [pan]);

  // 缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.min(Math.max(zoom * delta, 0.2), 3);
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      setPan(prev => ({
        x: mouseX - (mouseX - prev.x) * (newZoom / zoom),
        y: mouseY - (mouseY - prev.y) * (newZoom / zoom),
      }));
    }
    setZoom(newZoom);
  }, [zoom]);

  // 开始连线
  const handlePortMouseDown = useCallback((
    e: React.MouseEvent,
    nodeId: string,
    portId: string,
    type: 'input' | 'output'
  ) => {
    e.stopPropagation();
    e.preventDefault();
    if (readOnly) return;
    setConnecting({ nodeId, portId, type });
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setConnectionPreview({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    }
  }, [readOnly]);

  // 移动时更新预览
  useEffect(() => {
    if (!connecting) return;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        setConnectionPreview({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      }
    };
    const handleMouseUp = (e: MouseEvent) => {
      if (!connecting) return;
      const target = e.target as HTMLElement;
      const targetNodeId = target.closest('[data-node-id]')?.getAttribute('data-node-id');
      const targetPortId = target.closest('[data-port-id]')?.getAttribute('data-port-id');
      const targetPortType = target.closest('[data-port-type]')?.getAttribute('data-port-type') as 'input' | 'output' | null;

      if (targetNodeId && targetPortId && targetPortType && targetNodeId !== connecting.nodeId) {
        // 类型匹配检查：output -> input
        if (connecting.type === 'output' && targetPortType === 'input') {
          const newConnection: PipelineConnection = {
            id: genId(),
            source: { node_id: connecting.nodeId, port_id: connecting.portId },
            target: { node_id: targetNodeId, port_id: targetPortId },
          };
          onConnectionsChange([...connections, newConnection]);
          saveHistory(nodes, [...connections, newConnection]);
        } else if (connecting.type === 'input' && targetPortType === 'output') {
          const newConnection: PipelineConnection = {
            id: genId(),
            source: { node_id: targetNodeId, port_id: targetPortId },
            target: { node_id: connecting.nodeId, port_id: connecting.portId },
          };
          onConnectionsChange([...connections, newConnection]);
          saveHistory(nodes, [...connections, newConnection]);
        }
      }
      setConnecting(null);
      setConnectionPreview(null);
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [connecting, connections, nodes, onConnectionsChange, saveHistory]);

  // 节点拖拽
  const handleNodeMouseDown = useCallback((e: React.MouseEvent, node: PipelineNode) => {
    if (readOnly) return;
    e.stopPropagation();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setDraggedNode({
        nodeId: node.id,
        offsetX: e.clientX - rect.left - pan.x - node.position.x * zoom,
        offsetY: e.clientY - rect.top - pan.y - node.position.y * zoom,
      });
    }
  }, [pan, zoom, readOnly]);

  useEffect(() => {
    if (!draggedNode) return;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const newX = (e.clientX - rect.left - pan.x - draggedNode.offsetX) / zoom;
        const newY = (e.clientY - rect.top - pan.y - draggedNode.offsetY) / zoom;
        const updatedNodes = nodes.map(n =>
          n.id === draggedNode.nodeId ? { ...n, position: { x: newX, y: newY } } : n
        );
        onNodesChange(updatedNodes);
      }
    };
    const handleMouseUp = () => {
      if (draggedNode) {
        saveHistory(nodes.map(n => n.id === draggedNode.nodeId ? { ...n, position: n.position } : n), connections);
      }
      setDraggedNode(null);
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [draggedNode, pan, zoom, nodes, connections, onNodesChange, saveHistory]);

  // 处理从调色板拖拽节点
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (readOnly) return;
    const templateData = e.dataTransfer.getData('application/json');
    if (!templateData) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      const x = (e.clientX - rect.left - pan.x) / zoom;
      const y = (e.clientY - rect.top - pan.y) / zoom;
      // 这里需要从外部传入 alternativeImpls 和 defaultImpl
      // 暂时在 PipelineBuilder 中处理
      void x; void y;
    }
  }, [pan, zoom, readOnly]);

  // 渲染连线
  const renderConnections = useMemo(() => {
    return connections.map(conn => {
      const sourceNode = nodes.find(n => n.id === conn.source.node_id);
      const targetNode = nodes.find(n => n.id === conn.target.node_id);
      if (!sourceNode || !targetNode) return null;

      const sourcePort = sourceNode.outputs.find(p => p.id === conn.source.port_id);
      const targetPort = targetNode.inputs.find(p => p.id === conn.target.port_id);
      if (!sourcePort || !targetPort) return null;

      const sourceIdx = sourceNode.outputs.findIndex(p => p.id === conn.source.port_id);
      const targetIdx = targetNode.inputs.findIndex(p => p.id === conn.target.port_id);

      const sourcePos = getPortPosition(sourceNode, sourcePort, sourceIdx, sourceNode.outputs.length);
      const targetPos = getPortPosition(targetNode, targetPort, targetIdx, targetNode.inputs.length);

      // 贝塞尔曲线控制点
      const dx = targetPos.x - sourcePos.x;
      const cp1x = sourcePos.x + dx * 0.5;
      const cp2x = targetPos.x - dx * 0.5;

      const path = `M ${sourcePos.x} ${sourcePos.y} C ${cp1x} ${sourcePos.y} ${cp2x} ${targetPos.y} ${targetPos.x} ${targetPos.y}`;

      return (
        <path
          key={conn.id}
          d={path}
          stroke="var(--blue)"
          strokeWidth={2}
          fill="none"
          style={{
            filter: 'drop-shadow(0 0 3px var(--blue))',
            pointerEvents: 'none',
          }}
        />
      );
    });
  }, [connections, nodes, getPortPosition]);

  // 渲染连接预览
  const renderConnectionPreview = useMemo(() => {
    if (!connecting || !connectionPreview) return null;
    const sourceNode = nodes.find(n => n.id === connecting.nodeId);
    if (!sourceNode) return null;
    const sourcePort = connecting.type === 'output'
      ? sourceNode.outputs.find(p => p.id === connecting.portId)
      : sourceNode.inputs.find(p => p.id === connecting.portId);
    if (!sourcePort) return null;

    const sourceIdx = (connecting.type === 'output' ? sourceNode.outputs : sourceNode.inputs)
      .findIndex(p => p.id === connecting.portId);
    const total = connecting.type === 'output' ? sourceNode.outputs.length : sourceNode.inputs.length;
    const sourcePos = getPortPosition(sourceNode, sourcePort, sourceIdx, total);

    const dx = connectionPreview.x - sourcePos.x;
    const cp1x = sourcePos.x + dx * 0.5;
    const cp2x = connectionPreview.x - dx * 0.5;

    const path = `M ${sourcePos.x} ${sourcePos.y} C ${cp1x} ${sourcePos.y} ${cp2x} ${connectionPreview.y} ${connectionPreview.x} ${connectionPreview.y}`;

    return (
      <path
        d={path}
        stroke="var(--amber)"
        strokeWidth={2}
        strokeDasharray="5,5"
        fill="none"
        style={{ pointerEvents: 'none' }}
      />
    );
  }, [connecting, connectionPreview, nodes, getPortPosition]);

  // 渲染节点
  const renderNodes = useMemo(() => {
    return nodes.map(node => {
      const isSelected = node.id === selectedNodeId;
      const category = PIPELINE_NODE_CATEGORIES[node.metadata.category as PipelineNodeCategory] || { label: node.metadata.category, color: '#888', icon: '📦' };

      const inputPorts = node.inputs.map((port, idx) => (
        <div
          key={port.id}
          data-port-id={port.id}
          data-port-type="input"
          onMouseDown={e => handlePortMouseDown(e, node.id, port.id, 'input')}
          style={{
            position: 'absolute',
            left: -PORT_RADIUS,
            top: (NODE_HEIGHT - (node.inputs.length - 1) * PORT_GAP) / 2 + idx * PORT_GAP - PORT_RADIUS,
            width: PORT_RADIUS * 2,
            height: PORT_RADIUS * 2,
            borderRadius: '50%',
            background: 'var(--blue)',
            border: '2px solid var(--card)',
            cursor: 'crosshair',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
          }}
          title={`${port.name} (${port.dataType})${port.required ? ' * required' : ''}`}
        >
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--card)' }} />
        </div>
      ));

      const outputPorts = node.outputs.map((port, idx) => (
        <div
          key={port.id}
          data-port-id={port.id}
          data-port-type="output"
          onMouseDown={e => handlePortMouseDown(e, node.id, port.id, 'output')}
          style={{
            position: 'absolute',
            right: -PORT_RADIUS,
            top: (NODE_HEIGHT - (node.outputs.length - 1) * PORT_GAP) / 2 + idx * PORT_GAP - PORT_RADIUS,
            width: PORT_RADIUS * 2,
            height: PORT_RADIUS * 2,
            borderRadius: '50%',
            background: 'var(--green)',
            border: '2px solid var(--card)',
            cursor: 'crosshair',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
          }}
          title={`${port.name} (${port.dataType})${port.required ? ' * required' : ''}`}
        >
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--card)' }} />
        </div>
      ));

      return (
        <div
          key={node.id}
          data-node-id={node.id}
          onMouseDown={e => handleNodeMouseDown(e, node)}
          onClick={e => { e.stopPropagation(); onNodeSelect(node.id); }}
          onDoubleClick={e => { e.stopPropagation(); onNodeDoubleClick?.(node); }}
          draggable={!readOnly}
          onDragStart={e => {
            e.dataTransfer.setData('application/json', JSON.stringify({
              template_id: node.template_id,
              type: node.type,
              name: node.name,
              label: node.label,
            }));
          }}
          style={{
            position: 'absolute',
            left: node.position.x * zoom + pan.x,
            top: node.position.y * zoom + pan.y,
            width: NODE_WIDTH * zoom,
            height: NODE_HEIGHT * zoom,
            transform: `scale(${zoom})`,
            transformOrigin: 'top left',
            pointerEvents: 'auto',
          }}
        >
          <div
            style={{
              width: NODE_WIDTH,
              height: NODE_HEIGHT,
              background: isSelected ? 'var(--blue-bg)' : 'var(--card)',
              border: `2px solid ${isSelected ? 'var(--blue)' : 'var(--line)'}`,
              borderRadius: 12,
              boxShadow: isSelected ? '0 0 0 3px var(--blue-bg)' : '0 4px 20px rgba(0,0,0,0.15)',
              display: 'flex',
              flexDirection: 'column',
              position: 'relative',
              overflow: 'visible',
              cursor: readOnly ? 'default' : 'move',
              transition: 'all 0.15s ease',
            }}
          >
            {/* 头部 */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 12px',
              background: 'linear-gradient(90deg, var(--blue-bg) 0%, transparent 100%)',
              borderBottom: '1px solid var(--line)',
              borderRadius: '10px 10px 0 0',
            }}>
              <span style={{ fontSize: 18 }}>{category.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {node.label}
                </div>
                <div style={{ fontSize: 10, color: 'var(--sub)', fontFamily: 'var(--mono)' }}>
                  {node.name}
                </div>
              </div>
              {node.selected_impl && (
                <span style={{
                  fontSize: 9,
                  fontWeight: 700,
                  color: '#fff',
                  background: 'var(--green)',
                  padding: '2px 8px',
                  borderRadius: 10,
                }}>
                  {node.selected_impl.name}
                </span>
              )}
            </div>

            {/* 描述 */}
            <div style={{
              padding: '8px 12px',
              fontSize: 11,
              color: 'var(--sub)',
              lineHeight: 1.4,
              flex: 1,
              minHeight: 40,
            }}>
              {node.description}
            </div>

            {/* 底部：端口标签 + 替换按钮 */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              borderTop: '1px solid var(--line)',
              background: 'var(--bg)',
              borderRadius: '0 0 10px 10px',
              fontSize: 10,
            }}>
              <span style={{ color: 'var(--blue)' }}>{node.inputs.length} 入</span>
              <span style={{ color: 'var(--green)' }}>{node.outputs.length} 出</span>
              {!readOnly && node.alternative_impls.length > 0 && (
                <button
                  onClick={e => { e.stopPropagation(); onNodeDoubleClick?.(node); }}
                  style={{
                    padding: '2px 8px',
                    fontSize: 10,
                    background: 'var(--line)',
                    color: 'var(--ink)',
                    border: 'none',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                >
                  替换实现
                </button>
              )}
            </div>

            {/* 端口 */}
            {inputPorts}
            {outputPorts}
          </div>
        </div>
      );
    });
  }, [nodes, selectedNodeId, zoom, pan, getPortPosition, handlePortMouseDown, handleNodeMouseDown, onNodeSelect, onNodeDoubleClick, readOnly]);

  // 网格背景
  const gridSize = 40 * zoom;

  return (
    <div
      ref={canvasRef}
      onMouseDown={handleMouseDown}
      onWheel={handleWheel}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={() => onNodeSelect(null)}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background: 'var(--bg)',
        overflow: 'hidden',
        cursor: readOnly ? 'default' : 'grab',
        touchAction: 'none',
      }}
    >
      {/* 网格 */}
      {showGrid && (
        <svg style={{ position: 'absolute', inset: 0, pointerEvents: 'none', width: '100%', height: '100%' }}>
          <defs>
            <pattern id="grid" width={gridSize} height={gridSize} patternUnits="userSpaceOnUse">
              <path d="M 0 0 L {gridSize} 0 L {gridSize} {gridSize} L 0 {gridSize} Z" fill="none" stroke="var(--line)" strokeWidth={0.5} opacity={0.3} />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      )}

      {/* 连线层 */}
      <svg style={{ position: 'absolute', inset: 0, pointerEvents: 'none', width: '100%', height: '100%' }}>
        {renderConnections}
        {renderConnectionPreview}
      </svg>

      {/* 节点层 */}
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        {renderNodes}
      </div>

      {/* 空状态提示 */}
      {nodes.length === 0 && !readOnly && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--sub)',
          pointerEvents: 'none',
          gap: 12,
        }}>
          <div style={{ fontSize: 48 }}>🔗</div>
          <div style={{ fontSize: 16, fontWeight: 500 }}>拖拽左侧节点到画布开始构建流程</div>
          <div style={{ fontSize: 12, textAlign: 'center' }}>
            支持：数据生成 → 训练 → 推理 → 评估 全流程组装<br/>
            点击节点端口可连线，点击节点可替换实现
          </div>
        </div>
      )}
    </div>
  );
}