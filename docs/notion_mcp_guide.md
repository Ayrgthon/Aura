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
"Busca todos los proyectos con estado 'en progreso'"
"Actualiza el progreso del proyecto Aura al 75%"
"Crea una nueva tarea en el proyecto de desarrollo"
```

### Gestión de Conocimiento
```
"Busca todas las notas sobre Python"
"Crea una nueva página para documentar el nuevo proceso"
"Añade una nota sobre la reunión de hoy"
```

### Gestión de Tareas
```
"Muéstrame todas las tareas pendientes"
"Cambia el estado de la tarea 'actualizar documentación' a completado"
"Crea una nueva tarea para mañana"
```

### Investigación
```
"Busca páginas sobre inteligencia artificial"
"Crea una base de datos para organizar mis investigaciones"
"Añade una nueva entrada a mi lista de lectura"
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

## 💡 Consejos de Uso

1. **Usa nombres descriptivos**: Al crear páginas y bases de datos, usa nombres claros que faciliten la búsqueda.

2. **Organiza con propiedades**: Usa propiedades en las bases de datos para facilitar el filtrado y la organización.

3. **Comparte selectivamente**: Solo comparte las páginas y bases de datos que realmente necesites que Aura pueda acceder.

4. **Usa etiquetas**: Las etiquetas facilitan la búsqueda y organización del contenido.

5. **Backup regular**: Aunque Aura es confiable, es buena práctica hacer backups regulares de tu contenido importante.

## 🔗 Enlaces Útiles

- [Notion API Documentation](https://developers.notion.com/)
- [Notion Integrations](https://www.notion.so/my-integrations)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Aura Project](https://github.com/your-repo/aura)

---

**Desarrollado con ❤️ para Aura** 