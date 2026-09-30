import type { BridgeParams } from '../../lib/types';

const ROWS: [keyof BridgeParams, string][] = [
  ['L', '跨长 (m)'], ['E', '弹性模量 (GPa)'], ['I', '惯性矩 (m⁴)'],
  ['m', '线密度 (kg/m)'], ['mv', '车辆质量 (kg)'],
  ['kv', '悬挂刚度 (kN/m)'], ['cv', '阻尼 (N·s/m)'], ['V', '车速 (m/s)'],
];

export default function ParamTable({ params }: { params: BridgeParams }) {
  return (
    <div>
      {ROWS.map(([k, label]) => (
        <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <label style={{ color: 'var(--sub)', fontSize: 12 }}>{label}</label>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>
            {k === 'E' ? (params.E / 1e9).toFixed(1)
             : k === 'I' ? params.I.toFixed(4)
             : k === 'kv' ? (params.kv / 1e3).toFixed(1)
             : typeof params[k] === 'number' ? (params[k] as number).toFixed(k === 'm' ? 0 : 1)
             : String(params[k])}
          </span>
        </div>
      ))}
    </div>
  );
}
