# 🗃️ Obsidian Memory MCP - Memoria Centralizada para Aura

Este README documenta la integración del **Obsidian Memory MCP**, un servidor de Model Context Protocol que permite a Aura acceder y gestionar tu Baúl de Obsidian como una memoria centralizada a largo plazo.

## 🎯 Características

### 🔍 Búsqueda Avanzada
- **Búsqueda por contenido**: Encuentra notas que contengan texto específico
- **Búsqueda por nombre**: Busca notas por su título o nombre de archivo
- **Búsqueda por etiquetas**: Encuentra notas con etiquetas específicas (#tag)
- **Búsqueda por wikilinks**: Busca notas que contengan [[enlaces]] específicos
- **Búsqueda combinada**: Combina todos los tipos de búsqueda para resultados más precisos

### 📖 Gestión de Notas
- **Leer notas**: Lee el contenido completo de cualquier nota
- **Crear notas**: Crea nuevas notas con contenido y estructura automática
- **Actualizar notas**: Modifica notas existentes (agregar, anteponer, reemplazar)
- **Metadatos**: Obtiene información detallada sobre las notas (tamaño, fechas, etiquetas, etc.)

### 📁 Exploración del Vault
- **Estructura del vault**: Lista la organización completa de tu Baúl de Obsidian
- **Navegación inteligente**: Explora carpetas y subcarpetas de forma recursiva

## 🚀 Configuración

### 1. Requisitos
- **Node.js**: Para ejecutar el servidor MCP
- **Baúl de Obsidian**: Tu vault debe estar en `/home/ary/Documentos/Ary Vault`
- **Archivos .md**: El sistema solo lee archivos Markdown

### 2. Configuración Automática
Cuando ejecutes `python main.py`, verás estas opciones:

```
🔧 Configuración de MCP (Model Context Protocol)
=======================================================
Opciones disponibles:
1. 📁 Solo Filesystem (operaciones con archivos)
2. 🔍 Solo Brave Search (búsquedas web)
3. 🗃️ Solo Obsidian Memory (memoria centralizada)
4. 🌐 Filesystem + Brave Search
5. 🧠 Obsidian Memory + Brave Search (recomendado)
6. 🔧 Filesystem + Obsidian Memory + Brave Search (completo)
7. ❌ Sin MCP

Selecciona configuración MCP (1-7):
```

**Recomendación**: Usa la opción **5** (Obsidian Memory + Brave Search) para tener memoria centralizada y búsquedas web.

## 💬 Ejemplos de Uso

### Búsqueda por Contenido
```
👤 Tú: Busca información sobre RAG en mi vault
🤖 Aura: [Busca en tu vault y encuentra notas relacionadas con RAG]
```

### Búsqueda por Etiquetas
```
👤 Tú: Encuentra notas con la etiqueta #langchain
🤖 Aura: [Busca todas las notas que contengan #langchain]
```

### Búsqueda por Wikilinks
```
👤 Tú: Busca notas que mencionen [[Agentes de IA]]
🤖 Aura: [Encuentra notas con ese wikilink]
```

### Leer Notas Específicas
```
👤 Tú: Lee mi nota sobre MCPs
🤖 Aura: [Lee y muestra el contenido de Proyectos/Aura/MCPS.md]
```

### Crear Nuevas Notas
```
👤 Tú: Crea una nota llamada "Ideas para Aura" con mis ideas de mejoras
🤖 Aura: [Crea una nueva nota con el contenido especificado]
```

### Explorar Estructura
```
👤 Tú: Muéstrame la estructura de mi vault
🤖 Aura: [Lista toda la organización de tu Baúl de Obsidian]
```

## 🔧 Herramientas Disponibles

### 1. `search_notes`
Busca notas en el vault por diferentes criterios.

**Parámetros:**
- `query`: Término de búsqueda
- `search_type`: Tipo de búsqueda (content, filename, tags, wikilinks, all)
- `max_results`: Número máximo de resultados (por defecto 10)

### 2. `read_note`
Lee el contenido completo de una nota específica.

**Parámetros:**
- `note_path`: Ruta relativa de la nota (ej: "Proyectos/Aura/MCPS.md")

### 3. `create_note`
Crea una nueva nota en el vault.

**Parámetros:**
- `note_path`: Ruta donde crear la nota
- `content`: Contenido de la nota en Markdown
- `overwrite`: Si sobrescribir si ya existe (por defecto false)

### 4. `update_note`
Actualiza una nota existente.

**Parámetros:**
- `note_path`: Ruta de la nota a actualizar
- `content`: Nuevo contenido
- `mode`: Modo de actualización (append, prepend, replace)

### 5. `list_vault_structure`
Lista la estructura completa del vault.

**Parámetros:**
- `max_depth`: Profundidad máxima de listado (por defecto 10)

### 6. `get_note_metadata`
Obtiene metadatos detallados de una nota.

**Parámetros:**
- `note_path`: Ruta de la nota

## 🎨 Casos de Uso Avanzados

### Investigación y Consulta
```
👤 Tú: ¿Qué información tengo sobre embeddings en mi vault?
🤖 Aura: [Busca en todas las notas y resume la información encontrada]
```

### Gestión de Conocimiento
```
👤 Tú: Crea un resumen de mis notas sobre proyectos de IA
🤖 Aura: [Busca notas relacionadas, las analiza y crea un resumen]
```

### Conexión de Ideas
```
👤 Tú: ¿Qué notas están relacionadas con [[LangChain]]?
🤖 Aura: [Encuentra todas las notas que mencionan LangChain]
```

## 📊 Algoritmo de Relevancia

El sistema usa un algoritmo de puntuación para ordenar los resultados:

- **Nombre de archivo**: +10 puntos por coincidencia
- **Contenido**: +2 puntos por cada coincidencia
- **Etiquetas**: +5 puntos por cada etiqueta coincidente
- **Wikilinks**: +3 puntos por cada wikilink coincidente

Los resultados se ordenan por relevancia descendente.

## 🔍 Vista Previa de Resultados

Para cada resultado de búsqueda, el sistema muestra:
- **Nombre del archivo**
- **Ruta relativa** en el vault
- **Puntuación de relevancia**
- **Tipos de coincidencias** encontradas
- **Vista previa** del contenido relevante

## 🛠️ Solución de Problemas

### Error: "El vault de Obsidian no existe"
**Solución**: Verifica que tu vault esté en `/home/ary/Documentos/Ary Vault`

### Error: "El servidor MCP no existe"
**Solución**: Asegúrate de que `obsidian_memory_server.js` esté en el directorio del proyecto

### Error: "Node.js no encontrado"
**Solución**: Instala Node.js:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install nodejs npm

# Arch Linux
sudo pacman -S nodejs npm
```

### Sin resultados en búsquedas
**Posibles causas**:
- El término de búsqueda no existe en las notas
- Las notas no están en formato .md
- Permisos de lectura en el vault

## 📈 Rendimiento

- **Búsqueda**: Optimizada para vaults grandes
- **Caché**: No usa caché, siempre datos actuales
- **Límites**: Configurable (por defecto 10 resultados)
- **Recursión**: Búsqueda recursiva en subcarpetas

## 🔐 Seguridad

- **Acceso limitado**: Solo al vault especificado
- **Sin escritura externa**: No puede escribir fuera del vault
- **Validación**: Rutas validadas para prevenir ataques
- **Permisos**: Respeta los permisos del sistema de archivos

## 📄 Logs y Depuración

Los logs del servidor MCP aparecen en stderr:
```
🗃️ Obsidian Memory MCP Server iniciado para vault: /home/ary/Documentos/Ary Vault
```

Para depurar, puedes ejecutar el servidor manualmente:
```bash
node obsidian_memory_server.js
```

## 🚀 Mejoras Futuras

Posibles extensiones del sistema:
- **RAG con embeddings**: Búsqueda semántica avanzada
- **Análisis de grafos**: Conexiones entre notas
- **Búsqueda temporal**: Filtros por fecha
- **Exportación**: Generar reportes desde el vault
- **Sincronización**: Notificaciones de cambios

---

**¡Disfruta usando la memoria centralizada de Aura con tu Baúl de Obsidian! 🌟** 