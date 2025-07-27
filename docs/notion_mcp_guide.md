# 📝 Guía del Notion MCP Server para Aura

## 🚀 Introducción

El Notion MCP Server permite a Aura interactuar directamente con tu workspace de Notion, permitiendo crear, leer, actualizar y gestionar páginas, bases de datos y contenido de forma natural mediante comandos de voz o texto.

## ⚙️ Configuración

### 1. Obtener API Key de Notion

1. Ve a [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Haz clic en "New integration"
3. Completa la información:
   - **Name**: `Aura Assistant` (o el nombre que prefieras)
   - **Associated workspace**: Selecciona tu workspace
   - **Capabilities**: Marca todas las opciones (Read content, Update content, Insert content, etc.)
4. Haz clic en "Submit"
5. Copia el "Internal Integration Token"

### 2. Configurar en Aura

1. Abre el archivo `.env` en la raíz del proyecto
2. Añade tu API key:
   ```env
   NOTION_API_KEY=secret_your_integration_token_here
   ```

### 3. Compartir contenido con la integración

**Importante**: Para que Aura pueda acceder a tu contenido de Notion, debes compartir las páginas y bases de datos con tu integración:

1. Ve a cualquier página o base de datos en Notion
2. Haz clic en "Share" (botón superior derecho)
3. En "Add people, emails, groups, or integrations"
4. Busca el nombre de tu integración (ej: "Aura Assistant")
5. Selecciónala y haz clic en "Invite"

## 🛠️ Funciones Disponibles

### Búsqueda y Lectura

#### `search_pages`
Busca páginas en tu workspace de Notion.

**Ejemplos de uso:**
- "Busca páginas sobre inteligencia artificial"
- "Encuentra todas las páginas con la etiqueta 'proyecto'"
- "Busca notas sobre Python"

#### `get_page`
Obtiene el contenido completo de una página específica.

**Ejemplos de uso:**
- "Muéstrame la página del proyecto Aura"
- "Lee la página de notas de la reunión"
- "Obtén el contenido de mi lista de tareas"

#### `get_database`
Obtiene la estructura y entradas de una base de datos.

**Ejemplos de uso:**
- "Muéstrame mi base de datos de proyectos"
- "Obtén todas las entradas de mi lista de lectura"
- "Lee mi base de datos de contactos"

#### `query_database`
Consulta entradas específicas en una base de datos con filtros.

**Ejemplos de uso:**
- "Busca tareas pendientes en mi base de datos"
- "Encuentra proyectos con estado 'en progreso'"
- "Filtra contactos por empresa"

### Creación y Escritura

#### `create_page`
Crea nuevas páginas en bases de datos o como hijos de páginas existentes.

**Ejemplos de uso:**
- "Crea una nueva página en mi base de datos de proyectos"
- "Añade una nueva entrada a mi lista de lectura"
- "Crea una página de notas para la reunión de mañana"

#### `create_database`
Crea nuevas bases de datos.

**Ejemplos de uso:**
- "Crea una base de datos para gestionar mis tareas"
- "Haz una base de datos para mi colección de libros"
- "Crea una base de datos de contactos"

#### `append_block_children`
Añade nuevos bloques de contenido a una página existente.

**Ejemplos de uso:**
- "Añade una nueva tarea a mi lista"
- "Agrega una nota a la página del proyecto"
- "Incluye un enlace en la página de recursos"

### Actualización y Modificación

#### `update_page`
Actualiza las propiedades y contenido de una página.

**Ejemplos de uso:**
- "Cambia el estado del proyecto a 'completado'"
- "Actualiza la fecha de vencimiento de la tarea"
- "Modifica el título de la página"

#### `update_block`
Actualiza el contenido de un bloque específico.

**Ejemplos de uso:**
- "Corrige el texto del primer párrafo"
- "Actualiza la descripción del proyecto"
- "Modifica la lista de tareas"

### Eliminación

#### `delete_block`
Elimina bloques específicos de una página.

**Ejemplos de uso:**
- "Elimina la tarea completada"
- "Borra la nota obsoleta"
- "Quita el enlace roto"

## 🎯 Casos de Uso Comunes

### Gestión de Proyectos
```
"revisa la base de datos quest"
"crea una página llamada 'Nuevo Proyecto'"
"creame otra página con fecha 'July 30, 2025' y descripción 'Proyecto de desarrollo'"
```

### Gestión de Tareas
```
"revisa la base de datos quest"
"crea una página llamada 'Nueva Tarea'"
"creame otra página con skill 'Puntos Arthur Morgan' y arcos 'Nuevo inicio'"
```

### Investigación
```
"busca páginas de 'Puntos de Programación'"
"crea una página llamada 'Investigación IA'"
"creame otra página con descripción 'Notas sobre machine learning'"
```

## 🔧 Configuraciones Recomendadas

### Para Productividad (Opción 10)
- **Notion + Brave Search**: Perfecto para investigación y gestión de conocimiento
- Permite buscar información web y organizarla en Notion

### Para Desarrollo (Opción 11)
- **Todos los MCPs**: Máxima funcionalidad
- Incluye Notion para documentación y gestión de proyectos

### Solo Notion (Opción 5)
- **Solo Notion**: Enfoque en gestión de workspace
- Ideal para usuarios que principalmente usan Notion

## 🚨 Solución de Problemas

### Error: "No se pudo configurar MCP"
- Verifica que la API key esté correctamente configurada en `.env`
- Asegúrate de que la integración tenga los permisos necesarios

### Error: "No se encontró la página"
- Verifica que hayas compartido la página con tu integración
- Comprueba que el ID de la página sea correcto

### Error: "No tienes permisos"
- Asegúrate de que la integración tenga acceso a la página/base de datos
- Verifica que la integración tenga los permisos de escritura si intentas crear/modificar

### La integración no aparece en la lista
- Verifica que hayas creado la integración correctamente
- Asegúrate de que esté asociada al workspace correcto

### ⚠️ Problema Crítico: Páginas creadas en ubicación incorrecta
**Síntoma**: Las páginas se crean en la vista "arcos y misiones" en lugar de la base de datos "quest"

**Causa**: El modelo está usando el ID de la página padre en lugar del ID de la base de datos específica

**Solución**: 
- El modelo debe buscar específicamente la base de datos 'quest' con filtro `object='database'`
- Usar `database_id` NO `page_id` en la estructura de creación
- Estructura correcta: `parent: {database_id: 'ID'}, properties: {Name: {title: [{text: {content: 'título'}}]}}`

**Comandos de verificación**:
- "revisa la base de datos quest" → Debe mostrar el ID de la base de datos
- "crea una página llamada [título]" → Debe crear en la base de datos, no en la vista padre

**Estructura API Correcta**:
```json
{
  "parent": {
    "database_id": "1f434b11-5002-8130-94c4-e44a770d8c9e"
  },
  "properties": {
    "Name": {
      "title": [
        {
          "text": {
            "content": "Título de la página"
          }
        }
      ]
    }
  }
}
```

**Errores Comunes a Evitar**:
- ❌ `"type": "title"` → ✅ `"Name": {title: [...]}`
- ❌ `"page_id"` → ✅ `"database_id"`
- ❌ `"properties": {"type": "title", "title": [...]}` → ✅ `"properties": {"Name": {title: [...]}}`

### ⚠️ Problema: Modelo no responde (Flash 2.0/2.5)
**Síntoma**: El modelo se queda en silencio sin dar respuesta

**Causa**: Protocolo demasiado complejo para modelos más simples

**Solución**: 
- Protocolo simplificado para compatibilidad universal
- Instrucciones claras para siempre responder
- Proceso de creación en 2 pasos simples

### ⚠️ Problema: Error en API (modelos específicos)
**Síntoma**: Error en la llamada a la API de Notion

**Causa**: Llamadas incorrectas a la API

**Solución**: 
- Proceso simplificado de búsqueda y creación
- Manejo de errores mejorado
- Respuesta siempre garantizada

## 💡 Consejos de Uso

1. **Usa nombres descriptivos**: Al crear páginas y bases de datos, usa nombres claros que faciliten la búsqueda.

2. **Organiza con propiedades**: Usa propiedades en las bases de datos para facilitar el filtrado y la organización.

3. **Comparte selectivamente**: Solo comparte las páginas y bases de datos que realmente necesites que Aura pueda acceder.

4. **Usa etiquetas**: Las etiquetas facilitan la búsqueda y organización del contenido.

5. **Backup regular**: Aunque Aura es confiable, es buena práctica hacer backups regulares de tu contenido importante.

## 🤖 Compatibilidad de Modelos

### **Modelos Recomendados:**
- **Gemini 2.5 Pro**: Funciona perfectamente con todas las funcionalidades
- **Gemini 2.0 Flash**: Funciona bien con el protocolo directo
- **Ollama (qwen3:1.7b)**: Compatible con instrucciones básicas

### **Nuevo Protocolo Directo:**
El protocolo ha sido rediseñado con enfoque positivo:
- **4 pasos claros** y secuenciales
- **Instrucciones directas** sin negaciones
- **Proceso automático** sin confirmaciones
- **Estructura detallada** de properties

### **Proceso Estricto de Creación:**
1. **PASO 1**: Buscar la base de datos con `API-post-search`
2. **PASO 2**: Obtener `database_id` y revisar propiedades con `API-post-database-query`
3. **PASO 3**: Crear la página con `API-post-page`
4. **PASO 4**: Confirmar creación exitosa

### **Límites Estrictos:**
- **SOLO 4 pasos** en orden
- **NUNCA pasos extra**
- **NUNCA buscar otras bases de datos**
- **NUNCA comillas extra en nombres**

### **Optimización para Flash:**
- **Protocolo directo** sin instrucciones negativas
- **4 pasos secuenciales** fáciles de seguir
- **Estructura detallada** de properties
- **Debug activado** para monitorear progreso

### **Problema Específico de Flash:**
- **Síntoma**: Silencio total o protocolo ignorado
- **Causa**: Instrucciones negativas abruman al modelo
- **Solución**: Protocolo directo con pasos positivos
- **Prevención**: 4 pasos claros y secuenciales

### **Error Específico de Flash - page_id vs database_id:**
- **Síntoma**: Error 404 "Could not find page with ID"
- **Causa**: Flash usa `page_id` en lugar de `database_id`
- **Solución**: "IMPORTANTE: SIEMPRE usar database_id en parent, NUNCA page_id"
- **Prevención**: Enfatizar database_id en el protocolo

### **Problema de Alucinación (2.5 Pro y Flash):**
- **Síntoma**: Llamadas infinitas a API-post-search
- **Causa**: Modelo no entiende límites del protocolo
- **Solución**: Protocolo estricto con "SOLO 4 pasos"
- **Prevención**: "NUNCA hagas pasos extra"

### **Proceso de Creación Paso a Paso:**
1. **PASO 1**: Buscar la base de datos con `API-post-search`
2. **PASO 2**: Obtener el `database_id` del resultado
3. **PASO 3**: Revisar propiedades con `API-post-database-query`
4. **PASO 4**: Crear la página con `API-post-page`

### **Validación de Ejecución:**
- **SIEMPRE** ejecutar los 4 pasos en orden
- **SIEMPRE** responder después de cada paso
- **Verificar** que el debug muestre todas las llamadas
- **Confirmar** que el resultado sea exitoso

### **Automatización Completa:**
- **SIEMPRE** seguir el protocolo automáticamente
- **SIEMPRE** usar nombres exactos de propiedades
- **SIEMPRE** estructurar properties correctamente

### **Análisis de Errores Comunes:**
1. **Error 400 - "Couldn't find editable properties for these identifiers: type"**
   - **Causa**: Usar `"type": "title"` en lugar de `"Name"`
   - **Solución**: Siempre usar `"Name": {title: [...]}`

2. **Error 404 - "Could not find page with ID"**
   - **Causa**: Usar `page_id` en lugar de `database_id`
   - **Solución**: Siempre usar `database_id` para bases de datos

3. **Múltiples Intentos**
   - **Causa**: Flash no aprende del primer error
   - **Solución**: Instrucciones más específicas con NUNCA/SIEMPRE

4. **Página no creada (sin error)**
   - **Causa**: Modelo dice que creó pero no ejecuta API
   - **Solución**: SIEMPRE ejecutar API-post-page después de buscar

5. **Error 400 - "is not a property that exists"**
   - **Causa**: Usar comillas extra en nombres de propiedades (ej: `'Due date'`)
   - **Solución**: Usar nombres exactos sin comillas extra (`Due date`)

6. **Modelo pide ayuda manual**
   - **Causa**: Flash ignora el protocolo y pide confirmación
   - **Solución**: NUNCA pedir ayuda, SIEMPRE seguir protocolo automáticamente

7. **Error 404 - "Could not find page with ID" (Flash)**
   - **Causa**: Flash usa `page_id` en lugar de `database_id`
   - **Solución**: SIEMPRE usar `database_id` en parent
   - **Prevención**: "IMPORTANTE: SIEMPRE usar database_id en parent, NUNCA page_id"

## 🎯 Bases de Datos Quest y Arcos - Propiedades Específicas

Tienes acceso a dos bases de datos principales para gestionar tu sistema de tareas y eventos:

### **Estructura API Crítica:**
**IMPORTANTE**: Usar siempre `database_id` NO `page_id`

```json
{
  "parent": {
    "database_id": "ID_DE_LA_BASE_DE_DATOS"
  },
  "properties": {
    "Name": {
      "title": [
        {
          "text": {
            "content": "Título de la página"
          }
        }
      ]
    }
  }
}
```

### **Base de Datos "Quest" - Tareas Pendientes:**
- **Name**: Título de la tarea/misión
- **skill**: Categoría de habilidad (ej: "Puntos Arthur Morgan")
- **arcos**: Arco narrativo (ej: "Nuevo inicio")
- **Due date**: Fecha de vencimiento (formato: "July 28, 2025")
- **importancia**: Nivel de importancia (ej: "urgente")
- **Status**: Estado de la tarea
- **completed!**: Indicador de completado
- **Description**: Descripción detallada
- **Pistas**: Información adicional
- **personaje**: Personaje relacionado

### **Base de Datos "Arcos" - Eventos/Proyectos:**
- **Name**: Título del arco/evento
- **quest**: Referencia a tareas relacionadas
- **clear!**: Indicador de completado
- **personaje**: Personaje relacionado
- **skills**: Habilidades requeridas
- **Pistas**: Información adicional

### **Ejemplos de Uso:**
```
# Quest (por defecto)
"crea una página llamada 'Entrevista de trabajo' con fecha 'July 29, 2025'"
"crea en quest una página llamada 'Estudiar Python' con arcos 'Desarrollo Web'"

# Arcos
"crea en arcos una página llamada 'Examen Final'"
"crea en arcos una página llamada 'Entrevista Laboral' con skills 'Comunicación'"

# Consultas
"cuales son las propiedades de la base de datos quest"
"cuales son las propiedades de la base de datos arcos"
"revisa la base de datos quest"
"revisa la base de datos arcos"
```

### **Flujo de Trabajo Quest ↔ Arcos:**
1. **Crear Arco**: `"crea en arcos una página llamada 'Examen Final'"` → Define el evento/proyecto
2. **Crear Quest**: `"crea una página llamada 'Estudiar capítulo 1' con arcos 'Examen Final'"` → Tarea específica del arco
3. **Relación**: Las quests se vinculan a arcos mediante la propiedad `arcos`
4. **Organización**: Los arcos agrupan quests relacionadas

### **Comandos Avanzados:**
```
# Crear arco y quest relacionada
"crea en arcos una página llamada 'Proyecto Web'"
"crea una página llamada 'Diseñar interfaz' con arcos 'Proyecto Web'"

# Consultar relaciones
"busca páginas de arco 'Examen Final'" → Encuentra quests del arco
"revisa la base de datos arcos" → Ver todos los arcos activos
```

## 🔗 Enlaces Útiles

- [Notion API Documentation](https://developers.notion.com/)
- [Notion Integrations](https://www.notion.so/my-integrations)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Aura Project](https://github.com/your-repo/aura)

---

**Desarrollado con ❤️ para Aura** 