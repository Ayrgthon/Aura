#!/usr/bin/env python3
"""
Configuración de servidores MCP
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Cargar variables de entorno del .env
load_dotenv()


def get_mcp_servers_config() -> Dict[str, Dict[str, Any]]:
    """
    Retorna configuración de todos los servidores MCP disponibles
    
    Returns:
        Diccionario con configuraciones de servidores MCP
    """
    # Obtener el directorio base del proyecto (padre de client/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)  # Un nivel arriba desde client/
    mcp_dir = os.path.join(project_dir, "mcp")
    
    config = {}
    
    # Serpapi MCP (servidor local personalizado)
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_api_key:
        config["serpapi"] = {
            "command": "node",
            "args": [os.path.join(mcp_dir, "serpapi_server.js")],
            "env": {"SERPAPI_API_KEY": serpapi_api_key}
        }
    
    # Obsidian Memory MCP (servidor personalizado local)
    obsidian_vault = os.getenv("OBSIDIAN_VAULT_PATH", "/home/ary/Documents/Ary Vault")
    if os.path.exists(obsidian_vault):
        config["obsidian-memory"] = {
            "command": "node",
            "args": [os.path.join(mcp_dir, "obsidian_memory_server.js")],
            "env": {"OBSIDIAN_VAULT_PATH": obsidian_vault}
        }
    
    # Personal Assistant MCP (servidor personalizado local para tareas diarias)
    daily_path = os.getenv("DAILY_PATH", "/home/ary/Documents/Ary Vault/Daily")
    if os.path.exists(daily_path):
        config["personal-assistant"] = {
            "command": "node",
            "args": [os.path.join(mcp_dir, "personal_assistant_server.js")],
            "env": {"DAILY_PATH": daily_path}
        }
    
    # Sequential Thinking MCP (servidor oficial de Anthropic)
    config["sequential-thinking"] = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
    
    
    return config


def print_server_status(config: Dict[str, Dict[str, Any]]):
    """
    Imprime el estado de los servidores configurados
    
    Args:
        config: Configuración de servidores
    """
    print("\n📋 SERVIDORES MCP CONFIGURADOS:")
    print("-" * 50)
    
    for server_name, server_config in config.items():
        print(f"• {server_name}")
        print(f"  Comando: {server_config['command']} {' '.join(server_config.get('args', []))}")
        if server_config.get('env'):
            env_vars = list(server_config['env'].keys())
            print(f"  Variables: {', '.join(env_vars)}")
        print()
    
    print(f"Total: {len(config)} servidores configurados")
    print("-" * 50)