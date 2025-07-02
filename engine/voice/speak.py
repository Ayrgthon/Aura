#!/usr/bin/env python3
"""
Módulo de síntesis de voz (Text to Speech)
Utiliza gTTS y pygame para convertir texto a voz en español
"""

import os
import tempfile
import threading
import queue
import time as time_module
from gtts import gTTS
from pygame import mixer, time

class StreamingTTS:
    def __init__(self):
        """
        Clase para TTS en streaming paralelo
        """
        self.text_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.synthesizer = None
        
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
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
        self.is_running = False
    
    def _tts_worker(self):
        """
        Worker que procesa la cola de texto y reproduce audio
        """
        buffer = ""
        sentence_endings = ['.', '!', '?', '\n']
        
        while self.is_running:
            try:
                text_chunk = self.text_queue.get(timeout=1)
                
                if text_chunk is None:  # Señal de fin
                    # Reproducir texto restante en buffer
                    if buffer.strip():
                        self._speak_chunk(buffer)
                    break
                
                buffer += text_chunk
                
                # Buscar final de oración para reproducir
                for ending in sentence_endings:
                    if ending in buffer:
                        parts = buffer.split(ending, 1)
                        sentence = parts[0] + ending
                        buffer = parts[1] if len(parts) > 1 else ""
                        
                        if sentence.strip():
                            self._speak_chunk(sentence.strip())
                        break
                
                # Si el buffer es muy largo, reproducir por fragmentos
                if len(buffer) > 100:
                    # Buscar espacio para cortar
                    last_space = buffer.rfind(' ', 0, 80)
                    if last_space > 20:
                        chunk = buffer[:last_space]
                        buffer = buffer[last_space:].lstrip()
                        self._speak_chunk(chunk)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error en TTS worker: {e}")
                break  # Salir del loop en caso de error
    
    def _speak_chunk(self, text):
        """
        Reproduce un fragmento de texto
        """
        if self.synthesizer and text.strip():
            self.synthesizer.speak_chunk_async(text)

class VoiceSynthesizer:
    def __init__(self):
        """
        Inicializa el sintetizador de voz
        """
        self.initialized = False
        self.temp_dir = tempfile.gettempdir()
        self.audio_counter = 0
        self.initialize()
    
    def initialize(self):
        """
        Inicializa el mixer de pygame para reproducción de audio
        
        Returns:
            bool: True si se inicializa correctamente
        """
        try:
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
            audio_file = os.path.join(self.temp_dir, "response.mp3")
            
            # Generar audio con gTTS
            print(f"🗣️ Diciendo: {text_to_speak}")
            tts = gTTS(text=text_to_speak, lang=lang, slow=slow)
            tts.save(audio_file)
            
            # Reproducir audio con pygame
            mixer.music.load(audio_file)
            mixer.music.play()
            
            # Esperar a que termine la reproducción
            while mixer.music.get_busy():
                time.Clock().tick(10)
            
            # Limpiar archivo temporal
            mixer.music.unload()
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            return True
            
        except Exception as e:
            print(f"❌ Error al sintetizar/reproducir voz: {e}")
            return False
    
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

        try:
            # Crear archivo de audio temporal
            audio_file = os.path.join(self.temp_dir, "response_async.mp3")
            
            # Generar audio con gTTS
            print(f"🗣️ Diciendo: {text_to_speak}")
            tts = gTTS(text=text_to_speak, lang=lang, slow=slow)
            tts.save(audio_file)
            
            # Reproducir audio sin bloquear
            mixer.music.load(audio_file)
            mixer.music.play()
            
            return True
            
        except Exception as e:
            print(f"❌ Error al sintetizar voz asíncrona: {e}")
            return False
    
    def speak_chunk_async(self, text_chunk, lang='es'):
        """
        Reproduce un fragmento de texto de forma asíncrona para streaming
        
        Args:
            text_chunk (str): Fragmento de texto a reproducir
            lang (str): Idioma para la síntesis
        """
        def _async_speak():
            try:
                # Generar nombre único para evitar conflictos
                self.audio_counter += 1
                audio_file = os.path.join(self.temp_dir, f"chunk_{self.audio_counter}.mp3")
                
                # Generar audio
                tts = gTTS(text=text_chunk, lang=lang, slow=False)
                tts.save(audio_file)
                
                # Esperar a que termine la reproducción anterior si es necesario
                while mixer.music.get_busy():
                    time_module.sleep(0.1)
                
                # Cargar y reproducir
                mixer.music.load(audio_file)
                mixer.music.play()
                
                # Esperar a que termine y limpiar
                while mixer.music.get_busy():
                    time_module.sleep(0.1)
                
                mixer.music.unload()
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    
            except Exception as e:
                print(f"❌ Error en chunk async: {e}")
        
        # Ejecutar en hilo separado
        threading.Thread(target=_async_speak, daemon=True).start()
    
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
            mixer.music.stop()
            mixer.quit()
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