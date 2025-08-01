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
from dotenv import load_dotenv
from client import AuraClient

# Manejo de imports relativos/absolutos para funcionar desde src/ o como módulo
try:
    from voice.hear import initialize_recognizer, listen_for_command
except ImportError:
    # Si falla el import relativo, intentar import absoluto (cuando se ejecuta desde src/)
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from voice.hear import initialize_recognizer, listen_for_command

# Cargar variables de entorno desde .env
load_dotenv()

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
        """Configura el modelo Gemini a usar"""
        print("🤖 Configuración de Modelo Gemini")
        print("=" * 50)
        print("Modelos disponibles:")
        print("1. 🟢 gemini-2.5-pro (recomendado)")
        print("2. 🟢 gemini-2.5-flash")
        print("3. 🟢 gemini-2.5-flash-lite")
        print("4. 🟢 gemini-2.0-flash")
        print("5. 🟢 gemini-2.0-flash-lite")
        print("6. 🛠️  Personalizado")
        
        while True:
            try:
                choice = input("\nSelecciona un modelo (1-6): ").strip()
                
                if choice == "1":
                    model_name = "gemini-2.5-pro"
                    print(f"✅ Seleccionado: {model_name}")
                    break
                    
                elif choice == "2":
                    model_name = "gemini-2.5-flash"
                    print(f"✅ Seleccionado: {model_name}")
                    break
                    
                elif choice == "3":
                    model_name = "gemini-2.5-flash-lite"
                    print(f"✅ Seleccionado: {model_name}")
                    break
                    
                elif choice == "4":
                    model_name = "gemini-2.0-flash"
                    print(f"✅ Seleccionado: {model_name}")
                    break
                    
                elif choice == "5":
                    model_name = "gemini-2.0-flash-lite"
                    print(f"✅ Seleccionado: {model_name}")
                    break
                    
                elif choice == "6":
                    # Personalizado
                    print("\nConfiguración personalizada:")
                    print("Ejemplos: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash")
                    model_name = input("Nombre del modelo Gemini: ").strip()
                    
                    if not model_name:
                        print("❌ Nombre de modelo no puede estar vacío")
                        continue
                        
                    print(f"✅ Configuración personalizada: {model_name}")
                    break
                    
                else:
                    print("❌ Opción no válida. Selecciona 1, 2, 3, 4, 5 o 6.")
                    
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                exit(0)
        
        return model_name
    
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
        """Configura los servidores MCP con todas las herramientas disponibles"""
        print("\n🔧 Configurando MCP (Model Context Protocol)")
        print("🚀 Activando todas las herramientas: Filesystem + Brave Search + Obsidian Memory")
        print("=" * 70)
        
        # Configurar todos los MCPs disponibles
        filesystem_config = self._get_filesystem_config()
        brave_config = self._get_brave_search_config()
        obsidian_config = self._get_obsidian_memory_config()
        mcp_config = {**filesystem_config, **brave_config, **obsidian_config}
        
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
            (f"{home_dir}/Documentos", "Documentos"),
            (f"{home_dir}/Desktop", "Desktop"),
            (f"{home_dir}/Escritorio", "Escritorio"),
            (f"{home_dir}/Pictures", "Pictures"),
            (f"{home_dir}/Descargas", "Descargas"),
            (f"{home_dir}/Downloads", "Downloads"),
            ("/tmp", "temporal"),
            ("/home/ary/Documents/Ary Vault", "Obsidian Vault")  # Actualizada ruta
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
            print("❌ BRAVE_API_KEY no encontrada en las variables de entorno")
            return {}
        
        print("✅ Usando API key desde variables de entorno")
        
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
        server_path = "./mcp/obsidian_memory_server.js"
        if not os.path.exists(server_path):
            print(f"❌ El servidor MCP no existe en: {server_path}")
            print("💡 Asegúrate de que el archivo obsidian_memory_server.js está en el directorio actual")
            return {}
        
        print(f"✅ Vault detectado: {vault_path}")
        print(f"✅ Servidor MCP disponible: {server_path}")
        
        return {
            "obsidian-memory": {
                "command": "node",
                "args": [server_path],
                "transport": "stdio"
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
    
    async def cleanup_all(self):
        """Limpia todos los recursos"""
        # Limpiar cliente si existe
        if self.client:
            try:
                await self.client.cleanup()
            except Exception as e:
                print(f"⚠️  Error limpiando cliente: {e}")
        
        # Limpiar procesos
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
                
                if not user_input:
                    continue
                
                # Procesar con el cliente
                if not self.client:
                    print("❌ Cliente no disponible")
                    continue
                    
                print(f"\n🤖 GEMINI:", end=" ")
                await self.client.chat_with_voice(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def main(self):
        """Función principal del asistente"""
        print("🌟 AURA - Asistente Gemini con MCP")
        print("Soporte para Google Gemini y MCP")
        print("=" * 50)
        
        try:
            # 1. Configurar modelo
            model_name = self.setup_model()
            
            # 2. Configurar voz
            enable_voice = self.setup_voice()
            
            # 3. Inicializar cliente
            print(f"\n🚀 Inicializando cliente Gemini...")
            
            self.client = AuraClient(
                model_name=model_name,
                enable_voice=enable_voice
            )
            
            # 4. Configurar MCP
            await self.setup_mcp()
            
            # 5. Ejecutar modo interactivo
            await self.run_interactive_mode()
            
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            return 1
        finally:
            # Limpiar todos los recursos al salir
            await self.cleanup_all()
        
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
