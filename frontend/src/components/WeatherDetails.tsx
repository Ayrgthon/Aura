import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Eye, Gauge, Sun } from 'lucide-react';
import HolographicPanel from './HolographicPanel';

interface WeatherDetailsProps {
  pressure: number;
  visibility: number;
  uvIndex: number;
  delay?: number;
}

const WeatherDetails: React.FC<WeatherDetailsProps> = ({ 
  pressure, 
  visibility, 
  uvIndex, 
  delay = 0.15 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getUVLevel = (uv: number): string => {
    if (uv <= 2) return 'Bajo';
    if (uv <= 5) return 'Moderado';
    if (uv <= 7) return 'Alto';
    if (uv <= 10) return 'Muy alto';
    return 'Extremo';
  };

  const getUVColor = (uv: number): string => {
    if (uv <= 2) return 'text-neon-cyan';
    if (uv <= 5) return 'text-accent';
    if (uv <= 7) return 'text-primary';
    if (uv <= 10) return 'text-destructive';
    return 'text-neon-magenta';
  };

  return (
    <HolographicPanel title="Detalles" delay={delay}>
      <div className="text-sm space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Información adicional
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs text-primary hover:text-primary/80 transition-colors"
          >
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        {isExpanded ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-2 rounded bg-glass-panel/20">
              <div className="flex items-center gap-2">
                <Gauge className="w-3 h-3 text-primary" />
                <div>
                  <div className="text-xs font-medium">Presión</div>
                  <div className="text-xs text-muted-foreground">Atmosférica</div>
                </div>
              </div>
              <div className="text-xs font-medium">
                {pressure} hPa
              </div>
            </div>

            <div className="flex items-center justify-between p-2 rounded bg-glass-panel/20">
              <div className="flex items-center gap-2">
                <Eye className="w-3 h-3 text-neon-cyan" />
                <div>
                  <div className="text-xs font-medium">Visibilidad</div>
                  <div className="text-xs text-muted-foreground">Distancia</div>
                </div>
              </div>
              <div className="text-xs font-medium">
                {visibility} km
              </div>
            </div>

            <div className="flex items-center justify-between p-2 rounded bg-glass-panel/20">
              <div className="flex items-center gap-2">
                <Sun className="w-3 h-3 text-accent" />
                <div>
                  <div className="text-xs font-medium">Índice UV</div>
                  <div className="text-xs text-muted-foreground">Radiación</div>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-xs font-medium ${getUVColor(uvIndex)}`}>
                  {uvIndex} - {getUVLevel(uvIndex)}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Presión: {pressure} hPa</span>
            <span>UV: {uvIndex}</span>
          </div>
        )}
      </div>
    </HolographicPanel>
  );
};

export default WeatherDetails; 