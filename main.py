#!/usr/bin/env python3
"""
Punto de entrada principal para AuraOllama
Cliente de Ollama con funcionalidades de voz integradas
"""

import sys
from client import OllamaClient

def main():
    """
    Función principal del script
    """
    # Permitir configurar el contexto desde argumentos
    context_size = 130000  # Máximo para gemma3:4b
    
    # Verificar si se debe deshabilitar la voz
    disable_voice = '--no-voice' in sys.argv
    if disable_voice:
        sys.argv.remove('--no-voice')
    
    client = OllamaClient(context_size=context_size, enable_voice=not disable_voice)
    
    # Verificar si el servidor está ejecutándose
    if not client.is_server_running():
        print("❌ Error: El servidor de Ollama no está ejecutándose")
        print("💡 Asegúrate de que Ollama esté iniciado con: ollama serve")
        sys.exit(1)
    
    print("✅ Conectado al servidor de Ollama")
    
    # Listar modelos disponibles
    models = client.list_models()
    if models:
        print(f"📋 Modelos disponibles: {', '.join(models)}")
    
    # Verificar si el modelo está disponible
    if client.model not in models:
        print(f"⚠️  Advertencia: El modelo '{client.model}' no se encuentra en la lista")
        print(f"💡 Puedes descargarlo con: ollama pull {client.model}")
    
    # Mostrar información de contexto
    client.show_context_info()
    
    # Modo de uso
    if len(sys.argv) > 1:
        # Modo prompt único con streaming por defecto
        prompt = " ".join(sys.argv[1:])
        print(f"🤖 Respuesta para: '{prompt}'")
        print("🎬 Streaming activado:")
        client.generate_response(prompt, stream=True)
    else:
        # Modo chat interactivo
        client.chat()

if __name__ == "__main__":
    main() 