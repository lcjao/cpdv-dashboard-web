/** SymbolSearch - 全局符号搜索 */

import { useEffect, useRef, useState } from 'react';
import { searchSymbols } from '../../lib/algorithm-api';
import type { SymbolSearchParams, SymbolSearchResult } from '../../lib/algorithm-types';

interface SymbolSearchProps {
  isOpen?: boolean;
  onClose?: () => void;
  onSelect?: (result: SymbolSearchResult) => void;
  initialQuery?: string;
  library?: string;
  query?: string;
  height?: number;
  onResultClick?: (result: SymbolSearchResult) => void;
}

export default function SymbolSearch({
  isOpen = true,
  onClose = () => undefined,
  onSelect,
  initialQuery = '',
  library,
  query,
  height = 400,
  onResultClick,
}: SymbolSearchProps) {
  const [localQuery, setLocalQuery] = useState(query ?? initialQuery);
  const [results, setResults] = useState<SymbolSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const activeQuery = query ?? localQuery;

  useEffect(() => {
    if (query !== undefined) {
      setLocalQuery(query);
    }
  }, [query]);

  useEffect(() => {
    if (!isOpen) return;
    if (!activeQuery.trim()) {
      setResults([]);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    void (async () => {
      try {
        const params: SymbolSearchParams = {
          q: activeQuery,
          limit: 20,
          library,
        };
        const response = await searchSymbols(params);
        if (!cancelled) {
          setResults(response.symbols ?? []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(String(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeQuery, isOpen, library]);

  useEffect(() => {
    if (!isOpen || !inputRef.current) return;
    inputRef.current.focus();
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, background: 'var(--card)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
        <input
          ref={inputRef}
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
          placeholder="搜索符号、类、函数、协议..."
          style={{
            flex: 1,
            padding: '10px 12px',
            border: '1px solid var(--line)',
            borderRadius: 8,
            background: 'var(--bg)',
            color: 'var(--ink)',
            fontSize: 13,
            outline: 'none',
          }}
        />
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: '8px 10px',
            borderRadius: 6,
            border: '1px solid var(--line)',
            background: 'transparent',
            color: 'var(--sub)',
            cursor: 'pointer',
          }}
        >
          关闭
        </button>
      </div>

      <div style={{ maxHeight: height, overflowY: 'auto', padding: 8 }}>
        {loading && (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--sub)' }}>搜索中...</div>
        )}
        {error && (
          <div style={{ padding: '16px', color: 'var(--red)' }}>搜索失败: {error}</div>
        )}
        {!loading && !error && results.length === 0 && activeQuery.trim() && (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--sub)' }}>未找到匹配: "{activeQuery}"</div>
        )}
        {!loading && results.map((result, index) => (
          <button
            key={`${result.q}-${index}`}
            type="button"
            onClick={() => {
              onSelect?.(result);
              onResultClick?.(result);
              onClose();
            }}
            onMouseEnter={() => setSelectedIndex(index)}
            onMouseLeave={() => setSelectedIndex(-1)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
              padding: '10px 12px',
              marginBottom: 6,
              background: selectedIndex === index ? 'var(--blue-bg)' : 'transparent',
              border: '1px solid var(--line)',
              borderRadius: 8,
              color: 'var(--ink)',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{result.n}</div>
              <div style={{ fontSize: 11, color: 'var(--sub)', fontFamily: 'var(--mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{result.q}</div>
            </div>
            <span style={{ fontSize: 11, color: 'var(--sub)' }}>{result.t}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
