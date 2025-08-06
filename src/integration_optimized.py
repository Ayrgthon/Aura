#!/usr/bin/env python3
"""
Aura - Servidor de Integración Optimizado con WebRTC
Versión mejorada que soluciona los problemas de la implementación anterior:
- WebRTC para audio en tiempo real
- Manejo meticuloso de STT/TTS basado en main.py
- Optimización de velocidad y responsividad
- Sistema robusto anti-feedback
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from typing import Dict, Any, Optional, Set
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import queue
import uuid
from concurrent.futures import ThreadPoolExecutor

# Importar WebRTC y audio
try:
    import aiortc
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaRecorder, MediaPlayer
    WEBRTC_AVAILABLE = True
except ImportError:
    print("⚠️ WebRTC no disponible. Instala con: pip install aiortc")
    WEBRTC_AVAILABLE = False

# Agregar directorio voice al path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice'))
from hear import SpeechToText
from speak import TextToSpeech

# Importar cliente Aura
from client import SimpleAuraClient

# Configurar logging detallado
import logging.handlers

# Crear directorio de logs si no existe
import os
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configurar logging con archivo
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')

# Handler para archivo
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(logs_dir, 'aura_backend.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

# Handler para consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG)  # Cambiado a DEBUG temporalmente

# Configurar logger (solo uno para evitar duplicación)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Evitar propagación al root logger para evitar duplicados
logger.propagate = False

class OptimizedAudioTrack(MediaStreamTrack):
    """Track de audio optimizado para WebRTC"""
    
    kind = "audio"
    
    def __init__(self, stt_instance: SpeechToText):
        super().__init__()
        self.stt = stt_instance
        self.audio_queue = queue.Queue()
        
    async def recv(self):
        """Recibe frames de audio desde WebRTC"""
        # Implementación optimizada para recibir audio
        frame = await super().recv()
        
        # Procesar con STT si está disponible
        if self.stt and hasattr(frame, 'to_ndarray'):
            audio_data = frame.to_ndarray()
            self.audio_queue.put(audio_data)
        
        return frame

class AuraOptimizedServer:
    """Servidor Aura optimizado con WebRTC y manejo meticuloso"""
    
    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.clients: Dict[str, Dict[str, Any]] = {}  # Usar UUID como key
        
        # Sistema de audio optimizado
        self.stt: Optional[SpeechToText] = None
        self.tts: Optional[TextToSpeech] = None
        self.voice_language = "es"
        self.voice_initialized = False
        
        # Cliente Aura
        self.aura_client: Optional[SimpleAuraClient] = None
        self.aura_ready = False
        self.model_type = "gemini"
        self.model_name = "gemini-2.5-flash"
        
        # Sistema anti-feedback basado en main.py
        self.is_speaking = False
        self.is_listening = False
        self.speaking_lock = asyncio.Lock()
        self.listening_lock = asyncio.Lock()
        
        # Protección contra concurrencia
        self.client_processing_locks: Dict[str, asyncio.Lock] = {}
        self.audio_processing_lock = threading.Lock()  # Para proteger acceso a STT
        
        # Optimización de rendimiento
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.message_queue = asyncio.Queue()
        self.processing_tasks: Set[asyncio.Task] = set()
        
        # WebRTC
        self.rtc_connections: Dict[str, RTCPeerConnection] = {}
        
        # Estado del sistema
        self.system_on = True
        
        logger.info(f"Servidor optimizado inicializado en {host}:{port}")
    
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
            'audio_buffer': "",  # Buffer para acumular texto
            'processing': False  # Flag para evitar procesamiento múltiple
        }
        
        logger.info(f"Cliente registrado: {client_id} - {websocket.remote_address}")
        
        # Enviar mensaje de bienvenida rápido
        await self.send_to_client(client_id, {
            'type': 'connection',
            'message': 'Conectado al servidor Aura optimizado',
            'client_id': client_id,
            'webrtc_available': WEBRTC_AVAILABLE,
            'timestamp': time.time()
        })
        
        return client_id
    
    async def unregister_client(self, client_id: str):
        """Desregistra cliente y limpia recursos"""
        if client_id in self.clients:
            # Limpiar conexión WebRTC si existe
            if client_id in self.rtc_connections:
                await self.rtc_connections[client_id].close()
                del self.rtc_connections[client_id]
            
            # Limpiar lock del cliente
            if client_id in self.client_processing_locks:
                del self.client_processing_locks[client_id]
            
            del self.clients[client_id]
            logger.info(f"Cliente desregistrado: {client_id}")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Envío optimizado a cliente específico"""
        if client_id not in self.clients:
            logger.error(f"❌ Cliente {client_id} no existe en self.clients")
            return False
        
        try:
            websocket = self.clients[client_id]['websocket']
            message_str = json.dumps(message)
            logger.debug(f"📡 Enviando a {client_id}: {message.get('type', 'unknown')} - {message_str[:100]}...")
            await websocket.send(message_str)
            logger.debug(f"✅ Mensaje enviado exitosamente a {client_id}")
            return True
        except (ConnectionClosed, WebSocketException) as e:
            logger.warning(f"❌ Error enviando a {client_id}: {e}")
            await self.unregister_client(client_id)
            return False
    
    async def broadcast_message(self, message: Dict[str, Any], exclude_client: str = None):
        """Broadcast optimizado con exclusión opcional"""
        if not self.clients:
            return
        
        # Preparar mensaje una sola vez
        message_str = json.dumps(message)
        
        # Enviar concurrentemente
        tasks = []
        for client_id in list(self.clients.keys()):
            if client_id == exclude_client:
                continue
            tasks.append(self._send_raw_message(client_id, message_str))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_raw_message(self, client_id: str, message_str: str):
        """Envío de mensaje raw optimizado"""
        if client_id not in self.clients:
            return
        
        try:
            websocket = self.clients[client_id]['websocket']
            await websocket.send(message_str)
        except (ConnectionClosed, WebSocketException):
            await self.unregister_client(client_id)
    
    def get_mcp_config(self) -> Dict[str, Dict]:
        """Configuración MCP optimizada"""
        config = {}
        
        # Solo cargar MCP si las variables están disponibles
        serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        if serpapi_api_key:
            config["serpapi"] = {
                "command": "node",
                "args": ["mcp/serpapi_server.js"],
                "transport": "stdio",
                "env": {"SERPAPI_API_KEY": serpapi_api_key}
            }
        
        obsidian_vault = os.getenv("OBSIDIAN_VAULT_PATH", "/home/ary/Documents/Ary Vault")
        if os.path.exists(obsidian_vault):
            config["obsidian-memory"] = {
                "command": "node",
                "args": ["mcp/obsidian_memory_server.js"],
                "transport": "stdio",
                "env": {"OBSIDIAN_VAULT_PATH": obsidian_vault}
            }
        
        daily_path = os.getenv("DAILY_PATH", "/home/ary/Documents/Ary Vault/Daily")
        if os.path.exists(daily_path):
            config["personal-assistant"] = {
                "command": "node",
                "args": ["mcp/personal_assistant_server.js"],
                "transport": "stdio",
                "env": {"DAILY_PATH": daily_path}
            }
        
        return config
    
    async def init_voice_system_optimized(self):
        """Inicialización optimizada del sistema de voz"""
        try:
            logger.info("🎤 Inicializando sistema de voz optimizado...")
            
            # Usar executor para inicialización no-bloqueante
            loop = asyncio.get_event_loop()
            
            # Inicializar STT en hilo separado
            self.stt = await loop.run_in_executor(
                self.executor, 
                lambda: SpeechToText(language=self.voice_language)
            )
            
            # Inicializar TTS según idioma
            if self.voice_language == "es":
                self.tts = TextToSpeech(voice="en-US-EmmaMultilingualNeural")
                logger.info("✅ Emma configurada para español")
            else:
                self.tts = TextToSpeech(voice="en-US-AndrewMultilingualNeural")
                logger.info("✅ Andrew configurado para inglés")
            
            self.voice_initialized = True
            logger.info("✅ Sistema de voz optimizado inicializado")
            
            # Broadcast inmediato
            await self.broadcast_message({
                'type': 'voice_ready',
                'message': 'Sistema de voz optimizado listo',
                'language': self.voice_language,
                'webrtc_available': WEBRTC_AVAILABLE
            })
            
        except Exception as e:
            logger.error(f"❌ Error inicializando voz: {e}")
            await self.broadcast_message({
                'type': 'error',
                'message': f'Error inicializando voz: {str(e)}'
            })
    
    async def init_aura_client_optimized(self, model_type: str = None, model_name: str = None):
        """Inicialización optimizada del cliente Aura"""
        try:
            if model_type:
                self.model_type = model_type
            if model_name:
                self.model_name = model_name
                
            logger.info(f"🤖 Inicializando Aura optimizado: {self.model_type}:{self.model_name}")
            
            # Inicializar en executor para no bloquear
            loop = asyncio.get_event_loop()
            self.aura_client = await loop.run_in_executor(
                self.executor,
                lambda: SimpleAuraClient(model_name=self.model_name, debug_mode=False)  # Debug off para velocidad
            )
            
            # Configurar MCP de forma asíncrona
            mcp_config = self.get_mcp_config()
            if mcp_config:
                await self.aura_client.setup_mcp(mcp_config)
                logger.info(f"✅ MCP configurado: {len(mcp_config)} servidores")
            
            self.aura_ready = True
            logger.info("✅ Cliente Aura optimizado listo")
            
            # Broadcast inmediato
            await self.broadcast_message({
                'type': 'aura_ready',
                'message': 'Cliente Aura optimizado listo',
                'model_type': self.model_type,
                'model_name': self.model_name
            })
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Aura: {e}")
            self.aura_ready = False
            await self.broadcast_message({
                'type': 'error',
                'message': f'Error inicializando Aura: {str(e)}'
            })
    
    async def start_listening_optimized(self, client_id: str):
        """Inicio de escucha optimizado - PRIMER CLICK DEL BOTÓN"""
        logger.info(f"🎤 INICIANDO ESCUCHA para cliente {client_id}")
        
        async with self.listening_lock:
            if self.is_listening:
                logger.warning(f"Ya está escuchando para cliente {client_id}")
                return False
                
            if self.is_speaking:
                logger.warning(f"No puede escuchar: sistema hablando")
                return False
            
            if not self.stt or not self.voice_initialized:
                logger.error("Sistema de voz no inicializado")
                return False
            
            logger.info(f"✅ Activando escucha para cliente {client_id}")
            self.is_listening = True
            if client_id in self.clients:
                self.clients[client_id]['listening'] = True
            
            # Inicializar buffer de audio para acumular mientras escucha
            self.clients[client_id]['audio_buffer'] = ""
            
            # Crear tarea de escucha
            task = asyncio.create_task(self._listen_and_accumulate(client_id))
            self.processing_tasks.add(task)
            task.add_done_callback(self.processing_tasks.discard)
            
            # Enviar confirmación inmediata
            await self.send_to_client(client_id, {
                'type': 'status',
                'listening': True,
                'message': 'Escucha INICIADA - habla ahora'
            })
            
            logger.info(f"🎤 Cliente {client_id} está ahora ESCUCHANDO")
            return True
    
    async def stop_listening_optimized(self, client_id: str):
        """Detención de escucha optimizada - SEGUNDO CLICK DEL BOTÓN"""
        logger.info(f"🛑 DETENIENDO ESCUCHA para cliente {client_id}")
        
        async with self.listening_lock:
            if not self.is_listening:
                logger.warning(f"No estaba escuchando para cliente {client_id}")
                return False
            
            logger.info(f"✅ Deteniendo escucha para cliente {client_id}")
            self.is_listening = False
            if client_id in self.clients:
                self.clients[client_id]['listening'] = False
            
            await self.send_to_client(client_id, {
                'type': 'status',
                'listening': False,
                'message': 'Escucha DETENIDA - esperando texto final...'
            })
            
            logger.info(f"🛑 Cliente {client_id} dejó de escuchar, esperando texto acumulado...")
            
        # Esperar a que el hilo de acumulación termine y guarde el texto
        max_wait = 3  # Reducido a 3 segundos
        wait_interval = 0.1
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(wait_interval)
            waited += wait_interval
            
            # Verificar si ya hay texto acumulado
            if client_id in self.clients and 'audio_buffer' in self.clients[client_id]:
                accumulated_text = self.clients[client_id]['audio_buffer'].strip()
                if accumulated_text:
                    logger.info(f"📝 Texto obtenido tras {waited:.1f}s: '{accumulated_text}'")
                    
                    # PRIMERO: Enviar speech_recognized al frontend
                    speech_message = {
                        'type': 'speech_recognized',
                        'text': accumulated_text,
                        'timestamp': time.time()
                    }
                    logger.info(f"📤 Enviando speech_recognized al frontend: {speech_message}")
                    send_result = await self.send_to_client(client_id, speech_message)
                    logger.info(f"📤 Resultado del envío: {send_result}")
                    
                    # SEGUNDO: Procesar con Aura en tarea separada para no bloquear
                    asyncio.create_task(self._process_with_aura_optimized(client_id, accumulated_text))
                    return True
        
        # Si llegamos aquí, no se obtuvo texto
        logger.warning(f"❌ No se obtuvo texto tras {max_wait}s para cliente {client_id}")
        await self.send_to_client(client_id, {
            'type': 'no_speech_detected',
            'message': 'No se detectó voz durante la escucha'
        })
        
        return False
    
    async def _listen_and_accumulate(self, client_id: str):
        """Escucha y acumula texto hasta que se pare manualmente"""
        if not self.stt:
            logger.error("STT no disponible")
            return
        
        logger.info(f"🎤 Iniciando acumulación de audio para {client_id}")
        
        try:
            # Usar executor para operaciones bloqueantes
            loop = asyncio.get_event_loop()
            
            # Proteger acceso al STT con lock
            with self.audio_processing_lock:
                # Iniciar stream de audio
                self.stt.start_listening()  # Llamada directa, NO executor
                logger.info("🎤 Stream de audio iniciado")
            
            # Buffer para acumular texto
            accumulated_text_parts = []
            last_partial = ""
            
            while self.is_listening and not self.is_speaking:
                try:
                    # Proteger accesos concurrentes a STT
                    with self.audio_processing_lock:
                        # Leer audio
                        data = await loop.run_in_executor(
                            self.executor,
                            lambda: self.stt.stream.read(4000, exception_on_overflow=False)
                        )
                        
                        if len(data) == 0:
                            await asyncio.sleep(0.01)
                            continue
                        
                        # Procesar con Vosk
                        final_result = self.stt.rec.AcceptWaveform(data)
                    
                    if final_result:
                        # Resultado FINAL - acumular
                        with self.audio_processing_lock:
                            result = json.loads(self.stt.rec.Result())
                        
                        logger.debug(f"🔍 Resultado completo de Vosk: {result}")
                        text_chunk = result.get('text', '').strip()
                        
                        logger.debug(f"🔍 Texto extraído: '{text_chunk}' (longitud: {len(text_chunk)})")
                        
                        if text_chunk:
                            logger.info(f"🗣️ Chunk reconocido FINAL: '{text_chunk}'")
                            accumulated_text_parts.append(text_chunk)
                            
                            # Guardar inmediatamente en el buffer del cliente
                            current_accumulated = " ".join(accumulated_text_parts)
                            logger.info(f"💾 Guardando en buffer: '{current_accumulated}'")
                            
                            if client_id in self.clients:
                                self.clients[client_id]['audio_buffer'] = current_accumulated
                            
                            # Mostrar texto parcial acumulado al frontend
                            await self.send_to_client(client_id, {
                                'type': 'speech_partial_accumulated',
                                'text': current_accumulated,
                                'chunk': text_chunk,
                                'timestamp': time.time()
                            })
                        else:
                            logger.debug("🔍 Chunk vacío ignorado")
                    else:
                        # Resultado parcial - solo para mostrar
                        with self.audio_processing_lock:
                            partial_result = json.loads(self.stt.rec.PartialResult())
                        partial_text = partial_result.get('partial', '')
                        
                        if partial_text and partial_text != last_partial:
                            logger.debug(f"🎯 Partial reconocido: '{partial_text}'")
                            
                            # Mostrar lo acumulado + lo que está diciendo ahora
                            current_accumulated = " ".join(accumulated_text_parts)
                            if current_accumulated:
                                display_text = f"{current_accumulated} {partial_text}"
                            else:
                                display_text = partial_text
                                
                            await self.send_to_client(client_id, {
                                'type': 'speech_partial_live',
                                'text': display_text,
                                'timestamp': time.time()
                            })
                            last_partial = partial_text
                
                except Exception as e:
                    logger.error(f"Error procesando audio: {e}")
                    await asyncio.sleep(0.1)
            
            # Finalizar - asegurar que el texto esté guardado
            final_text = " ".join(accumulated_text_parts).strip()
            logger.info(f"🎯 Texto final acumulado: '{final_text}'")
            
            # Guardar texto final (puede que ya esté guardado por los chunks)
            if client_id in self.clients:
                self.clients[client_id]['audio_buffer'] = final_text
                logger.info(f"💾 Texto guardado en buffer del cliente: '{final_text}'")
                
        except Exception as e:
            logger.error(f"Error en escucha y acumulación: {e}")
        finally:
            # Cleanup
            try:
                if self.stt:
                    with self.audio_processing_lock:
                        self.stt.stop_listening()  # Llamada directa, NO executor
                    logger.info("🎤 Stream de audio detenido")
            except Exception as e:
                logger.error(f"Error deteniendo stream: {e}")
            
            # No cambiar estados aquí - se manejan en stop_listening_optimized
    
    async def _process_with_aura_optimized(self, client_id: str, text: str):
        """Procesamiento optimizado con Aura"""
        # Verificar si ya está procesando para este cliente
        if client_id in self.clients and self.clients[client_id].get('processing', False):
            logger.warning(f"⚠️ Cliente {client_id} ya está procesando, ignorando solicitud duplicada")
            return
        
        # Marcar como procesando
        if client_id in self.clients:
            self.clients[client_id]['processing'] = True
        
        try:
            logger.info(f"🤖 Iniciando procesamiento con Aura - texto: '{text}'")
            
            if not self.aura_ready:
                logger.error("❌ Aura no está listo")
                await self.send_to_client(client_id, {
                    'type': 'error',
                    'message': 'Aura no está inicializado'
                })
                return
                
            if not self.aura_client:
                logger.error("❌ Cliente Aura es None")
                await self.send_to_client(client_id, {
                    'type': 'error',
                    'message': 'Cliente Aura no disponible'
                })
                return
            
            logger.info(f"✅ Aura está listo, procesando: '{text}'")
            
            response = None  # Inicializar para evitar NameError
            
            try:
                # NO pausar STT - simplificado como main.py
                logger.info("⚡ Procesamiento directo (sin pausar STT)")
                
                # Enviar estado de procesamiento
                logger.info("📤 Enviando estado de procesamiento al frontend...")
                await self.send_to_client(client_id, {
                    'type': 'status',
                    'message': 'Procesando con Aura...',
                    'processing': True
                })
                logger.info("✅ Estado enviado")
                
                # Procesar con Aura de forma no-bloqueante
                logger.info(f"🤖 Llamando a aura_client.chat con texto: '{text}'")
                logger.info(f"🤖 Tipo de aura_client: {type(self.aura_client)}")
                
                response = await self.aura_client.chat(text)
                logger.info(f"🤖 Respuesta Aura recibida: {response[:100] if response else 'None'}...")
                
                # Enviar respuesta
                logger.info("📤 Enviando respuesta de Aura al frontend...")
                await self.send_to_client(client_id, {
                    'type': 'aura_response',
                    'response': response,
                    'timestamp': time.time()
                })
                logger.info("✅ Respuesta enviada al frontend")
                
                # Hablar respuesta si TTS está disponible
                if self.tts and response:
                    logger.info("🔊 Iniciando TTS...")
                    await self._speak_optimized(response, exclude_client=client_id)
                    logger.info("✅ TTS completado")
                
            except Exception as aura_error:
                logger.error(f"❌ Error específico en procesamiento Aura: {aura_error}")
                logger.error(f"❌ Tipo de error: {type(aura_error)}")
                import traceback
                logger.error(f"❌ Traceback completo:\n{traceback.format_exc()}")
                
                await self.send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Error en Aura: {str(aura_error)}'
                })
        
        except Exception as e:
            logger.error(f"Error procesando con Aura: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'Error procesando: {str(e)}'
            })
        finally:
            # Desmarcar procesamiento
            if client_id in self.clients:
                self.clients[client_id]['processing'] = False
    
    async def _speak_optimized(self, text: str, exclude_client: str = None):
        """TTS optimizado con protección anti-feedback"""
        async with self.speaking_lock:
            self.is_speaking = True
            
            try:
                # Notificar inicio de habla
                await self.broadcast_message({
                    'type': 'tts_status',
                    'speaking': True,
                    'speaking_animation': True,
                    'message': 'Aura hablando...'
                }, exclude_client)
                
                # Ejecutar TTS en executor
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.tts.speak,
                    text
                )
                
                # Notificar fin de habla
                await self.broadcast_message({
                    'type': 'tts_status',
                    'speaking': False,
                    'speaking_animation': False,
                    'message': 'TTS completado'
                }, exclude_client)
                
            except Exception as e:
                logger.error(f"Error en TTS optimizado: {e}")
                await self.broadcast_message({
                    'type': 'error',
                    'message': f'Error en TTS: {str(e)}'
                }, exclude_client)
            finally:
                self.is_speaking = False
    
    async def create_webrtc_connection(self, client_id: str):
        """Crear conexión WebRTC para audio de alta calidad"""
        if not WEBRTC_AVAILABLE:
            return None
        
        try:
            pc = RTCPeerConnection()
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
    
    async def handle_message_optimized(self, client_id: str, message: Dict[str, Any]):
        """Manejo optimizado de mensajes"""
        message_type = message.get('type', '')
        
        try:
            if message_type == 'init_voice':
                await self.init_voice_system_optimized()
                
            elif message_type == 'init_aura':
                model_type = message.get('model_type', self.model_type)
                model_name = message.get('model_name', self.model_name)
                await self.init_aura_client_optimized(model_type, model_name)
                
            elif message_type == 'start_listening':
                await self.start_listening_optimized(client_id)
                
            elif message_type == 'stop_listening':
                await self.stop_listening_optimized(client_id)
                
            elif message_type == 'webrtc_offer':
                await self.handle_webrtc_offer(client_id, message.get('offer', {}))
                
            elif message_type == 'webrtc_ice_candidate':
                # Manejar candidatos ICE
                if client_id in self.rtc_connections:
                    pc = self.rtc_connections[client_id]
                    candidate = message.get('candidate')
                    if candidate:
                        await pc.addIceCandidate(candidate)
                
            elif message_type == 'change_language':
                language = message.get('language', 'es')
                await self.change_language_optimized(language)
                
            elif message_type == 'shutdown_system':
                await self.shutdown_system_optimized()
                
            else:
                logger.warning(f"Tipo de mensaje no reconocido: {message_type}")
                
        except Exception as e:
            logger.error(f"Error manejando mensaje {message_type}: {e}")
            await self.send_to_client(client_id, {
                'type': 'error',
                'message': f'Error procesando {message_type}: {str(e)}'
            })
    
    async def change_language_optimized(self, language: str):
        """Cambio optimizado de idioma"""
        try:
            logger.info(f"🌐 Cambiando idioma a: {language}")
            
            old_language = self.voice_language
            self.voice_language = language
            
            # Reinicializar solo si es necesario
            if old_language != language:
                await self.init_voice_system_optimized()
            
            await self.broadcast_message({
                'type': 'language_changed',
                'language': language,
                'previous_language': old_language,
                'message': f'Idioma cambiado a {language}'
            })
            
        except Exception as e:
            logger.error(f"Error cambiando idioma: {e}")
    
    async def shutdown_system_optimized(self):
        """Apagado optimizado del sistema"""
        try:
            logger.info("🔌 Apagando sistema optimizado...")
            self.system_on = False
            
            # Detener todas las tareas
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
            
            # Limpiar conexiones WebRTC
            for pc in self.rtc_connections.values():
                await pc.close()
            self.rtc_connections.clear()
            
            # Limpiar cliente Aura
            if self.aura_client:
                await self.aura_client.cleanup()
                self.aura_client = None
            
            self.voice_initialized = False
            self.aura_ready = False
            
            await self.broadcast_message({
                'type': 'shutdown_complete',
                'message': 'Sistema apagado correctamente'
            })
            
            logger.info("✅ Sistema apagado correctamente")
            
        except Exception as e:
            logger.error(f"Error apagando sistema: {e}")
    
    async def handle_client_optimized(self, websocket, path=None):
        """Manejo optimizado de cliente WebSocket"""
        client_id = await self.register_client(websocket)
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type', '')
                    
                    # Mensajes críticos que SIEMPRE se procesan (sin lock)
                    if message_type in ['stop_listening', 'shutdown_system', 'webrtc_ice_candidate']:
                        task = asyncio.create_task(
                            self.handle_message_optimized(client_id, data)
                        )
                        self.processing_tasks.add(task)
                        task.add_done_callback(self.processing_tasks.discard)
                        continue
                    
                    # Otros mensajes usan lock para evitar concurrencia
                    if client_id in self.client_processing_locks:
                        # No bloquear, solo verificar si está ocupado
                        if self.client_processing_locks[client_id].locked():
                            logger.warning(f"⚠️ Cliente {client_id} ocupado, ignorando mensaje {message_type}")
                            continue
                            
                        # Crear tarea para procesamiento con lock
                        task = asyncio.create_task(
                            self._handle_message_with_lock(client_id, data)
                        )
                        self.processing_tasks.add(task)
                        task.add_done_callback(self.processing_tasks.discard)
                    
                except json.JSONDecodeError:
                    logger.error(f"Mensaje JSON inválido de {client_id}")
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
    
    async def _handle_message_with_lock(self, client_id: str, data: Dict[str, Any]):
        """Maneja mensajes con lock específico del cliente"""
        if client_id not in self.client_processing_locks:
            return
            
        async with self.client_processing_locks[client_id]:
            await self.handle_message_optimized(client_id, data)
    
    async def start_server_optimized(self):
        """Inicio optimizado del servidor"""
        logger.info(f"🚀 Iniciando servidor optimizado en ws://{self.host}:{self.port}")
        
        # Inicialización asíncrona concurrente
        init_tasks = [
            asyncio.create_task(self.init_voice_system_optimized()),
            # Note: No auto-init Aura para mejorar tiempo de arranque
        ]
        
        # Esperar inicialización básica
        await asyncio.gather(*init_tasks, return_exceptions=True)
        
        logger.info(f"✅ Servidor Aura optimizado ejecutándose en ws://{self.host}:{self.port}")
        logger.info("📡 WebRTC: " + ("Disponible" if WEBRTC_AVAILABLE else "No disponible"))
        
        # Iniciar servidor WebSocket
        async with websockets.serve(
            self.handle_client_optimized,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
            max_size=2**20,  # 1MB max message size
            compression=None  # Disable compression for speed
        ):
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("🛑 Cerrando servidor...")
                await self.shutdown_system_optimized()

async def main():
    """Función principal optimizada"""
    server = AuraOptimizedServer()
    
    try:
        await server.start_server_optimized()
    except KeyboardInterrupt:
        logger.info("👋 Servidor detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error en servidor: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Configurar política de eventos para mejor rendimiento en Linux
    if sys.platform.startswith('linux'):
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.info("🚀 Usando uvloop para mejor rendimiento")
        except ImportError:
            logger.info("ℹ️ uvloop no disponible, usando asyncio estándar")
    
    exit(asyncio.run(main()))
