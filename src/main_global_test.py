#!/usr/bin/env python3
"""
Main Global Test - Aura Conversacional con WebSocket
Sistema de escucha permanente con timeout conversacional de 4 segundos + integración frontend.

Flujo:
1. Escucha permanente hasta detectar "Aura despierta"
2. Envía "Aura, despierta" al cliente Gemini
3. Entra en modo conversacional con timeout de 4 segundos
4. Acumula texto mientras habla el usuario
5. Después de 4 segundos sin voz → procesa mensaje y responde
6. Vuelve a modo conversacional (sin necesidad de nueva activación)

Integración Frontend:
- WebSocket server para mostrar estados en tiempo real
- Buffer conversacional visible en UI
- Estados del sistema reflejados en frontend
- Texto reconocido mostrado en tiempo real
"""

import os
import sys
import time
import json
import threading
import logging
import asyncio
import uuid
import websockets
from typing import Optional, Dict, Any, Set
from enum import Enum
from websockets.exceptions import ConnectionClosed, WebSocketException
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# Agregar paths necesarios
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice'))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client'))

# Importar módulos del sistema
from hear import SpeechToText
from speak import TextToSpeech
from gemini_client import SimpleGeminiClient
from config import get_mcp_servers_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
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

    def __init__(self, tts_instance: TextToSpeech, server_instance=None):
        self.tts = tts_instance
        self.server = server_instance  # Referencia al servidor para notificaciones
        self.queue = asyncio.Queue()
        self.is_playing = False
        self.current_item = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.processing_task = None
        self.should_stop = False  # Flag para interrupción
        self.current_thread = None  # Referencia al hilo actual de TTS
        self.played_items = []  # Lista de items reproducidos completamente
        self.has_sequential_thinking = False  # Track si hay sequential thinking
        self.first_reasoning_sent = False  # Track si ya se envió el primer razonamiento

    def get_completed_context(self) -> list:
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

    def _split_into_sentences(self, text: str) -> list:
        """Separa texto en oraciones por puntos, comas y signos de puntuación"""
        import re

        # Separar por puntos, comas, signos de exclamación, interrogación, etc.
        # Mantener el separador al final de cada oración
        sentences = re.split(r'([.!?,;:])', text)

        # Recombinar oraciones con sus signos de puntuación
        result = []
        current_sentence = ""

        for i, part in enumerate(sentences):
            current_sentence += part

            # Si es un signo de puntuación o llegamos al final
            if part in '.!?,;:' or i == len(sentences) - 1:
                if current_sentence.strip():
                    result.append(current_sentence.strip())
                current_sentence = ""

        return [s for s in result if s.strip()]

    def _get_first_paragraph(self, text: str) -> str:
        """Extrae el primer párrafo del texto"""
        paragraphs = text.split('\n\n')
        return paragraphs[0] if paragraphs else text

    def reset_conversation_tracking(self):
        """Resetea el tracking de conversación para nueva interacción"""
        self.has_sequential_thinking = False
        self.first_reasoning_sent = False
        logger.info("🔄 Tracking de conversación reseteado")

    async def _notify_tts_start(self, item: TTSQueueItem):
        """Notifica al frontend que empezó reproducción de TTS"""
        if self.server:
            await self.server.broadcast_message({
                'type': 'tts_status',
                'speaking': True,
                'speaking_animation': True,
                'message': f'Reproduciendo {item.item_type}',
                'item_type': item.item_type,
                'content_preview': item.content[:50] + '...' if len(item.content) > 50 else item.content
            })

    async def _notify_tts_end(self, item: TTSQueueItem):
        """Notifica al frontend que terminó reproducción de TTS"""
        if self.server:
            # Verificar si hay más items en la cola
            has_more_items = not self.queue.empty()
            await self.server.broadcast_message({
                'type': 'tts_status',
                'speaking': has_more_items,  # Solo speaking=false si no hay más items
                'speaking_animation': has_more_items,
                'message': f'Completado {item.item_type}',
                'item_completed': True,
                'queue_remaining': self.queue.qsize()
            })

    async def _notify_tts_interrupted(self, item: TTSQueueItem):
        """Notifica al frontend que se interrumpió TTS"""
        if self.server:
            await self.server.broadcast_message({
                'type': 'tts_status',
                'speaking': False,
                'speaking_animation': False,
                'message': f'Interrumpido {item.item_type}',
                'interrupted': True
            })

    async def add_item(self, item: TTSQueueItem):
        """Añade item al buffer"""
        await self.queue.put(item)
        logger.info(f"🔊 Item añadido al buffer TTS: {item.item_type} - '{item.content[:50]}...'")

        # Iniciar procesamiento si no está activo
        if not self.processing_task or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_queue())

    async def add_response_with_sentence_splitting(self, text: str, item_type: str = 'response'):
        """Añade respuesta con separación SOLO de la primera oración para respuesta rápida"""
        if not text.strip():
            return

        # Determinar si separar solo la primera oración
        should_split_first = False

        if self.has_sequential_thinking:
            # Si hay sequential thinking, solo separar la primera oración del primer razonamiento
            if item_type == 'thought' and not self.first_reasoning_sent:
                should_split_first = True
                self.first_reasoning_sent = True
                logger.info("📝 Enviando primera oración del primer razonamiento (sequential thinking)")
        else:
            # Sin sequential thinking, separar solo la primera oración de la respuesta
            if item_type == 'response':
                should_split_first = True
                logger.info("📝 Enviando primera oración de la respuesta (sin sequential thinking)")

        if should_split_first:
            sentences = self._split_into_sentences(text)

            if len(sentences) > 0:
                first_sentence = sentences[0]
                remaining_text = " ".join(sentences[1:]) if len(sentences) > 1 else ""

                logger.info(f"🎵 Enviando primera oración rápida: '{first_sentence[:50]}...'")

                # Enviar primera oración con velocidad normal pero prioridad alta
                await self.add_item(TTSQueueItem(
                    id=str(uuid.uuid4()),
                    content=first_sentence,
                    item_type=f'{item_type}_first',
                    priority=0,  # Máxima prioridad
                    speed_multiplier=1.0  # Velocidad normal
                ))

                # Enviar resto del texto si existe
                if remaining_text.strip():
                    await self.add_item(TTSQueueItem(
                        id=str(uuid.uuid4()),
                        content=remaining_text,
                        item_type=item_type,
                        priority=1,
                        speed_multiplier=1.0  # Velocidad normal
                    ))
            else:
                # No se pudo separar, enviar todo
                await self.add_item(TTSQueueItem(
                    id=str(uuid.uuid4()),
                    content=text,
                    item_type=item_type,
                    speed_multiplier=1.0
                ))
        else:
            # Enviar texto completo normalmente
            await self.add_item(TTSQueueItem(
                id=str(uuid.uuid4()),
                content=text,
                item_type=item_type,
                speed_multiplier=1.0  # Velocidad normal
            ))

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

                # 📡 NOTIFICAR AL FRONTEND QUE EMPEZÓ REPRODUCCIÓN
                await self._notify_tts_start(item)

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
                    # 📡 NOTIFICAR AL FRONTEND QUE TERMINÓ REPRODUCCIÓN
                    await self._notify_tts_end(item)

                    # Pausa mínima entre items para evitar superposición pero mantener fluidez
                    await asyncio.sleep(0.01)  # 10ms mínimo entre oraciones - máxima fluidez
                else:
                    logger.info(f"🔇 Interrumpido: {item.item_type}")
                    # 📡 NOTIFICAR INTERRUPCIÓN AL FRONTEND
                    await self._notify_tts_interrupted(item)
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

                # Loop interrumpible con menos tiempo entre checks
                while pygame.mixer.music.get_busy() and not self.should_stop:
                    pygame.time.wait(10)  # Check mucho más frecuente para menos latencia

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

    def get_status(self) -> dict:
        """Estado actual del buffer"""
        return {
            'is_playing': self.is_playing,
            'queue_size': self.queue.qsize(),
            'current_item': {
                'type': self.current_item.item_type,
                'content': self.current_item.content[:50] + '...'
            } if self.current_item else None
        }

class ConversationState(Enum):
    LISTENING_FOR_WAKE = "listening_for_wake"
    CONVERSATIONAL = "conversational"
    PROCESSING = "processing"
    SPEAKING = "speaking"

class AuraGlobalSystem:
    """Sistema Aura global conversacional con WebSocket"""

    def __init__(self, host: str = "localhost", port: int = 8766):
        # Configuración WebSocket
        self.host = host
        self.port = port
        self.clients: Dict[str, Dict[str, Any]] = {}

        # Estado del sistema
        self.state = ConversationState.LISTENING_FOR_WAKE
        self.running = True

        # Componentes del sistema
        self.stt: Optional[SpeechToText] = None
        self.tts: Optional[TextToSpeech] = None
        self.gemini_client: Optional[SimpleGeminiClient] = None

        # Control conversacional
        self.conversation_buffer = ""
        self.last_speech_time = 0
        self.timeout_seconds = 2.0
        self.wake_phrase = "aura despierta"

        # Control de bloqueo de audio para evitar feedback (ya no necesario con detección dinámica)
        # self.is_speaking = False  # Removido - ahora usamos detección dinámica

        # Buffer TTS para reasoning secuencial (COPIADO DEL SISTEMA ORIGINAL)
        self.tts_buffer = None

        # Hilos
        self.conversation_thread = None
        self.timeout_thread = None
        self.listening_thread = None
        self.tts_thread = None

        # Event loop persistente para async operations
        self.event_loop = None
        self.loop_thread = None

        # Pool de hilos
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.processing_tasks: Set[asyncio.Task] = set()

        logger.info(f"🚀 Sistema Aura Global con WebSocket inicializado en {host}:{port}")

    # ================================
    # MÉTODOS WEBSOCKET
    # ================================

    async def register_client(self, websocket, client_id: str = None):
        """Registra cliente WebSocket"""
        if not client_id:
            client_id = str(uuid.uuid4())

        self.clients[client_id] = {
            'websocket': websocket,
            'connected_at': time.time(),
            'listening': False,
            'processing': False
        }

        logger.info(f"👤 Cliente WebSocket registrado: {client_id}")

        # Enviar estado inicial
        await self.send_to_client(client_id, {
            'type': 'connection',
            'message': 'Conectado al sistema Aura Global',
            'client_id': client_id,
            'state': self.state.value,
            'conversation_buffer': self.conversation_buffer,
            'timestamp': time.time()
        })

        return client_id

    async def unregister_client(self, client_id: str):
        """Desregistra cliente WebSocket"""
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"👋 Cliente WebSocket desregistrado: {client_id}")

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

    async def notify_state_change(self, new_state: ConversationState, extra_data: Dict = None):
        """Notifica cambio de estado a todos los clientes"""
        message = {
            'type': 'state_change',
            'state': new_state.value,
            'conversation_buffer': self.conversation_buffer,
            'timestamp': time.time()
        }

        if extra_data:
            message.update(extra_data)

        await self.broadcast_message(message)
        logger.info(f"📡 Estado cambiado a: {new_state.value}")

    async def notify_speech_recognized(self, text: str, is_partial: bool = False):
        """Notifica texto reconocido al frontend"""
        await self.broadcast_message({
            'type': 'speech_recognized' if not is_partial else 'speech_partial',
            'text': text,
            'conversation_buffer': self.conversation_buffer,
            'timestamp': time.time()
        })

    async def notify_conversation_buffer_update(self):
        """Notifica actualización del buffer conversacional"""
        await self.broadcast_message({
            'type': 'conversation_buffer_update',
            'conversation_buffer': self.conversation_buffer,
            'last_speech_time': self.last_speech_time,
            'timeout_remaining': max(0, self.timeout_seconds - (time.time() - self.last_speech_time)),
            'timestamp': time.time()
        })

    async def notify_processing_start(self, message: str):
        """Notifica inicio de procesamiento"""
        await self.broadcast_message({
            'type': 'processing_start',
            'message': message,
            'state': 'processing',
            'timestamp': time.time()
        })

    async def notify_response_received(self, response: str):
        """Notifica respuesta recibida"""
        await self.broadcast_message({
            'type': 'aura_response',
            'response': response,
            'timestamp': time.time()
        })

    async def notify_tts_status(self, speaking: bool, message: str = None):
        """Notifica estado del TTS"""
        await self.broadcast_message({
            'type': 'tts_status',
            'speaking': speaking,
            'speaking_animation': speaking,
            'message': message or ('Reproduciendo respuesta' if speaking else 'Reproducción completada'),
            'timestamp': time.time()
        })

    # ================================
    # MÉTODOS CORE (MODIFICADOS PARA WEBSOCKET)
    # ================================

    def _start_event_loop(self):
        """Inicia un event loop persistente en hilo separado"""
        def run_loop():
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            self.event_loop.run_forever()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

        # Esperar a que el loop esté listo
        while self.event_loop is None:
            time.sleep(0.01)

        logger.info("🔄 Event loop persistente iniciado")

    def _run_async(self, coro):
        """Ejecuta una corrutina en el event loop persistente"""
        if not self.event_loop or self.event_loop.is_closed():
            raise RuntimeError("Event loop no disponible")

        future = asyncio.run_coroutine_threadsafe(coro, self.event_loop)
        return future.result()

    def init_components(self):
        """Inicializar todos los componentes del sistema"""
        try:
            # Iniciar event loop persistente
            self._start_event_loop()

            logger.info("🎤 Inicializando STT...")
            self.stt = SpeechToText(language="es")

            logger.info("🔊 Inicializando TTS...")
            self.tts = TextToSpeech(voice="en-US-EmmaMultilingualNeural")

            # Inicializar buffer TTS
            logger.info("🎭 Inicializando buffer TTS...")
            self.tts_buffer = TTSBuffer(self.tts, self)

            logger.info("🤖 Inicializando cliente Gemini...")
            self.gemini_client = SimpleGeminiClient(model_name="gemini-2.5-flash", debug=True)

            # Configurar servidores MCP (async)
            mcp_config = get_mcp_servers_config()
            if mcp_config:
                logger.info(f"🛠️ Configurando {len(mcp_config)} servidores MCP...")
                success = self._run_async(self.gemini_client.setup_mcp_servers(mcp_config))

                if success:
                    logger.info("✅ Servidores MCP configurados")
                else:
                    logger.warning("⚠️ Algunos servidores MCP fallaron")

            logger.info("✅ Todos los componentes inicializados correctamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False

    def detect_wake_phrase(self, text: str) -> bool:
        """Detecta la frase de activación"""
        return self.wake_phrase.lower() in text.lower()

    def is_tts_playing(self) -> bool:
        """Detecta dinámicamente si el TTS está reproduciéndose"""
        try:
            import pygame
            # Verificar si pygame mixer está inicializado y reproduciéndose
            if pygame.mixer.get_init() is not None:
                return pygame.mixer.music.get_busy()
            return False
        except Exception as e:
            logger.debug(f"Error verificando estado TTS: {e}")
            return False

    async def _process_with_reasoning_interception(self, text: str) -> str:
        """Procesa con Aura interceptando reasoning para TTS buffer - ARQUITECTURA ASYNC PURA"""

        # Monkey patch temporal para interceptar reasoning
        original_method = self.gemini_client._process_response

        async def intercepted_process_response(response, chat_session=None):
            return await self._intercept_reasoning_response(
                original_method, response, chat_session
            )

        # Aplicar interceptor temporal
        self.gemini_client._process_response = intercepted_process_response

        try:
            # Procesar con async puro - SIN executors
            response = await self.gemini_client.chat(text)
            return response
        finally:
            # Restaurar método original
            self.gemini_client._process_response = original_method

    async def _intercept_reasoning_response(self, original_method, response, chat_session):
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

                # Usar nueva función de separación por oraciones para respuestas finales
                if self.tts_buffer and final_text.strip():
                    await self.tts_buffer.add_response_with_sentence_splitting(
                        final_text,
                        item_type='response'
                    )

                return final_text

            # Ejecutar function calls
            function_responses = []
            for func_call in function_calls:
                try:
                    # ¡DETECTAR SEQUENTIAL THINKING!
                    if func_call.name == 'sequentialthinking':
                        await self._handle_sequential_thinking(func_call)

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

    async def _handle_sequential_thinking(self, func_call):
        """Maneja llamadas a Sequential Thinking para extraer pensamientos"""
        try:
            # Marcar que hay sequential thinking en esta conversación
            if self.tts_buffer:
                self.tts_buffer.has_sequential_thinking = True

            args = dict(func_call.args) if func_call.args else {}

            # Extraer información del pensamiento
            thought_content = args.get('thought', '')
            thought_number = args.get('thoughtNumber', 0)
            total_thoughts = args.get('totalThoughts', 0)

            if thought_content and thought_content.strip():
                logger.info(f"💭 Pensamiento {thought_number}/{total_thoughts}: {thought_content[:50]}...")

                # Enviar pensamiento al frontend para mostrar visualmente
                await self.broadcast_message({
                    'type': 'reasoning_thought',
                    'thought': thought_content,
                    'thought_number': int(thought_number),
                    'total_thoughts': int(total_thoughts),
                    'timestamp': time.time()
                })

                # Usar nueva función de separación por oraciones para primer razonamiento
                if self.tts_buffer:
                    await self.tts_buffer.add_response_with_sentence_splitting(
                        thought_content,
                        item_type='thought'
                    )

        except Exception as e:
            logger.error(f"Error manejando sequential thinking: {e}")



    def start_conversation_mode(self):
        """Inicia el modo conversacional"""
        logger.info("💬 Entrando en modo conversacional")
        self.state = ConversationState.CONVERSATIONAL
        self.conversation_buffer = ""
        self.last_speech_time = time.time()

        # Notificar cambio de estado via WebSocket
        asyncio.run_coroutine_threadsafe(
            self.notify_state_change(ConversationState.CONVERSATIONAL, {
                'message': 'Modo conversacional activado - di algo...'
            }),
            self.event_loop
        )

        # Iniciar hilo de timeout
        if self.timeout_thread and self.timeout_thread.is_alive():
            self.timeout_thread = None

        self.timeout_thread = threading.Thread(target=self._timeout_monitor, daemon=True)
        self.timeout_thread.start()

    def _timeout_monitor(self):
        """Monitor del timeout conversacional"""
        while self.state == ConversationState.CONVERSATIONAL and self.running:
            current_time = time.time()
            time_since_speech = current_time - self.last_speech_time

            if time_since_speech >= self.timeout_seconds and self.conversation_buffer.strip():
                logger.info(f"⏰ Timeout de {self.timeout_seconds}s alcanzado - procesando mensaje")
                self._process_conversation_message()
                break

            time.sleep(0.1)

    def _process_conversation_message(self):
        """Procesa el mensaje conversacional acumulado (wrapper síncrono)"""
        asyncio.run_coroutine_threadsafe(
            self._process_conversation_message_async(),
            self.event_loop
        )

    async def _process_conversation_message_async(self):
        """Procesa el mensaje conversacional acumulado (versión async)"""
        if not self.conversation_buffer.strip():
            logger.info("📝 Buffer vacío, volviendo a escucha")
            return

        # Resetear tracking de conversación para nueva interacción
        if self.tts_buffer:
            self.tts_buffer.reset_conversation_tracking()

        self.state = ConversationState.PROCESSING
        message = self.conversation_buffer.strip()
        logger.info(f"🤖 Procesando: '{message}'")

        # Notificar inicio de procesamiento via WebSocket
        await self.notify_processing_start(f"Procesando: {message}")

        try:
            # Usar la arquitectura async pura como tu sistema original
            response = await self._process_with_reasoning_interception(message)

            if response and response.strip():
                logger.info(f"💬 Respuesta final recibida: '{response[:100]}...'")

                # Notificar respuesta recibida via WebSocket
                await self.notify_response_received(response)

                logger.info("✅ Respuesta procesada con reasoning TTS")
            else:
                logger.warning("⚠️ Respuesta vacía del cliente")

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")

            logger.info("🔊 Iniciando TTS error - bloqueo dinámico activo")
            self.tts.speak("Lo siento, hubo un error procesando tu mensaje.")

            # Pequeña pausa adicional para evitar capturar eco residual
            time.sleep(0.5)

            # Limpiar reconocedor para eliminar cualquier audio contaminado acumulado
            if self.stt:
                import vosk
                self.stt.rec = vosk.KaldiRecognizer(self.stt.model, 16000)
                logger.info("🧹 Reconocedor limpiado después de error")

            logger.info("🔊 TTS error completado - bloqueo dinámico desactivado")

        # Limpiar buffer y volver a modo conversacional
        self.conversation_buffer = ""
        self.start_conversation_mode()

    def handle_speech_input(self, text: str):
        """Maneja entrada de voz según el estado actual"""
        if not text.strip():
            return

        if self.state == ConversationState.LISTENING_FOR_WAKE:
            logger.info(f"🎤 Escuchando: '{text}'")

            # Notificar texto reconocido via WebSocket
            asyncio.run_coroutine_threadsafe(
                self.notify_speech_recognized(text),
                self.event_loop
            )

            if self.detect_wake_phrase(text):
                logger.info("🌟 Frase de activación detectada!")

                # Notificar activación via WebSocket
                asyncio.run_coroutine_threadsafe(
                    self.notify_state_change(ConversationState.PROCESSING, {
                        'message': 'Aura despertando...'
                    }),
                    self.event_loop
                )

                # Enviar mensaje inicial
                try:
                    # Resetear tracking de conversación para nueva activación
                    if self.tts_buffer:
                        self.tts_buffer.reset_conversation_tracking()

                    self.state = ConversationState.PROCESSING

                    # Llamada async al cliente Gemini usando event loop persistente
                    response = self._run_async(self.gemini_client.chat("Aura, despierta"))

                    if response and response.strip():
                        self.state = ConversationState.SPEAKING

                        # Notificar respuesta recibida via WebSocket
                        asyncio.run_coroutine_threadsafe(
                            self.notify_response_received(response),
                            self.event_loop
                        )

                        # Notificar inicio TTS via WebSocket
                        asyncio.run_coroutine_threadsafe(
                            self.notify_tts_status(True, "Aura despertando"),
                            self.event_loop
                        )

                        logger.info("🔊 Iniciando TTS activación - bloqueo dinámico activo")

                        self.tts.speak(response)

                        # Pequeña pausa adicional para evitar capturar eco residual
                        time.sleep(0.5)

                        # Limpiar reconocedor para eliminar cualquier audio contaminado acumulado
                        if self.stt:
                            import vosk
                            self.stt.rec = vosk.KaldiRecognizer(self.stt.model, 16000)
                            logger.info("🧹 Reconocedor limpiado después de activación")

                        logger.info("🔊 TTS activación completado - bloqueo dinámico desactivado")

                        # Notificar fin TTS via WebSocket
                        asyncio.run_coroutine_threadsafe(
                            self.notify_tts_status(False, "Aura lista"),
                            self.event_loop
                        )

                        logger.info("✅ Aura despertada")

                    # Entrar en modo conversacional
                    self.start_conversation_mode()

                except Exception as e:
                    logger.error(f"❌ Error despertando Aura: {e}")
                    self.state = ConversationState.LISTENING_FOR_WAKE

        elif self.state == ConversationState.CONVERSATIONAL:
            # Acumular texto en buffer conversacional
            if self.conversation_buffer:
                self.conversation_buffer += " " + text
            else:
                self.conversation_buffer = text

            # Actualizar timestamp
            self.last_speech_time = time.time()

            logger.info(f"💬 Buffer: '{self.conversation_buffer}'")

            # Notificar actualización de buffer via WebSocket
            asyncio.run_coroutine_threadsafe(
                self.notify_conversation_buffer_update(),
                self.event_loop
            )

        elif self.state == ConversationState.PROCESSING:
            logger.info("⏳ Sistema procesando, ignorando entrada")

        elif self.state == ConversationState.SPEAKING:
            logger.info("🗣️ Sistema hablando, ignorando entrada")

    def listen_continuously(self):
        """Loop principal de escucha continua"""
        if not self.stt:
            logger.error("❌ STT no inicializado")
            return

        logger.info("🎤 Iniciando escucha continua...")
        self.stt.start_listening()

        try:
            while self.running:
                try:
                    # Leer datos de audio
                    data = self.stt.stream.read(4000, exception_on_overflow=False)

                    if len(data) == 0:
                        time.sleep(0.01)
                        continue

                    # VERIFICAR DINÁMICAMENTE SI EL TTS ESTÁ REPRODUCIÉNDOSE
                    if not self.is_tts_playing():
                        # Procesar con Vosk solo si TTS no está activo
                        if self.stt.rec.AcceptWaveform(data):
                            # Resultado final
                            result = json.loads(self.stt.rec.Result())
                            text = result.get('text', '').strip()

                            if text:
                                self.handle_speech_input(text)
                    else:
                        # Si TTS está activo, limpiar periódicamente el reconocedor para evitar acumulación
                        if hasattr(self, '_last_clear_time'):
                            if time.time() - self._last_clear_time > 2.0:  # Limpiar cada 2 segundos
                                import vosk
                                self.stt.rec = vosk.KaldiRecognizer(self.stt.model, 16000)
                                self._last_clear_time = time.time()
                                logger.debug("🧹 Reconocedor limpiado durante TTS dinámico")
                        else:
                            self._last_clear_time = time.time()

                    # Pequeña pausa para no saturar CPU
                    time.sleep(0.01)

                except Exception as e:
                    logger.error(f"❌ Error en loop de escucha: {e}")
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("👋 Interrupción por usuario")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpieza de recursos"""
        logger.info("🧹 Limpiando recursos...")
        self.running = False

        if self.stt:
            try:
                self.stt.close()
            except Exception as e:
                logger.error(f"Error cerrando STT: {e}")

        if self.tts:
            try:
                self.tts.close()
            except Exception as e:
                logger.error(f"Error cerrando TTS: {e}")

        if self.gemini_client:
            try:
                # Usar el event loop persistente para cleanup
                if self.event_loop and not self.event_loop.is_closed():
                    self._run_async(self.gemini_client.cleanup())
            except Exception as e:
                logger.error(f"Error cerrando cliente Gemini: {e}")

        # Cerrar event loop persistente
        if self.event_loop and not self.event_loop.is_closed():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
            if self.loop_thread:
                self.loop_thread.join(timeout=2)

        logger.info("✅ Limpieza completada")

    async def handle_websocket_client(self, websocket, path=None):
        """Maneja conexión de cliente WebSocket"""
        client_id = await self.register_client(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # En el futuro se pueden agregar comandos desde el frontend
                    # Por ahora solo enviamos confirmación
                    await self.send_to_client(client_id, {
                        'type': 'command_received',
                        'command': data.get('type', 'unknown'),
                        'timestamp': time.time()
                    })
                except json.JSONDecodeError:
                    logger.error(f"JSON inválido de {client_id}")
        except ConnectionClosed:
            logger.info(f"Cliente WebSocket desconectado: {client_id}")
        except Exception as e:
            logger.error(f"Error en cliente WebSocket {client_id}: {e}")
        finally:
            await self.unregister_client(client_id)

    def start_listening_in_thread(self):
        """Inicia escucha continua en hilo separado"""
        def listen_thread():
            try:
                self.listen_continuously()
            except Exception as e:
                logger.error(f"❌ Error en hilo de escucha: {e}")

        self.listening_thread = threading.Thread(target=listen_thread, daemon=True)
        self.listening_thread.start()
        logger.info("🎤 Hilo de escucha iniciado")

    async def start_websocket_server(self):
        """Inicia el servidor WebSocket"""
        logger.info(f"🌐 Iniciando servidor WebSocket en ws://{self.host}:{self.port}")

        async with websockets.serve(
            self.handle_websocket_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5
        ):
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("🛑 Cerrando servidor WebSocket...")

    async def run_async(self):
        """Ejecutar el sistema principal (versión async)"""
        logger.info("🚀 Iniciando sistema Aura Global con WebSocket...")

        # Inicializar componentes
        if not self.init_components():
            logger.error("❌ Fallo en inicialización, abortando")
            return 1

        # Iniciar escucha continua en hilo separado
        self.start_listening_in_thread()

        # Mensaje de bienvenida
        logger.info("🎯 Sistema listo - Di 'Aura despierta' para activar")
        logger.info(f"🌐 WebSocket disponible en ws://{self.host}:{self.port}")
        logger.info("⌨️ Presiona Ctrl+C para salir")

        try:
            # Iniciar servidor WebSocket (esto mantiene el programa ejecutándose)
            await self.start_websocket_server()
            return 0

        except Exception as e:
            logger.error(f"❌ Error crítico: {e}")
            return 1

    def run(self):
        """Wrapper síncrono para run_async"""
        return asyncio.run(self.run_async())

def main():
    """Función principal"""
    system = AuraGlobalSystem()
    return system.run()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)