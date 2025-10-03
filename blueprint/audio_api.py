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
import threading
import time
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Agregar paths necesarios
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice'))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client'))

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

# Importar componentes del sistema
from hear import SpeechToText
from speak import TextToSpeech
from gemini_client import SimpleGeminiClient
from config import get_mcp_servers_config
import asyncio
import base64
import tempfile

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

# Inicializar TTS
logger.info("🔊 Inicializando TTS...")
try:
    tts = TextToSpeech(voice="en-US-EmmaMultilingualNeural")
    logger.info("✅ TTS inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando TTS: {e}")
    tts = None

# Event loop persistente para operaciones async del cliente Gemini
event_loop = None
event_loop_thread = None

def start_event_loop():
    """Inicia un event loop persistente en un thread separado"""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()

def run_async(coro):
    """Ejecuta una corrutina en el event loop persistente"""
    global event_loop
    if not event_loop or event_loop.is_closed():
        raise RuntimeError("Event loop no disponible")
    future = asyncio.run_coroutine_threadsafe(coro, event_loop)
    return future.result()

# Iniciar event loop persistente en thread separado
logger.info("🔄 Iniciando event loop persistente...")
event_loop_thread = threading.Thread(target=start_event_loop, daemon=True)
event_loop_thread.start()

# Esperar a que el loop esté listo
time.sleep(0.1)
logger.info("✅ Event loop persistente iniciado")

# Inicializar Gemini Client
logger.info("🤖 Inicializando Gemini Client...")
gemini_client = None
try:
    gemini_client = SimpleGeminiClient(model_name="gemini-2.5-flash", debug=True)

    # Configurar servidores MCP usando el event loop persistente
    mcp_config = get_mcp_servers_config()
    if mcp_config:
        logger.info(f"🛠️ Configurando {len(mcp_config)} servidores MCP...")
        success = run_async(gemini_client.setup_mcp_servers(mcp_config))

        if success:
            logger.info("✅ Gemini Client y MCP configurados correctamente")
        else:
            logger.warning("⚠️ Algunos servidores MCP fallaron")
    else:
        logger.info("✅ Gemini Client inicializado (sin MCP)")

except Exception as e:
    logger.error(f"❌ Error inicializando Gemini: {e}")
    gemini_client = None


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


@app.get("/status")
async def get_system_status():
    """Endpoint para obtener el estado de todos los componentes del sistema"""
    return {
        "available": True,
        "stt": stt is not None,
        "tts": tts is not None,
        "gemini": gemini_client is not None,
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


@app.post("/process-audio")
async def process_audio(audio: UploadFile = File(...)):
    """
    Endpoint completo: Recibe audio → Transcribe → Procesa con Gemini → Genera TTS → Retorna todo

    Args:
        audio: Archivo de audio (webm, mp4, wav, etc.)

    Returns:
        JSON con transcripción, respuesta de texto y audio en base64
    """
    wav_temp_path = None
    tts_temp_path = None

    try:
        logger.info("=" * 80)
        logger.info("🚀 INICIO DE PROCESO COMPLETO")
        logger.info("=" * 80)

        # === PASO 1: RECIBIR Y GUARDAR AUDIO ===
        logger.info("📥 PASO 1: Recibiendo archivo de audio...")
        audio_data = await audio.read()
        audio_size = len(audio_data)
        logger.info(f"📦 Tamaño: {audio_size} bytes ({audio_size / 1024:.2f} KB)")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

        with open(filepath, "wb") as f:
            f.write(audio_data)
        logger.info(f"✅ PASO 1 COMPLETO: Archivo guardado en {filepath}")

        # === PASO 2: TRANSCRIBIR CON VOSK ===
        logger.info("📝 PASO 2: Transcribiendo audio con Vosk...")
        transcription = None

        if not stt:
            raise Exception("Vosk STT no está inicializado")

        wav_temp_path = os.path.join(AUDIO_FOLDER, f"temp_{timestamp}.wav")

        if extension != "wav":
            if not convert_audio_to_wav(filepath, wav_temp_path):
                raise Exception("No se pudo convertir audio a WAV")
            transcription = stt.transcribe_audio_file(wav_temp_path)
        else:
            transcription = stt.transcribe_audio_file(filepath)

        logger.info(f"✅ PASO 2 COMPLETO: Transcripción: '{transcription}'")

        if not transcription or not transcription.strip():
            raise Exception("Transcripción vacía")

        # === PASO 3: PROCESAR CON GEMINI ===
        logger.info("🤖 PASO 3: Procesando con Gemini...")

        if not gemini_client:
            raise Exception("Gemini Client no está inicializado")

        # Usar el event loop persistente para ejecutar gemini.chat
        gemini_response = run_async(gemini_client.chat(transcription))

        logger.info(f"✅ PASO 3 COMPLETO: Respuesta Gemini: '{gemini_response[:100]}...'")

        if not gemini_response or not gemini_response.strip():
            raise Exception("Respuesta de Gemini vacía")

        # === PASO 4: GENERAR AUDIO CON TTS ===
        logger.info("🔊 PASO 4: Generando audio con TTS...")

        if not tts:
            raise Exception("TTS no está inicializado")

        # Crear archivo temporal para el audio TTS
        tts_temp_path = os.path.join(AUDIO_FOLDER, f"tts_{timestamp}.mp3")

        # Generar audio usando edge-tts directamente (async)
        import edge_tts
        communicate = edge_tts.Communicate(gemini_response, tts.voice, rate="+0%")
        await communicate.save(tts_temp_path)

        if not os.path.exists(tts_temp_path):
            raise Exception("No se pudo generar audio TTS")

        logger.info(f"✅ PASO 4 COMPLETO: Audio TTS generado en {tts_temp_path}")

        # === PASO 5: CONVERTIR AUDIO A BASE64 ===
        logger.info("📦 PASO 5: Convirtiendo audio a base64...")

        with open(tts_temp_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')

        audio_size_kb = len(audio_base64) / 1024
        logger.info(f"✅ PASO 5 COMPLETO: Audio base64 generado ({audio_size_kb:.2f} KB)")

        # === PASO 6: RETORNAR RESPUESTA COMPLETA ===
        logger.info("✅ PROCESO COMPLETO EXITOSO")
        logger.info("=" * 80)

        response_data = {
            "success": True,
            "message": "Audio procesado completamente",
            "transcription": transcription,
            "gemini_response": gemini_response,
            "audio_base64": audio_base64,
            "audio_format": "mp3",
            "processing_time": "< 1s"  # Puedes agregar tracking de tiempo si quieres
        }

        return JSONResponse(status_code=200, content=response_data)

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ ERROR EN PROCESO: {str(e)}")
        logger.error("=" * 80)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando audio: {str(e)}"
        )

    finally:
        # Limpiar archivos temporales
        if wav_temp_path and os.path.exists(wav_temp_path):
            try:
                os.remove(wav_temp_path)
                logger.info(f"🗑️ Archivo WAV temporal eliminado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar WAV temporal: {e}")

        if tts_temp_path and os.path.exists(tts_temp_path):
            try:
                os.remove(tts_temp_path)
                logger.info(f"🗑️ Archivo TTS temporal eliminado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar TTS temporal: {e}")


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
