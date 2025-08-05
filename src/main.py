#!/usr/bin/env python3
"""
Aura - Main Simplificado
Launcher minimalista para el cliente simple
"""

import os
import asyncio
from client import SimpleAuraClient


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
    print("🌟 AURA - Cliente Simplificado")
    print("=" * 40)
    
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
    
    # Configurar MCP
    mcp_config = get_mcp_config(debug_mode)
    if mcp_config:
        if debug_mode:
            print("🔧 Configurando MCP...")
        await client.setup_mcp(mcp_config)
    
    # Loop interactivo
    print("\n💬 Chat iniciado (escribe 'salir' para terminar, 'limpiar' para resetear)")
    print("-" * 50)
    
    try:
        while True:
            user_input = input("\n👤 Tú: ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("👋 ¡Hasta luego!")
                break
            
            if user_input.lower() in ['limpiar', 'clear']:
                client.clear_history()
                continue
            
            if not user_input:
                continue
            
            print("🤖 Aura: ", end="", flush=True)
            response = await client.chat(user_input)
            print(response)
    
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    
    finally:
        await client.cleanup()
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))