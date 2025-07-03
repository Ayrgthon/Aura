#!/usr/bin/env python3
"""
Servidor WebSocket integrado con Aura - Procesamiento completo
"""

import asyncio
import websockets
import json
import logging
import sys
import os
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

# Agregar el directorio actual al path para importar client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedAuraWebSocketHandler:
    def __init__(self):
        self.voice_recognizer = None
        self.voice_synthesizer = None
        self.clients = set()
        self.is_listening = False
        self.voice_initialized = False
        self.aura_client = None
        self.aura_initialized = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._main_loop = None  # Se configurará cuando se inicie el servidor
        
    def set_event_loop(self, loop):
        """Configura el event loop principal"""
        self._main_loop = loop
        
    def initialize_voice_lazy(self):
        """Inicializa los componentes de voz bajo demanda"""
        if self.voice_initialized:
            return True
            
        try:
            logger.info("Cargando módulos de voz...")
            from engine.voice.hear import initialize_recognizer
            from engine.voice.speak import get_synthesizer
            
            logger.info("Inicializando reconocimiento de voz...")
            self.voice_recognizer = initialize_recognizer()
            
            logger.info("Inicializando síntesis de voz...")
            self.voice_synthesizer = get_synthesizer()
            
            if self.voice_synthesizer:
                self.voice_synthesizer.initialized = True
                
            self.voice_initialized = True
            logger.info("✅ Sistema de voz inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando voz: {e}")
            return False
    
    async def initialize_aura_client(self, model_type="gemini", model_name="gemini-2.0-flash-exp"):
        """Inicializa el cliente Aura de forma asíncrona"""
        # Si ya está inicializado con el mismo modelo, no hacer nada
        if (self.aura_initialized and 
            hasattr(self, 'current_model_type') and hasattr(self, 'current_model_name') and
            self.current_model_type == model_type and self.current_model_name == model_name):
            return True
        
        # Si ya estaba inicializado, cerrarlo primero
        if self.aura_initialized:
            self.aura_initialized = False
            self.aura_client = None
            
        try:
            logger.info(f"Inicializando cliente Aura con {model_type}: {model_name}...")
            from client import AuraClient
            
            # Configuración de MCP
            mcp_config = {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", os.path.expanduser("~")],
                    "transport": "stdio"
                },
                "brave-search": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                    "transport": "stdio",
                    "env": {
                        "BRAVE_API_KEY": "YOUR_BRAVE_API_KEY_HERE"
                    }
                }
            }
            
            def create_client():
                return AuraClient(
                    model_type=model_type,
                    model_name=model_name,
                    enable_voice=True
                )
            
            # Crear cliente en thread separado
            self.aura_client = await self._main_loop.run_in_executor(self.executor, create_client)
            
            # Configurar MCP
            success = await self.aura_client.setup_mcp_servers(mcp_config)
            if not success:
                logger.warning("⚠️ No se pudo configurar MCP, continuando sin herramientas adicionales")
            
            # Guardar configuración actual
            self.current_model_type = model_type
            self.current_model_name = model_name
            self.aura_initialized = True
            logger.info(f"✅ Cliente Aura inicializado correctamente con {model_type}: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente Aura: {e}")
            return False
    
    async def handle_client(self, websocket):
        """Maneja la conexión de un cliente WebSocket"""
        self.clients.add(websocket)
        logger.info(f"🔌 Cliente conectado desde: {websocket.remote_address}")
        
        try:
            # Enviar confirmación de conexión inmediatamente
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "Conectado al servidor Aura",
                "voice_ready": self.voice_initialized,
                "aura_ready": self.aura_initialized
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Formato de mensaje inválido"
                    }))
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Cliente desconectado: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error en conexión: {e}")
        finally:
            self.clients.remove(websocket)
    
    async def process_message(self, websocket, data):
        """Procesa los mensajes del cliente"""
        msg_type = data.get("type")
        
        if msg_type == "start_listening":
            await self.start_listening(websocket)
        elif msg_type == "stop_listening":
            await self.stop_listening(websocket)
        elif msg_type == "speak":
            text = data.get("text", "")
            await self.speak_text(websocket, text)
        elif msg_type == "ping":
            await websocket.send(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat(),
                "voice_ready": self.voice_initialized,
                "aura_ready": self.aura_initialized
            }))
        elif msg_type == "init_voice":
            await self.init_voice_on_demand(websocket)
        elif msg_type == "init_aura":
            model_type = data.get("model_type", "gemini")
            model_name = data.get("model_name", "gemini-2.0-flash-exp")
            await self.init_aura_on_demand(websocket, model_type, model_name)
        elif msg_type == "process_text":
            text = data.get("text", "")
            await self.process_with_aura(websocket, text)
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Tipo de mensaje desconocido: {msg_type}"
            }))
    
    async def init_voice_on_demand(self, websocket):
        """Inicializa la voz bajo demanda"""
        await websocket.send(json.dumps({
            "type": "status",
            "message": "Inicializando sistema de voz..."
        }))
        
        def init_voice_thread():
            try:
                return self.initialize_voice_lazy()
            except Exception as e:
                logger.error(f"Error en thread de voz: {e}")
                return False
        
        # Ejecutar en thread separado
        success = await self._main_loop.run_in_executor(self.executor, init_voice_thread)
        
        if success:
            await websocket.send(json.dumps({
                "type": "voice_ready",
                "message": "Sistema de voz listo"
            }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "No se pudo inicializar el sistema de voz"
            }))
    
    async def init_aura_on_demand(self, websocket, model_type="gemini", model_name="gemini-2.0-flash-exp"):
        """Inicializa el cliente Aura bajo demanda"""
        await websocket.send(json.dumps({
            "type": "status",
            "message": f"Inicializando cliente Aura con {model_type}: {model_name}..."
        }))
        
        success = await self.initialize_aura_client(model_type, model_name)
        
        if success:
            await websocket.send(json.dumps({
                "type": "aura_ready",
                "message": f"Cliente Aura listo con {model_type}: {model_name}"
            }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"No se pudo inicializar el cliente Aura con {model_type}: {model_name}"
            }))
    
    async def process_with_aura(self, websocket, text):
        """Procesa texto usando el cliente Aura"""
        if not self.aura_initialized or not self.aura_client:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Cliente Aura no inicializado. Envía 'init_aura' primero."
            }))
            return
        
        if not text:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "No hay texto para procesar"
            }))
            return
        
        try:
            await websocket.send(json.dumps({
                "type": "status",
                "message": f"Procesando: '{text}'"
            }))
            
            # Procesar con Aura
            response = await self.aura_client.chat_with_voice(text)
            
            # Asegurar que response es string
            response_str = str(response) if response else "Sin respuesta"
            
            # Enviar respuesta
            await websocket.send(json.dumps({
                "type": "aura_response",
                "user_text": text,
                "response": response_str,
                "timestamp": datetime.now().isoformat()
            }))
            
            # Sintetizar respuesta automáticamente
            if self.voice_initialized and response_str:
                await self.speak_text(websocket, response_str)
            
        except Exception as e:
            logger.error(f"Error procesando con Aura: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Error procesando texto: {str(e)}"
            }))
    
    async def start_listening(self, websocket):
        """Inicia el reconocimiento de voz"""
        if not self.voice_initialized:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Sistema de voz no inicializado. Envía 'init_voice' primero."
            }))
            return
            
        if self.is_listening:
            await websocket.send(json.dumps({
                "type": "status",
                "listening": True,
                "message": "Ya estoy escuchando"
            }))
            return
        
        self.is_listening = True
        
        # Notificar que empezó a escuchar
        await websocket.send(json.dumps({
            "type": "status",
            "listening": True,
            "message": "Escuchando..."
        }))
        
        # Ejecutar reconocimiento de voz en un thread separado
        try:
            loop = asyncio.get_event_loop()
            
            # Importar aquí para evitar carga inicial
            from engine.voice.hear import listen_for_command
            
            text = await loop.run_in_executor(
                None, 
                listen_for_command, 
                self.voice_recognizer, 
                10  # timeout de 10 segundos
            )
            
            if text:
                # Enviar el texto reconocido
                await websocket.send(json.dumps({
                    "type": "speech_recognized",
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                }))
                logger.info(f"🎤 Texto reconocido: {text}")
                
                # Procesar automáticamente con Aura si está disponible
                if self.aura_initialized:
                    await websocket.send(json.dumps({
                        "type": "status",
                        "message": "Procesando texto reconocido con Aura..."
                    }))
                    await self.process_with_aura(websocket, text)
                else:
                    await websocket.send(json.dumps({
                        "type": "info",
                        "message": "Texto reconocido. Cliente Aura no inicializado."
                    }))
            else:
                await websocket.send(json.dumps({
                    "type": "status",
                    "message": "No se detectó voz clara"
                }))
                
        except Exception as e:
            logger.error(f"Error en reconocimiento de voz: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Error en reconocimiento: {str(e)}"
            }))
        finally:
            self.is_listening = False
            await websocket.send(json.dumps({
                "type": "status",
                "listening": False,
                "message": "Reconocimiento finalizado"
            }))
    
    async def stop_listening(self, websocket):
        """Detiene el reconocimiento de voz"""
        self.is_listening = False
        await websocket.send(json.dumps({
            "type": "status",
            "listening": False,
            "message": "Escucha detenida"
        }))
    
    async def speak_text(self, websocket, text):
        """Sintetiza y reproduce texto"""
        if not text:
            return
            
        if not self.voice_initialized:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Sistema de voz no inicializado"
            }))
            return
        
        try:
            # Notificar que empezó a hablar
            await websocket.send(json.dumps({
                "type": "status",
                "speaking": True,
                "message": "Hablando..."
            }))
            
            # Importar aquí para evitar carga inicial
            from engine.voice.speak import speak
            
            # Sintetizar en thread separado
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, speak, text)
            
            # Notificar que terminó
            await websocket.send(json.dumps({
                "type": "status",
                "speaking": False,
                "message": "Síntesis completada"
            }))
            
        except Exception as e:
            logger.error(f"Error en síntesis de voz: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Error en síntesis: {str(e)}"
            }))

async def main():
    """Función principal del servidor WebSocket integrado"""
    # Crear el handler
    handler = IntegratedAuraWebSocketHandler()
    
    # Configurar el event loop principal
    handler.set_event_loop(asyncio.get_event_loop())
    
    # Iniciar servidor WebSocket
    host = "localhost"
    port = 8765
    
    logger.info(f"🚀 Servidor WebSocket INTEGRADO iniciado en ws://{host}:{port}")
    logger.info("📡 Listo para conexiones (voz y Aura se cargan bajo demanda)")
    
    async with websockets.serve(handler.handle_client, host, port):
        await asyncio.Future()  # Ejecutar para siempre

if __name__ == "__main__":
    try:
        # Asegurarse de que no haya otros procesos usando el puerto
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 8765))
        sock.close()
        
        # Ejecutar el servidor
        asyncio.run(main())
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.error("❌ El puerto 8765 ya está en uso. Asegúrate de que no haya otra instancia ejecutándose.")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n👋 Servidor detenido") 