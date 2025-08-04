#!/usr/bin/env python3
"""
Aura - Main Simplificado
Launcher minimalista para el cliente simple
"""

import os
import asyncio
from client import SimpleAuraClient


def get_mcp_config():
    """Configuración simple de MCP con Brave Search y Obsidian"""
    config = {}
    
    # Brave Search MCP
    brave_api_key = os.getenv("BRAVE_API_KEY")
    if brave_api_key:
        config["brave-search"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "transport": "stdio",
            "env": {"BRAVE_API_KEY": brave_api_key}
        }
        print("🔍 Brave Search MCP configurado")
    
    # Obsidian Memory MCP (servidor personalizado local)
    obsidian_vault = os.getenv("OBSIDIAN_VAULT_PATH", "/home/ary/Documents/Ary Vault")
    if os.path.exists(obsidian_vault):
        config["obsidian-memory"] = {
            "command": "node",
            "args": ["mcp/obsidian_memory_server.js"],
            "transport": "stdio",
            "env": {"OBSIDIAN_VAULT_PATH": obsidian_vault}
        }
        print(f"🗃️ Obsidian Memory MCP configurado: {obsidian_vault}")
    
    return config


async def main():
    """Función principal simplificada"""
    print("🌟 AURA - Cliente Simplificado")
    print("=" * 40)
    
    # Crear cliente
    try:
        client = SimpleAuraClient()
    except Exception as e:
        print(f"❌ Error inicializando cliente: {e}")
        return 1
    
    # Configurar MCP
    mcp_config = get_mcp_config()
    if mcp_config:
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