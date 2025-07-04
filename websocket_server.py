#!/usr/bin/env python3
"""
Servidor WebSocket para conectar la interfaz web con Aura
"""

import asyncio
import websockets
import json
import logging
import sys
import os
from datetime import datetime

# Importar módulos de Aura
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from engine.voice.hear import initialize_recognizer, listen_for_command
from engine.voice.speak import speak, StreamingTTS, get_synthesizer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuraWebSocketHandler:
    def __init__(self):
        self.voice_recognizer = None
        self.voice_synthesizer = None
        self.aura_client = None
        self.clients = set()
        self.is_listening = False
        
    def initialize_voice(self):
        """Inicializa los componentes de voz"""
        try:
            self.voice_recognizer = initialize_recognizer()
            self.voice_synthesizer = get_synthesizer()
            if self.voice_synthesizer:
                self.voice_synthesizer.initialized = True
            logger.info("✅ Sistema de voz inicializado")
            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando voz: {e}")
            return False
    
    async def handle_client(self, websocket, path=None):
        """Maneja la conexión de un cliente WebSocket"""
        self.clients.add(websocket)
        logger.info(f"🔌 Cliente conectado: {websocket.remote_address}")
        
        try:
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "Conectado al servidor Aura"
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
        finally:
            self.clients.remove(websocket)
    
    async def process_message(self, websocket, data):
        """Procesa los mensajes del cliente"""
        msg_type = data.get("type")
        
        if msg_type == "init_voice":
            # Inicializar componentes de voz si no están inicializados
            if not self.voice_recognizer or not self.voice_synthesizer:
                if self.initialize_voice():
                    await websocket.send(json.dumps({
                        "type": "voice_ready",
                        "message": "Sistema de voz inicializado"
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Error inicializando sistema de voz"
                    }))
            else:
                await websocket.send(json.dumps({
                    "type": "voice_ready",
                    "message": "Sistema de voz ya estaba inicializado"
                }))
            return
            
        elif msg_type == "init_aura":
            # Inicializar cliente Aura con el modelo especificado
            model_type = data.get("model_type", "gemini")
            model_name = data.get("model_name", "gemini-2.0-flash-exp")
            
            try:
                from client import AuraClient
                self.aura_client = AuraClient(
                    model_type=model_type,
                    model_name=model_name,
                    enable_voice=True
                )
                await websocket.send(json.dumps({
                    "type": "aura_ready",
                    "message": f"Cliente Aura inicializado con {model_type} ({model_name})"
                }))
            except Exception as e:
                logger.error(f"Error inicializando Aura: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Error inicializando Aura: {str(e)}"
                }))
            return
            
        elif msg_type == "start_listening":
            await self.start_listening(websocket)
        elif msg_type == "stop_listening":
            await self.stop_listening(websocket)
        elif msg_type == "speak":
            text = data.get("text", "")
            await self.speak_text(websocket, text)
        elif msg_type == "ping":
            await websocket.send(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Tipo de mensaje desconocido: {msg_type}"
            }))
    
    async def start_listening(self, websocket):
        """Inicia el reconocimiento de voz"""
        if self.is_listening:
            await websocket.send(json.dumps({
                "type": "status",
                "listening": True,
                "message": "Ya estoy escuchando"
            }))
            return
            
        if not self.voice_recognizer:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Reconocimiento de voz no disponible"
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
                
                # Procesar con Aura si está disponible
                if self.aura_client:
                    await websocket.send(json.dumps({
                        "type": "status",
                        "message": "Procesando texto reconocido con Aura...",
                        "streaming": True
                    }))
                    
                    try:
                        # Procesar con Aura en un thread separado para evitar bloqueo
                        response = await loop.run_in_executor(
                            None,
                            lambda: self.aura_client.chat_with_voice(text)
                        )
                        
                        # Enviar respuesta final
                        await websocket.send(json.dumps({
                            "type": "aura_response",
                            "response": response,
                            "timestamp": datetime.now().isoformat(),
                            "streaming": False
                        }))
                        
                    except Exception as e:
                        logger.error(f"Error procesando con Aura: {e}")
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Error procesando texto: {str(e)}"
                        }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Cliente Aura no inicializado"
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
                "streaming": False,
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
            
        if not self.voice_synthesizer:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Síntesis de voz no disponible"
            }))
            return
        
        try:
            # Notificar que empezó a hablar
            await websocket.send(json.dumps({
                "type": "status",
                "speaking": True,
                "message": "Hablando..."
            }))
            
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
    """Función principal del servidor WebSocket"""
    handler = AuraWebSocketHandler()
    
    # Inicializar componentes de voz
    if handler.initialize_voice():
        logger.info("✅ Componentes de voz listos")
    else:
        logger.warning("⚠️  Ejecutando sin capacidades de voz")
    
    # Iniciar servidor WebSocket
    host = "localhost"
    port = 8765
    
    logger.info(f"🚀 Servidor WebSocket iniciado en ws://{host}:{port}")
    logger.info("📡 Esperando conexiones...")
    
    async with websockets.serve(handler.handle_client, host, port):
        await asyncio.Future()  # Ejecutar para siempre

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Servidor detenido") 