#!/usr/bin/env python3
"""
WebSocket Server para Aura - Asistente de IA con Voz
Servidor único y simplificado para comunicación en tiempo real
"""

import asyncio
import json
import logging
import threading
import time
import os
import sys
from typing import Dict, Set, Optional, Any
import websockets
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports de módulos locales
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from voice.hear import initialize_recognizer, listen_for_command, change_language
    from voice.speak import (
        get_synthesizer, start_streaming_tts, add_text_to_stream, 
        finish_streaming_tts, set_tts_engine
    )
    from client import AuraClient
    from system_stats_api import get_cpu_usage, get_ram_usage, get_ssd_usage, get_gpu_usage
    voice_modules_available = True
    logger.info("✅ Módulos de voz cargados correctamente")
except ImportError as e:
    logger.warning(f"⚠️ Algunos módulos no están disponibles: {e}")
    logger.info("🚀 Iniciando en modo simplificado (solo testing)")
    voice_modules_available = False

class AuraWebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.clients: Set = set()
        
        # Estados del sistema
        self.voice_recognizer = None
        self.voice_synthesizer = None
        self.aura_client: Optional[AuraClient] = None
        self.current_language = "es"
        self.available_languages = {"es": "vosk-model-es-0.42", "en": "vosk-model-en-us-0.42-gigaspeech"}
        
        # Estados de la sesión
        self.is_listening = False
        self.is_speaking = False
        self.is_streaming = False
        self.is_processing = False
        self.voice_modules_available = voice_modules_available
        
        # Hilos para tareas asíncronas
        self.listen_thread = None
        self.listen_stop_event = threading.Event()
        self.main_loop = None
        
    async def register_client(self, websocket):
        """Registra un nuevo cliente WebSocket"""
        self.clients.add(websocket)
        logger.info(f"Cliente conectado. Total: {len(self.clients)}")
        
        # Enviar mensaje de bienvenida
        await self.send_to_client(websocket, {
            "type": "connection",
            "message": "Conectado al servidor Aura",
            "language": self.current_language,
            "available_languages": list(self.available_languages.keys()),
            "voice_available": self.voice_modules_available
        })
        
    async def unregister_client(self, websocket):
        """Desregistra un cliente WebSocket"""
        self.clients.discard(websocket)
        logger.info(f"Cliente desconectado. Total: {len(self.clients)}")
        
    async def send_to_client(self, websocket, message: Dict[str, Any]):
        """Envía un mensaje a un cliente específico"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            self.clients.discard(websocket)
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            
    async def broadcast(self, message: Dict[str, Any]):
        """Envía un mensaje a todos los clientes conectados"""
        if not self.clients:
            return
            
        disconnected = []
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(client)
            except Exception as e:
                logger.error(f"Error en broadcast: {e}")
                disconnected.append(client)
        
        # Limpiar clientes desconectados
        for client in disconnected:
            self.clients.discard(client)
            
    async def handle_message(self, websocket, message: str):
        """Maneja los mensajes recibidos del cliente"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            logger.info(f"Mensaje recibido: {message_type}")
            
            if message_type == "init_voice":
                await self.init_voice_system()
                
            elif message_type == "init_aura":
                model_type = data.get("model_type", "gemini")
                model_name = data.get("model_name", "gemini-2.5-flash-lite")
                await self.init_aura_client(model_type, model_name)
                
            elif message_type == "start_listening":
                await self.start_listening()
                
            elif message_type == "stop_listening":
                await self.stop_listening()
                
            elif message_type == "change_language":
                language = data.get("language", "es")
                await self.change_language(language)
                
            elif message_type == "change_tts_engine":
                engine = data.get("engine", "gtts")
                await self.change_tts_engine(engine)
                
            elif message_type == "shutdown_system":
                await self.shutdown_system()
                
            elif message_type == "get_system_stats":
                await self.send_system_stats()
                
            else:
                logger.warning(f"Tipo de mensaje no reconocido: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Error decodificando JSON")
            await self.send_to_client(websocket, {
                "type": "error",
                "message": "Formato de mensaje inválido"
            })
        except Exception as e:
            logger.error(f"Error manejando mensaje: {e}")
            await self.send_to_client(websocket, {
                "type": "error", 
                "message": f"Error procesando mensaje: {str(e)}"
            })
    
    async def init_voice_system(self):
        """Inicializa el sistema de reconocimiento y síntesis de voz"""
        if not self.voice_modules_available:
            await self.broadcast({
                "type": "voice_ready",
                "message": "Sistema de voz simulado (módulos no disponibles)",
                "language": self.current_language
            })
            return
            
        try:
            logger.info("Inicializando sistema de voz...")
            
            # Inicializar reconocimiento de voz
            self.voice_recognizer = initialize_recognizer(self.current_language)
            
            # Inicializar síntesis de voz
            self.voice_synthesizer = get_synthesizer()
            
            if self.voice_recognizer and self.voice_synthesizer.initialized:
                await self.broadcast({
                    "type": "voice_ready",
                    "message": "Sistema de voz inicializado correctamente",
                    "language": self.current_language
                })
                logger.info("Sistema de voz inicializado correctamente")
            else:
                await self.broadcast({
                    "type": "error",
                    "message": "Error inicializando sistema de voz"
                })
                
        except Exception as e:
            logger.error(f"Error inicializando voz: {e}")
            await self.broadcast({
                "type": "error",
                "message": f"Error inicializando voz: {str(e)}"
            })
    
    async def init_aura_client(self, model_type: str, model_name: str):
        """Inicializa el cliente Aura con el modelo especificado"""
        if not self.voice_modules_available:
            await self.broadcast({
                "type": "aura_ready",
                "message": f"Cliente Aura simulado con {model_type}:{model_name}",
                "model_type": model_type,
                "model_name": model_name
            })
            return
            
        try:
            logger.info(f"Inicializando cliente Aura con {model_type}:{model_name}")
            
            # Limpiar cliente anterior si existe
            if self.aura_client:
                try:
                    await self.aura_client.cleanup()
                except:
                    pass
            
            # Crear nuevo cliente
            self.aura_client = AuraClient(
                model_name=model_name,
                enable_voice=True
            )
            
            # Configurar MCP con todas las herramientas
            mcp_config = self._get_mcp_config()
            if mcp_config:
                logger.info("🚀 Configurando servidores MCP...")
                success = await self.aura_client.setup_mcp_servers(mcp_config)
                
                if success:
                    logger.info("✅ Servidores MCP configurados correctamente")
                    # Si se detectaron directorios permitidos para filesystem, pásalos al cliente
                    if hasattr(self, "allowed_dirs") and self.allowed_dirs:
                        try:
                            self.aura_client.add_allowed_directories_context(self.allowed_dirs)
                        except Exception as e:
                            logger.warning(f"⚠️  No se pudo añadir contexto de directorios: {e}")
                else:
                    logger.warning("⚠️  MCP no disponible, continuando sin herramientas adicionales")
            
            await self.broadcast({
                "type": "aura_ready",
                "message": f"Cliente Aura inicializado con {model_type}:{model_name}",
                "model_type": model_type,
                "model_name": model_name
            })
            logger.info("Cliente Aura inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando Aura: {e}")
            await self.broadcast({
                "type": "error",
                "message": f"Error inicializando Aura: {str(e)}"
            })
    
    async def start_listening(self):
        """Inicia el reconocimiento de voz continuo"""
        if self.is_listening:
            return
            
        logger.info("Iniciando reconocimiento de voz...")
        self.is_listening = True
        self.listen_stop_event.clear()
        
        await self.broadcast({
            "type": "status",
            "listening": True,
            "message": "Iniciando reconocimiento de voz..."
        })
        
        if self.voice_modules_available and self.voice_recognizer:
            # Iniciar hilo de reconocimiento real
            self.listen_thread = threading.Thread(
                target=self._listen_continuous,
                daemon=True
            )
            self.listen_thread.start()
        else:
            # Simular reconocimiento después de 3 segundos
            asyncio.create_task(self.simulate_speech_recognition())
    
    async def stop_listening(self):
        """Detiene el reconocimiento de voz"""
        if not self.is_listening:
            return
            
        logger.info("Deteniendo reconocimiento de voz...")
        self.is_listening = False
        self.listen_stop_event.set()
        
        await self.broadcast({
            "type": "status",
            "listening": False,
            "message": "Reconocimiento de voz detenido"
        })
    
    def _listen_continuous(self):
        """Hilo para reconocimiento de voz continuo"""
        try:
            while self.is_listening and not self.listen_stop_event.is_set():
                try:
                    # Escuchar por comando de voz
                    text = listen_for_command(self.voice_recognizer, timeout=5)
                    
                    if text and len(text.strip()) > 0:
                        logger.info(f"Texto reconocido: {text}")
                        
                        # Usar el loop principal almacenado
                        if self.main_loop and not self.main_loop.is_closed():
                            # Enviar texto reconocido al frontend
                            future1 = asyncio.run_coroutine_threadsafe(
                                self.broadcast({
                                    "type": "speech_recognized",
                                    "text": text
                                }),
                                self.main_loop
                            )
                            
                            # Procesar con Aura si está disponible
                            if self.aura_client:
                                future2 = asyncio.run_coroutine_threadsafe(
                                    self._process_with_aura(text),
                                    self.main_loop
                                )
                            
                            # Opcional: esperar a que termine el broadcast
                            try:
                                future1.result(timeout=1.0)
                            except:
                                pass
                        else:
                            logger.warning("No hay loop principal disponible")
                    
                    # Pequeña pausa para evitar sobrecarga
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error en reconocimiento continuo: {e}")
                    time.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error fatal en reconocimiento continuo: {e}")
        finally:
            self.is_listening = False
    
    async def simulate_speech_recognition(self):
        """Simula el reconocimiento de voz para testing"""
        await asyncio.sleep(3)
        
        test_phrases = [
            "Hola Aura, ¿cómo estás?",
            "¿Cuál es la temperatura actual?",
            "Cuéntame una historia",
            "¿Qué tiempo hace hoy?"
        ]
        
        import random
        text = random.choice(test_phrases)
        
        await self.broadcast({
            "type": "speech_recognized", 
            "text": text
        })
        
        # Simular respuesta
        await asyncio.sleep(2)
        response = f"Esta es una respuesta simulada para: '{text}'. El sistema WebSocket está funcionando correctamente."
        
        await self.broadcast({
            "type": "aura_response",
            "response": response,
            "original_text": text
        })
    
    async def _process_with_aura(self, text: str):
        """Procesa el texto reconocido con Aura"""
        try:
            self.is_processing = True
            
            await self.broadcast({
                "type": "status",
                "processing": True,
                "message": "Procesando texto reconocido con Aura..."
            })
            
            # Procesar con Aura
            response = await self.aura_client.chat_with_voice(text)
            
            await self.broadcast({
                "type": "aura_response",
                "response": response or "No se pudo generar respuesta",
                "original_text": text
            })
            
            await self.broadcast({
                "type": "status",
                "processing": False,
                "streaming": False,
                "message": "Respuesta completada"
            })
            
        except Exception as e:
            logger.error(f"Error procesando con Aura: {e}")
            await self.broadcast({
                "type": "error",
                "message": f"Error procesando con Aura: {str(e)}"
            })
        finally:
            self.is_processing = False
    
    async def change_language(self, language: str):
        """Cambia el idioma del reconocimiento de voz"""
        if language not in self.available_languages:
            await self.broadcast({
                "type": "error",
                "message": f"Idioma no soportado: {language}"
            })
            return
        
        try:
            logger.info(f"Cambiando idioma a: {language}")
            
            # Detener reconocimiento actual
            was_listening = self.is_listening
            if self.is_listening:
                await self.stop_listening()
            
            # Cambiar idioma
            self.current_language = language
            
            if self.voice_modules_available:
                # Reinicializar reconocedor con nuevo idioma
                self.voice_recognizer = change_language(language)
                
                if self.voice_recognizer:
                    await self.broadcast({
                        "type": "language_changed",
                        "language": language,
                        "message": f"Idioma cambiado a: {language.upper()}"
                    })
                    
                    # Reanudar escucha si estaba activa
                    if was_listening:
                        await self.start_listening()
                else:
                    await self.broadcast({
                        "type": "error",
                        "message": f"Error cargando modelo para idioma: {language}"
                    })
            else:
                await self.broadcast({
                    "type": "language_changed",
                    "language": language,
                    "message": f"Idioma cambiado a: {language.upper()} (simulado)"
                })
            
        except Exception as e:
            logger.error(f"Error cambiando idioma: {e}")
            await self.broadcast({
                "type": "error",
                "message": f"Error cambiando idioma: {str(e)}"
            })
    
    async def change_tts_engine(self, engine: str):
        """Cambia el motor de TTS"""
        try:
            logger.info(f"Cambiando motor TTS a: {engine}")
            
            if self.voice_modules_available:
                success = set_tts_engine(engine)
                if success:
                    await self.broadcast({
                        "type": "tts_engine_changed",
                        "engine": engine,
                        "message": f"Motor TTS cambiado a: {engine}"
                    })
                else:
                    await self.broadcast({
                        "type": "error",
                        "message": f"Error cambiando motor TTS a: {engine}"
                    })
            else:
                await self.broadcast({
                    "type": "tts_engine_changed",
                    "engine": engine,
                    "message": f"Motor TTS cambiado a: {engine} (simulado)"
                })
                
        except Exception as e:
            logger.error(f"Error cambiando motor TTS: {e}")
            await self.broadcast({
                "type": "error",
                "message": f"Error cambiando motor TTS: {str(e)}"
            })
    
    async def send_system_stats(self):
        """Envía las estadísticas del sistema"""
        try:
            if self.voice_modules_available:
                stats = {
                    "cpu": get_cpu_usage(),
                    "gpu": get_gpu_usage(), 
                    "ram": get_ram_usage(),
                    "ssd": get_ssd_usage()
                }
            else:
                # Estadísticas simuladas
                import random
                stats = {
                    "cpu": round(random.uniform(10, 80), 1),
                    "gpu": round(random.uniform(5, 70), 1),
                    "ram": round(random.uniform(20, 85), 1),
                    "ssd": round(random.uniform(30, 90), 1)
                }
            
            await self.broadcast({
                "type": "system_stats",
                "stats": stats,
                "timestamp": time.time()
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
    
    async def start_stats_broadcast(self):
        """Inicia el broadcast periódico de estadísticas del sistema"""
        while True:
            try:
                await self.send_system_stats()
                await asyncio.sleep(5)  # Enviar cada 5 segundos
            except Exception as e:
                logger.error(f"Error en broadcast de stats: {e}")
                await asyncio.sleep(5)
    
    async def shutdown_system(self):
        """Apaga el sistema Aura"""
        try:
            logger.info("Apagando sistema Aura...")
            
            # Detener reconocimiento
            if self.is_listening:
                await self.stop_listening()
            
            # Limpiar cliente Aura
            if self.aura_client:
                await self.aura_client.cleanup()
                self.aura_client = None
            
            # Limpiar sintetizador
            if self.voice_synthesizer:
                self.voice_synthesizer.cleanup()
            
            await self.broadcast({
                "type": "shutdown_complete",
                "message": "Sistema apagado correctamente"
            })
            
        except Exception as e:
            logger.error(f"Error apagando sistema: {e}")
    
    def _get_mcp_config(self) -> Dict[str, Any]:
        """Obtiene la configuración completa de MCP con todas las herramientas"""
        logger.info("🔧 Configurando MCP (Model Context Protocol)")
        logger.info("🚀 Activando todas las herramientas: Filesystem + Brave Search + Obsidian Memory")
        
        # Configurar todos los MCPs disponibles
        filesystem_config = self._get_filesystem_config()
        brave_config = self._get_brave_search_config()
        obsidian_config = self._get_obsidian_memory_config()
        mcp_config = {**filesystem_config, **brave_config, **obsidian_config}
        
        return mcp_config
    
    def _get_filesystem_config(self) -> Dict[str, Any]:
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
            ("/home/ary/Documents/Ary Vault", "Obsidian Vault")
        ]
        
        # Filtrar solo directorios que existen
        allowed_dirs = []
        for dir_path, description in possible_dirs:
            if os.path.exists(dir_path):
                allowed_dirs.append(dir_path)
                logger.info(f"📁 Directorio detectado: {description} ({dir_path})")
        
        if not allowed_dirs:
            logger.warning("⚠️  No se encontraron directorios para MCP filesystem")
            return {}
        
        logger.info(f"✅ {len(allowed_dirs)} directorios configurados para acceso MCP")
        
        # Guardar para que el cliente pueda añadirlos al prompt de sistema más tarde
        self.allowed_dirs = allowed_dirs
        
        return {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_dirs,
                "transport": "stdio"
            }
        }
    
    def _get_brave_search_config(self) -> Dict[str, Any]:
        """Obtiene la configuración del MCP Brave Search"""
        logger.info("🔍 Configurando Brave Search...")
        
        brave_api_key = os.getenv("BRAVE_API_KEY")
        if not brave_api_key:
            logger.warning("❌ BRAVE_API_KEY no encontrada en las variables de entorno")
            return {}
        
        logger.info("✅ Usando API key desde variables de entorno")
        
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
    
    def _get_obsidian_memory_config(self) -> Dict[str, Any]:
        """Obtiene la configuración del MCP Obsidian Memory"""
        logger.info("🗃️ Configurando Obsidian Memory...")
        
        # Verificar que el vault existe
        vault_path = "/home/ary/Documents/Ary Vault"
        if not os.path.exists(vault_path):
            logger.warning(f"❌ El vault de Obsidian no existe en: {vault_path}")
            logger.info("💡 Verifica la ruta del vault en el archivo obsidian_memory_server.js")
            return {}
        
        # Verificar que el servidor MCP existe
        server_path = "./mcp/obsidian_memory_server.js"
        if not os.path.exists(server_path):
            logger.warning(f"❌ El servidor MCP no existe en: {server_path}")
            logger.info("💡 Asegúrate de que el archivo obsidian_memory_server.js está en el directorio actual")
            return {}
        
        logger.info(f"✅ Vault detectado: {vault_path}")
        logger.info(f"✅ Servidor MCP disponible: {server_path}")
        
        return {
            "obsidian-memory": {
                "command": "node",
                "args": [server_path],
                "transport": "stdio"
            }
        }
    
    async def handle_client(self, websocket):
        """Maneja la conexión de un cliente WebSocket"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error en cliente WebSocket: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Inicia el servidor WebSocket"""
        logger.info(f"Iniciando servidor WebSocket en {self.host}:{self.port}")
        
        # Almacenar el loop principal para uso en hilos
        self.main_loop = asyncio.get_running_loop()
        
        # Iniciar broadcast de estadísticas
        stats_task = asyncio.create_task(self.start_stats_broadcast())
        
        # Iniciar servidor WebSocket
        try:
            async with websockets.serve(
                self.handle_client, 
                self.host, 
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ):
                logger.info(f"✅ Servidor WebSocket iniciado en ws://{self.host}:{self.port}")
                logger.info("🚀 Listo para recibir conexiones del frontend")
                
                # Mantener el servidor corriendo indefinidamente
                try:
                    await asyncio.Event().wait()  # Más robusto que Future()
                except asyncio.CancelledError:
                    logger.info("Servidor cancelado")
                
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.error(f"❌ Puerto {self.port} ya está en uso")
                logger.info("💡 Intenta con: kill -9 $(lsof -ti:8766)")
            else:
                logger.error(f"❌ Error de red: {e}")
            raise
        except KeyboardInterrupt:
            logger.info("Cerrando servidor...")
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            raise
        finally:
            stats_task.cancel()
            await self.shutdown_system()

async def main():
    """Función principal"""
    server = AuraWebSocketServer()
    await server.start_server()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()