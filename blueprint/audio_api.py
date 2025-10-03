"""
REST API para recibir audio del navegador y transcribirlo con Vosk
Endpoint que recibe audio, lo convierte a WAV y lo transcribe
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
from datetime import datetime
import logging
import subprocess

# Agregar path a la carpeta voice para importar hear.py
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear instancia de FastAPI
app = FastAPI(
    title="Audio Recording API",
    description="API para recibir grabaciones de audio del navegador",
    version="1.0.0"
)

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica el origen exacto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar SpeechToText desde voice/hear.py
from hear import SpeechToText

# Crear carpeta para guardar audios si no existe
AUDIO_FOLDER = "blueprint/recordings"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Inicializar Vosk STT (español por defecto)
logger.info("🎤 Inicializando Vosk STT...")
try:
    stt = SpeechToText(language="es")
    logger.info("✅ Vosk STT inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando Vosk: {e}")
    stt = None


def convert_audio_to_wav(input_path: str, output_path: str) -> bool:
    """
    Convierte cualquier formato de audio a WAV mono 16kHz para Vosk usando ffmpeg

    Args:
        input_path: Ruta al archivo de entrada (webm, mp4, etc.)
        output_path: Ruta donde guardar el WAV convertido

    Returns:
        bool: True si la conversión fue exitosa
    """
    try:
        logger.info(f"🔄 Convirtiendo {input_path} a WAV con ffmpeg...")

        # Comando ffmpeg para convertir a WAV mono 16kHz 16-bit PCM
        command = [
            'ffmpeg',
            '-i', input_path,           # Input file
            '-ar', '16000',              # Sample rate 16kHz
            '-ac', '1',                  # Mono (1 channel)
            '-sample_fmt', 's16',        # 16-bit PCM
            '-y',                        # Overwrite output file
            output_path
        ]

        # Ejecutar ffmpeg
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        logger.info(f"✅ Audio convertido exitosamente a {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error ejecutando ffmpeg: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        logger.error("❌ ffmpeg no está instalado. Instálalo con: sudo apt-get install ffmpeg")
        return False
    except Exception as e:
        logger.error(f"❌ Error convirtiendo audio: {e}")
        return False


@app.get("/")
async def root():
    """Endpoint raíz para verificar que la API está funcionando"""
    return {
        "message": "Audio Recording API está funcionando",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload-audio": "Subir archivo de audio",
            "GET /health": "Verificar estado del servidor"
        }
    }


@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/upload-audio")
async def upload_audio(audio: UploadFile = File(...)):
    """
    Recibe un archivo de audio del navegador, lo guarda y lo transcribe con Vosk

    Args:
        audio: Archivo de audio (webm, mp4, wav, etc.)

    Returns:
        JSON con información del archivo y transcripción
    """
    wav_temp_path = None
    try:
        logger.info(f"📥 Recibiendo archivo de audio: {audio.filename}")
        logger.info(f"📊 Content-Type: {audio.content_type}")

        # Leer el contenido del archivo
        audio_data = await audio.read()
        audio_size = len(audio_data)

        logger.info(f"📦 Tamaño del archivo: {audio_size} bytes ({audio_size / 1024:.2f} KB)")

        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Detectar extensión del archivo basado en content_type
        extension_map = {
            "audio/webm": "webm",
            "audio/webm;codecs=opus": "webm",
            "audio/ogg": "ogg",
            "audio/mp4": "mp4",
            "audio/wav": "wav",
            "audio/mpeg": "mp3"
        }

        extension = extension_map.get(audio.content_type, "webm")
        filename = f"recording_{timestamp}.{extension}"
        filepath = os.path.join(AUDIO_FOLDER, filename)

        # Guardar el archivo original
        with open(filepath, "wb") as f:
            f.write(audio_data)

        logger.info(f"✅ Archivo guardado exitosamente: {filepath}")

        # Transcribir el audio con Vosk
        transcription = None
        if stt:
            try:
                # Crear archivo temporal WAV
                wav_temp_path = os.path.join(AUDIO_FOLDER, f"temp_{timestamp}.wav")

                # Convertir a WAV si no es WAV
                if extension != "wav":
                    logger.info("🔄 Convirtiendo audio a formato WAV para Vosk...")
                    if convert_audio_to_wav(filepath, wav_temp_path):
                        logger.info("📝 Iniciando transcripción con Vosk...")
                        transcription = stt.transcribe_audio_file(wav_temp_path)
                        logger.info(f"✅ Transcripción completada: '{transcription}'")
                    else:
                        logger.warning("⚠️ No se pudo convertir el audio a WAV")
                else:
                    # Ya es WAV, transcribir directamente
                    logger.info("📝 Iniciando transcripción con Vosk...")
                    transcription = stt.transcribe_audio_file(filepath)
                    logger.info(f"✅ Transcripción completada: '{transcription}'")

            except Exception as e:
                logger.error(f"❌ Error en transcripción: {e}", exc_info=True)
                transcription = f"Error transcribiendo: {str(e)}"
        else:
            transcription = "Vosk no inicializado"

        # Retornar información del archivo y transcripción
        response_data = {
            "success": True,
            "message": "Audio recibido y transcrito correctamente",
            "file": {
                "filename": filename,
                "size": audio_size,
                "size_kb": round(audio_size / 1024, 2),
                "content_type": audio.content_type,
                "saved_path": filepath,
                "timestamp": timestamp
            },
            "transcription": transcription
        }

        return JSONResponse(status_code=200, content=response_data)

    except Exception as e:
        logger.error(f"❌ Error procesando audio: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el audio: {str(e)}"
        )
    finally:
        # Limpiar archivo temporal WAV
        if wav_temp_path and os.path.exists(wav_temp_path):
            try:
                os.remove(wav_temp_path)
                logger.info(f"🗑️ Archivo temporal eliminado: {wav_temp_path}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar archivo temporal: {e}")


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Iniciando servidor de Audio API...")
    logger.info(f"📁 Carpeta de grabaciones: {os.path.abspath(AUDIO_FOLDER)}")

    # Iniciar servidor en puerto 8001 (8000 es para system-stats)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
