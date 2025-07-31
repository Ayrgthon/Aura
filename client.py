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
from dotenv import load_dotenv
from gtts import gTTS
import pygame
from typing import List, Dict, Any, Iterator, Optional, Literal
from gemini_client import GeminiClient, Message, StreamingCallback

# Cargar variables de entorno desde .env
load_dotenv()

# Silenciar todos los warnings molestos
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

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

# Importaciones para MCP nativo
try:
    from mcp_client_native import NativeMCPClient, MCPToolCall
    MCP_NATIVE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Error cargando MCP nativo: {e}")
    NativeMCPClient = None
    MCPToolCall = None
    MCP_NATIVE_AVAILABLE = False

# Verificar disponibilidad de modelos
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Google Gemini no disponible: {e}")
    GEMINI_AVAILABLE = False

# Para mantener compatibilidad con Ollama (cliente básico)
try:
    import requests
    OLLAMA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Requests no disponible para Ollama: {e}")
    OLLAMA_AVAILABLE = False

# Configurar API Key de Google desde variables de entorno
if GEMINI_AVAILABLE:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("⚠️  GOOGLE_API_KEY no encontrada en las variables de entorno")
        GEMINI_AVAILABLE = False


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
        
        # Inicializar cliente de modelo según el tipo
        self.gemini_client = None
        self.ollama_client = None
        self._initialize_model()
        
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
        
        print(f"✅ Cliente Aura inicializado con {self.model_type.upper()}")
    
    def _initialize_model(self):
        """Inicializa el modelo LLM según la configuración"""
        if self.model_type == "gemini":
            if not GEMINI_AVAILABLE:
                raise Exception("Google Gemini no está disponible. Instala: pip install google-generativeai")
            
            model_name = self.model_name or "gemini-2.0-flash-exp"
            print(f"🤖 Inicializando Google Gemini: {model_name}")
            self.gemini_client = GeminiClient(
                model_name=model_name,
                temperature=0.01
            )
        
        elif self.model_type == "ollama":
            if not OLLAMA_AVAILABLE:
                raise Exception("Ollama no está disponible. Instala: pip install requests")
            
            model_name = self.model_name or "qwen2.5-coder:7b"
            print(f"🦙 Inicializando Ollama: {model_name}")
            # Para simplificar, crear un cliente básico de Ollama
            self.ollama_client = self._create_ollama_client(model_name)
        
        else:
            raise ValueError(f"Tipo de modelo no soportado: {self.model_type}")
    
    def _create_ollama_client(self, model_name: str):
        """Crea un cliente básico para Ollama"""
        class SimpleOllamaClient:
            def __init__(self, model_name: str):
                self.model_name = model_name
                self.base_url = "http://localhost:11434"
            
            def generate(self, messages: List[Message]) -> str:
                """Genera respuesta usando la API de Ollama"""
                try:
                    # Convertir mensajes al formato de Ollama
                    ollama_messages = []
                    for msg in messages:
                        if msg.role == "system":
                            ollama_messages.append({"role": "system", "content": msg.content})
                        elif msg.role == "user":
                            ollama_messages.append({"role": "user", "content": msg.content})
                        elif msg.role in ["assistant", "model"]:
                            ollama_messages.append({"role": "assistant", "content": msg.content})
                    
                    payload = {
                        "model": self.model_name,
                        "messages": ollama_messages,
                        "stream": False
                    }
                    
                    response = requests.post(f"{self.base_url}/api/chat", json=payload)
                    if response.status_code == 200:
                        return response.json().get('message', {}).get('content', '')
                    else:
                        raise Exception(f"Ollama API error: {response.status_code}")
                        
                except Exception as e:
                    raise Exception(f"Error conectando con Ollama: {e}")
        
        return SimpleOllamaClient(model_name)
    
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
            print("ℹ️  Asegúrate de tener Node.js y npm instalados para usar servidores MCP")
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
        Soporta tanto Gemini como Ollama con herramientas MCP con síntesis natural.
        
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
        print(f"🔧 Usando {len(self.mcp_tools)} herramientas MCP con {self.model_type.upper()}")
        
        all_tool_results = []
        max_iterations = 5  # Máximo de iteraciones para evitar loops infinitos
        iteration = 0
        
        try:
            # Para Gemini, usar el cliente nativo con herramientas
            if self.model_type == "gemini" and self.gemini_client:
                current_conversation = self.conversation_history.copy()
                
                while iteration < max_iterations:
                    iteration += 1
                    print(f"🔄 Iteración {iteration}")
                    
                    # Convertir herramientas MCP al formato de Gemini
                    gemini_tools = self.mcp_client.get_tools_for_gemini() if self.mcp_client else []
                    
                    # Obtener respuesta con herramientas
                    response = self.gemini_client.generate_with_tools(current_conversation, gemini_tools)
                    
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
            
            else:
                # Para Ollama, MCPs no están soportados actualmente sin Langchain
                print("⚠️  MCPs no soportados con Ollama en esta implementación")
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
            if self.model_type == "gemini" and self.gemini_client:
                for chunk in self.gemini_client.stream(synthesis_messages, callback=streaming_callback.on_token):
                    natural_response += chunk
                streaming_callback.on_complete()
            
            elif self.model_type == "ollama" and self.ollama_client:
                # Para Ollama, generar respuesta completa
                response_text = self.ollama_client.generate(synthesis_messages)
                natural_response = response_text
                print(response_text, end='', flush=True)
            
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
        print(f"🤖 Usando {self.model_type.upper()} sin herramientas MCP")
        
        try:
            if self.model_type == "gemini" and self.gemini_client:
                # Crear callback para streaming con TTS
                streaming_callback = StreamingCallback(
                    voice_enabled=self.voice_enabled
                )
                
                response_text = ""
                for chunk in self.gemini_client.stream(self.conversation_history, callback=streaming_callback.on_token):
                    response_text += chunk
                
                streaming_callback.on_complete()
                print()  # Nueva línea
                
                self.conversation_history.append(Message(role="assistant", content=response_text))
                return response_text
            
            elif self.model_type == "ollama" and self.ollama_client:
                response_text = self.ollama_client.generate(self.conversation_history)
                return await self._stream_response(response_text)
            
            else:
                raise Exception(f"Cliente {self.model_type} no disponible")
            
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
                print(f"⚠️  Error cerrando conexiones MCP: {e}")

# Alias para mantener compatibilidad con el código existente
# Nota: No sobrescribir GeminiClient ya que es importado de gemini_client.py
OllamaClient = AuraClient

 
