#!/usr/bin/env python3
"""
Módulo de síntesis de voz (Text to Speech)
Utiliza gTTS y pygame para convertir texto a voz en español
"""

import os
import tempfile
from gtts import gTTS
from pygame import mixer, time

class VoiceSynthesizer:
    def __init__(self):
        """
        Inicializa el sintetizador de voz
        """
        self.initialized = False
        self.temp_dir = tempfile.gettempdir()
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

# Instancia global del sintetizador para facilitar el uso
_voice_synthesizer = None

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