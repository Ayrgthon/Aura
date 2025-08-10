#!/usr/bin/env python3
"""
Test del Cliente Aura - Modo Chatbot
Permite probar el agente autónomo antes de pasar a audio
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio client al path (ahora desde tests/ necesitamos subir un nivel)
client_dir = Path(__file__).parent.parent / "client"  # Subir un nivel más
sys.path.insert(0, str(client_dir))

from gemini_client import SimpleGeminiClient
from config import get_mcp_servers_config, print_server_status


def print_test_welcome():
    """Mostrar mensaje de bienvenida para testing"""
    print("=" * 70)
    print("🧪 AURA TEST - Cliente de Prueba")
    print("=" * 70)
    print("🎯 Modo: Chatbot para testing del agente autónomo")
    print("🔧 Herramientas: Obsidian, Google Workspace, Sequential Thinking, SerpAPI")
    print("📝 Comandos:")
    print("  • 'quit', 'exit' o 'salir' - Salir")
    print("  • 'tools' - Ver herramientas disponibles")
    print("  • 'clear' - Limpiar historial")
    print("  • 'test obsidian' - Probar funciones de Obsidian")
    print("  • 'test google' - Probar Google Workspace")
    print("=" * 70)
    print()


def print_test_suggestions():
    """Sugerir pruebas específicas"""
    suggestions = [
        "🔍 Pruebas sugeridas:",
        "  1. 'busca información sobre Claude AI' (SerpAPI + Sequential Thinking)",
        "  2. 'busca notas sobre proyectos en mi vault' (Obsidian)",
        "  3. 'muéstrame mis eventos de esta semana' (Google Workspace)",
        "  4. 'crea una nota nueva sobre testing' (Obsidian)",
        "  5. 'agenda una reunión para mañana' (Sequential + Google Workspace)",
        "",
        "🎯 El agente debe usar múltiples herramientas automáticamente"
    ]
    
    for suggestion in suggestions:
        print(suggestion)
    print()


async def test_client():
    """Función principal de testing"""
    print_test_welcome()
    
    try:
        # Inicializar cliente Gemini con debug activado
        print("🚀 Inicializando cliente de prueba...")
        client = SimpleGeminiClient(model_name="gemini-2.5-flash", debug=True)
        
        # Configurar servidores MCP
        print("\n🔧 Configurando servidores MCP...")
        mcp_config = get_mcp_servers_config()
        print_server_status(mcp_config)
        
        # Conectar a servidores MCP
        success = await client.setup_mcp_servers(mcp_config)
        
        if success:
            tools = client.get_available_tools()
            print(f"✅ Servidores MCP configurados - {len(tools)} herramientas disponibles")
            print(f"🛠️  Herramientas: {', '.join(tools)}")
        else:
            print("⚠️ Algunos servidores MCP fallaron, pero continuando...")
            tools = client.get_available_tools()
            print(f"🛠️  Herramientas disponibles: {', '.join(tools) if tools else 'Ninguna'}")
        
        print("\n🎯 CLIENTE DE PRUEBA LISTO")
        print_test_suggestions()
        print("=" * 70)
        print()
        
        # Bucle principal del chat de prueba
        while True:
            try:
                # Leer input del usuario
                user_input = input("👤 Tester: ").strip()
                
                # Comandos especiales
                if user_input.lower() in ['quit', 'exit', 'salir']:
                    print("\n👋 ¡Test finalizado!")
                    break
                
                if user_input.lower() == 'tools':
                    available_tools = client.get_available_tools()
                    if available_tools:
                        print(f"🛠️  HERRAMIENTAS DISPONIBLES ({len(available_tools)}):")
                        for i, tool in enumerate(available_tools, 1):
                            print(f"  {i}. {tool}")
                    else:
                        print("⚠️ No hay herramientas disponibles")
                    print()
                    continue
                
                if user_input.lower() == 'clear':
                    client.clear_history()
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print_test_welcome()
                    print_test_suggestions()
                    continue
                
                # Comandos de prueba específicos
                if user_input.lower() == 'test obsidian':
                    user_input = "Lista la estructura de mi vault de Obsidian y busca notas sobre proyectos"
                
                if user_input.lower() == 'test google':
                    user_input = "Muéstrame mis eventos de esta semana y crea un evento de prueba para mañana"
                
                if not user_input:
                    continue
                
                print(f"\n🤖 Aura procesando: '{user_input}'...")
                print("🔄 Herramientas que puede usar:", ", ".join(client.get_available_tools()))
                print("-" * 50)
                
                # Procesar mensaje con el agente
                response = await client.chat(user_input)
                
                print("-" * 50)
                print(f"🤖 Aura: {response}")
                print("=" * 70)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Test interrumpido por el usuario")
                break
            except EOFError:
                print("\n\n👋 Test finalizado")
                break
            except Exception as e:
                print(f"\n❌ Error durante el test: {e}")
                print("📋 Tip: Verifica que los servidores MCP estén funcionando")
                print("Continuando con el test...\n")
    
    except Exception as e:
        print(f"❌ Error fatal en el test: {e}")
        return 1
    
    finally:
        # Cleanup
        if 'client' in locals():
            try:
                await client.cleanup()
                print("🧹 Cliente limpiado")
            except Exception as e:
                print(f"⚠️ Error durante cleanup: {e}")
    
    return 0


def main():
    """Punto de entrada"""
    try:
        exit_code = asyncio.run(test_client())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 ¡Test terminado!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error ejecutando test: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
