#!/bin/bash

echo "🚀 Iniciando Interfaz de Voz de Aura..."
echo "======================================"

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi

# Verificar si Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado"
    exit 1
fi

# Instalar dependencias de Python si es necesario
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

echo "📦 Instalando dependencias de Python..."
source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

# Instalar dependencias del frontend si es necesario
if [ ! -d "stellar-voice-display/node_modules" ]; then
    echo "📦 Instalando dependencias del frontend..."
    cd stellar-voice-display
    npm install > /dev/null 2>&1
    cd ..
fi

# Iniciar servidor WebSocket en segundo plano
echo "📡 Iniciando servidor WebSocket..."
python websocket_server_simple.py > websocket.log 2>&1 &
WEBSOCKET_PID=$!

# Esperar un poco
sleep 2

# Iniciar frontend en segundo plano
echo "🌐 Iniciando interfaz web..."
cd stellar-voice-display
npm run dev &
FRONTEND_PID=$!
cd ..

# Esperar un poco más
sleep 3

echo ""
echo "✅ ¡Interfaz de voz iniciada!"
echo "=============================="
echo "🌐 Abre tu navegador en: http://localhost:5173"
echo "📡 WebSocket activo en: ws://localhost:8765"
echo ""
echo "Para detener, presiona Ctrl+C"
echo ""

# Función para limpiar al salir
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

# Mantener el script ejecutándose
wait 