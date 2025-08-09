#!/usr/bin/env python3
"""
Cliente Aura Simple - Nueva implementación
Sistema directo LLM + MCPs con múltiples function calls
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from gemini_client import SimpleGeminiClient
from config import get_mcp_servers_config, print_server_status


def print_welcome():
    """Mostrar mensaje de bienvenida"""
    print("=" * 60)
    print("🌟 AURA - Cliente Simple (Nueva Implementación)")
    print("=" * 60)
    print("💬 Chat directo con Gemini + MCPs")
    print("🔧 Múltiples function calls en una sola petición")
    print("📝 Escribe 'quit', 'exit' o 'salir' para salir")
    print("🔄 Escribe 'clear' para limpiar historial")
    print("🛠️  Escribe 'tools' para ver herramientas disponibles")
    print("=" * 60)
    print()


def print_available_tools(client: SimpleGeminiClient):
    """Mostrar herramientas disponibles"""
    tools = client.get_available_tools()
    if tools:
        print(f"🛠️  HERRAMIENTAS DISPONIBLES ({len(tools)}):")
        print("-" * 40)
        for tool in tools:
            print(f"  • {tool}")
        print("-" * 40)
        print()
    else:
        print("⚠️ No hay herramientas MCP disponibles")
        print()


async def main():
    """Función principal"""
    print_welcome()
    
    try:
        # Inicializar cliente Gemini
        print("🚀 Inicializando cliente Gemini...")
        client = SimpleGeminiClient(model_name="gemini-2.5-pro", debug=True)
        
        # Configurar servidores MCP
        print("\n🔧 Configurando servidores MCP...")
        mcp_config = get_mcp_servers_config()
        print_server_status(mcp_config)
        
        # Conectar a servidores MCP
        success = await client.setup_mcp_servers(mcp_config)
        if success:
            print("✅ Servidores MCP configurados exitosamente")
            print_available_tools(client)
        else:
            print("⚠️ Algunos servidores MCP fallaron, continuando...")
        
        print("🎯 CLIENTE LISTO - ¡Empezá a chatear!")
        print("=" * 60)
        print()
        
        # Bucle principal del chat
        while True:
            try:
                # Leer input del usuario
                user_input = input("👤 Tú: ").strip()
                
                # Comandos especiales
                if user_input.lower() in ['quit', 'exit', 'salir']:
                    print("\n👋 ¡Hasta luego!")
                    break
                
                if user_input.lower() == 'tools':
                    print_available_tools(client)
                    continue
                
                if user_input.lower() == 'clear':
                    client.clear_history()
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print_welcome()
                    print_available_tools(client)
                    continue
                
                if not user_input:
                    continue
                
                print("\n🤖 Aura está procesando...")
                print("-" * 40)
                
                # Procesar mensaje
                response = await client.chat(user_input)
                
                print("-" * 40)
                print(f"🤖 Aura: {response}")
                print("=" * 60)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrumpido. ¡Hasta luego!")
                break
            except EOFError:
                print("\n\n👋 Chat terminado. ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error en el chat: {e}")
                print("Continuando...")
                print()
    
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        return 1
    
    finally:
        # Cleanup
        if 'client' in locals():
            try:
                await client.cleanup()
            except Exception as e:
                print(f"⚠️ Error durante cleanup: {e}")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
        sys.exit(0)