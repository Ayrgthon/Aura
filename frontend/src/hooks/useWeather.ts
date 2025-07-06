import { useState, useEffect } from 'react';

interface WeatherData {
  temperature: number;
  weatherCode: number;
  description: string;
  humidity: number;
  windSpeed: number;
  city: string;
  country: string;
  loading: boolean;
  error: string | null;
}

interface ForecastData {
  date: string;
  maxTemp: number;
  minTemp: number;
  weatherCode: number;
  description: string;
  precipitation: number;
}

interface ExtendedWeatherData extends WeatherData {
  forecast: ForecastData[];
  feelsLike: number;
  pressure: number;
  visibility: number;
  uvIndex: number;
}

interface GeocodingResult {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  country: string;
  admin1: string;
}

const WEATHER_CODES: { [key: number]: string } = {
  0: 'Cielo despejado',
  1: 'Mayormente despejado',
  2: 'Parcialmente nublado',
  3: 'Nublado',
  45: 'Niebla',
  48: 'Niebla con escarcha',
  51: 'Llovizna ligera',
  53: 'Llovizna moderada',
  55: 'Llovizna intensa',
  56: 'Llovizna helada ligera',
  57: 'Llovizna helada intensa',
  61: 'Lluvia ligera',
  63: 'Lluvia moderada',
  65: 'Lluvia intensa',
  66: 'Lluvia helada ligera',
  67: 'Lluvia helada intensa',
  71: 'Nieve ligera',
  73: 'Nieve moderada',
  75: 'Nieve intensa',
  77: 'Granizo',
  80: 'Chubascos ligeros',
  81: 'Chubascos moderados',
  82: 'Chubascos intensos',
  85: 'Chubascos de nieve ligeros',
  86: 'Chubascos de nieve intensos',
  95: 'Tormenta',
  96: 'Tormenta con granizo ligero',
  99: 'Tormenta con granizo intenso'
};

export const useWeather = (city: string = 'Barranquilla') => {
  const [weatherData, setWeatherData] = useState<ExtendedWeatherData>({
    temperature: 0,
    weatherCode: 0,
    description: 'Cargando...',
    humidity: 0,
    windSpeed: 0,
    city: city,
    country: '',
    loading: true,
    error: null,
    forecast: [],
    feelsLike: 0,
    pressure: 0,
    visibility: 0,
    uvIndex: 0
  });

  const getWeatherDescription = (code: number): string => {
    return WEATHER_CODES[code] || 'Desconocido';
  };

  const fetchWeatherData = async (cityName: string) => {
    try {
      setWeatherData(prev => ({ ...prev, loading: true, error: null }));

      // Paso 1: Obtener coordenadas de la ciudad
      const geocodingUrl = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=1&language=es&format=json`;
      const geocodingResponse = await fetch(geocodingUrl);
      const geocodingData = await geocodingResponse.json();

      if (!geocodingData.results || geocodingData.results.length === 0) {
        throw new Error(`No se encontró la ciudad: ${cityName}`);
      }

      const location = geocodingData.results[0];

      // Paso 2: Obtener datos del clima actual y pronóstico
      const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${location.latitude}&longitude=${location.longitude}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature,pressure_msl,visibility,uv_index&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto`;
      const weatherResponse = await fetch(weatherUrl);
      const weatherData = await weatherResponse.json();

      if (!weatherData.current || !weatherData.daily) {
        throw new Error('No se pudieron obtener los datos del clima');
      }

      const current = weatherData.current;
      const daily = weatherData.daily;

      // Procesar pronóstico diario
      const forecast: ForecastData[] = daily.time.map((date: string, index: number) => ({
        date: new Date(date).toLocaleDateString('es-ES', { weekday: 'short', month: 'short', day: 'numeric' }),
        maxTemp: Math.round(daily.temperature_2m_max[index]),
        minTemp: Math.round(daily.temperature_2m_min[index]),
        weatherCode: daily.weather_code[index],
        description: getWeatherDescription(daily.weather_code[index]),
        precipitation: Math.round(daily.precipitation_sum[index] * 10) / 10
      }));

      setWeatherData({
        temperature: Math.round(current.temperature_2m),
        weatherCode: current.weather_code,
        description: getWeatherDescription(current.weather_code),
        humidity: current.relative_humidity_2m,
        windSpeed: Math.round(current.wind_speed_10m),
        city: location.name,
        country: location.country,
        loading: false,
        error: null,
        forecast: forecast.slice(1, 6), // Próximos 5 días (excluyendo hoy)
        feelsLike: Math.round(current.apparent_temperature),
        pressure: Math.round(current.pressure_msl),
        visibility: Math.round(current.visibility / 1000), // Convertir a km
        uvIndex: Math.round(current.uv_index)
      });

    } catch (error) {
      console.error('Error fetching weather data:', error);
      setWeatherData(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Error desconocido'
      }));
    }
  };

  useEffect(() => {
    fetchWeatherData(city);
  }, [city]);

  const refreshWeather = () => {
    fetchWeatherData(city);
  };

  return {
    weatherData,
    refreshWeather
  };
}; 