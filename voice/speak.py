#!/usr/bin/env python3
"""
Módulo de síntesis de voz (Text to Speech)
Utiliza ElevenLabs y pygame para convertir texto a voz en español
Versión optimizada para evitar cortes y delays
"""

import os
import tempfile
import threading
import queue
import time as time_module
import atexit
import requests
import re
from pygame import mixer

# Importar gTTS como fallback
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("⚠️ gTTS no disponible. Solo se usará ElevenLabs.")

# NUEVO: intentar usar mutagen para conocer con precisión la duración del MP3
try:
    from mutagen.mp3 import MP3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

# Motor TTS actual (puede ser 'elevenlabs' o 'gtts')
CURRENT_TTS_ENGINE = 'gtts'  # Por defecto gTTS para ahorrar API

# Configuración ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/"

# Voces populares de ElevenLabs en español
ELEVENLABS_VOICES = {
    "spanish_male": "pNInz6obpgDQGcFmaJgB",      # Adam (inglés pero funciona bien)
    "spanish_female": "EXAVITQu4vr4xnSDxMaL",     # Bella (inglés pero suena bien)
    "multilingual_v1": "pMsXgVXv3BLzUgSXRplE",   # Premade voice multilingue
    "multilingual_v2": "IKne3meq5aSn9XLyUdCD",   # Premade voice multilingue 
    "default": "pNInz6obpgDQGcFmaJgB"             # Adam por defecto
}

# Usar voz por defecto
DEFAULT_VOICE_ID = ELEVENLABS_VOICES["multilingual_v1"]

# Constante global de longitud segura de texto por chunk
MAX_TTS_CHARACTERS = 180  # margen para cualquier motor

def generate_elevenlabs_audio(text, voice_id=None, output_file=None):
    """
    Genera audio usando ElevenLabs API
    
    Args:
        text (str): Texto a sintetizar
        voice_id (str): ID de la voz (opcional)
        output_file (str): Archivo de salida (opcional)
    
    Returns:
        str: Ruta del archivo de audio generado
    """
    if not text or text.isspace():
        return None
    
    if not voice_id:
        voice_id = DEFAULT_VOICE_ID
    
    if not output_file:
        output_file = os.path.join(tempfile.gettempdir(), f"elevenlabs_{int(time_module.time() * 1000)}.mp3")
    
    try:
        url = f"{ELEVENLABS_URL}{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",  # Modelo multilingüe para español
            "voice_settings": {
                "stability": 0.7,           # Más estable para evitar artefactos
                "similarity_boost": 0.9,    # Mayor similitud a la voz original
                "style": 0.2,               # Algo de expresividad 
                "use_speaker_boost": True   # Mejora la claridad
            }
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return output_file
        else:
            print(f"❌ Error ElevenLabs API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error generando audio con ElevenLabs: {e}")
        return None

def generate_gtts_audio(text, output_file=None, lang='es', slow=False):
    """
    Genera audio usando gTTS (Google Text-to-Speech)
    
    Args:
        text (str): Texto a sintetizar
        output_file (str): Archivo de salida (opcional)
        lang (str): Idioma
        slow (bool): Velocidad lenta
    
    Returns:
        str: Ruta del archivo de audio generado
    """
    if not GTTS_AVAILABLE:
        print("❌ gTTS no está disponible")
        return None
        
    if not text or text.isspace():
        return None
    
    if not output_file:
        output_file = os.path.join(tempfile.gettempdir(), f"gtts_{int(time_module.time() * 1000)}.mp3")
    
    try:
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(output_file)
        return output_file
    except Exception as e:
        print(f"❌ Error generando audio con gTTS: {e}")
        return None

def generate_audio_with_current_engine(text, output_file=None, lang='es', slow=False):
    """
    Genera audio usando el motor TTS configurado actualmente
    
    Args:
        text (str): Texto a sintetizar
        output_file (str): Archivo de salida (opcional)
        lang (str): Idioma
        slow (bool): Velocidad lenta
    
    Returns:
        str: Ruta del archivo de audio generado
    """
    global CURRENT_TTS_ENGINE
    
    if CURRENT_TTS_ENGINE == 'elevenlabs':
        return generate_elevenlabs_audio(text, output_file=output_file)
    elif CURRENT_TTS_ENGINE == 'gtts':
        return generate_gtts_audio(text, output_file=output_file, lang=lang, slow=slow)
    else:
        print(f"❌ Motor TTS desconocido: {CURRENT_TTS_ENGINE}")
        return None

def set_tts_engine(engine_name):
    """
    Cambia el motor TTS actual
    
    Args:
        engine_name (str): 'elevenlabs' o 'gtts'
    
    Returns:
        bool: True si el cambio fue exitoso
    """
    global CURRENT_TTS_ENGINE
    
    if engine_name == 'elevenlabs':
        CURRENT_TTS_ENGINE = 'elevenlabs'
        print("✅ Motor TTS cambiado a ElevenLabs")
        return True
    elif engine_name == 'gtts':
        if GTTS_AVAILABLE:
            CURRENT_TTS_ENGINE = 'gtts'
            print("✅ Motor TTS cambiado a gTTS")
            return True
        else:
            print("❌ gTTS no está disponible")
            return False
    else:
        print(f"❌ Motor TTS no válido: {engine_name}. Usa 'elevenlabs' o 'gtts'")
        return False

def get_current_tts_engine():
    """
    Obtiene el motor TTS actual
    
    Returns:
        str: Motor TTS actual ('elevenlabs' o 'gtts')
    """
    return CURRENT_TTS_ENGINE

def get_available_tts_engines():
    """
    Obtiene la lista de motores TTS disponibles
    
    Returns:
        list: Lista de motores disponibles
    """
    engines = ['elevenlabs']
    if GTTS_AVAILABLE:
        engines.append('gtts')
    return engines

def change_voice(voice_name):
    """
    Cambia la voz utilizada por ElevenLabs
    
    Args:
        voice_name (str): Nombre de la voz a usar
    
    Returns:
        bool: True si el cambio fue exitoso
    """
    global DEFAULT_VOICE_ID
    
    if voice_name in ELEVENLABS_VOICES:
        DEFAULT_VOICE_ID = ELEVENLABS_VOICES[voice_name]
        print(f"✅ Voz cambiada a: {voice_name} (ID: {DEFAULT_VOICE_ID})")
        return True
    else:
        print(f"❌ Voz '{voice_name}' no encontrada. Voces disponibles: {list(ELEVENLABS_VOICES.keys())}")
        return False

def get_available_voices():
    """
    Obtiene la lista de voces disponibles
    
    Returns:
        dict: Diccionario con las voces disponibles
    """
    return ELEVENLABS_VOICES.copy()

def get_current_voice():
    """
    Obtiene la voz actualmente seleccionada
    
    Returns:
        str: ID de la voz actual
    """
    return DEFAULT_VOICE_ID

class StreamingTTS:
    def __init__(self):
        """
        Clase para TTS en streaming con orden secuencial garantizado
        """
        self.text_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.synthesizer = None
        self.audio_lock = threading.Lock()  # Para garantizar orden secuencial
        self.first_chunk_played = False  # Para iniciar el audio lo antes posible
        
    def start(self, synthesizer):
        """
        Inicia el worker de TTS en un hilo separado
        """
        self.synthesizer = synthesizer
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.worker_thread.start()
    
    def add_text(self, text_chunk):
        """
        Añade un fragmento de texto a la cola para síntesis
        """
        if text_chunk.strip():
            self.text_queue.put(text_chunk)
    
    def finish(self):
        """
        Indica que no hay más texto y espera a que termine
        """
        self.text_queue.put(None)  # Señal de fin
        
        # Esperar a que el worker termine de procesar todo
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=15)  # Aumentado el timeout
            
        self.is_running = False
    
    def _tts_worker(self):
        """
        Worker que procesa la cola de texto y reproduce audio secuencialmente
        Optimizado para reproducir por oraciones completas (separadas por ".")
        """
        buffer = ""
        sentence_endings = ['.', ',', ';', '?', '!', '\n']  # Más delimitadores
        finish_signal_received = False
        last_speech_time = time_module.time()  # Para forzar reproducción por tiempo
        
        while self.is_running:
            try:
                text_chunk = self.text_queue.get(timeout=1)
                
                if text_chunk is None:  # Señal de fin
                    finish_signal_received = True
                    break
                
                buffer += text_chunk
                
                # Buscar final de oración para reproducir (solo punto)
                sentence_found = False
                for ending in sentence_endings:
                    if ending in buffer:
                        # Encontrar la posición del primer final de oración
                        pos = buffer.find(ending)
                        sentence = buffer[:pos + 1]
                        buffer = buffer[pos + 1:].lstrip()  # Eliminar espacios al inicio del buffer restante
                        
                        if sentence.strip():
                            self._speak_chunk_sync(sentence.strip())
                            sentence_found = True
                            last_speech_time = time_module.time()  # Actualizar tiempo de última reproducción
                        break
                
                # Forzar reproducción si ha pasado mucho tiempo sin hablar
                current_time = time_module.time()

                # Tiempo límite dinámico: 1s para el primer chunk, 4s después
                max_silence = 1.0 if not self.first_chunk_played else 4.0

                # Reglas adicionales para arrancar rápido el primer audio
                if buffer.strip():
                    # Si aún no hemos hablado y el buffer tiene >80 caracteres
                    if not self.first_chunk_played and len(buffer) > 80:
                        self._speak_chunk_sync(buffer.strip())
                        buffer = ""
                        last_speech_time = current_time
                        self.first_chunk_played = True
                    elif (current_time - last_speech_time) > max_silence:
                        self._speak_chunk_sync(buffer.strip())
                        buffer = ""
                        last_speech_time = current_time
                        self.first_chunk_played = True
                
            except queue.Empty:
                # Continuar si no hay nuevos chunks, pero verificar si debemos finalizar
                if not self.is_running:
                    break
                # También verificar timeout por tiempo cuando no hay nuevos chunks
                current_time = time_module.time()
                max_silence = 1.0 if not self.first_chunk_played else 3.0
                if buffer.strip() and (current_time - last_speech_time) > max_silence:
                    self._speak_chunk_sync(buffer.strip())
                    buffer = ""
                    last_speech_time = current_time
                    self.first_chunk_played = True
                continue
            except Exception as e:
                print(f"❌ Error en TTS worker: {e}")
                break
        
        # CRUCIAL: Reproducir TODO el buffer restante al finalizar
        if buffer.strip():
            self._speak_chunk_sync(buffer.strip())
        self.first_chunk_played = True
    
    def _speak_chunk_sync(self, text):
        """
        Reproduce un fragmento de texto de forma secuencial (sin paralelo)
        """
        # Saltar fragmentos sin ningún carácter alfanumérico para evitar errores de gTTS
        if not re.search(r"[a-zA-Z0-9ÁÉÍÓÚáéíóú]", text):
            return

        if self.synthesizer and text.strip():
            with self.audio_lock:  # Garantizar que solo se reproduce uno a la vez
                self.synthesizer.speak_chunk_sequential(text)

class VoiceSynthesizer:
    def __init__(self):
        """
        Inicializa el sintetizador de voz
        """
        self.initialized = False
        self.temp_dir = tempfile.gettempdir()
        self.audio_counter = 0
        self.temp_files = []  # Lista para rastrear archivos temporales
        self.initialize()
        
        # Registrar limpieza al salir
        atexit.register(self.cleanup)
    
    def initialize(self):
        """
        Inicializa el mixer de pygame para reproducción de audio
        
        Returns:
            bool: True si se inicializa correctamente
        """
        try:
            # Configuración optimizada de pygame mixer
            mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            mixer.init()
            self.initialized = True
            print(f"✅ Sintetizador de voz ({CURRENT_TTS_ENGINE.upper()} + Pygame) iniciado")
            return True
        except Exception as e:
            print(f"❌ Error al inicializar el sintetizador de voz: {e}")
            self.initialized = False
            return False
    
    def speak(self, text_to_speak, lang='es', slow=False):
        """
        Convierte texto a voz y lo reproduce
        
        Args:
            text_to_speak (str): Texto a convertir en voz
            lang (str): Idioma para la síntesis (por defecto 'es' para español)
            slow (bool): Si True, habla más lentamente
            
        Returns:
            bool: True si se reproduce correctamente
        """
        if not self.initialized:
            print("❌ El sintetizador no está inicializado")
            return False
        
        if not text_to_speak or text_to_speak.isspace():
            print("🤐 Texto vacío, no hay nada que decir")
            return False

        try:
            # Crear archivo de audio temporal
            audio_file = os.path.join(self.temp_dir, f"response_{self.audio_counter}.mp3")
            self.audio_counter += 1
            self.temp_files.append(audio_file)
            
            # Generar audio con el motor actual
            print(f"🗣️ Diciendo ({CURRENT_TTS_ENGINE.upper()}): {text_to_speak}")
            audio_file = generate_audio_with_current_engine(text_to_speak, output_file=audio_file, lang=lang, slow=slow)
            
            if not audio_file or not os.path.exists(audio_file):
                print(f"❌ No se pudo generar el audio con {CURRENT_TTS_ENGINE.upper()}")
                return False
            
            # Reproducir audio con pygame
            mixer.music.load(audio_file)
            mixer.music.play()
            
            # Esperar a que termine la reproducción usando la duración real
            duration = _get_audio_length(audio_file)
            if duration <= 0:
                duration = 30  # valor de respaldo
            timeout = duration + 2  # pequeño margen extra

            start_time = time_module.time()
            while mixer.music.get_busy():
                if time_module.time() - start_time > timeout:
                    break  # algo salió mal, salimos del bucle
                time_module.sleep(0.01)
            
            # Limpiar archivo temporal de forma segura
            self._safe_cleanup_file(audio_file)
            
            return True
            
        except Exception as e:
            print(f"❌ Error al sintetizar/reproducir voz: {e}")
            return False
    
    def speak_chunk_sequential(self, text_chunk, lang='es'):
        """
        Reproduce un fragmento de texto de forma secuencial (sin hilo separado)
        Garantiza el orden correcto de reproducción - VERSIÓN OPTIMIZADA
        
        Args:
            text_chunk (str): Fragmento de texto a reproducir
            lang (str): Idioma para la síntesis
        """
        if not self.initialized:
            return False
        
        # Ignorar fragmentos vacíos o que no tengan alfanuméricos
        if not text_chunk or text_chunk.isspace() or not re.search(r"[a-zA-Z0-9ÁÉÍÓÚáéíóú]", text_chunk):
            return False

        # Dividir texto largo en chunks manejables para cualquier motor TTS
        if len(text_chunk) > MAX_TTS_CHARACTERS:
            for part in _split_text_into_chunks(text_chunk, MAX_TTS_CHARACTERS):
                self.speak_chunk_sequential(part, lang)
            return True

        try:
            # Generar nombre único para evitar conflictos
            self.audio_counter += 1
            audio_file = os.path.join(self.temp_dir, f"seq_chunk_{self.audio_counter}.mp3")
            self.temp_files.append(audio_file)
            
            # Generar audio con el motor actual
            audio_file = generate_audio_with_current_engine(text_chunk, output_file=audio_file, lang=lang)
            
            if not audio_file or not os.path.exists(audio_file):
                print(f"❌ No se pudo generar chunk de audio con {CURRENT_TTS_ENGINE.upper()}")
                return False
            
            # Esperar indefinidamente hasta que termine el audio anterior
            while mixer.music.get_busy():
                time_module.sleep(0.01)
            
            # Cargar y reproducir
            mixer.music.load(audio_file)
            mixer.music.play()
            
            # Esperar a que termine la reproducción actual basándonos en la duración real
            duration = _get_audio_length(audio_file)
            if duration <= 0:
                duration = 30  # respaldo
            timeout = duration + 2  # margen extra

            start_time = time_module.time()
            while mixer.music.get_busy():
                if time_module.time() - start_time > timeout:
                    break
                time_module.sleep(0.01)
            
            # Limpiar archivo temporal de forma segura
            self._safe_cleanup_file(audio_file)
            
            return True
                
        except Exception as e:
            print(f"❌ Error en chunk secuencial: {e}")
            return False
    
    def _safe_cleanup_file(self, audio_file):
        """
        Limpia un archivo de forma segura sin causar errores
        """
        try:
            # Pequeña pausa para asegurar que pygame terminó de usar el archivo
            time_module.sleep(0.05)
            
            if os.path.exists(audio_file):
                os.remove(audio_file)
                if audio_file in self.temp_files:
                    self.temp_files.remove(audio_file)
        except Exception as e:
            print(f"⚠️ No se pudo limpiar archivo temporal {audio_file}: {e}")
    
    def _async_worker(self, text, lang='es', slow=False):
        """Hilo interno que reproduce texto de forma asíncrona"""
        try:
            # Ya no dividimos: reproducir el texto completo en un solo MP3
            # Crear archivo de audio temporal
            audio_file = os.path.join(self.temp_dir, f"response_async_{self.audio_counter}.mp3")
            self.audio_counter += 1
            self.temp_files.append(audio_file)

            print(f"🗣️ Diciendo ({CURRENT_TTS_ENGINE.upper()}): {text}")
            audio_file = generate_audio_with_current_engine(text, output_file=audio_file, lang=lang, slow=slow)

            if not audio_file or not os.path.exists(audio_file):
                print(f"❌ No se pudo generar audio asíncrono con {CURRENT_TTS_ENGINE.upper()}")
                return

            # Reproducir audio sin bloquear
            mixer.music.load(audio_file)
            mixer.music.play()

            # Esperar y limpiar
            duration = _get_audio_length(audio_file)
            if duration <= 0:
                duration = 30
            timeout = duration + 2

            start_time = time_module.time()
            while mixer.music.get_busy():
                if time_module.time() - start_time > timeout:
                    break
                time_module.sleep(0.01)

            self._safe_cleanup_file(audio_file)
        except Exception as e:
            print(f"❌ Error en voz asíncrona: {e}")

    def speak_async(self, text, lang='es', slow=False):
        """Inicia la reproducción de texto en un hilo separado"""
        if not self.initialized:
            print("❌ El sintetizador no está inicializado")
            return False

        if not text or text.isspace():
            return False

        threading.Thread(target=self._async_worker, args=(text, lang, slow), daemon=True).start()
        return True
    
    def is_speaking(self):
        """
        Verifica si actualmente se está reproduciendo audio
        
        Returns:
            bool: True si se está reproduciendo audio
        """
        if not self.initialized:
            return False
        return mixer.music.get_busy()
    
    def stop_speaking(self):
        """
        Detiene la reproducción actual
        """
        if self.initialized:
            mixer.music.stop()
    
    def test_voice(self):
        """
        Función de prueba para verificar que la síntesis funciona
        
        Returns:
            bool: True si la prueba es exitosa
        """
        test_text = f"Hola, soy Aura. El sintetizador de voz con {CURRENT_TTS_ENGINE.upper()} está funcionando correctamente."
        return self.speak(test_text)
    
    def cleanup(self):
        """
        Limpia recursos del sintetizador
        """
        if self.initialized:
            try:
                mixer.music.stop()
                
                # Limpiar todos los archivos temporales restantes
                for temp_file in self.temp_files[:]:  # Copia la lista para evitar modificaciones durante iteración
                    self._safe_cleanup_file(temp_file)
                
                mixer.quit()
                self.initialized = False
                print("🧹 Sintetizador de voz limpiado")
            except Exception as e:
                # Solo mostrar error si no es el error común de "mixer not initialized"
                if "mixer not initialized" not in str(e):
                    print(f"⚠️ Error durante limpieza: {e}")
                self.initialized = False

# Instancias globales para facilitar el uso
_voice_synthesizer = None
_streaming_tts = None

def get_synthesizer():
    """
    Obtiene la instancia del sintetizador (singleton)
    
    Returns:
        VoiceSynthesizer: Instancia del sintetizador
    """
    global _voice_synthesizer
    if _voice_synthesizer is None:
        _voice_synthesizer = VoiceSynthesizer()
    return _voice_synthesizer

def speak(text, lang='es', slow=False):
    """
    Función simple para síntesis de voz
    
    Args:
        text (str): Texto a sintetizar
        lang (str): Idioma
        slow (bool): Velocidad lenta
        
    Returns:
        bool: True si se reproduce correctamente
    """
    synthesizer = get_synthesizer()
    return synthesizer.speak(text, lang, slow)

def speak_async(text, lang='es', slow=False):
    """
    Función simple para síntesis de voz asíncrona
    """
    synthesizer = get_synthesizer()
    return synthesizer.speak_async(text, lang, slow)

def is_speaking():
    """
    Verifica si se está hablando actualmente
    
    Returns:
        bool: True si se está reproduciendo voz
    """
    synthesizer = get_synthesizer()
    return synthesizer.is_speaking()

def stop_speaking():
    """
    Detiene la síntesis actual
    """
    synthesizer = get_synthesizer()
    synthesizer.stop_speaking()

# Funciones para TTS en streaming
def start_streaming_tts():
    """
    Inicia el sistema de TTS en streaming
    
    Returns:
        StreamingTTS: Instancia del streaming TTS
    """
    global _streaming_tts
    _streaming_tts = StreamingTTS()
    synthesizer = get_synthesizer()
    _streaming_tts.start(synthesizer)
    return _streaming_tts

def add_text_to_stream(text_chunk):
    """
    Añade texto al stream de TTS
    
    Args:
        text_chunk (str): Fragmento de texto a añadir
    """
    global _streaming_tts
    if _streaming_tts:
        _streaming_tts.add_text(text_chunk)

def finish_streaming_tts():
    """
    Finaliza el streaming de TTS
    """
    global _streaming_tts
    if _streaming_tts:
        _streaming_tts.finish()
        _streaming_tts = None

# NUEVO: Helper para obtener la duración real del audio usando pygame

def _get_audio_length(audio_path: str) -> float:
    """
    Devuelve la duración en segundos de un archivo de audio MP3.
    Intenta primero con mutagen; si no está disponible usa pygame.Sound.
    """
    # Con mutagen, más fiable y sin cargar todo el audio
    if MUTAGEN_AVAILABLE:
        try:
            return MP3(audio_path).info.length
        except Exception as e:
            print(f"⚠️ Mutagen no pudo leer duración: {e}")
    # Fallback: pygame
    try:
        sound = mixer.Sound(audio_path)
        return sound.get_length()
    except Exception as e:
        print(f"⚠️ No se pudo obtener duración del audio con pygame: {e}")
        return 0.0

# Helper para dividir texto largo en chunks manejables

def _split_text_into_chunks(text: str, max_len: int = MAX_TTS_CHARACTERS):
    """Divide texto en partes <= max_len intentando respetar signos de puntuación."""
    if len(text) <= max_len:
        return [text.strip()]

    split_regex = re.compile(r"(?<=[\.!?;:,\n])\s+")
    parts = []
    buffer = ""
    for segment in split_regex.split(text):
        if not segment:
            continue
        if len(buffer) + len(segment) + 1 <= max_len:
            buffer += segment + " "
        else:
            parts.append(buffer.strip())
            buffer = segment + " "
    if buffer.strip():
        parts.append(buffer.strip())
    # Garantía extra: si algún segmento sigue siendo demasiado largo, cortar duro
    final_parts = []
    for p in parts:
        if len(p) <= max_len:
            final_parts.append(p)
        else:
            # cortar por longitud
            for i in range(0, len(p), max_len):
                final_parts.append(p[i:i+max_len])
    return final_parts

if __name__ == "__main__":
    # Prueba del módulo
    print("🗣️ Prueba del sintetizador de voz")
    
    synthesizer = VoiceSynthesizer()
    if synthesizer.initialized:
        synthesizer.test_voice()
        
        # Prueba interactiva
        while True:
            text = input("\nEscribe algo para que lo diga (o 'salir' para terminar): ")
            if text.lower() in ['salir', 'exit']:
                break
            synthesizer.speak(text)
        
        synthesizer.cleanup()
    else:
        print("❌ No se pudo inicializar el sintetizador") 