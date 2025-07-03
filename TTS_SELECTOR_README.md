# 🎤 Selector de Motor TTS - Aura

## Descripción

Se ha implementado un selector de motor de síntesis de voz que permite alternar entre:
- **gTTS**: Motor gratuito de Google (por defecto)
- **ElevenLabs**: Motor premium de alta calidad

## Características

### 🔧 Motores Disponibles
- **gTTS (Google Text-to-Speech)**
  - ✅ Gratuito e ilimitado
  - ✅ Buena calidad de voz
  - ✅ Soporte para español
  - ❌ Voz menos expresiva

- **ElevenLabs**
  - ✅ Calidad premium
  - ✅ Voz muy expresiva y natural
  - ✅ Configuración optimizada para español
  - ❌ API limitada (ideal para presentaciones)

### 🎯 Motor por Defecto
- **gTTS** está configurado por defecto para ahorrar las peticiones de ElevenLabs
- Cambio dinámico desde la interfaz web

## Uso

### Desde la Interfaz Web
1. Hacer clic en el botón ⚙️ (configuración)
2. Seleccionar el motor TTS deseado:
   - **gTTS (Gratuito)**: Para uso diario
   - **ElevenLabs (Premium)**: Para presentaciones

### Desde Código Python
```python
from engine.voice.speak import set_tts_engine, get_current_tts_engine

# Cambiar a gTTS
set_tts_engine('gtts')

# Cambiar a ElevenLabs
set_tts_engine('elevenlabs')

# Obtener motor actual
current = get_current_tts_engine()
print(f"Motor actual: {current}")
```

## Funcionamiento Interno

### Archivos Modificados
- `engine/voice/speak.py`: Lógica de selector TTS
- `stellar-voice-display/src/components/VoiceAssistant.tsx`: Interfaz de usuario
- `websocket_server_simple.py`: Manejo de comandos WebSocket

### Flujo de Funcionamiento
1. Usuario selecciona motor en interfaz
2. Frontend envía comando `change_tts_engine` via WebSocket
3. Backend actualiza `CURRENT_TTS_ENGINE`
4. Próximas síntesis usan el motor seleccionado

## Configuración API

### ElevenLabs
- **API Key**: Configurada en `speak.py`
- **Voz**: multilingual_v1 (optimizada para español)
- **Parámetros**: stability 0.7, similarity_boost 0.9

### gTTS
- **Sin configuración adicional**
- **Idioma**: Español por defecto
- **Velocidad**: Normal (configurable)

## Recomendaciones

- **Uso diario**: Mantener gTTS como motor principal
- **Presentaciones**: Cambiar a ElevenLabs momentáneamente
- **Después de presentar**: Volver a gTTS para ahorrar API
- **Monitoreo**: Verificar consumo de API ElevenLabs

## Verificación

Para verificar que todo funciona correctamente:

```bash
# Desde el directorio del proyecto
python -c "from engine.voice.speak import get_available_tts_engines; print(get_available_tts_engines())"
```

Debe mostrar: `['elevenlabs', 'gtts']`

---

💡 **Consejo**: Usa ElevenLabs solo para presentaciones importantes para conservar tu API gratuita. 