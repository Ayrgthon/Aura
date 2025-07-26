import React from 'react';
import { Card } from '@/components/ui/card';

interface HolographicPanelProps {
  title: string;
  children: React.ReactNode;
  delay?: number;
  className?: string;
}

const HolographicPanel: React.FC<HolographicPanelProps> = ({ 
  title, 
  children, 
  delay = 0,
  className = ""
}) => {
  return (
    <Card 
      className={`glass-panel p-4 float ${className}`}
      style={{ 
        animationDelay: `${delay}s`,
        minWidth: '160px'
      }}
    >
      {/* Panel header with holographic effect */}
      <div className="border-b border-primary/20 pb-2 mb-3">
        <h3 className="text-sm font-light text-hologram uppercase tracking-wider">
          {title}
        </h3>
      </div>
      
      {/* Panel content */}
      <div className="text-foreground/90">
        {children}
      </div>
      
      {/* Holographic scan line effect */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-lg">
        <div 
          className="absolute w-full h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent animate-pulse"
          style={{
            top: '20%',
            animationDuration: '2s',
            animationDelay: `${delay + 1}s`
          }}
        />
      </div>
      
      {/* Corner accents */}
      <div className="absolute top-0 left-0 w-3 h-3 border-l border-t border-accent/50" />
      <div className="absolute top-0 right-0 w-3 h-3 border-r border-t border-accent/50" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-l border-b border-accent/50" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-r border-b border-accent/50" />
    </Card>
  );
};

export default HolographicPanel;