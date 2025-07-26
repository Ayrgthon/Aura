import React from 'react';
import { Cpu, MemoryStick, HardDrive, Monitor } from 'lucide-react';
import { useSystemStats } from '@/hooks/useSystemStats';
import HolographicPanel from './HolographicPanel';

type StatKey = 'cpu' | 'gpu' | 'ram' | 'ssd';

const icons = {
  cpu: <Cpu className="w-3.5 h-3.5" style={{color: 'rgb(34, 211, 238)', filter: 'drop-shadow(0 0 8px rgba(34, 211, 238, 0.6))'}} />,
  gpu: <Monitor className="w-3.5 h-3.5" style={{color: 'rgb(34, 211, 238)', filter: 'drop-shadow(0 0 8px rgba(34, 211, 238, 0.6))'}} />,
  ram: <MemoryStick className="w-3.5 h-3.5" style={{color: 'rgb(34, 211, 238)', filter: 'drop-shadow(0 0 8px rgba(34, 211, 238, 0.6))'}} />,
  ssd: <HardDrive className="w-3.5 h-3.5" style={{color: 'rgb(34, 211, 238)', filter: 'drop-shadow(0 0 8px rgba(34, 211, 238, 0.6))'}} />,
};

const labels = {
  cpu: 'CPU',
  gpu: 'GPU',
  ram: 'RAM',
  ssd: 'SSD',
};

const accent = {
  cpu: 'text-white/90',
  gpu: 'text-white/90',
  ram: 'text-white/90',
  ssd: 'text-white/90',
};

interface SystemStatsPanelProps {
  statKey?: StatKey;
}

const SystemStatsPanel: React.FC<SystemStatsPanelProps> = ({ statKey }) => {
  const { stats } = useSystemStats();

  const renderValue = (val: number | null, key: keyof typeof icons) => (
    <span className={`text-sm font-bold ${accent[key]} transition-all duration-500 text-white/90`}>{
      val !== null ? `${val.toFixed(0)}%` : '--%'
    }</span>
  );

  if (statKey) {
    return (
      <>
        {icons[statKey]}
        {renderValue(stats[statKey], statKey)}
      </>
    );
  }

  // Grilla completa (no usada en el nuevo layout, pero útil para referencia)
  return (
    <div className="grid grid-cols-2 grid-rows-2 gap-2">
      {(['cpu', 'gpu', 'ram', 'ssd'] as const).map((key, i) => (
        <HolographicPanel
          key={key}
          title={labels[key]}
          delay={0.1 * i}
          className="w-24 px-1.5 py-1.5 float min-w-0"
        >
          <div className="flex flex-col items-center justify-center gap-0.5">
            {icons[key]}
            {renderValue(stats[key], key)}
          </div>
        </HolographicPanel>
      ))}
    </div>
  );
};

export default SystemStatsPanel; 