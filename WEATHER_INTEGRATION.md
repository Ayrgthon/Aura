# 🌤️ Integración del Clima con Open-Meteo

## Descripción

Esta integración permite obtener datos meteorológicos en tiempo real para cualquier ciudad del mundo utilizando las APIs gratuitas de Open-Meteo. La implementación incluye datos actuales y pronósticos extendidos.

## 🚀 Características

### Datos Actuales
- **Temperatura**: Temperatura actual en grados Celsius
- **Sensación térmica**: Temperatura percibida considerando humedad y viento
- **Humedad relativa**: Porcentaje de humedad en el aire
- **Velocidad del viento**: En kilómetros por hora
- **Código del clima**: Código numérico que describe las condiciones
- **Presión atmosférica**: En hectopascales (hPa)
- **Visibilidad**: Distancia de visibilidad en kilómetros
- **Índice UV**: Nivel de radiación ultravioleta

### Pronóstico Extendido
- **5 días de pronóstico**: Temperaturas máximas y mínimas
- **Condiciones del clima**: Descripción detallada del clima esperado
- **Precipitaciones**: Cantidad de lluvia esperada en milímetros
- **Iconos dinámicos**: Emojis que representan las condiciones

## 🛠️ Componentes Implementados

### 1. `useWeather` Hook
```typescript
// stellar-voice-display/src/hooks/useWeather.ts
const { weatherData, refreshWeather } = useWeather('Barranquilla');
```

**Funcionalidades:**
- Geocoding automático de ciudades
- Obtención de datos meteorológicos actuales
- Pronóstico extendido de 5 días
- Manejo de errores y estados de carga
- Actualización manual de datos

### 2. `WeatherPanel` Component
```typescript
// stellar-voice-display/src/components/WeatherPanel.tsx
<WeatherPanel city="Barranquilla" delay={0} />
```

**Características:**
- Panel holográfico con diseño cyberpunk
- Temperatura actual con icono del clima
- Descripción del clima en español
- Ubicación (ciudad y país)
- Humedad y velocidad del viento
- Botón de actualización manual

### 3. `WeatherForecast` Component
```typescript
// stellar-voice-display/src/components/WeatherForecast.tsx
<WeatherForecast forecast={weatherData.forecast} delay={1.2} />
```

**Funcionalidades:**
- Panel expandible con pronóstico
- Vista resumida y detallada
- Iconos del clima para cada día
- Temperaturas máximas y mínimas
- Precipitaciones esperadas

### 4. `WeatherDetails` Component
```typescript
// stellar-voice-display/src/components/WeatherDetails.tsx
<WeatherDetails 
  pressure={weatherData.pressure} 
  visibility={weatherData.visibility} 
  uvIndex={weatherData.uvIndex} 
  delay={1.4} 
/>
```

**Información adicional:**
- Presión atmosférica
- Visibilidad
- Índice UV con niveles de riesgo

## 🌍 APIs Utilizadas

### 1. Geocoding API
```
GET https://geocoding-api.open-meteo.com/v1/search
```

**Parámetros:**
- `name`: Nombre de la ciudad
- `count`: Número de resultados (1 para obtener la primera coincidencia)
- `language`: Idioma de respuesta (es para español)
- `format`: Formato de respuesta (json)

**Ejemplo de respuesta:**
```json
{
  "results": [
    {
      "id": 3689147,
      "name": "Barranquilla",
      "latitude": 10.96854,
      "longitude": -74.78132,
      "country": "Colombia",
      "admin1": "Atlántico"
    }
  ]
}
```

### 2. Weather Forecast API
```
GET https://api.open-meteo.com/v1/forecast
```

**Parámetros:**
- `latitude`: Latitud de la ubicación
- `longitude`: Longitud de la ubicación
- `current`: Variables meteorológicas actuales
- `daily`: Variables meteorológicas diarias
- `timezone`: Zona horaria automática

**Variables disponibles:**
- `temperature_2m`: Temperatura a 2 metros
- `relative_humidity_2m`: Humedad relativa
- `weather_code`: Código del clima
- `wind_speed_10m`: Velocidad del viento
- `apparent_temperature`: Sensación térmica
- `pressure_msl`: Presión atmosférica
- `visibility`: Visibilidad
- `uv_index`: Índice UV

## 📊 Códigos del Clima

| Código | Descripción |
|--------|-------------|
| 0 | Cielo despejado |
| 1 | Mayormente despejado |
| 2 | Parcialmente nublado |
| 3 | Nublado |
| 45 | Niebla |
| 48 | Niebla con escarcha |
| 51-55 | Llovizna (ligera a intensa) |
| 56-57 | Llovizna helada |
| 61-65 | Lluvia (ligera a intensa) |
| 66-67 | Lluvia helada |
| 71-75 | Nieve (ligera a intensa) |
| 77 | Granizo |
| 80-82 | Chubascos |
| 85-86 | Chubascos de nieve |
| 95 | Tormenta |
| 96-99 | Tormenta con granizo |

## 🎨 Diseño y UX

### Estilo Cyberpunk
- Paneles holográficos con efectos de cristal
- Animaciones de flotación con delays escalonados
- Colores neón y efectos de brillo
- Iconos emoji para representar el clima
- Transiciones suaves y efectos hover

### Responsive Design
- Adaptable a diferentes tamaños de pantalla
- Paneles que se reorganizan automáticamente
- Texto legible en todos los dispositivos

### Interactividad
- Botones de actualización manual
- Paneles expandibles para más información
- Estados de carga y error
- Feedback visual para las acciones del usuario

## 🔧 Configuración

### Instalación
No se requieren dependencias adicionales. Las APIs de Open-Meteo son gratuitas y no requieren autenticación.

### Uso Básico
```typescript
import { useWeather } from '@/hooks/useWeather';

function MyComponent() {
  const { weatherData, refreshWeather } = useWeather('Tu Ciudad');
  
  return (
    <div>
      <p>Temperatura: {weatherData.temperature}°C</p>
      <p>Clima: {weatherData.description}</p>
      <button onClick={refreshWeather}>Actualizar</button>
    </div>
  );
}
```

### Personalización
- Cambiar la ciudad por defecto en el hook
- Modificar los delays de animación
- Personalizar los colores y estilos
- Agregar más variables meteorológicas

## 🐛 Solución de Problemas

### Error de CORS
Las APIs de Open-Meteo no tienen restricciones de CORS, por lo que funcionan directamente desde el navegador.

### Ciudad no encontrada
El sistema intenta encontrar la ciudad más cercana. Si no encuentra resultados, muestra un error descriptivo.

### Datos no disponibles
Algunas variables pueden no estar disponibles en ciertas ubicaciones. El sistema maneja estos casos mostrando valores por defecto.

### Límites de API
Open-Meteo tiene límites generosos:
- 10,000 requests por día
- Sin autenticación requerida
- Datos actualizados cada hora

## 🚀 Mejoras Futuras

- [ ] Soporte para múltiples ciudades
- [ ] Gráficos de temperatura y precipitaciones
- [ ] Alertas meteorológicas
- [ ] Integración con mapas
- [ ] Historial de datos meteorológicos
- [ ] Notificaciones push para cambios de clima
- [ ] Modo oscuro/claro automático basado en la hora
- [ ] Widgets personalizables

## 📝 Notas

- Los datos se actualizan automáticamente al cargar la página
- El pronóstico incluye los próximos 5 días
- Todas las descripciones están en español
- Los iconos se adaptan automáticamente al código del clima
- La implementación es completamente gratuita y sin límites estrictos 