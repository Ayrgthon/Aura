#!/bin/bash

# Script de inicialización para Aura
# Autor: Claude
# Descripción: Configura e inicia todos los servicios de Aura con logs separados

set -e  # Salir si cualquier comando falla

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes coloreados
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_DIR/logs"

print_status "Directorio del proyecto: $PROJECT_DIR"

# Crear directorio de logs si no existe
if [ ! -d "$LOGS_DIR" ]; then
    mkdir -p "$LOGS_DIR"
    print_success "Directorio de logs creado: $LOGS_DIR"
fi

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR"

print_status "=== CONFIGURANDO ENTORNO VIRTUAL DE PYTHON ==="

# Verificar si existe el entorno virtual
if [ ! -d "venv" ]; then
    print_status "Creando entorno virtual..."
    python3 -m venv venv
    print_success "Entorno virtual creado"
else
    print_success "Entorno virtual ya existe"
fi

# Activar entorno virtual
source venv/bin/activate
print_success "Entorno virtual activado"

# Verificar si las dependencias están instaladas
print_status "Verificando dependencias de Python..."
if ! pip show requests > /dev/null 2>&1; then
    print_status "Instalando dependencias de Python..."
    pip install -r requirements.txt
    print_success "Dependencias de Python instaladas"
else
    print_success "Dependencias de Python ya están instaladas"
fi

print_status "=== CONFIGURANDO DEPENDENCIAS NODE.JS ==="

# Instalar dependencias del directorio raíz
print_status "Verificando dependencias Node.js del directorio raíz..."
if [ ! -d "node_modules" ]; then
    print_status "Instalando dependencias del directorio raíz..."
    npm install
    print_success "Dependencias del directorio raíz instaladas"
else
    print_success "Dependencias del directorio raíz ya están instaladas"
fi

# Instalar dependencias del frontend
print_status "Verificando dependencias del frontend..."
cd frontend/
if [ ! -d "node_modules" ]; then
    print_status "Instalando dependencias del frontend..."
    npm install
    print_success "Dependencias del frontend instaladas"
else
    print_success "Dependencias del frontend ya están instaladas"
fi

# Volver al directorio del proyecto
cd "$PROJECT_DIR"

print_status "=== INICIANDO SERVICIOS ==="

# Función para verificar si un puerto está en uso
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Puerto en uso
    else
        return 1  # Puerto libre
    fi
}

# Limpiar logs anteriores
print_status "Limpiando logs anteriores..."
rm -f "$LOGS_DIR"/*.log
print_success "Logs anteriores eliminados"

# Iniciar aura_websocket_server.py
print_status "Iniciando servidor WebSocket de Aura..."
if check_port 8766; then
    print_warning "El puerto 8766 ya está en uso. El servidor WebSocket podría ya estar ejecutándose."
else
    cd src/
    nohup python aura_websocket_server.py > "$LOGS_DIR/websocket_server.log" 2>&1 &
    WEBSOCKET_PID=$!
    echo $WEBSOCKET_PID > "$LOGS_DIR/websocket_server.pid"
    cd "$PROJECT_DIR"
    print_success "Servidor WebSocket iniciado (PID: $WEBSOCKET_PID)"
    sleep 2
fi

# Iniciar system_stats_api.py
print_status "Iniciando API de estadísticas del sistema..."
if check_port 8000; then
    print_warning "El puerto 8000 ya está en uso. La API de estadísticas podría ya estar ejecutándose."
else
    cd src/
    nohup python system_stats_api.py > "$LOGS_DIR/system_stats_api.log" 2>&1 &
    STATS_PID=$!
    echo $STATS_PID > "$LOGS_DIR/system_stats_api.pid"
    cd "$PROJECT_DIR"
    print_success "API de estadísticas iniciada (PID: $STATS_PID)"
    sleep 2
fi

# Iniciar frontend
print_status "Iniciando servidor de desarrollo del frontend..."
if check_port 5173; then
    print_warning "El puerto 5173 ya está en uso. El frontend podría ya estar ejecutándose."
else
    cd frontend/
    nohup npm run dev > "$LOGS_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$LOGS_DIR/frontend.pid"
    cd "$PROJECT_DIR"
    print_success "Frontend iniciado (PID: $FRONTEND_PID)"
    sleep 3
fi

print_success "=== TODOS LOS SERVICIOS INICIADOS ==="
echo ""
print_status "Servicios disponibles:"
print_status "  - WebSocket Server: ws://localhost:8766"
print_status "  - System Stats API: http://localhost:8000"
print_status "  - Frontend: http://localhost:5173"
echo ""
print_status "Logs disponibles en: $LOGS_DIR"
print_status "  - websocket_server.log"
print_status "  - system_stats_api.log"
print_status "  - frontend.log"
echo ""
print_status "Para detener los servicios, ejecuta: ./scripts/stop_aura.sh"
print_status "Para ver logs en tiempo real: tail -f logs/<servicio>.log"

# Verificar que los servicios estén funcionando
sleep 5
print_status "=== VERIFICANDO SERVICIOS ==="

failed_services=0

if check_port 8766; then
    print_success "✓ WebSocket Server está ejecutándose"
else
    print_error "✗ WebSocket Server no está ejecutándose"
    failed_services=$((failed_services + 1))
fi

if check_port 8000; then
    print_success "✓ System Stats API está ejecutándose"
else
    print_error "✗ System Stats API no está ejecutándose"
    failed_services=$((failed_services + 1))
fi

if check_port 5173; then
    print_success "✓ Frontend está ejecutándose"
else
    print_error "✗ Frontend no está ejecutándose"
    failed_services=$((failed_services + 1))
fi

if [ $failed_services -eq 0 ]; then
    print_success "¡Todos los servicios están ejecutándose correctamente!"
    echo ""
    print_status "🚀 Aura está listo para usar en: http://localhost:5173"
else
    print_warning "Algunos servicios fallaron al iniciar. Revisa los logs en $LOGS_DIR/"
fi