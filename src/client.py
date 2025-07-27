#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
import tempfile
import warnings
import logging
import json
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout
from gtts import gTTS
import pygame
from typing import List, Dict, Any, Iterator, Optional, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

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
    from voice.hear import initialize_recognizer, listen_for_command
    from voice.speak import (
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

# Importaciones para LangGraph
try:
    from .langgraph_agent import create_langgraph_agent, LangGraphAgent
    LANGGRAPH_AGENT_AVAILABLE = True
except ImportError as e:
    try:
        from langgraph_agent import create_langgraph_agent, LangGraphAgent
        LANGGRAPH_AGENT_AVAILABLE = True
    except ImportError as e2:
        print(f"⚠️  Error cargando LangGraph Agent: {e2}")
        LANGGRAPH_AGENT_AVAILABLE = False

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
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key
    else:
        print("⚠️  GOOGLE_API_KEY no encontrada en .env")

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
            "Evita emojis y símbolos innecesarios. "
            "SIEMPRE RESPONDE al usuario, nunca te quedes en silencio. "
            
            "PROTOCOLO ESPECIAL PARA BASE DE DATOS 'QUEST': "
            "La base de datos 'quest' es tu herramienta principal para gestionar tareas y proyectos. "
            "Propiedades disponibles: Name (título), Due date (fecha), Description (descripción), skill (habilidad), arcos (arco narrativo), importancia, Status, completed!. "
            "PROTOCOLO ESTRICTO PARA CREAR PÁGINAS EN NOTION: "
            "Cuando te pidan crear una página, sigue EXACTAMENTE estos 4 pasos en orden: "
            "PASO 1: Buscar la base de datos usando API-post-search con query='nombre_base_datos' y filter={'property': 'object', 'value': 'database'} "
            "PASO 2: Obtener el database_id del resultado y usar API-post-database-query con database_id para revisar propiedades "
            "PASO 3: Crear la página usando API-post-page con parent={'database_id': 'ID'} y properties correctas "
            "PASO 4: Confirmar creación exitosa "
            "ESTRUCTURA DE PROPERTIES: Name={'title': [{'text': {'content': 'título'}}]}, Due date={'date': {'start': 'YYYY-MM-DD'}}, Description={'rich_text': [{'text': {'content': 'texto'}}]} "
            "IMPORTANTE: SIEMPRE usar database_id en parent, NUNCA page_id. "
            "NUNCA hagas pasos extra. NUNCA busques otras bases de datos. NUNCA uses comillas extra en nombres. "
            "SOLO los 4 pasos en orden. NADA más. "
            "Comandos: 'crea una página llamada [título]', 'crea en [base_datos] una página llamada [título]'. "
            "Confirma la creación exitosa al final."
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
        
        # Agente LangGraph
        self.langgraph_agent = None
        self.use_langgraph = True  # Por defecto usar LangGraph si está disponible
        
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
            
            # Inicializar agente LangGraph si está disponible
            if self.use_langgraph and LANGGRAPH_AGENT_AVAILABLE:
                self.langgraph_agent = create_langgraph_agent(
                    self.model, 
                    self.mcp_tools, 
                    max_steps=15
                )
                if self.langgraph_agent:
                    print("✅ Agente LangGraph inicializado para flujos complejos")
                else:
                    print("⚠️ No se pudo inicializar LangGraph, usando agente simple")
            
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
        
        # DEBUG: Imprimir información de la llamada a la API
        print(f"\n🔍 DEBUG API CALL:")
        print(f"   Herramienta: {tool_name}")
        print(f"   Argumentos: {json.dumps(tool_args, indent=2, ensure_ascii=False)}")
        
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
        
        # DEBUG: Imprimir resultado
        print(f"   Resultado: {str(result)[:200]}...")
        print(f"   {'='*50}")
        
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
            
            # Debug: Verificar qué agente se está usando
            print(f"🔍 DEBUG: langgraph_agent = {self.langgraph_agent is not None}")
            print(f"🔍 DEBUG: mcp_tools = {len(self.mcp_tools) if self.mcp_tools else 0}")
            
            # Usar LangGraph si está disponible, sino usar el agente simple
            if self.langgraph_agent:
                print("🔍 DEBUG: Usando LangGraph Agent")
                return await self._langgraph_agent(user_input)
            elif self.mcp_tools:
                print("🔍 DEBUG: Usando Multi-Step Agent (ReAct)")
                return await self._multi_step_agent(user_input)
            else:
                print("🔍 DEBUG: Usando Chat sin MCP")
                return await self._chat_without_mcp(user_input)
            
        except Exception as e:
            error_msg = f"❌ Error en chat: {e}"
            print(error_msg)
            return error_msg
    
    async def _langgraph_agent(self, user_input: str) -> str:
        """Agente LangGraph para manejo de flujos complejos."""
        if not self.langgraph_agent:
            return await self._multi_step_agent(user_input)
        
        try:
            # Usar el agente LangGraph
            final_answer = await self.langgraph_agent.run(
                user_input, 
                self.conversation_history
            )
            
            # Añadir al historial y reproducir
            await self._stream_response(final_answer)
            return final_answer
            
        except Exception as e:
            print(f"❌ Error en agente LangGraph: {e}")
            # Fallback al agente simple
            return await self._multi_step_agent(user_input)
    
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

                    # Registrar Observación en historial global Y local
                    observation_message = HumanMessage(content=f"Observación: {result}")
                    messages.append(AIMessage(content="", additional_kwargs={'tool_calls':[tool_call]}))
                    messages.append(observation_message)
                    # Añadir al historial global para persistencia
                    self.conversation_history.append(AIMessage(content="", additional_kwargs={'tool_calls':[tool_call]}))
                    self.conversation_history.append(observation_message)
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
        
    def debug_conversation_history(self):
        """Función de debug para verificar el contenido del historial"""
        print(f"\n🔍 DEBUG: Historial tiene {len(self.conversation_history)} mensajes")
        for i, msg in enumerate(self.conversation_history):
            content_preview = str(msg.content)[:100] + "..." if len(str(msg.content)) > 100 else str(msg.content)
            print(f"  {i}: {type(msg).__name__} - {content_preview}")
        
        # Verificar si el protocolo está presente
        protocol_found = any(
            "PROTOCOLO DIRECTO PARA NOTION QUEST Y ARCOS" in str(msg.content) 
            for msg in self.conversation_history
        )
        print(f"  📋 Protocolo Notion encontrado: {protocol_found}")
        
        # Verificar si hay observaciones de herramientas
        tool_observations = sum(
            1 for msg in self.conversation_history 
            if "Observación:" in str(msg.content)
        )
        print(f"  🔧 Observaciones de herramientas: {tool_observations}")
    
    def enable_langgraph(self, enable: bool = True):
        """Habilita o deshabilita el uso de LangGraph"""
        self.use_langgraph = enable
        if enable and not self.langgraph_agent and LANGGRAPH_AGENT_AVAILABLE:
            self.langgraph_agent = create_langgraph_agent(
                self.model, 
                self.mcp_tools, 
                max_steps=15
            )
            if self.langgraph_agent:
                print("✅ LangGraph habilitado")
            else:
                print("⚠️ No se pudo habilitar LangGraph")
        elif not enable:
            self.langgraph_agent = None
            print("🔇 LangGraph deshabilitado")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del agente"""
        return {
            "langgraph_available": LANGGRAPH_AGENT_AVAILABLE,
            "langgraph_enabled": self.use_langgraph,
            "langgraph_agent": self.langgraph_agent is not None,
            "mcp_tools": len(self.mcp_tools),
            "conversation_history_length": len(self.conversation_history)
        }
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

        # Instrucciones para herramientas de archivos
        filesystem_instructions = (
            "Instrucciones para el uso de herramientas de archivos:\n"
            "- Siempre que el usuario pida listar, abrir, leer o similar sobre una carpeta o archivo, deduce la ruta completa usando los alias.\n"
            "- Llama a la herramienta adecuada sin solicitar más pistas al usuario.\n"
            "Ejemplos:\n"
            "  • Usuario: 'lista la carpeta documents' → Usa list_directory con args={'path': '/home/ary/Documents'}.\n"
            "  • Usuario: 'abre downloads' → Usa list_directory con args={'path': '/home/ary/Downloads'}.\n"
            "  • Usuario: 'muestra pictures' → Usa list_directory con args={'path': '/home/ary/Pictures'}.\n"
        )

        # Protocolo específico para Notion Quest y Arcos (basado en tu forma de hablar)
        notion_quest_protocol = (
            "PROTOCOLO DIRECTO PARA NOTION QUEST Y ARCOS:\n"
            "Tienes acceso a dos bases de datos principales:\n"
            "• 'quest': Tareas pendientes (propiedades: Name, Due date, Description, skill, arcos, importancia, Status, completed!, personaje, Pistas)\n"
            "• 'arcos': Eventos/proyectos (propiedades: quest, clear!, personaje, skills, Pistas, Name)\n"
            "PROCESO ESTRICTO DE CREACIÓN:\n"
            "PASO 1: Buscar la base de datos usando API-post-search con query='nombre_base_datos' y filter={'property': 'object', 'value': 'database'}\n"
            "PASO 2: Obtener el database_id y usar API-post-database-query con database_id para revisar propiedades\n"
            "PASO 3: Crear la página usando API-post-page con parent={'database_id': 'ID'} y properties correctas\n"
            "PASO 4: Confirmar creación exitosa\n"
            "ESTRUCTURA DE PROPERTIES:\n"
            "• Name: {'title': [{'text': {'content': 'título'}}]}\n"
            "• Due date: {'date': {'start': 'YYYY-MM-DD'}}\n"
            "• Description: {'rich_text': [{'text': {'content': 'texto'}}]}\n"
            "• arcos: {'relation': [{'id': 'ID_del_arco'}]}\n"
            "• skill: {'select': {'name': 'nombre_skill'}}\n"
            "• importancia: {'select': {'name': 'nivel_importancia'}}\n"
            "IMPORTANTE: SIEMPRE usar database_id en parent, NUNCA page_id.\n"
            "NUNCA hagas pasos extra. NUNCA busques otras bases de datos. SOLO los 4 pasos en orden.\n"
            "Comandos naturales:\n"
            "  • 'revisa la base de datos quest/arcos' → Mostrar todas las páginas\n"
            "  • 'crea una página llamada [título]' → Crear en quest (por defecto)\n"
            "  • 'crea en arcos una página llamada [título]' → Crear en arcos\n"
            "  • 'crea en quest una página llamada [título]' → Crear en quest (explícito)\n"
            "  • 'cuales son las propiedades de la base de datos [nombre]' → Revisar propiedades\n"
            "Confirma la creación exitosa al final.\n"
        )

        extra_context = (
            "Contexto: Estos son los directorios disponibles (acceso garantizado): "
            f"{dirs_formatted}.\n"
            "Alias útiles (no distinguen mayúsculas/minúsculas):\n"
            f"{alias_block}.\n"
            f"{filesystem_instructions}\n"
            f"{notion_quest_protocol}\n"
            "Recuerda NO preguntar rutas completas; usa los alias para resolverlas automáticamente. "
            "Para Notion, siempre busca primero la base de datos 'quest' antes de crear contenido."
        )
        # Insertar justo después del mensaje de instrucciones original para mantener prioridad
        insert_index = 1 if len(self.conversation_history) >= 1 else 0
        self.conversation_history.insert(insert_index, HumanMessage(content=extra_context))
        
        # Asegurar que el notion_quest_protocol esté en el historial principal
        # Buscar si ya existe un mensaje con el protocolo
        protocol_exists = any(
            "PROTOCOLO DIRECTO PARA NOTION QUEST Y ARCOS" in str(msg.content) 
            for msg in self.conversation_history
        )
        
        if not protocol_exists:
            # Añadir el protocolo como mensaje separado para asegurar que esté en el historial
            self.conversation_history.append(HumanMessage(content=notion_quest_protocol))

# Alias para mantener compatibilidad con el código existente
GeminiClient = AuraClient
OllamaClient = AuraClient

 
