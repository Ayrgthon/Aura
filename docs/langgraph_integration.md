# LangGraph Integration en Aura

## 🎯 Descripción

LangGraph se ha integrado en Aura para proporcionar un manejo más robusto de flujos complejos, manteniendo la flexibilidad y transparencia del agente actual.

## 🚀 Características

### **Flujo Automático y Transparente**
- ✅ **Análisis automático** de peticiones del usuario
- ✅ **Decisión inteligente** sobre uso de herramientas
- ✅ **Manejo de estados** persistente entre pasos
- ✅ **Fallback automático** al agente simple si LangGraph falla

### **Flexibilidad Total**
- ✅ **Mismo comportamiento** que antes - el usuario no nota diferencia
- ✅ **Comandos naturales** funcionan igual: "Busca noticias", "Crea carpeta", etc.
- ✅ **Herramientas MCP** se usan automáticamente cuando es necesario
- ✅ **Protocolo Notion** se mantiene intacto

### **Control del Usuario**
- ✅ **Habilitar/Deshabilitar** LangGraph en tiempo real
- ✅ **Ver estado** del agente
- ✅ **Debug** del historial y flujos

## 🔧 Instalación

### **Dependencias**
```bash
pip install langgraph>=0.2.0
```

### **Verificación**
```bash
python -c "import langgraph; print('✅ LangGraph instalado')"
```

## 📊 Arquitectura

### **Flujo LangGraph**
```
Usuario → Analizar → ¿Necesita herramientas? → Ejecutar → ¿Continuar? → Respuesta
   ↓         ↓              ↓                      ↓           ↓         ↓
  Input   Análisis      Decisión              Herramientas  Loop    Respuesta
```

### **Estados del Agente**
```python
AgentState:
  - messages: Historial de conversación
  - user_input: Petición actual
  - current_step: Paso actual
  - max_steps: Límite de pasos
  - tools_used: Herramientas utilizadas
  - last_tool_result: Resultado último
  - should_continue: Continuar flujo
  - final_answer: Respuesta final
```

## 🎮 Uso

### **Comandos Disponibles**

#### **Control de LangGraph**
```bash
langgraph on    # Habilitar LangGraph
langgraph off   # Deshabilitar LangGraph
langgraph       # Ver estado actual
```

#### **Información del Sistema**
```bash
status          # Ver estado completo del agente
```

### **Ejemplos de Uso**

#### **Búsqueda Web (Automática)**
```
👤 Tú: Busca las últimas noticias sobre IA
🤖 GEMINI: [LangGraph analiza → Usa Brave Search → Procesa resultados → Responde]
```

#### **Creación de Archivos (Automática)**
```
👤 Tú: Crea una carpeta llamada "proyectos" en Documents
🤖 GEMINI: [LangGraph analiza → Usa Filesystem MCP → Crea carpeta → Confirma]
```

#### **Notion (Protocolo Mantenido)**
```
👤 Tú: Crea una página llamada "Reunión" en quest
🤖 GEMINI: [LangGraph usa protocolo Notion → 4 pasos estrictos → Crea página]
```

## 🔍 Debug y Monitoreo

### **Estado del Agente**
```bash
status
```
**Salida:**
```
🤖 Estado del Agente:
  📊 LangGraph disponible: True
  🔧 LangGraph habilitado: True
  ⚡ Agente LangGraph activo: True
  🛠️ Herramientas MCP: 5
  💬 Historial: 12 mensajes
```

### **Debug del Historial**
```python
client.debug_conversation_history()
```

## ⚙️ Configuración

### **Parámetros Ajustables**
```python
# En client.py
self.use_langgraph = True  # Habilitar por defecto
max_steps = 15             # Máximo pasos por flujo
```

### **Fallback Automático**
- Si LangGraph falla → Agente ReAct simple
- Si LangGraph no está disponible → Agente ReAct simple
- Transparencia total para el usuario

## 🎯 Ventajas sobre ReAct Simple

### **Manejo de Estados**
- ✅ **Persistencia** entre pasos
- ✅ **Contexto mantenido** durante flujos largos
- ✅ **Memoria de herramientas** utilizadas

### **Decisión Inteligente**
- ✅ **Análisis previo** de peticiones
- ✅ **Uso óptimo** de herramientas
- ✅ **Evita loops** infinitos

### **Robustez**
- ✅ **Límites de pasos** configurables
- ✅ **Manejo de errores** mejorado
- ✅ **Fallback automático** garantizado

## 🔧 Personalización

### **Crear Flujos Personalizados**
```python
# En langgraph_agent.py
def _create_flow_graph(self) -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Añadir nodos personalizados
    workflow.add_node("custom_step", self._custom_function)
    
    # Configurar flujo personalizado
    workflow.add_edge("custom_step", "next_step")
```

### **Estados Personalizados**
```python
class CustomAgentState(TypedDict):
    messages: List[BaseMessage]
    custom_field: str
    # ... más campos
```

## 🚨 Solución de Problemas

### **LangGraph No Disponible**
```
⚠️ LangGraph no disponible. Usando agente simple.
```
**Solución:** `pip install langgraph>=0.2.0`

### **Error en Flujo**
```
❌ Error en flujo LangGraph: [error]
```
**Solución:** Fallback automático al agente simple

### **Herramientas No Encontradas**
```
❌ Herramienta 'tool_name' no encontrada
```
**Solución:** Verificar configuración MCP

## 📈 Métricas y Rendimiento

### **Estadísticas del Flujo**
```python
stats = langgraph_agent.get_flow_stats()
# {
#   "tools_available": 5,
#   "max_steps": 15,
#   "langgraph_available": True
# }
```

### **Monitoreo de Rendimiento**
- Tiempo de respuesta por flujo
- Número de pasos utilizados
- Herramientas más usadas
- Tasa de éxito vs fallback

## 🔮 Futuras Mejoras

### **Flujos Especializados**
- Flujo específico para Notion
- Flujo para búsquedas web
- Flujo para manejo de archivos

### **Optimizaciones**
- Cache de resultados
- Paralelización de herramientas
- Predicción de herramientas necesarias

### **Integración Avanzada**
- Grafos personalizados por dominio
- Aprendizaje de patrones de uso
- Optimización automática de flujos 