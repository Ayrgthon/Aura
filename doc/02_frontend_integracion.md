# Frontend e Integración Backend - Documentación Técnica Detallada

## Descripción General

El frontend de Aura es una aplicación React moderna con TypeScript que integra múltiples sistemas complejos: WebSocket optimizado, WebRTC para audio, APIs del sistema, clima, y una arquitectura de componentes futuristas. La integración backend incluye manejo avanzado de buffers de audio, sincronización de animaciones, y comunicación bidireccional en tiempo real.

## Arquitectura del Frontend

### Stack Tecnológico
- **React 18** con TypeScript
- **Vite** para bundling optimizado
- **Tailwind CSS** con configuraciones personalizadas
- **WebSocket** para comunicación tiempo real
- **WebRTC** para audio de alta calidad
- **Fetch API** para APIs REST
- **shadcn/ui** para componentes base
- **Lucide React** para iconografía

### Estructura de Componentes

```
frontend/
├── src/
│   ├── components/
│   │   ├── VoiceAssistant.tsx      # Componente principal
│   │   ├── EnergyOrb.tsx           # Orbe central con animaciones
│   │   ├── ModernGlassCard.tsx     # Cards con efecto glassmorphism
│   │   ├── SystemStatsPanel.tsx    # Panel de estadísticas del sistema
│   │   ├── WeatherPanel.tsx        # Panel del clima
│   │   └── ui/                     # shadcn/ui components
│   ├── hooks/
│   │   ├── useWebSocket.ts         # WebSocket estándar
│   │   ├── useOptimizedWebSocket.ts # WebSocket + WebRTC
│   │   ├── useWebRTC.ts            # WebRTC puro
│   │   ├── useWeather.ts           # API del clima
│   │   └── useSystemStats.ts       # Stats del sistema
│   └── pages/
│       └── Index.tsx               # Página principal
```

## Componente Principal: VoiceAssistant

### Arquitectura del Estado (`VoiceAssistant.tsx:16-46`)

```typescript
// Estados principales del sistema
const [isListening, setIsListening] = useState(false);        // Escucha activa
const [isSpeaking, setIsSpeaking] = useState(false);          // TTS reproduciéndose
const [isStreaming, setIsStreaming] = useState(false);        // Audio streaming
const [isAuraReady, setIsAuraReady] = useState(false);        // Cliente Gemini listo
const [isProcessing, setIsProcessing] = useState(false);      // Procesando con IA

// Estados de transcripción
const [lastRecognizedText, setLastRecognizedText] = useState<string>('');
const [lastResponse, setLastResponse] = useState<string>('');
const [liveTranscription, setLiveTranscription] = useState<string>('');

// Estados de configuración
const [modelType, setModelType] = useState<'gemini' | 'ollama'>('gemini');
const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
const [ttsEngine, setTtsEngine] = useState<'gtts' | 'elevenlabs'>('gtts');
const [currentLanguage, setCurrentLanguage] = useState<'es' | 'en'>('es');
```

### Gestión de Modelos IA (`VoiceAssistant.tsx:47-107`)

**Modelos Gemini Disponibles:**
```typescript
const geminiModels = [
  'gemini-2.5-pro',      // Modelo principal, más capaz
  'gemini-2.5-flash',    // Rápido, balanceado
  'gemini-2.5-flash-lite', // Ligero
  'gemini-2.0-flash',    // Versión anterior
  'gemini-2.0-flash-lite' // Anterior ligero
];
```

**Integración con Ollama:**
```typescript
const fetchOllamaModels = async () => {
  try {
    const response = await fetch('http://localhost:11434/api/tags');
    const data = await response.json();
    const models = data.models?.map((model: any) => model.name) || [];
    setOllamaModels(models);
  } catch (error) {
    console.error('Error fetching Ollama models:', error);
    setOllamaModels([]);
  }
};
```

**Cambio dinámico de modelos:**
- Reinicializa automáticamente el cliente Aura cuando cambia el modelo
- Notificación inmediata al backend via WebSocket
- UI responsive que refleja el estado de inicialización

### Control de Sistema (`VoiceAssistant.tsx:138-198`)

**Apagado del Sistema:**
```typescript
const handleSystemShutdown = async () => {
  setIsShuttingDown(true);
  
  // Envío dual: WebSocket + HTTP
  if (isConnected) {
    sendMessage({ type: 'shutdown_system' });
  }
  
  await fetch('http://localhost:8000/shutdown', { 
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  
  // Limpieza de estados locales
  setIsSystemOn(false);
  setIsAuraReady(false);
  // ... más limpieza
};
```

**Características del control:**
- **Redundancia**: WebSocket + HTTP para máxima confiabilidad
- **Estados coherentes**: Sincronización entre UI y backend
- **Manejo de errores**: Fallbacks y notificaciones apropiadas

## Sistema de Audio y WebRTC

### Hook useWebRTC (`useWebRTC.ts:9-229`)

**Configuración de Audio de Alta Calidad:**
```typescript
const stream = await navigator.mediaDevices.getUserMedia({
  audio: {
    echoCancellation: true,    // Cancelación de eco
    noiseSuppression: true,    // Supresión de ruido
    autoGainControl: true,     // Control automático de ganancia
    sampleRate: 16000,         // Óptimo para STT
    channelCount: 1            // Mono para eficiencia
  }
});
```

**Procesamiento de Audio en Tiempo Real:**
```typescript
processor.onaudioprocess = (event) => {
  if (onAudioData && isRecording) {
    const inputBuffer = event.inputBuffer;
    const inputData = inputBuffer.getChannelData(0);
    
    // Conversión Float32 -> Int16 para backend
    const buffer = new ArrayBuffer(inputData.length * 2);
    const view = new Int16Array(buffer);
    
    for (let i = 0; i < inputData.length; i++) {
      view[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
    }
    
    onAudioData(buffer);
  }
};
```

### Hook useOptimizedWebSocket (`useOptimizedWebSocket.ts:20-261`)

**Integración WebSocket + WebRTC:**
```typescript
const {
  isConnected: webRTCConnected,
  connectionState: webRTCState,
  isRecording,
  initializeWebRTC,
  startAudioCapture,
  stopAudioCapture,
  createOffer,
  handleAnswer,
  addIceCandidate,
  cleanup: cleanupWebRTC
} = useWebRTC({
  onAudioData: useCallback((audioData: ArrayBuffer) => {
    // Procesamiento de audio en tiempo real si necesario
  }, []),
  // ... más callbacks
});
```

**Características avanzadas:**
- **Fallback automático**: WebRTC -> WebSocket si falla
- **Reconexión exponencial**: Backoff inteligente para robustez
- **Cola de mensajes**: Buffer para envíos durante desconexiones
- **Detección de capacidades**: Auto-detección de WebRTC disponible

### Manejo de Mensajes WebSocket (`VoiceAssistant.tsx:204-330`)

**Routing de Mensajes:**
```typescript
switch (message.type) {
  case 'connection':
    // Inicialización automática del sistema de voz
    sendMessage({ type: 'init_voice' });
    break;
    
  case 'voice_ready':
    // Inicialización del cliente Aura con modelo configurado
    sendMessage({ 
      type: 'init_aura',
      model_type: modelType,
      model_name: selectedModel
    });
    break;
    
  case 'speech_recognized':
    setLastRecognizedText(message.text);
    setLiveTranscription('');
    break;
    
  case 'speech_partial_accumulated':
  case 'speech_partial_live':
    setLiveTranscription(message.text);
    break;
    
  case 'tts_status':
    // Sincronización precisa de animaciones con audio
    if (message.speaking !== undefined) {
      setIsSpeaking(message.speaking);
    }
    if (message.speaking_animation !== undefined) {
      setIsStreaming(message.speaking_animation);
    }
    break;
    
  case 'reasoning_thought':
    // Visualización de pensamientos de Sequential Thinking
    const thoughtText = `💭 Pensamiento ${message.thought_number}/${message.total_thoughts}: ${message.thought}`;
    toast.info(thoughtText, {
      duration: 4000,
      position: 'top-center'
    });
    break;
}
```

## Animaciones y Sincronización Visual

### EnergyOrb: Centro Visual del Sistema (`EnergyOrb.tsx:8-107`)

**Estados Visuales Dinámicos:**
```typescript
const EnergyOrb: React.FC<EnergyOrbProps> = ({ isListening, isSpeaking }) => {
  // Transformaciones basadas en estado
  const orbTransform = isListening ? 'scale-125 rotate-12' : 
                      isSpeaking ? 'scale-110 rotate-6' : 'scale-100';
  
  // Colores dinámicos para estados
  const background = isSpeaking 
    ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.8), rgba(59, 130, 246, 0.6), rgba(34, 211, 238, 0.4))'
    : 'linear-gradient(135deg, rgba(59, 130, 246, 0.8), rgba(34, 211, 238, 0.6), rgba(147, 197, 253, 0.4))';
    
  // Sombras 3D sincronizadas
  const boxShadow = isSpeaking 
    ? `0 0 50px rgba(239, 68, 68, 0.6), 0 0 100px rgba(59, 130, 246, 0.4), 0 0 150px rgba(34, 211, 238, 0.2), inset 0 0 30px rgba(255, 255, 255, 0.2)`
    : `0 0 50px rgba(59, 130, 246, 0.6), 0 0 100px rgba(34, 211, 238, 0.4), 0 0 150px rgba(147, 197, 253, 0.2), inset 0 0 30px rgba(255, 255, 255, 0.2)`;
};
```

**Animación de Ondas de Sonido:**
```typescript
{isSpeaking && (
  <div className="absolute inset-0 flex items-center justify-center">
    {[...Array(8)].map((_, i) => (
      <div
        key={i}
        className="absolute w-1 rounded-full wave-animation"
        style={{
          height: `${20 + i * 8}px`,
          left: `${35 + i * 8}%`,
          animationDelay: `${i * 0.12}s`,
          background: i % 2 === 0 
            ? 'linear-gradient(to top, rgba(239, 68, 68, 0.8), rgba(255, 255, 255, 0.6))'
            : 'linear-gradient(to top, rgba(255, 255, 255, 0.7), rgba(59, 130, 246, 0.5))'
        }}
      />
    ))}
  </div>
)}
```

### Sincronización con Backend de Audio

**Integración Buffer TTS -> Animaciones:**

1. **Backend envía estados precisos** (`aura_websocket_server.py:99-134`):
   ```python
   await self.server.broadcast_message({
       'type': 'tts_status',
       'speaking': True,
       'speaking_animation': True,
       'message': f'Reproduciendo {item.item_type}',
       'item_type': item.item_type
   })
   ```

2. **Frontend recibe y sincroniza** (`VoiceAssistant.tsx:289-301`):
   ```typescript
   case 'tts_status':
     if (message.speaking !== undefined) {
       setIsSpeaking(message.speaking);
     }
     if (message.speaking_animation !== undefined) {
       setIsStreaming(message.speaking_animation);
     }
     break;
   ```

3. **CSS y animaciones responden** (`EnergyOrb.tsx:60-77`):
   - Cambio de colores en tiempo real
   - Ondas de sonido dinámicas
   - Efectos de resplandor sincronizados

## APIs e Integraciones Externas

### API del Clima (`useWeather.ts:72-170`)

**Integración Open-Meteo (Gratuita):**

```typescript
// Paso 1: Geocoding para obtener coordenadas
const geocodingUrl = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=1&language=es&format=json`;

// Paso 2: Datos meteorológicos completos
const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${location.latitude}&longitude=${location.longitude}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature,pressure_msl,visibility,uv_index&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto`;
```

**Datos proporcionados:**
- Temperatura actual y sensación térmica
- Humedad, velocidad del viento, presión
- Pronóstico de 5 días con precipitación
- Códigos meteorológicos con descripciones en español
- Índice UV y visibilidad

### API de Estadísticas del Sistema (`system_stats_api.py:172-198`)

**Monitoreo Multiplataforma:**

```python
@app.get("/system-stats")
async def system_stats() -> Dict[str, Optional[float]]:
    stats = {
        "cpu": get_cpu_usage(),        # psutil.cpu_percent()
        "ram": get_ram_usage(),        # psutil.virtual_memory()
        "ssd": get_ssd_usage(),        # psutil.disk_usage()
        "gpu": get_gpu_usage()         # Múltiples métodos AMD
    }
```

**Detección GPU AMD Avanzada:**
1. **ROCm-smi**: `rocm-smi --showuse`
2. **amdgpu_top**: `amdgpu_top -J -n 1`
3. **Archivos del sistema**: `/sys/class/drm/card*/device/gpu_busy_percent`
4. **radeontop**: `radeontop -d - -l 1`
5. **Detección Ollama**: Inferencia cuando Ollama está activo

### Hook useSystemStats (`useSystemStats.ts:10-47`)

**Polling Inteligente:**
```typescript
useEffect(() => {
  let isMounted = true;
  let interval: NodeJS.Timeout;

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8000/system-stats');
      const data = await res.json();
      if (isMounted) {
        setStats(data);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  fetchStats();
  interval = setInterval(fetchStats, 5000); // Actualización cada 5s
  return () => {
    isMounted = false;
    clearInterval(interval);
  };
}, []);
```

## Integración Backend Completa

### Servidor WebSocket Principal (`aura_websocket_server.py:345-1273`)

**Arquitectura de Clases:**

#### TTSBuffer: Gestión Avanzada de Audio (`aura_websocket_server.py:69-322`)

```python
class TTSBuffer:
    def __init__(self, tts_instance: TextToSpeech, server_instance=None):
        self.tts = tts_instance
        self.server = server_instance  # Para notificaciones a frontend
        self.queue = asyncio.Queue()   # Cola asíncrona
        self.is_playing = False
        self.current_item = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.should_stop = False       # Flag para interrupción
        self.played_items = []         # Historial de reproducción completa
```

**Características del Buffer:**

1. **Reproducción Secuencial**: Queue FIFO con procesamiento asíncrono
2. **Interrupción Inmediata**: Sistema anti-feedback que para TTS cuando usuario habla
3. **Velocidades Dinámicas**: Pensamientos a 1.8x, respuestas a velocidad normal
4. **Sincronización Frontend**: Notificaciones precisas del estado
5. **Context Tracking**: Seguimiento de lo que realmente se reprodujo

#### AuraWebSocketServer: Orquestador Principal

**Manejo de Estados Complejos:**
```python
# Sistema anti-feedback
self.is_speaking = False
self.is_listening = False
self.speaking_lock = asyncio.Lock()
self.listening_lock = asyncio.Lock()

# Protección contra concurrencia
self.client_processing_locks: Dict[str, asyncio.Lock] = {}
self.audio_processing_lock = threading.Lock()

# Pool de recursos
self.executor = ThreadPoolExecutor(max_workers=4)
self.processing_tasks: Set[asyncio.Task] = set()
```

### Manejo de Audio Complejo

#### Escucha con Acumulación (`aura_websocket_server.py:647-732`)

**Algoritmo de Acumulación de Voz:**
```python
async def _listen_and_accumulate(self, client_id: str):
    accumulated_text_parts = []
    
    while self.is_listening and not self.is_speaking:
        # Leer datos de audio
        data = await loop.run_in_executor(
            self.executor,
            lambda: self.stt.stream.read(4000, exception_on_overflow=False)
        )
        
        # Procesar con Vosk
        final_result = self.stt.rec.AcceptWaveform(data)
        
        if final_result:
            # Texto final reconocido
            result = json.loads(self.stt.rec.Result())
            text_chunk = result.get('text', '').strip()
            
            if text_chunk:
                accumulated_text_parts.append(text_chunk)
                current_accumulated = " ".join(accumulated_text_parts)
                
                # Enviar acumulado al frontend
                await self.send_to_client(client_id, {
                    'type': 'speech_partial_accumulated',
                    'text': current_accumulated,
                    'chunk': text_chunk
                })
        else:
            # Resultado parcial (transcripción en vivo)
            partial_result = json.loads(self.stt.rec.PartialResult())
            partial_text = partial_result.get('partial', '')
            
            if partial_text:
                display_text = f"{current_accumulated} {partial_text}".strip()
                await self.send_to_client(client_id, {
                    'type': 'speech_partial_live',
                    'text': display_text
                })
```

#### Interceptación de Sequential Thinking (`aura_websocket_server.py:786-947`)

**Monkey Patching para Capturar Razonamiento:**
```python
async def _process_with_reasoning_interception(self, text: str, client_id: str) -> str:
    # Monkey patch temporal para interceptar reasoning
    original_method = self.gemini_client._process_response
    
    async def intercepted_process_response(response, chat_session=None):
        return await self._intercept_reasoning_response(
            original_method, response, chat_session, client_id
        )
    
    # Aplicar interceptor
    self.gemini_client._process_response = intercepted_process_response
    
    try:
        response = await self.gemini_client.chat(text)
        return response
    finally:
        # Restaurar método original
        self.gemini_client._process_response = original_method
```

**Detección y Procesamiento de Pensamientos:**
```python
async def _handle_sequential_thinking(self, func_call, client_id: str):
    args = dict(func_call.args) if func_call.args else {}
    
    thought_content = args.get('thought', '')
    thought_number = args.get('thoughtNumber', 0)
    total_thoughts = args.get('totalThoughts', 0)
    
    if thought_content and thought_content.strip():
        # Enviar al frontend para visualización
        await self.send_to_client(client_id, {
            'type': 'reasoning_thought',
            'thought': thought_content,
            'thought_number': int(thought_number),
            'total_thoughts': int(total_thoughts)
        })
        
        # Añadir al buffer TTS con velocidad aumentada
        await self.tts_buffer.add_item(TTSQueueItem(
            id=str(uuid.uuid4()),
            content=thought_content,
            item_type='thought',
            thought_number=int(thought_number),
            total_thoughts=int(total_thoughts),
            speed_multiplier=1.8  # 80% más rápido para pensamientos
        ))
```

## Diseño UI/UX Futurista

### Sistema de Design (`tailwind.config.ts`)

**Colores Cyberpunk:**
```javascript
colors: {
  'cyber-blue': '#00d4ff',
  'neon-purple': '#a855f7',
  'electric-green': '#10b981',
  'plasma-pink': '#f472b6'
}

backgrounds: {
  'glass-panel': 'rgba(255, 255, 255, 0.05)',
  'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))'
}

effects: {
  'backdrop-blur-glass': 'blur(20px)',
  'glow-cyan': '0 0 20px rgba(34, 211, 238, 0.6)',
  'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite'
}
```

### Layout Responsivo Avanzado (`VoiceAssistant.tsx:366-840`)

**Grid System Inteligente:**

```typescript
{/* Paneles IZQUIERDA en grilla 2x2 */}
<div className="absolute left-8 top-8 grid grid-cols-2 grid-rows-2 h-[calc(100vh-4rem)] gap-4 items-start auto-rows-min">
  <ModernGlassCard title="WEATHER" />
  <ModernGlassCard title="AURA STATUS" />
  <ModernGlassCard title="PRONÓSTICO" />
  <ModernGlassCard title="DETALLES" />
</div>

{/* Paneles SUPERIORES CENTRO */}
<div className="absolute top-8 left-1/2 transform -translate-x-1/2 flex gap-6 items-start">
  <ModernGlassCard title={currentTime.toLocaleTimeString()} />
  <ModernGlassCard title="MUSIC" />
</div>

{/* Stats del sistema DERECHA */}
<div className="absolute top-8 right-8 grid grid-cols-2 gap-1.5 items-start z-20">
  {/* CPU, GPU, RAM, SSD en mini-cards */}
</div>
```

**Características del Layout:**
- **Positioning absoluto** para control preciso
- **Grid system** flexible y responsivo
- **Z-index management** para capas correctas
- **Transform optimizations** para mejor performance

### ModernGlassCard: Componente Base

**Efecto Glassmorphism:**
```css
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
```

**Animaciones de Entrada:**
- **Staggered animations** con delays progresivos
- **Transform3D** para aceleración hardware
- **Easing functions** suaves para sensación premium

## Performance y Optimizaciones

### Optimizaciones Frontend

#### 1. Bundle Splitting
```typescript
// Lazy loading de componentes pesados
const SystemStatsPanel = lazy(() => import('./SystemStatsPanel'));
const WeatherDetails = lazy(() => import('./WeatherDetails'));
```

#### 2. Memoization Estratégica
```typescript
const EnergyOrb = React.memo<EnergyOrbProps>(({ isListening, isSpeaking }) => {
  // ... componente
});

const useOptimizedCallback = useCallback((audioData: ArrayBuffer) => {
  // Procesamiento solo cuando necesario
}, [dependencies]);
```

#### 3. CSS Optimizations
- **transform3d** para aceleración GPU
- **will-change** para animaciones suaves
- **contain** para aislamiento de renders

### Optimizaciones Backend

#### 1. Async/Await Patterns
```python
# Procesamiento paralelo de tareas
init_tasks = [
    asyncio.create_task(self.init_voice_system()),
    asyncio.create_task(self.init_aura_client())
]
await asyncio.gather(*init_tasks, return_exceptions=True)
```

#### 2. ThreadPool Management
```python
self.executor = ThreadPoolExecutor(max_workers=4)
# Operaciones blocking en threads separados
await loop.run_in_executor(self.executor, blocking_operation)
```

#### 3. Memory Management
- **Cleanup automático** de recursos WebRTC
- **Context tracking** limitado para evitar memory leaks
- **Queue management** con límites apropiados

## Patrones Avanzados de Integración

### 1. Event-Driven Architecture

**Frontend -> Backend:**
```typescript
const sendOptimizedMessage = useCallback((type: string, data: any = {}) => {
  return sendMessage({ type, ...data, timestamp: Date.now() });
}, [sendMessage]);
```

**Backend -> Frontend:**
```python
await self.broadcast_message({
    'type': 'reasoning_thought',
    'thought': thought_content,
    'timestamp': time.time()
})
```

### 2. State Synchronization

**Bidirectional State:**
- Frontend mantiene shadow state del backend
- Backend notifica cambios inmediatamente
- Conflict resolution via timestamps

### 3. Error Recovery

**Network Resilience:**
- Exponential backoff para reconexión
- Message queuing durante desconexiones
- Graceful degradation de funcionalidades

**Resource Recovery:**
- Auto-cleanup de recursos WebRTC
- Fallback chains para APIs fallidas
- Health checks periódicos

## Casos de Uso Complejos

### 1. Flujo Completo de Conversación

```
1. Usuario habla -> WebRTC captura audio
2. STT procesa -> Transcripción en vivo en UI
3. Texto completo -> Enviado a Gemini via MCP
4. Sequential Thinking -> Pensamientos mostrados + TTS rápido
5. Respuesta final -> TTS normal + animaciones sincronizadas
6. Interruption handling -> Stop inmediato si usuario habla
```

### 2. Multi-Modal Interaction

```
1. Voz + Sistema Stats -> "¿Cómo está la PC?"
2. Voz + Clima -> "¿Necesito paraguas hoy?"
3. Voz + Sequential Thinking -> Problemas complejos paso a paso
```

### 3. Adaptive Performance

```
1. GPU Load Detection -> Ajuste de animaciones
2. Network Quality -> Fallback WebRTC -> WebSocket
3. Audio Quality -> Dynamic sample rate adjustment
```

## Conclusión Arquitectónica

El frontend de Aura representa una implementación sofisticada que combina:

- **Realtime Communication**: WebSocket + WebRTC para baja latencia
- **Advanced Audio Processing**: Buffer management sincronizado con UI
- **Modern React Patterns**: Hooks optimizados y state management
- **Futuristic UX**: Animaciones hardware-accelerated
- **Multi-API Integration**: Clima, sistema, IA en tiempo real
- **Robust Error Handling**: Múltiples layers de fallback

La integración backend es especialmente notable por su capacidad de interceptar y procesar sequential thinking en tiempo real, proporcionando una experiencia de IA verdaderamente interactiva donde el usuario puede "ver pensar" al asistente mientras mantiene una respuesta de audio fluida y sin latencia.