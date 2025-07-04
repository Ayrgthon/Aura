import React from 'react';
import { Cpu, MemoryStick, HardDrive, MonitorSmartphone } from 'lucide-react';
import { useSystemStats } from '@/hooks/useSystemStats';
import HolographicPanel from './HolographicPanel';

type StatKey = 'cpu' | 'gpu' | 'ram' | 'ssd';

const icons = {
  cpu: <Cpu className="w-3.5 h-3.5 text-cyan-400" />,
  gpu: <MonitorSmartphone className="w-3.5 h-3.5 text-fuchsia-400" />,
  ram: <MemoryStick className="w-3.5 h-3.5 text-green-400" />,
  ssd: <HardDrive className="w-3.5 h-3.5 text-yellow-400" />,
};

const labels = {
  cpu: 'CPU',
  gpu: 'GPU',
  ram: 'RAM',
  ssd: 'SSD',
};

const accent = {
  cpu: 'text-cyan-400',
  gpu: 'text-fuchsia-400',
  ram: 'text-green-400',
  ssd: 'text-yellow-400',
};

interface SystemStatsPanelProps {
  statKey?: StatKey;
}

const SystemStatsPanel: React.FC<SystemStatsPanelProps> = ({ statKey }) => {
  const { stats } = useSystemStats();

  const renderValue = (val: number | null, key: keyof typeof icons) => (
    <span className={`text-sm font-bold ${accent[key]} transition-all duration-500`}>{
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