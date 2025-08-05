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
            ChatMessage(role="user", content="Eres Aura, asistente de IA especializado en análisis temporal y tareas. REGLAS CRÍTICAS: 1) SIEMPRE obtén y verifica la hora/fecha actual usando herramientas antes de hacer afirmaciones sobre tiempo. 2) Cuando evalúes si algo es 'futuro' o 'pasado', calcula correctamente basándote en la hora actual obtenida. 3) Para fechas, usa el formato correcto del día actual, no fechas anteriores. 4) Analiza cada solicitud completamente y ejecuta todas las herramientas necesarias para completar la tarea completa. 5) No termines tu respuesta hasta haber completado todos los aspectos de la solicitud.")
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
        """Chat con herramientas MCP - detecta si necesita múltiples rondas"""
        try:
            # Convertir herramientas MCP al formato Gemini
            gemini_tools = self.mcp_client.get_tools_for_gemini() if self.mcp_client else []
            
            # Primera llamada para detectar complejidad
            gemini_messages = self._convert_to_gemini_format(self.chat_history)
            
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
            
            # Procesar primera respuesta
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                text_response = ""
                tool_calls = []
                
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_response += part.text
                        elif hasattr(part, 'function_call') and part.function_call:
                            if hasattr(part.function_call, 'name') and part.function_call.name:
                                tool_call = {
                                    'name': part.function_call.name,
                                    'args': dict(part.function_call.args) if hasattr(part.function_call, 'args') else {}
                                }
                                tool_calls.append(tool_call)
                
                # Si no hay herramientas, respuesta simple
                if not tool_calls:
                    return text_response if text_response.strip() else "No se pudo generar respuesta"
                
                # SIEMPRE usar flujo multi-herramienta para evaluar si hay más tareas
                return await self._execute_multi_tool_sequence(tool_calls, user_message)
            
            return "No se pudo generar respuesta"
            
        except Exception as e:
            raise Exception(f"Error en chat con herramientas: {e}")
    
    async def _execute_multi_tool_sequence(self, initial_tool_calls: List[Dict], user_message: str) -> str:
        """Ejecuta secuencia de múltiples herramientas iterativamente"""
        try:
            gemini_tools = self.mcp_client.get_tools_for_gemini() if self.mcp_client else []
            max_iterations = 20  # Aumentado para tareas muy complejas
            iteration = 0
            executed_tools = []  # Registro de herramientas ejecutadas
            
            # Ejecutar herramientas iniciales
            await self._execute_tools_sequential_with_tracking(initial_tool_calls, executed_tools)
            
            while iteration < max_iterations:
                iteration += 1
                print(f"🔄 Evaluando si necesita más herramientas (ronda {iteration}/{max_iterations})")
                print(f"📊 Herramientas ejecutadas hasta ahora: {[tool['name'] for tool in executed_tools]}")
                
                # Prompt mejorado para finalización con contexto
                self.chat_history.append(ChatMessage(
                    role="user", 
                    content=f"¿Has completado todas las tareas solicitadas del usuario: '{user_message}'? Si SÍ y tienes suficiente información, proporciona la respuesta final completa. Si NO y necesitas más información, usa la siguiente herramienta necesaria. Recuerda verificar la hora actual si es relevante para la tarea."
                ))
                
                # Generar siguiente respuesta
                gemini_messages = self._convert_to_gemini_format(self.chat_history)
                
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
                            if hasattr(part, 'text') and part.text:
                                text_response += part.text
                            elif hasattr(part, 'function_call') and part.function_call:
                                if hasattr(part.function_call, 'name') and part.function_call.name:
                                    tool_call = {
                                        'name': part.function_call.name,
                                        'args': dict(part.function_call.args) if hasattr(part.function_call, 'args') else {}
                                    }
                                    tool_calls.append(tool_call)
                    
                    # Mejorar detección de respuesta final
                    if text_response.strip() and not tool_calls:
                        # Verificar si es realmente una respuesta final
                        if self._is_final_response(text_response, user_message, executed_tools):
                            print("📝 Respuesta final detectada (contenido completo)")
                            return text_response
                    
                    # Si hay herramientas, validar que no sean duplicadas
                    if tool_calls:
                        new_tools = self._filter_duplicate_tools(tool_calls, executed_tools)
                        if new_tools:
                            await self._execute_tools_sequential_with_tracking(new_tools, executed_tools)
                            continue
                        else:
                            print("⚠️ Todas las herramientas ya fueron ejecutadas, generando respuesta final")
                            break
                    
                    # Si hay texto final, devolver respuesta
                    if text_response.strip():
                        return text_response
                
                # Si no hay herramientas ni texto, salir
                break
            
            print(f"🏁 Límite de iteraciones alcanzado ({max_iterations}), generando síntesis final")
            print(f"📋 Herramientas ejecutadas en total: {len(executed_tools)}")
            # Generar síntesis final si el loop termina sin respuesta clara
            return await self._synthesize_response(user_message, executed_tools)
            
        except Exception as e:
            raise Exception(f"Error en secuencia multi-herramienta: {e}")
    
    def _is_final_response(self, text_response: str, user_message: str, executed_tools: List[Dict]) -> bool:
        """Determina si el texto es una respuesta final válida"""
        # Criterios para respuesta final:
        # 1. Texto suficientemente largo (>50 chars)
        # 2. Contiene información útil (no solo confirmación)
        # 3. Se ejecutó al menos una herramienta relevante
        
        if len(text_response.strip()) < 50:
            return False
        
        # Indicadores de respuesta final
        final_indicators = [
            "completado", "terminado", "listo", "resultado", "encontr", 
            "agendad", "guardad", "creado", "actualizado"
        ]
        
        has_final_indicator = any(indicator in text_response.lower() for indicator in final_indicators)
        has_tools_executed = len(executed_tools) > 0
        
        return has_final_indicator and has_tools_executed

    def _filter_duplicate_tools(self, tool_calls: List[Dict], executed_tools: List[Dict]) -> List[Dict]:
        """Filtra herramientas duplicadas basado en nombre y argumentos con lógica mejorada"""
        new_tools = []
        for tool_call in tool_calls:
            # Permitir re-ejecución para herramientas de consulta temporal
            temporal_tools = ["get_current_date", "get_current_time"]
            
            if tool_call['name'] in temporal_tools:
                # Siempre permitir herramientas temporales
                new_tools.append(tool_call)
                continue
            
            # Para otras herramientas, verificar duplicados
            is_duplicate = any(
                executed['name'] == tool_call['name'] and 
                executed['args'] == tool_call['args']
                for executed in executed_tools
            )
            if not is_duplicate:
                new_tools.append(tool_call)
        return new_tools
    
    def _validate_and_fix_tool_args(self, tool_name: str, args: Dict) -> Dict:
        """Valida y corrige argumentos de herramientas"""
        validated_args = args.copy()
        
        # Validaciones específicas para edit_task
        if tool_name == "edit_task":
            # Si hay start_date y se refiere a "hoy", usar fecha actual
            if "start_date" in validated_args:
                # Si el usuario dice "hoy" o similar, asegurar fecha correcta
                # Por ahora, registramos para debugging
                print(f"🔍 Validando fecha en edit_task: {validated_args['start_date']}")
            
            # Validar formato de hora
            if "time" in validated_args:
                time_str = validated_args["time"]
                print(f"🕐 Validando hora en edit_task: {time_str}")
        
        return validated_args

    async def _execute_tools_sequential_with_tracking(self, tool_calls: List[Dict], executed_tools: List[Dict]) -> None:
        """Ejecuta herramientas secuencialmente con tracking y logging detallado"""
        for tool_call in tool_calls:
            try:
                print(f"🔧 Ejecutando: {tool_call['name']}")
                
                # Validar argumentos antes de ejecutar
                validated_args = self._validate_and_fix_tool_args(tool_call['name'], tool_call['args'])
                print(f"📋 Argumentos MCP: {validated_args}")
                
                result = await self.mcp_client.execute_tool(tool_call['name'], validated_args)
                
                # Agregar al registro de herramientas ejecutadas
                executed_tools.append({
                    'name': tool_call['name'],
                    'args': validated_args,
                    'result': result[:200] + "..." if len(result) > 200 else result
                })
                
                # Agregar resultado al historial
                self.chat_history.append(ChatMessage(
                    role="assistant", 
                    content=f"Herramienta {tool_call['name']} ejecutada: {result[:500]}..."
                ))
                
                print(f"✅ {tool_call['name']} completado")
                print(f"📊 Resultado (primeros 200 chars): {result[:200]}...")
                
            except Exception as e:
                print(f"❌ Error en {tool_call['name']}: {e}")
                executed_tools.append({
                    'name': tool_call['name'],
                    'args': tool_call.get('args', {}),
                    'result': f"Error: {e}"
                })
                self.chat_history.append(ChatMessage(
                    role="assistant", 
                    content=f"Error ejecutando {tool_call['name']}: {e}"
                ))
    
    async def _execute_tools_sequential(self, tool_calls: List[Dict]) -> None:
        """Ejecuta herramientas secuencialmente y agrega resultados al historial"""
        for tool_call in tool_calls:
            try:
                print(f"🔧 Ejecutando: {tool_call['name']}")
                result = await self.mcp_client.execute_tool(tool_call['name'], tool_call['args'])
                
                # Agregar resultado al historial
                self.chat_history.append(ChatMessage(
                    role="assistant", 
                    content=f"Herramienta {tool_call['name']} ejecutada: {result[:500]}..."
                ))
                
                print(f"✅ {tool_call['name']} completado")
                
            except Exception as e:
                print(f"❌ Error en {tool_call['name']}: {e}")
                self.chat_history.append(ChatMessage(
                    role="assistant", 
                    content=f"Error ejecutando {tool_call['name']}: {e}"
                ))

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
        if not tool_results:
            return "No se pudieron obtener resultados de las herramientas."
        
        context_parts = [
            f"Usuario preguntó: {user_message}",
            "\nInformación obtenida:"
        ]
        
        for result in tool_results:
            # Manejar diferentes formatos de tool_results
            tool_name = result.get('tool_name', result.get('name', 'herramienta'))
            tool_result = result.get('result', str(result))
            context_parts.append(
                f"\n• {tool_name}: {str(tool_result)[:1000]}..."
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
            # Respuesta de fallback más robusta
            if tool_results and len(tool_results) > 0:
                first_result = tool_results[0]
                result_text = first_result.get('result', str(first_result))
                return f"Basado en la información obtenida: {str(result_text)[:500]}..."
            return "Error procesando la información obtenida."
    
    def clear_history(self):
        """Limpiar historial de chat manteniendo el system prompt actualizado"""
        self.chat_history = [
            ChatMessage(role="user", content="Eres Aura, asistente de IA especializado en análisis temporal y tareas. REGLAS CRÍTICAS: 1) SIEMPRE obtén y verifica la hora/fecha actual usando herramientas antes de hacer afirmaciones sobre tiempo. 2) Cuando evalúes si algo es 'futuro' o 'pasado', calcula correctamente basándote en la hora actual obtenida. 3) Para fechas, usa el formato correcto del día actual, no fechas anteriores. 4) Analiza cada solicitud completamente y ejecuta todas las herramientas necesarias para completar la tarea completa. 5) No termines tu respuesta hasta haber completado todos los aspectos de la solicitud.")
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