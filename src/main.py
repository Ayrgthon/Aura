#!/usr/bin/env python3
"""
Aura - Main Simplificado
Launcher minimalista para el cliente simple
"""

import os
import sys
import time
import json
import asyncio
from client import SimpleAuraClient

# Add voice directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice'))
from hear import SpeechToText
from speak import TextToSpeech


def get_model_choice():
    """Menú para seleccionar modelo Gemini"""
    models = {
        "1": "gemini-2.5-pro",
        "2": "gemini-2.5-flash", 
        "3": "gemini-2.5-flash-lite",
        "4": "gemini-2.0-flash",
        "5": "gemini-2.0-flash-lite"
    }
    
    print("🤖 Selecciona el modelo Gemini:")
    print("1. gemini-2.5-pro")
    print("2. gemini-2.5-flash")
    print("3. gemini-2.5-flash-lite") 
    print("4. gemini-2.0-flash")
    print("5. gemini-2.0-flash-lite")
    
    while True:
        choice = input("\n👉 Elige (1-5): ").strip()
        if choice in models:
            selected_model = models[choice]
            print(f"✅ Modelo seleccionado: {selected_model}")
            return selected_model
        else:
            print("❌ Opción inválida. Elige entre 1-5.")


def get_language_choice():
    """Menú para seleccionar idioma de voz"""
    print("🗣️ Selecciona el idioma de voz:")
    print("1. Español (Emma TTS + Modelo ES STT)")
    print("2. English (Andrew TTS + Modelo EN STT)")
    
    while True:
        choice = input("\n👉 Elige (1-2): ").strip()
        if choice == "1":
            print("✅ Idioma seleccionado: Español")
            return "es"
        elif choice == "2":
            print("✅ Idioma seleccionado: English")
            return "en"
        else:
            print("❌ Opción inválida. Elige entre 1-2.")

def get_debug_mode():
    """Menú para seleccionar modo de debug"""
    print("🔧 Selecciona el modo de funcionamiento:")
    print("1. Modo Debug (con logs detallados)")
    print("2. Modo Producción (sin logs innecesarios)")
    
    while True:
        choice = input("\n👉 Elige (1-2): ").strip()
        if choice == "1":
            print("✅ Modo Debug activado")
            return True
        elif choice == "2":
            print("✅ Modo Producción activado")
            return False
        else:
            print("❌ Opción inválida. Elige entre 1-2.")


def get_mcp_config(debug_mode: bool = False):
    """Configuración simple de MCP con Serpapi y Obsidian"""
    config = {}
    
    # Serpapi MCP (servidor local personalizado)
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_api_key:
        config["serpapi"] = {
            "command": "node",
            "args": ["mcp/serpapi_server.js"],
            "transport": "stdio",
            "env": {"SERPAPI_API_KEY": serpapi_api_key}
        }
        if debug_mode:
            print("🔍 Serpapi MCP configurado")
    
    # Obsidian Memory MCP (servidor personalizado local)
    obsidian_vault = os.getenv("OBSIDIAN_VAULT_PATH", "/home/ary/Documents/Ary Vault")
    if os.path.exists(obsidian_vault):
        config["obsidian-memory"] = {
            "command": "node",
            "args": ["mcp/obsidian_memory_server.js"],
            "transport": "stdio",
            "env": {"OBSIDIAN_VAULT_PATH": obsidian_vault}
        }
        if debug_mode:
            print(f"🗃️ Obsidian Memory MCP configurado: {obsidian_vault}")
    
    # Personal Assistant MCP (servidor personalizado local para tareas diarias)
    daily_path = os.getenv("DAILY_PATH", "/home/ary/Documents/Ary Vault/Daily")
    if os.path.exists(daily_path):
        config["personal-assistant"] = {
            "command": "node",
            "args": ["mcp/personal_assistant_server.js"],
            "transport": "stdio",
            "env": {"DAILY_PATH": daily_path}
        }
        if debug_mode:
            print(f"📋 Personal Assistant MCP configurado: {daily_path}")
    
    return config


async def main():
    """Función principal simplificada"""
    print("🌟 AURA - Cliente Simplificado con Voz")
    print("=" * 45)
    
    # Seleccionar idioma de voz
    voice_language = get_language_choice()
    print()
    
    # Seleccionar modo debug
    debug_mode = get_debug_mode()
    print()
    
    # Seleccionar modelo
    selected_model = get_model_choice()
    
    # Crear cliente con modelo seleccionado y modo debug
    try:
        client = SimpleAuraClient(model_name=selected_model, debug_mode=debug_mode)
    except Exception as e:
        print(f"❌ Error inicializando cliente: {e}")
        return 1
    
    # Inicializar sistema de voz
    try:
        print("\n🎤 Inicializando sistema de voz...")
        stt = SpeechToText(language=voice_language)
        
        # Configurar TTS según el idioma
        if voice_language == "es":
            tts = TextToSpeech(voice="en-US-EmmaMultilingualNeural")  # Emma para español
            print("✅ Emma configurada para español")
        else:
            tts = TextToSpeech(voice="en-US-AndrewMultilingualNeural")  # Andrew para inglés
            print("✅ Andrew configurado para inglés")
            
        print("✅ Sistema de voz inicializado correctamente")
    except Exception as e:
        print(f"❌ Error inicializando sistema de voz: {e}")
        print("⚠️ Continuando sin voz...")
        stt = None
        tts = None
    
    # Configurar MCP
    mcp_config = get_mcp_config(debug_mode)
    if mcp_config:
        if debug_mode:
            print("🔧 Configurando MCP...")
        await client.setup_mcp(mcp_config)
    
    # Loop interactivo con voz
    if stt:
        print("\n🎤 Chat con voz iniciado")
        print("🗣️ Habla para interactuar (di 'salir' para terminar, 'limpiar' para resetear)")
        print("🔁 Si no te escucho, te pediré que repitas")
        stt.start_listening()
    else:
        print("\n💬 Chat iniciado (escribe 'salir' para terminar, 'limpiar' para resetear)")
    print("-" * 60)
    
    try:
        while True:
            user_input = ""
            
            # Intentar STT primero si está disponible
            if stt:
                print("\n🎤 Escuchando... (habla ahora)")
                
                # Usar el método continuous para obtener resultado completo
                user_input = ""
                
                # Escuchar hasta obtener resultado final
                start_time = time.time()
                timeout = 10  # 10 segundos
                last_partial = ""
                
                while time.time() - start_time < timeout:
                    data = stt.stream.read(4000, exception_on_overflow=False)
                    if len(data) == 0:
                        continue
                        
                    if stt.rec.AcceptWaveform(data):
                        # Solo usar resultado FINAL, no parcial
                        result = json.loads(stt.rec.Result())
                        user_input = result.get('text', '').strip()
                        if user_input:
                            print(f"\n🗣️ Escuchado: {user_input}")
                            break
                    else:
                        # Mostrar partial para feedback pero NO enviarlo
                        partial_result = json.loads(stt.rec.PartialResult())
                        partial_text = partial_result.get('partial', '')
                        if partial_text and partial_text != last_partial:
                            print(f"🎯 Hablando: {partial_text}", end='\r')
                            last_partial = partial_text
                
                # Si no se detectó nada, pedir repetir por voz
                if not user_input:
                    print("\n🤷 No se detectó voz clara")
                    if tts:
                        sorry_msg = "Lo siento, ¿podrías repetir lo que dijiste? No pude escucharte bien." if voice_language == "es" else "Sorry, could you repeat what you said? I couldn't hear you well."
                        print("🔊 Aura: Lo siento, ¿podrías repetir?")
                        tts.speak(sorry_msg)
                    continue  # Volver al inicio del loop para escuchar de nuevo
            else:
                user_input = input("\n👤 Tú: ").strip()
            
            # Procesar comandos especiales
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("👋 ¡Hasta luego!")
                if tts:
                    farewell = "¡Hasta luego!" if voice_language == "es" else "Goodbye!"
                    tts.speak(farewell)
                break
            
            if user_input.lower() in ['limpiar', 'clear']:
                client.clear_history()
                print("🧹 Historial limpiado")
                if tts:
                    clear_msg = "Historial limpiado" if voice_language == "es" else "History cleared"
                    tts.speak(clear_msg)
                continue
            
            if not user_input:
                continue
            
            # Pausar STT mientras procesamos y hablamos
            if stt:
                stt.stop_listening()
            
            # Obtener respuesta de Aura
            print("🤖 Aura: ", end="", flush=True)
            response = await client.chat(user_input)
            print(response)
            
            # Hablar la respuesta si TTS está disponible
            if tts and response:
                print("🔊 Aura hablando...")
                tts.speak(response)
            
            # Reanudar STT para la siguiente entrada
            if stt:
                stt.start_listening()
    
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    
    finally:
        # Cleanup
        if stt:
            stt.close()
        if tts:
            tts.close()
        await client.cleanup()
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))