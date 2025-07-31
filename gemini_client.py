#!/usr/bin/env python3
"""
Cliente nativo para Google Gemini API sin Langchain
Soporta streaming, function calling y conversaciones
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Iterator, Callable, Union
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold


class Message:
    """Clase simple para representar mensajes"""
    def __init__(self, role: str, content: str):
        self.role = role  # 'user', 'model', 'system'
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class GeminiClient:
    """Cliente nativo para Google Gemini API"""
    
    def __init__(self, 
                 model_name: str = "gemini-2.0-flash-exp",
                 api_key: Optional[str] = None,
                 temperature: float = 0.01,
                 max_output_tokens: Optional[int] = None):
        """
        Inicializa el cliente de Gemini
        
        Args:
            model_name: Nombre del modelo de Gemini
            api_key: API key de Google (si no se proporciona, se lee de env)
            temperature: Temperatura para la generación
            max_output_tokens: Máximo de tokens de salida
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        
        # Configurar API key
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada en las variables de entorno")
        
        genai.configure(api_key=api_key)
        
        # Configuración de seguridad (permisiva para uso interno)
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Inicializar modelo
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings
        )
        
        print(f"✅ Cliente Gemini inicializado: {self.model_name}")
    
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
    
    async def astream(self, messages: List[Message], 
                      tools: Optional[List[Any]] = None,
                      callback: Optional[Callable[[str], None]] = None) -> Iterator[str]:
        """
        Versión asíncrona del streaming
        
        Args:
            messages: Lista de mensajes de la conversación
            tools: Lista de herramientas/funciones disponibles
            callback: Función de callback para cada chunk
            
        Yields:
            Chunks de texto de la respuesta
        """
        # Por ahora, usar la versión síncrona en un executor
        loop = asyncio.get_event_loop()
        
        def sync_stream():
            chunks = []
            for chunk in self.stream(messages, tools, callback):
                chunks.append(chunk)
            return chunks
        
        chunks = await loop.run_in_executor(None, sync_stream)
        for chunk in chunks:
            yield chunk
    
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
        try:
            from engine.voice.speak import (
                start_streaming_tts, add_text_to_stream, 
                finish_streaming_tts, speak_async
            )
            self.start_streaming_tts = start_streaming_tts
            self.add_text_to_stream = add_text_to_stream
            self.finish_streaming_tts = finish_streaming_tts
            self.speak_async = speak_async
            self.tts_available = True
        except ImportError:
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
                        self.streaming_tts = self.start_streaming_tts()
                    except Exception as e:
                        print(f"\n❌ Error iniciando TTS streaming: {e}")
                
                # Agregar token al stream
                if self.streaming_tts:
                    try:
                        self.add_text_to_stream(token)
                    except Exception as e:
                        print(f"\n❌ Error en TTS chunk: {e}")
                
                # Detectar final de primera oración
                if '.' in token or '!' in token or '?' in token:
                    if self.streaming_tts:
                        try:
                            self.finish_streaming_tts()
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
                self.finish_streaming_tts()
            except Exception:
                pass
        
        # Reproducir el resto del texto
        if (self.first_sentence_done and 
            self.remaining_buffer.strip() and 
            self.voice_enabled and 
            self.tts_available):
            try:
                self.speak_async(self.remaining_buffer.strip())
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
                self.finish_streaming_tts()
            except Exception:
                pass