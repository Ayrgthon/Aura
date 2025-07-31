#!/usr/bin/env python3
"""
Agente Estructurado - Sistema formal de agente multipasos
Reemplaza el sistema artesanal basado en prompts con lógica explícita
"""

import json
import asyncio
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


class TaskState(Enum):
    """Estados explícitos del agente"""
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    SYNTHESIZING = "synthesizing"
    DONE = "done"


@dataclass
class Goal:
    """Representa un objetivo específico a completar"""
    text: str
    goal_type: str = "search"  # search, file_operation, memory, etc.
    keywords: List[str] = field(default_factory=list)
    completed: bool = False
    evidence: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        # Extraer keywords automáticamente
        if not self.keywords:
            self.keywords = self._extract_keywords()
    
    def _extract_keywords(self) -> List[str]:
        """Extrae keywords del texto del objetivo"""
        import re
        # Buscar palabras clave importantes
        text_lower = self.text.lower()
        keywords = []
        
        # Nombres de superhéroes y personajes
        characters = ["batman", "superman", "spiderman", "spider-man", "joker", "wonder woman"]
        for char in characters:
            if char in text_lower:
                keywords.append(char)
        
        # Palabras clave de acción
        actions = ["buscar", "investigar", "encontrar", "listar", "crear", "escribir"]
        for action in actions:
            if action in text_lower:
                keywords.append(action)
        
        # Extraer palabras importantes (sustantivos probables)
        words = re.findall(r'\b[a-záéíóúñ]{4,}\b', text_lower)
        keywords.extend(words[:3])  # Máximo 3 palabras adicionales
        
        return list(set(keywords))


@dataclass
class ToolAction:
    """Representa una acción específica con una herramienta"""
    tool_name: str
    arguments: Dict[str, Any]
    goal_id: Optional[str] = None
    priority: int = 1
    executed: bool = False
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass  
class AgentState:
    """Estado completo del agente durante la ejecución"""
    user_input: str
    current_state: TaskState = TaskState.ANALYZING
    goals: List[Goal] = field(default_factory=list)
    completed_goals: List[Goal] = field(default_factory=list)
    current_plan: List[ToolAction] = field(default_factory=list)
    executed_actions: List[ToolAction] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def pending_goals(self) -> List[Goal]:
        """Objetivos que aún no se han completado"""
        return [g for g in self.goals if not g.completed]
    
    @property
    def completion_percentage(self) -> float:
        """Porcentaje de objetivos completados"""
        if not self.goals:
            return 0.0
        return len(self.completed_goals) / len(self.goals) * 100


class ObjectiveAnalyzer:
    """Analiza la solicitud del usuario y extrae objetivos específicos"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def analyze_request(self, user_input: str) -> List[Goal]:
        """
        Analiza la solicitud y extrae objetivos específicos
        
        Args:
            user_input: Solicitud del usuario
            
        Returns:
            Lista de objetivos estructurados
        """
        # Prompt específico para análisis de objetivos
        analysis_prompt = f"""
        Analiza esta solicitud del usuario y extrae objetivos específicos de INFORMACIÓN/DATOS:
        
        Solicitud: "{user_input}"
        
        IMPORTANTE: 
        - Solo incluye objetivos que requieren obtener información específica
        - NO incluyas objetivos de "generar reporte" o "hacer resumen" (eso es síntesis final)
        - Enfócate en QUÉ información necesita obtener el usuario
        
        Responde ÚNICAMENTE en este formato JSON válido:
        {{
            "objectives": [
                {{
                    "text": "obtener/buscar información específica sobre X",
                    "type": "search|file_operation|memory",
                    "keywords": ["palabra1", "palabra2"]
                }}
            ]
        }}
        
        Ejemplos:
        - "Busca batman y superman" → 2 objetivos de búsqueda
        - "Busca X, luego busca Y y hazme un reporte" → 2 objetivos de búsqueda (no incluir "reporte")
        - "Lee archivo.txt y busca errores" → 1 file_operation + 1 search
        """
        
        try:
            from gemini_client import Message
            analysis_messages = [Message(role="user", content=analysis_prompt)]
            response = self.llm_client.generate(analysis_messages)
            
            # Extraer JSON de la respuesta
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                # Fallback: crear objetivos básicos
                return self._create_fallback_goals(user_input)
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            goals = []
            for obj in data.get("objectives", []):
                goal = Goal(
                    text=obj.get("text", ""),
                    goal_type=obj.get("type", "search"),
                    keywords=obj.get("keywords", [])
                )
                goals.append(goal)
            
            return goals if goals else self._create_fallback_goals(user_input)
            
        except Exception as e:
            print(f"⚠️  Error en análisis de objetivos: {e}")
            return self._create_fallback_goals(user_input)
    
    def _create_fallback_goals(self, user_input: str) -> List[Goal]:
        """Crea objetivos básicos cuando falla el análisis automático"""
        # Detección simple de palabras clave
        text_lower = user_input.lower()
        goals = []
        
        # Buscar personajes/temas conocidos
        characters = ["batman", "superman", "spiderman", "spider-man"]
        for char in characters:
            if char in text_lower:
                goals.append(Goal(
                    text=f"Buscar información sobre {char}",
                    goal_type="search",
                    keywords=[char]
                ))
        
        # Si no se encontraron objetivos específicos, crear uno genérico
        if not goals:
            goals.append(Goal(
                text=f"Procesar solicitud: {user_input}",
                goal_type="search",
                keywords=[]
            ))
        
        return goals


class ActionPlanner:
    """Crea planes de ejecución específicos para objetivos"""
    
    def __init__(self, available_tools: List[Any]):
        self.available_tools = available_tools
        self.tool_mapping = self._create_tool_mapping()
    
    def _create_tool_mapping(self) -> Dict[str, str]:
        """Mapea tipos de objetivos a herramientas específicas"""
        mapping = {}
        
        for tool in self.available_tools:
            tool_name = tool.name.lower()
            
            # Mapeo más específico basado en nombres de herramientas
            if "brave" in tool_name or "web_search" in tool_name:
                mapping["web_search"] = tool.name
            elif "search" in tool_name and "note" not in tool_name:
                mapping["search"] = tool.name
            elif "file" in tool_name or "read" in tool_name:
                mapping["file_operation"] = tool.name  
            elif "memory" in tool_name or "note" in tool_name:
                mapping["memory"] = tool.name
        
        # Preferir búsqueda web para información actual
        if "web_search" in mapping:
            mapping["search"] = mapping["web_search"]
        
        return mapping
    
    def create_execution_plan(self, goals: List[Goal]) -> List[ToolAction]:
        """
        Crea un plan de ejecución específico para los objetivos
        
        Args:
            goals: Lista de objetivos a completar
            
        Returns:
            Lista de acciones ordenadas por prioridad
        """
        actions = []
        
        for i, goal in enumerate(goals):
            action = self._goal_to_action(goal, priority=i+1)
            if action:
                actions.append(action)
        
        # Ordenar acciones por prioridad
        actions.sort(key=lambda x: x.priority)
        
        return actions
    
    def _goal_to_action(self, goal: Goal, priority: int = 1) -> Optional[ToolAction]:
        """Convierte un objetivo en una acción específica"""
        goal_type = goal.goal_type
        
        if goal_type == "search":
            # Buscar herramienta de búsqueda web específicamente
            search_tool = None
            for tool in self.available_tools:
                if "brave" in tool.name.lower() and "search" in tool.name.lower():
                    search_tool = tool.name
                    break
            
            if not search_tool:
                search_tool = self.tool_mapping.get("search", "brave_web_search")
            
            # Crear query de búsqueda más específica
            if goal.keywords:
                # Filtrar keywords útiles
                useful_keywords = [k for k in goal.keywords if len(k) > 3 and k not in ["latest", "news", "buscar"]]
                if useful_keywords:
                    query = " ".join(useful_keywords[:3])
                else:
                    query = " ".join(goal.keywords[:3])
            else:
                query = goal.text
            
            # Detectar si necesita información reciente
            needs_recent = any(word in goal.text.lower() for word in ["últimas", "recientes", "actuales", "2025", "julio"])
            if needs_recent:
                query = f"latest news {query} 2025"
            else:
                query = f"news {query}"
            
            return ToolAction(
                tool_name=search_tool,
                arguments={"query": query},
                goal_id=goal.text,
                priority=priority
            )
        
        elif goal_type == "file_operation":
            # Mapear a herramientas de archivo
            file_tool = self.tool_mapping.get("file_operation", "read_file")
            
            return ToolAction(
                tool_name=file_tool,
                arguments={"path": goal.keywords[0] if goal.keywords else ""},
                goal_id=goal.text,
                priority=priority
            )
        
        elif goal_type == "memory":
            # Mapear a herramientas de memoria/notas
            memory_tool = self.tool_mapping.get("memory", "search_notes")
            
            return ToolAction(
                tool_name=memory_tool,
                arguments={"query": " ".join(goal.keywords)},
                goal_id=goal.text,
                priority=priority
            )
        
        return None


class CompletionEvaluator:
    """Evalúa si los objetivos han sido completados"""
    
    def evaluate_goal_completion(self, goal: Goal, action_results: List[ToolAction]) -> bool:
        """
        Evalúa si un objetivo específico ha sido completado
        
        Args:
            goal: Objetivo a evaluar
            action_results: Resultados de acciones ejecutadas
            
        Returns:
            True si el objetivo está completado
        """
        # Buscar evidencia en los resultados de las acciones
        relevant_results = [
            action for action in action_results 
            if action.goal_id == goal.text and action.result
        ]
        
        if not relevant_results:
            return False
        
        # Verificar que hay contenido útil en los resultados
        for action in relevant_results:
            if action.result and len(action.result.strip()) > 10:
                # Verificar que el resultado contiene información relevante
                result_lower = action.result.lower()
                keyword_matches = sum(
                    1 for keyword in goal.keywords 
                    if keyword.lower() in result_lower
                )
                
                # Si al menos la mitad de las keywords aparecen en el resultado
                if len(goal.keywords) == 0 or keyword_matches >= len(goal.keywords) * 0.5:
                    goal.evidence.append(f"Encontrado en {action.tool_name}: {action.result[:100]}...")
                    return True
        
        return False
    
    def should_continue_execution(self, state: AgentState) -> bool:
        """
        Determina si el agente debe continuar ejecutando acciones
        
        Args:
            state: Estado actual del agente
            
        Returns:
            True si debe continuar
        """
        # Verificar límites
        if state.iteration >= state.max_iterations:
            print(f"🛑 Límite de iteraciones alcanzado ({state.max_iterations})")
            return False
        
        # Verificar si todos los objetivos están completados
        if len(state.completed_goals) >= len(state.goals):
            print("✅ Todos los objetivos completados")
            return False
        
        # Verificar si hay acciones pendientes en el plan
        pending_actions = [a for a in state.current_plan if not a.executed]
        if not pending_actions:
            print("📋 No hay más acciones planificadas")
            return False
        
        return True


class StructuredAgent:
    """Agente estructurado con lógica explícita para decisiones"""
    
    def __init__(self, llm_client, mcp_client, available_tools):
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.available_tools = available_tools
        
        # Componentes especializados
        self.analyzer = ObjectiveAnalyzer(llm_client)
        self.planner = ActionPlanner(available_tools)
        self.evaluator = CompletionEvaluator()
        
        # Debug: mostrar herramientas disponibles
        print(f"🔧 Herramientas disponibles para agente estructurado:")
        for tool in available_tools:
            print(f"   - {tool.name}")
        print(f"🗺️  Mapeo de herramientas: {self.planner.tool_mapping}")
    
    async def execute_structured_task(self, user_input: str) -> str:
        """
        Ejecuta una tarea usando el sistema estructurado
        
        Args:
            user_input: Solicitud del usuario
            
        Returns:
            Respuesta final sintetizada
        """
        print("🏗️  Iniciando agente estructurado")
        
        # Inicializar estado
        state = AgentState(user_input=user_input)
        
        try:
            # 1. ANÁLISIS: Extraer objetivos explícitos
            state.current_state = TaskState.ANALYZING
            print("🔍 Analizando solicitud y extrayendo objetivos...")
            
            state.goals = await self.analyzer.analyze_request(user_input)
            print(f"🎯 Objetivos identificados ({len(state.goals)}):")
            for i, goal in enumerate(state.goals, 1):
                print(f"   {i}. {goal.text} [keywords: {', '.join(goal.keywords)}]")
            
            # 2. PLANIFICACIÓN: Crear plan específico
            state.current_state = TaskState.PLANNING
            print("\n📋 Creando plan de ejecución...")
            
            state.current_plan = self.planner.create_execution_plan(state.goals)
            print(f"⚡ Plan creado con {len(state.current_plan)} acciones:")
            for i, action in enumerate(state.current_plan, 1):
                print(f"   {i}. {action.tool_name}({action.arguments}) → {action.goal_id}")
            
            # 3. EJECUCIÓN: Loop controlado por lógica explícita
            state.current_state = TaskState.EXECUTING
            print(f"\n🚀 Iniciando ejecución (máx. {state.max_iterations} iteraciones)")
            
            while self.evaluator.should_continue_execution(state):
                state.iteration += 1
                print(f"\n🔄 Iteración {state.iteration}")
                
                # Ejecutar siguiente acción del plan
                pending_actions = [a for a in state.current_plan if not a.executed]
                if pending_actions:
                    action = pending_actions[0]
                    await self._execute_action(action, state)
                
                # 4. EVALUACIÓN: Verificar objetivos completados
                state.current_state = TaskState.EVALUATING
                self._evaluate_progress(state)
            
            # 5. SÍNTESIS: Crear respuesta final
            state.current_state = TaskState.SYNTHESIZING
            print(f"\n🧠 Sintetizando respuesta final...")
            print(f"📊 Progreso: {state.completion_percentage:.1f}% completado")
            
            final_response = await self._synthesize_final_response(state)
            
            state.current_state = TaskState.DONE
            return final_response
            
        except Exception as e:
            print(f"❌ Error en agente estructurado: {e}")
            import traceback
            traceback.print_exc()
            return f"Error ejecutando tarea: {e}"
    
    async def _execute_action(self, action: ToolAction, state: AgentState):
        """Ejecuta una acción específica"""
        print(f"🔧 Ejecutando: {action.tool_name} → {action.goal_id}")
        
        try:
            # Ejecutar herramienta MCP
            result = await self.mcp_client.execute_tool(action.tool_name, action.arguments)
            
            action.result = result
            action.executed = True
            state.executed_actions.append(action)
            
            # Agregar a resultados globales para síntesis
            state.tool_results.append({
                'tool_name': action.tool_name,
                'query': action.arguments,
                'result': result
            })
            
            print(f"✅ {action.tool_name} completado ({len(result)} caracteres)")
            
        except Exception as e:
            print(f"❌ Error ejecutando {action.tool_name}: {e}")
            action.error = str(e)
            action.executed = True
    
    def _evaluate_progress(self, state: AgentState):
        """Evalúa el progreso y actualiza objetivos completados"""
        print("📊 Evaluando progreso...")
        
        for goal in state.goals:
            if not goal.completed:
                is_completed = self.evaluator.evaluate_goal_completion(goal, state.executed_actions)
                if is_completed:
                    goal.completed = True
                    state.completed_goals.append(goal)
                    print(f"   ✅ Objetivo completado: {goal.text}")
                else:
                    print(f"   ⏳ Pendiente: {goal.text}")
        
        # Mostrar progreso
        progress = len(state.completed_goals) / len(state.goals) * 100
        print(f"   📈 Progreso total: {progress:.1f}% ({len(state.completed_goals)}/{len(state.goals)})")
    
    async def _synthesize_final_response(self, state: AgentState) -> str:
        """Sintetiza la respuesta final basada en todos los resultados"""
        if not state.tool_results:
            return "No se pudo obtener información para completar la solicitud."
        
        # Construir contexto para síntesis
        context_parts = [
            f"Solicitud original: {state.user_input}",
            f"Objetivos completados: {len(state.completed_goals)}/{len(state.goals)}",
            "\nInformación recopilada:"
        ]
        
        for result in state.tool_results:
            context_parts.append(
                f"\n• {result['tool_name']}: {result['result'][:1500]}..."
            )
        
        context_parts.append(
            "\nInstrucciones: Basándote en la información recopilada, responde la solicitud original "
            "de manera natural y conversacional. Organiza la información de forma clara y útil. "
            "NO menciones herramientas técnicas ni procesos internos."
        )
        
        synthesis_prompt = "".join(context_parts)
        
        try:
            from gemini_client import Message
            synthesis_messages = [Message(role="user", content=synthesis_prompt)]
            response = self.llm_client.generate(synthesis_messages)
            return response
            
        except Exception as e:
            print(f"❌ Error en síntesis: {e}")
            # Fallback simple
            return f"Información encontrada sobre: {', '.join([g.text for g in state.completed_goals])}"
