#!/usr/bin/env python3
"""
Ejemplo de uso de MCPs (Model Context Protocol) con Aura

Este script demuestra cómo:
1. Configurar servidores MCP
2. Usar herramientas de filesystem
3. Crear configuraciones personalizadas
"""

import os
import asyncio
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from client import GeminiClient

async def test_filesystem_mcp():
    """Probar el servidor MCP de filesystem"""
    print("🧪 === PRUEBA DE FILESYSTEM MCP ===\n")
    
    # Crear cliente
    client = GeminiClient()
    
    # Configurar MCP con filesystem
    home_dir = os.path.expanduser("~")
    mcp_config = {
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                home_dir,           # Directorio home
                f"{home_dir}/Documents",  # Documentos
                f"{home_dir}/Desktop",    # Escritorio
            ],
            "transport": "stdio"
        }
    }
    
    # Intentar configurar MCP
    success = await client.setup_mcp_servers(mcp_config)
    
    if not success:
        print("❌ No se pudo configurar MCP. Verifica que Node.js esté instalado:")
        print("   sudo apt update && sudo apt install nodejs npm")
        print("   # o")
        print("   brew install node")
        return
    
    print(f"✅ MCP configurado. Herramientas disponibles: {len(client.mcp_tools)}")
    
    # Ejemplos de comandos para probar
    test_commands = [
        "Lista los archivos en mi escritorio",
        "¿Qué archivos hay en mi directorio Documents?",
        "Crea un archivo llamado 'test_mcp.txt' en mi escritorio con el contenido 'Hola desde MCP!'",
        "Lee el contenido del archivo test_mcp.txt en mi escritorio",
        "Busca archivos que contengan la palabra 'test' en el nombre",
    ]
    
    print("\n🎯 Comandos de ejemplo que puedes probar:")
    for i, cmd in enumerate(test_commands, 1):
        print(f"   {i}. {cmd}")
    
    print("\n💬 Prueba interactiva:")
    while True:
        try:
            user_input = input("\n👤 Comando: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'salir']:
                break
            
            if not user_input:
                continue
            
            print("🤖 Respuesta: ", end="", flush=True)
            response = await client.chat_with_voice(user_input)
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

async def test_custom_mcp_config():
    """Ejemplo de configuración MCP personalizada"""
    print("🔧 === CONFIGURACIÓN MCP PERSONALIZADA ===\n")
    
    # Configuración para múltiples servidores MCP
    custom_config = {
        "filesystem": {
            "command": "npx",
            "args": [
                "-y", 
                "@modelcontextprotocol/server-filesystem",
                "/tmp",  # Solo acceso a /tmp por seguridad
            ],
            "transport": "stdio"
        },
        # Puedes agregar más servidores aquí
        # "weather": {
        #     "command": "python",
        #     "args": ["path/to/weather_server.py"],
        #     "transport": "stdio"
        # }
    }
    
    client = GeminiClient()
    success = await client.setup_mcp_servers(custom_config)
    
    if success:
        print("✅ Configuración personalizada exitosa")
        print(f"🔧 {len(client.mcp_tools)} herramientas cargadas")
    else:
        print("❌ Error en configuración personalizada")

def show_mcp_info():
    """Mostrar información sobre MCPs"""
    print("📚 === INFORMACIÓN SOBRE MCP ===\n")
    
    print("🔍 ¿Qué es MCP?")
    print("   Model Context Protocol es un protocolo abierto que permite")
    print("   a las aplicaciones LLM conectarse con fuentes de datos externas")
    print("   y herramientas de manera estandarizada.\n")
    
    print("🛠️  Herramientas disponibles en Filesystem MCP:")
    print("   • read_file - Leer contenido de archivos")
    print("   • write_file - Escribir/crear archivos")
    print("   • list_directory - Listar contenido de directorios")
    print("   • search_files - Buscar archivos por nombre")
    print("   • get_file_info - Obtener metadatos de archivos")
    print("   • create_directory - Crear directorios")
    print("   • move_file - Mover/renombrar archivos")
    print("   • edit_file - Editar archivos existentes\n")
    
    print("📋 Requisitos:")
    print("   • Node.js y npm instalados")
    print("   • Paquete @modelcontextprotocol/server-filesystem")
    print("   • langchain-mcp-adapters en Python\n")
    
    print("🔒 Seguridad:")
    print("   • MCPs solo pueden acceder a directorios especificados")
    print("   • Validación de rutas para prevenir ataques")
    print("   • Sandboxing por diseño\n")

async def main():
    """Función principal del ejemplo"""
    print("🌟 === EJEMPLOS DE MCP CON AURA ===\n")
    
    while True:
        print("Selecciona una opción:")
        print("1. Probar Filesystem MCP")
        print("2. Configuración MCP personalizada")
        print("3. Información sobre MCP")
        print("4. Salir")
        
        choice = input("\nOpción (1-4): ").strip()
        
        if choice == "1":
            await test_filesystem_mcp()
        elif choice == "2":
            await test_custom_mcp_config()
        elif choice == "3":
            show_mcp_info()
        elif choice == "4":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida")
        
        input("\nPresiona Enter para continuar...")
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Programa terminado!")
    except Exception as e:
        print(f"❌ Error: {e}") 