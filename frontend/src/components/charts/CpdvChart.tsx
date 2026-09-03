import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend,
} from 'chart.js';
import type { Bridge } from '../../lib/types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

export default function CpdvChart({ b }: { b: Bridge }) {
  const labels = b.cpdv.map((_, i) => i / (b.cpdv.length - 1));
  const data = {
    labels,
    datasets: [{
      label: 'CPDV 信号',
      data: b.cpdv,
      borderColor: '#2f6fed',
      backgroundColor: 'transparent',
      pointRadius: 0,
      borderWidth: 1.5,
    }],
  };
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    scales: {
      x: { title: { display: true, text: '采样点（归一化 0~1）' } },
      y: { title: { display: true, text: 'CPDV (m)' } },
    },
  };
  return <Line data={data} options={opts} height={260} />;
}
