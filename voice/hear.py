#!/usr/bin/env python3
"""
Módulo de reconocimiento de voz (Speech to Text)
Utiliza Vosk para convertir audio a texto en español
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
MODEL_PATH = os.path.join(SCRIPT_DIR, "vosk-model-es-0.42")
SAMPLE_RATE = 16000
DEVICE = None
BLOCKSIZE = 8000
q = queue.Queue()

def _audio_callback(indata, frames, time, status):
    """Callback para captura de audio"""
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def initialize_recognizer():
    """
    Inicializa el reconocedor de voz Vosk
    
    Returns:
        KaldiRecognizer: Objeto reconocedor inicializado o None si hay error
    """
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: La carpeta del modelo Vosk no se encuentra en '{MODEL_PATH}'")
        return None
    
    try:
        model = Model(MODEL_PATH)
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        print("✅ Motor de reconocimiento de voz (Vosk) iniciado")
        return recognizer
    except Exception as e:
        print(f"❌ Error al cargar el modelo Vosk: {e}")
        return None

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