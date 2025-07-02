#!/usr/bin/env python3
"""
Punto de entrada principal para AuraGemini
Cliente de Google Gemini con funcionalidades de voz integradas usando LangChain
"""

import sys
from client import GeminiClient

def main():
    """
    Función principal del script
    """
    # Permitir configurar el contexto desde argumentos
    context_size = 100000  # Contexto para Gemini
    
    # Verificar si se debe deshabilitar la voz
    disable_voice = '--no-voice' in sys.argv
    if disable_voice:
        sys.argv.remove('--no-voice')
    
    client = GeminiClient(context_size=context_size, enable_voice=not disable_voice)
    
    # Verificar si el modelo está disponible
    if not client.is_server_running():
        print("❌ Error: El modelo Gemini no se pudo inicializar")
        print("💡 Verifica tu API key de Google")
        sys.exit(1)
    
    print("✅ Conectado a Google Gemini mediante LangChain")
    
    # Listar modelos disponibles
    models = client.list_models()
    if models:
        print(f"📋 Modelo activo: {', '.join(models)}")
    
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