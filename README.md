# 🌟 Aura - Advanced AI Assistant with Voice & Sequential Thinking

Aura es un asistente de inteligencia artificial de última generación que integra un** cliente** con capacidades avanzadas de voz, razonamiento secuencial, y herramientas especializadas através del **Model Context Protocol (MCP)**. Cuenta con un frontend futurista, procesamiento de audio en tiempo real, y integración completa con servicios como Google Workspace, Obsidian, y APIs web.

## 🚀 Características Principales

### 🎯 **Core Features**
- **🧠 Sequential Thinking**: Razonamiento paso a paso visible con reproducción TTS sincronizada
- **🗣️ Procesamiento de Audio Avanzado**: WebRTC con cancelación de eco y supresión de ruido
- **🤖 Ollama & Gemini Clients**: Integración nativa con function calls iterativos 
- **⚡ Buffer TTS Inteligente**: Reproducción secuencial con interrupciones inmediatas
- **🌐 Frontend Futurista**: React + TypeScript con animaciones hardware-accelerated

### 🛠️ **Herramientas MCP Integradas**
- **🔍 SerpAPI**: Búsquedas web completas (Google, News, Images)
- **🗃️ Obsidian Memory**: Sistema de notas con búsqueda semántica
- **📅 Google Workspace**: Calendar completo, Gmail, análisis de productividad
- **🧠 Sequential Thinking**: Servidor oficial de Anthropic para razonamiento estructurado

### 💡 **Capacidades Técnicas**
- **🎵 Animaciones Sincronizadas**: EnergyOrb que responde al estado de audio en tiempo real
- **📊 Monitoreo del Sistema**: CPU, GPU (AMD), RAM, SSD con APIs optimizadas
- **🌤️ Integración Meteorológica**: API Open-Meteo para datos del clima
- **🔄 WebSocket Optimizado**: Comunicación bidireccional con reconexión automática

## 📋 Requisitos del Sistema

- **Python 3.8+** con asyncio
- **Node.js 16+** para MCP servers y frontend
- **Linux** (recomendado Arch Linux para GPU AMD)
- **Micrófono** para reconocimiento de voz
- **Conectividad a Internet** para APIs

## 🛠️ Instalación Rápida

### 1. Clonar y Configurar

```bash
git clone <tu-repositorio>
cd Aura
cp env.template .env
```

### 2. Configurar Variables de Entorno

Edita el archivo `.env` con tus credenciales:

```env
# Google Gemini (REQUERIDO)
GOOGLE_API_KEY=tu_google_api_key

# SerpAPI para búsquedas web (REQUERIDO)
SERPAPI_API_KEY=tu_serpapi_api_key

# Obsidian Vault (OPCIONAL)
OBSIDIAN_VAULT_PATH=/home/ary/Documents/Ary Vault

# Google Workspace (OPCIONAL)
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_TOKEN_PATH=./token.json

# ElevenLabs TTS Premium (OPCIONAL)
ELEVENLABS_API_KEY=tu_elevenlabs_api_key
```

### 3. Instalar Dependencias

```bash
# Backend Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend React
cd frontend && npm install && cd ..

# MCP Dependencies
npm install
```

### 4. Inicializar Sistema

```bash
# Opción 1: Scripts automatizados
./scripts/start_aura.sh

# Opción 2: Manual
python src/system_stats_api.py &    # API estadísticas (puerto 8000)
python src/aura_websocket_server.py & # WebSocket server (puerto 8766) 
cd frontend && npm run dev          # Frontend React (puerto 5173)
```

## 🎮 Uso del Sistema

### 🌐 **Interfaz Web Principal**

1. **Acceder**: `http://localhost:5173`
2. **Configurar Modelo**: Botón ⚙️ para seleccionar Gemini 2.5 Pro/Flash o modelos Ollama
3. **Interacción por Voz**: 
   - **Primer click**: Iniciar escucha (transcripción en vivo)
   - **Segundo click**: Procesar con Aura
4. **Monitoreo Visual**: Paneles de clima, sistema, estado de Aura

### 🎯 **Características de la Interfaz**

#### **EnergyOrb Central**
- **Azul**: Estado normal/escuchando
- **Rojo + Ondas**: Hablando/reproduciendo TTS
- **Escala dinámica**: Responde a estados de audio
- **Efectos 3D**: Glassmorphism con perspectiva hardware-accelerated

#### **Paneles de Información**
- **WEATHER**: Datos en tiempo real de Barranquilla (Open-Meteo API)
- **AURA STATUS**: Estado de conexión WebSocket y cliente Gemini
- **SISTEMA**: CPU, GPU AMD, RAM, SSD en tiempo real
- **VOICE RECOGNITION**: Transcripción en vivo y respuestas

#### **Sequential Thinking Visual**
- **Notificaciones**: Cada pensamiento aparece como toast notification
- **TTS Acelerado**: Pensamientos se reproducen a 1.8x velocidad
- **Progreso**: "💭 Pensamiento 3/7: Análisis de la consulta..."

## 🧠 Funcionamiento del Sequential Thinking

### **Flujo de Razonamiento**
1. **Usuario habla**: "¿Cuál es la mejor estrategia para aprender IA?"
2. **Detección automática**: Aura identifica complejidad y activa Sequential Thinking
3. **Pensamientos secuenciales**:
   - 💭 **Pensamiento 1/5**: Analizando los diferentes campos de la IA...
   - 💭 **Pensamiento 2/5**: Considerando recursos de aprendizaje disponibles...
   - 💭 **Pensamiento 3/5**: Evaluando progresión de habilidades técnicas...
4. **TTS Sincronizado**: Cada pensamiento se reproduce mientras se genera el siguiente
5. **Respuesta final**: Síntesis completa con plan detallado

### **Características Técnicas**
- **Interceptación automática**: Monkey patching del cliente Gemini
- **Buffer inteligente**: Queue asyncio con interrupciones
- **Velocidades dinámicas**: 1.8x para pensamientos, 1.0x para respuestas
- **Context tracking**: Solo se incluye en historial lo que se reprodujo completamente

## 🔧 Herramientas MCP en Detalle

### 🔍 **SerpAPI Server**
```javascript
// Herramientas disponibles
google_search(query, location="Colombia", language="es", num_results=10)
google_news_search(query, time_period="qdr:d")
google_images_search(query, image_size="medium", image_type="photo")
```

**Uso típico**: *"Busca las últimas noticias sobre IA en Colombia"*
- Resultados orgánicos con snippets
- Knowledge Graph si disponible
- Answer boxes destacados
- Búsquedas relacionadas

### 🗃️ **Obsidian Memory Server**
```javascript
// Gestión completa de notas
search_notes(query, search_type="all", max_results=10)
read_note(note_path)
create_note(note_path, content, overwrite=false)
update_note(note_path, content, mode="append")
get_current_datetime(format="readable")
```

**Características avanzadas**:
- **Búsqueda semántica**: Por contenido, filename, #tags, [[wikilinks]]
- **Sistema de relevancia**: Puntuación basada en coincidencias múltiples
- **Timestamps automáticos**: Zona horaria America/Bogotá
- **Metadata extraction**: Tags y enlaces automáticamente identificados

**Uso típico**: *"Busca mis notas sobre Sequential Thinking y actualiza con lo que acabamos de aprender"*

### 📅 **Google Workspace Server**
```javascript
// Calendar management completo
list_calendar_events(time_period="today", search_query="")
create_calendar_event(title, start_datetime, end_datetime, location="", attendees=[], create_meet=false)
find_free_time(start_date, end_date, duration_minutes=60, working_hours_only=true)
get_calendar_summary(period="week", include_stats=true)
send_calendar_reminder_email(subject, message, recipient_email)
```

**Funcionalidades premium**:
- **Análisis de productividad**: Estadísticas detalladas y insights
- **Búsqueda inteligente de tiempo libre**: Con filtros de horario laboral
- **Google Meet automático**: Creación de enlaces de reunión
- **Recordatorios personalizados**: Envío automático de emails
- **Multi-timezone**: Soporte para America/Bogotá

**Uso típico**: *"¿Qué tengo mañana? Crea una reunión de 2 horas con Juan el viernes y encuentra tiempo libre esta semana"*

### 🧠 **Sequential Thinking (Oficial Anthropic)**
```javascript
sequentialthinking(
    thought="string", 
    thoughtNumber=1, 
    totalThoughts=5,
    nextThoughtNeeded=true
)
```

**Integración automática**:
- **Detección de complejidad**: Se activa automáticamente para tareas complejas
- **Razonamiento visible**: Cada pensamiento mostrado en UI
- **TTS buffer integration**: Reproducción sincronizada de pensamientos
- **Context preservation**: Historial actualizado con razonamiento completo

## 🏗️ Arquitectura del Sistema

### **Backend (Python)**
```
src/
├── aura_websocket_server.py      # Servidor principal con TTS buffer
└── system_stats_api.py           # API FastAPI para estadísticas

client/
├── gemini_client.py              # Cliente Gemini con function calls iterativos
├── mcp_client.py                 # Gestor de conexiones MCP
├── config.py                     # Configuración centralized de servidores
└── main.py                       # CLI interface

voice/
├── hear.py                       # STT con Vosk (español/inglés)
├── speak.py                      # TTS con gTTS/ElevenLabs/Edge-TTS
└── vosk-model-*/                 # Modelos de reconocimiento offline
```

### **Frontend (React + TypeScript)**
```
frontend/src/
├── components/
│   ├── VoiceAssistant.tsx        # Componente principal
│   ├── EnergyOrb.tsx             # Orbe central animado
│   └── ModernGlassCard.tsx       # Cards con glassmorphism
├── hooks/
│   ├── useOptimizedWebSocket.ts  # WebSocket + WebRTC integration
│   ├── useWebRTC.ts              # Audio processing puro
│   ├── useWeather.ts             # API del clima
│   └── useSystemStats.ts         # Estadísticas del sistema
└── pages/
    └── Index.tsx                 # Página principal
```

### **MCP Servers (Node.js)**
```
mcp/
├── serpapi_server.js             # Búsquedas web completas
├── obsidian_memory_server.js     # Sistema de memoria persistente
└── google_workspace_server.js    # Google Calendar + Gmail
```

## ⚡ Optimizaciones de Performance

### **Audio Processing**
- **WebRTC**: Cancelación de eco, supresión de ruido, AGC
- **Sample Rate**: 16kHz optimizado para STT
- **Buffer Management**: Queue asíncrono con interrupción inmediata
- **Context Window**: 1M tokens de Gemini aprovechados completamente

### **Frontend**
- **Hardware Acceleration**: CSS transform3d para animaciones
- **Lazy Loading**: Componentes cargados bajo demanda
- **Memoization**: React.memo para componentes pesados
- **WebSocket Optimization**: Reconexión exponential backoff

### **Backend**
- **Async/Await**: ThreadPoolExecutor para operaciones blocking
- **Connection Pooling**: MCP connections persistentes
- **Memory Management**: Cleanup automático de recursos
- **uvloop**: Event loop optimizado para Linux

## 🔧 Configuración Avanzada

### **Selección de Modelos**
- **Gemini 2.5 Flash**: Balance velocidad/capacidad
- **Ollama Local**: Modelos offline (gpt-oss:20b, llama3:8b, etc.)

### **Motores TTS**
- **ElevenLabs**: Calidad premium, requiere API key
- **Edge-TTS**: Gratuito, voces Microsoft

### **Idiomas Soportados**
- **Español**: Reconocimiento y síntesis completa
- **Inglés**: Reconocimiento y síntesis completa
- **Cambio dinámico**: Sin reiniciar el sistema

### **GPU AMD Support**
```python
# Detección automática multi-método
def get_gpu_usage():
    # 1. ROCm-smi --showuse
    # 2. amdgpu_top -J -n 1  
    # 3. /sys/class/drm/card*/device/gpu_busy_percent
    # 4. radeontop -d - -l 1
    # 5. Detección de Ollama activo
```

## 🐛 Resolución de Problemas

### **Problemas Comunes**

#### **Audio no funciona**
```bash
# Verificar permisos de micrófono
sudo usermod -a -G audio $USER

# Comprobar dispositivos
arecord -l
pulseaudio --check

# Logs de audio
tail -f logs/aura_websocket.log | grep -i audio
```

#### **MCP Servers fallan**
```bash
# Verificar Node.js y dependencies
node --version  # >= 16
npm list -g @modelcontextprotocol/server-sequential-thinking

# Test individual de servidores
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | node mcp/serpapi_server.js
```

#### **Frontend no carga**
```bash
# Verificar puertos
netstat -tulpn | grep -E ':(5173|8000|8766)'

# Logs detallados
cd frontend && npm run dev -- --verbose
```

### **Logs del Sistema**
```bash
# Estructura completa de logs
logs/
├── aura_websocket.log           # Servidor principal
├── backend_stats.log            # API de estadísticas  
└── frontend.log                 # React dev server

# Monitoreo en tiempo real
tail -f logs/aura_websocket.log logs/backend_stats.log
```

## 📊 Métricas y Monitoreo

### **Estadísticas en Vivo**
- **CPU Usage**: Via psutil con interval optimizado
- **GPU AMD**: Múltiples métodos de detección
- **Memory**: Virtual memory percentage
- **Disk Usage**: Root filesystem utilization

### **Performance Insights**
- **Function Calls**: Hasta 15 iteraciones por consulta
- **TTS Buffer**: Queue size y tiempo de reproducción
- **WebSocket**: Latencia y reconexión automática
- **MCP Connections**: Health checks y timeouts

### **Analytics de Uso**
- **Sequential Thinking**: Frecuencia y complejidad de pensamientos
- **Calendar Integration**: Análisis de productividad semanal/mensual
- **Search Patterns**: Tipos de búsquedas más frecuentes
- **Audio Processing**: Tiempo de respuesta STT->TTS

## 🤝 Contribuciones y Desarrollo

### **Estructura para Contribuir**
1. **Fork** el proyecto
2. **Feature branch**: `git checkout -b feature/AmazingFeature`
3. **Testing**: Verificar que todas las herramientas MCP funcionen
4. **Documentation**: Actualizar README y doc/ si necesario
5. **Pull Request**: Con descripción detallada

### **Agregar Nuevos MCP Servers**
```javascript
// 1. Crear server en mcp/nuevo_server.js
class NuevoServer {
    constructor() {
        this.tools = [
            {
                name: "nueva_herramienta",
                description: "CUÁNDO USAR: ... CÓMO USAR: ...",
                inputSchema: { /* JSON Schema */ }
            }
        ];
    }
    
    async callTool(params) {
        // Implementación de la herramienta
    }
}
```

```python
# 2. Agregar a client/config.py
config["nuevo-server"] = {
    "command": "node",
    "args": [os.path.join(mcp_dir, "nuevo_server.js")],
    "env": {"API_KEY": os.getenv("NUEVA_API_KEY")}
}
```

## 📚 Documentación Técnica

Para documentación detallada sobre la implementación, consulta:

- **`doc/01_cliente_gemini.md`**: Arquitectura del cliente Gemini y MCP
- **`doc/02_frontend_integracion.md`**: Frontend React y integración backend  
- **`doc/03_servidores_mcp.md`**: Implementación de herramientas MCP

## 🙏 Reconocimientos

- **Api Gratuita de Google Gemini**: Modelo de IA de última generación
- **Anthropic Sequential Thinking**: Servidor oficial de razonamiento
- **Model Context Protocol**: Arquitectura extensible de herramientas
- **Vosk**: Reconocimiento de voz offline
- **Open-Meteo**: API meteorológica gratuita
- **SerpAPI**: Búsquedas web estructuradas

---

> *Aura representa el estado del arte en asistentes de IA conversacionales, combinando razonamiento secuencial visible, procesamiento de audio en tiempo real, y herramientas especializadas en una experiencia futurista e inmersiva.*
