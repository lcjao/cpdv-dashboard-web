/** CodeLibraryNavigator - 顶部导航栏 */

import type { ViewMode } from '../../lib/algorithm-types';

interface CodeLibraryNavigatorProps {
  currentLibrary: string;
  onLibraryChange: (id: string) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onSearch: (query: string) => void;
  searchQuery: string;
  showSearchResults?: boolean;
  onCloseSearch?: () => void;
}

export default function CodeLibraryNavigator({
  currentLibrary,
  onLibraryChange,
  viewMode,
  onViewModeChange,
  onSearch,
  searchQuery,
}: CodeLibraryNavigatorProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      padding: '8px 12px',
      borderBottom: '1px solid var(--line)',
      background: 'var(--card)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink)' }}>代码库</span>
        <select
          value={currentLibrary}
          onChange={(e) => onLibraryChange(e.target.value)}
          style={{
            padding: '6px 10px',
            border: '1px solid var(--line)',
            borderRadius: 6,
            background: 'var(--bg)',
            color: 'var(--ink)',
          }}
        >
          <option value={currentLibrary}>{currentLibrary}</option>
        </select>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button
          type="button"
          onClick={() => onViewModeChange('topology')}
          style={{
            padding: '6px 10px',
            borderRadius: 6,
            border: '1px solid var(--line)',
            background: viewMode === 'topology' ? 'var(--blue-bg)' : 'transparent',
            color: 'var(--ink)',
            cursor: 'pointer',
          }}
        >
          拓扑
        </button>
        <button
          type="button"
          onClick={() => onViewModeChange('list')}
          style={{
            padding: '6px 10px',
            borderRadius: 6,
            border: '1px solid var(--line)',
            background: viewMode === 'list' ? 'var(--blue-bg)' : 'transparent',
            color: 'var(--ink)',
            cursor: 'pointer',
          }}
        >
          列表
        </button>
        <button
          type="button"
          onClick={() => onViewModeChange('compare')}
          style={{
            padding: '6px 10px',
            borderRadius: 6,
            border: '1px solid var(--line)',
            background: viewMode === 'compare' ? 'var(--blue-bg)' : 'transparent',
            color: 'var(--ink)',
            cursor: 'pointer',
          }}
        >
          对比
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <input
          value={searchQuery}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="搜索符号"
          style={{
            width: 200,
            padding: '6px 10px',
            border: '1px solid var(--line)',
            borderRadius: 6,
            background: 'var(--bg)',
            color: 'var(--ink)',
          }}
        />
      </div>
    </div>
  );
}
