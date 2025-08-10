#!/usr/bin/env python3
"""
Nuevo Servidor WebSocket Aura - Integración con Cliente Refactorizado
- Integra client/gemini_client.py con Sequential Thinking
- Buffer TTS para reasoning secuencial 
- WebRTC para audio en tiempo real
- Sistema anti-feedback mejorado
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
import queue
import uuid
from typing import Dict, Any, Optional, Set, List
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# Importar WebRTC y audio
try:
    import aiortc
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaRecorder, MediaPlayer
    WEBRTC_AVAILABLE = True
except ImportError:
    print("⚠️ WebRTC no disponible. Instala con: pip install aiortc")
    WEBRTC_AVAILABLE = False

# Agregar paths necesarios
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice'))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client'))

# Importar módulos de voz
from hear import SpeechToText
from speak import TextToSpeech

# Importar el nuevo cliente Gemini
from gemini_client import SimpleGeminiClient
from config import get_mcp_servers_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'aura_websocket.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TTSQueueItem:
    """Item del buffer TTS"""
    id: str
    content: str
    item_type: str  # 'thought', 'response', 'system'
    thought_number: Optional[int] = None
    total_thoughts: Optional[int] = None
    priority: int = 0  # 0 = alta prioridad
    speed_multiplier: float = 1.0  # Multiplicador de velocidad para este item

class TTSBuffer:
    """Buffer para reproducción secuencial de TTS"""
    
    def __init__(self, tts_instance: TextToSpeech):
        self.tts = tts_instance
        self.queue = asyncio.Queue()
        self.is_playing = False
        self.current_item = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.processing_task = None
        self.should_stop = False  # Flag para interrupción
        self.current_thread = None  # Referencia al hilo actual de TTS
        self.played_items = []  # Lista de items reproducidos completamente
        
    def get_completed_context(self) -> List[str]:
        """Obtiene el contexto de lo que realmente se reprodujo completamente"""
        context = []
        for item in self.played_items:
            if item.item_type == 'thought':
                context.append(f"Pensamiento {item.thought_number}: {item.content}")
            elif item.item_type == 'response':
                context.append(f"Respuesta: {item.content}")
        return context
    
    def clear_played_history(self):
        """Limpia el historial de items reproducidos"""
        self.played_items.clear()
        logger.info("🧹 Historial de reproducciones limpiado")
        
    async def add_item(self, item: TTSQueueItem):
        """Añade item al buffer"""
        await self.queue.put(item)
        logger.info(f"🔊 Item añadido al buffer TTS: {item.item_type} - '{item.content[:50]}...'")
        
        # Iniciar procesamiento si no está activo
        if not self.processing_task or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_queue())
    
    async def _process_queue(self):
        """Procesa la cola TTS secuencialmente"""
        while True:
            try:
                # Esperar siguiente item
                item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Verificar si debe parar antes de procesar
                if self.should_stop:
                    break
                
                self.is_playing = True
                self.current_item = item
                
                logger.info(f"🎵 Reproduciendo: {item.item_type} - {item.content[:50]}... (velocidad: {item.speed_multiplier}x)")
                
                # Ejecutar TTS en hilo separado con velocidad específica
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self._speak_with_speed,
                    item.content,
                    item.speed_multiplier
                )
                
                # Solo marcar como completado si no fue interrumpido
                if not self.should_stop:
                    logger.info(f"✅ Completado: {item.item_type}")
                    # Guardar item completado para tracking del contexto
                    self.played_items.append(item)
                else:
                    logger.info(f"🔇 Interrumpido: {item.item_type}")
                    break
                
                self.current_item = None
                self.queue.task_done()
                
            except asyncio.TimeoutError:
                # No hay más items, pausar procesamiento
                self.is_playing = False
                break
            except asyncio.CancelledError:
                logger.info("🔇 Tarea de TTS cancelada")
                self.is_playing = False
                break
            except Exception as e:
                logger.error(f"❌ Error en TTS buffer: {e}")
                self.is_playing = False
                
    def _speak_with_speed(self, text: str, speed_multiplier: float):
        """Habla con velocidad específica usando edge-tts"""
        if speed_multiplier != 1.0:
            # Calcular rate para edge-tts (formato: "+50%" o "-20%")
            if speed_multiplier >= 2.0:
                rate_percent = "+100%"  # Muy rápido
            elif speed_multiplier >= 1.8:
                rate_percent = "+80%"   # Rápido
            elif speed_multiplier >= 1.5:
                rate_percent = "+50%"   # Medio-rápido
            elif speed_multiplier >= 1.2:
                rate_percent = "+30%"   # Un poco más rápido
            else:
                rate_percent = "+0%"    # Normal
            
            # Usar el método speak_with_rate personalizado
            self._speak_edge_tts_with_rate(text, rate_percent)
        else:
            # Velocidad normal
            self.tts.speak(text)
    
    def _speak_edge_tts_with_rate(self, text: str, rate: str):
        """Método personalizado e interrumpible para hablar con rate específico"""
        import edge_tts
        import pygame
        import tempfile
        import asyncio
        import threading
        import os
        
        def run_edge_tts():
            try:
                # Verificar si debe parar antes de empezar
                if self.should_stop:
                    return
                
                async def _edge_speak():
                    communicate = edge_tts.Communicate(text, self.tts.voice, rate=rate)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                        await communicate.save(fp.name)
                        return fp.name
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_file = loop.run_until_complete(_edge_speak())
                loop.close()
                
                # Verificar si debe parar antes de reproducir
                if self.should_stop:
                    os.unlink(audio_file)
                    return
                
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                # Loop interrumpible
                while pygame.mixer.music.get_busy() and not self.should_stop:
                    pygame.time.wait(50)  # Check más frecuente
                
                # Si fue interrumpido, parar inmediatamente
                if self.should_stop:
                    pygame.mixer.music.stop()
                    
                os.unlink(audio_file)
                
            except Exception as e:
                logger.error(f"Error en TTS interrumpible: {e}")
        
        thread = threading.Thread(target=run_edge_tts)
        self.current_thread = thread  # Guardar referencia
        thread.start()
        thread.join()
    
    def clear_queue(self):
        """Limpia la cola TTS y detiene reproducción actual agresivamente"""
        logger.info("🛑 INTERRUPCIÓN TOTAL DE TTS - Parando todo")
        
        # 1. Activar flag de parada
        self.should_stop = True
        
        # 2. Detener pygame inmediatamente
        try:
            import pygame
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                logger.info("🔇 Pygame mixer detenido")
        except Exception as e:
            logger.debug(f"Error deteniendo pygame: {e}")
        
        # 3. Crear nueva cola (limpia pendientes)
        old_queue = self.queue
        self.queue = asyncio.Queue()
        
        # 4. Marcar como no reproduciendo
        self.is_playing = False
        
        # 5. Guardar último item reproducido para contexto
        if self.current_item:
            # Solo guardar si se completó (no interrumpido a medias)
            if not self.should_stop:
                self.played_items.append(self.current_item)
            self.current_item = None
        
        # 6. Cancelar tarea de procesamiento si existe
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
        
        # 7. Resetear flag para próximas reproducciones
        self.should_stop = False
        
        logger.info("🧹 Buffer TTS COMPLETAMENTE limpiado con interrupción total")
        
    def get_status(self) -> Dict[str, Any]:
        """Estado actual del buffer"""
        return {
            'is_playing': self.is_playing,
            'queue_size': self.queue.qsize(),
            'current_item': {
                'type': self.current_item.item_type,
                'content': self.current_item.content[:50] + '...'
            } if self.current_item else None
        }

class OptimizedAudioTrack(MediaStreamTrack):
    """Track de audio optimizado para WebRTC"""
    
    kind = "audio"
    
    def __init__(self, stt_instance: SpeechToText):
        super().__init__()
        self.stt = stt_instance
        self.audio_queue = queue.Queue()
        
    async def recv(self):
        """Recibe frames de audio desde WebRTC"""
        frame = await super().recv()
        
        # Procesar con STT si está disponible
        if self.stt and hasattr(frame, 'to_ndarray'):
            audio_data = frame.to_ndarray()
            self.audio_queue.put(audio_data)
        
        return frame

class AuraWebSocketServer:
    """Servidor WebSocket Aura con Cliente Refactorizado"""
    
    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.clients: Dict[str, Dict[str, Any]] = {}
        
        # Sistema de audio
        self.stt: Optional[SpeechToText] = None
        self.tts: Optional[TextToSpeech] = None
        self.tts_buffer: Optional[TTSBuffer] = None
        self.voice_language = "es"
        self.voice_initialized = False
        
        # Cliente Gemini refactorizado
        self.gemini_client: Optional[SimpleGeminiClient] = None
        self.aura_ready = False
        self.model_name = "gemini-2.5-flash"
        
        # Sistema anti-feedback
        self.is_speaking = False
        self.is_listening = False
        self.speaking_lock = asyncio.Lock()
        self.listening_lock = asyncio.Lock()
        
        # Protección contra concurrencia
        self.client_processing_locks: Dict[str, asyncio.Lock] = {}
        self.audio_processing_lock = threading.Lock()
        
        # Pool de hilos y tareas
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.processing_tasks: Set[asyncio.Task] = set()
        
        # WebRTC
        self.rtc_connections: Dict[str, RTCPeerConnection] = {}
        
        # Control de sistema
        self.system_on = True
        
        # Contexto limitado por TTS
        self.last_complete_response = None  # Último response completamente reproducido
        self.pending_context = []  # Contexto generado pero no reproducido
        
        logger.info(f"🚀 Servidor Aura WebSocket inicializado en {host}:{port}")
    
    async def register_client(self, websocket, client_id: str = None):
        """Registra cliente con UUID único"""
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Crear lock específico para este cliente
        self.client_processing_locks[client_id] = asyncio.Lock()
        
        self.clients[client_id] = {
            'websocket': websocket,
            'connected_at': time.time(),
            'voice_ready': False,
            'aura_ready': False,
            'listening': False,
            'processing': False,
            'audio_buffer': ""
        }
        
        logger.info(f"👤 Cliente registrado: {client_id}")
        
        # Enviar mensaje de bienvenida
        await self.send_to_client(client_id, {
            'type': 'connection',
            'message': 'Conectado al servidor Aura refactorizado',
            'client_id': client_id,
            'webrtc_available': WEBRTC_AVAILABLE,
            'timestamp': time.time()
        })
        
        return client_id
    
    async def unregister_client(self, client_id: str):
        """Desregistra cliente y limpia recursos"""
        if client_id in self.clients:
            # Limpiar conexión WebRTC
            if client_id in self.rtc_connections:
                await self.rtc_connections[client_id].close()
                del self.rtc_connections[client_id]
            
            # Limpiar lock del cliente
            if client_id in self.client_processing_locks:
                del self.client_processing_locks[client_id]
            
            del self.clients[client_id]
            logger.info(f"👋 Cliente desregistrado: {client_id}")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Envío a cliente específico"""
        if client_id not in self.clients:
            logger.error(f"❌ Cliente {client_id} no existe")
            return False
        
        try:
            websocket = self.clients[client_id]['websocket']
            await websocket.send(json.dumps(message))
            logger.debug(f"📤 Enviado a {client_id}: {message.get('type', 'unknown')}")
            return True
        except (ConnectionClosed, WebSocketException) as e:
            logger.warning(f"❌ Error enviando a {client_id}: {e}")
            await self.unregister_client(client_id)
            return False
    
    async def broadcast_message(self, message: Dict[str, Any], exclude_client: str = None):
        """Broadcast a todos los clientes"""
        if not self.clients:
            return
        
        tasks = []
        for client_id in list(self.clients.keys()):
            if client_id == exclude_client:
                continue
            tasks.append(self.send_to_client(client_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def init_voice_system(self):
        """Inicializar sistema de voz"""
        try:
            logger.info("🎤 Inicializando sistema de voz...")
            
            # Inicializar STT
            loop = asyncio.get_event_loop()
            self.stt = await loop.run_in_executor(
                self.executor, 
                lambda: SpeechToText(language=self.voice_language)
            )
            
            # Inicializar TTS
            if self.voice_language == "es":
                self.tts = TextToSpeech(voice="en-US-EmmaMultilingualNeural")
            else:
                self.tts = TextToSpeech(voice="en-US-AndrewMultilingualNeural")
            
            # Inicializar buffer TTS
            self.tts_buffer = TTSBuffer(self.tts)
            
            self.voice_initialized = True
            logger.info("✅ Sistema de voz inicializado")
            
            await self.broadcast_message({
                'type': 'voice_ready',
                'message': 'Sistema de voz listo',
                'language': self.voice_language,
                'webrtc_available': WEBRTC_AVAILABLE
            })
            
        except Exception as e:
            logger.error(f"❌ Error inicializando voz: {e}")
            await self.broadcast_message({
                'type': 'error',
                'message': f'Error inicializando voz: {str(e)}'
            })
    
    async def init_aura_client(self, model_name: str = None):
        """Inicializar cliente Aura refactorizado"""
        try:
            if model_name:
                self.model_name = model_name
            
            # Limpiar cliente anterior si existe
            if self.gemini_client:
                try:
                    await self.gemini_client.cleanup()
                except Exception as e:
                    logger.warning(f"⚠️ Error limpiando cliente anterior: {e}")
                finally:
                    self.gemini_client = None
                
            logger.info(f"🤖 Inicializando cliente Aura: {self.model_name}")
            
            # Inicializar cliente Gemini
            loop = asyncio.get_event_loop()
            self.gemini_client = await loop.run_in_executor(
                self.executor,
                lambda: SimpleGeminiClient(model_name=self.model_name, debug=True)
            )
            
            # Configurar servidores MCP
            mcp_config = get_mcp_servers_config()
            if mcp_config:
                success = await self.gemini_client.setup_mcp_servers(mcp_config)
                if success:
                    logger.info(f"✅ MCP configurado: {len(mcp_config)} servidores")
                else:
                    logger.warning("⚠️ Algunos servidores MCP fallaron")
            
            self.aura_ready = True
            logger.info("✅ Cliente Aura refactorizado listo")
            
            await self.broadcast_message({
                'type': 'aura_ready',
                'message': 'Cliente Aura refactorizado listo',
                'model_name': self.model_name,
                'tools_available': len(self.gemini_client.get_available_tools()) if self.gemini_client else 0
            })
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Aura: {e}")
            self.aura_ready = False
            await self.broadcast_message({
                'type': 'error',
                'message': f'Error inicializando Aura: {str(e)}'
            })
    
    async def start_listening(self, client_id: str):
        """Iniciar escucha de voz - INTERRUMPE TTS INMEDIATAMENTE"""
        logger.info(f"🎤 Iniciando escucha para {client_id}")
        
        # 🛑 INTERRUPCIÓN INMEDIATA - En cuanto el usuario habla, para todo
        if self.tts_buffer:
            self.tts_buffer.clear_queue()
            self._update_conversation_context()
            logger.info("🔇 TTS interrumpido por nueva voz del usuario")
        
        async with self.listening_lock:
            if self.is_listening:
                logger.warning("Ya está escuchando")
                return False
            
            if not self.stt or not self.voice_initialized:
                logger.error("Sistema de voz no inicializado")
                return False
            
            # Ya no verificamos is_speaking porque lo interrumpimos arriba
            self.is_speaking = False  # Forzar como no hablando
            
            self.is_listening = True
            if client_id in self.clients:
                self.clients[client_id]['listening'] = True
                self.clients[client_id]['audio_buffer'] = ""
            
            # Crear tarea de escucha
            task = asyncio.create_task(self._listen_and_accumulate(client_id))
            self.processing_tasks.add(task)
            task.add_done_callback(self.processing_tasks.discard)
            
            await self.send_to_client(client_id, {
                'type': 'status',
                'listening': True,
                'message': 'Escucha iniciada - habla ahora'
            })
            
            return True
    
    async def stop_listening(self, client_id: str):
        """Detener escucha y procesar texto"""
        logger.info(f"🛑 Deteniendo escucha para {client_id}")
        
        async with self.listening_lock:
            if not self.is_listening:
                logger.warning("No estaba escuchando")
                return False
            
            self.is_listening = False
            if client_id in self.clients:
                self.clients[client_id]['listening'] = False
            
            await self.send_to_client(client_id, {
                'type': 'status',
                'listening': False,
                'message': 'Escucha detenida - procesando...'
            })
            
        # Esperar texto acumulado
        max_wait = 3
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(0.1)
            waited += 0.1
            
            if client_id in self.clients and 'audio_buffer' in self.clients[client_id]:
                accumulated_text = self.clients[client_id]['audio_buffer'].strip()
                if accumulated_text:
                    logger.info(f"📝 Texto obtenido: '{accumulated_text}'")
                    
                    # Enviar texto reconocido
                    await self.send_to_client(client_id, {
                        'type': 'speech_recognized',
                        'text': accumulated_text,
                        'timestamp': time.time()
                    })
                    
                    # Procesar con Aura
                    asyncio.create_task(self._process_with_aura(client_id, accumulated_text))
                    return True
        
        # Sin texto detectado
        await self.send_to_client(client_id, {
            'type': 'no_speech_detected',
            'message': 'No se detectó voz'
        })
        
        return False
    
    async def _listen_and_accumulate(self, client_id: str):
        """Escucha y acumula texto"""
        if not self.stt:
            logger.error("STT no disponible")
            return
        
        logger.info(f"🎤 Iniciando acumulación para {client_id}")
        
        try:
            with self.audio_processing_lock:
                self.stt.start_listening()
                
            accumulated_text_parts = []
            
            while self.is_listening and not self.is_speaking:
                try:
                    with self.audio_processing_lock:
                        loop = asyncio.get_event_loop()
                        data = await loop.run_in_executor(
                            self.executor,
                            lambda: self.stt.stream.read(4000, exception_on_overflow=False)
                        )
                        
                        if len(data) == 0:
                            await asyncio.sleep(0.01)
                            continue
                        
                        final_result = self.stt.rec.AcceptWaveform(data)
                    
                    if final_result:
                        with self.audio_processing_lock:
                            result = json.loads(self.stt.rec.Result())
                        
                        text_chunk = result.get('text', '').strip()
                        
                        if text_chunk:
                            logger.info(f"🗣️ Chunk reconocido: '{text_chunk}'")
                            accumulated_text_parts.append(text_chunk)
                            
                            # Guardar en buffer del cliente
                            current_accumulated = " ".join(accumulated_text_parts)
                            if client_id in self.clients:
                                self.clients[client_id]['audio_buffer'] = current_accumulated
                            
                            # Mostrar transcripción parcial
                            await self.send_to_client(client_id, {
                                'type': 'speech_partial_accumulated',
                                'text': current_accumulated,
                                'chunk': text_chunk,
                                'timestamp': time.time()
                            })
                    else:
                        # Resultado parcial
                        with self.audio_processing_lock:
                            partial_result = json.loads(self.stt.rec.PartialResult())
                        partial_text = partial_result.get('partial', '')
                        
                        if partial_text:
                            current_accumulated = " ".join(accumulated_text_parts)
                            display_text = f"{current_accumulated} {partial_text}".strip()
                            
                            await self.send_to_client(client_id, {
                                'type': 'speech_partial_live',
                                'text': display_text,
                                'timestamp': time.time()
                            })
                
                except Exception as e:
                    logger.error(f"Error procesando audio: {e}")
                    await asyncio.sleep(0.1)
            
            # Guardar texto final
            final_text = " ".join(accumulated_text_parts).strip()
            if client_id in self.clients:
                self.clients[client_id]['audio_buffer'] = final_text
                
        except Exception as e:
            logger.error(f"Error en escucha: {e}")
        finally:
            try:
                if self.stt:
                    with self.audio_processing_lock:
                        self.stt.stop_listening()
            except Exception as e:
                logger.error(f"Error deteniendo stream: {e}")
    
    async def _process_with_aura(self, client_id: str, text: str):
        """Procesar texto con Aura y manejar reasoning"""
        if client_id in self.clients and self.clients[client_id].get('processing', False):
            logger.warning(f"Cliente {client_id} ya está procesando")
            return
        
        if client_id in self.clients:
            self.clients[client_id]['processing'] = True
        
        try:
            logger.info(f"🤖 Procesando con Aura: '{text}'")
            
            if not self.aura_ready or not self.gemini_client:
                await self.send_to_client(client_id, {
                    'type': 'error',
                    'message': 'Aura no está listo'
                })
                return
            
            # 🧹 LIMPIAR BUFFER TTS - Nueva consulta cancela TTS anterior
            if self.tts_buffer:
                self.tts_buffer.clear_queue()
                # Actualizar contexto basado en lo que se reprodujo antes de limpiar
                self._update_conversation_context()
                logger.info("🧹 Buffer TTS limpiado para nueva consulta")
            
            await self.send_to_client(client_id, {
                'type': 'status',
                'message': 'Procesando con Aura...',
                'processing': True
            })
            
            # ¡AQUÍ VIENE LA MAGIA DEL REASONING!
            # Vamos a interceptar las llamadas al sequentialthinking
            response = await self._process_with_reasoning_interception(text, client_id)
            
            # Enviar respuesta final
            await self.send_to_client(client_id, {
                'type': 'aura_response',
                'response': response,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"❌ Error procesando con Aura: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'Error procesando: {str(e)}'
            })
        finally:
            if client_id in self.clients:
                self.clients[client_id]['processing'] = False
    
    async def _process_with_reasoning_interception(self, text: str, client_id: str) -> str:
        """Procesa con Aura interceptando reasoning para TTS buffer"""
        
        # Esta será nuestra clase para interceptar el método _process_response
        class ReasoningInterceptor:
            def __init__(self, server, client_id):
                self.server = server
                self.client_id = client_id
                self.original_process_response = None
                
        interceptor = ReasoningInterceptor(self, client_id)
        
        # Monkey patch temporal para interceptar reasoning
        original_method = self.gemini_client._process_response
        
        async def intercepted_process_response(response, chat_session=None):
            return await self._intercept_reasoning_response(
                original_method, response, chat_session, client_id
            )
        
        # Aplicar interceptor temporal
        self.gemini_client._process_response = intercepted_process_response
        
        try:
            # Procesar normalmente - ahora con interceptor
            response = await self.gemini_client.chat(text)
            return response
        finally:
            # Restaurar método original
            self.gemini_client._process_response = original_method
    
    async def _intercept_reasoning_response(self, original_method, response, chat_session, client_id):
        """Intercepta responses para detectar reasoning y enviarlo al TTS buffer"""
        
        # Llamar al método original pero interceptando los resultados
        max_iterations = 15
        iteration = 0
        current_response = response
        
        while iteration < max_iterations:
            iteration += 1
            
            if not current_response.candidates:
                return "No se pudo generar respuesta"
            
            candidate = current_response.candidates[0]
            
            # Verificar si hay function calls
            function_calls = []
            text_parts = []
            
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        func_call = part.function_call
                        if hasattr(func_call, 'name') and func_call.name:
                            function_calls.append(func_call)
                    elif hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
            
            # Si no hay function calls, respuesta final
            if not function_calls:
                final_text = "".join(text_parts) if text_parts else "Tarea completada"
                
                # Añadir respuesta final al buffer TTS
                if self.tts_buffer and final_text.strip():
                    await self.tts_buffer.add_item(TTSQueueItem(
                        id=str(uuid.uuid4()),
                        content=final_text,
                        item_type='response'
                    ))
                
                return final_text
            
            # Ejecutar function calls
            function_responses = []
            for func_call in function_calls:
                try:
                    # ¡DETECTAR SEQUENTIAL THINKING!
                    if func_call.name == 'sequentialthinking':
                        await self._handle_sequential_thinking(func_call, client_id)
                    
                    # Ejecutar herramienta MCP
                    result = await self.gemini_client.mcp_client.execute_tool(
                        func_call.name,
                        dict(func_call.args) if func_call.args else {}
                    )
                    
                    function_responses.append({
                        "function_response": {
                            "name": func_call.name,
                            "response": result
                        }
                    })
                    
                except Exception as e:
                    logger.error(f"Error ejecutando {func_call.name}: {e}")
                    function_responses.append({
                        "function_response": {
                            "name": func_call.name,
                            "response": f"Error: {e}"
                        }
                    })
            
            # Continuar conversación
            if not chat_session:
                break
            
            try:
                results_text = "Resultados de las herramientas:\n\n"
                for func_resp in function_responses:
                    name = func_resp["function_response"]["name"]
                    response_text = func_resp["function_response"]["response"]
                    results_text += f"**{name}**: {response_text}\n\n"
                
                if self.gemini_client.tools_available:
                    tools = self.gemini_client.mcp_client.get_tools_for_gemini()
                    current_response = chat_session.send_message(results_text, tools=tools)
                else:
                    current_response = chat_session.send_message(results_text)
                    
            except Exception as e:
                logger.error(f"Error continuando conversación: {e}")
                break
        
        return "Proceso completado"
    
    async def _handle_sequential_thinking(self, func_call, client_id: str):
        """Maneja llamadas a Sequential Thinking para extraer pensamientos"""
        try:
            args = dict(func_call.args) if func_call.args else {}
            
            # Extraer información del pensamiento
            thought_content = args.get('thought', '')
            thought_number = args.get('thoughtNumber', 0)
            total_thoughts = args.get('totalThoughts', 0)
            
            if thought_content and thought_content.strip():
                logger.info(f"💭 Pensamiento {thought_number}/{total_thoughts}: {thought_content[:50]}...")
                
                # Enviar pensamiento al frontend para mostrar visualmente
                await self.send_to_client(client_id, {
                    'type': 'reasoning_thought',
                    'thought': thought_content,
                    'thought_number': int(thought_number),
                    'total_thoughts': int(total_thoughts),
                    'timestamp': time.time()
                })
                
                # Añadir pensamiento al buffer TTS con velocidad aumentada
                if self.tts_buffer:
                    await self.tts_buffer.add_item(TTSQueueItem(
                        id=str(uuid.uuid4()),
                        content=thought_content,
                        item_type='thought',
                        thought_number=int(thought_number),
                        total_thoughts=int(total_thoughts),
                        speed_multiplier=1.8  # Más rápido para pensamientos
                    ))
                
        except Exception as e:
            logger.error(f"Error manejando sequential thinking: {e}")
    
    def _update_conversation_context(self):
        """Actualiza el contexto de la conversación basado en TTS completado"""
        if not self.tts_buffer:
            return
            
        # Obtener lo que realmente se reprodujo
        completed_context = self.tts_buffer.get_completed_context()
        
        if completed_context:
            # Construir respuesta completa de lo reproducido
            response_parts = []
            for context_item in completed_context:
                if context_item.startswith("Pensamiento"):
                    # Extraer solo el contenido del pensamiento
                    thought_content = context_item.split(": ", 1)[1] if ": " in context_item else context_item
                    response_parts.append(thought_content)
                elif context_item.startswith("Respuesta"):
                    # Extraer contenido de respuesta
                    response_content = context_item.split(": ", 1)[1] if ": " in context_item else context_item
                    response_parts.append(response_content)
            
            if response_parts:
                # Unir todo lo reproducido como última respuesta válida
                self.last_complete_response = " ".join(response_parts)
                logger.info(f"💾 Contexto actualizado hasta: '{self.last_complete_response[:100]}...'")
                
                # Actualizar historial del cliente Gemini para que solo incluya lo reproducido
                if self.gemini_client and hasattr(self.gemini_client, 'chat_history'):
                    # Modificar la última respuesta del modelo en el historial
                    if len(self.gemini_client.chat_history) > 1:
                        # Reemplazar última respuesta con lo que realmente se reprodujo
                        from gemini_client import ChatMessage
                        self.gemini_client.chat_history[-1] = ChatMessage(
                            role="model", 
                            content=self.last_complete_response
                        )
                        logger.info("🔄 Historial de Gemini actualizado con contexto reproducido")
    
    def get_context_status(self) -> Dict[str, Any]:
        """Obtiene estado del contexto para debugging"""
        context_info = {
            'last_complete_response_length': len(self.last_complete_response) if self.last_complete_response else 0,
            'tts_buffer_status': self.tts_buffer.get_status() if self.tts_buffer else None,
            'completed_items_count': len(self.tts_buffer.played_items) if self.tts_buffer else 0,
            'gemini_history_length': len(self.gemini_client.chat_history) if self.gemini_client else 0
        }
        return context_info
    
    async def create_webrtc_connection(self, client_id: str):
        """Crear conexión WebRTC para audio de alta calidad"""
        if not WEBRTC_AVAILABLE:
            return None
        
        try:
            pc = RTCPeerConnection({
                'iceServers': [{'urls': 'stun:stun.l.google.com:19302'}]
            })
            
            self.rtc_connections[client_id] = pc
            
            # Configurar track de audio optimizado
            if self.stt:
                audio_track = OptimizedAudioTrack(self.stt)
                pc.addTrack(audio_track)
            
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"WebRTC {client_id}: {pc.connectionState}")
                if pc.connectionState == "closed":
                    if client_id in self.rtc_connections:
                        del self.rtc_connections[client_id]
            
            return pc
            
        except Exception as e:
            logger.error(f"Error creando conexión WebRTC: {e}")
            return None
    
    async def handle_webrtc_offer(self, client_id: str, offer_data: Dict[str, Any]):
        """Manejar oferta WebRTC"""
        if not WEBRTC_AVAILABLE:
            await self.send_to_client(client_id, {
                'type': 'webrtc_error',
                'message': 'WebRTC no disponible'
            })
            return
        
        try:
            pc = await self.create_webrtc_connection(client_id)
            if not pc:
                return
            
            # Procesar oferta
            offer = RTCSessionDescription(sdp=offer_data['sdp'], type=offer_data['type'])
            await pc.setRemoteDescription(offer)
            
            # Crear respuesta
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            # Enviar respuesta al cliente
            await self.send_to_client(client_id, {
                'type': 'webrtc_answer',
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type
            })
            
        except Exception as e:
            logger.error(f"Error manejando oferta WebRTC: {e}")
            await self.send_to_client(client_id, {
                'type': 'webrtc_error',
                'message': f'Error WebRTC: {str(e)}'
            })
    
    async def handle_webrtc_ice_candidate(self, client_id: str, candidate_data: Dict[str, Any]):
        """Manejar candidatos ICE"""
        if client_id in self.rtc_connections:
            pc = self.rtc_connections[client_id]
            candidate = candidate_data.get('candidate')
            if candidate:
                try:
                    await pc.addIceCandidate(candidate)
                    logger.debug(f"ICE candidate añadido para {client_id}")
                except Exception as e:
                    logger.error(f"Error añadiendo ICE candidate: {e}")
    
    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        """Manejo de mensajes WebSocket"""
        message_type = message.get('type', '')
        
        try:
            if message_type == 'init_voice':
                await self.init_voice_system()
                
            elif message_type == 'init_aura':
                model_name = message.get('model_name', self.model_name)
                # Marcar como no ready mientras reinicializa
                self.aura_ready = False
                await self.broadcast_message({
                    'type': 'aura_initializing',
                    'message': f'Reinicializando con modelo {model_name}...'
                })
                await self.init_aura_client(model_name)
                
            elif message_type == 'start_listening':
                await self.start_listening(client_id)
                
            elif message_type == 'stop_listening':
                await self.stop_listening(client_id)
                
            elif message_type == 'webrtc_offer':
                await self.handle_webrtc_offer(client_id, message.get('offer', {}))
                
            elif message_type == 'webrtc_ice_candidate':
                await self.handle_webrtc_ice_candidate(client_id, message)
                
            elif message_type == 'change_language':
                language = message.get('language', 'es')
                await self.change_language(language)
                
            elif message_type == 'shutdown_system':
                await self.shutdown_system()
                
            else:
                logger.warning(f"Tipo de mensaje desconocido: {message_type}")
                
        except Exception as e:
            logger.error(f"Error manejando mensaje {message_type}: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'Error procesando {message_type}: {str(e)}'
            })
    
    async def change_language(self, language: str):
        """Cambiar idioma del sistema"""
        try:
            logger.info(f"🌐 Cambiando idioma a: {language}")
            
            old_language = self.voice_language
            self.voice_language = language
            
            if old_language != language:
                await self.init_voice_system()
            
            await self.broadcast_message({
                'type': 'language_changed',
                'language': language,
                'previous_language': old_language
            })
            
        except Exception as e:
            logger.error(f"Error cambiando idioma: {e}")
    
    async def shutdown_system(self):
        """Apagar sistema"""
        try:
            logger.info("🔌 Apagando sistema...")
            self.system_on = False
            
            # Detener tareas
            for task in list(self.processing_tasks):
                task.cancel()
            
            # Limpiar recursos de voz
            if self.stt:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, self.stt.close
                )
                self.stt = None
            
            if self.tts:
                self.tts.close()
                self.tts = None
                
            if self.tts_buffer:
                self.tts_buffer.clear_queue()
                self.tts_buffer = None
            
            # Limpiar conexiones WebRTC
            for pc in self.rtc_connections.values():
                await pc.close()
            self.rtc_connections.clear()
            
            # Limpiar cliente Aura con manejo seguro
            if self.gemini_client:
                try:
                    await self.gemini_client.cleanup()
                except Exception as e:
                    logger.warning(f"⚠️ Error limpiando cliente Aura: {e}")
                finally:
                    self.gemini_client = None
            
            self.voice_initialized = False
            self.aura_ready = False
            
            await self.broadcast_message({
                'type': 'shutdown_complete',
                'message': 'Sistema apagado correctamente'
            })
            
        except Exception as e:
            logger.error(f"Error apagando: {e}")
    
    async def handle_client(self, websocket, path=None):
        """Manejar conexión de cliente WebSocket"""
        client_id = await self.register_client(websocket)
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    # Crear tarea para procesamiento
                    if client_id in self.client_processing_locks:
                        async with self.client_processing_locks[client_id]:
                            await self.handle_message(client_id, data)
                    
                except json.JSONDecodeError:
                    logger.error(f"JSON inválido de {client_id}")
                    await self.send_to_client(client_id, {
                        'type': 'error',
                        'message': 'Formato de mensaje inválido'
                    })
        except ConnectionClosed:
            logger.info(f"Cliente desconectado: {client_id}")
        except Exception as e:
            logger.error(f"Error en cliente {client_id}: {e}")
        finally:
            await self.unregister_client(client_id)
    
    async def start_server(self):
        """Iniciar servidor WebSocket"""
        logger.info(f"🚀 Iniciando servidor en ws://{self.host}:{self.port}")
        
        # Inicialización paralela
        init_tasks = [
            asyncio.create_task(self.init_voice_system())
        ]
        
        await asyncio.gather(*init_tasks, return_exceptions=True)
        
        logger.info(f"✅ Servidor Aura listo en ws://{self.host}:{self.port}")
        
        # Iniciar servidor WebSocket
        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
            max_size=2**20
        ):
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("🛑 Cerrando servidor...")
                await self.shutdown_system()

async def main():
    """Función principal"""
    server = AuraWebSocketServer()
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("👋 Servidor detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error en servidor: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Optimizar para Linux si disponible
    if sys.platform.startswith('linux'):
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.info("🚀 Usando uvloop para mejor rendimiento")
        except ImportError:
            logger.info("ℹ️ uvloop no disponible, usando asyncio estándar")
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)