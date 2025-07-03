#!/bin/bash

echo "🚀 Iniciando Aura Web Interface"
echo "================================"

# Verificar directorio
if [ ! -d "stellar-voice-display" ]; then
    echo "❌ Error: No se encuentra el directorio stellar-voice-display"
    echo "   Ejecuta este script desde el directorio Aura_Ollama"
    exit 1
fi

# Verificar entorno virtual
if [ ! -d "venv" ]; then
    echo "❌ Error: No se encuentra el entorno virtual"
    echo "   Ejecuta: python -m venv venv"
    exit 1
fi

# Activar entorno virtual
echo "📦 Activando entorno virtual..."
source venv/bin/activate

# Verificar dependencias de Python
echo "🔍 Verificando dependencias de Python..."
if ! pip show websockets > /dev/null 2>&1; then
    echo "📦 Instalando dependencias de Python..."
    pip install -r requirements.txt
fi

# Verificar dependencias de Node.js y MCP
echo "🔍 Verificando dependencias de Node.js y MCP..."
if [ ! -d "node_modules/@modelcontextprotocol" ]; then
    echo "📦 Instalando dependencias de MCP..."
    npm install @modelcontextprotocol/server-filesystem @modelcontextprotocol/server-brave-search
fi

cd stellar-voice-display
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias de Node.js..."
    npm install
fi
cd ..

# Función para limpiar procesos al salir
cleanup() {
    echo ""
    echo "🛑 Deteniendo servicios..."
    kill $WEBSOCKET_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "👋 ¡Hasta luego!"
    exit 0
}

# Capturar Ctrl+C
trap cleanup INT

# Iniciar servidor WebSocket
echo "📡 Iniciando servidor WebSocket..."
python websocket_server_simple.py > websocket.log 2>&1 &
WEBSOCKET_PID=$!

# Esperar que el WebSocket inicie
sleep 3

# Verificar que el WebSocket esté funcionando
if ! pgrep -f "websocket_server_simple.py" > /dev/null; then
    echo "❌ Error: No se pudo iniciar el servidor WebSocket"
    exit 1
fi

# Iniciar frontend
echo "🌐 Iniciando interfaz web..."
cd stellar-voice-display
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Esperar que el frontend inicie
sleep 5

# Mostrar información
echo ""
echo "✅ ¡Aura Web Interface iniciado!"
echo "================================"
echo "📡 WebSocket Server: ws://localhost:8765"
echo "🌐 Web Interface: http://localhost:8081"
echo ""
echo "📋 Instrucciones:"
echo "1. Abre tu navegador en: http://localhost:8081"
echo "2. Espera a que aparezcan los paneles"
echo "3. Haz clic en 'Touch to activate' para usar la voz"
echo ""
echo "📊 Logs:"
echo "- WebSocket: tail -f websocket.log"
echo "- Frontend: tail -f frontend.log"
echo ""
echo "Para detener, presiona Ctrl+C"
echo ""

# Mantener el script ejecutándose
wait 