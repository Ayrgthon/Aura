# 🚀 Guía de Instalación - Aura_Ollama

Esta guía te ayudará a instalar y configurar **Aura_Ollama** desde cero en tu sistema Linux.

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.8+** 
- **Git**
- **Node.js 18+** y **npm** (para MCPs)
- **Micrófono y altavoces** (opcional, para funcionalidades de voz)

---

## 🔧 Instalación Paso a Paso

### **Paso 1: Clonar el Repositorio**

```bash
git clone <URL_DEL_REPOSITORIO>
cd Aura_Ollama
```

### **Paso 2: Crear Entorno Virtual de Python**

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Verificar que estás en el entorno virtual (debe aparecer (venv) en el prompt)
```

### **Paso 3: Instalar Dependencias de Python**

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias del proyecto
pip install -r requirements.txt
```

### **Paso 4: Verificar Node.js (para MCPs)**

```bash
# Verificar instalación de Node.js
node --version
npm --version

# Si no tienes Node.js instalado:
# Ubuntu/Debian: sudo apt install nodejs npm
# Arch Linux: sudo pacman -S nodejs npm
```

### **Paso 5: Configurar Modelos de IA**

Elige una de estas opciones según tus preferencias:

#### **Opción A: Google Gemini (Recomendado)**
- ✅ **Ventajas**: Más potente, mejor para MCPs, no requiere instalación local
- ❌ **Desventajas**: Requiere conexión a internet

El proyecto ya incluye una API key demo. Para uso intensivo, obtén tu propia clave en:
👉 [Google AI Studio](https://aistudio.google.com/app/apikey)

#### **Opción B: Ollama (Local)**
- ✅ **Ventajas**: Privacidad total, funciona offline
- ❌ **Desventajas**: Requiere recursos del sistema, instalación adicional

```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar servicio Ollama
ollama serve &

# Descargar modelo recomendado (en otra terminal)
ollama pull qwen3:1.7b
```

### **Paso 6: Configurar Audio (Opcional)**

Si quieres usar las funcionalidades de voz:

```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev python3-pyaudio

# Arch Linux
sudo pacman -S portaudio

# Verificar que tu micrófono funciona
arecord -d 3 test.wav && aplay test.wav && rm test.wav
```

---

## 🎯 Primer Uso

### **Ejecutar Aura**

```bash
# Asegúrate de estar en el entorno virtual
source venv/bin/activate

# Ejecutar la aplicación
python main.py
```

### **Configuración Inicial**

Al ejecutar por primera vez, verás este menú:

```
🤖 Configuración de Modelo LLM
==================================================
Modelos disponibles:
1. 🟢 Google Gemini (gemini-2.0-flash-exp)
2. 🦙 Ollama (qwen3:1.7b)
3. 🛠️  Personalizado
```

**Recomendación**: Selecciona **opción 1** (Gemini) para la mejor experiencia.

### **Configuración de Voz**

```
🎤 Configuración de Voz
==============================
¿Habilitar funcionalidades de voz? (s/n):
```

- **s** = Habilita reconocimiento y síntesis de voz
- **n** = Solo modo texto

### **Configuración de MCP**

```
🔧 Configuración de MCP (Model Context Protocol)
=======================================================
Opciones disponibles:
1. 📁 Solo Filesystem (operaciones con archivos)
2. 🔍 Solo Brave Search (búsquedas web)
3. 🌐 Filesystem + Brave Search (recomendado)
4. ❌ Sin MCP
```

**Recomendación**: Selecciona **opción 3** para máxima funcionalidad.

---

## 💬 Usando Aura

Una vez configurado, verás:

```
🗣️  Modo Interactivo Activado
===================================
Comandos disponibles:
  • 'salir' o 'exit' - Terminar
  • 'escuchar' - Entrada por voz (si está disponible)
  • 'limpiar' - Limpiar historial
--------------------------------------------------

👤 Tú: 
```

### **Ejemplos de Uso**

```bash
# Conversación básica
👤 Tú: Hola, ¿cómo estás?

# Búsquedas web (con Brave Search MCP)
👤 Tú: ¿Cuáles son las últimas noticias sobre IA?

# Operaciones con archivos (con Filesystem MCP)
👤 Tú: Lista los archivos Python en mi directorio home

# Entrada por voz (si está habilitada)
👤 Tú: escuchar
🎤 Escuchando... (habla ahora)
```

---

## 🔧 Solución de Problemas

### **Error: "ModuleNotFoundError"**

```bash
# Asegúrate de estar en el entorno virtual
source venv/bin/activate

# Reinstalar dependencias
pip install -r requirements.txt
```

### **Error: "Node.js not found" para MCPs**

```bash
# Verificar instalación
node --version

# Si no está instalado (Ubuntu/Debian):
sudo apt update && sudo apt install nodejs npm

# Si no está instalado (Arch Linux):
sudo pacman -S nodejs npm
```

### **Error: "Ollama connection failed"**

```bash
# Verificar que Ollama está ejecutándose
ollama serve

# En otra terminal, verificar que el modelo está descargado
ollama list

# Si no aparece qwen3:1.7b, descargarlo:
ollama pull qwen3:1.7b
```

### **Problemas de Audio**

```bash
# Verificar dispositivos de audio
aplay -l  # Listar dispositivos de salida
arecord -l  # Listar dispositivos de entrada

# Probar grabación
arecord -d 3 test.wav && aplay test.wav
```

### **MCP no se conecta**

```bash
# Verificar que Node.js funciona
npx --version

# Probar MCP manualmente
npx -y @modelcontextprotocol/server-filesystem /tmp
```

---

## 🚀 Optimización de Rendimiento

### **Para mejor rendimiento con Gemini:**
- Usa una conexión a internet estable
- La API key demo tiene límites, considera obtener tu propia clave

### **Para mejor rendimiento con Ollama:**
- Asegúrate de tener al menos 4GB RAM disponible
- Usa SSDs para mejor velocidad de carga del modelo
- Considera modelos más grandes si tienes más RAM: `ollama pull qwen3:8b`

### **Para funcionalidades de voz:**
- Usa un micrófono externo para mejor calidad
- Ajusta el volumen del sistema apropiadamente
- En ambientes ruidosos, habla cerca del micrófono

---

## 📱 Comandos Útiles

```bash
# Activar entorno virtual (siempre antes de usar)
source venv/bin/activate

# Ejecutar Aura
python main.py

# Actualizar dependencias
pip install -r requirements.txt --upgrade

# Verificar versiones
python --version
node --version
ollama --version

# Desactivar entorno virtual
deactivate
```

---

## 🆘 Obtener Ayuda

Si tienes problemas:

1. **Revisa esta guía** completa
2. **Verifica los requisitos previos**
3. **Comprueba que el entorno virtual esté activo**
4. **Consulta la sección de solución de problemas**

---

## 🌟 ¡Listo para Usar!

Con esta configuración tendrás:

- ✅ **Asistente de IA** con Gemini o Ollama
- ✅ **Búsquedas web en tiempo real** con Brave Search
- ✅ **Operaciones con archivos** locales
- ✅ **Reconocimiento y síntesis de voz**
- ✅ **Chat interactivo** con streaming de respuestas

**¡Disfruta usando Aura! 🚀** 