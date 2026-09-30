/** TopologyCanvas - 算法代码拓扑图组件 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import type { TopologyNode, TopologyEdge, TopologyData } from '../../lib/algorithm-types';

cytoscape.use(coseBilkent);

const NODE_TYPE_COLORS: Record<string, string> = {
  protocol: '#2F6FED',
  class: '#00C853',
  function: '#FFD600',
  method: '#FF9800',
  variable: '#9C27B0',
  import: '#607D8B',
  unknown: '#757575',
};

const NODE_TYPE_SHAPES: Record<string, string> = {
  protocol: 'diamond',
  class: 'rectangle',
  function: 'ellipse',
  method: 'round-rectangle',
  variable: 'triangle',
  import: 'hexagon',
  unknown: 'ellipse',
};

interface TopologyCanvasProps {
  data: TopologyData | null;
  onNodeClick?: (node: TopologyNode) => void;
  onNodeHover?: (node: TopologyNode | null) => void;
  layout?: 'cose-bilkent' | 'cose' | 'dagre' | 'concentric';
  fitOnLoad?: boolean;
  minZoom?: number;
  maxZoom?: number;
  style?: React.CSSProperties;
  className?: string;
}

export default function TopologyCanvas({
  data,
  onNodeClick,
  onNodeHover,
  layout = 'cose-bilkent',
  fitOnLoad = true,
  minZoom = 0.1,
  maxZoom = 4,
  style,
  className,
}: TopologyCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [ready, setReady] = useState(false);
  const [layoutRunning, setLayoutRunning] = useState(false);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);

  const cyStyle = useMemo<any[]>(() => [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'font-size': '10px',
        'font-family': 'var(--mono)',
        'color': '#1a1a2e',
        'text-wrap': 'wrap',
        'text-max-width': '80px',
        'text-valign': 'center',
        'text-halign': 'center',
        'background-color': (ele: any) => NODE_TYPE_COLORS[ele.data('nodeType')] || NODE_TYPE_COLORS.unknown,
        'shape': (ele: any) => NODE_TYPE_SHAPES[ele.data('nodeType')] || NODE_TYPE_SHAPES.unknown,
        'width': (ele: any) => {
          const type = ele.data('nodeType');
          return type === 'protocol' ? 60 : type === 'class' ? 50 : 40;
        },
        'height': (ele: any) => {
          const type = ele.data('nodeType');
          return type === 'protocol' ? 60 : type === 'class' ? 40 : 30;
        },
        'border-width': 2,
        'border-color': '#fff',
        'border-opacity': 0.8,
        'overlay-padding': '6px',
        'text-outline-width': 2,
        'text-outline-color': '#fff',
        'transition-property': 'background-color, border-color, width, height',
        'transition-duration': '0.2s',
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#2F6FED',
        'border-opacity': 1,
        'z-index': 999,
      },
    },
    {
      selector: 'node.hover',
      style: {
        'border-width': 3,
        'border-color': '#FFD600',
        'border-opacity': 1,
        'z-index': 998,
      },
    },
    {
      selector: 'node.faded',
      style: {
        'opacity': 0.2,
        'text-opacity': 0.2,
      },
    },
    {
      selector: 'edge',
      style: {
        'width': 1.5,
        'line-color': '#90a4ae',
        'target-arrow-color': '#90a4ae',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.6,
        'transition-property': 'opacity, line-color, width',
        'transition-duration': '0.2s',
      },
    },
    {
      selector: 'edge.hover',
      style: {
        'width': 3,
        'line-color': '#FFD600',
        'target-arrow-color': '#FFD600',
        'opacity': 1,
        'z-index': 997,
      },
    },
    {
      selector: 'edge.faded',
      style: {
        'opacity': 0.1,
      },
    },
    {
      selector: ':parent',
      style: {
        'background-opacity': 0.05,
        'border-width': 1,
        'border-style': 'dashed',
        'border-color': '#90a4ae',
      },
    },
  ], []);

  // 初始化 cytoscape
  useEffect(() => {
    if (!containerRef.current || cyRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: cyStyle,
      elements: [],
      layout: { name: 'preset' },
      minZoom,
      maxZoom,
      wheelSensitivity: 0.3,
      autoungrabify: false,
      autounselectify: false,
      boxSelectionEnabled: true,
    });

    cyRef.current = cy;

    // 事件绑定
    cy.on('tap', 'node', (e) => {
      const node = e.target;
      const nodeData = node.data() as TopologyNode;
      setSelectedNode(nodeData);
      onNodeClick?.(nodeData);
    });

    cy.on('mouseover', 'node', (e) => {
      const node = e.target;
      node.addClass('hover');
      const nodeData = node.data() as TopologyNode;
      onNodeHover?.(nodeData);
    });

    cy.on('mouseout', 'node', (e) => {
      const node = e.target;
      node.removeClass('hover');
      onNodeHover?.(null);
    });

    cy.on('tap', (e) => {
      if (e.target === cy) {
        setSelectedNode(null);
        onNodeClick?.(null as any);
      }
    });

    cy.on('mouseover', 'edge', (e) => {
      e.target.addClass('hover');
    });

    cy.on('mouseout', 'edge', (e) => {
      e.target.removeClass('hover');
    });

    // 视口变化处理
    cy.on('viewport', () => {
      // 可选：视口变化时的处理
    });

    setReady(true);

    // 清理函数
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [cyStyle, onNodeClick, onNodeHover]);

  // 布局运行函数
  const runLayout = useCallback((cy: cytoscape.Core, layoutName: string): Promise<void> => {
    return new Promise((resolve) => {
      const layoutOptions: any = {
        name: layoutName,
        animate: true,
        animationDuration: 800,
        animationEasing: 'ease-out',
        fit: true,
        padding: 50,
        randomize: true,
      };

      // 针对不同布局的特定配置
      if (layoutName === 'cose-bilkent') {
        Object.assign(layoutOptions, {
          idealEdgeLength: 100,
          nodeOverlap: 20,
          refresh: 20,
          gravity: 80,
          numIter: 2500,
          tile: true,
          tillingPaddingVertical: 10,
          tillingPaddingHorizontal: 10,
        });
      } else if (layoutName === 'cose') {
        Object.assign(layoutOptions, {
          idealEdgeLength: 100,
          nodeOverlap: 20,
          refresh: 20,
          gravity: 80,
          numIter: 2500,
        });
      }

      const layout = cy.layout(layoutOptions);
      layout.one('layoutstop', () => resolve());
      layout.run();
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 数据加载函数
  const loadData = useCallback(async () => {
    if (!cyRef.current || !data) return;

    const cy = cyRef.current;
    setLayoutRunning(true);

    try {
      // 清除现有元素
      cy.elements().remove();

      // 添加节点
      const nodes = data.nodes.map((node: TopologyNode) => ({
        group: 'nodes',
        data: {
          id: node.id,
          label: node.label,
          nodeType: node.type,
          module: node.module,
          file: node.file,
          line: node.line,
          docstring: node.docstring || '',
          qualified_name: node.id,
        },
        position: { x: 0, y: 0 },
      }));

      // 添加边
      const edges = data.edges.map((edge: TopologyEdge, idx: number) => ({
        group: 'edges',
        data: {
          id: `edge-${idx}`,
          source: edge.source,
          target: edge.target,
          edgeType: edge.type,
        },
      }));

      cy.add([...nodes, ...edges] as any);

      // 运行布局
      await runLayout(cy, layout);

      if (fitOnLoad) {
        cy.fit(cy.elements(), 50);
      }
    } finally {
      setLayoutRunning(false);
    }
  }, [data, layout, fitOnLoad, runLayout]);

  // 数据变化时重新加载
  useEffect(() => {
    if (ready && data) {
      loadData();
    }
  }, [data, ready, loadData]);

  // 导出/截图功能
  const exportPNG = useCallback(() => {
    if (!cyRef.current) return;
    const png = cyRef.current!.png({ full: true, bg: '#fff', scale: 2 });
    const link = document.createElement('a');
    link.download = `topology-${Date.now()}.png`;
    link.href = png;
    link.click();
  }, []);

  const exportJSON = useCallback(() => {
    if (!cyRef.current) return;
    const json = cyRef.current!.json();
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.download = `topology-${Date.now()}.json`;
    link.href = URL.createObjectURL(blob);
    link.click();
  }, []);

  // 工具栏操作
  const resetView = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.fit(cyRef.current.elements(), 50);
    }
  }, []);

  const zoomIn = useCallback(() => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() * 1.2);
  }, []);

  const zoomOut = useCallback(() => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() / 1.2);
  }, []);

  // 空状态
  if (!data) {
    return (
      <div
        ref={containerRef}
        className={className}
        style={{
          width: '100%',
          height: '100%',
          minHeight: 400,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg)',
          border: '1px solid var(--line)',
          borderRadius: 12,
          color: 'var(--sub)',
          ...style,
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 12 }}>🔬</div>
        <div style={{ fontSize: 14, fontWeight: 500 }}>暂无拓扑数据</div>
        <div style={{ fontSize: 12, marginTop: 4 }}>请选择代码库或节点查看拓扑</div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        width: '100%',
        height: '100%',
        minHeight: 500,
        background: 'var(--bg)',
        border: '1px solid var(--line)',
        borderRadius: 12,
        overflow: 'hidden',
        position: 'relative',
        ...style,
      }}
    >
      {/* 工具栏 */}
      <div style={{
        position: 'absolute',
        top: 12,
        left: 12,
        right: 12,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        zIndex: 100,
        pointerEvents: 'none',
        padding: '8px 12px',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          pointerEvents: 'auto',
        }}>
          <span style={{
            fontSize: 12,
            fontWeight: 600,
            color: 'var(--ink)',
            background: 'var(--card)',
            padding: '4px 10px',
            borderRadius: 6,
            border: '1px solid var(--line)',
          }}>
            🔬 拓扑图
          </span>
          {layoutRunning && (
            <span style={{
              fontSize: 11,
              color: 'var(--blue)',
              background: 'var(--blue-bg)',
              padding: '2px 8px',
              borderRadius: 4,
            }}>布局计算中...</span>
          )}
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          pointerEvents: 'auto',
        }}>
          <button onClick={zoomIn} title="放大" style={toolButtonStyle}>＋</button>
          <button onClick={zoomOut} title="缩小" style={toolButtonStyle}>－</button>
          <button onClick={resetView} title="重置视图" style={toolButtonStyle}>⌂</button>
          <button onClick={exportPNG} title="导出 PNG" style={toolButtonStyle}>📷</button>
          <button onClick={exportJSON} title="导出 JSON" style={toolButtonStyle}>💾</button>
        </div>
      </div>

      {/* 画布容器 */}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
        }}
      />

      {/* 选中节点详情面板 */}
      {selectedNode && (
        <div style={{
          position: 'absolute',
          bottom: 12,
          left: 12,
          right: 12,
          maxWidth: 420,
          pointerEvents: 'auto',
          background: 'var(--card)',
          border: '1px solid var(--line)',
          borderRadius: 10,
          padding: '12px 16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
          zIndex: 50,
          animation: 'slideUp 0.2s ease',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
            marginBottom: 8,
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 4,
              }}>
                <span style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: 'var(--ink)',
                  fontFamily: 'var(--mono)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>{selectedNode.label}</span>
                <span style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: NODE_TYPE_COLORS[selectedNode.type] || NODE_TYPE_COLORS.unknown,
                  background: (NODE_TYPE_COLORS[selectedNode.type] || NODE_TYPE_COLORS.unknown) + '20',
                  padding: '2px 8px',
                  borderRadius: 4,
                  textTransform: 'capitalize',
                }}>{selectedNode.type}</span>
              </div>
              <div style={{
                fontSize: 11,
                color: 'var(--sub)',
                fontFamily: 'var(--mono)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>{selectedNode.module}</div>
            </div>
            <button
              onClick={() => { setSelectedNode(null); onNodeHover?.(null); }}
              style={{
                padding: '4px 8px',
                fontSize: 11,
                background: 'var(--line)',
                color: 'var(--sub)',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              关闭
            </button>
          </div>

          {selectedNode.docstring && (
            <div style={{
              fontSize: 11,
              color: 'var(--ink)',
              lineHeight: 1.5,
              marginBottom: 8,
              padding: '8px 10px',
              background: 'var(--bg)',
              borderRadius: 6,
              border: '1px solid var(--line)',
              maxHeight: 120,
              overflow: 'auto',
            }}>
              {selectedNode.docstring}
            </div>
          )}

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 10,
            color: 'var(--sub)',
            flexWrap: 'wrap',
          }}>
            <span>📄 {selectedNode.file}</span>
            <span>📍 第 {selectedNode.line} 行</span>
            <span>🆔 {selectedNode.id}</span>
          </div>
        </div>
      )}
    </div>
  );
}

const toolButtonStyle: React.CSSProperties = {
  padding: '6px 10px',
  fontSize: 12,
  fontWeight: 600,
  background: 'var(--card)',
  color: 'var(--ink)',
  border: '1px solid var(--line)',
  borderRadius: 6,
  cursor: 'pointer',
  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  transition: 'all 0.15s ease',
  minWidth: 36,
  textAlign: 'center',
};