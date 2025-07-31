#!/usr/bin/env python3
"""
Módulo de reconocimiento de voz (Speech to Text)
Utiliza Vosk para converter audio a texto en español e inglés
Soporte para cambio dinámico de idioma
"""

import queue
import sys
import os
import sounddevice as sd
import json
from vosk import Model, KaldiRecognizer

# --- Configuración ---
# Obtener la ruta del directorio actual del script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Modelos disponibles
AVAILABLE_MODELS = {
    "es": "vosk-model-es-0.42",
    "en": "vosk-model-en-us-0.42-gigaspeech"
}

# Configuraciones por defecto
SAMPLE_RATE = 16000
DEVICE = None
BLOCKSIZE = 8000
q = queue.Queue()

# Variables globales para modelo y reconocedor actual
current_language = "es"
current_model = None
current_recognizer = None

def _audio_callback(indata, frames, time, status):
    """Callback para captura de audio"""
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def initialize_recognizer(language="es"):
    """
    Inicializa el reconocedor de voz Vosk con el idioma especificado
    
    Args:
        language (str): Código del idioma ('es' o 'en')
    
    Returns:
        KaldiRecognizer: Objeto reconocedor inicializado o None si hay error
    """
    global current_language, current_model, current_recognizer
    
    if language not in AVAILABLE_MODELS:
        print(f"❌ Error: Idioma '{language}' no soportado. Idiomas disponibles: {list(AVAILABLE_MODELS.keys())}")
        return None
    
    model_path = os.path.join(SCRIPT_DIR, AVAILABLE_MODELS[language])
    
    if not os.path.exists(model_path):
        print(f"❌ Error: La carpeta del modelo Vosk no se encuentra en '{model_path}'")
        # Intentar con el otro idioma
        for alt_lang, alt_model in AVAILABLE_MODELS.items():
            if alt_lang != language:
                alt_path = os.path.join(SCRIPT_DIR, alt_model)
                if os.path.exists(alt_path):
                    print(f"🔄 Intentando con modelo alternativo: {alt_lang}")
                    return initialize_recognizer(alt_lang)
        return None
    
    try:
        # Si ya tenemos un modelo cargado para este idioma, reutilizarlo
        if current_language == language and current_model and current_recognizer:
            print(f"✅ Reutilizando modelo de {language}")
            return current_recognizer
        
        print(f"🔄 Cargando modelo de reconocimiento para {language}...")
        model = Model(model_path)
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        
        # Actualizar variables globales
        current_language = language
        current_model = model
        current_recognizer = recognizer
        
        print(f"✅ Motor de reconocimiento de voz (Vosk-{language.upper()}) iniciado")
        return recognizer
    except Exception as e:
        print(f"❌ Error al cargar el modelo Vosk para {language}: {e}")
        return None

def change_language(language):
    """
    Cambia el idioma del reconocimiento de voz
    
    Args:
        language (str): Código del idioma ('es' o 'en')
    
    Returns:
        KaldiRecognizer: Nuevo reconocedor o None si hay error
    """
    print(f"🌍 Cambiando idioma de reconocimiento a: {language}")
    return initialize_recognizer(language)

def get_current_language():
    """
    Obtiene el idioma actual del reconocimiento
    
    Returns:
        str: Código del idioma actual
    """
    return current_language

def get_available_languages():
    """
    Obtiene la lista de idiomas disponibles
    
    Returns:
        list: Lista de códigos de idioma disponibles
    """
    return list(AVAILABLE_MODELS.keys())

def listen_for_command(recognizer, timeout=5):
    """
    Escucha audio del micrófono y lo convierte a texto
    
    Args:
        recognizer: Objeto KaldiRecognizer inicializado
        timeout (int): Tiempo límite de escucha en segundos
        
    Returns:
        str: Texto reconocido del audio
    """
    # Limpiar la cola de audio
    with q.mutex:
        q.queue.clear()

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, device=DEVICE,
                           dtype="int16", channels=1, callback=_audio_callback):
        
        print("🎤 Escuchando... (Habla ahora)")
        recognized_text = ""
        
        while True:
            try:
                data = q.get(timeout=timeout)
                if recognizer.AcceptWaveform(data):
                    result_json = json.loads(recognizer.Result())
                    text = result_json.get("text", "")
                    if text:
                        recognized_text = text
                        break
            except queue.Empty:
                print("⏰ Tiempo de escucha agotado")
                break
    
    # Obtener resultado final
    final_result_json = json.loads(recognizer.FinalResult())
    final_text = final_result_json.get("text", "")
    
    if final_text:
        recognized_text = final_text

    if recognized_text:
        print(f"👂 Escuché: '{recognized_text}'")
    else:
        print("🔇 No se detectó voz clara")
    
    return recognized_text

def test_microphone():
    """
    Función de prueba para verificar que el micrófono funciona
    
    Returns:
        bool: True si el micrófono funciona correctamente
    """
    try:
        recognizer = initialize_recognizer()
        if not recognizer:
            return False
        
        print("🧪 Probando micrófono...")
        result = listen_for_command(recognizer, timeout=3)
        return len(result) > 0
        
    except Exception as e:
        print(f"❌ Error en prueba de micrófono: {e}")
        return False

if __name__ == "__main__":
    # Prueba del módulo
    print("🎤 Prueba del reconocimiento de voz")
    recognizer = initialize_recognizer()
    
    if recognizer:
        while True:
            text = listen_for_command(recognizer)
            if text.lower() in ['salir', 'exit', 'terminar']:
                break
            print(f"Reconocido: {text}")
    else:
        print("❌ No se pudo inicializar el reconocedor") 