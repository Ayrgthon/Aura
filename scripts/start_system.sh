#!/bin/bash

# Script para iniciar el sistema Aura de forma manual y controlada

echo "🌟 INICIANDO SISTEMA AURA"
echo "========================="

# Activar entorno virtual
echo "📦 Activando entorno virtual..."
source venv/bin/activate

# Verificar que estamos en el entorno correcto
echo "🐍 Python: $(which python)"
echo "📍 Directorio: $(pwd)"

# Función para matar procesos al salir
cleanup() {
    echo ""
    echo "🛑 Cerrando sistema..."
    
    # Matar procesos por nombre
    pkill -f "python.*system_stats_api.py" 2>/dev/null
    pkill -f "python.*websocket_server.py" 2>/dev/null
    pkill -f "npm run dev" 2>/dev/null
    
    # Matar procesos por PID si los tenemos
    if [ ! -z "$STATS_PID" ]; then
        kill -9 $STATS_PID 2>/dev/null || true
    fi
    if [ ! -z "$WEBSOCKET_PID" ]; then
        kill -9 $WEBSOCKET_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill -9 $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Liberar puertos forzosamente
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8766 | xargs kill -9 2>/dev/null || true
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    
    sleep 2
    echo "👋 Sistema cerrado"
    exit 0
}

# Configurar manejo de señales
trap cleanup SIGINT SIGTERM

# Matar procesos previos que puedan estar corriendo
echo "🧹 Limpiando procesos previos..."
pkill -f "python.*system_stats_api.py" 2>/dev/null
pkill -f "python.*websocket_server.py" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# Matar procesos específicos en los puertos
echo "🔪 Liberando puertos..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8766 | xargs kill -9 2>/dev/null || true  
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Esperar más tiempo para que los procesos terminen completamente
sleep 5

# Verificar que los puertos estén libres
if ss -tln | grep -q ":8000 "; then
    echo "❌ Puerto 8000 aún ocupado"
    exit 1
fi

if ss -tln | grep -q ":8766 "; then
    echo "❌ Puerto 8766 aún ocupado"
    exit 1
fi

if ss -tln | grep -q ":5173 "; then
    echo "❌ Puerto 5173 aún ocupado" 
    exit 1
fi

echo "✅ Puertos liberados correctamente"

# Iniciar API de estadísticas
echo "📊 Iniciando API de estadísticas en puerto 8000..."
cd src
python system_stats_api.py &
STATS_PID=$!
echo "   PID: $STATS_PID"
sleep 3

# Verificar que la API está corriendo
if ! curl -s http://localhost:8000/system-stats > /dev/null; then
    echo "❌ Error: API de estadísticas no responde"
    exit 1
fi
echo "✅ API de estadísticas funcionando"

# Iniciar servidor WebSocket
echo "🌐 Iniciando servidor WebSocket en puerto 8766..."
python websocket_server.py &
WEBSOCKET_PID=$!
echo "   PID: $WEBSOCKET_PID"
sleep 5

# Verificar que el WebSocket está corriendo
sleep 2  # Esperar más tiempo para que inicie
retry_count=0
while [ $retry_count -lt 10 ]; do
    if ss -tln | grep 8766 > /dev/null; then
        echo "✅ Servidor WebSocket funcionando"
        break
    fi
    echo "⏳ Esperando que el WebSocket inicie... ($retry_count/10)"
    sleep 1
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq 10 ]; then
    echo "❌ Error: Servidor WebSocket no pudo iniciarse"
    echo "📋 Revisando el proceso..."
    if ! kill -0 $WEBSOCKET_PID 2>/dev/null; then
        echo "💔 El proceso WebSocket murió"
        exit 1
    fi
fi

# Volver al directorio principal
cd ..

# Iniciar frontend
echo "🎨 Iniciando frontend en puerto 5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"
sleep 5

# Verificar que el frontend está corriendo
if ! ss -tln | grep 5173 > /dev/null; then
    echo "❌ Error: Frontend no está escuchando"
    exit 1
fi
echo "✅ Frontend funcionando"

# Volver al directorio principal
cd ..

echo ""
echo "🎉 SISTEMA AURA INICIADO CORRECTAMENTE"
echo "======================================"
echo "📊 API de estadísticas: http://localhost:8000"
echo "🌐 Servidor WebSocket:   ws://localhost:8766"
echo "🎨 Frontend:             http://localhost:5173"
echo ""
echo "💡 Presiona Ctrl+C para cerrar todo el sistema"
echo "======================================"

# Monitorear procesos
while true; do
    sleep 10
    
    # Verificar que todos los procesos siguen corriendo
    if ! kill -0 $STATS_PID 2>/dev/null; then
        echo "💔 API de estadísticas se cerró inesperadamente"
    fi
    
    if ! kill -0 $WEBSOCKET_PID 2>/dev/null; then
        echo "💔 Servidor WebSocket se cerró inesperadamente"
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "💔 Frontend se cerró inesperadamente"
    fi
done