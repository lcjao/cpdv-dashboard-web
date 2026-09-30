import { useEffect, useState } from 'react';
import type { DashboardData } from './lib/types';
import { api } from './lib/api-client';
import Header from './components/layout/Header';
import BridgeSidebar from './components/layout/BridgeSidebar';
import ChatPanel from './components/layout/ChatPanel';
import ParamTable from './components/bridge/ParamTable';
import CpdvChart from './components/charts/CpdvChart';
import ProfileChart from './components/charts/ProfileChart';
import SettingsDialog from './components/layout/SettingsDialog';
import AlgorithmSidebar from './components/layout/AlgorithmSidebar';
import AlgorithmDashboard from './components/algorithm/AlgorithmDashboard';
import { ProgressProvider, useActiveTasks } from './lib/progress-context';

/** Global progress toast bar (fixed bottom) */
function GlobalProgressBar() {
  const activeTasks = useActiveTasks();
  if (activeTasks.length === 0) return null;

  // Show the most recent active task
  const task = activeTasks[activeTasks.length - 1];
  const percent = task.percent ?? 0;
  const isError = task.stage === 'error';

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 380,  // leave space for AI chat panel (width 380px)
        zIndex: 999,
        background: isError ? 'var(--red)' : 'var(--card)',
        borderTop: '2px solid var(--line)',
        borderBottom: 'none',
        boxShadow: '0 -4px 20px rgba(0,0,0,.3)',
        padding: '8px 16px',
        fontFamily: 'var(--mono)',
        fontSize: 12,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, maxWidth: 900, margin: '0 auto' }}>
        <span style={{ fontWeight: 700, color: isError ? '#fff' : 'var(--fg)', textTransform: 'capitalize' }}>
          {task.tag}
        </span>
        <span style={{ flex: 1, color: isError ? '#ffe0e0' : 'var(--muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {task.stage}: {task.message}
        </span>
        <div style={{ width: 160, height: 6, background: 'rgba(255,255,255,.15)', borderRadius: 3, overflow: 'hidden', flexShrink: 0 }}>
          <div
            style={{
              width: `${Math.min(100, Math.max(0, percent))}%`,
              height: '100%',
              background: isError ? '#ff6b6b' : 'var(--accent)',
              transition: 'width .3s ease',
            }}
          />
        </div>
        <span style={{ color: isError ? '#fff' : 'var(--muted)', fontSize: 11, minWidth: '36px', textAlign: 'right' }}>
          {Math.round(percent)}%
        </span>
      </div>
    </div>
  );
}

/** Inner app component (needs ProgressProvider context) */
function AppInner() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [cur, setCur] = useState(0);
  const [err, setErr] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [showConsole, setShowConsole] = useState(false);
  const [showAlgorithmSidebar, setShowAlgorithmSidebar] = useState(false);
  const [showAlgorithmDashboard, setShowAlgorithmDashboard] = useState(false);

  useEffect(() => {
    api.fetchDashboard().then(setData).catch(e => setErr(String(e)));
  }, []);

  if (err) return <div style={{ padding: 40, color: 'var(--red)' }}>加载失败: {err}</div>;
  if (!data) return <div style={{ padding: 40 }}>加载中…</div>;

  const b = data.bridges[cur];

  if (showAlgorithmDashboard) {
    return <AlgorithmDashboard onBack={() => setShowAlgorithmDashboard(false)} />;
  }

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '16px 20px 40px' }}>
      <GlobalProgressBar />
      <Header
        meta={data.meta}
        showConsole={showConsole}
        onToggleConsole={() => setShowConsole(v => !v)}
        onOpenSettings={() => setShowSettings(true)}
        showAlgorithmSidebar={showAlgorithmSidebar}
        onToggleAlgorithmSidebar={() => setShowAlgorithmSidebar(v => !v)}
        showAlgorithmDashboard={showAlgorithmDashboard}
        onToggleAlgorithmDashboard={() => setShowAlgorithmDashboard(v => !v)}
      />
      <div style={{ display: 'grid', gridTemplateColumns: `${showAlgorithmSidebar ? '260px ' : ''}290px 1fr`, gap: 14, alignItems: 'start' }}>
        {showAlgorithmSidebar && (
          <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 260 }}>
            <AlgorithmSidebar onFileClick={(path) => console.log('Open file:', path)} />
          </div>
        )}
<div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>① 桥梁工况</h3>
            <BridgeSidebar bridges={data.bridges.filter(b => b.status !== 'legacy')} cur={cur} onSelect={setCur} onRefresh={async () => {
              const fresh = await api.fetchDashboard();
              setData(fresh);
              if (cur >= fresh.bridges.length) setCur(0);
            }} />
          </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>② CPDV 接触点位移变化（时间序列）</h3>
            <div style={{ height: 260 }}>
              <CpdvChart b={b} />
            </div>
          </div>
          <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>③ 多裂缝预测 · 梁纵断面（位置×深度比）</h3>
            <ProfileChart b={b} />
          </div>
          <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>④ 桥梁参数</h3>
            <ParamTable params={b.params} />
          </div>
        </div>
      </div>

      {showConsole && (
        <button
          onClick={() => setShowConsole(false)}
          aria-label="关闭 AI 命令控制台"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,.35)',
            zIndex: 890,
            border: 'none',
            cursor: 'pointer',
          }}
        />
      )}
      <div
        role="dialog"
        aria-label="AI 命令控制台"
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: 380,
          zIndex: 900,
          transform: showConsole ? 'translateX(0)' : 'translateX(calc(100% + 16px))',
          opacity: showConsole ? 1 : 0,
          pointerEvents: showConsole ? 'auto' : 'none',
          transition: 'transform .24s ease, opacity .2s ease',
        }}
      >
        <ChatPanel
          bridges={data.bridges}
          cur={cur}
          onRefresh={async () => {
            try {
              const result = await api.refreshDashboard();
              // Merge fresh signals into dashboard bridges (signals are loaded separately)
              const merged = { ...result.dashboard };
              if (result.signals) {
                merged.bridges = merged.bridges.map((br: any) => ({
                  ...br,
                  ...((result.signals as any)[br.id] ?? {}),
                }));
              }
              setData(merged);
            } catch (e) {
              const fresh = await api.fetchDashboard();
              setData(fresh);
            }
          }}
          onClose={() => setShowConsole(false)}
        />
      </div>

      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  );
}

/** Root app with ProgressProvider */
export default function App() {
  return (
    <ProgressProvider>
      <AppInner />
    </ProgressProvider>
  );
}