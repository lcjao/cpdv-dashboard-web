/** ModuleTree - 代码库模块树（左侧边栏） */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import type { ModuleTreeNode } from '../../lib/algorithm-types';
import { fetchTopology } from '../../lib/algorithm-api';

const FILE_ICONS: Record<string, string> = {
  '.py': '🐍',
  '.txt': '📄',
  '.md': '📝',
  '.yaml': '⚙️',
  '.yml': '⚙️',
  '.json': '📋',
  '.toml': '⚙️',
  '.cfg': '⚙️',
  '.ini': '⚙️',
  '.js': '📜',
  '.ts': '📘',
  '.tsx': '⚛️',
};

function getFileIcon(name: string): string {
  const ext = name.substring(name.lastIndexOf('.'));
  return FILE_ICONS[ext] || '📄';
}

function getFolderIcon(expanded: boolean): string {
  return expanded ? '📂' : '📁';
}

interface ModuleTreeProps {
  library?: string;
  onNodeClick?: (node: ModuleTreeNode) => void;
  onNodeSelect?: (node: ModuleTreeNode) => void;
  selectedNode?: ModuleTreeNode | null;
  searchQuery?: string;
  showProtocolBadge?: boolean;
}

export default function ModuleTree({
  library,
  onNodeClick,
  onNodeSelect,
  selectedNode,
  searchQuery = '',
  showProtocolBadge = true,
}: ModuleTreeProps) {
  const [treeData, setTreeData] = useState<ModuleTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [hoveredPath, setHoveredPath] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const buildModuleTree = useCallback(async () => {
    if (!library) return;
    setLoading(true);
    try {
      const topology = await fetchTopology({ library });
      const root: ModuleTreeNode = {
        name: library,
        path: library,
        type: 'folder',
        module: library,
        children: [],
        symbolCount: 0,
      };

      const ensureFolder = (parent: ModuleTreeNode, name: string, path: string): ModuleTreeNode => {
        if (!parent.children) parent.children = [];
        let child = parent.children.find(node => node.path === path);
        if (!child) {
          child = {
            name,
            path,
            type: 'folder',
            module: library,
            children: [],
            symbolCount: 0,
          };
          parent.children.push(child);
        }
        return child;
      };

      topology.nodes.forEach(node => {
        const fileValue = (node.file || '').replace(/\\/g, '/');
        const segments = fileValue.split('/').filter(Boolean);
        const rootIndex = segments.findIndex(seg => seg.toLowerCase() === library.toLowerCase());
        const relativeSegments = rootIndex >= 0 ? segments.slice(rootIndex + 1) : segments.slice(-2);

        if (relativeSegments.length === 0) return;

        const folderSegments = relativeSegments.slice(0, -1).map(seg => seg.replace(/\.[^/.]+$/, ''));
        const finalSegment = relativeSegments[relativeSegments.length - 1] || 'root';

        let cursor: ModuleTreeNode = root;
        let currentPath = library;

        if (folderSegments.length > 0) {
          for (let i = 0; i < folderSegments.length; i += 1) {
            const segment = folderSegments[i];
            currentPath = `${currentPath}/${segment}`;
            cursor = ensureFolder(cursor, segment, currentPath);
          }
        }

        const finalPath = `${currentPath}/${finalSegment}`;

        if (!cursor.children) cursor.children = [];
        let leaf = cursor.children.find(child => child.path === finalPath);
        if (!leaf) {
          leaf = {
            name: finalSegment,
            path: finalPath,
            type: 'file',
            module: library,
            file: node.file,
            symbolCount: 0,
          };
          cursor.children.push(leaf);
        }

        leaf.symbolCount = (leaf.symbolCount || 0) + 1;
        if (node.type === 'protocol' && !leaf.hasProtocol) {
          leaf.hasProtocol = true;
        }
      });

      const sortTree = (nodes: ModuleTreeNode[]) => {
        nodes.sort((a, b) => {
          if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
          return a.name.localeCompare(b.name);
        });
        nodes.forEach(n => {
          if (n.children) sortTree(n.children);
        });
      };

      const roots = root.children || [];
      sortTree(roots);

      const initialExpanded = new Set<string>([root.path]);
      roots.forEach(r => initialExpanded.add(r.path));
      setExpandedPaths(initialExpanded);
      setTreeData([root]);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [library]);

  useEffect(() => { buildModuleTree(); }, [buildModuleTree]);

  const toggleExpand = useCallback((path: string) => {
    setExpandedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const filteredTree = useMemo(() => {
    if (!searchQuery.trim()) return treeData;

    const query = searchQuery.toLowerCase();
    const matchedPaths = new Set<string>();

    const findMatches = (nodes: ModuleTreeNode[], parentPath = '') => {
      for (const node of nodes) {
        const fullPath = parentPath ? `${parentPath}.${node.name}` : node.name;
        if (node.name.toLowerCase().includes(query) || node.path.toLowerCase().includes(query)) {
          matchedPaths.add(node.path);
          let p = parentPath;
          while (p) {
            matchedPaths.add(p);
            const idx = p.lastIndexOf('.');
            p = idx > 0 ? p.substring(0, idx) : '';
          }
        }
        if (node.children) findMatches(node.children, fullPath);
      }
    };

    findMatches(treeData);

    const filterTree = (nodes: ModuleTreeNode[]): ModuleTreeNode[] => {
      return nodes
        .filter(n => matchedPaths.has(n.path) || n.children?.some(c => matchedPaths.has(c.path)))
        .map(n => ({
          ...n,
          children: n.children ? filterTree(n.children) : undefined,
          matched: matchedPaths.has(n.path),
        }));
    };

    return filterTree(treeData);
  }, [treeData, searchQuery]);

  useEffect(() => {
    if (searchQuery.trim()) {
      const matched = new Set<string>();
      const find = (nodes: ModuleTreeNode[]) => {
        for (const n of nodes) {
          if ((n as any).matched) matched.add(n.path);
          if (n.children) find(n.children);
        }
      };
      find(filteredTree);
      if (matched.size > 0) {
        setExpandedPaths(prev => new Set([...prev, ...matched]));
      }
    }
  }, [filteredTree, searchQuery]);

  const renderNode = useCallback((
    node: ModuleTreeNode,
    depth: number,
  ) => {
    const isExpanded = expandedPaths.has(node.path);
    const isSelected = selectedNode?.path === node.path;
    const isHovered = hoveredPath === node.path;
    const isMatched = (node as any).matched;
    const hasChildren = node.children && node.children.length > 0;
    const indent = depth * 16;

    const handleClick = (e: React.MouseEvent) => {
      e.stopPropagation();
      if (hasChildren) {
        toggleExpand(node.path);
      } else {
        onNodeClick?.(node);
      }
      onNodeSelect?.(node);
    };

    const handleDoubleClick = (e: React.MouseEvent) => {
      e.stopPropagation();
      if (hasChildren) toggleExpand(node.path);
    };

    const handleContextMenu = (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };

    return (
      <div
        key={node.path}
        style={{
          paddingLeft: indent + 4,
        }}
        onMouseEnter={() => setHoveredPath(node.path)}
        onMouseLeave={() => setHoveredPath(null)}
        onContextMenu={handleContextMenu}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            height: 24,
            padding: `0 ${hasChildren ? '4px' : '10px'} 0 8px`,
            borderRadius: 4,
            cursor: hasChildren ? 'pointer' : 'default',
            background: isSelected ? 'var(--blue-bg)' : isHovered ? 'var(--hover-bg, var(--blue-bg))' : 'transparent',
            transition: 'background 0.1s',
            borderLeft: isSelected ? '2px solid var(--blue)' : '2px solid transparent',
            opacity: (node as any).matched ? 1 : searchQuery && !isMatched ? 0.4 : 1,
          }}
          onClick={handleClick}
          onDoubleClick={handleDoubleClick}
          onMouseEnter={() => setHoveredPath(node.path)}
          onMouseLeave={() => setHoveredPath(null)}
          title={node.path}
        >
          {hasChildren && (
            <span
              style={{
                display: 'inline-flex',
                width: 16,
                height: 16,
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                color: isExpanded ? 'var(--blue)' : 'var(--sub)',
                transition: 'transform 0.15s',
                transform: isExpanded ? 'rotate(90deg)' : 'rotate(0)',
                flexShrink: 0,
              }}
            >
              ▸
            </span>
          )}
          {!hasChildren && (
            <span style={{ width: 16, flexShrink: 0 }} />
          )}
          <span style={{
            fontSize: 13,
            fontWeight: isSelected || isMatched ? 600 : 400,
            color: isSelected ? 'var(--blue)' : isMatched ? 'var(--ink)' : 'var(--ink)',
          }}>
            {getFolderIcon(isExpanded)}
          </span>
          {node.type === 'file' && <span style={{ fontSize: 13 }}>{getFileIcon(node.name)}</span>}
          <span style={{
            fontSize: 12,
            fontWeight: isSelected || isMatched ? 600 : 400,
            color: isSelected ? 'var(--blue)' : isMatched ? 'var(--ink)' : 'var(--ink)',
            fontFamily: node.type === 'file' ? 'var(--mono)' : 'inherit',
            maxWidth: 200,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}>
            {node.name}
          </span>
          {(node.symbolCount !== undefined && node.symbolCount > 0) && (
            <span style={{
              fontSize: 10,
              color: 'var(--sub)',
              background: 'var(--bg)',
              padding: '1px 6px',
              borderRadius: 4,
              fontFamily: 'var(--mono)',
            }}>
              {node.symbolCount}
            </span>
          )}
          {showProtocolBadge && (node as any).hasProtocol && (
            <span style={{
              fontSize: 9,
              fontWeight: 700,
              color: '#fff',
              background: 'var(--blue)',
              padding: '1px 6px',
              borderRadius: 4,
              flexShrink: 0,
            }}>
              Protocol
            </span>
          )}
        </div>
        {isExpanded && node.children && (
          <div style={{ animation: 'slideDown 0.15s ease' }}>
            {node.children.map(child => (
              renderNode(child, depth + 1)
            ))}
          </div>
        )}
      </div>
    );
  }, [expandedPaths, selectedNode, searchQuery, hoveredPath, onNodeClick, onNodeSelect, toggleExpand]);

  if (loading) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--sub)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 20, marginBottom: 8 }}>🔬</div>
          <div>加载模块树...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, padding: 20, color: 'var(--red)' }}>
        <div>加载失败: {error}</div>
        <button onClick={buildModuleTree} style={{ padding: '6px 16px', fontSize: 12, background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          重试
        </button>
      </div>
    );
  }

  if (treeData.length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--sub)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📁</div>
          <div>暂无模块数据</div>
          <div style={{ fontSize: 12, marginTop: 4 }}>请选择代码库</div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '8px 4px',
        fontFamily: 'inherit',
      }}
      role="tree"
      aria-label="模块树"
    >
      <div style={{ padding: '8px 4px' }}>
        {filteredTree.map(node => renderNode(node, 0))}
      </div>
    </div>
  );
}