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
from typing import List, Dict, Any, Iterator, Optional, Literal
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

# Importar modelos LLM
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Google Gemini no disponible: {e}")
    GEMINI_AVAILABLE = False

try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Ollama no disponible: {e}")
    OLLAMA_AVAILABLE = False

# Configurar API Key de Google
if GEMINI_AVAILABLE:
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

class AuraClient:
    def __init__(self, 
                 model_type: Literal["gemini", "ollama"] = "gemini",
                 model_name: Optional[str] = None,
                 context_size: int = 100000, 
                 enable_voice: bool = True):
        """
        Inicializa el cliente Aura con soporte para Gemini y Ollama
        
        Args:
            model_type: Tipo de modelo ("gemini" o "ollama")
            model_name: Nombre específico del modelo (opcional)
            context_size: Tamaño del contexto
            enable_voice: Si habilitar capacidades de voz
        """
        self.model_type = model_type
        self.model_name = model_name
        self.context_size = context_size
        self.voice_enabled = enable_voice
        
        # Inicializar modelo según el tipo
        self.model = self._initialize_model()
        
        # Configuraciones
        self.conversation_history: List[BaseMessage] = []
        
        # Inicializar voz si está habilitado
        self.voice_synthesizer = None
        if self.voice_enabled:
            self._initialize_voice()
        
        # Lock para controlar orden del audio
        self.audio_lock = threading.Lock()
        
        # Cliente MCP
        self.mcp_client = None
        self.mcp_tools = []
        
        print(f"✅ Cliente Aura inicializado con {self.model_type.upper()}")
    
    def _initialize_model(self):
        """Inicializa el modelo LLM según la configuración"""
        if self.model_type == "gemini":
            if not GEMINI_AVAILABLE:
                raise Exception("Google Gemini no está disponible. Instala: pip install langchain-google-genai")
            
            model_name = self.model_name or "gemini-2.0-flash-exp"
            print(f"🤖 Inicializando Google Gemini: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                convert_system_message_to_human=True
            )
        
        elif self.model_type == "ollama":
            if not OLLAMA_AVAILABLE:
                raise Exception("Ollama no está disponible. Instala: pip install langchain-ollama")
            
            model_name = self.model_name or "qwen2.5-coder:7b"
            print(f"🦙 Inicializando Ollama: {model_name}")
            return ChatOllama(model=model_name)
        
        else:
            raise ValueError(f"Tipo de modelo no soportado: {self.model_type}")
    
    def _initialize_voice(self):
        """Inicializa las capacidades de voz"""
        if get_synthesizer:
            try:
                self.voice_synthesizer = get_synthesizer()
                if self.voice_synthesizer.initialized:
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

    async def setup_mcp_servers(self, mcp_configs: Dict[str, Dict] = None):
        """
        Configura servidores MCP
        
        Args:
            mcp_configs: Configuración de servidores MCP
        """
        if not MultiServerMCPClient:
            print("❌ langchain-mcp-adapters no está instalado")
            return False
            
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

    async def chat_with_voice(self, user_input: str) -> str:
        """
        Realiza una conversación con entrada de texto y salida de voz con streaming.
        Soporta tanto Gemini como Ollama con herramientas MCP.
        
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
                print(f"🔧 Usando {len(self.mcp_tools)} herramientas MCP con {self.model_type.upper()}")
            else:
                model_with_tools = self.model
                print(f"🤖 Usando {self.model_type.upper()} sin herramientas MCP")
            
            # Intentar streaming primero
            try:
                full_response = ""
                
                if self.voice_enabled and StreamingTTS:
                    # Streaming con TTS
                    streaming_tts = StreamingTTS()
                    if self.voice_synthesizer:
                        streaming_tts.start(self.voice_synthesizer)
                    
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

# Alias para mantener compatibilidad con el código existente
GeminiClient = AuraClient
OllamaClient = AuraClient

 
