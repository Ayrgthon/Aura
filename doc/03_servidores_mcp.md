# Servidores MCP - Documentación Técnica Detallada

## Descripción General

Los servidores MCP (Model Context Protocol) de Aura son herramientas especializadas desarrolladas en Node.js que extienden las capacidades del asistente mediante integraciones con APIs externas y sistemas locales. Cada servidor implementa el protocolo MCP estándar, proporcionando herramientas específicas para diferentes dominios funcionales.

## Arquitectura del Sistema MCP

### Protocolo MCP Implementado

**Especificación**: MCP 2024-11-05  
**Transporte**: StdIO (Standard Input/Output)  
**Formato**: JSON-RPC 2.0  
**Lenguaje**: Node.js con ES6+

### Estructura Base de Servidores

```javascript
class MCPServer {
    constructor() {
        this.tools = []; // Definición de herramientas disponibles
    }
    
    async handleRequest(request) {
        const { method, params, id } = request;
        // Routing de métodos MCP estándar
    }
    
    initialize() {
        return {
            protocolVersion: "2024-11-05",
            capabilities: { tools: { listChanged: false } },
            serverInfo: { name: "server-name", version: "1.0.0" }
        };
    }
    
    async callTool(params) {
        // Ejecución de herramientas específicas
    }
}
```

## Servidor SerpAPI (`serpapi_server.js`)

### Propósito y Funcionalidad

Integración con SerpAPI para búsquedas web avanzadas, proporcionando acceso a resultados de Google Search, Google News y Google Images de forma programática.

### Configuración y Autenticación (`serpapi_server.js:12-25`)

```javascript
const MCP_CONFIG = {
    name: "serpapi",
    version: "1.0.0",
    api_key: process.env.SERPAPI_API_KEY
};
```

**Variables de entorno requeridas:**
- `SERPAPI_API_KEY`: API key de SerpAPI (obtenida desde serpapi.com)

### Herramientas Disponibles

#### 1. google_search (`serpapi_server.js:194-231`)

**Funcionalidad**: Búsquedas generales en Google con resultados orgánicos, snippets destacados y knowledge graph.

**Parámetros:**
```javascript
{
    query: "string",           // Término de búsqueda (requerido)
    location: "Colombia",      // Ubicación geográfica
    language: "es",            // Idioma de resultados
    num_results: 10,           // Número de resultados (1-100)
    safe_search: "active"      // Filtro de contenido
}
```

**Procesamiento de resultados:**
- **Answer Box**: Respuestas destacadas de Google
- **Knowledge Graph**: Panel de información lateral
- **Resultados orgánicos**: Links principales con títulos y snippets
- **Búsquedas relacionadas**: Sugerencias adicionales

#### 2. google_news_search (`serpapi_server.js:233-269`)

**Funcionalidad**: Búsqueda específica en Google News con filtros temporales.

**Parámetros especializados:**
```javascript
{
    time_period: "qdr:d",      // qdr:h (1 hora), qdr:d (1 día), qdr:w (1 semana)
    // ... parámetros base de búsqueda
}
```

#### 3. google_images_search (`serpapi_server.js:271-309`)

**Funcionalidad**: Búsqueda de imágenes con filtros de tamaño y tipo.

**Parámetros específicos:**
```javascript
{
    image_size: "medium",      // large, medium, icon
    image_type: "photo",       // photo, clipart, lineart, face, news
    num_results: 10            // Máximo 50 para imágenes
}
```

### Sistema de Requests HTTP (`serpapi_server.js:311-374`)

**Implementación robusta con:**
- **Timeout configurado**: 30 segundos máximo
- **Manejo de errores HTTP**: Códigos de estado y mensajes específicos
- **Parsing de JSON seguro**: Validación de estructura de respuesta
- **User-Agent específico**: Identificación como cliente Aura
- **Error handling**: Reintentos y mensajes informativos

### Formato de Salida

```markdown
🔍 **Resultados de Google para: "query"**

📌 **Respuesta destacada:**
[Snippet destacado si existe]
🔗 Fuente: [URL]

---

📋 **Resultados orgánicos:**

1. **Título del resultado**
🔗 [URL]
📝 [Snippet descriptivo]
📅 [Fecha si disponible]

🔍 **Búsquedas relacionadas:**
• Término relacionado 1
• Término relacionado 2
```

## Servidor Obsidian Memory (`obsidian_memory_server.js`)

### Propósito y Funcionalidad

Sistema de memoria persistente integrado con Obsidian Vault, proporcionando gestión completa de notas, búsqueda semántica y manejo de metadatos para crear una base de conocimientos centralizada.

### Configuración del Vault (`obsidian_memory_server.js:14-22`)

```javascript
const MCP_CONFIG = {
    name: "obsidian-memory",
    version: "1.0.0",
    vault_path: process.env.OBSIDIAN_VAULT_PATH || "/home/ary/Documents/Ary Vault"
};
```

**Variables de entorno:**
- `OBSIDIAN_VAULT_PATH`: Ruta completa al vault de Obsidian

### Herramientas de Gestión de Memoria

#### 1. search_notes (`obsidian_memory_server.js:273-304`)

**Sistema de búsqueda inteligente con múltiples modalidades:**

```javascript
{
    query: "string",                    // Término de búsqueda
    search_type: "all",                 // content, filename, tags, wikilinks, all
    max_results: 10                     // Límite de resultados
}
```

**Algoritmo de búsqueda (`obsidian_memory_server.js:306-385`):**

1. **Detección automática de tipo:**
   ```javascript
   const isTagSearch = query.startsWith('#');
   const isWikilinkSearch = query.includes('[[') || query.includes(']]');
   ```

2. **Sistema de relevancia:**
   - Coincidencia en nombre de archivo: +10 puntos
   - Coincidencia en contenido: +2 puntos por match
   - Coincidencia en etiquetas: +5 puntos por tag
   - Coincidencia en wikilinks: +3 puntos por link

3. **Extracción de metadatos:**
   ```javascript
   extractTags(content) {
       const tagRegex = /#[a-zA-Z0-9_-]+/g;
       return content.match(tagRegex) || [];
   }
   
   extractWikilinks(content) {
       const wikilinkRegex = /\[\[([^\]]+)\]\]/g;
       // Extrae todos los [[wikilinks]] del contenido
   }
   ```

#### 2. read_note (`obsidian_memory_server.js:439-463`)

**Lectura completa de notas con metadatos:**
- Contenido completo de la nota
- Información de archivo (tamaño, fecha de modificación)
- Ruta relativa dentro del vault

#### 3. create_note (`obsidian_memory_server.js:465-506`)

**Creación de notas con estructura automática:**

```javascript
// Template automático generado
const finalContent = `# ${path.basename(note_path, '.md')}

*Creado: ${timestamp}*

${content}`;
```

**Características:**
- **Creación de directorios**: Automática si no existen
- **Verificación de existencia**: Previene sobrescritura accidental
- **Timestamping**: Marcas de tiempo automáticas
- **Estructura consistente**: Headers y metadatos estandarizados

#### 4. update_note (`obsidian_memory_server.js:508-555`)

**Actualización flexible con tres modalidades:**

```javascript
switch (mode) {
    case 'append':   // Agregar al final con timestamp
    case 'prepend':  // Agregar al inicio con timestamp  
    case 'replace':  // Reemplazar completamente con timestamp
}
```

#### 5. get_current_datetime (`obsidian_memory_server.js:685-748`)

**Sistema de timestamps contextual:**

```javascript
// Zona horaria America/Bogotá configurada
const options = {
    timeZone: 'America/Bogota',
    // ... opciones de formato
};
```

**Formatos disponibles:**
- `iso`: 2025-08-10T14:30:00-05:00
- `readable`: "sábado, 10 de agosto de 2025, 14:30:00"
- `date_only`: "sábado, 10 de agosto de 2025"
- `time_only`: "14:30:00"

### Gestión Avanzada del Vault

#### list_vault_structure (`obsidian_memory_server.js:557-576`)

**Exploración recursiva de la estructura:**
- Listado completo de archivos .md y directorios
- Control de profundidad para evitar estructuras muy grandes
- Organización jerárquica de la información

#### Operaciones Destructivas Seguras

**delete_note y delete_folder** requieren confirmación explícita:
```javascript
if (!confirm) {
    throw new Error('Debes confirmar la eliminación estableciendo confirm=true');
}
```

### Sistema de Vista Previa (`obsidian_memory_server.js:403-419`)

**Generación inteligente de snippets:**
```javascript
generatePreview(content, searchTerm) {
    // Busca líneas que contengan el término
    // Si no encuentra, toma las primeras líneas
    // Limita a 200 caracteres para resúmenes concisos
}
```

## Servidor Google Workspace (`google_workspace_server.js`)

### Propósito y Funcionalidad

Integración completa con Google Workspace (Calendar, Gmail, Drive) proporcionando gestión avanzada de calendario, envío de emails y análisis de productividad.

### Configuración OAuth2 (`google_workspace_server.js:14-28`)

```javascript
const MCP_CONFIG = {
    name: "google-workspace",
    version: "1.0.0",
    credentials_path: process.env.GOOGLE_CREDENTIALS_PATH || './credentials.json',
    token_path: process.env.GOOGLE_TOKEN_PATH || './token.json',
    user_email: "ayrgthon223@gmail.com"
};

const SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
];
```

### Sistema de Autenticación (`google_workspace_server.js:345-365`)

**Flujo OAuth2 completo:**
1. **Carga de credenciales**: `credentials.json` desde Google Cloud Console
2. **Configuración del cliente**: OAuth2Client con redirect URIs
3. **Carga de tokens**: `token.json` con access/refresh tokens
4. **Manejo de renovación**: Automático via googleapis library

### Herramientas de Calendar

#### 1. list_calendar_events (`google_workspace_server.js:434-546`)

**Consulta flexible de eventos con múltiples filtros:**

```javascript
// Períodos predefinidos
switch (time_period) {
    case 'today':    // Día actual completo
    case 'tomorrow': // Día siguiente completo  
    case 'week':     // Próximos 7 días
    case 'month':    // Próximo mes
    case 'custom':   // Rango personalizado
}
```

**Características avanzadas:**
- **Búsqueda por texto**: Query en título y descripción
- **Ordenamiento temporal**: `orderBy: 'startTime'`
- **Eventos únicos**: `singleEvents: true` para series recurrentes
- **Límites configurables**: Hasta 50 eventos por request

#### 2. create_calendar_event (`google_workspace_server.js:548-684`)

**Creación avanzada de eventos con múltiples opciones:**

```javascript
// Configuración de fechas inteligente
if (!end_datetime) {
    const startDate = new Date(start_datetime);
    startDate.setHours(startDate.getHours() + 1); // Default 1 hora
    endDateTime = startDate.toISOString().slice(0, 19);
}
```

**Características especiales:**
- **Google Meet automático**: `create_meet: true`
- **Recordatorios configurables**: Email y popup con timing específico
- **Colores organizacionales**: 11 colores predefinidos
- **Invitaciones automáticas**: Lista de attendees con notificación
- **Zonas horarias**: Soporte completo para America/Bogota

#### 3. update_calendar_event (`google_workspace_server.js:686-798`)

**Actualización inteligente con búsqueda:**

```javascript
// Búsqueda por título si no hay ID
if (!eventId && search_title) {
    const searchResponse = await calendar.events.list({
        calendarId: 'primary',
        q: search_title,
        maxResults: 1,
        singleEvents: true,
        orderBy: 'startTime'
    });
}
```

**Modalidades de actualización:**
- **Reemplazo completo**: Lista nueva de attendees
- **Adición incremental**: `add_attendees` para agregar sin reemplazar
- **Preservación de metadatos**: Mantiene timezone y configuraciones existentes

#### 4. find_free_time (`google_workspace_server.js:862-968`)

**Algoritmo inteligente de búsqueda de disponibilidad:**

```javascript
// Configuración de horario laboral
const workStart = working_hours_only ? 9 : 0;
const workEnd = working_hours_only ? 18 : 24;

// Detección de conflictos
const hasConflict = busyEvents.some(event => {
    const eventStart = new Date(event.start.dateTime || event.start.date);
    const eventEnd = new Date(event.end.dateTime || event.end.date);
    return (slotStart < eventEnd && slotEnd > eventStart);
});
```

**Características del algoritmo:**
- **Exclusión de fines de semana**: Configurable
- **Horario laboral**: 9am-6pm por defecto
- **Duración mínima**: Especificable en minutos
- **Detección de conflictos**: Comparación precisa de intervalos
- **Resultados limitados**: Máximo 20 slots para performance

### Sistema de Email (`google_workspace_server.js:970-1025`)

#### send_calendar_reminder_email

**Envío de recordatorios personalizados:**

```javascript
// Construcción del email
let emailBody = `Estimado usuario,\n\n${message}\n\n`;
if (event_title) emailBody += `📅 Evento: ${event_title}\n`;
if (event_datetime) emailBody += `🕐 Fecha/Hora: ${event_datetime}\n`;
emailBody += `\nEste es un recordatorio automático enviado desde tu asistente Aura.\n\n`;

// Codificación Base64 para Gmail API
const encodedEmail = Buffer.from(email).toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
```

### Análisis de Productividad (`google_workspace_server.js:1027-1182`)

#### get_calendar_summary

**Sistema completo de estadísticas y análisis:**

```javascript
const stats = {
    totalEvents: events.length,
    meetings: 0,                    // Eventos con attendees
    allDayEvents: 0,               // Eventos de día completo
    eventsWithLocation: 0,         // Con ubicación física
    eventsWithAttendees: 0,        // Con participantes
    totalDuration: 0,              // Tiempo total en minutos
    byDay: {},                     // Distribución por día
    upcomingEvents: []             // Próximos 7 días
};
```

**Análisis de insights:**
- **Días más ocupados**: Ranking por número de eventos
- **Ratio de reuniones**: Porcentaje de eventos colaborativos
- **Duración promedio**: Cálculo de tiempo medio por evento
- **Distribución temporal**: Análisis por días de la semana

## Sequential Thinking Server (Oficial de Anthropic)

### Integración y Configuración

**Servidor oficial**: `@modelcontextprotocol/server-sequential-thinking`  
**Instalación**: Via NPX para siempre obtener la versión más reciente  
**Configuración**: Sin variables de entorno requeridas

```javascript
// En config.py
config["sequential-thinking"] = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
}
```

### Funcionalidad y Uso

**Herramienta principal**: `sequentialthinking`

**Parámetros clave:**
- `thought`: Contenido del pensamiento actual
- `thoughtNumber`: Número secuencial del pensamiento
- `totalThoughts`: Total estimado de pensamientos necesarios
- `nextThoughtNeeded`: Boolean para continuar razonamiento

### Integración con Sistema TTS

**Interceptación en backend** (`aura_websocket_server.py:913-947`):

```python
async def _handle_sequential_thinking(self, func_call, client_id: str):
    # Extraer información del pensamiento
    thought_content = args.get('thought', '')
    thought_number = args.get('thoughtNumber', 0)
    total_thoughts = args.get('totalThoughts', 0)
    
    # Enviar al frontend para visualización
    await self.send_to_client(client_id, {
        'type': 'reasoning_thought',
        'thought': thought_content,
        'thought_number': int(thought_number),
        'total_thoughts': int(total_thoughts)
    })
    
    # Añadir al buffer TTS con velocidad aumentada
    await self.tts_buffer.add_item(TTSQueueItem(
        content=thought_content,
        item_type='thought',
        speed_multiplier=1.8  # 80% más rápido
    ))
```

## Patrones Comunes de Implementación

### 1. Manejo de Input/Output StdIO

```javascript
// Patrón estándar para todos los servidores
process.stdin.setEncoding('utf8');
let buffer = '';

process.stdin.on('data', async (chunk) => {
    buffer += chunk;
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    
    for (const line of lines) {
        if (!line.trim()) continue;
        
        try {
            const request = JSON.parse(line);
            const response = await server.handleRequest(request);
            console.log(JSON.stringify(response));
        } catch (error) {
            console.log(JSON.stringify({ 
                jsonrpc: "2.0", 
                id: null, 
                error: { code: -1, message: error.message } 
            }));
        }
    }
});
```

### 2. Schema de Herramientas Consistente

```javascript
const tool = {
    name: "tool_name",
    description: "CUÁNDO USAR: ... CÓMO USAR: ...", // Descripción detallada
    inputSchema: {
        type: "object",
        properties: {
            param1: {
                type: "string",
                description: "Descripción del parámetro",
                default: "valor_default" // Si aplica
            }
        },
        required: ["param1"] // Parámetros obligatorios
    }
}
```

### 3. Manejo de Errores Robusto

```javascript
try {
    // Operación principal
    const result = await externalAPI.call(params);
    return { content: [{ type: "text", text: formatResult(result) }] };
} catch (error) {
    throw new Error(`Error específico en operación: ${error.message}`);
}
```

### 4. Formateo de Salida Consistente

**Todos los servidores usan formato unificado:**
- **Emojis descriptivos**: 🔍 📅 📄 ✅ ❌
- **Markdown estructurado**: Headers, listas, emphasis
- **Información contextual**: IDs, timestamps, metadatos
- **Límites de texto**: Previews de ~200 caracteres máximo

## Configuración y Deployment

### Variables de Entorno por Servidor

```bash
# SerpAPI
SERPAPI_API_KEY="tu_serpapi_key"

# Obsidian Memory  
OBSIDIAN_VAULT_PATH="/ruta/completa/al/vault"

# Google Workspace
GOOGLE_CREDENTIALS_PATH="./credentials.json"
GOOGLE_TOKEN_PATH="./token.json"

# Sequential Thinking - Sin variables requeridas
```

### Proceso de Inicialización

1. **Validación de dependencias**: Verificar archivos y variables requeridas
2. **Configuración de clientes**: OAuth, API keys, paths
3. **Inicialización de herramientas**: Definir schemas y handlers
4. **Setup de comunicación**: StdIO listeners y error handlers
5. **Health checks**: Verificación de conectividad con servicios externos

### Consideraciones de Seguridad

- **API Keys seguras**: Solo via variables de entorno
- **Scopes mínimos**: OAuth con permisos limitados necesarios
- **Validación de input**: Sanitización de parámetros de usuario
- **Error sanitization**: No exposición de información sensible en errores
- **Rate limiting**: Timeouts y límites de requests configurados

## Extensibilidad

### Agregar Nuevo Servidor MCP

1. **Crear archivo servidor**: `nuevo_servidor.js` en carpeta `mcp/`
2. **Implementar clase base**: Con métodos estándar MCP
3. **Definir herramientas**: Array con schemas completos
4. **Configurar en config.py**: Agregar entrada con command y args
5. **Testing**: Verificar integración con cliente Gemini

### Mejores Prácticas

- **Documentación inline**: Descripciones detalladas en schemas
- **Manejo de casos edge**: Validaciones robustas
- **Performance optimization**: Timeouts y limits apropiados
- **Logging estructurado**: Para debugging y monitoreo
- **Backward compatibility**: Versioning de schemas y APIs