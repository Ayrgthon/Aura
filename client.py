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
        StreamingTTS, VoiceSynthesizer, get_synthesizer, speak_async
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
    Callback handler para manejar streaming de respuestas con TTS
    """
    def __init__(self, voice_streaming=False, voice_enabled=False):
        super().__init__()
        self.voice_streaming = voice_streaming
        self.voice_enabled = voice_enabled
        self.streaming_tts = None
        self.full_response = ""
        # Nueva lógica para streaming parcial
        self.first_paragraph_done = False
        self.remaining_buffer = ""
        self.accumulated_first_para = ""
        self.char_counter = 0
        
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
        
        # Streaming hasta el primer punto '.', luego el resto se reproduce completo
        if self.voice_streaming:
            if not self.first_paragraph_done:
                # Iniciar streaming TTS si aún no
                if self.streaming_tts is None and self.voice_enabled:
                    try:
                        self.streaming_tts = start_streaming_tts()
                    except Exception as e:
                        print(f"❌ Error iniciando TTS streaming: {e}")

                if self.streaming_tts:
                    try:
                        add_text_to_stream(token)
                    except Exception as e:
                        print(f"\n❌ Error en TTS chunk: {e}")

                # Detectar primer punto
                if '.' in token:
                    if self.streaming_tts:
                        finish_streaming_tts()
                        self.streaming_tts = None
                    self.first_paragraph_done = True
            else:
                # Guardar el resto
                self.remaining_buffer += token
    
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
        # Asegurar cierre del streaming si sigue abierto
        if self.streaming_tts:
            try:
                finish_streaming_tts()
            except Exception as e:
                print(f"\n❌ Error al finalizar TTS streaming: {e}")

        # Reproducir el resto del texto de una sola vez
        if self.first_paragraph_done and self.remaining_buffer.strip() and self.voice_enabled:
            try:
                # Usar speak_async para no bloquear la impresión del texto restante
                speak_async(self.remaining_buffer.strip())
            except Exception as e:
                print(f"❌ Error reproduciendo resto del texto: {e}")

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
        
        # Mensaje de sistema para guiar la salida a un formato fácil de leer en voz
        system_instructions = (
            "Eres AURA, un asistente de voz en español. "
            "Responde de forma clara, conversacional y sin utilizar markdown ni caracteres especiales como *, #, **, guiones bajos, etc. "
            "Si necesitas enumerar, utiliza guiones simples '-' al inicio de cada punto. "
            "Mantén las oraciones cortas para que se lean naturalmente en voz alta. "
            "Evita emojis y símbolos innecesarios."
        )

        self.conversation_history: List[BaseMessage] = [
            HumanMessage(content=system_instructions)
        ]
        
        # Reactivar TTS de forma controlada
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
                convert_system_message_to_human=True,
                temperature=0.01

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
            self.mcp_client = MultiServerMCPClient(mcp_configs)  # type: ignore
            
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
            original_error = str(e)
            try:
                captured_stderr = StringIO()
                with redirect_stderr(captured_stderr):
                    result = target_tool.invoke(tool_args)
            except Exception as e2:
                raise Exception(f"Error ejecutando herramienta: {e2} | Error original async: {original_error}")
        
        return str(result)

    async def chat_with_voice(self, user_input: str) -> str:
        """
        Realiza una conversación con entrada de texto y salida de voz con streaming.
        Soporta tanto Gemini como Ollama con herramientas MCP con síntesis natural.
        
        Args:
            user_input: El mensaje del usuario
            
        Returns:
            La respuesta del asistente
        """
        try:
            # Agregar mensaje del usuario al historial
            self.conversation_history.append(HumanMessage(content=user_input))
            
            # Usar un enfoque de dos fases si hay herramientas MCP
            if self.mcp_tools:
                return await self._multi_step_agent(user_input)
            else:
                return await self._chat_without_mcp(user_input)
            
        except Exception as e:
            error_msg = f"❌ Error en chat: {e}"
            print(error_msg)
            return error_msg
    
    async def _multi_step_agent(self, user_input: str) -> str:
        """Agente estilo ReAct con varios pasos, usando callbacks de voz."""
        from langchain.schema import HumanMessage, AIMessage
        # Incluir StreamingTTS solo si hay voz habilitada
        speak_cb = speak_async if self.voice_enabled else lambda x: None

        model_with_tools = self.model.bind_tools(self.mcp_tools)

        messages: List[BaseMessage] = list(self.conversation_history)
        messages.append(HumanMessage(content=user_input))

        step = 1
        while True:
            speak_cb(f"Paso {step}. Pensando…")
            response = model_with_tools.invoke(messages)

            if hasattr(response, 'tool_calls') and getattr(response, 'tool_calls'):
                for tool_call in getattr(response, 'tool_calls'):
                    tool_name = tool_call['name']
                    speak_cb(f"Ejecutando {tool_name}")
                    try:
                        result = await self._execute_mcp_tool(tool_call)
                        speak_cb(f"{tool_name} completado")
                    except Exception as e:
                        speak_cb(f"Error en {tool_name}")
                        result = f"Error: {e}"

                    # Registrar Observación
                    messages.append(AIMessage(content="", additional_kwargs={'tool_calls':[tool_call]}))
                    messages.append(HumanMessage(content=f"Observación: {result}"))
                step += 1
                continue  # Permitir nuevo ciclo
            else:
                final_answer = response.content
                if not isinstance(final_answer, str):
                    final_answer = str(final_answer)
                speak_cb("Respuesta lista")
                # Stream + voz para la respuesta completa
                await self._stream_response(final_answer)
                return final_answer
    
    async def _chat_without_mcp(self, user_input: str) -> str:
        """
        Chat normal sin herramientas MCP
        """
        print(f"🤖 Usando {self.model_type.upper()} sin herramientas MCP")
        
        try:
            response = self.model.invoke(self.conversation_history)
            return await self._stream_response(response.content)
            
        except Exception as e:
            print(f"❌ Error en chat simple: {e}")
            return f"Error: {e}"
    
    async def _stream_response(self, content: str) -> str:
        """
        Reproduce una respuesta con streaming y TTS por oraciones
        """
        print(content)

        # Reproducir todo el texto con el mecanismo robusto (speak_async maneja división)
        if self.voice_enabled:
            speak_async(content)
        
        print()  # Nueva línea
        self.conversation_history.append(AIMessage(content=content))
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
            "  • Usuario: 'lista la carpeta documentos' → Usa list_directory con args={'path': '/home/ary/Documentos'}.\n"
            "  • Usuario: 'abre documents' → Usa list_directory con args={'path': '/home/ary/Documents'}.\n"
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
        self.conversation_history.insert(insert_index, HumanMessage(content=extra_context))

# Alias para mantener compatibilidad con el código existente
GeminiClient = AuraClient
OllamaClient = AuraClient

 
