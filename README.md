# 🌟 Aura - Asistente de IA Universal con Voz

Aura es un asistente de inteligencia artificial avanzado que combina procesamiento de lenguaje natural, síntesis de voz, y capacidades extendidas a través del Model Context Protocol (MCP). Soporta múltiples modelos de IA incluyendo Google Gemini y Ollama.

## 🚀 Características Principales

- **🗣️ Interfaz de Voz**: Reconocimiento y síntesis de voz en español
- **🤖 Múltiples Modelos**: Soporte para Google Gemini y Ollama
- **🔧 Model Context Protocol (MCP)**: Integración con herramientas externas
- **🌐 Interfaz Web**: Frontend moderno con React y Vite
- **📊 Monitoreo del Sistema**: Visualización en tiempo real de estadísticas
- **🔄 WebSocket**: Comunicación en tiempo real entre frontend y backend

## 📋 Requisitos

- Python 3.8+
- Node.js 16+
- npm o yarn
- Arch Linux (recomendado) o cualquier distribución Linux

## 🛠️ Instalación

### 1. Clonar el repositorio

```bash
git clone <tu-repositorio>
cd Aura_Ollama
```

### 2. Configurar variables de entorno

```bash
cp env.template .env
```

Edita el archivo `.env` y configura tus API keys:

```env
# Google Gemini API
GOOGLE_API_KEY=tu_api_key_de_google

# Brave Search API  
BRAVE_API_KEY=tu_api_key_de_brave

# ElevenLabs API (para síntesis de voz premium)
ELEVENLABS_API_KEY=tu_api_key_de_elevenlabs

# Ruta del Vault de Obsidian (opcional)
OBSIDIAN_VAULT_PATH=/ruta/a/tu/vault
```

### 3. Instalar dependencias

#### Backend (Python)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Frontend (Node.js)
```bash
cd frontend
npm install
cd ..
```

#### Dependencias de MCP
```bash
npm install
```

### 4. Iniciar el proyecto

```bash
./start.sh
```

El script iniciará automáticamente:
- API de estadísticas del sistema (puerto 8000)
- Servidor WebSocket (puerto 8765)
- Frontend de React (puerto 5173)

## 🎮 Uso

### Interfaz Web

1. Abre tu navegador en `http://localhost:5173`
2. Haz clic en el botón del micrófono para hablar
3. El asistente procesará tu solicitud y responderá por voz

### Interfaz de Terminal

También puedes ejecutar Aura directamente desde la terminal:

```bash
cd src
python main.py
```

## 🔌 Model Context Protocol (MCP)

Aura integra varios servidores MCP que extienden sus capacidades:

### 📁 Filesystem MCP
Permite a Aura acceder y manipular archivos en directorios específicos del sistema.

**Funciones disponibles:**
- `list_directory`: Lista el contenido de un directorio
- `read_file`: Lee el contenido de un archivo
- `write_file`: Escribe o modifica archivos
- `create_directory`: Crea nuevos directorios
- `delete_file`: Elimina archivos
- `move_file`: Mueve o renombra archivos

**Configuración:**
Los directorios permitidos se configuran automáticamente basándose en los directorios existentes del sistema (Documentos, Descargas, etc.).

### 🔍 Brave Search MCP
Permite realizar búsquedas web en tiempo real usando el motor de búsqueda Brave.

**Funciones disponibles:**
- `brave_search`: Busca información actualizada en la web
- `brave_local_search`: Búsqueda de negocios y lugares locales
- `brave_news_search`: Búsqueda específica de noticias

**Uso típico:**
- "Busca las últimas noticias sobre IA"
- "¿Cuál es el clima actual en Madrid?"
- "Encuentra información sobre Python 3.12"

### 🗃️ Obsidian Memory MCP
Integración con Obsidian para crear un sistema de memoria persistente.

**Funciones disponibles:**
- `search_notes`: Busca notas por contenido, etiquetas o wikilinks
- `read_note`: Lee el contenido completo de una nota
- `create_note`: Crea nuevas notas en el vault
- `update_note`: Actualiza notas existentes
- `list_vault_structure`: Lista la estructura del vault
- `get_note_metadata`: Obtiene metadatos de las notas

**Configuración:**
Configura la ruta de tu vault de Obsidian en el archivo `.env`:
```env
OBSIDIAN_VAULT_PATH=/home/usuario/Documentos/Mi Vault
```

### 🌐 Playwright MCP
Automatización web avanzada para navegación, scraping y búsquedas en sitios web.

**Funciones disponibles:**
- `goto`: Navegar a URLs específicas
- `click`: Hacer clic en elementos de la página
- `fill`: Llenar formularios de búsqueda
- `textContent`: Extraer texto de elementos
- `screenshot`: Capturar pantallas
- `evaluate`: Ejecutar JavaScript personalizado
- `waitForSelector`: Esperar elementos específicos

**Uso típico para Ecommerce:**
- "Busca el precio del iPhone 15 en Amazon"
- "Compara precios de laptops en MercadoLibre"
- "Extrae información de productos de eBay"
- "Navega por catálogos de tiendas online"

**Configuración:**
Playwright se instala automáticamente con los navegadores necesarios. No requiere configuración adicional.

## 🎨 Arquitectura del Proyecto

```
Aura_Ollama/
├── src/                    # Código fuente principal
│   ├── main.py            # Punto de entrada principal
│   ├── client.py          # Cliente de IA (Gemini/Ollama)
│   ├── websocket_server.py # Servidor WebSocket
│   └── system_stats_api.py # API de estadísticas
├── voice/                  # Módulos de voz
│   ├── hear.py            # Reconocimiento de voz
│   ├── speak.py           # Síntesis de voz
│   └── vosk-model-es-0.42/ # Modelo de voz en español
├── mcp/                    # Servidores MCP
│   └── obsidian_memory_server.js
├── frontend/               # Aplicación React
│   ├── src/
│   ├── public/
│   └── package.json
├── logs/                   # Archivos de log
├── .env                    # Variables de entorno
├── requirements.txt        # Dependencias Python
├── package.json           # Dependencias Node.js
└── start.sh               # Script de inicio
```

## 🔧 Configuración Avanzada

### Cambiar el modelo de IA

Por defecto, Aura usa Google Gemini. Para cambiar a Ollama:

1. Instala Ollama: https://ollama.ai
2. Descarga un modelo: `ollama pull qwen2.5-coder:7b`
3. Al iniciar Aura, selecciona la opción de Ollama

### Agregar nuevos MCPs

Para agregar un nuevo servidor MCP:

1. Instala el servidor MCP:
```bash
npm install @modelcontextprotocol/server-ejemplo
```

2. Modifica `src/main.py` o `src/websocket_server.py` para agregar la configuración:
```python
"ejemplo": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-ejemplo"],
    "transport": "stdio"
}
```

3. El servidor estará disponible automáticamente en la próxima ejecución.

### Configuraciones MCP Recomendadas

**Para Ecommerce (Opción 8):**
- Filesystem + Brave Search + Playwright
- Ideal para búsquedas de precios y comparaciones

**Para Desarrollo (Opción 9):**
- Todos los MCPs (Filesystem + Brave Search + Obsidian Memory + Playwright)
- Máxima funcionalidad disponible

**Para Búsquedas Básicas (Opción 6):**
- Obsidian Memory + Brave Search
- Equilibrio entre funcionalidad y rendimiento

### Motores de síntesis de voz

Aura soporta múltiples motores TTS:

- **gTTS** (por defecto): Gratuito, requiere conexión a internet
- **ElevenLabs**: Alta calidad, requiere API key
- **edge-tts**: Gratuito, usa voces de Microsoft Edge

Para cambiar el motor, usa el comando en la interfaz web o modifica `voice/speak.py`.

## 🐛 Solución de Problemas

### El reconocimiento de voz no funciona
- Verifica que tengas un micrófono conectado
- Asegúrate de que el modelo Vosk esté en `voice/vosk-model-es-0.42/`
- Revisa los permisos del micrófono en tu sistema

### Error de conexión WebSocket
- Verifica que el puerto 8765 no esté en uso
- Revisa los logs en `logs/websocket.log`

### El frontend no carga
- Asegúrate de haber instalado las dependencias con `npm install`
- Verifica que el puerto 5173 esté libre
- Revisa los logs en `logs/frontend.log`

## 📝 Logs

Los logs se guardan en la carpeta `logs/`:
- `backend_stats.log`: API de estadísticas
- `websocket.log`: Servidor WebSocket
- `frontend.log`: Aplicación React

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- Google Gemini y Ollama por los modelos de IA
- Vosk por el reconocimiento de voz offline
- Model Context Protocol por la arquitectura extensible
- La comunidad de código abierto

---

**Desarrollado con ❤️ por Ary** 