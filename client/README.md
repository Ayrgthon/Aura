# Aura Client - Nueva Implementación Simple

## Descripción

Cliente **completamente nuevo** y **simplificado** para Aura que utiliza:
- **Gemini API** con soporte nativo para múltiples function calls
- **Múltiples servidores MCP** conectados simultáneamente
- **Arquitectura directa** sin complejidad innecesaria

## Arquitectura

```
client/
├── mcp_client.py      # Cliente MCP limpio para múltiples servidores
├── gemini_client.py   # Cliente Gemini con soporte para function calls
├── config.py          # Configuración de servidores MCP
├── main.py           # Aplicación principal
└── README.md         # Esta documentación
```

## Características Clave

### ✅ **Simplicidad**
- Código limpio sin complejidades innecesarias
- Lógica directa: prompt → function calls → respuesta
- Sin sistemas complejos de "planes" o estados confusos

### ✅ **Gemini Nativo**
- Uso directo de la API de Gemini para múltiples function calls
- Gemini decide automáticamente qué herramientas usar y cuándo
- Sin lógica de continuación artificial

### ✅ **MCPs Múltiples**
- Conexión simultánea a todos los servidores MCP disponibles
- Sequential Thinking MCP integrado
- Schema cleaning automático para compatibilidad

### ✅ **Manejo Robusto**
- Manejo correcto de errores de conexión
- Cleanup automático de recursos
- Debug logging opcional

## Servidores MCP Soportados

1. **Serpapi** - Búsqueda web con Google
2. **Obsidian Memory** - Gestión de notas
3. **Personal Assistant** - Tareas diarias
4. **Sequential Thinking** - Razonamiento estructurado (Anthropic)
5. **Brave Search** - Búsqueda alternativa

## Instalación y Uso

```bash
# Navegar al directorio
cd /home/ary/Documents/Aura/client

# Ejecutar el cliente
python main.py
```

## Variables de Entorno Requeridas

```bash
GOOGLE_API_KEY=tu_clave_gemini
SERPAPI_API_KEY=tu_clave_serpapi  # (opcional)
OBSIDIAN_VAULT_PATH=/path/to/vault  # (opcional)
DAILY_PATH=/path/to/daily  # (opcional)
```

## Comandos Especiales

- `quit`, `exit`, `salir` - Salir del chat
- `clear` - Limpiar historial
- `tools` - Mostrar herramientas disponibles

## Diferencias con la Implementación Anterior

### ❌ **Anterior (Complejo)**
- Lógica de "planes" abstractos
- Sistema de tracking manual de herramientas
- Múltiples prompts de continuación
- Estados complejos y confusos
- Loops infinitos y errores de contexto

### ✅ **Nuevo (Simple)**
- Gemini maneja automáticamente múltiples function calls
- Sin lógica de tracking manual
- Respuesta directa basada en resultados
- Sin estados complejos
- Funcionamiento confiable y predecible

## Ejemplo de Uso

```
👤 Tú: Investiga las últimas noticias sobre Spiderman. Luego, investiga las últimas noticias sobre Superman. Finalmente, en mis notas, dentro de una carpeta llamada "Héroes", guarda la información encontrada de cada una de las búsquedas.

🤖 Aura: [Ejecuta automáticamente]:
        1. google_news_search(query="Spiderman")
        2. google_news_search(query="Superman") 
        3. create_note(path="Héroes/Spiderman.md", content="...")
        4. create_note(path="Héroes/Superman.md", content="...")
        
        [Responde con síntesis completa]
```

## Ventajas del Enfoque

1. **Confiabilidad**: Gemini maneja la coordinación de herramientas
2. **Simplicidad**: Menos código = menos bugs
3. **Mantenibilidad**: Fácil de entender y modificar
4. **Escalabilidad**: Fácil agregar nuevos MCPs
5. **Performance**: Sin overhead de lógica compleja