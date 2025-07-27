#!/usr/bin/env python3
"""
Aura - Asistente de IA con Voz y MCP
Soporta Google Gemini y Ollama con herramientas MCP
"""

import os
import asyncio
import warnings
import subprocess
import threading
import time
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import AuraClient
from voice.hear import initialize_recognizer, listen_for_command

# Silenciar warnings
warnings.filterwarnings("ignore")

class AuraAssistant:
    def __init__(self):
        """Inicializa el asistente Aura"""
        self.client = None
        self.voice_recognizer = None
        self.websocket_process = None
        self.frontend_process = None
        
    def setup_model(self):
        """Configura el modelo LLM a usar"""
        print("🤖 Configuración de Modelo LLM")
        print("=" * 50)
        print("Modelos disponibles:")
        print("1. 🟢 Google Gemini (gemini-2.0-flash-exp)")
        print("2. 🦙 Ollama (qwen3:1.7b)")
        print("3. 🛠️  Personalizado")
        
        while True:
            try:
                choice = input("\nSelecciona un modelo (1-3): ").strip()
                
                if choice == "1":
                    # Google Gemini
                    model_type = "gemini"
                    model_name = "gemini-2.0-flash-exp"
                    print(f"✅ Seleccionado: Google Gemini ({model_name})")
                    break
                    
                elif choice == "2":
                    # Ollama
                    model_type = "ollama"
                    model_name = "qwen3:1.7b"
                    print(f"✅ Seleccionado: Ollama ({model_name})")
                    break
                    
                elif choice == "3":
                    # Personalizado
                    print("\nConfiguración personalizada:")
                    model_type = input("Tipo de modelo (gemini/ollama): ").strip().lower()
                    
                    if model_type not in ["gemini", "ollama"]:
                        print("❌ Tipo de modelo no válido")
                        continue
                        
                    if model_type == "gemini":
                        print("Ejemplos: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp")
                        model_name = input("Nombre del modelo: ").strip()
                    else:
                        print("Ejemplos: qwen3:1.7b, llama3.2:latest, codellama:latest")
                        model_name = input("Nombre del modelo: ").strip()
                    
                    if not model_name:
                        print("❌ Nombre de modelo no puede estar vacío")
                        continue
                        
                    print(f"✅ Configuración personalizada: {model_type.upper()} ({model_name})")
                    break
                    
                else:
                    print("❌ Opción no válida. Selecciona 1, 2 o 3.")
                    
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                exit(0)
        
        return model_type, model_name
    
    def setup_voice(self):
        """Configura las capacidades de voz"""
        print("\n🎤 Configuración de Voz")
        print("=" * 30)
        
        while True:
            try:
                choice = input("¿Habilitar funcionalidades de voz? (s/n): ").strip().lower()
                
                if choice in ['s', 'si', 'sí', 'y', 'yes']:
                    print("🎤 Inicializando reconocimiento de voz...")
                    try:
                        self.voice_recognizer = initialize_recognizer()
                        if self.voice_recognizer:
                            print("✅ Reconocimiento de voz activado")
                            
                            # Lanzar servidor WebSocket y frontend
                            self.launch_voice_interface()
                            
                            return True
                        else:
                            print("⚠️  No se pudo inicializar el reconocimiento de voz")
                            print("ℹ️  Continuando sin funcionalidades de voz")
                            return False
                    except Exception as e:
                        print(f"❌ Error configurando voz: {e}")
                        print("ℹ️  Continuando sin funcionalidades de voz")
                        return False
                        
                elif choice in ['n', 'no']:
                    print("✅ Modo sin voz seleccionado")
                    return False
                    
                else:
                    print("❌ Respuesta no válida. Usa 's' para sí o 'n' para no.")
                    
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                exit(0)
    
    async def setup_mcp(self):
        """Configura los servidores MCP"""
        print("\n🔧 Configuración de MCP (Model Context Protocol)")
        print("=" * 55)
        print("Opciones disponibles:")
        print("1. 📁 Solo Filesystem (operaciones con archivos)")
        print("2. 🔍 Solo Brave Search (búsquedas web)")
        print("3. 🗃️ Solo Obsidian Memory (memoria centralizada)")
        print("4. 🌐 Solo Playwright (automatización web)")
        print("5. 📝 Solo Notion (gestión de notas)")
        print("6. 🌐 Filesystem + Brave Search")
        print("7. 🧠 Obsidian Memory + Brave Search (recomendado)")
        print("8. 🔧 Filesystem + Obsidian Memory + Brave Search")
        print("9. 🚀 Filesystem + Brave Search + Playwright (ecommerce)")
        print("10. 📝 Notion + Brave Search (productividad)")
        print("11. ⭐ Todos los MCPs (completo)")
        print("0. ❌ Sin MCP")
        
        while True:
            try:
                choice = input("\nSelecciona configuración MCP (1-9, 0): ").strip()
                
                if choice == "1":
                    # Solo filesystem
                    mcp_config = self._get_filesystem_config()
                    break
                elif choice == "2":
                    # Solo Brave Search
                    mcp_config = self._get_brave_search_config()
                    break
                elif choice == "3":
                    # Solo Obsidian Memory
                    mcp_config = self._get_obsidian_memory_config()
                    break
                elif choice == "4":
                    # Solo Playwright
                    mcp_config = self._get_playwright_config()
                    break
                elif choice == "5":
                    # Solo Notion
                    mcp_config = self._get_notion_config()
                    break
                elif choice == "6":
                    # Filesystem + Brave Search
                    filesystem_config = self._get_filesystem_config()
                    brave_config = self._get_brave_search_config()
                    mcp_config = {**filesystem_config, **brave_config}
                    break
                elif choice == "7":
                    # Obsidian Memory + Brave Search
                    obsidian_config = self._get_obsidian_memory_config()
                    brave_config = self._get_brave_search_config()
                    mcp_config = {**obsidian_config, **brave_config}
                    break
                elif choice == "8":
                    # Filesystem + Obsidian Memory + Brave Search
                    filesystem_config = self._get_filesystem_config()
                    brave_config = self._get_brave_search_config()
                    obsidian_config = self._get_obsidian_memory_config()
                    mcp_config = {**filesystem_config, **brave_config, **obsidian_config}
                    break
                elif choice == "9":
                    # Filesystem + Brave Search + Playwright (ecommerce)
                    filesystem_config = self._get_filesystem_config()
                    brave_config = self._get_brave_search_config()
                    playwright_config = self._get_playwright_config()
                    mcp_config = {**filesystem_config, **brave_config, **playwright_config}
                    break
                elif choice == "10":
                    # Notion + Brave Search
                    notion_config = self._get_notion_config()
                    brave_config = self._get_brave_search_config()
                    mcp_config = {**notion_config, **brave_config}
                    break
                elif choice == "11":
                    # Todos los MCPs
                    filesystem_config = self._get_filesystem_config()
                    brave_config = self._get_brave_search_config()
                    obsidian_config = self._get_obsidian_memory_config()
                    playwright_config = self._get_playwright_config()
                    notion_config = self._get_notion_config()
                    mcp_config = {**filesystem_config, **brave_config, **obsidian_config, **playwright_config, **notion_config}
                    break
                elif choice == "0":
                    # Sin MCP
                    print("✅ Continuando sin MCP")
                    return False
                else:
                    print("❌ Opción no válida. Selecciona 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 o 0.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                exit(0)
        
        if not self.client:
            print("❌ Cliente no inicializado")
            return False
            
        print("🚀 Configurando servidores MCP...")
        success = await self.client.setup_mcp_servers(mcp_config)
        
        if success:
            print("✅ Servidores MCP configurados correctamente")
            # Si se detectaron directorios permitidos para filesystem, pásalos al cliente
            if hasattr(self, "allowed_dirs") and self.allowed_dirs:
                try:
                    self.client.add_allowed_directories_context(self.allowed_dirs)  # type: ignore
                except Exception as e:
                    print(f"⚠️  No se pudo añadir contexto de directorios: {e}")
            return True
        else:
            print("⚠️  MCP no disponible, continuando sin herramientas adicionales")
            return False
    
    def _get_filesystem_config(self):
        """Obtiene la configuración del MCP filesystem"""
        # Detectar directorios existentes para la configuración
        home_dir = os.path.expanduser("~")
        possible_dirs = [
            (home_dir, "home"),
            (f"{home_dir}/Documents", "Documents"),
            (f"{home_dir}/Downloads", "Downloads"),
            (f"{home_dir}/Pictures", "Pictures"),
            ("/tmp", "temporal"),
            ("/home/ary/Documents/Ary Vault", "Obsidian Vault")
        ]
        
        # Filtrar solo directorios que existen
        allowed_dirs = []
        for dir_path, description in possible_dirs:
            if os.path.exists(dir_path):
                allowed_dirs.append(dir_path)
                print(f"📁 Directorio detectado: {description} ({dir_path})")
        
        if not allowed_dirs:
            print("⚠️  No se encontraron directorios para MCP filesystem")
            return {}
        
        print(f"✅ {len(allowed_dirs)} directorios configurados para acceso MCP")
        
        # Guardar para que el cliente pueda añadirlos al prompt de sistema más tarde
        self.allowed_dirs = allowed_dirs
        
        return {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_dirs,
                "transport": "stdio"
            }
        }
    
    def _get_brave_search_config(self):
        """Obtiene la configuración del MCP Brave Search"""
        print("🔍 Configurando Brave Search...")
        
        brave_api_key = os.getenv("BRAVE_API_KEY")
        if not brave_api_key:
            print("⚠️  BRAVE_API_KEY no encontrada en .env")
            return {}
        
        print("✅ Usando API key de Brave Search")
        
        return {
            "brave-search": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "transport": "stdio",
                "env": {
                    "BRAVE_API_KEY": brave_api_key
                }
            }
        }
    
    def _get_obsidian_memory_config(self):
        """Obtiene la configuración del MCP Obsidian Memory"""
        print("🗃️ Configurando Obsidian Memory...")
        
        # Verificar que el vault existe
        vault_path = "/home/ary/Documents/Ary Vault"
        if not os.path.exists(vault_path):
            print(f"❌ El vault de Obsidian no existe en: {vault_path}")
            print("💡 Verifica la ruta del vault en el archivo obsidian_memory_server.js")
            return {}
        
        # Verificar que el servidor MCP existe
        server_path = "./obsidian_memory_server.js"
        if not os.path.exists(server_path):
            print(f"❌ El servidor MCP no existe en: {server_path}")
            print("💡 Asegúrate de que el archivo obsidian_memory_server.js está en el directorio actual")
            return {}
        
        print(f"✅ Vault detectado: {vault_path}")
        print(f"✅ Servidor MCP disponible: {server_path}")
        
        return {
            "obsidian-memory": {
                "command": "node",
                "args": ["./mcp/obsidian_memory_server.js"],
                "transport": "stdio"
            }
        }
    
    def _get_playwright_config(self):
        """Obtiene la configuración del MCP Playwright"""
        print("🌐 Configurando Playwright...")
        
        # Verificar que Playwright está instalado
        try:
            import subprocess
            result = subprocess.run(["npx", "playwright", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Playwright detectado y listo")
            else:
                print("⚠️  Playwright no está completamente instalado")
                print("💡 Ejecuta: npx playwright install")
                return {}
        except Exception as e:
            print(f"⚠️  Error verificando Playwright: {e}")
            return {}
        
        return {
            "playwright": {
                "command": "npx",
                "args": ["-y", "@playwright/mcp"],
                "transport": "stdio"
            }
        }
    
    def _get_notion_config(self):
        """Obtiene la configuración del MCP Notion"""
        print("📝 Configurando Notion...")
        
        notion_api_key = os.getenv("NOTION_API_KEY")
        if not notion_api_key:
            print("⚠️  NOTION_API_KEY no encontrada en .env")
            print("💡 Obtén tu API key en: https://www.notion.so/my-integrations")
            return {}
        
        print("✅ Usando API key de Notion")
        
        return {
            "notion": {
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "transport": "stdio",
                "env": {
                    "OPENAPI_MCP_HEADERS": json.dumps({
                        "Authorization": f"Bearer {notion_api_key}",
                        "Notion-Version": "2022-06-28"
                    })
                }
            }
        }
    
    def launch_voice_interface(self):
        """Lanza el servidor WebSocket y la interfaz web"""
        print("\n🚀 Iniciando interfaz de voz...")
        
        try:
            # 1. Iniciar servidor WebSocket
            print("📡 Iniciando servidor WebSocket...")
            self.websocket_process = subprocess.Popen(
                ["python", "websocket_server_simple.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Esperar un poco para que el servidor inicie
            time.sleep(2)
            
            # 2. Iniciar frontend
            print("🌐 Iniciando interfaz web...")
            self.frontend_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd="stellar-voice-display",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Esperar un poco más
            time.sleep(3)
            
            print("✅ Interfaz de voz iniciada")
            print("🌐 Abre tu navegador en: http://localhost:5173")
            print("📡 WebSocket escuchando en: ws://localhost:8765")
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ Error iniciando interfaz de voz: {e}")
            self.cleanup_processes()
    
    def cleanup_processes(self):
        """Limpia los procesos iniciados"""
        if self.websocket_process:
            try:
                self.websocket_process.terminate()
                self.websocket_process = None
            except:
                pass
                
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process = None
            except:
                pass

    async def run_interactive_mode(self):
        """Ejecuta el modo interactivo"""
        print("\n🗣️  Modo Interactivo Activado")
        print("=" * 35)
        print("Comandos disponibles:")
        print("  • 'salir' o 'exit' - Terminar")
        print("  • 'escuchar' - Entrada por voz (si está disponible)")
        print("  • 'limpiar' - Limpiar historial")
        print("  • 'langgraph on/off' - Habilitar/deshabilitar LangGraph")
        print("  • 'status' - Ver estado del agente")
        
        # Si la interfaz de voz está activa, mostrar información adicional
        if self.websocket_process:
            print("\n💡 Tip: También puedes usar la interfaz web para control por voz")
            print("🌐 http://localhost:8081")
        
        print("-" * 50)
        
        while True:
            try:
                # Obtener entrada del usuario
                user_input = input("\n👤 Tú: ").strip()
                
                # Comandos especiales
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("👋 ¡Hasta luego!")
                    break
                
                if user_input.lower() in ['limpiar', 'clear']:
                    if self.client:
                        self.client.conversation_history = []
                        print("🗑️  Historial limpiado")
                    continue
                
                if user_input.lower() in ['escuchar', 'listen'] and self.voice_recognizer:
                    print("🎤 Escuchando... (habla ahora)")
                    voice_text = listen_for_command(self.voice_recognizer, timeout=10)
                    if voice_text:
                        user_input = voice_text
                        print(f"👤 Tú (por voz): {user_input}")
                    else:
                        print("🔇 No se detectó entrada de voz")
                        continue
                
                # Comandos de LangGraph
                if user_input.lower().startswith('langgraph'):
                    if self.client:
                        if 'on' in user_input.lower():
                            self.client.enable_langgraph(True)
                        elif 'off' in user_input.lower():
                            self.client.enable_langgraph(False)
                        else:
                            status = self.client.get_agent_status()
                            print(f"🔧 LangGraph: {'Habilitado' if status['langgraph_enabled'] else 'Deshabilitado'}")
                    continue
                
                if user_input.lower() == 'status':
                    if self.client:
                        status = self.client.get_agent_status()
                        print(f"\n🤖 Estado del Agente:")
                        print(f"  📊 LangGraph disponible: {status['langgraph_available']}")
                        print(f"  🔧 LangGraph habilitado: {status['langgraph_enabled']}")
                        print(f"  ⚡ Agente LangGraph activo: {status['langgraph_agent']}")
                        print(f"  🛠️ Herramientas MCP: {status['mcp_tools']}")
                        print(f"  💬 Historial: {status['conversation_history_length']} mensajes")
                    continue
                
                if not user_input:
                    continue
                
                # Procesar con el cliente
                if not self.client:
                    print("❌ Cliente no disponible")
                    continue
                    
                print(f"\n🤖 {self.client.model_type.upper()}:", end=" ")

                # Si hay herramientas MCP, usar flujo multi-paso
                if self.client.mcp_tools:
                    await self._multi_step_agent(user_input)
                else:
                    await self.client.chat_with_voice(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def _multi_step_agent(self, user_input: str):
        """Agente sencillo ReAct con múltiples pasos y callbacks de voz"""
        from langchain.schema import HumanMessage, AIMessage
        from voice.speak import speak_async

        if not self.client:
            print("❌ Cliente no inicializado")
            return

        model_with_tools = self.client.model.bind_tools(self.client.mcp_tools)

        # Historial temporal que incluye instrucciones de sistema y alias
        messages = list(self.client.conversation_history)
        messages.append(HumanMessage(content=user_input))

        step = 1
        while True:
            # Pensar
            speak_async(f"Paso {step}: pensando …")
            response = model_with_tools.invoke(messages)

            # ¿Pidió herramientas?
            if hasattr(response, 'tool_calls') and getattr(response, 'tool_calls'):
                for tool_call in getattr(response, 'tool_calls'):
                    tool_name = tool_call['name']
                    args = tool_call.get('args', {})
                    speak_async(f"Ejecutando {tool_name}")
                    try:
                        result = await self.client._execute_mcp_tool(tool_call)
                        speak_async(f"{tool_name} completado")
                    except Exception as e:
                        speak_async(f"Error en {tool_name}")
                        result = f"Error: {e}"

                    # Añadir al historial local Y global
                    observation_message = HumanMessage(content=f"Observación: {result}")
                    messages.append(AIMessage(content="", additional_kwargs={'tool_calls':[tool_call]}))
                    messages.append(observation_message)
                    # Añadir al historial global para persistencia
                    self.client.conversation_history.append(AIMessage(content="", additional_kwargs={'tool_calls':[tool_call]}))
                    self.client.conversation_history.append(observation_message)
                step += 1
                # Continuar loop para permitir nuevos planes
                continue
            else:
                # Respuesta final
                final_answer = response.content
                speak_async("Respuesta lista")
                print(final_answer)
                # Guardar en historial global
                self.client.conversation_history.append(HumanMessage(content=user_input))
                self.client.conversation_history.append(AIMessage(content=final_answer))
                break
    
    async def main(self):
        """Función principal del asistente"""
        print("🌟 AURA - Asistente de IA Universal")
        print("Soporte para Gemini, Ollama y MCP")
        print("=" * 50)
        
        try:
            # 1. Configurar modelo
            model_type, model_name = self.setup_model()
            
            # 2. Configurar voz
            enable_voice = self.setup_voice()
            
            # 3. Inicializar cliente
            print(f"\n🚀 Inicializando cliente {model_type.upper()}...")
            # Validar tipo de modelo
            if model_type not in ["gemini", "ollama"]:
                raise ValueError(f"Tipo de modelo no soportado: {model_type}")
            
            self.client = AuraClient(
                model_type=model_type,  # type: ignore
                model_name=model_name,
                enable_voice=enable_voice
            )
            
            # 4. Configurar MCP
            await self.setup_mcp()
            
            # Debug: Verificar historial después de configuración
            if self.client:
                print("\n🔍 Verificando configuración del historial...")
                self.client.debug_conversation_history()
                
                # Mostrar estado del agente
                status = self.client.get_agent_status()
                print(f"\n🤖 Estado del Agente:")
                print(f"  📊 LangGraph disponible: {status['langgraph_available']}")
                print(f"  🔧 LangGraph habilitado: {status['langgraph_enabled']}")
                print(f"  ⚡ Agente LangGraph activo: {status['langgraph_agent']}")
                print(f"  🛠️ Herramientas MCP: {status['mcp_tools']}")
                print(f"  💬 Historial: {status['conversation_history_length']} mensajes")
            
            # 5. Ejecutar modo interactivo
            await self.run_interactive_mode()
            
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            return 1
        finally:
            # Limpiar procesos al salir
            self.cleanup_processes()
        
        return 0

def main():
    """Punto de entrada principal"""
    assistant = AuraAssistant()
    try:
        return asyncio.run(assistant.main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
        return 0

if __name__ == "__main__":
    exit(main()) 