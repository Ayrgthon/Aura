import React, { useState, useEffect } from 'react';
import { Mic, MicOff, Volume2, Cloud, Wifi, Clock, Music, Cpu, Monitor, MemoryStick, HardDrive, Calendar, Info, Mic as MicIcon, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import EnergyOrb from './EnergyOrb';
import HolographicPanel from './HolographicPanel';
import ModernGlassCard from './ModernGlassCard';
import WeatherPanel from './WeatherPanel';
import WeatherForecast from './WeatherForecast';
import WeatherDetails from './WeatherDetails';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useWeather } from '@/hooks/useWeather';
import { toast } from 'sonner';
import SystemStatsPanel from './SystemStatsPanel';

const VoiceAssistant = () => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [lastRecognizedText, setLastRecognizedText] = useState<string>('');
  const [lastResponse, setLastResponse] = useState<string>('');
  const [isAuraReady, setIsAuraReady] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

    // Estados para configuración de modelos
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [modelType, setModelType] = useState<'gemini' | 'ollama'>('gemini');
  const [selectedModel, setSelectedModel] = useState('gemini-2.0-flash-exp');
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  
  // Estados para control de encendido/apagado
  const [isSystemOn, setIsSystemOn] = useState(true);
  const [isShuttingDown, setIsShuttingDown] = useState(false);
  
  // Estados para motor TTS
  const [ttsEngine, setTtsEngine] = useState<'gtts' | 'elevenlabs'>('gtts');

  // Modelos de Gemini disponibles
  const geminiModels = [
    'gemini-2.0-flash-exp',
    'gemini-2.5-pro',
    'gemini-2.5-flash',
    'gemini-2.5-flash-preview-04-17',
    'gemini-2.5-flash-lite-preview-06-17',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite'
  ];

  // Función para obtener modelos de Ollama
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

  // Función para cambiar tipo de modelo
  const handleModelTypeChange = (type: 'gemini' | 'ollama') => {
    setModelType(type);
    let newModel = '';
    if (type === 'gemini') {
      newModel = 'gemini-2.0-flash-exp';
      setSelectedModel(newModel);
    } else if (ollamaModels.length > 0) {
      newModel = ollamaModels[0];
      setSelectedModel(newModel);
    }
    
    // Si Aura ya está inicializado, reinicializarlo con el nuevo tipo de modelo
    if (isAuraReady && isConnected && newModel) {
      setIsAuraReady(false);
      sendMessage({ 
        type: 'init_aura',
        model_type: type,
        model_name: newModel
      });
    }
  };

  // Función para cambiar modelo específico
  const handleModelChange = (model: string) => {
    setSelectedModel(model);
    setShowModelMenu(false);
    toast.success(`Modelo cambiado a: ${model}`);
    
    // Si Aura ya está inicializado, reinicializarlo con el nuevo modelo
    if (isAuraReady && isConnected) {
      setIsAuraReady(false);
      sendMessage({ 
        type: 'init_aura',
        model_type: modelType,
        model_name: model
      });
    }
  };

  // Función para cambiar motor TTS
  const handleTtsEngineChange = (engine: 'gtts' | 'elevenlabs') => {
    setTtsEngine(engine);
    toast.success(`Motor TTS cambiado a: ${engine.toUpperCase()}`);
    
    // Enviar cambio al backend
    if (isConnected) {
      sendMessage({
        type: 'change_tts_engine',
        engine: engine
      });
    }
  };

  // Función para apagar el sistema
  const handleSystemShutdown = async () => {
    if (isShuttingDown) return;
    
    setIsShuttingDown(true);
    toast.success('Apagando sistema...');
    
    try {
      // Enviar comando de apagado al backend
      if (isConnected) {
        sendMessage({ type: 'shutdown_system' });
      }
      
      // Hacer llamada HTTP para apagar servicios
      await fetch('http://localhost:8000/shutdown', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      // Actualizar estado local
      setIsSystemOn(false);
      setIsAuraReady(false);
      setIsListening(false);
      setIsSpeaking(false);
      setIsStreaming(false);
      
      toast.success('Sistema apagado correctamente');
    } catch (error) {
      console.error('Error apagando sistema:', error);
      toast.error('Error al apagar el sistema');
    } finally {
      setIsShuttingDown(false);
    }
  };

  // Función para encender el sistema
  const handleSystemStartup = async () => {
    try {
      toast.success('Iniciando sistema...');
      
      // Hacer llamada HTTP para iniciar servicios
      await fetch('http://localhost:8000/startup', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      // Actualizar estado local
      setIsSystemOn(true);
      
      // Intentar reconectar WebSocket
      setTimeout(() => {
        if (!isConnected) {
          // El hook useWebSocket debería reconectar automáticamente
          toast.success('Sistema iniciado correctamente');
        }
      }, 2000);
      
    } catch (error) {
      console.error('Error iniciando sistema:', error);
      toast.error('Error al iniciar el sistema');
    }
  };

  // Configurar Weather
  const { weatherData } = useWeather('Barranquilla');

  // Configurar WebSocket
  const { isConnected, sendMessage } = useWebSocket({
    onMessage: (message) => {
      console.log('Mensaje recibido:', message);
      
      switch (message.type) {
        case 'connection':
          // Inicializar voice inmediatamente al conectar
          sendMessage({ type: 'init_voice' });
          break;
          
        case 'speech_recognized':
          setLastRecognizedText(message.text);
          break;
          
        case 'voice_ready':
          toast.success('Sistema de voz inicializado');
          // Inicializar Aura inmediatamente después con configuración del modelo
          sendMessage({ 
            type: 'init_aura',
            model_type: modelType,
            model_name: selectedModel
          });
          break;
          
        case 'aura_ready':
          setIsAuraReady(true);
          toast.success('Cliente Aura listo');
          break;
          
        case 'aura_response':
          setLastResponse(message.response);
          setIsProcessing(false);
          setIsStreaming(false);
          break;
          
        case 'status':
          if (message.listening !== undefined) {
            setIsListening(message.listening);
          }
          if (message.streaming !== undefined) {
            setIsStreaming(message.streaming);
          }
          if (message.speaking !== undefined && !message.streaming) {
            setIsSpeaking(message.speaking);
          }
          if (message.message === 'Procesando texto reconocido con Aura...') {
            setIsProcessing(true);
            setLastResponse('');  // Limpiar respuesta anterior al empezar
          }
          break;
          
        case 'error':
          toast.error(message.message);
          setIsListening(false);
          setIsSpeaking(false);
          setIsStreaming(false);
          setIsProcessing(false);
          break;
          
        case 'shutdown_complete':
          setIsSystemOn(false);
          setIsAuraReady(false);
          setIsListening(false);
          setIsSpeaking(false);
          setIsStreaming(false);
          setIsProcessing(false);
          toast.success('Sistema apagado correctamente');
          break;
          
        case 'tts_engine_changed':
          setTtsEngine(message.engine);
          toast.success(`Motor TTS cambiado a ${message.engine.toUpperCase()}`);
          break;
          
        case 'tts_status':
          // Manejar estado de TTS streaming para animación de la esfera
          if (message.speaking !== undefined) {
            setIsSpeaking(message.speaking);
          }
          if (message.speaking_animation !== undefined) {
            setIsStreaming(message.speaking_animation);
          }
          // Mostrar mensaje opcional en consola para debugging
          if (message.message) {
            console.log('TTS Status:', message.message);
          }
          break;
      }
    },
    onOpen: () => {
      console.log('Conectado al servidor Aura');
    },
    onClose: () => {
      console.log('Desconectado del servidor Aura');
      setIsListening(false);
      setIsSpeaking(false);
      setIsStreaming(false);
      setIsAuraReady(false);
      setIsProcessing(false);
    },
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Cargar modelos de Ollama al montar el componente
  useEffect(() => {
    fetchOllamaModels();
  }, []);

  const toggleListening = () => {
    if (!isConnected) {
      toast.error('No hay conexión con el servidor');
      return;
    }

    if (isListening) {
      // Detener escucha
      sendMessage({ type: 'stop_listening' });
    } else {
      // Iniciar escucha
      sendMessage({ type: 'start_listening' });
    }
  };

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Subtle background gradient effect */}
      <div className="absolute inset-0 bg-gradient-radial from-white/5 via-transparent to-transparent" />
      
      {/* Minimal background grid */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
          animation: 'grid-move 30s linear infinite'
        }} />
      </div>
      
      {/* Minimal floating particles effect */}
      <div className="absolute inset-0">
        {[...Array(15)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-white/20 rounded-full animate-pulse"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${4 + Math.random() * 3}s`
            }}
          />
        ))}
      </div>

      {/* Main container */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen p-8">
        {/* Paneles IZQUIERDA en grilla 2x2 con alto mínimo por contenido */}
        <div className="absolute left-8 top-8 grid grid-cols-2 grid-rows-2 h-[calc(100vh-4rem)] gap-4 items-start auto-rows-min">
          <ModernGlassCard 
            title="WEATHER" 
            delay={0.8} 
            icon={<Cloud className="w-3 h-3" />}
            accentColor="cyan"
            className="w-40"
          >
            <div className="space-y-2">
              <div className="text-xl font-light text-white">28°C</div>
              <div className="text-xs text-white/70">Cielo despejado</div>
              <div className="text-xs text-white/60">Barranquilla, Colombia</div>
              <div className="flex justify-between text-xs text-white/60">
                <span>65%</span>
                <span>27 km/h</span>
              </div>
              <div className="text-xs text-white/60">Sensación: 31°C</div>
              <div className="text-xs underline cursor-pointer" style={{color: 'rgb(34, 211, 238)', textShadow: '0 0 8px rgba(34, 211, 238, 0.6)'}}>Actualizar</div>
            </div>
          </ModernGlassCard>
          
          <ModernGlassCard 
            title="AURA STATUS" 
            delay={1.0} 
            icon={<Wifi className="w-3 h-3" />}
            accentColor="green"
            className="w-40"
          >
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'pulse-slow' : 'bg-red-400'}`} style={isConnected ? {backgroundColor: 'rgb(34, 211, 238)', boxShadow: '0 0 8px rgba(34, 211, 238, 0.6)'} : {}} />
                <span className="text-xs text-white/80">{isConnected ? 'Online' : 'Offline'}</span>
              </div>
              <div className="text-xs text-white/60">
                WebSocket: {isConnected ? 'Conectado' : 'Desconectado'}
              </div>
              <div className="text-xs text-white/60">
                Voice recognition: {isListening ? 'Escuchando...' : 'Listo'}
              </div>
              <div className="text-xs text-white/60">
                Aura Client: {isAuraReady ? 'Listo' : 'Inicializando...'}
              </div>
              <div className="text-xs" style={{color: 'rgb(34, 211, 238)', textShadow: '0 0 8px rgba(34, 211, 238, 0.6)'}}>
                {isProcessing ? 'Procesando texto...' : (isStreaming || isSpeaking) ? 'Hablando...' : 'Listo'}
              </div>
            </div>
          </ModernGlassCard>
          
          <ModernGlassCard 
            title="PRONÓSTICO" 
            delay={1.2} 
            icon={<Calendar className="w-3 h-3" />}
            accentColor="blue"
            className="w-40"
          >
            <div className="space-y-2">
              <div className="text-xs text-white/70">Próximos días</div>
              <div className="flex justify-between text-xs text-white/60">
                <span>5 días</span>
                <span>30° / 27°</span>
              </div>
            </div>
          </ModernGlassCard>
          
          <ModernGlassCard 
            title="DETALLES" 
            delay={1.4} 
            icon={<Info className="w-3 h-3" />}
            accentColor="magenta"
            className="w-40"
          >
            <div className="space-y-2">
              <div className="text-xs text-white/70">Información adicional</div>
              <div className="text-xs text-white/60">Presión: 1009 hPa</div>
              <div className="text-xs text-white/60">UV: 0</div>
            </div>
          </ModernGlassCard>
        </div>
        {/* Paneles SUPERIORES CENTRO */}
        <div className="absolute top-8 left-1/2 transform -translate-x-1/2 flex gap-6 items-start">
          <ModernGlassCard 
            title={currentTime.toLocaleTimeString()} 
            delay={0.2}
            icon={<Clock className="w-3 h-3" />}
            accentColor="cyan"
            className="w-40"
          >
            <div className="text-xs space-y-1">
              <div className="text-xs text-white/60">
                {currentTime.toLocaleDateString()}
              </div>
              <div className="text-xs text-white/50">Pacific Time</div>
            </div>
          </ModernGlassCard>
          
          <ModernGlassCard 
            title="MUSIC" 
            delay={0.4}
            icon={<Music className="w-3 h-3" />}
            accentColor="pink"
            className="w-40"
          >
            <div className="text-xs space-y-2">
              <div className="text-xs font-medium text-white/80">Cyberpunk Ambient</div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 inline-block rounded-full" style={{backgroundColor: 'rgb(34, 211, 238)', boxShadow: '0 0 8px rgba(34, 211, 238, 0.6)'}} />
                <div className="text-xs text-white/60">Playing</div>
              </div>
            </div>
          </ModernGlassCard>
        </div>
        {/* Paneles DERECHA: grilla de sistema arriba */}
        <div className="absolute top-8 right-8 grid grid-cols-2 gap-1.5 items-start z-20">
          <ModernGlassCard 
            title="CPU" 
            delay={0.1} 
            icon={<Cpu className="w-2.5 h-2.5" />}
            accentColor="cyan"
            className="w-20 px-1 py-1 min-w-0"
          >
            <div className="flex flex-col items-center justify-center gap-0.5">
              <SystemStatsPanel statKey="cpu" />
            </div>
          </ModernGlassCard>
          
          <ModernGlassCard 
            title="GPU" 
            delay={0.2} 
            icon={<Monitor className="w-2.5 h-2.5" />}
            accentColor="pink"
            className="w-20 px-1 py-1 min-w-0"
          >
            <div className="flex flex-col items-center justify-center gap-0.5">
              <SystemStatsPanel statKey="gpu" />
            </div>
          </ModernGlassCard>
          
          <ModernGlassCard 
            title="RAM" 
            delay={0.3} 
            icon={<MemoryStick className="w-2.5 h-2.5" />}
            accentColor="green"
            className="w-20 px-1 py-1 min-w-0"
          >
            <div className="flex flex-col items-center justify-center gap-0.5">
              <SystemStatsPanel statKey="ram" />
            </div>
          </ModernGlassCard>
          
          <ModernGlassCard 
            title="SSD" 
            delay={0.4} 
            icon={<HardDrive className="w-2.5 h-2.5" />}
            accentColor="yellow"
            className="w-20 px-1 py-1 min-w-0"
          >
            <div className="flex flex-col items-center justify-center gap-0.5">
              <SystemStatsPanel statKey="ssd" />
            </div>
          </ModernGlassCard>
        </div>
        
        {/* Panel Voice Recognition con posición absoluta y tamaño fijo */}
        <div className="absolute bottom-8 z-20" style={{width: '380px', height: '340px', right: '-1.5rem'}}>
          <div style={{width: '330px', height: '240px', minWidth: '330px', maxWidth: '330px', minHeight: '240px', maxHeight: '240px', position: 'relative'}}>
            <ModernGlassCard 
              title="VOICE RECOGNITION" 
              delay={0.8} 
              icon={<MicIcon className="w-3.5 h-3.5" />}
              accentColor="blue"
              className="w-full h-full"
            >
              <div style={{display: 'flex', flexDirection: 'column', height: '200px', overflow: 'hidden', width: '100%', boxSizing: 'border-box'}}>
                <div className="text-xs p-2 rounded bg-white/5 border border-white/10" style={{flexShrink: 0, wordWrap: 'break-word', overflowWrap: 'break-word', boxSizing: 'border-box', maxWidth: '100%'}}>
                  <div className="font-medium mb-1" style={{color: 'rgb(34, 211, 238)', textShadow: '0 0 8px rgba(34, 211, 238, 0.6)'}}>Estado</div>
                  <div className="text-white/70">
                    {isConnected ? '✅ Conectado' : '❌ Desconectado'}
                  </div>
                  <div className="text-white/70">
                    Aura: {isAuraReady ? '✅ Listo' : '⏳ Inicializando...'}
                  </div>
                </div>
                {lastRecognizedText && (
                  <div className="text-xs p-2 rounded bg-white/5 border border-white/10 mt-2" style={{flexShrink: 0, wordWrap: 'break-word', overflowWrap: 'break-word', boxSizing: 'border-box', maxWidth: '100%'}}>
                    <div className="text-blue-400 font-medium mb-1">
                      {isProcessing ? '⏳ Procesando...' : 'Texto reconocido'}
                    </div>
                    <div className="text-white/70" style={{wordWrap: 'break-word', overflowWrap: 'break-word', maxWidth: '100%', boxSizing: 'border-box'}}>{lastRecognizedText}</div>
                  </div>
                )}
                <div style={{flex: '1 1 0', minHeight: '0', overflowY: 'auto', marginTop: '8px', width: '100%', boxSizing: 'border-box'}}>
                  {lastResponse && (
                    <div className="text-xs p-2 rounded bg-white/5 border border-white/10" style={{wordWrap: 'break-word', overflowWrap: 'break-word', width: '100%', boxSizing: 'border-box', maxWidth: '100%'}}>
                      <div className="text-blue-400 font-medium mb-1">Respuesta de Aura</div>
                      <div className="text-white/70 text-xs leading-relaxed" style={{wordWrap: 'break-word', overflowWrap: 'break-word', whiteSpace: 'pre-wrap', maxWidth: '100%', boxSizing: 'border-box'}}>
                        {lastResponse}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </ModernGlassCard>
          </div>
        </div>
        
        {/* Módulo de configuración y control - esquina inferior izquierda */}
        <div className="absolute bottom-8 left-8 z-20">
          <div className="flex gap-3 items-end">
            {/* Botón de encendido/apagado */}
          <div className="relative">
              <Button
                onClick={isSystemOn ? handleSystemShutdown : handleSystemStartup}
                disabled={isShuttingDown}
                className={`w-12 h-12 rounded-full border-0 transition-all duration-500 transform-gpu hover:scale-110 ${
                  isSystemOn 
                    ? 'bg-white/10 hover:bg-white/15' 
                    : 'bg-white/10 hover:bg-white/15'
                }`}
                style={{
                  fontSize: '20px',
                  backdropFilter: 'blur(20px)',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
                }}
              >
                {isShuttingDown ? '⏳' : isSystemOn ? '🔋' : '⚡'}
              </Button>
            </div>
            
            {/* Botón de configuración */}
            <div className="relative">
            <Button
              onClick={() => setShowModelMenu(!showModelMenu)}
                disabled={!isSystemOn}
                className={`w-12 h-12 rounded-full border-0 transition-all duration-500 transform-gpu hover:scale-110 bg-white/10 hover:bg-white/15 ${
                  !isSystemOn ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                style={{
                  fontSize: '20px',
                  backdropFilter: 'blur(20px)',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
                }}
            >
              ⚙️
            </Button>
            
            {/* Menú desplegable */}
            {showModelMenu && (
              <div className="absolute bottom-16 left-0 w-72 bg-glass-panel backdrop-blur-lg rounded-lg border border-primary/20 p-3 shadow-lg">
                <h3 className="text-xs font-medium text-primary mb-2">Configuración de Modelo</h3>
                
                {/* Selector de tipo de modelo */}
                <div className="mb-4">
                  <label className="text-xs text-muted-foreground mb-2 block">Tipo de Modelo:</label>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={modelType === 'gemini' ? 'default' : 'outline'}
                      onClick={() => handleModelTypeChange('gemini')}
                      className="flex-1"
                    >
                      Gemini
                    </Button>
                    <Button
                      size="sm"
                      variant={modelType === 'ollama' ? 'default' : 'outline'}
                      onClick={() => handleModelTypeChange('ollama')}
                      className="flex-1"
                    >
                      Ollama
                    </Button>
                  </div>
                </div>
                
                                  {/* Selector de motor TTS */}
                  <div className="mb-4">
                    <label className="text-xs text-muted-foreground mb-2 block">Motor de Voz:</label>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant={ttsEngine === 'gtts' ? 'default' : 'outline'}
                        onClick={() => handleTtsEngineChange('gtts')}
                        className="flex-1"
                      >
                        gTTS (Gratuito)
                      </Button>
                      <Button
                        size="sm"
                        variant={ttsEngine === 'elevenlabs' ? 'default' : 'outline'}
                        onClick={() => handleTtsEngineChange('elevenlabs')}
                        className="flex-1"
                      >
                        ElevenLabs (Premium)
                      </Button>
                    </div>
                  </div>
                
                  {/* Lista de modelos */}
                  <div>
                    <label className="text-xs text-muted-foreground mb-2 block">
                      Modelo Seleccionado: <span className="text-accent">{selectedModel}</span>
                    </label>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                    {modelType === 'gemini' ? (
                      geminiModels.map((model) => (
                        <button
                          key={model}
                          onClick={() => handleModelChange(model)}
                          className={`w-full text-left px-3 py-2 rounded text-xs transition-colors ${
                            selectedModel === model
                              ? 'bg-primary text-primary-foreground'
                              : 'hover:bg-glass-panel/50 text-muted-foreground'
                          }`}
                        >
                          {model}
                        </button>
                      ))
                    ) : (
                      ollamaModels.length > 0 ? (
                        ollamaModels.map((model) => (
                          <button
                            key={model}
                            onClick={() => handleModelChange(model)}
                            className={`w-full text-left px-3 py-2 rounded text-xs transition-colors ${
                              selectedModel === model
                                ? 'bg-primary text-primary-foreground'
                                : 'hover:bg-glass-panel/50 text-muted-foreground'
                            }`}
                          >
                            {model}
                          </button>
                        ))
                      ) : (
                        <div className="text-xs text-muted-foreground p-3 text-center">
                          No se encontraron modelos de Ollama
                        </div>
                      )
                    )}
                  </div>
                </div>
                
                {/* Botón cerrar */}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowModelMenu(false)}
                  className="w-full mt-3"
                >
                  Cerrar
                </Button>
              </div>
            )}
            </div>
          </div>
        </div>
        {/* Central energy orb */}
        <div className="flex-1 flex items-center justify-center">
          <EnergyOrb isListening={isListening} isSpeaking={isStreaming || isSpeaking} />
        </div>
        {/* Bottom controls */}
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2">
          <ModernGlassCard 
            title="VOICE CONTROL" 
            delay={0.6}
            icon={<MicIcon className="w-3.5 h-3.5" />}
            accentColor="magenta"
            className="w-80"
          >
            <div className="flex items-center gap-4">
              <Button 
                size="lg" 
                variant={isListening ? "destructive" : "default"} 
                onClick={toggleListening} 
                className="rounded-full w-14 h-14 border-0 transition-all duration-500 transform-gpu hover:scale-110"
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  backdropFilter: 'blur(20px)',
                  boxShadow: '0 12px 40px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
                }}
              >
                {isListening ? (
                  <MicOff className="w-5 h-5" style={{color: 'rgb(34, 211, 238)', filter: 'drop-shadow(0 0 8px rgba(34, 211, 238, 0.6))'}} />
                ) : (
                  <Mic className="w-5 h-5" style={{color: 'rgb(34, 211, 238)', filter: 'drop-shadow(0 0 8px rgba(34, 211, 238, 0.6))'}} />
                )}
              </Button>
              <div className="text-center">
                <div className="text-xs text-white/80">
                  {isListening ? "Listening..." : (isStreaming || isSpeaking) ? "Speaking..." : "Say something"}
                </div>
                <div className="text-xs text-white/60 mt-1">
                  {isListening ? "Touch to stop" : "Touch to activate"}
                </div>
              </div>
            </div>
          </ModernGlassCard>
        </div>
      </div>
    </div>
  );
};

export default VoiceAssistant;