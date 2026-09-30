import type { Bridge } from '../../lib/types';
import BridgeCard from '../bridge/BridgeCard';
import { api } from '../../lib/api-client';

export default function BridgeSidebar({ bridges, cur, onSelect, onRefresh }: {
  bridges: Bridge[]; cur: number; onSelect: (i: number) => void; onRefresh?: () => Promise<void>;
}) {
  const handleDelete = async (id: string) => {
    await api.deleteBridge(id);
    if (onRefresh) await onRefresh();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 720, overflowY: 'auto', paddingRight: 2 }}>
      {bridges.map((b, i) => (
        <BridgeCard
          key={b.id}
          b={b}
          active={i === cur}
          onClick={() => onSelect(i)}
          onDelete={handleDelete}
          isRegistered={b.status === 'registered'}
        />
      ))}
    </div>
  );
}
