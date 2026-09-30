/** DashboardSync Component - Auto-sync dashboard widgets with pipeline outputs */
import { useEffect } from 'react';
import { useDashboardSync, DashboardWidgetData } from '../hooks/useAICommand';

interface DashboardSyncProps {
  widgets?: string[];
  children: (data: DashboardWidgetData | null, loading: boolean, error: string | null, refresh: () => Promise<void>) => React.ReactNode;
  autoRefreshInterval?: number; // ms, 0 to disable
}

export function DashboardSync({ 
  widgets, 
  children, 
  autoRefreshInterval = 0 
}: DashboardSyncProps) {
  const { widgetData, loading, error, sync } = useDashboardSync(widgets);
  
  // Auto-refresh timer
  useEffect(() => {
    if (autoRefreshInterval <= 0) return;
    
    const timer = setInterval(() => {
      sync(false).catch(console.error);
    }, autoRefreshInterval);
    
    return () => clearInterval(timer);
  }, [autoRefreshInterval, sync]);

  // Listen for pipeline completion events to trigger refresh
  useEffect(() => {
    const ws = new WebSocket(
      `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ai/ws?tags=pipeline,analysis`
    );
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Refresh when pipeline completes
        if (msg.progress?.stage === 'dashboard_sync' && msg.progress?.percent === 100) {
          sync(false).catch(console.error);
        }
        // Also refresh on pipeline completion
        if (msg.progress?.stage?.includes('completed') && msg.progress?.percent === 100) {
          setTimeout(() => sync(false).catch(console.error), 1000);
        }
      } catch (e) {
        // Ignore parse errors
      }
    };
    
    return () => ws.close();
  }, [sync]);

  return (
    <div data-dashboard-sync>
      {children(widgetData, loading, error, () => { sync(false).catch(console.error); return Promise.resolve(); })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Widget-specific data extractors
// ─────────────────────────────────────────────────────────────────────

export function useCpdvTimeseries(widgetData: DashboardWidgetData | null) {
  return widgetData?.cpdv_timeseries || null;
}

export function useModelScorecard(widgetData: DashboardWidgetData | null) {
  return widgetData?.model_scorecard || null;
}

export function usePeakAnalysis(widgetData: DashboardWidgetData | null) {
  return widgetData?.peak_vs_position || widgetData?.peak_vs_depth || null;
}

export function useCvAnalysis(widgetData: DashboardWidgetData | null) {
  return widgetData?.cv_analysis || widgetData?.multi_position_boxplot || null;
}

export function useMultiCrackComparison(widgetData: DashboardWidgetData | null) {
  return widgetData?.multi_crack_comparison || null;
}

export function useErrorDistribution(widgetData: DashboardWidgetData | null) {
  return widgetData?.error_distribution || null;
}

export function useRoadProfile(widgetData: DashboardWidgetData | null) {
  return widgetData?.road_profile || null;
}

// ─────────────────────────────────────────────────────────────────────
// Dashboard Status Indicator
// ─────────────────────────────────────────────────────────────────────

export function DashboardStatusIndicator({ 
  loading, 
  error, 
  lastSync 
}: { 
  loading: boolean;
  error: string | null;
  lastSync: string | null;
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-amber-600">
        <span className="animate-spin">⟳</span>
        <span>同步中...</span>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-600">
        <span>⚠</span>
        <span>同步失败: {error}</span>
      </div>
    );
  }
  
  return (
    <div className="flex items-center gap-2 text-green-600">
      <span>✓</span>
      <span>数据已同步</span>
      {lastSync && (
        <span className="text-xs text-gray-500">
          ({new Date(lastSync).toLocaleTimeString()})
        </span>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Widget Data Availability Badges
// ─────────────────────────────────────────────────────────────────────

export function WidgetDataBadges({ widgetData }: { widgetData: DashboardWidgetData | null }) {
  if (!widgetData) return null;
  
  const widgets = [
    { key: 'cpdv_timeseries', label: 'CPDV 时序' },
    { key: 'model_scorecard', label: '模型评分' },
    { key: 'peak_vs_position', label: '峰值-位置' },
    { key: 'cv_analysis', label: 'CV 分析' },
    { key: 'multi_crack_comparison', label: '多裂缝对比' },
    { key: 'error_distribution', label: '误差分布' },
    { key: 'road_profile', label: '路面谱' },
  ];
  
  return (
    <div className="flex flex-wrap gap-1">
      {widgets.map(w => (
        <span
          key={w.key}
          className={`px-2 py-0.5 text-xs rounded ${
            widgetData[w.key as keyof DashboardWidgetData] 
              ? 'bg-green-100 text-green-700' 
              : 'bg-gray-100 text-gray-500'
          }`}
        >
          {w.label}
        </span>
      ))}
    </div>
  );
}