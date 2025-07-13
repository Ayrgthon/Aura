import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Calendar } from 'lucide-react';
import HolographicPanel from './HolographicPanel';

interface ForecastData {
  date: string;
  maxTemp: number;
  minTemp: number;
  weatherCode: number;
  description: string;
  precipitation: number;
}

interface WeatherForecastProps {
  forecast: ForecastData[];
  delay?: number;
}

const WeatherForecast: React.FC<WeatherForecastProps> = ({ 
  forecast, 
  delay = 0.1 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getWeatherIcon = (code: number) => {
    if (code >= 0 && code <= 3) return '☀️';
    if (code >= 45 && code <= 48) return '🌫️';
    if (code >= 51 && code <= 67) return '🌧️';
    if (code >= 71 && code <= 77) return '❄️';
    if (code >= 80 && code <= 86) return '🌦️';
    if (code >= 95 && code <= 99) return '⛈️';
    return '🌤️';
  };

  if (!forecast || forecast.length === 0) {
    return null;
  }

  return (
    <HolographicPanel title="Pronóstico" delay={delay}>
      <div className="text-sm space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="w-3 h-3" />
            <span>Próximos días</span>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs text-primary hover:text-primary/80 transition-colors"
          >
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        {isExpanded ? (
          <div className="space-y-2">
            {forecast.map((day, index) => (
              <div key={index} className="flex items-center justify-between p-2 rounded bg-glass-panel/20">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{getWeatherIcon(day.weatherCode)}</span>
                  <div>
                    <div className="text-xs font-medium">{day.date}</div>
                    <div className="text-xs text-muted-foreground">{day.description}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-medium">
                    {day.maxTemp}° / {day.minTemp}°
                  </div>
                  {day.precipitation > 0 && (
                    <div className="text-xs text-primary">
                      {day.precipitation}mm
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="text-xs text-muted-foreground">
              {forecast.length} días
            </div>
            <div className="text-xs">
              {forecast[0].maxTemp}° / {forecast[0].minTemp}°
            </div>
          </div>
        )}
      </div>
    </HolographicPanel>
  );
};

export default WeatherForecast; 