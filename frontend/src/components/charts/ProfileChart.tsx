import { useEffect, useRef } from 'react';
import type { Bridge } from '../../lib/types';

export default function ProfileChart({ b }: { b: Bridge }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current!;
    const ctx = cv.getContext('2d')!;
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);
    const L = b.params.L;
    const pad = { l: 50, r: 16, t: 20, b: 34 };
    const X = (pos: number) => pad.l + (W - pad.l - pad.r) * (pos / L);

    // G17: 动态 depth 轴上限 = max(0.35, 数据最大 depth) × 1.15 padding
    // 旧版写死 0.35，导致真实裂缝 depth=0.5 时被切到图外。
    const dataMax = Math.max(
      0,
      ...b.true_cracks.map(t => t.depth || 0),
      ...b.pred_cracks.map(p => p.depth || 0),
    );
    const yMax = Math.max(0.35, dataMax) * 1.15;
    // 刻度 0~1，向上对齐到 0.05 整数倍更整齐
    const yMaxAligned = Math.ceil(yMax * 20) / 20;
    const Y = (depth: number) => pad.t + (H - pad.t - pad.b) * (1 - depth / yMaxAligned);

    // 梁体背景
    ctx.fillStyle = '#f0f2f5';
    ctx.fillRect(pad.l, pad.t, W - pad.l - pad.r, H - pad.t - pad.b);

    // 刻度
    ctx.strokeStyle = '#e3e8f0'; ctx.fillStyle = '#98a2b3'; ctx.font = '10px Consolas';
    for (let i = 0; i <= 5; i++) {
      const x = pad.l + (W - pad.l - pad.r) * i / 5;
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
      ctx.textAlign = 'center'; ctx.fillText((L * i / 5).toFixed(0), x, H - pad.b + 14);
    }
    // Y 轴刻度（depth 0/25%/50%/75%/100%）
    for (let i = 0; i <= 4; i++) {
      const ratio = i / 4;
      const y = pad.t + (H - pad.t - pad.b) * ratio;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y);
      ctx.strokeStyle = '#e3e8f0'; ctx.stroke();
      ctx.fillStyle = '#98a2b3'; ctx.textAlign = 'right';
      ctx.fillText(((1 - ratio) * yMaxAligned * 100).toFixed(0) + '%', pad.l - 4, y + 4);
    }

    // 真实裂缝（绿三角）
    b.true_cracks.forEach(t => {
      const x = X(t.pos), y = Y(t.depth);
      ctx.fillStyle = '#1fa25c';
      ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x - 7, y + 7); ctx.lineTo(x + 7, y + 7); ctx.closePath(); ctx.fill();
    });
    // 预测裂缝（蓝圆 + 置信度）
    b.pred_cracks.forEach(p => {
      const x = X(p.pos), y = Y(p.depth);
      ctx.fillStyle = '#2f6fed';
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = '9px Consolas'; ctx.textAlign = 'center';
      ctx.fillText((p.conf! * 100).toFixed(0), x, y + 3);
    });
    // 漏检标红叉
    b.true_cracks.forEach((t, ti) => {
      const hit = b.pred_cracks.some(p => p.match === ti);
      if (!hit) {
        const x = X(t.pos), y = Y(t.depth);
        ctx.strokeStyle = '#d94141'; ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - 6, y - 6); ctx.lineTo(x + 6, y + 6);
        ctx.moveTo(x + 6, y - 6); ctx.lineTo(x - 6, y + 6);
        ctx.stroke();
      }
    });
    // 匹配连线
    b.pred_cracks.forEach(p => {
      if (p.match != null) {
        const t = b.true_cracks[p.match];
        ctx.strokeStyle = '#98a2b3'; ctx.lineWidth = 0.8; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(X(t.pos), Y(t.depth)); ctx.lineTo(X(p.pos), Y(p.depth)); ctx.stroke();
        ctx.setLineDash([]);
      }
    });
  }, [b]);

  return <canvas ref={ref} width={1100} height={180} style={{ width: '100%', height: 180, display: 'block' }} />;
}
