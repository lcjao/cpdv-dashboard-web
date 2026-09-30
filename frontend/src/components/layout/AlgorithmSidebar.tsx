import { useState, useEffect, useCallback } from 'react';

// 文件树节点类型
interface FileNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  size?: number;
  modified?: number;
  expanded?: boolean;
}

interface ExternalCodeTreeResponse {
  root: string;
  root_type: string;
  root_label: string;
  tree: FileNode[];
}

interface FileContentResponse {
  path: string;
  name: string;
  content: string;
  size: number;
  modified: number;
}

// 文件图标映射
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
};

function getFileIcon(name: string): string {
  const ext = name.substring(name.lastIndexOf('.'));
  return FILE_ICONS[ext] || '📄';
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// 文件树节点组件
function FileTreeNode({
  node,
  depth = 0,
  onFileClick,
  onFolderToggle,
  expandedPaths,
}: {
  node: FileNode;
  depth?: number;
  onFileClick?: (path: string) => void;
  onFolderToggle?: (path: string) => void;
  expandedPaths: Set<string>;
}) {
  const isExpanded = expandedPaths.has(node.path);
  const indent = depth * 16;

  const toggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFolderToggle?.(node.path);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (node.type === 'file' && onFileClick) {
      onFileClick(node.path);
    } else {
      toggleExpand(e);
    }
  };

  if (node.type === 'file') {
    return (
      <div
        style={{
          paddingLeft: indent + 24,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          height: 24,
          cursor: 'pointer',
          borderRadius: 4,
          transition: 'background 0.1s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--blue-bg)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        onClick={handleClick}
        title={node.path}
      >
        <span style={{ fontSize: 13 }}>{getFileIcon(node.name)}</span>
        <span style={{
          fontSize: 12,
          color: 'var(--ink)',
          fontFamily: 'var(--mono)',
          maxWidth: 220,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>{node.name}</span>
        {node.size !== undefined && (
          <span style={{
            fontSize: 10,
            color: 'var(--sub)',
            marginLeft: 'auto',
            opacity: 0.7,
            fontFamily: 'var(--mono)',
          }}>{formatSize(node.size)}</span>
        )}
      </div>
    );
  }

  return (
    <div style={{ paddingLeft: indent }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          height: 24,
          cursor: 'pointer',
          borderRadius: 4,
          padding: '0 4px',
          transition: 'background 0.1s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--blue-bg)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        onClick={toggleExpand}
        title={node.path}
      >
        <span style={{
          fontSize: 10,
          color: isExpanded ? 'var(--blue)' : 'var(--sub)',
          transition: 'transform 0.15s',
          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0)',
          display: 'inline-block',
          minWidth: 12,
        }}>
          ▸
        </span>
        <span style={{ fontSize: 13 }}>📁</span>
        <span style={{
          fontSize: 12,
          fontWeight: 600,
          color: 'var(--ink)',
          maxWidth: 180,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>{node.name}</span>
      </div>
      {isExpanded && node.children && (
        <div style={{ animation: 'slideDown 0.15s ease' }}>
          {node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              onFileClick={onFileClick}
              onFolderToggle={onFolderToggle}
              expandedPaths={expandedPaths}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// 代码查看器组件
function CodeViewer({ filePath, content, rootType, onSave, onClose }: {
  filePath: string;
  content: string;
  rootType: string;
  onSave?: (path: string, content: string, rootType: string) => void;
  onClose: () => void;
}) {
  const [editedContent, setEditedContent] = useState(content);
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const handleSave = async () => {
    if (!onSave || saving) return;
    setSaving(true);
    setSaveStatus('idle');
    try {
      await onSave(filePath, editedContent, rootType);
      setSaveStatus('success');
      setIsDirty(false);
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (e) {
      setSaveStatus('error');
      console.error('保存失败:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.currentTarget;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      setEditedContent(prev => prev.substring(0, start) + '  ' + prev.substring(end));
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: 300,
      background: 'var(--bg)',
      borderRadius: 8,
      overflow: 'hidden',
      border: '1px solid var(--line)',
    }}>
      {/* 顶部工具栏 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        background: 'var(--card)',
        borderBottom: '1px solid var(--line)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13 }}>{getFileIcon(filePath)}</span>
          <span style={{
            fontSize: 12,
            fontWeight: 500,
            color: 'var(--ink)',
            fontFamily: 'var(--mono)',
            maxWidth: 300,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>{filePath}</span>
          <span style={{
            fontSize: 9,
            color: rootType === 'algorithm' ? 'var(--blue)' : 'var(--amber)',
            background: rootType === 'algorithm' ? 'var(--blue-bg)' : 'var(--amber-bg)',
            padding: '1px 6px',
            borderRadius: 3,
            fontWeight: 600,
          }}>{rootType === 'algorithm' ? '纯算法库' : '原始Pipeline'}</span>
          {isDirty && (
            <span style={{
              fontSize: 10,
              color: 'var(--amber)',
              background: 'var(--amber-bg)',
              padding: '2px 6px',
              borderRadius: 4,
            }}>● 未保存</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={handleSave}
            disabled={saving || !isDirty}
            style={{
              padding: '6px 12px',
              fontSize: 11,
              fontWeight: 600,
              background: isDirty ? 'var(--blue)' : 'var(--line)',
              color: isDirty ? '#fff' : 'var(--sub)',
              border: 'none',
              borderRadius: 6,
              cursor: isDirty ? 'pointer' : 'not-allowed',
            }}
          >
            {saving ? '保存中...' : '保存 (Ctrl+S)'}
          </button>
          {saveStatus === 'success' && (
            <span style={{
              fontSize: 11,
              color: 'var(--green)',
              display: 'flex',
              alignItems: 'center',
            }}>✓ 已保存</span>
          )}
          {saveStatus === 'error' && (
            <span style={{
              fontSize: 11,
              color: 'var(--red)',
              display: 'flex',
              alignItems: 'center',
            }}>✗ 保存失败</span>
          )}
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
        </div>
      </div>

      {/* 代码编辑区 */}
      <textarea
        value={editedContent}
        onChange={(e) => {
          setEditedContent(e.target.value);
          setIsDirty(true);
        }}
        onKeyDown={handleKeyDown}
        spellCheck={false}
        style={{
          flex: 1,
          padding: 12,
          fontSize: 13,
          fontFamily: 'var(--mono)',
          lineHeight: 1.6,
          color: 'var(--ink)',
          background: 'var(--bg)',
          border: 'none',
          outline: 'none',
          resize: 'none',
          tabSize: 2,
        }}
      />
    </div>
  );
}

interface AlgorithmSidebarProps {
  onFileClick?: (path: string, rootType: string) => void;
}

export default function AlgorithmSidebar({ onFileClick }: AlgorithmSidebarProps) {
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [selectedFile, setSelectedFile] = useState<{ path: string; content: string; rootType: string } | null>(null);
  const [codeRoot, setCodeRoot] = useState('');
  const [currentRootType, setCurrentRootType] = useState<'pipeline' | 'algorithm'>('algorithm');

  // 加载文件树
  const loadTree = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/external-code/tree?root=${currentRootType}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ExternalCodeTreeResponse = await res.json();
      setCodeRoot(data.root_label || data.root);  // 显示带标签的路径
      setFileTree(data.tree);
      // 默认展开一级目录
      const newExpanded = new Set<string>();
      data.tree.forEach(n => newExpanded.add(n.path));
      setExpandedPaths(newExpanded);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [currentRootType]);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  // 切换文件夹展开
  const handleFolderToggle = (path: string) => {
    setExpandedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  // 点击文件 - 读取内容
  const handleFileClick = async (path: string) => {
    try {
      const res = await fetch(`/api/external-code/read?path=${encodeURIComponent(path)}&root=${currentRootType}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: FileContentResponse = await res.json();
      setSelectedFile({ path: data.path, content: data.content, rootType: currentRootType });
      onFileClick?.(data.path, currentRootType);
    } catch (e) {
      console.error('读取文件失败:', e);
      alert('读取文件失败: ' + e);
    }
  };

  // 保存文件
  const handleSaveFile = async (path: string, content: string) => {
    const res = await fetch('/api/external-code/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content, root: currentRootType }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || '保存失败');
    }
  };

  // 关闭代码查看器
  const handleCloseViewer = () => {
    setSelectedFile(null);
  };

  if (loading) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--sub)' }}>
        加载外部代码树...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, padding: 20, color: 'var(--red)' }}>
        <div>加载失败: {error}</div>
        <button onClick={loadTree} style={{ padding: '6px 16px', fontSize: 12, background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          重试
        </button>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--card)', borderRadius: 12, overflow: 'hidden' }}>
      {/* 头部 */}
      <div style={{
        padding: '12px 12px 10px',
        borderBottom: '1px solid var(--line)',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        background: 'linear-gradient(180deg, rgba(47,111,237,0.03) 0%, rgba(255,255,255,0) 100%)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 10,
          flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: '1 1 150px' }}>
            <span style={{
              display: 'inline-flex',
              width: 26,
              height: 26,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 8,
              background: 'var(--blue-bg)',
              color: 'var(--blue)',
              fontSize: 14,
              boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.8)',
              flexShrink: 0,
            }}>
              🔬
            </span>
            <span style={{
              fontSize: 13,
              fontWeight: 700,
              color: 'var(--ink)',
              letterSpacing: 0.3,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              外部算法代码
            </span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            minWidth: 0,
            flex: '1 1 220px',
            justifyContent: 'flex-end',
            flexWrap: 'wrap',
          }}>
            <span style={{
              fontSize: 10,
              color: 'var(--sub)',
              background: 'var(--bg)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              padding: '4px 8px',
              maxWidth: '100%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontFamily: 'var(--mono)',
              flex: '1 1 120px',
            }} title={codeRoot}>
              {codeRoot}
            </span>
            <button
              onClick={loadTree}
              style={{
                padding: '5px 10px',
                fontSize: 10,
                background: 'var(--blue)',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600,
                boxShadow: '0 1px 2px rgba(47,111,237,0.2)',
                flexShrink: 0,
              }}
            >
              刷新
            </button>
          </div>
        </div>
        {/* 根目录切换器 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--sub)' }}>
          <span style={{ fontWeight: 600 }}>代码库</span>
          <select
            value={currentRootType}
            onChange={(e) => setCurrentRootType(e.target.value as 'pipeline' | 'algorithm')}
            style={{
              flex: 1,
              minWidth: 0,
              padding: '5px 10px',
              fontSize: 11,
              background: 'var(--card)',
              color: 'var(--ink)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="algorithm">📚 纯算法库 (可 import 复用)</option>
            <option value="pipeline">🔧 原始 Pipeline (后端执行)</option>
          </select>
        </div>
      </div>

      {/* 内容区域：左侧文件树 + 右侧代码查看器 */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 左侧文件树 */}
        <div style={{
          width: 280,
          minWidth: 240,
          maxWidth: 360,
          borderRight: '1px solid var(--line)',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg)',
        }}>
          <div style={{
            padding: '8px 10px',
            fontSize: 11,
            color: 'var(--sub)',
            borderBottom: '1px solid var(--line)',
            background: 'var(--card)',
          }}>
            {currentRootType === 'algorithm'
              ? '纯算法库：simulation/ models/ data/ training/ (可 import)'
              : '原始 Pipeline：scripts/ model/ simulation/ data_pipeline/ (可执行)'}
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 4px' }}>
            {fileTree.map((node) => (
              <FileTreeNode
                key={node.path}
                node={node}
                onFileClick={handleFileClick}
                onFolderToggle={handleFolderToggle}
                expandedPaths={expandedPaths}
              />
            ))}
          </div>
        </div>

        {/* 右侧代码查看器 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          {selectedFile ? (
            <CodeViewer
              filePath={selectedFile.path}
              content={selectedFile.content}
              rootType={selectedFile.rootType}
              onSave={handleSaveFile}
              onClose={handleCloseViewer}
            />
          ) : (
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--sub)',
              padding: 20,
            }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>📄</div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>点击左侧文件查看代码</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>支持查看和编辑保存</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}