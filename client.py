#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
import tempfile
import warnings
import logging
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout
from gtts import gTTS
import pygame
from typing import List, Dict, Any, Iterator, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# Silenciar todos los warnings molestos
warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated!")
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configurar logging para silenciar mensajes de schema
logging.getLogger("langchain").setLevel(logging.ERROR)
logging.getLogger("langchain_core").setLevel(logging.ERROR)
logging.getLogger("langchain_google_genai").setLevel(logging.ERROR)

# Importar módulos de voz
try:
    from engine.voice.hear import initialize_recognizer, listen_for_command
    from engine.voice.speak import (
        speak, stop_speaking, is_speaking,
        start_streaming_tts, add_text_to_stream, finish_streaming_tts,
        StreamingTTS, VoiceSynthesizer, get_synthesizer
    )
    VOICE_AVAILABLE = True
    print("✅ Módulos de voz cargados correctamente")
    print("🔧 Funciones streaming TTS importadas:", 
          start_streaming_tts.__name__, add_text_to_stream.__name__, finish_streaming_tts.__name__)
except ImportError as e:
    VOICE_AVAILABLE = False
    print(f"⚠️ Módulos de voz no disponibles: {e}")
    print("💡 Instala las dependencias con: pip install -r requirements.txt")
    StreamingTTS = None
    VoiceSynthesizer = None
    get_synthesizer = None

# Importaciones para MCP
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError as e:
    print(f"⚠️  Error cargando MCP: {e}")
    MultiServerMCPClient = None

# Configurar API Key de Google
os.environ["GOOGLE_API_KEY"] = "YOUR_GOOGLE_API_KEY_HERE"

class StreamingCallbackHandler(BaseCallbackHandler):
    """
    Callback handler para manejar streaming de respuestas
    """
    def __init__(self, voice_streaming=False, voice_enabled=False):
        super().__init__()
        self.voice_streaming = voice_streaming
        self.voice_enabled = voice_enabled
        self.streaming_tts = None
        self.full_response = ""
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Llamado cuando el LLM comienza a generar"""
        if self.voice_streaming and self.voice_enabled:
            try:
                self.streaming_tts = start_streaming_tts()
                print("🗣️ TTS en paralelo activado (via callbacks)")
            except Exception as e:
                print(f"❌ Error al inicializar TTS streaming: {e}")
                self.streaming_tts = None
                
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Llamado cuando se genera un nuevo token"""
        # Imprimir el token
        print(token, end='', flush=True)
        self.full_response += token
        
        # Enviar chunk al TTS en paralelo
        if self.streaming_tts and self.voice_streaming:
            try:
                add_text_to_stream(token)
            except Exception as e:
                print(f"\n❌ Error en TTS chunk: {e}")
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Llamado cuando ocurre un error"""
        print(f"\n❌ Error en LLM: {error}")
        if self.streaming_tts:
            try:
                finish_streaming_tts()
            except:
                pass
                
    def on_llm_end(self, response, **kwargs: Any) -> None:
        """Llamado cuando el LLM termina de generar"""
        # Finalizar TTS streaming
        if self.streaming_tts:
            try:
                finish_streaming_tts()
            except Exception as e:
                print(f"\n❌ Error al finalizar TTS streaming: {e}")

class GeminiClient:
    def __init__(self, context_size=100000, enable_voice=True):
        """
        Inicializa el cliente de Google Gemini usando LangChain
        
        Args:
            context_size (int): Tamaño del contexto en tokens
            enable_voice (bool): Si True, habilita funcionalidades de voz
        """
        self.model_name = "gemini-2.0-flash-exp"
        self.context_size = context_size
        self.conversation_history: List[BaseMessage] = []
        
        # Configuración de voz
        self.voice_enabled = enable_voice and VOICE_AVAILABLE
        self.voice_recognizer = None
        
        # Inicializar modelo de LangChain
        try:
            # Crear el modelo con configuración para streaming
            self.model = ChatGoogleGenerativeAI(
                model=self.model_name,
                max_output_tokens=2048,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                convert_system_message_to_human=True  # Para manejar mensajes del sistema
            )
            print(f"✅ Modelo {self.model_name} inicializado correctamente")
        except Exception as e:
            print(f"❌ Error al inicializar modelo: {e}")
            # Intentar con un modelo alternativo
            try:
                self.model_name = "gemini-1.5-flash"
                self.model = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    max_output_tokens=2048,
                    temperature=0.7,
                    convert_system_message_to_human=True
                )
                print(f"✅ Modelo alternativo {self.model_name} inicializado")
            except:
                self.model = None
        
        if self.voice_enabled:
            self._initialize_voice()
        
        # Lock para controlar orden del audio
        self.audio_lock = threading.Lock()
        
        # Cliente MCP
        self.mcp_client = None
        self.mcp_tools = []
        
        # Inicializar pygame para audio
        pygame.mixer.init()
        
        print("✅ Cliente Gemini inicializado correctamente")
    
    def _initialize_voice(self):
        """
        Inicializa los componentes de voz
        """
        if get_synthesizer:
            try:
                self.voice_recognizer = initialize_recognizer()
                if self.voice_recognizer:
                    print("🎤 Sistema de voz activado")
                else:
                    print("⚠️  Sistema de voz no pudo inicializarse")
                    self.voice_enabled = False
            except Exception as e:
                print(f"⚠️  Error inicializando voz: {e}")
                self.voice_enabled = False
        else:
            print("⚠️  Módulos de voz no disponibles")
            self.voice_enabled = False
    
    def listen_to_voice(self, timeout=5):
        """
        Escucha entrada de voz del usuario
        
        Args:
            timeout (int): Tiempo límite de escucha
            
        Returns:
            str: Texto reconocido de la voz
        """
        if not self.voice_enabled or not self.voice_recognizer:
            print("❌ Funcionalidad de voz no disponible")
            return ""
        
        return listen_for_command(self.voice_recognizer, timeout)
    
    def speak_response(self, text):
        """
        Convierte respuesta a voz
        
        Args:
            text (str): Texto a convertir en voz
        """
        if not self.voice_enabled:
            return
        
        speak(text)

    def is_server_running(self):
        """
        Verifica si el modelo está disponible
        
        Returns:
            bool: True si el modelo está listo, False en caso contrario
        """
        return self.model is not None
    
    def list_models(self):
        """
        Lista los modelos disponibles (en este caso, solo Gemini)
        
        Returns:
            list: Lista de modelos disponibles
        """
        if self.model:
            return [self.model_name]
        return []
    
    def generate_response(self, prompt, stream=False, use_history=True, voice_streaming=False):
        """
        Genera una respuesta usando el modelo Gemini
        
        Args:
            prompt (str): El prompt/pregunta para el modelo
            stream (bool): Si True, transmite la respuesta en tiempo real
            use_history (bool): Si True, incluye el historial de conversación
            voice_streaming (bool): Si True, activa TTS en paralelo
            
        Returns:
            str: La respuesta del modelo
        """
        if not prompt.strip():
            return "Prompt vacío"
            
        if not self.model:
            return "❌ Error: Modelo no inicializado"
        
        try:
            # Construir lista de mensajes
            messages = []
            
            # Incluir historial si está habilitado
            if use_history and self.conversation_history:
                # Limitar el historial para no exceder el contexto
                recent_history = self._get_recent_history()
                messages.extend(recent_history)
            
            # Agregar el mensaje actual
            messages.append(HumanMessage(content=prompt))
            
            if stream:
                response_text = self._stream_response(messages, voice_streaming)
            else:
                # Respuesta sin streaming
                response = self.model.invoke(messages)
                response_text = response.content
                
                if not response_text.strip():
                    print("⚠️ La respuesta del modelo está vacía")
                    return "Sin respuesta"
            
            # Agregar al historial si está habilitado y hay respuesta válida
            if use_history and response_text and response_text != "Sin respuesta":
                self._add_to_history("user", prompt)
                self._add_to_history("assistant", response_text)
            
            return response_text
            
        except Exception as e:
            error_msg = f"❌ Error al generar respuesta: {e}"
            print(error_msg)
            return error_msg
    
    def _get_recent_history(self):
        """
        Obtiene el historial reciente limitado por contexto
        
        Returns:
            list: Lista de mensajes recientes
        """
        max_history_messages = 10
        if len(self.conversation_history) > max_history_messages:
            return self.conversation_history[-max_history_messages:]
        return self.conversation_history
    
    def _add_to_history(self, role, content):
        """
        Agrega una entrada al historial de conversación
        
        Args:
            role (str): 'user' o 'assistant'
            content (str): El contenido del mensaje
        """
        if role == "user":
            self.conversation_history.append(HumanMessage(content=content))
        else:
            self.conversation_history.append(AIMessage(content=content))
        
        # Mantener el historial dentro del límite
        self._trim_history_if_needed()
    
    def _trim_history_if_needed(self):
        """
        Recorta el historial si excede el límite de contexto
        """
        # Estimación aproximada: 1 token ≈ 4 caracteres
        total_chars = sum(len(msg.content) for msg in self.conversation_history)
        max_chars = self.context_size * 3  # Dejar espacio para la respuesta
        
        while total_chars > max_chars and len(self.conversation_history) > 2:
            # Remover las entradas más antiguas (pero mantener al menos 1 par)
            removed = self.conversation_history.pop(0)
            total_chars -= len(removed.content)
    
    def clear_history(self):
        """
        Limpia el historial de conversación
        """
        self.conversation_history = []
        print("🗑️ Historial de conversación limpiado")
    
    def show_context_info(self):
        """
        Muestra información sobre el contexto configurado
        """
        print(f"📊 Información de Contexto:")
        print(f"   • Modelo: {self.model_name}")
        print(f"   • Contexto configurado: {self.context_size:,} tokens")
        print(f"   • Historial: {len(self.conversation_history)} mensajes")
        
        if self.conversation_history:
            total_chars = sum(len(msg.content) for msg in self.conversation_history)
            estimated_tokens = total_chars // 4
            print(f"   • Tokens estimados en historial: {estimated_tokens:,}")
            usage_percent = (estimated_tokens / self.context_size) * 100
            print(f"   • Uso del contexto: {usage_percent:.1f}%")
    
    def _stream_response(self, messages, enable_voice_streaming=False):
        """
        Maneja las respuestas en streaming
        
        Args:
            messages (list): Lista de mensajes para el modelo
            enable_voice_streaming (bool): Si True, activa TTS en paralelo
            
        Returns:
            str: Respuesta completa
        """
        try:
            print("Respuesta del modelo (streaming):")
            
            # Buffer para acumular la respuesta completa
            full_response = ""
            streaming_tts = None
            
            # Inicializar TTS streaming si está habilitado
            if enable_voice_streaming and self.voice_enabled:
                try:
                    streaming_tts = start_streaming_tts()
                    print("🗣️ TTS en paralelo activado")
                except Exception as e:
                    print(f"❌ Error al inicializar TTS streaming: {e}")
                    streaming_tts = None
            
            # Usar el método stream() nativo de LangChain
            try:
                # El método stream() ya está implementado en ChatGoogleGenerativeAI
                for chunk in self.model.stream(messages):
                    # Cada chunk es un AIMessageChunk con contenido
                    chunk_content = ""
                    if hasattr(chunk, 'content'):
                        chunk_content = chunk.content
                    elif isinstance(chunk, str):
                        chunk_content = chunk
                    
                    if chunk_content:
                        print(chunk_content, end='', flush=True)
                        full_response += chunk_content
                        
                        # Enviar chunk al TTS en paralelo
                        if streaming_tts:
                            try:
                                add_text_to_stream(chunk_content)
                            except Exception as e:
                                print(f"\n❌ Error en TTS chunk: {e}")
                                
            except Exception as e:
                # Si hay algún error con streaming, usar invoke normal
                print(f"\n⚠️ Error en streaming ({e}), usando modo no-streaming...")
                
                # Usar invoke normal sin streaming
                response = self.model.invoke(messages)
                
                if hasattr(response, 'content'):
                    full_response = response.content
                    print(full_response)
                else:
                    full_response = str(response)
                    print(full_response)
                
                # Reproducir la respuesta completa con TTS si está habilitado
                if streaming_tts and full_response:
                    try:
                        add_text_to_stream(full_response)
                    except Exception as e:
                        print(f"\n❌ Error en TTS: {e}")
            
            # Finalizar TTS streaming
            if streaming_tts:
                try:
                    finish_streaming_tts()
                except Exception as e:
                    print(f"\n❌ Error al finalizar TTS streaming: {e}")
            
            print()  # Nueva línea al final
            
            if not full_response.strip():
                print("\n⚠️ La respuesta del modelo está vacía")
                return "Sin respuesta"
                
            return full_response
            
        except Exception as e:
            error_msg = f"Error en streaming: {e}"
            print(f"\n❌ {error_msg}")
            return error_msg
    
    def chat(self):
        """
        Inicia una sesión de chat interactiva
        """
        print(f"🤖 Cliente Gemini - Modelo: {self.model_name}")
        print(f"🧠 Contexto: {self.context_size:,} tokens")
        print("🎬 Streaming: ACTIVADO por defecto")
        
        if self.voice_enabled:
            print("🎤🗣️ Modo VOZ: ACTIVADO")
        else:
            print("⚠️ Modo voz: NO disponible")
        
        print("Comandos disponibles:")
        print("  • 'salir' o 'exit' - Terminar sesión")
        print("  • 'stream' - Alternar modo streaming")
        print("  • 'historial' - Mostrar historial de conversación")
        print("  • 'limpiar' - Limpiar historial")
        print("  • 'info' - Mostrar información de contexto")
        
        if self.voice_enabled:
            print("  • 'escuchar' - Activar entrada por voz")
            print("  • 'voz' - Alternar respuestas por voz")
            print("  • 'voz-streaming' - TTS en paralelo (recomendado)")
        
        print("-" * 60)
        
        use_stream = True  # Streaming activado por defecto
        use_voice_output = False  # Respuestas por voz
        use_voice_streaming = False  # TTS en paralelo
        
        while True:
            try:
                user_input = input("\n👤 Tú: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("👋 ¡Hasta luego!")
                    break
                
                if user_input.lower() == 'stream':
                    use_stream = not use_stream
                    status = "🎬 ACTIVADO" if use_stream else "⏸️ DESACTIVADO"
                    print(f"✅ Modo streaming: {status}")
                    continue
                
                if user_input.lower() in ['historial', 'history']:
                    self._show_history()
                    continue
                
                if user_input.lower() in ['limpiar', 'clear']:
                    self.clear_history()
                    continue
                
                if user_input.lower() == 'info':
                    self.show_context_info()
                    continue
                
                # Comandos de voz
                if self.voice_enabled and user_input.lower() in ['escuchar', 'listen']:
                    print("🎤 Modo escucha activado...")
                    voice_text = self.listen_to_voice()
                    if voice_text:
                        user_input = voice_text
                        print(f"👤 Tú (por voz): {user_input}")
                    else:
                        print("🔇 No se detectó entrada de voz")
                        continue
                
                if self.voice_enabled and user_input.lower() in ['voz', 'voice']:
                    use_voice_output = not use_voice_output
                    status = "🗣️ ACTIVADA" if use_voice_output else "🔇 DESACTIVADA"
                    print(f"✅ Respuesta por voz: {status}")
                    if use_voice_output:
                        print("💡 Usa 'voz-streaming' para TTS en paralelo (más fluido)")
                    continue
                
                if self.voice_enabled and user_input.lower() in ['voz-streaming', 'voice-streaming']:
                    use_voice_streaming = not use_voice_streaming
                    if use_voice_streaming:
                        use_voice_output = True  # Activar voz automáticamente
                        status = "🎬🗣️ ACTIVADO (TTS en paralelo)"
                    else:
                        status = "⏸️ DESACTIVADO"
                    print(f"✅ TTS Streaming: {status}")
                    continue
                
                if not user_input:
                    continue
                
                print(f"\n🤖 {self.model_name}:", end=" ")
                if use_stream:
                    # Si el streaming de voz está activado, no reproducir después
                    voice_after_stream = use_voice_output and not use_voice_streaming
                    response = self.generate_response(
                        user_input, 
                        stream=True, 
                        voice_streaming=use_voice_streaming
                    )
                    
                    # Solo reproducir voz después si no fue streaming
                    if voice_after_stream and response:
                        print("🗣️ Reproduciendo respuesta completa...")
                        self.speak_response(response)
                        
                else:
                    response = self.generate_response(user_input, stream=False)
                    print(response)
                    
                    # Síntesis de voz si está activada (modo no-stream)
                    if use_voice_output and response and self.voice_enabled:
                        print("🗣️ Reproduciendo respuesta...")
                        self.speak_response(response)
                
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _show_history(self):
        """
        Muestra el historial de conversación
        """
        if not self.conversation_history:
            print("📝 No hay historial de conversación")
            return
        
        print("📝 Historial de conversación:")
        print("-" * 40)
        for i, msg in enumerate(self.conversation_history, 1):
            role_icon = "👤" if isinstance(msg, HumanMessage) else "🤖"
            role_name = "Tú" if isinstance(msg, HumanMessage) else self.model_name
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            print(f"{i}. {role_icon} {role_name}: {content}")

    async def setup_mcp_servers(self, mcp_configs: Dict[str, Dict] = None):
        """
        Configura servidores MCP
        
        Args:
            mcp_configs: Configuración de servidores MCP
                Ejemplo:
                {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/ruta/permitida"],
                        "transport": "stdio"
                    }
                }
        """
        if not MultiServerMCPClient:
            print("❌ langchain-mcp-adapters no está instalado")
            return False
            
        if mcp_configs is None:
            # Configuración por defecto para filesystem MCP
            home_dir = os.path.expanduser("~")
            mcp_configs = {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        home_dir,  # Permite acceso al directorio home
                        f"{home_dir}/Documents",  # y a Documents
                        f"{home_dir}/Desktop"     # y a Desktop
                    ],
                    "transport": "stdio"
                }
            }
        
        try:
            # Crear cliente MCP
            self.mcp_client = MultiServerMCPClient(mcp_configs)
            
            # Obtener herramientas disponibles
            self.mcp_tools = await self.mcp_client.get_tools()
            
            print(f"✅ MCPs configurados correctamente. {len(self.mcp_tools)} herramientas disponibles:")
            for tool in self.mcp_tools:
                print(f"  - {tool.name}: {tool.description}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error configurando MCPs: {e}")
            print("ℹ️  Asegúrate de tener Node.js y npm instalados para usar el filesystem MCP")
            self.mcp_client = None
            self.mcp_tools = []
            return False
    
    def add_mcp_server(self, name: str, config: Dict[str, Any]):
        """
        Agregar un servidor MCP adicional dinámicamente
        """
        # Esta función requeriría reinicializar el cliente MCP
        # Por simplicidad, recomendamos configurar todos los servidores al inicio
        print(f"ℹ️  Para agregar '{name}', reinicia el cliente con la nueva configuración")

    async def chat_with_voice(self, user_input: str) -> str:
        """
        Realiza una conversación con entrada de texto y salida de voz con streaming.
        Ahora incluye soporte para herramientas MCP.
        
        Args:
            user_input: El mensaje del usuario
            
        Returns:
            La respuesta del asistente
        """
        try:
            # Agregar mensaje del usuario al historial
            self.conversation_history.append(HumanMessage(content=user_input))
            
            # Crear modelo con herramientas MCP si están disponibles
            if self.mcp_tools:
                model_with_tools = self.model.bind_tools(self.mcp_tools)
                print(f"🔧 Usando {len(self.mcp_tools)} herramientas MCP disponibles")
            else:
                model_with_tools = self.model
            
            # Intentar streaming primero
            try:
                full_response = ""
                
                if self.voice_enabled and StreamingTTS:
                    # Streaming con TTS
                    streaming_tts = StreamingTTS()
                    if get_synthesizer:
                        streaming_tts.start(get_synthesizer())
                    
                    for chunk in model_with_tools.stream(self.conversation_history):
                        if hasattr(chunk, 'content') and chunk.content:
                            content = chunk.content
                            full_response += content
                            print(content, end='', flush=True)
                            
                            # Agregar contenido al buffer de TTS
                            if streaming_tts:
                                streaming_tts.add_text(content)
                        
                        # Manejar llamadas a herramientas MCP
                        elif hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                            for tool_call in chunk.tool_calls:
                                print(f"\n🔧 Ejecutando herramienta: {tool_call['name']}")
                                print(f"📋 Argumentos: {tool_call['args']}")
                                
                                # Ejecutar herramienta MCP
                                try:
                                    tool_result = await self._execute_mcp_tool(tool_call)
                                    tool_response = f"\n✅ Resultado de {tool_call['name']}: {tool_result}\n"
                                    full_response += tool_response
                                    print(tool_response)
                                    
                                    # Agregar resultado al TTS
                                    if streaming_tts:
                                        streaming_tts.add_text(tool_response)
                                        
                                except Exception as e:
                                    error_msg = f"\n❌ Error ejecutando {tool_call['name']}: {e}\n"
                                    full_response += error_msg
                                    print(error_msg)
                    
                    # Finalizar TTS
                    if streaming_tts:
                        streaming_tts.finish()
                
                else:
                    # Solo texto, sin voz
                    for chunk in model_with_tools.stream(self.conversation_history):
                        if hasattr(chunk, 'content') and chunk.content:
                            content = chunk.content
                            full_response += content
                            print(content, end='', flush=True)
                        elif hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                            for tool_call in chunk.tool_calls:
                                try:
                                    tool_result = await self._execute_mcp_tool(tool_call)
                                    tool_response = f"\n✅ {tool_call['name']}: {tool_result}\n"
                                    full_response += tool_response
                                    print(tool_response)
                                except Exception as e:
                                    error_msg = f"\n❌ Error en {tool_call['name']}: {e}\n"
                                    full_response += error_msg
                                    print(error_msg)
                
                print()  # Nueva línea al final
                
            except Exception as streaming_error:
                print(f"⚠️  Streaming falló: {streaming_error}")
                print("🔄 Intentando con invoke...")
                
                # Fallback a invoke
                response = model_with_tools.invoke(self.conversation_history)
                full_response = response.content
                
                # Verificar si hay llamadas a herramientas
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    for tool_call in response.tool_calls:
                        try:
                            tool_result = await self._execute_mcp_tool(tool_call)
                            tool_response = f"\n✅ {tool_call['name']}: {tool_result}\n"
                            full_response += tool_response
                        except Exception as e:
                            error_msg = f"\n❌ Error en {tool_call['name']}: {e}\n"
                            full_response += error_msg
                
                print(full_response)
                
                # Reproducir audio si está habilitado
                if self.voice_enabled:
                    self.speak_text(full_response)
            
            # Agregar respuesta al historial
            self.conversation_history.append(AIMessage(content=full_response))
            
            return full_response
            
        except Exception as e:
            error_msg = f"❌ Error en chat: {e}"
            print(error_msg)
            return error_msg
    
    async def _execute_mcp_tool(self, tool_call: Dict[str, Any]) -> str:
        """
        Ejecuta una herramienta MCP silenciando mensajes de schema
        
        Args:
            tool_call: Información de la llamada a la herramienta
            
        Returns:
            Resultado de la herramienta
        """
        if not self.mcp_client:
            raise Exception("Cliente MCP no inicializado")
        
        tool_name = tool_call['name']
        tool_args = tool_call.get('args', {})
        
        # Buscar la herramienta en nuestras herramientas MCP
        target_tool = None
        for tool in self.mcp_tools:
            if tool.name == tool_name:
                target_tool = tool
                break
        
        if not target_tool:
            raise Exception(f"Herramienta '{tool_name}' no encontrada")
        
        # Ejecutar la herramienta silenciando mensajes de schema
        try:
            # Capturar stderr para silenciar mensajes de "Key" y "$schema"
            captured_stderr = StringIO()
            with redirect_stderr(captured_stderr):
                result = await target_tool.ainvoke(tool_args)
        except Exception as e:
            # Fallback a invoke si ainvoke no funciona
            try:
                captured_stderr = StringIO()
                with redirect_stderr(captured_stderr):
                    result = target_tool.invoke(tool_args)
            except Exception as e2:
                raise Exception(f"Error ejecutando herramienta: {e2}")
        
        return str(result)

    def speak_text(self, text: str):
        """
        Reproduce texto usando síntesis de voz
        
        Args:
            text: Texto a reproducir
        """
        if self.voice_enabled and get_synthesizer:
            get_synthesizer().speak(text)
        else:
            print("🔇 Voz no disponible")

# Alias para mantener compatibilidad con el código existente
OllamaClient = GeminiClient

 
