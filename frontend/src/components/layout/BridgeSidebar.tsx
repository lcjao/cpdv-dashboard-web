import type { Bridge } from '../../lib/types';
import BridgeCard from '../bridge/BridgeCard';

export default function BridgeSidebar({ bridges, cur, onSelect }: {
  bridges: Bridge[]; cur: number; onSelect: (i: number) => void;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 720, overflowY: 'auto', paddingRight: 2 }}>
      {bridges.map((b, i) => (
        <BridgeCard key={b.id} b={b} active={i === cur} onClick={() => onSelect(i)} />
      ))}
    </div>
  );
}
