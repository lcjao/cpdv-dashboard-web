import { useEffect, useState } from 'react';
import type { DashboardData } from './lib/types';
import { api } from './lib/api-client';
import Header from './components/layout/Header';
import BridgeSidebar from './components/layout/BridgeSidebar';
import ChatPanel from './components/layout/ChatPanel';
import ParamTable from './components/bridge/ParamTable';
import CpdvChart from './components/charts/CpdvChart';
import ProfileChart from './components/charts/ProfileChart';

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [cur, setCur] = useState(0);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.fetchDashboard().then(setData).catch(e => setErr(String(e)));
  }, []);

  if (err) return <div style={{ padding: 40, color: 'var(--red)' }}>加载失败: {err}</div>;
  if (!data) return <div style={{ padding: 40 }}>加载中…</div>;

  const b = data.bridges[cur];

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '16px 20px 40px' }}>
      <Header meta={data.meta} />
      <div style={{ display: 'grid', gridTemplateColumns: '290px 1fr 320px', gap: 14, alignItems: 'start' }}>
        <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>① 桥梁工况</h3>
          <BridgeSidebar bridges={data.bridges} cur={cur} onSelect={setCur} />
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
        <ChatPanel
          bridges={data.bridges}
          cur={cur}
          onRefresh={() => api.fetchDashboard().then(setData)}
        />
      </div>
    </div>
  );
}
