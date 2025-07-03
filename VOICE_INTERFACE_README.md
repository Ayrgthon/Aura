# 🎤 Interfaz de Voz Web para Aura

## 📋 Descripción

Esta integración conecta la interfaz gráfica `stellar-voice-display` con el asistente Aura, permitiendo usar el reconocimiento de voz desde una interfaz web moderna.

## 🚀 Cómo Usar

### Opción 1: Desde el main.py (Recomendado)

1. **Ejecutar el asistente:**
   ```bash
   python main.py
   ```

2. **Seleccionar modelo** (Gemini o Ollama)

3. **Cuando te pregunte sobre voz, responder "sí"**
   - Se iniciará automáticamente el servidor WebSocket
   - Se abrirá la interfaz web en el navegador

4. **En el navegador:**
   - Hacer clic en el botón "Voice control, touch to activate"
   - Hablar cuando veas "Escuchando..."
   - El texto reconocido aparecerá en pantalla

### Opción 2: Script Directo

```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x start_voice_interface.sh

# Ejecutar
./start_voice_interface.sh
```

## 🏗️ Arquitectura

```
┌─────────────────┐     WebSocket      ┌────────────────┐
│   Interfaz Web  │ ◄──────────────► │ WebSocket Server│
│ (React + Vite)  │     ws://8765     │   (Python)      │
└─────────────────┘                    └────────────────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │ Voice Engine│
                                       │ (Vosk + gTTS)│
                                       └─────────────┘
```

## 📡 Protocolo WebSocket

### Mensajes del Cliente → Servidor

```json
// Iniciar reconocimiento de voz
{
  "type": "start_listening"
}

// Detener reconocimiento
{
  "type": "stop_listening"
}

// Sintetizar texto (TTS)
{
  "type": "speak",
  "text": "Texto a sintetizar"
}
```

### Mensajes del Servidor → Cliente

```json
// Conexión establecida
{
  "type": "connection",
  "status": "connected",
  "message": "Conectado al servidor Aura"
}

// Texto reconocido
{
  "type": "speech_recognized",
  "text": "texto reconocido",
  "timestamp": "2024-01-01T12:00:00"
}

// Estado del sistema
{
  "type": "status",
  "listening": true/false,
  "speaking": true/false,
  "message": "mensaje de estado"
}

// Error
{
  "type": "error",
  "message": "descripción del error"
}
```

## 🛠️ Componentes

### Backend (Python)

- **websocket_server.py**: Servidor WebSocket que expone las funcionalidades de voz
- **engine/voice/hear.py**: Reconocimiento de voz con Vosk
- **engine/voice/speak.py**: Síntesis de voz con gTTS

### Frontend (React)

- **useWebSocket.ts**: Hook personalizado para manejar la conexión WebSocket
- **VoiceAssistant.tsx**: Componente principal con la interfaz de usuario
- **EnergyOrb.tsx**: Visualización animada del estado

## 🔧 Configuración

### Puertos

- **Frontend**: http://localhost:5173
- **WebSocket**: ws://localhost:8765

### Requisitos

- Python 3.8+
- Node.js 18+
- Micrófono funcional
- Modelo Vosk español instalado

## 🐛 Solución de Problemas

### "No se conecta al WebSocket"

1. Verificar que el servidor esté ejecutándose:
   ```bash
   ps aux | grep websocket_server.py
   ```

2. Verificar el puerto:
   ```bash
   netstat -an | grep 8765
   ```

### "No reconoce voz"

1. Verificar permisos del micrófono
2. Probar el micrófono:
   ```bash
   arecord -d 3 test.wav && aplay test.wav
   ```

### "La interfaz no se abre"

1. Verificar Node.js:
   ```bash
   node --version
   npm --version
   ```

2. Instalar dependencias manualmente:
   ```bash
   cd stellar-voice-display
   npm install
   ```

## 🚀 Mejoras Futuras

- [ ] Streaming de respuestas del asistente en tiempo real
- [ ] Visualización de formas de onda de audio
- [ ] Soporte para múltiples idiomas
- [ ] Integración completa con el chat del asistente
- [ ] Configuración de modelos desde la interfaz

## 📝 Notas

- La interfaz solo maneja la parte de voz por ahora
- El chat principal sigue siendo por línea de comandos
- El WebSocket se reconecta automáticamente si se pierde la conexión 