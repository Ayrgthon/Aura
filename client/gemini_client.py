#!/usr/bin/env python3
"""
Gemini Client Simple
Cliente Gemini optimizado para múltiples function calls en una sola petición
"""

import os
import asyncio
import warnings
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Silenciar warnings
warnings.filterwarnings("ignore")

# Importar Gemini
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    print("❌ google-generativeai no disponible")
    GEMINI_AVAILABLE = False

from mcp_client import SimpleMCPClient


class ChatMessage:
    """Mensaje simple para el historial"""
    def __init__(self, role: str, content: str):
        self.role = role  # 'user' o 'model' (para Gemini)
        self.content = content
    
    def to_gemini_format(self) -> Dict[str, Any]:
        """Convierte el mensaje al formato de Gemini"""
        return {
            "role": self.role,
            "parts": [self.content]
        }


class SimpleGeminiClient:
    """Cliente Gemini simple con soporte para múltiples function calls"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro", debug: bool = False):
        if not GEMINI_AVAILABLE:
            raise Exception("Gemini no disponible")
        
        self.model_name = model_name
        self.debug = debug
        
        # Configurar Gemini
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise Exception("GOOGLE_API_KEY no encontrada")
        
        genai.configure(api_key=google_api_key)
        
        # Configuración de seguridad permisiva
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
        
        # Historial de chat con system prompt
        self.chat_history: List[ChatMessage] = [
            ChatMessage(
                role="user", 
                content="Eres Aura, un asistente de IA. Para tareas complejas o que requieran múltiples pasos, usa la herramienta sequential_thinking para planificar primero, luego ejecuta TODAS las herramientas necesarias para completar la tarea completamente. Responde de forma directa y útil."
            )
        ]
        
        # Cliente MCP
        self.mcp_client = SimpleMCPClient(debug=debug)
        self.tools_available = False
        
        if self.debug:
            print(f"✅ Cliente Gemini inicializado: {self.model_name}")
    
    async def setup_mcp_servers(self, server_configs: Dict[str, Dict]) -> bool:
        """
        Configura servidores MCP
        
        Args:
            server_configs: Configuraciones de servidores MCP
            
        Returns:
            True si se configuró exitosamente
        """
        success = await self.mcp_client.connect_to_servers(server_configs)
        if success:
            self.tools_available = True
            if self.debug:
                print(f"🛠️  Herramientas disponibles: {self.mcp_client.get_tool_names()}")
        return success
    
    async def chat(self, user_message: str) -> str:
        """
        Envía un mensaje y obtiene respuesta, manejando múltiples function calls automáticamente
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Respuesta final del asistente
        """
        # Agregar mensaje del usuario al historial
        self.chat_history.append(ChatMessage(role="user", content=user_message))
        
        try:
            # Preparar herramientas si están disponibles
            tools = None
            if self.tools_available:
                tools = self.mcp_client.get_tools_for_gemini()
            
            # Convertir historial a formato Gemini
            gemini_history = [msg.to_gemini_format() for msg in self.chat_history]
            
            # Configurar chat con historial
            if len(gemini_history) > 1:
                # Usar historial previo
                chat_session = self.model.start_chat(
                    history=gemini_history[:-1]  # Todos excepto el último mensaje
                )
                
                # Enviar último mensaje
                if tools:
                    response = chat_session.send_message(
                        gemini_history[-1]['parts'][0],
                        tools=tools
                    )
                else:
                    response = chat_session.send_message(
                        gemini_history[-1]['parts'][0]
                    )
            else:
                # Primera interacción
                if tools:
                    response = self.model.generate_content(
                        user_message,
                        tools=tools
                    )
                else:
                    response = self.model.generate_content(user_message)
            
            # Procesar respuesta
            final_response = await self._process_response(response)
            
            # Agregar respuesta al historial
            self.chat_history.append(ChatMessage(role="model", content=final_response))
            
            return final_response
            
        except Exception as e:
            error_msg = f"Error en chat: {e}"
            if self.debug:
                print(f"❌ Error detallado: {type(e).__name__}: {e}")
                # Mostrar más detalles si está disponible
                if hasattr(e, 'response'):
                    print(f"📋 Respuesta del error: {e.response}")
            self.chat_history.append(ChatMessage(role="model", content=error_msg))
            return error_msg
    
    async def _process_response(self, response) -> str:
        """
        Procesa la respuesta de Gemini, ejecutando function calls si es necesario
        
        Args:
            response: Respuesta de Gemini
            
        Returns:
            Respuesta final procesada
        """
        if not response.candidates:
            return "No se pudo generar respuesta"
        
        candidate = response.candidates[0]
        
        # Verificar si hay function calls
        function_calls = []
        text_parts = []
        
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
                elif hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
        
        # Si no hay function calls, retornar texto directamente
        if not function_calls:
            return "".join(text_parts) if text_parts else "No se pudo generar respuesta"
        
        # Ejecutar function calls
        function_results = []
        for func_call in function_calls:
            try:
                if self.debug:
                    print(f"🔧 Ejecutando: {func_call.name}")
                    print(f"📋 Argumentos: {dict(func_call.args) if func_call.args else {}}")
                
                # Ejecutar herramienta MCP
                result = await self.mcp_client.execute_tool(
                    func_call.name,
                    dict(func_call.args) if func_call.args else {}
                )
                
                function_results.append({
                    "name": func_call.name,
                    "result": result
                })
                
                if self.debug:
                    print(f"✅ {func_call.name} completado")
                    print(f"📊 Resultado (primeros 200 chars): {result[:200]}...")
                
            except Exception as e:
                error_result = f"Error en {func_call.name}: {e}"
                function_results.append({
                    "name": func_call.name,
                    "result": error_result
                })
                
                if self.debug:
                    print(f"❌ Error en {func_call.name}: {e}")
        
        # Generar respuesta final basada en los resultados
        return await self._generate_final_response(function_results, "".join(text_parts))
    
    async def _generate_final_response(self, function_results: List[Dict], initial_text: str = "") -> str:
        """
        Genera respuesta final basada en los resultados de las function calls
        
        Args:
            function_results: Lista de resultados de function calls
            initial_text: Texto inicial de la respuesta (si lo hay)
            
        Returns:
            Respuesta final
        """
        if not function_results:
            return initial_text or "No se ejecutaron herramientas"
        
        # Crear prompt para generar respuesta final
        results_summary = "\n".join([
            f"Herramienta {result['name']}: {result['result']}"
            for result in function_results
        ])
        
        final_prompt = f"""
Basándote en los siguientes resultados de herramientas, genera una respuesta completa y útil:

{results_summary}

{f"Contexto inicial: {initial_text}" if initial_text else ""}

Proporciona una respuesta clara y organizada que sintetice toda la información obtenida.
"""
        
        try:
            # Generar respuesta final sin herramientas
            final_response = self.model.generate_content(final_prompt)
            
            if final_response.candidates:
                candidate = final_response.candidates[0]
                if candidate.content and candidate.content.parts:
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    return "".join(text_parts)
            
            # Fallback: retornar resultados directamente
            return results_summary
            
        except Exception as e:
            if self.debug:
                print(f"❌ Error generando respuesta final: {e}")
            # Fallback: retornar resultados directamente
            return results_summary
    
    def clear_history(self):
        """Limpia el historial de chat"""
        self.chat_history.clear()
        if self.debug:
            print("🧹 Historial limpiado")
    
    async def cleanup(self):
        """Limpia recursos"""
        await self.mcp_client.cleanup()
        if self.debug:
            print("🧹 Cliente limpiado")
    
    def get_available_tools(self) -> List[str]:
        """Retorna lista de herramientas disponibles"""
        if self.tools_available:
            return self.mcp_client.get_tool_names()
        return []