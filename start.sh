#!/usr/bin/env bash

# Script de inicio para Aura
# Este script inicia todos los servicios necesarios

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌟 Iniciando Aura - Asistente de IA Universal${NC}"
echo "================================================"

# Verificar archivo .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo "Copiando env.template a .env..."
    cp env.template .env
    echo -e "${YELLOW}Por favor, configura tus API keys en .env antes de continuar${NC}"
    exit 1
fi

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
            echo -e "${GREEN}✅ $service_name está respondiendo en puerto $port${NC}"
            return 0
        fi
        echo "Intento $attempt de $max_attempts..."
        sleep 1
        ((attempt++))
    done
    echo -e "${RED}❌ $service_name no respondió después de $max_attempts intentos${NC}"
    return 1
}

# Función para matar proceso por puerto
kill_port() {
    local port=$1
    if check_port $port; then
        echo "Liberando puerto $port..."
        fuser -k $port/tcp > /dev/null 2>&1
        sleep 1
    fi
}

# Verificar si existe el venv
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment no encontrado${NC}"
    echo "Creando virtual environment..."
    python3 -m venv venv
    echo "Instalando dependencias..."
    venv/bin/pip install -r requirements.txt
else
    # Verificar si las dependencias están instaladas
    if ! venv/bin/python -c "import sounddevice, vosk" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Instalando dependencias faltantes...${NC}"
        venv/bin/pip install -r requirements.txt
    fi
fi

# Asegurarse de que los puertos estén libres
echo -e "${YELLOW}🔧 Liberando puertos...${NC}"
kill_port 8000
kill_port 8765
kill_port 5173

# Iniciar backend stats API
echo -e "${GREEN}🚀 Iniciando API de estadísticas del sistema...${NC}"
cd src
nohup ../venv/bin/python system_stats_api.py > ../logs/backend_stats.log 2>&1 &
API_PID=$!
cd ..

# Esperar a que la API esté disponible
if ! wait_for_service 8000 "Stats API"; then
    echo -e "${RED}❌ Error: La API no pudo iniciarse correctamente${NC}"
    kill $API_PID 2>/dev/null
    exit 1
fi

# Iniciar servidor WebSocket
echo -e "${GREEN}🚀 Iniciando servidor WebSocket...${NC}"
cd src
nohup ../venv/bin/python websocket_server.py > ../logs/websocket.log 2>&1 &
WS_PID=$!
cd ..

# Esperar un momento para que el WebSocket inicie
sleep 2

# Iniciar frontend
echo -e "${GREEN}🚀 Iniciando frontend...${NC}"
cd frontend
if ! pgrep -f "vite" > /dev/null; then
    nohup npm run dev > ../logs/frontend.log 2>&1 &
else
    echo -e "${YELLOW}Frontend ya está corriendo${NC}"
fi
cd ..

echo ""
echo -e "${GREEN}✅ Todos los servicios están activos:${NC}"
echo "   - Stats API: http://localhost:8000"
echo "   - WebSocket: ws://localhost:8765"
echo "   - Frontend: http://localhost:5173"
echo ""
echo -e "${YELLOW}💡 Para detener todos los servicios, presiona Ctrl+C${NC}"
echo ""
echo -e "${GREEN}🎯 Abre tu navegador en http://localhost:5173${NC}"

# Mantener el script corriendo
trap "echo -e '\n${YELLOW}Deteniendo servicios...${NC}'; kill $API_PID $WS_PID 2>/dev/null; exit" INT TERM
wait 