import React from 'react';
import { Card } from '@/components/ui/card';

interface ModernGlassCardProps {
  title: string;
  children: React.ReactNode;
  delay?: number;
  className?: string;
  icon?: React.ReactNode;
  accentColor?: 'cyan' | 'magenta' | 'blue' | 'green' | 'yellow' | 'pink';
}

const ModernGlassCard: React.FC<ModernGlassCardProps> = ({ 
  title, 
  children, 
  delay = 0,
  className = "",
  icon,
  accentColor = 'cyan'
}) => {
  const accentColors = {
    cyan: 'from-cyan-400/20 to-cyan-600/20',
    magenta: 'from-pink-400/20 to-pink-600/20',
    blue: 'from-blue-400/20 to-blue-600/20',
    green: 'from-green-400/20 to-green-600/20',
    yellow: 'from-yellow-400/20 to-yellow-600/20',
    pink: 'from-pink-400/20 to-pink-600/20'
  };

  const borderColors = {
    cyan: 'border-cyan-400/30',
    magenta: 'border-pink-400/30',
    blue: 'border-blue-400/30',
    green: 'border-green-400/30',
    yellow: 'border-yellow-400/30',
    pink: 'border-pink-400/30'
  };

  return (
    <Card 
      className={`relative overflow-hidden transform-gpu transition-all duration-500 hover:scale-105 float-modern ${className}`}
      style={{ 
        animationDelay: `${delay}s`,
        minWidth: '160px',
        background: 'rgba(255, 255, 255, 0.05)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        boxShadow: `
          0 8px 32px rgba(0, 0, 0, 0.3),
          inset 0 1px 0 rgba(255, 255, 255, 0.1),
          0 0 0 1px rgba(255, 255, 255, 0.02)
        `,
        transform: 'perspective(1000px) rotateX(1deg) rotateY(0.5deg)',
        transformStyle: 'preserve-3d'
      }}
    >
      {/* Glass reflection effect - top left (rectangular) */}
      <div className="absolute top-0 left-0 w-24 h-20 bg-gradient-to-br from-white/25 via-white/18 via-white/10 to-transparent rounded-tl-lg z-5 glass-reflection" />
      
      {/* Subtle accent border */}
      <div className={`absolute inset-0 rounded-lg border border-${accentColor}-400/10`} />
      
      {/* Inner glass panel */}
      <div className="relative z-20 p-3">
        {/* Header with icon and title */}
        <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/10">
          {icon && (
            <div className="text-lg opacity-90" style={{
              filter: 'drop-shadow(0 0 8px rgba(34, 211, 238, 0.8))',
              color: 'rgb(34, 211, 238)'
            }}>
              {icon}
            </div>
          )}
          <h3 className="text-sm font-medium text-white/90 uppercase tracking-wider">
            {title}
          </h3>
        </div>
        
        {/* Content */}
        <div className="text-white/80">
          {children}
        </div>
      </div>

      {/* Subtle corner accents */}
      <div className="absolute top-0 left-0 w-3 h-3 border-l border-t border-white/15 rounded-tl-lg" />
      <div className="absolute top-0 right-0 w-3 h-3 border-r border-t border-white/15 rounded-tr-lg" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-l border-b border-white/15 rounded-bl-lg" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-r border-b border-white/15 rounded-br-lg" />

    </Card>
  );
};

export default ModernGlassCard; 