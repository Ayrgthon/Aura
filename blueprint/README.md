# Audio Recording REST API con Transcripción Vosk

API REST para recibir archivos de audio grabados desde el navegador y transcribirlos automáticamente usando Vosk.

## Instalación

```bash
# Instalar dependencias Python
pip install -r requirements.txt

# Instalar ffmpeg (requerido para conversión de audio)
# En Ubuntu/Debian:
sudo apt-get install ffmpeg

# En macOS:
brew install ffmpeg

# En Windows: Descargar de https://ffmpeg.org/download.html
```

## Modelos de Vosk

Asegúrate de tener los modelos de Vosk descargados en la carpeta `voice/`:
- Español: `vosk-model-es-0.42`
- Inglés: `vosk-model-en-us-0.42-gigaspeech`

Puedes descargarlos desde: https://alphacephei.com/vosk/models

## Uso

### Iniciar el servidor

```bash
python audio_api.py
```

El servidor se iniciará en `http://localhost:8001`

**Nota:** El puerto 8001 se usa para evitar conflictos con la API de system-stats que corre en el puerto 8000.

### Endpoints disponibles

#### `GET /`
Información sobre la API

#### `GET /health`
Verificar estado del servidor

#### `POST /upload-audio`
Subir archivo de audio y obtener transcripción

**Body (form-data):**
- `audio`: Archivo de audio (webm, mp4, wav, etc.)

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Audio recibido y transcrito correctamente",
  "file": {
    "filename": "recording_20250103_162045.webm",
    "size": 12345,
    "size_kb": 12.05,
    "content_type": "audio/webm;codecs=opus",
    "saved_path": "blueprint/recordings/recording_20250103_162045.webm",
    "timestamp": "20250103_162045"
  },
  "transcription": "hola este es un ejemplo de transcripción con vosk"
}
```

## Prueba con curl

```bash
curl -X POST http://localhost:8000/upload-audio \
  -F "audio=@ruta/al/archivo.webm"
```

## Archivos guardados

Los archivos de audio se guardan en la carpeta `blueprint/recordings/`

## Cómo funciona

1. **Recepción**: El frontend graba audio en formato WebM/Opus usando MediaRecorder API
2. **Conversión**: La API usa ffmpeg para convertir el audio a WAV mono 16kHz 16-bit PCM (formato requerido por Vosk)
3. **Transcripción**: Vosk procesa el archivo WAV y genera la transcripción en texto
4. **Respuesta**: Se retorna el archivo guardado y la transcripción al frontend

## CORS

La API está configurada para aceptar peticiones de cualquier origen. En producción, configura `allow_origins` con el dominio específico de tu frontend.

## Notas

- El audio se convierte automáticamente a WAV si no está en ese formato
- Los archivos temporales WAV se eliminan después de la transcripción
- Vosk se inicializa en español por defecto (puedes cambiarlo en el código)
