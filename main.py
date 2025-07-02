#!/usr/bin/env python3
"""
Aura - Asistente de IA con Voz y MCP
Soporta Google Gemini y Ollama con herramientas MCP
"""

import os
import asyncio
import warnings
from client import AuraClient
from engine.voice.hear import initialize_recognizer, listen_for_command

# Silenciar warnings
warnings.filterwarnings("ignore")

class AuraAssistant:
    def __init__(self):
        """Inicializa el asistente Aura"""
        self.client = None
        self.voice_recognizer = None
        
    def setup_model(self):
        """Configura el modelo LLM a usar"""
        print("🤖 Configuración de Modelo LLM")
        print("=" * 50)
        print("Modelos disponibles:")
        print("1. 🟢 Google Gemini (gemini-2.0-flash-exp)")
        print("2. 🦙 Ollama (qwen2.5-coder:7b)")
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
                    model_name = "qwen2.5-coder:7b"
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
                        print("Ejemplos: qwen2.5-coder:7b, llama3.2:latest, codellama:latest")
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
        
        # Detectar directorios existentes para la configuración
        home_dir = os.path.expanduser("~")
        possible_dirs = [
            (home_dir, "home"),
            (f"{home_dir}/Documents", "Documents"),
            (f"{home_dir}/Documentos", "Documentos"),
            (f"{home_dir}/Desktop", "Desktop"),
            (f"{home_dir}/Escritorio", "Escritorio"),
            (f"{home_dir}/Descargas", "Descargas"),
            (f"{home_dir}/Downloads", "Downloads"),
            ("/tmp", "temporal")
        ]
        
        # Filtrar solo directorios que existen
        allowed_dirs = []
        for dir_path, description in possible_dirs:
            if os.path.exists(dir_path):
                allowed_dirs.append(dir_path)
                print(f"📁 Directorio detectado: {description} ({dir_path})")
        
        if not allowed_dirs:
            print("⚠️  No se encontraron directorios para MCP filesystem")
            return False
        
        print(f"\n✅ {len(allowed_dirs)} directorios configurados para acceso MCP")
        
        # Configuración de servidores MCP
        mcp_config = {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_dirs,
                "transport": "stdio"
            }
        }
        
        print("🚀 Configurando servidores MCP...")
        success = await self.client.setup_mcp_servers(mcp_config)
        
        if success:
            print("✅ Servidores MCP configurados correctamente")
            return True
        else:
            print("⚠️  MCP no disponible, continuando sin herramientas de archivos")
            return False
    
    async def run_interactive_mode(self):
        """Ejecuta el modo interactivo"""
        print("\n🗣️  Modo Interactivo Activado")
        print("=" * 35)
        print("Comandos disponibles:")
        print("  • 'salir' o 'exit' - Terminar")
        print("  • 'escuchar' - Entrada por voz (si está disponible)")
        print("  • 'limpiar' - Limpiar historial")
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
                print(f"\n🤖 {self.client.model_type.upper()}:", end=" ")
                await self.client.chat_with_voice(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
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
            self.client = AuraClient(
                model_type=model_type,
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