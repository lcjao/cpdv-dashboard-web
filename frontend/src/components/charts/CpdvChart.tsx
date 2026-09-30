import { useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend,
} from 'chart.js';
import type { Bridge } from '../../lib/types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

// G19: 多位置曲线调色板（8 色，循环取用）
const PALETTE = ['#2f6fed', '#e74c3c', '#27ae60', '#f39c12', '#8e44ad', '#16a085', '#c0392b', '#2980b9'];

export default function CpdvChart({ b }: { b: Bridge }) {
  // G22: 信号显示模式切换
  const [showMode, setShowMode] = useState<'combined' | 'multi'>('combined');
  
  // Use inline data from bridge (loaded via /api/dashboard or /api/signals/refresh)
  const combined = b.combined_cpdv && b.combined_cpdv.length > 0 ? b.combined_cpdv : null;
  const series = (!combined && b.cpdv_signals && b.cpdv_signals.length > 0) ? b.cpdv_signals : null;

  if (!combined && !series && (!b.cpdv || b.cpdv.length < 2)) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--sub)', fontSize: 13 }}>
        暂无 CPDV 信号数据 — 对该桥执行「计算CPDV」后刷新看板
      </div>
    );
  }

  let labels: number[] = [];
  let datasets: { label: string; data: number[]; borderColor: string; backgroundColor: string; pointRadius: number; borderWidth: number }[] = [];

  // G22: 根据用户选择的模式渲染
  if (showMode === 'combined' && combined) {
    const len = combined.length;
    labels = combined.map((_: number, i: number) => i / (len - 1));
    datasets = [{
      label: '多裂缝组合 CPDV',
      data: combined,
      borderColor: '#2f6fed',
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 2,
    }];
  } else if (showMode === 'multi' && series && series.length > 0) {
    const len = series[0].signal.length;
    labels = series[0].signal.map((_: number, i: number) => i / (len - 1));
    datasets = series.map((s: any, idx: number) => ({
      label: s.depth !== undefined ? `位置 ${s.pos} m · d=${s.depth}` : `位置 ${s.pos} m`,
      data: s.signal,
      borderColor: PALETTE[idx % PALETTE.length],
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 1.5,
    }));
  } else if (combined) {
    const len = combined.length;
    labels = combined.map((_: number, i: number) => i / (len - 1));
    datasets = [{
      label: '多裂缝组合 CPDV',
      data: combined,
      borderColor: '#2f6fed',
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 2,
    }];
  } else if (series && series.length > 0) {
    const len = series[0].signal.length;
    labels = series[0].signal.map((_: number, i: number) => i / (len - 1));
    datasets = series.map((s: any, idx: number) => ({
      label: s.depth !== undefined ? `位置 ${s.pos} m · d=${s.depth}` : `位置 ${s.pos} m`,
      data: s.signal,
      borderColor: PALETTE[idx % PALETTE.length],
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 1.5,
    }));
  } else {
    labels = b.cpdv.map((_: number, i: number) => i / (b.cpdv.length - 1));
    datasets = [{
      label: 'CPDV 信号',
      data: b.cpdv,
      borderColor: '#2f6fed',
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 1.5,
    }];
  }

  const data = { labels, datasets };
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    scales: {
      x: { title: { display: true, text: '采样点（归一化 0~1）' } },
      y: { title: { display: true, text: 'CPDV (m)' } },
    },
  };
  
  // 判断是否可切换
  const canSwitch = !!(combined && series && series.length > 0);
  
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 模式切换按钮 */}
      {canSwitch && (
        <div style={{
          display: 'flex',
          gap: 4,
          marginBottom: 8,
          justifyContent: 'flex-end',
        }}>
          <button
            type="button"
            onClick={() => setShowMode('combined')}
            style={{
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: showMode === 'combined' ? 600 : 400,
              background: showMode === 'combined' ? 'var(--blue)' : 'var(--bg)',
              color: showMode === 'combined' ? '#fff' : 'var(--ink)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            组合信号
          </button>
          <button
            type="button"
            onClick={() => setShowMode('multi')}
            style={{
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: showMode === 'multi' ? 600 : 400,
              background: showMode === 'multi' ? 'var(--blue)' : 'var(--bg)',
              color: showMode === 'multi' ? '#fff' : 'var(--ink)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            多位置信号
          </button>
        </div>
      )}
      <Line data={data} options={opts} height={260} />
    </div>
  );
}
