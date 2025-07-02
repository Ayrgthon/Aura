#!/usr/bin/env python3
"""
Script de demostración para Aura con soporte Gemini/Ollama + MCP
Muestra cómo usar ambos modelos con herramientas MCP
"""

import os
import asyncio
import warnings
from client import AuraClient

# Silenciar warnings
warnings.filterwarnings("ignore")

async def demo_gemini_with_mcp():
    """Demuestra Aura con Google Gemini y herramientas MCP"""
    print("🟢 === DEMO: Google Gemini con MCP ===")
    print("=" * 50)
    
    # Crear cliente Gemini
    client = AuraClient(
        model_type="gemini",
        model_name="gemini-2.0-flash-exp",
        enable_voice=False  # Sin voz para esta demo
    )
    
    # Configurar MCP
    home_dir = os.path.expanduser("~")
    allowed_dirs = [home_dir, "/tmp"]
    
    # Agregar directorios que existen
    for potential_dir in [f"{home_dir}/Documents", f"{home_dir}/Documentos", f"{home_dir}/Descargas"]:
        if os.path.exists(potential_dir):
            allowed_dirs.append(potential_dir)
    
    mcp_config = {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_dirs,
            "transport": "stdio"
        }
    }
    
    print("🔧 Configurando servidores MCP...")
    mcp_success = await client.setup_mcp_servers(mcp_config)
    
    if not mcp_success:
        print("⚠️  MCP no disponible, continuando sin herramientas")
    
    # Pruebas con Gemini
    test_prompts = [
        "Hola, ¿quién eres?",
        "Lista los archivos en mi directorio home",
        "¿Puedes explicarme qué es Python en 2 líneas?",
        "Muéstrame información sobre un archivo llamado README.md si existe"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Prueba {i}: Gemini ---")
        print(f"👤 Pregunta: {prompt}")
        print("🤖 Gemini:", end=" ")
        
        try:
            await client.chat_with_voice(prompt)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return client

async def demo_ollama_with_mcp():
    """Demuestra Aura con Ollama y herramientas MCP"""
    print("\n\n🦙 === DEMO: Ollama con MCP ===")
    print("=" * 50)
    
    # Crear cliente Ollama
    try:
        client = AuraClient(
            model_type="ollama",
            model_name="qwen2.5-coder:7b",
            enable_voice=False  # Sin voz para esta demo
        )
    except Exception as e:
        print(f"❌ Error inicializando Ollama: {e}")
        print("💡 Asegúrate de que Ollama esté ejecutándose con: ollama serve")
        print("💡 Y que tengas el modelo instalado: ollama pull qwen2.5-coder:7b")
        return None
    
    # Configurar MCP (reutilizar la misma configuración)
    home_dir = os.path.expanduser("~")
    allowed_dirs = [home_dir, "/tmp"]
    
    for potential_dir in [f"{home_dir}/Documents", f"{home_dir}/Documentos", f"{home_dir}/Descargas"]:
        if os.path.exists(potential_dir):
            allowed_dirs.append(potential_dir)
    
    mcp_config = {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_dirs,
            "transport": "stdio"
        }
    }
    
    print("🔧 Configurando servidores MCP para Ollama...")
    mcp_success = await client.setup_mcp_servers(mcp_config)
    
    if not mcp_success:
        print("⚠️  MCP no disponible, continuando sin herramientas")
    
    # Pruebas con Ollama (enfoque en programación)
    test_prompts = [
        "Hola, soy un desarrollador. ¿Puedes ayudarme?",
        "Lista archivos Python en mi directorio si hay alguno",
        "Explica las diferencias entre async y sync en Python",
        "¿Qué archivos de configuración encuentras en mi home?"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Prueba {i}: Ollama ---")
        print(f"👤 Pregunta: {prompt}")
        print("🦙 Ollama:", end=" ")
        
        try:
            await client.chat_with_voice(prompt)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return client

async def comparison_demo():
    """Demuestra una comparación directa entre ambos modelos"""
    print("\n\n⚖️  === DEMO: Comparación Gemini vs Ollama ===")
    print("=" * 60)
    
    # Pregunta común para ambos
    common_question = "Escribe una función Python que calcule el factorial de un número de forma recursiva"
    
    print(f"📝 Pregunta común: {common_question}")
    print("\n" + "=" * 30 + " GEMINI " + "=" * 30)
    
    # Respuesta de Gemini
    try:
        gemini_client = AuraClient(model_type="gemini", enable_voice=False)
        print("🤖 Gemini:", end=" ")
        await gemini_client.chat_with_voice(common_question)
    except Exception as e:
        print(f"❌ Error con Gemini: {e}")
    
    print("\n" + "=" * 30 + " OLLAMA " + "=" * 30)
    
    # Respuesta de Ollama
    try:
        ollama_client = AuraClient(model_type="ollama", enable_voice=False)
        print("🦙 Ollama:", end=" ")
        await ollama_client.chat_with_voice(common_question)
    except Exception as e:
        print(f"❌ Error con Ollama: {e}")

async def interactive_choice_demo():
    """Demo interactiva que permite al usuario elegir el modelo"""
    print("\n\n🎮 === DEMO INTERACTIVA ===")
    print("=" * 40)
    print("¿Qué modelo quieres probar?")
    print("1. 🟢 Google Gemini")
    print("2. 🦙 Ollama")
    print("3. ⚖️  Comparar ambos")
    print("4. 🚪 Salir")
    
    while True:
        try:
            choice = input("\nSelecciona una opción (1-4): ").strip()
            
            if choice == "1":
                client = AuraClient(model_type="gemini", enable_voice=False)
                break
            elif choice == "2":
                client = AuraClient(model_type="ollama", enable_voice=False)
                break
            elif choice == "3":
                await comparison_demo()
                return
            elif choice == "4":
                print("👋 ¡Hasta luego!")
                return
            else:
                print("❌ Opción no válida")
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            return
    
    # Configurar MCP para el modelo elegido
    home_dir = os.path.expanduser("~")
    allowed_dirs = [home_dir, "/tmp"]
    
    for potential_dir in [f"{home_dir}/Documents", f"{home_dir}/Documentos", f"{home_dir}/Descargas"]:
        if os.path.exists(potential_dir):
            allowed_dirs.append(potential_dir)
    
    mcp_config = {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_dirs,
            "transport": "stdio"
        }
    }
    
    print("🔧 Configurando MCP...")
    await client.setup_mcp_servers(mcp_config)
    
    # Chat interactivo
    print(f"\n🗣️  Chat con {client.model_type.upper()}")
    print("Escribe 'salir' para terminar")
    print("-" * 40)
    
    while True:
        try:
            user_input = input(f"\n👤 Tú: ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                break
            
            if not user_input:
                continue
            
            print(f"🤖 {client.model_type.upper()}:", end=" ")
            await client.chat_with_voice(user_input)
            
        except KeyboardInterrupt:
            break
    
    print("👋 ¡Hasta luego!")

async def main():
    """Función principal del demo"""
    print("🌟 AURA - Demo de Capacidades Gemini/Ollama + MCP")
    print("=" * 60)
    
    # Verificar dependencias
    print("🔍 Verificando dependencias...")
    
    try:
        # Verificar imports básicos
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("✅ Google Gemini disponible")
    except ImportError:
        print("❌ Google Gemini no disponible")
    
    try:
        from langchain_ollama import ChatOllama
        print("✅ Ollama disponible")
    except ImportError:
        print("❌ Ollama no disponible")
    
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        print("✅ MCP adapters disponibles")
    except ImportError:
        print("❌ MCP adapters no disponibles")
    
    print("\n¿Qué demo quieres ejecutar?")
    print("1. 🟢 Demo completo con Gemini")
    print("2. 🦙 Demo completo con Ollama")
    print("3. ⚖️  Comparación lado a lado")
    print("4. 🎮 Demo interactivo (tú eliges)")
    print("5. 🚪 Salir")
    
    while True:
        try:
            choice = input("\nSelecciona una opción (1-5): ").strip()
            
            if choice == "1":
                await demo_gemini_with_mcp()
                break
            elif choice == "2":
                await demo_ollama_with_mcp()
                break
            elif choice == "3":
                await comparison_demo()
                break
            elif choice == "4":
                await interactive_choice_demo()
                break
            elif choice == "5":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error: {e}") 