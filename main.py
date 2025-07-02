#!/usr/bin/env python3
"""
Punto de entrada principal para AuraGemini
Cliente de Google Gemini con funcionalidades de voz integradas usando LangChain
"""

import os
import sys
import asyncio
import warnings
from pathlib import Path

# Silenciar warnings molestos
warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated!")
warnings.filterwarnings("ignore", category=UserWarning)

# Silenciar mensajes de schema de MCP
import logging
logging.getLogger().setLevel(logging.ERROR)

# Redirigir stderr temporalmente para silenciar mensajes de Key schema
import io
from contextlib import redirect_stderr

# Agregar el directorio actual al path de Python
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from client import GeminiClient
    from engine.voice.hear import initialize_recognizer, listen_for_command
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("💡 Asegúrate de tener todas las dependencias instaladas")
    print("💡 Ejecuta: pip install -r requirements.txt")
    sys.exit(1)

class AuraAssistant:
    def __init__(self):
        """Inicializar el asistente Aura con soporte MCP"""
        self.client = GeminiClient()
        self.voice_recognizer = None
        self.mcp_enabled = False
        
    async def setup_mcp(self, custom_configs=None):
        """
        Configurar servidores MCP
        
        Args:
            custom_configs: Configuraciones personalizadas de MCP
        """
        print("🔧 Configurando servidores MCP...")
        
        if custom_configs is None:
            # Configuración por defecto - solo usar directorios que existen
            home_dir = os.path.expanduser("~")
            allowed_dirs = [home_dir]
            
            # Agregar directorios comunes solo si existen
            common_dirs = [
                f"{home_dir}/Documents",
                f"{home_dir}/Documentos",  # Para sistemas en español
                f"{home_dir}/Desktop",
                f"{home_dir}/Escritorio",  # Para sistemas en español  
                f"{home_dir}/Downloads",
                f"{home_dir}/Descargas",   # Para sistemas en español
                "/tmp"  # Directorio temporal siempre existe
            ]
            
            for directory in common_dirs:
                if os.path.exists(directory):
                    allowed_dirs.append(directory)
            
            custom_configs = {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem"
                    ] + allowed_dirs,  # Usar solo directorios que existen
                    "transport": "stdio"
                }
            }
            
            print(f"📁 Directorios MCP permitidos: {allowed_dirs}")
        
        self.mcp_enabled = await self.client.setup_mcp_servers(custom_configs)
        
        if self.mcp_enabled:
            print("✅ MCPs configurados correctamente")
            print("🎯 Ahora puedes pedirme que:")
            print("  - Liste archivos en tu sistema")
            print("  - Lea el contenido de archivos")
            print("  - Cree o modifique archivos")
            print("  - Busque archivos por nombre")
            print("  - Obtenga información de archivos")
        else:
            print("⚠️  MCPs no disponibles - funcionando solo con capacidades básicas")
    
    def setup_voice(self):
        """Configurar reconocimiento de voz"""
        try:
            self.voice_recognizer = initialize_recognizer()
            if self.voice_recognizer:
                print("🎤 Reconocimiento de voz activado")
                return True
            else:
                print("⚠️  No se pudo activar el reconocimiento de voz")
                return False
        except Exception as e:
            print(f"⚠️  No se pudo activar el reconocimiento de voz: {e}")
            return False
    
    async def start_chat(self):
        """Iniciar el loop principal de chat"""
        print("🚀 ¡Aura está listo!")
        print("💬 Escribe 'quit' para salir")
        print("🎤 Escribe 'voice' para usar reconocimiento de voz")
        
        if self.mcp_enabled:
            print("🔧 Herramientas MCP disponibles - ¡Prueba comandos como 'lista mis archivos'!")
        
        while True:
            try:
                # Obtener entrada del usuario
                user_input = input("\n👤 Tú: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'salir']:
                    print("👋 ¡Hasta luego!")
                    break
                
                if user_input.lower() == 'voice':
                    if not self.voice_recognizer:
                        if not self.setup_voice():
                            print("❌ No se pudo activar reconocimiento de voz")
                            continue
                    
                    print("🎤 Escuchando... (habla ahora)")
                    voice_input = listen_for_command(self.voice_recognizer)
                    
                    if not voice_input:
                        print("❌ No se detectó audio")
                        continue
                    
                    print(f"👤 Tú (voz): {voice_input}")
                    user_input = voice_input
                
                if not user_input:
                    continue
                
                # Obtener respuesta del asistente
                print("🤖 Aura: ", end="", flush=True)
                response = await self.client.chat_with_voice(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

async def main():
    """Función principal"""
    print("🌟 === AURA - Asistente IA con MCP ===")
    
    # Crear asistente
    assistant = AuraAssistant()
    
    # Configurar MCPs
    await assistant.setup_mcp()
    
    # Iniciar chat
    await assistant.start_chat()

if __name__ == "__main__":
    try:
        # Ejecutar el asistente
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Programa terminado por el usuario!")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        sys.exit(1) 