#!/usr/bin/env python3
"""
Aura - Cliente Simplificado
Solo LLM + MCP + Memory Chat + System Prompt Simple
"""

import os
import asyncio
import warnings
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Cargar variables de entorno
load_dotenv()

# Silenciar warnings
warnings.filterwarnings("ignore")

# Importar MCP
try:
    from mcp_client_native import NativeMCPClient
    MCP_AVAILABLE = True
except ImportError:
    print("⚠️ MCP no disponible")
    MCP_AVAILABLE = False

# Configurar Gemini
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    GEMINI_AVAILABLE = True
else:
    print("❌ GOOGLE_API_KEY no encontrada")
    GEMINI_AVAILABLE = False


class ChatMessage:
    """Mensaje simple para el historial"""
    def __init__(self, role: str, content: str):
        self.role = role  # 'user' o 'assistant'
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class SimpleAuraClient:
    """Cliente Aura simplificado"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro"):
        if not GEMINI_AVAILABLE:
            raise Exception("Gemini no disponible")
        
        self.model_name = model_name
        
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
        
        # Sistema de memoria (historial de chat)
        self.chat_history: List[ChatMessage] = [
            ChatMessage(role="user", content="Eres un asistente de IA llamado Aura")
        ]
        
        # Cliente MCP
        self.mcp_client = None
        self.mcp_tools = []
        
        print(f"✅ Cliente Aura simplificado inicializado: {self.model_name}")
    
    async def setup_mcp(self, mcp_configs: Dict[str, Dict] = None) -> bool:
        """Configurar servidores MCP"""
        if not MCP_AVAILABLE:
            return False
        
        try:
            self.mcp_client = NativeMCPClient()
            success = await self.mcp_client.setup_servers(mcp_configs or {})
            
            if success:
                self.mcp_tools = self.mcp_client.tools
                print(f"✅ MCP configurado: {len(self.mcp_tools)} herramientas")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error configurando MCP: {e}")
            return False
    
    def _convert_to_gemini_format(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Convierte mensajes al formato de Gemini"""
        gemini_messages = []
        
        for msg in messages:
            if msg.role == 'user':
                gemini_messages.append({
                    'role': 'user',
                    'parts': [msg.content]
                })
            elif msg.role == 'assistant':
                gemini_messages.append({
                    'role': 'model',
                    'parts': [msg.content]
                })
        
        return gemini_messages
    
    async def chat(self, user_message: str) -> str:
        """Método principal de chat"""
        # Agregar mensaje del usuario al historial
        self.chat_history.append(ChatMessage(role="user", content=user_message))
        
        try:
            # Si hay herramientas MCP disponibles, usar el flujo con herramientas
            if self.mcp_tools:
                response = await self._chat_with_tools(user_message)
            else:
                response = await self._chat_simple(user_message)
            
            # Agregar respuesta al historial
            self.chat_history.append(ChatMessage(role="assistant", content=response))
            
            return response
            
        except Exception as e:
            error_msg = f"Error: {e}"
            self.chat_history.append(ChatMessage(role="assistant", content=error_msg))
            return error_msg
    
    async def _chat_simple(self, user_message: str) -> str:
        """Chat sin herramientas MCP"""
        try:
            # Convertir historial a formato Gemini
            gemini_messages = self._convert_to_gemini_format(self.chat_history)
            
            # Usar chat de Gemini
            if len(gemini_messages) > 1:
                chat = self.model.start_chat(history=gemini_messages[:-1])
                response = chat.send_message(gemini_messages[-1]['parts'][0])
            else:
                response = self.model.generate_content(gemini_messages[-1]['parts'][0])
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Error en chat simple: {e}")
    
    async def _chat_with_tools(self, user_message: str) -> str:
        """Chat con herramientas MCP"""
        try:
            # Convertir herramientas MCP al formato Gemini
            gemini_tools = self.mcp_client.get_tools_for_gemini() if self.mcp_client else []
            
            # Convertir historial
            gemini_messages = self._convert_to_gemini_format(self.chat_history)
            
            # Generar respuesta con herramientas
            if len(gemini_messages) > 1:
                chat = self.model.start_chat(history=gemini_messages[:-1])
                response = chat.send_message(
                    gemini_messages[-1]['parts'][0],
                    tools=gemini_tools
                )
            else:
                response = self.model.generate_content(
                    gemini_messages[-1]['parts'][0],
                    tools=gemini_tools
                )
            
            # Procesar respuesta
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                text_response = ""
                tool_calls = []
                
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Texto
                        if hasattr(part, 'text') and part.text:
                            text_response += part.text
                        
                        # Llamadas a herramientas
                        elif hasattr(part, 'function_call') and part.function_call:
                            if hasattr(part.function_call, 'name') and part.function_call.name:
                                tool_call = {
                                    'name': part.function_call.name,
                                    'args': dict(part.function_call.args) if hasattr(part.function_call, 'args') else {}
                                }
                                tool_calls.append(tool_call)
                
                # Si hay llamadas a herramientas, ejecutarlas
                if tool_calls:
                    return await self._execute_tools_and_respond(tool_calls, user_message)
                else:
                    return text_response
            
            return "No se pudo generar respuesta"
            
        except Exception as e:
            raise Exception(f"Error en chat con herramientas: {e}")
    
    async def _execute_tools_and_respond(self, tool_calls: List[Dict], user_message: str) -> str:
        """Ejecuta herramientas y genera respuesta final"""
        tool_results = []
        
        # Ejecutar cada herramienta
        for tool_call in tool_calls:
            try:
                print(f"🔧 Ejecutando: {tool_call['name']}")
                result = await self.mcp_client.execute_tool(tool_call['name'], tool_call['args'])
                
                tool_result = {
                    'tool_name': tool_call['name'],
                    'query': tool_call['args'],
                    'result': result
                }
                tool_results.append(tool_result)
                
                # Agregar resultado al historial para que Aura lo recuerde
                self.chat_history.append(ChatMessage(
                    role="assistant", 
                    content=f"Herramienta {tool_call['name']} ejecutada: {result[:500]}..."
                ))
                
                print(f"✅ {tool_call['name']} completado")
                
            except Exception as e:
                print(f"❌ Error en {tool_call['name']}: {e}")
                error_result = {
                    'tool_name': tool_call['name'],
                    'query': tool_call['args'],
                    'result': f"Error: {e}"
                }
                tool_results.append(error_result)
        
        # Generar respuesta final basada en los resultados
        if tool_results:
            return await self._synthesize_response(user_message, tool_results)
        else:
            return "No se pudieron ejecutar las herramientas solicitadas"
    
    async def _synthesize_response(self, user_message: str, tool_results: List[Dict]) -> str:
        """Sintetiza respuesta natural basada en resultados de herramientas"""
        context_parts = [
            f"Usuario preguntó: {user_message}",
            "\nInformación obtenida:"
        ]
        
        for result in tool_results:
            context_parts.append(
                f"\n• {result['tool_name']}: {result['result'][:1000]}..."
            )
        
        context_parts.append(
            "\nResponde de forma natural y conversacional basándote en esta información. "
            "NO menciones herramientas o procesos técnicos."
        )
        
        synthesis_prompt = "".join(context_parts)
        
        try:
            response = self.model.generate_content(synthesis_prompt)
            return response.text
        except Exception as e:
            print(f"❌ Error en síntesis: {e}")
            return f"Información encontrada: {tool_results[0]['result'][:500]}..." if tool_results else "Error procesando información"
    
    def clear_history(self):
        """Limpiar historial de chat manteniendo el system prompt"""
        self.chat_history = [
            ChatMessage(role="user", content="Eres un asistente de IA llamado Aura")
        ]
        print("🗑️ Historial limpiado")
    
    async def cleanup(self):
        """Limpiar recursos"""
        if self.mcp_client:
            try:
                await self.mcp_client.cleanup()
                print("🧹 Recursos MCP limpiados")
            except Exception as e:
                print(f"⚠️ Error limpiando MCP: {e}")