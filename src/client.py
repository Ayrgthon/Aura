#!/usr/bin/env python3
"""
Cliente unificado de Aura con Google Gemini integrado
Fusiona gemini_client.py y client.py en un solo archivo
"""
import os
import asyncio
import threading
import warnings
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Iterator, Callable
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Cargar variables de entorno desde .env
load_dotenv()

# Silenciar todos los warnings molestos
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Importar módulos de voz
try:
    # Intentar imports relativos primero (cuando se usa como módulo)
    from ..engine.voice.hear import initialize_recognizer, listen_for_command
    from ..engine.voice.speak import (
        speak, stop_speaking, is_speaking,
        start_streaming_tts, add_text_to_stream, finish_streaming_tts,
        StreamingTTS, VoiceSynthesizer, get_synthesizer, speak_async
    )
    VOICE_AVAILABLE = True
    print("✅ Módulos de voz cargados correctamente")
except ImportError:
    try:
        # Si falla, intentar imports absolutos (cuando se ejecuta desde src/)
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        sys.path.append(parent_dir)
        
        from engine.voice.hear import initialize_recognizer, listen_for_command
        from engine.voice.speak import (
            speak, stop_speaking, is_speaking,
            start_streaming_tts, add_text_to_stream, finish_streaming_tts,
            StreamingTTS, VoiceSynthesizer, get_synthesizer, speak_async
        )
        VOICE_AVAILABLE = True
        print("✅ Módulos de voz cargados correctamente")
    except ImportError as e:
        VOICE_AVAILABLE = False
        print(f"⚠️ Módulos de voz no disponibles: {e}")
        print("💡 Instala las dependencias con: pip install -r requirements.txt")

# Importaciones para MCP nativo
try:
    # Intentar import relativo primero
    from .mcp_client_native import NativeMCPClient, MCPToolCall
    MCP_NATIVE_AVAILABLE = True
except ImportError:
    try:
        # Si falla, intentar import absoluto (cuando se ejecuta desde src/)
        from mcp_client_native import NativeMCPClient, MCPToolCall
        MCP_NATIVE_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️ Error cargando MCP nativo: {e}")
        NativeMCPClient = None
        MCPToolCall = None
        MCP_NATIVE_AVAILABLE = False

# Verificar disponibilidad de Google Gemini
try:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("⚠️ GOOGLE_API_KEY no encontrada en las variables de entorno")
        GEMINI_AVAILABLE = False
    else:
        GEMINI_AVAILABLE = True
        genai.configure(api_key=google_api_key)
except ImportError as e:
    print(f"⚠️ Google Gemini no disponible: {e}")
    GEMINI_AVAILABLE = False


class Message:
    """Clase simple para representar mensajes"""
    def __init__(self, role: str, content: str):
        self.role = role  # 'user', 'model', 'system'
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class StreamingCallback:
    """Callback handler para streaming con TTS"""
    
    def __init__(self, 
                 tts_callback: Optional[Callable[[str], None]] = None,
                 voice_enabled: bool = False):
        """
        Inicializa el callback handler
        
        Args:
            tts_callback: Función para reproducir texto con TTS
            voice_enabled: Si la voz está habilitada
        """
        self.tts_callback = tts_callback
        self.voice_enabled = voice_enabled
        self.full_response = ""
        self.first_sentence_done = False
        self.remaining_buffer = ""
        self.streaming_tts = None
        
        # Intentar importar funciones de TTS
        if VOICE_AVAILABLE:
            self.tts_available = True
        else:
            self.tts_available = False
    
    def on_token(self, token: str):
        """
        Llamado cuando se recibe un nuevo token
        
        Args:
            token: Nuevo token generado
        """
        # Imprimir el token
        print(token, end='', flush=True)
        self.full_response += token
        
        # Manejar TTS streaming
        if self.voice_enabled and self.tts_available:
            if not self.first_sentence_done:
                # Iniciar streaming TTS si aún no está iniciado
                if self.streaming_tts is None:
                    try:
                        self.streaming_tts = start_streaming_tts()
                    except Exception as e:
                        print(f"\n❌ Error iniciando TTS streaming: {e}")
                
                # Agregar token al stream
                if self.streaming_tts:
                    try:
                        add_text_to_stream(token)
                    except Exception as e:
                        print(f"\n❌ Error en TTS chunk: {e}")
                
                # Detectar final de primera oración
                if '.' in token or '!' in token or '?' in token:
                    if self.streaming_tts:
                        try:
                            finish_streaming_tts()
                        except Exception:
                            pass
                        self.streaming_tts = None
                    self.first_sentence_done = True
            else:
                # Guardar el resto para reproducir después
                self.remaining_buffer += token
    
    def on_complete(self):
        """Llamado cuando se completa la generación"""
        # Finalizar streaming TTS si aún está activo
        if self.streaming_tts:
            try:
                finish_streaming_tts()
            except Exception:
                pass
        
        # Reproducir el resto del texto
        if (self.first_sentence_done and 
            self.remaining_buffer.strip() and 
            self.voice_enabled and 
            self.tts_available):
            try:
                speak_async(self.remaining_buffer.strip())
            except Exception as e:
                print(f"\n❌ Error reproduciendo resto del texto: {e}")
    
    def on_error(self, error: Exception):
        """
        Llamado cuando ocurre un error
        
        Args:
            error: Error ocurrido
        """
        print(f"\n❌ Error en streaming: {error}")
        if self.streaming_tts:
            try:
                finish_streaming_tts()
            except Exception:
                pass


class AuraClient:
    """Cliente unificado de Aura con Google Gemini integrado"""
    
    def __init__(self, 
                 model_name: Optional[str] = None,
                 context_size: int = 100000, 
                 enable_voice: bool = True,
                 temperature: float = 0.01,
                 max_output_tokens: Optional[int] = None):
        """
        Inicializa el cliente Aura con soporte solo para Gemini
        
        Args:
            model_name: Nombre específico del modelo Gemini (opcional)
            context_size: Tamaño del contexto
            enable_voice: Si habilitar capacidades de voz
            temperature: Temperatura para la generación
            max_output_tokens: Máximo de tokens de salida
        """
        if not GEMINI_AVAILABLE:
            raise Exception("Google Gemini no está disponible. Verifica GOOGLE_API_KEY y dependencias.")
        
        self.model_name = model_name or "gemini-2.5-pro"
        self.context_size = context_size
        self.voice_enabled = enable_voice
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        
        # Configuración de seguridad (permisiva para uso interno)
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Inicializar modelo de Gemini
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings
        )
        
        print(f"✅ Cliente Gemini inicializado: {self.model_name}")
        
        # Mensaje de sistema para guiar la salida a un formato fácil de leer en voz
        system_instructions = (
            "Eres AURA, un asistente de voz en español. "
            "Responde de forma clara, conversacional y sin utilizar markdown ni caracteres especiales como *, #, **, guiones bajos, etc. "
            "Si necesitas enumerar, utiliza guiones simples '-' al inicio de cada punto. "
            "Mantén las oraciones cortas para que se lean naturalmente en voz alta. "
            "Evita emojis y símbolos innecesarios."
        )

        self.conversation_history: List[Message] = [
            Message(role="system", content=system_instructions)
        ]
        
        # Reactivar TTS de forma controlada
        self.voice_synthesizer = None
        if self.voice_enabled:
            self._initialize_voice()
        
        # Lock para controlar orden del audio
        self.audio_lock = threading.Lock()
        
        # Cliente MCP nativo
        self.mcp_client = None
        self.mcp_tools = []
        
        print(f"✅ Cliente Aura inicializado con Gemini")
    
    def _initialize_voice(self):
        """Inicializa las capacidades de voz"""
        if not VOICE_AVAILABLE:
            print("⚠️ Módulos de voz no disponibles")
            self.voice_enabled = False
            return
            
        try:
            self.voice_synthesizer = get_synthesizer()
            if self.voice_synthesizer.initialized:
                print("🎤 Sistema de voz activado")
            else:
                print("⚠️ Sistema de voz no pudo inicializarse")
                self.voice_enabled = False
        except Exception as e:
            print(f"⚠️ Error inicializando voz: {e}")
            self.voice_enabled = False
    
    def speak_text(self, text: str):
        """
        Reproduce texto usando síntesis de voz
        
        Args:
            text: Texto a reproducir
        """
        if self.voice_enabled and self.voice_synthesizer:
            self.voice_synthesizer.speak(text)
        else:
            print("🔇 Voz no disponible")
    
    def _messages_to_gemini_format(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        Convierte mensajes al formato esperado por Gemini
        
        Args:
            messages: Lista de mensajes
            
        Returns:
            Lista de mensajes en formato Gemini
        """
        gemini_messages = []
        
        for msg in messages:
            # Gemini usa 'user' y 'model' como roles
            if msg.role == 'system':
                # Los mensajes de sistema se convierten a mensajes de usuario
                gemini_messages.append({
                    'role': 'user',
                    'parts': [msg.content]
                })
            elif msg.role == 'user':
                gemini_messages.append({
                    'role': 'user', 
                    'parts': [msg.content]
                })
            elif msg.role in ['model', 'assistant']:
                gemini_messages.append({
                    'role': 'model',
                    'parts': [msg.content]
                })
        
        return gemini_messages
    
    def generate(self, messages: List[Message], tools: Optional[List[Any]] = None) -> str:
        """
        Genera una respuesta sin streaming
        
        Args:
            messages: Lista de mensajes de la conversación
            tools: Lista de herramientas/funciones disponibles
            
        Returns:
            Respuesta del modelo
        """
        try:
            # Preparar mensajes
            if len(messages) == 1:
                # Para un solo mensaje, usar generate_content directamente
                response = self.model.generate_content(
                    messages[0].content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_output_tokens
                    ),
                    tools=tools
                )
            else:
                # Para múltiples mensajes, usar chat
                gemini_messages = self._messages_to_gemini_format(messages)
                chat = self.model.start_chat(history=gemini_messages[:-1])
                response = chat.send_message(
                    gemini_messages[-1]['parts'][0],
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_output_tokens
                    ),
                    tools=tools
                )
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Error generando respuesta: {e}")
    
    def stream(self, messages: List[Message], 
               tools: Optional[List[Any]] = None,
               callback: Optional[Callable[[str], None]] = None) -> Iterator[str]:
        """
        Genera una respuesta con streaming
        
        Args:
            messages: Lista de mensajes de la conversación
            tools: Lista de herramientas/funciones disponibles
            callback: Función de callback para cada chunk
            
        Yields:
            Chunks de texto de la respuesta
        """
        try:
            # Preparar mensajes
            if len(messages) == 1:
                # Para un solo mensaje, usar generate_content con streaming
                response = self.model.generate_content(
                    messages[0].content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_output_tokens
                    ),
                    tools=tools,
                    stream=True
                )
            else:
                # Para múltiples mensajes, usar chat con streaming
                gemini_messages = self._messages_to_gemini_format(messages)
                chat = self.model.start_chat(history=gemini_messages[:-1])
                response = chat.send_message(
                    gemini_messages[-1]['parts'][0],
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_output_tokens
                    ),
                    tools=tools,
                    stream=True
                )
            
            # Procesar chunks
            for chunk in response:
                if chunk.text:
                    if callback:
                        callback(chunk.text)
                    yield chunk.text
                    
        except Exception as e:
            error_msg = f"Error en streaming: {e}"
            if callback:
                callback(error_msg)
            yield error_msg
    
    def generate_with_tools(self, messages: List[Message], 
                           tools: List[Any]) -> Dict[str, Any]:
        """
        Genera una respuesta que puede incluir llamadas a herramientas
        
        Args:
            messages: Lista de mensajes de la conversación
            tools: Lista de herramientas disponibles (formato Gemini)
            
        Returns:
            Dict con la respuesta y posibles llamadas a herramientas
        """
        try:
            # Preparar herramientas si las hay
            gemini_tools = None
            if tools:
                # Las herramientas ya vienen en formato Gemini desde MCP client
                gemini_tools = tools
            
            # Preparar mensajes
            if len(messages) == 1:
                response = self.model.generate_content(
                    messages[0].content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_output_tokens
                    ),
                    tools=gemini_tools
                )
            else:
                gemini_messages = self._messages_to_gemini_format(messages)
                chat = self.model.start_chat(history=gemini_messages[:-1])
                response = chat.send_message(
                    gemini_messages[-1]['parts'][0],
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_output_tokens
                    ),
                    tools=gemini_tools
                )
            
            result = {
                'text': '',
                'tool_calls': []
            }
            
            # Procesar la respuesta de Gemini
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                if hasattr(candidate, 'content') and candidate.content and candidate.content.parts:
                    text_parts = []
                    
                    for part in candidate.content.parts:
                        # Manejar partes de texto
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                        
                        # Manejar llamadas a funciones
                        elif hasattr(part, 'function_call') and part.function_call:
                            try:
                                # Verificar que function_call tiene los atributos necesarios
                                if hasattr(part.function_call, 'name') and part.function_call.name:
                                    tool_call = {
                                        'name': part.function_call.name,
                                        'args': dict(part.function_call.args) if hasattr(part.function_call, 'args') and part.function_call.args else {}
                                    }
                                    result['tool_calls'].append(tool_call)
                            except Exception as e:
                                # Si hay error procesando una function_call, continuar con las demás
                                print(f"⚠️  Error procesando function_call: {e}")
                                continue
                    
                    # Combinar todas las partes de texto
                    result['text'] = ''.join(text_parts)
            
            return result
            
        except Exception as e:
            raise Exception(f"Error generando respuesta con herramientas: {e}")

    async def setup_mcp_servers(self, mcp_configs: Dict[str, Dict] = None):
        """
        Configura servidores MCP usando la librería oficial
        
        Args:
            mcp_configs: Configuración de servidores MCP
        """
        if not MCP_NATIVE_AVAILABLE or not NativeMCPClient:
            print("❌ MCP SDK oficial no está instalado")
            print("💡 Instala con: pip install mcp")
            return False
            
        try:
            # Crear cliente MCP nativo
            self.mcp_client = NativeMCPClient()
            
            # Configurar servidores
            success = await self.mcp_client.setup_servers(mcp_configs)
            
            if success:
                # Obtener herramientas disponibles
                self.mcp_tools = self.mcp_client.tools
                return True
            else:
                self.mcp_client = None
                self.mcp_tools = []
                return False
            
        except Exception as e:
            print(f"❌ Error configurando MCPs: {e}")
            print("ℹ️ Asegúrate de tener Node.js y npm instalados para usar servidores MCP")
            self.mcp_client = None
            self.mcp_tools = []
            return False
    
    async def _execute_mcp_tool(self, tool_call: Dict[str, Any]) -> str:
        """
        Ejecuta una herramienta MCP usando la librería oficial
        
        Args:
            tool_call: Información de la llamada a la herramienta
            
        Returns:
            Resultado de la herramienta
        """
        if not self.mcp_client:
            raise Exception("Cliente MCP no inicializado")
        
        tool_name = tool_call['name']
        tool_args = tool_call.get('args', {})
        
        # Verificar que la herramienta existe
        tool_exists = any(tool.name == tool_name for tool in self.mcp_tools)
        if not tool_exists:
            raise Exception(f"Herramienta '{tool_name}' no encontrada")
        
        # Ejecutar la herramienta usando el cliente nativo
        try:
            result = await self.mcp_client.execute_tool(tool_name, tool_args)
            return result
        except Exception as e:
            raise Exception(f"Error ejecutando herramienta '{tool_name}': {e}")

    async def chat_with_voice(self, user_input: str) -> str:
        """
        Realiza una conversación con entrada de texto y salida de voz con streaming.
        Soporta Gemini con herramientas MCP con síntesis natural.
        
        Args:
            user_input: El mensaje del usuario
            
        Returns:
            La respuesta del asistente
        """
        try:
            # Agregar mensaje del usuario al historial
            self.conversation_history.append(Message(role="user", content=user_input))
            
            # Usar un enfoque de dos fases si hay herramientas MCP
            if self.mcp_tools:
                return await self._chat_with_mcp_synthesis(user_input)
            else:
                return await self._chat_without_mcp(user_input)
            
        except Exception as e:
            error_msg = f"❌ Error en chat: {e}"
            print(error_msg)
            return error_msg
    
    async def _chat_with_mcp_synthesis(self, user_input: str) -> str:
        """
        Chat con MCPs usando agente multipasos - puede ejecutar múltiples rondas de herramientas
        """
        print(f"🔧 Usando {len(self.mcp_tools)} herramientas MCP con Gemini")
        
        all_tool_results = []
        max_iterations = 5  # Máximo de iteraciones para evitar loops infinitos
        iteration = 0
        
        try:
            current_conversation = self.conversation_history.copy()
            
            while iteration < max_iterations:
                iteration += 1
                print(f"🔄 Iteración {iteration}")
                
                # Convertir herramientas MCP al formato de Gemini
                gemini_tools = self.mcp_client.get_tools_for_gemini() if self.mcp_client else []
                
                # Obtener respuesta con herramientas
                response = self.generate_with_tools(current_conversation, gemini_tools)
                
                # Verificar si se usaron herramientas MCP en esta iteración
                if response.get('tool_calls'):
                    print(f"🔍 Ejecutando {len(response['tool_calls'])} herramientas...")
                    
                    # Ejecutar herramientas de esta iteración
                    iteration_results = []
                    for tool_call in response['tool_calls']:
                        print(f"🔧 Ejecutando: {tool_call['name']}")
                        
                        try:
                            tool_result = await self._execute_mcp_tool(tool_call)
                            tool_result_data = {
                                'tool_name': tool_call['name'],
                                'query': tool_call.get('args', {}),
                                'result': tool_result
                            }
                            iteration_results.append(tool_result_data)
                            all_tool_results.append(tool_result_data)
                            print(f"✅ {tool_call['name']} completado")
                            
                        except Exception as e:
                            print(f"❌ Error en {tool_call['name']}: {e}")
                            error_result = {
                                'tool_name': tool_call['name'],
                                'query': tool_call.get('args', {}),
                                'result': f"Error: {e}"
                            }
                            iteration_results.append(error_result)
                            all_tool_results.append(error_result)
                    
                    # Agregar los resultados de las herramientas a la conversación
                    results_text = "\n".join([
                        f"Resultado de {r['tool_name']}: {r['result']}"
                        for r in iteration_results
                    ])
                    
                    # Actualizar conversación con resultados
                    current_conversation.append(Message(role="user", content=f"Resultados de herramientas: {results_text}"))
                    
                    # Preguntar al LLM si necesita más herramientas
                    continue_prompt = (
                        f"Basándote en los resultados anteriores, ¿necesitas ejecutar más herramientas para completar "
                        f"la solicitud original del usuario: '{user_input}'? "
                        f"Si necesitas más información, ejecuta las herramientas necesarias. "
                        f"Si ya tienes suficiente información, responde directamente al usuario."
                    )
                    current_conversation.append(Message(role="user", content=continue_prompt))
                    
                else:
                    # No se usaron herramientas, el LLM considera que ya terminó
                    print("✅ El agente considera completada la tarea")
                    
                    # Si no hay tool results, respuesta directa
                    if not all_tool_results:
                        return await self._stream_response(response.get('text', ''))
                    
                    # Si hay resultados, hacer síntesis final
                    break
            
            # Si llegamos aquí, hacer síntesis final con todos los resultados
            if all_tool_results:
                print(f"\n🧠 Procesando información de {len(all_tool_results)} herramientas ejecutadas...")
                return await self._synthesize_natural_response(user_input, all_tool_results)
            else:
                # Sin herramientas ejecutadas, respuesta simple
                return await self._chat_without_mcp(user_input)
        
        except Exception as e:
            print(f"❌ Error en procesamiento MCP: {e}")
            # Fallback a respuesta simple
            return await self._chat_without_mcp(user_input)
    
    async def _synthesize_natural_response(self, user_input: str, tool_results: List[Dict]) -> str:
        """
        Sintetiza una respuesta natural basada en los resultados de las herramientas MCP
        """
        # Construir contexto con información recopilada
        context_parts = [
            f"Pregunta del usuario: {user_input}",
            "\nInformación recopilada:",
        ]
        
        for result in tool_results:
            context_parts.append(
                f"\n• De {result['tool_name']}: {result['result'][:1500]}..."  # Limitar longitud
            )
        
        context_parts.append(
            "\nInstrucciones: Basándote en la información anterior, responde la pregunta del usuario de manera natural y conversacional, como si fueras una persona hablando. NO menciones herramientas, APIs o resultados técnicos. NO leas literalmente los resultados. Sintetiza la información y responde directamente la pregunta con un tono humano y natural."
        )
        
        synthesis_prompt = "".join(context_parts)
        
        # Crear nueva conversación temporal para la síntesis
        synthesis_messages = [Message(role="user", content=synthesis_prompt)]
        
        # Generar respuesta natural
        try:
            natural_response = ""
            
            # Crear callback para streaming con TTS
            streaming_callback = StreamingCallback(
                voice_enabled=self.voice_enabled
            )
            
            # Streaming de la respuesta sintetizada
            for chunk in self.stream(synthesis_messages, callback=streaming_callback.on_token):
                natural_response += chunk
            streaming_callback.on_complete()
            
            print()  # Nueva línea
            
            # Agregar la respuesta sintetizada al historial
            self.conversation_history.append(Message(role="assistant", content=natural_response))
            return natural_response
            
        except Exception as e:
            print(f"❌ Error en síntesis: {e}")
            # Fallback: usar la información bruta pero de forma más limpia
            fallback_response = f"Según la información encontrada: {tool_results[0]['result'][:500]}..."
            print(fallback_response)
            
            self.conversation_history.append(Message(role="assistant", content=fallback_response))
            return fallback_response
    
    async def _chat_without_mcp(self, user_input: str) -> str:
        """
        Chat normal sin herramientas MCP
        """
        print("🤖 Usando Gemini sin herramientas MCP")
        
        try:
            # Crear callback para streaming con TTS
            streaming_callback = StreamingCallback(
                voice_enabled=self.voice_enabled
            )
            
            response_text = ""
            for chunk in self.stream(self.conversation_history, callback=streaming_callback.on_token):
                response_text += chunk
            
            streaming_callback.on_complete()
            print()  # Nueva línea
            
            self.conversation_history.append(Message(role="assistant", content=response_text))
            return response_text
            
        except Exception as e:
            print(f"❌ Error en chat simple: {e}")
            return f"Error: {e}"
    
    async def _stream_response(self, content: str) -> str:
        """
        Reproduce una respuesta con streaming y TTS por oraciones
        """
        print(content)

        # Reproducir todo el texto con el mecanismo robusto (speak_async maneja división)
        if self.voice_enabled and VOICE_AVAILABLE:
            speak_async(content)
        
        print()  # Nueva línea
        self.conversation_history.append(Message(role="assistant", content=content))
        return content

    def add_allowed_directories_context(self, allowed_dirs: List[str]):
        """Agrega al historial un mensaje de sistema con los directorios permitidos.

        Esto ayuda al modelo a mapear nombres hablados como "Documentos" al path real.
        """
        if not allowed_dirs:
            return
        # Construir el texto explicativo
        dirs_formatted = ", ".join(allowed_dirs)
        # Crear alias insensibles a mayúsculas
        alias_lines = []
        for path in allowed_dirs:
            base = os.path.basename(path)
            if base:
                alias_lines.append(f"  - '{base.lower()}' → {path}")

        alias_block = "\n".join(alias_lines)

        # Instrucciones y ejemplos claros
        instructions_block = (
            "Instrucciones para el uso de herramientas:\n"
            "- Siempre que el usuario pida listar, abrir, leer o similar sobre una carpeta o archivo, deduce la ruta completa usando los alias.\n"
            "- Llama a la herramienta adecuada sin solicitar más pistas al usuario.\n"
            "Ejemplos:\n"
            "  • Usuario: 'lista la carpeta documentos' → Usa list_directory con path='/home/ary/Documentos'.\n"
            "  • Usuario: 'abre documents' → Usa list_directory con path='/home/ary/Documents'.\n"
        )

        extra_context = (
            "Contexto: Estos son los directorios disponibles (acceso garantizado): "
            f"{dirs_formatted}.\n"
            "Alias útiles (no distinguen mayúsculas/minúsculas):\n"
            f"{alias_block}.\n"
            f"{instructions_block}"
            "Recuerda NO preguntar rutas completas; usa los alias para resolverlas automáticamente."
        )
        # Insertar justo después del mensaje de instrucciones original para mantener prioridad
        insert_index = 1 if len(self.conversation_history) >= 1 else 0
        self.conversation_history.insert(insert_index, Message(role="user", content=extra_context))
    
    async def cleanup(self):
        """Limpia recursos, especialmente conexiones MCP"""
        if self.mcp_client:
            try:
                await self.mcp_client.cleanup()
                print("🧹 Conexiones MCP cerradas")
            except Exception as e:
                print(f"⚠️ Error cerrando conexiones MCP: {e}")