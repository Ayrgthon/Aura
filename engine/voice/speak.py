#!/usr/bin/env python3
"""
Módulo de síntesis de voz (Text to Speech)
Utiliza gTTS y pygame para convertir texto a voz en español
Versión optimizada para evitar cortes y delays
"""

import os
import tempfile
import threading
import queue
import time as time_module
import atexit
from gtts import gTTS
from pygame import mixer

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
        """
        buffer = ""
        sentence_endings = ['.', '!', '?']  # Solo finales de oración importantes
        word_count = 0
        finish_signal_received = False
        last_speech_time = time_module.time()  # Para forzar reproducción por tiempo
        
        while self.is_running:
            try:
                text_chunk = self.text_queue.get(timeout=1)
                
                if text_chunk is None:  # Señal de fin
                    finish_signal_received = True
                    break
                
                buffer += text_chunk
                word_count += len(text_chunk.split())
                
                # Buscar final de oración para reproducir
                sentence_found = False
                for ending in sentence_endings:
                    if ending in buffer:
                        # Encontrar la posición del primer final de oración
                        pos = buffer.find(ending)
                        sentence = buffer[:pos + 1]
                        buffer = buffer[pos + 1:].lstrip()  # Eliminar espacios al inicio del buffer restante
                        
                        if sentence.strip():
                            self._speak_chunk_sync(sentence.strip())
                            word_count = len(buffer.split()) if buffer.strip() else 0
                            sentence_found = True
                            last_speech_time = time_module.time()  # Actualizar tiempo de última reproducción
                        break
                
                # Si no hay final de oración pero ya tenemos varias palabras, reproducir
                if not sentence_found and word_count >= 8:  # Reducido a 8 palabras para procesar más frecuentemente
                    # Buscar el último espacio para cortar en palabra completa
                    words = buffer.split()
                    if len(words) >= 6:
                        # Tomar las primeras 6 palabras y dejar el resto en buffer
                        chunk_words = words[:6]
                        remaining_words = words[6:]
                        
                        chunk_text = ' '.join(chunk_words)
                        buffer = ' '.join(remaining_words)
                        
                        if chunk_text.strip():
                            self._speak_chunk_sync(chunk_text)
                            word_count = len(remaining_words)
                            last_speech_time = time_module.time()  # Actualizar tiempo
                
                # NUEVO: Forzar reproducción si ha pasado mucho tiempo sin hablar (3 segundos)
                current_time = time_module.time()
                if buffer.strip() and (current_time - last_speech_time) > 3.0:
                    self._speak_chunk_sync(buffer.strip())
                    buffer = ""
                    word_count = 0
                    last_speech_time = current_time
                
            except queue.Empty:
                # Continuar si no hay nuevos chunks, pero verificar si debemos finalizar
                if not self.is_running:
                    break
                # También verificar timeout por tiempo cuando no hay nuevos chunks
                current_time = time_module.time()
                if buffer.strip() and (current_time - last_speech_time) > 2.0:
                    self._speak_chunk_sync(buffer.strip())
                    buffer = ""
                    word_count = 0
                    last_speech_time = current_time
                continue
            except Exception as e:
                print(f"❌ Error en TTS worker: {e}")
                break
        
        # CRUCIAL: Reproducir TODO el buffer restante al finalizar
        if buffer.strip():
            self._speak_chunk_sync(buffer.strip())
    
    def _speak_chunk_sync(self, text):
        """
        Reproduce un fragmento de texto de forma secuencial (sin paralelo)
        """
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
            print("✅ Sintetizador de voz (gTTS + Pygame) iniciado")
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
            
            # Generar audio con gTTS
            print(f"🗣️ Diciendo: {text_to_speak}")
            tts = gTTS(text=text_to_speak, lang=lang, slow=slow)
            tts.save(audio_file)
            
            # Reproducir audio con pygame
            mixer.music.load(audio_file)
            mixer.music.play()
            
            # Esperar a que termine la reproducción de forma más eficiente
            timeout = 30  # 30 segundos máximo
            start_time = time_module.time()
            while mixer.music.get_busy():
                if time_module.time() - start_time > timeout:
                    break
                time_module.sleep(0.01)  # Reducido el sleep
            
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
        
        if not text_chunk or text_chunk.isspace():
            return False

        try:
            # Generar nombre único para evitar conflictos
            self.audio_counter += 1
            audio_file = os.path.join(self.temp_dir, f"seq_chunk_{self.audio_counter}.mp3")
            self.temp_files.append(audio_file)
            
            # Generar audio
            tts = gTTS(text=text_chunk, lang=lang, slow=False)
            tts.save(audio_file)
            
            # Esperar a que termine la reproducción anterior de forma más eficiente
            timeout = 10  # 10 segundos máximo para esperar
            start_time = time_module.time()
            while mixer.music.get_busy():
                if time_module.time() - start_time > timeout:
                    mixer.music.stop()  # Forzar parada si tarda mucho
                    break
                time_module.sleep(0.01)  # Sleep muy corto para evitar delays
            
            # Cargar y reproducir
            mixer.music.load(audio_file)
            mixer.music.play()
            
            # Esperar a que termine la reproducción actual
            start_time = time_module.time()
            timeout = 30  # 30 segundos máximo para la reproducción
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
    
    def speak_async(self, text_to_speak, lang='es', slow=False):
        """
        Reproduce texto sin bloquear la ejecución
        
        Args:
            text_to_speak (str): Texto a convertir en voz
            lang (str): Idioma para la síntesis
            slow (bool): Si True, habla más lentamente
            
        Returns:
            bool: True si inicia la reproducción correctamente
        """
        if not self.initialized:
            print("❌ El sintetizador no está inicializado")
            return False
        
        if not text_to_speak or text_to_speak.isspace():
            return False

        def _async_speak():
            try:
                # Crear archivo de audio temporal
                audio_file = os.path.join(self.temp_dir, f"response_async_{self.audio_counter}.mp3")
                self.audio_counter += 1
                self.temp_files.append(audio_file)
                
                # Generar audio con gTTS
                print(f"🗣️ Diciendo: {text_to_speak}")
                tts = gTTS(text=text_to_speak, lang=lang, slow=slow)
                tts.save(audio_file)
                
                # Reproducir audio sin bloquear
                mixer.music.load(audio_file)
                mixer.music.play()
                
                # Esperar y limpiar en el hilo asíncrono
                start_time = time_module.time()
                while mixer.music.get_busy():
                    if time_module.time() - start_time > 30:
                        break
                    time_module.sleep(0.01)
                
                self._safe_cleanup_file(audio_file)
                
            except Exception as e:
                print(f"❌ Error en voz asíncrona: {e}")
        
        # Ejecutar en hilo separado
        threading.Thread(target=_async_speak, daemon=True).start()
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
        test_text = "Hola, soy Aura. El sintetizador de voz está funcionando correctamente."
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
    
    Args:
        text (str): Texto a sintetizar
        lang (str): Idioma
        slow (bool): Velocidad lenta
        
    Returns:
        bool: True si inicia la reproducción
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