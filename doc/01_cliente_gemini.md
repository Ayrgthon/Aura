# Cliente Gemini - Documentación Técnica Detallada

## Descripción General

El cliente Gemini de Aura es un sistema sofisticado de IA conversacional que combina el modelo Gemini 2.5 Pro de Google con múltiples herramientas MCP (Model Context Protocol) para crear un asistente autónomo capaz de ejecutar tareas complejas de forma iterativa.

## Arquitectura del Sistema

### Componentes Principales

#### 1. SimpleGeminiClient (`gemini_client.py:45-382`)
Clase principal que orquesta toda la interacción con Gemini y las herramientas MCP.

**Características clave:**
- **Model**: Gemini 2.5 Pro con 1M tokens de context window
- **Configuración de seguridad permisiva**: Todos los filtros de contenido desactivados para máxima flexibilidad
- **Historial persistente**: Mantiene conversaciones completas en memoria
- **Function calls iterativos**: Soporte para hasta 15 iteraciones de herramientas en una sola petición
- **Integración MCP**: Conexión nativa con múltiples servidores de herramientas

#### 2. SimpleMCPClient (`mcp_client.py:33-310`)
Gestor de conexiones a servidores MCP que permite integrar herramientas externas.

**Funcionalidades:**
- **Conexión múltiple**: Maneja varios servidores MCP simultáneamente
- **Schema cleaning**: Convierte automáticamente schemas MCP al formato Gemini
- **Pooling de herramientas**: Centraliza todas las herramientas de diferentes servidores
- **Gestión de sesiones**: Mantiene conexiones persistentes con cleanup automático

#### 3. ChatMessage (`gemini_client.py:31-43`)
Sistema de mensajes optimizado para el formato específico de Gemini.

#### 4. MCPTool (`mcp_client.py:22-31`)
Representación unificada de herramientas MCP con metadatos.

## Configuración y Inicialización

### Variables de Entorno Requeridas
```bash
GOOGLE_API_KEY="tu_api_key_de_google"
SERPAPI_API_KEY="tu_api_key_de_serpapi"
OBSIDIAN_VAULT_PATH="/ruta/a/tu/vault/obsidian"
GOOGLE_CREDENTIALS_PATH="./credentials.json"
GOOGLE_TOKEN_PATH="./token.json"
```

### Proceso de Inicialización (`gemini_client.py:48-89`)

1. **Validación de dependencias**: Verifica disponibilidad de `google-generativeai`
2. **Configuración de API Key**: Configura autenticación con Google AI
3. **Configuración de seguridad**: Establece filtros permisivos
4. **Inicialización del modelo**: Crea instancia de Gemini 2.5 Pro
5. **Setup del historial**: Configura system prompt optimizado para síntesis de voz
6. **Inicialización MCP**: Prepara cliente para conexiones MCP

### System Prompt Especializado (`gemini_client.py:78-82`)
```
"Eres Aura, un asistente de IA autónomo. Es fundamental que sigas estos principios operativos. Para tareas complejas, múltiples herramientas o cualquier reto lógico que requiera razonamiento step-by-step, usa primero 'sequentialthinking' para planificar y luego ejecuta todas las herramientas necesarias. Para investigación, gestión de notas o tareas de planificación, siempre usa 'get_current_datetime' primero para obtener contexto temporal relevante. No te detengas hasta completar todos los pasos planificados y responde de forma directa y útil. Importante también que respondas en texto natural y continuo, sin formato markdown, listas o viñetas, usando párrafos fluidos apropiados para síntesis de voz."
```

**Optimizaciones clave:**
- **Autonomía**: Enfatiza la ejecución completa de tareas
- **Sequential thinking**: Fuerza el uso de razonamiento estructurado
- **Síntesis de voz**: Formato de respuesta optimizado para audio
- **Contextualización temporal**: Uso proactivo de timestamps

## Integración con Herramientas MCP

### Servidores MCP Configurados (`config.py:14-76`)

#### 1. Sequential Thinking (Oficial de Anthropic)
```javascript
{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
}
```
- **Propósito**: Razonamiento estructurado paso a paso
- **Uso**: Planificación de tareas complejas y resolución de problemas

#### 2. SerpAPI (Personalizado)
```javascript
{
  "command": "node",
  "args": ["./mcp/serpapi_server.js"],
  "env": {"SERPAPI_API_KEY": "..."}
}
```
- **Propósito**: Búsqueda web y obtención de información actualizada
- **Integración**: API key desde variables de entorno

#### 3. Obsidian Memory (Personalizado)
```javascript
{
  "command": "node", 
  "args": ["./mcp/obsidian_memory_server.js"],
  "env": {"OBSIDIAN_VAULT_PATH": "..."}
}
```
- **Propósito**: Gestión de memoria persistente y notas
- **Funcionalidades**: Creación, búsqueda y actualización de notas

#### 4. Google Workspace (Personalizado)
```javascript
{
  "command": "node",
  "args": ["./mcp/google_workspace_server.js"],
  "env": {
    "GOOGLE_CREDENTIALS_PATH": "...",
    "GOOGLE_TOKEN_PATH": "..."
  }
}
```
- **Propósito**: Integración con Calendar, Gmail, Drive
- **Autenticación**: OAuth2 con credenciales y tokens

### Proceso de Conexión MCP (`mcp_client.py:48-134`)

1. **Validación MCP SDK**: Verifica disponibilidad del protocolo
2. **Configuración de parámetros**: Setup de comando, argumentos y variables de entorno
3. **Conexión StdIO**: Establece comunicación bidireccional con cada servidor
4. **Inicialización de sesión**: Configura ClientSession para cada servidor
5. **Discovery de herramientas**: Enumera herramientas disponibles via `list_tools`
6. **Pooling centralizado**: Agrega todas las herramientas a una lista unificada
7. **Gestión de errores**: Continúa con servidores funcionales aunque otros fallen

### Conversión de Schemas (`mcp_client.py:193-280`)

**Problema**: Los schemas JSON de MCP contienen campos que Gemini no soporta.

**Solución**: Schema cleaning automático (`_clean_schema_for_gemini`):
- **Campos permitidos**: `type`, `properties`, `required`, `items`, `enum`, `description`
- **Campos removidos**: `minimum`, `maximum`, `format`, `pattern`, etc.
- **Limpieza recursiva**: Procesa propiedades anidadas y arrays
- **Validación**: Asegura schemas válidos con defaults seguros

## Ciclo de Vida de Function Calls

### Proceso Iterativo (`gemini_client.py:177-312`)

El sistema maneja múltiples function calls de forma iterativa, permitiendo que el modelo use resultados de herramientas para ejecutar herramientas adicionales.

#### 1. Detección de Function Calls (`gemini_client.py:202-219`)
```python
for part in candidate.content.parts:
    if hasattr(part, 'function_call') and part.function_call:
        func_call = part.function_call
        if hasattr(func_call, 'name') and func_call.name:
            function_calls.append(func_call)
```

#### 2. Ejecución Paralela (`mcp_client.py:136-191`)
- **Tool lookup**: Busca herramientas en todos los servidores conectados
- **Validación de argumentos**: Verifica parámetros antes de ejecución
- **Ejecución en servidor**: Ejecuta via MCP protocol
- **Procesamiento de resultados**: Normaliza respuestas de diferentes tipos

#### 3. Continuación de Conversación (`gemini_client.py:288-308`)
```python
results_text = "Resultados de las herramientas:\n\n"
for func_resp in function_responses:
    name = func_resp["function_response"]["name"] 
    response = func_resp["function_response"]["response"]
    results_text += f"**{name}**: {response}\n\n"

current_response = chat_session.send_message(results_text, tools=tools)
```

#### 4. Límites y Optimización
- **Máximo 15 iteraciones**: Aprovecha el context window de 1M tokens
- **Detección de ciclos infinitos**: Previene loops de herramientas
- **Manejo de errores robusto**: Continúa ejecución aunque fallen herramientas individuales
- **Fallback inteligente**: Genera respuestas útiles con información parcial

## Gestión de Historial y Memoria

### Sistema de Historial (`gemini_client.py:76-82`, `118-119`, `162-163`)

**Estructura**:
```python
self.chat_history: List[ChatMessage] = [
    ChatMessage(role="user", content="system_prompt"),
    ChatMessage(role="user", content="mensaje_usuario_1"),
    ChatMessage(role="model", content="respuesta_1"),
    # ... conversación completa
]
```

**Características**:
- **Persistente**: Mantiene contexto completo durante la sesión
- **Formato nativo Gemini**: Conversión automática via `to_gemini_format()`
- **Sistema prompt fijo**: Siempre incluye instrucciones de comportamiento
- **Limpieza manual**: Comando `clear` reinicia historial

### Context Window Management

**Gemini 2.5 Pro Features**:
- **1M tokens de context**: Permite conversaciones extensas con múltiples function calls
- **Optimización automática**: Gemini maneja truncation interno si es necesario
- **Historial completo**: Se envía todo el historial en cada request para máximo contexto

## Manejo de Errores y Robustez

### Estrategias de Error Handling

#### 1. Errores de Conexión MCP (`mcp_client.py:119-121`)
```python
except Exception as e:
    print(f"❌ Error conectando a {server_name}: {e}")
    continue  # Continúa con otros servidores
```

#### 2. Errores de Function Call (`gemini_client.py:270-281`)
```python
except Exception as e:
    error_result = f"Error en {func_call.name}: {e}"
    function_responses.append({
        "function_response": {
            "name": func_call.name,
            "response": error_result
        }
    })
```

#### 3. Function Calls Malformados (`gemini_client.py:213-216`, `236-246`)
- **Detección**: Verifica campos obligatorios en function calls
- **Manejo graceful**: Convierte errores en respuestas útiles para el modelo
- **Continuación**: Permite que otros function calls continúen ejecutándose

#### 4. Fallbacks Inteligentes (`gemini_client.py:314-364`)
- **Generación de respuesta final**: Crea respuestas útiles con información parcial
- **Síntesis de resultados**: Combina resultados exitosos ignorando errores
- **Graceful degradation**: Sistema funciona aunque fallen herramientas específicas

## Optimizaciones de Performance

### 1. Conexiones Persistentes MCP
- **AsyncExitStack**: Mantiene conexiones abiertas durante toda la sesión
- **Pooling de sesiones**: Reutiliza conexiones para múltiples calls
- **Cleanup automático**: Gestión de recursos via context managers

### 2. Batch Processing de Function Calls
- **Ejecución paralela**: Procesa múltiples herramientas en una iteración
- **Mínimas roundtrips**: Reduce latencia con menos requests a Gemini
- **Context sharing**: Compartir resultados entre herramientas en la misma iteración

### 3. Schema Optimization
- **Caching de schemas**: Conversión una sola vez al inicializar
- **Schemas mínimos**: Solo incluye campos necesarios para reducir tokens
- **Validación previa**: Evita errores costosos durante ejecución

## Debugging y Monitoreo

### Sistema de Debug (`debug=True`)

**Outputs de diagnóstico**:
```python
print(f"✅ Cliente Gemini inicializado: {self.model_name}")
print(f"🛠️ Herramientas disponibles: {self.mcp_client.get_tool_names()}")
print(f"🔄 Iteración {iteration}: Ejecutando {len(function_calls)} herramientas") 
print(f"🔧 Ejecutando: {func_call.name}")
print(f"📋 Argumentos: {dict(func_call.args)}")
print(f"✅ {func_call.name} completado")
```

**Información de performance**:
- **Número de iteraciones**: Tracking de ciclos de function calls
- **Tiempo de ejecución**: Implícito via timestamps en logs
- **Uso de tokens**: Visible en respuestas de Gemini (cuando debug está activo)

### Logging Estructurado
- **Levels apropiados**: INFO para operaciones normales, DEBUG para detalles
- **Contexto rico**: Incluye nombres de herramientas, argumentos y resultados
- **Error tracking**: Stack traces completos para debugging

## Casos de Uso y Patrones

### 1. Investigación Autónoma
```
Usuario: "Investiga las últimas tendencias en IA generativa"
Sistema: 
1. sequentialthinking -> planifica investigación
2. serpapi -> búsqueda web actualizada
3. obsidian-memory -> guarda información importante
4. respuesta sintetizada
```

### 2. Gestión de Productividad
```
Usuario: "Organiza mi día de mañana"
Sistema:
1. get_current_datetime -> contexto temporal
2. google-workspace -> revisa calendario
3. obsidian-memory -> consulta tareas pendientes 
4. google-workspace -> crea eventos optimizados
```

### 3. Análisis y Síntesis
```
Usuario: "Analiza este documento complejo"
Sistema:
1. sequentialthinking -> estructura análisis
2. obsidian-memory -> busca información relacionada
3. múltiples iteraciones de análisis
4. obsidian-memory -> guarda conclusiones
```

## Consideraciones de Seguridad

### 1. API Keys y Credenciales
- **Variables de entorno**: Nunca hardcodeadas en código
- **Validación de existencia**: Falla gracefully si faltan credenciales
- **Scope mínimo**: Cada herramienta solo accede a sus credenciales específicas

### 2. Filtros de Contenido
- **Configuración permisiva**: Necesaria para casos de uso técnicos
- **Responsabilidad del usuario**: Sistema asume uso ético y legal
- **Logging**: Actividades registradas para auditoría

### 3. Sandbox de Herramientas
- **Aislamiento MCP**: Cada servidor ejecuta en su propio proceso
- **Permisos limitados**: Servidores solo acceden a recursos específicos
- **Error containment**: Fallos aislados no afectan el sistema completo

## Extensibilidad y Personalización

### Agregar Nuevos Servidores MCP

1. **Configuración** (`config.py`):
```python
config["nuevo_servidor"] = {
    "command": "comando",
    "args": ["argumentos"],
    "env": {"VAR": "valor"}
}
```

2. **Auto-discovery**: Sistema detecta automáticamente nuevas herramientas
3. **Schema compatibility**: Conversión automática para Gemini
4. **Error handling**: Robusto ante servidores nuevos o inestables

### Personalización de Comportamiento

- **System prompt**: Modificable para diferentes personalidades o casos de uso
- **Límites de iteración**: Ajustables según necesidades específicas
- **Configuraciones de seguridad**: Personalizables por caso de uso
- **Debugging levels**: Granularidad ajustable para desarrollo vs producción