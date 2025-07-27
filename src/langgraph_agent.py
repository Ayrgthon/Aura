#!/usr/bin/env python3
"""
Módulo LangGraph para manejo de flujos complejos en Aura
Mantiene la flexibilidad del agente actual pero con mejor manejo de estados
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Literal, TypedDict, Annotated
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain_core.messages import BaseMessage

# Importar LangGraph solo si está disponible
try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Definir placeholders para evitar errores
    StateGraph = None
    END = None
    ToolNode = None
    MemorySaver = None
    print("⚠️ LangGraph no disponible. Instala: pip install langgraph")

class AgentState(TypedDict):
    """Estado del agente LangGraph"""
    messages: Annotated[List[BaseMessage], "Historial de mensajes"]
    user_input: Annotated[str, "Entrada del usuario"]
    current_step: Annotated[int, "Paso actual del flujo"]
    max_steps: Annotated[int, "Máximo número de pasos permitidos"]
    tools_used: Annotated[List[str], "Herramientas utilizadas en esta sesión"]
    last_tool_result: Annotated[Optional[str], "Resultado de la última herramienta"]
    should_continue: Annotated[bool, "Si debe continuar el flujo"]
    final_answer: Annotated[Optional[str], "Respuesta final del agente"]

class LangGraphAgent:
    """
    Agente LangGraph que maneja flujos complejos de manera transparente
    Mantiene la flexibilidad del agente actual pero con mejor manejo de estados
    """
    
    def __init__(self, model, tools: List = None, max_steps: int = 10):
        """
        Inicializa el agente LangGraph
        
        Args:
            model: Modelo LLM (Gemini, Ollama, etc.)
            tools: Lista de herramientas disponibles
            max_steps: Máximo número de pasos por flujo
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph no está disponible")
            
        self.model = model
        self.tools = tools or []
        self.max_steps = max_steps
        self.memory = MemorySaver()
        
        # Crear el grafo de flujo
        self.graph = self._create_flow_graph()
        
        print(f"✅ Agente LangGraph inicializado con {len(self.tools)} herramientas")
    
    def _create_flow_graph(self) -> StateGraph:
        """Crea el grafo de flujo del agente"""
        
        # Crear el grafo
        workflow = StateGraph(AgentState)
        
        # Nodos del flujo
        workflow.add_node("analyze", self._analyze_request)
        workflow.add_node("execute_tools", self._execute_tools)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("decide_next", self._decide_next_step)
        
        # Configurar el flujo
        workflow.set_entry_point("analyze")
        
        # Condiciones de flujo
        workflow.add_conditional_edges(
            "analyze",
            self._should_use_tools,
            {
                "tools": "execute_tools",
                "response": "generate_response"
            }
        )
        
        workflow.add_conditional_edges(
            "execute_tools",
            self._should_continue_flow,
            {
                "continue": "decide_next",
                "finish": "generate_response"
            }
        )
        
        workflow.add_conditional_edges(
            "decide_next",
            self._should_continue_flow,
            {
                "continue": "execute_tools",
                "finish": "generate_response"
            }
        )
        
        workflow.add_edge("generate_response", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    def _analyze_request(self, state: AgentState) -> AgentState:
        """Analiza la petición del usuario y decide el siguiente paso"""
        messages = state["messages"]
        user_input = state["user_input"]
        
        print("⚡ LangGraph: Analizando petición del usuario...")
        
        # Crear mensaje de análisis
        analysis_prompt = f"""
        Analiza la siguiente petición del usuario y decide si necesita herramientas:
        
        Petición: {user_input}
        
        Herramientas disponibles: {[tool.name for tool in self.tools]}
        
        Responde con:
        - "tools" si necesita usar herramientas
        - "response" si puede responder directamente
        
        Solo responde con una palabra: tools o response
        """
        
        # Usar el modelo para analizar
        response = self.model.invoke([HumanMessage(content=analysis_prompt)])
        decision = response.content.strip().lower()
        
        print(f"⚡ LangGraph: Decisión: {decision}")
        
        # Actualizar estado
        state["should_continue"] = decision == "tools"
        state["current_step"] = 1
        
        return state
    
    def _should_use_tools(self, state: AgentState) -> Literal["tools", "response"]:
        """Decide si usar herramientas o responder directamente"""
        return "tools" if state["should_continue"] else "response"
    
    def _execute_tools(self, state: AgentState) -> AgentState:
        """Ejecuta las herramientas necesarias"""
        messages = state["messages"]
        user_input = state["user_input"]
        
        print("⚡ LangGraph: Ejecutando herramientas...")
        
        # Crear mensaje para el modelo con herramientas
        model_with_tools = self.model.bind_tools(self.tools)
        
        # Obtener respuesta del modelo
        response = model_with_tools.invoke(messages + [HumanMessage(content=user_input)])
        
        # Ejecutar herramientas si las pidió
        if hasattr(response, 'tool_calls') and getattr(response, 'tool_calls'):
            for tool_call in getattr(response, 'tool_calls'):
                tool_name = tool_call['name']
                tool_args = tool_call.get('args', {})
                
                print(f"⚡ LangGraph: Ejecutando herramienta: {tool_name}")
                
                # Ejecutar herramienta
                try:
                    result = self._execute_single_tool(tool_call)
                    state["last_tool_result"] = result
                    state["tools_used"].append(tool_name)
                    
                    # Añadir al historial
                    messages.append(AIMessage(content="", additional_kwargs={'tool_calls':[tool_call]}))
                    messages.append(HumanMessage(content=f"Observación: {result}"))
                    
                except Exception as e:
                    error_msg = f"Error ejecutando {tool_name}: {e}"
                    state["last_tool_result"] = error_msg
                    messages.append(HumanMessage(content=f"Error: {error_msg}"))
        else:
            print("⚡ LangGraph: No se requirieron herramientas")
        
        state["messages"] = messages
        return state
    
    def _execute_single_tool(self, tool_call: Dict[str, Any]) -> str:
        """Ejecuta una herramienta individual"""
        tool_name = tool_call['name']
        tool_args = tool_call.get('args', {})
        
        # Buscar la herramienta
        target_tool = None
        for tool in self.tools:
            if tool.name == tool_name:
                target_tool = tool
                break
        
        if not target_tool:
            raise Exception(f"Herramienta '{tool_name}' no encontrada")
        
        # Ejecutar herramienta
        try:
            result = target_tool.invoke(tool_args)
            return str(result)
        except Exception as e:
            raise Exception(f"Error ejecutando herramienta: {e}")
    
    def _should_continue_flow(self, state: AgentState) -> Literal["continue", "finish"]:
        """Decide si continuar el flujo o terminar"""
        current_step = state["current_step"]
        max_steps = state["max_steps"]
        
        # Verificar límite de pasos
        if current_step >= max_steps:
            return "finish"
        
        # Verificar si hay resultado de herramienta
        if state["last_tool_result"]:
            # Preguntar al modelo si debe continuar
            continue_prompt = f"""
            Basándote en el resultado de la herramienta:
            {state["last_tool_result"]}
            
            ¿Necesitas hacer algo más o puedes dar la respuesta final?
            Responde con "continue" o "finish"
            """
            
            response = self.model.invoke([HumanMessage(content=continue_prompt)])
            decision = response.content.strip().lower()
            
            if decision == "continue":
                state["current_step"] += 1
                return "continue"
        
        return "finish"
    
    def _decide_next_step(self, state: AgentState) -> AgentState:
        """Decide el siguiente paso basado en el resultado anterior"""
        # El modelo decide automáticamente basado en el historial
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Genera la respuesta final"""
        messages = state["messages"]
        user_input = state["user_input"]
        
        print("⚡ LangGraph: Generando respuesta final...")
        
        # Generar respuesta final
        final_response = self.model.invoke(messages + [HumanMessage(content=user_input)])
        
        state["final_answer"] = final_response.content
        state["should_continue"] = False
        
        print("⚡ LangGraph: Respuesta generada exitosamente")
        
        return state
    
    async def run(self, user_input: str, conversation_history: List[BaseMessage] = None) -> str:
        """
        Ejecuta el flujo del agente
        
        Args:
            user_input: Entrada del usuario
            conversation_history: Historial de conversación
            
        Returns:
            Respuesta final del agente
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph no está disponible")
        
        print("⚡ LangGraph: Iniciando flujo de análisis...")
        
        # Preparar estado inicial
        initial_state = AgentState(
            messages=conversation_history or [],
            user_input=user_input,
            current_step=0,
            max_steps=self.max_steps,
            tools_used=[],
            last_tool_result=None,
            should_continue=True,
            final_answer=None
        )
        
        # Ejecutar el flujo
        try:
            print("⚡ LangGraph: Ejecutando grafo de flujo...")
            result = await self.graph.ainvoke(initial_state)
            print(f"⚡ LangGraph: Flujo completado. Herramientas usadas: {result.get('tools_used', [])}")
            return result["final_answer"] or "No se pudo generar una respuesta"
            
        except Exception as e:
            print(f"❌ Error en flujo LangGraph: {e}")
            # Fallback al método simple
            return await self._fallback_response(user_input, conversation_history)
    
    async def _fallback_response(self, user_input: str, conversation_history: List[BaseMessage] = None) -> str:
        """Método de fallback si LangGraph falla"""
        messages = conversation_history or []
        messages.append(HumanMessage(content=user_input))
        
        response = self.model.invoke(messages)
        return response.content
    
    def get_flow_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del flujo"""
        return {
            "tools_available": len(self.tools),
            "max_steps": self.max_steps,
            "langgraph_available": LANGGRAPH_AVAILABLE
        }

# Función de utilidad para crear el agente
def create_langgraph_agent(model, tools: List = None, max_steps: int = 10) -> Optional[LangGraphAgent]:
    """
    Crea un agente LangGraph si está disponible
    
    Args:
        model: Modelo LLM
        tools: Lista de herramientas
        max_steps: Máximo número de pasos
        
    Returns:
        Agente LangGraph o None si no está disponible
    """
    if not LANGGRAPH_AVAILABLE:
        print("⚠️ LangGraph no disponible. Usando agente simple.")
        return None
    
    try:
        return LangGraphAgent(model, tools, max_steps)
    except Exception as e:
        print(f"❌ Error creando agente LangGraph: {e}")
        return None 