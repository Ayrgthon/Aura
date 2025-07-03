#!/usr/bin/env bash

# Función para verificar si un puerto está en uso
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Puerto en uso
    else
        return 1  # Puerto libre
    fi
}

# Función para esperar a que un servicio esté disponible
wait_for_service() {
    local port=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    echo "Esperando a que $service_name esté disponible en puerto $port..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
            echo "✅ $service_name está respondiendo en puerto $port"
            return 0
        fi
        echo "Intento $attempt de $max_attempts..."
        sleep 1
        ((attempt++))
    done
    echo "❌ $service_name no respondió después de $max_attempts intentos"
    return 1
}

# Función para matar proceso por puerto
kill_port() {
    local port=$1
    if check_port $port; then
        echo "Matando proceso en puerto $port..."
        fuser -k $port/tcp
        sleep 1
    fi
}

# Activar entorno virtual
source venv/bin/activate

# Asegurarse de que el puerto 8000 esté libre
kill_port 8000

# Iniciar backend stats API
echo "Iniciando backend system_stats_api.py en puerto 8000..."
nohup python system_stats_api.py > backend_stats.log 2>&1 &
API_PID=$!

# Esperar a que la API esté disponible
if ! wait_for_service 8000 "Stats API"; then
    echo "❌ Error: La API no pudo iniciarse correctamente"
    kill $API_PID 2>/dev/null
    exit 1
fi

# Asegurarse de que el puerto 8765 esté libre
kill_port 8765

# Iniciar servidor WebSocket
echo "Iniciando servidor WebSocket en puerto 8765..."
nohup python websocket_server_simple.py > websocket.log 2>&1 &
WS_PID=$!

# Esperar a que el WebSocket esté disponible
sleep 2  # Dar tiempo a que inicie

# Iniciar frontend
cd stellar-voice-display
if ! pgrep -f "vite" > /dev/null; then
    echo "Iniciando frontend (npm run dev)..."
    nohup npm run dev > ../frontend.log 2>&1 &
else
    echo "Frontend ya está corriendo."
fi
cd ..

echo "✅ Todos los servicios están activos:"
echo "   - Stats API: http://localhost:8000"
echo "   - WebSocket: ws://localhost:8765"
echo "   - Frontend: http://localhost:5173" 