import React from 'react';
import { RefreshCw, Thermometer, Droplets, Wind } from 'lucide-react';
import { useWeather } from '@/hooks/useWeather';
import HolographicPanel from './HolographicPanel';

interface WeatherPanelProps {
  city?: string;
  delay?: number;
}

const WeatherPanel: React.FC<WeatherPanelProps> = ({ 
  city = 'Barranquilla', 
  delay = 0 
}) => {
  const { weatherData, refreshWeather } = useWeather(city);

  const getWeatherIcon = (code: number) => {
    if (code >= 0 && code <= 3) return '☀️'; // Despejado a nublado
    if (code >= 45 && code <= 48) return '🌫️'; // Niebla
    if (code >= 51 && code <= 67) return '🌧️'; // Lluvia
    if (code >= 71 && code <= 77) return '❄️'; // Nieve
    if (code >= 80 && code <= 86) return '🌦️'; // Chubascos
    if (code >= 95 && code <= 99) return '⛈️'; // Tormenta
    return '🌤️'; // Por defecto
  };

  if (weatherData.loading) {
    return (
      <HolographicPanel title="Weather" delay={delay}>
        <div className="text-sm space-y-2">
          <div className="text-lg font-light animate-pulse">Cargando...</div>
          <div className="text-muted-foreground">Obteniendo datos</div>
        </div>
      </HolographicPanel>
    );
  }

  if (weatherData.error) {
    return (
      <HolographicPanel title="Weather" delay={delay}>
        <div className="text-sm space-y-2">
          <div className="text-red-400 text-xs">Error</div>
          <div className="text-muted-foreground text-xs">{weatherData.error}</div>
          <button 
            onClick={refreshWeather}
            className="text-xs text-primary hover:text-primary/80 transition-colors"
          >
            Reintentar
          </button>
        </div>
      </HolographicPanel>
    );
  }

  return (
    <HolographicPanel title="Weather" delay={delay}>
      <div className="text-sm space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-lg font-light">
            {weatherData.temperature}°C
          </div>
          <div className="text-2xl">
            {getWeatherIcon(weatherData.weatherCode)}
          </div>
        </div>
        
        <div className="text-muted-foreground text-xs">
          {weatherData.description}
        </div>
        
        <div className="text-xs opacity-60">
          {weatherData.city}, {weatherData.country}
        </div>
        
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Droplets className="w-3 h-3" />
            <span>{weatherData.humidity}%</span>
          </div>
          <div className="flex items-center gap-1">
            <Wind className="w-3 h-3" />
            <span>{weatherData.windSpeed} km/h</span>
          </div>
        </div>
        
        <div className="text-xs text-muted-foreground">
          Sensación: {weatherData.feelsLike}°C
        </div>
        
        <button 
          onClick={refreshWeather}
          className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" />
          Actualizar
        </button>
      </div>
    </HolographicPanel>
  );
};

export default WeatherPanel; 