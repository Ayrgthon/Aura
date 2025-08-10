#!/bin/bash

# Script para detener todos los servicios de Aura
# Autor: Claude
# Descripción: Detiene de forma segura todos los servicios de Aura

set -e

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

print_status "=== DETENIENDO SERVICIOS DE AURA ==="

# Función para detener un proceso por PID
stop_process() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            print_status "Deteniendo $service_name (PID: $pid)..."
            kill $pid
            sleep 2
            
            # Verificar si el proceso aún existe
            if ps -p $pid > /dev/null 2>&1; then
                print_warning "Forzando cierre de $service_name..."
                kill -9 $pid
            fi
            
            print_success "$service_name detenido"
        else
            print_warning "$service_name no estaba ejecutándose (PID no válido: $pid)"
        fi
        rm -f "$pid_file"
    else
        print_warning "No se encontró archivo PID para $service_name"
    fi
}

# Detener cada servicio
stop_process "WebSocket Server" "$LOGS_DIR/websocket_server.pid"
stop_process "System Stats API" "$LOGS_DIR/system_stats_api.pid"
stop_process "Frontend" "$LOGS_DIR/frontend.pid"

# Verificar y matar procesos por puerto como respaldo
print_status "Verificando procesos en puertos..."

# Puerto 8766 (WebSocket)
if lsof -ti :8766 > /dev/null 2>&1; then
    print_status "Deteniendo proceso en puerto 8766..."
    lsof -ti :8766 | xargs kill -9 2>/dev/null || true
fi

# Puerto 8000 (System Stats API)
if lsof -ti :8000 > /dev/null 2>&1; then
    print_status "Deteniendo proceso en puerto 8000..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
fi

# Puerto 5173 (Frontend)
if lsof -ti :5173 > /dev/null 2>&1; then
    print_status "Deteniendo proceso en puerto 5173..."
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
fi

print_success "=== TODOS LOS SERVICIOS DETENIDOS ==="
print_status "Los logs se han conservado en: $LOGS_DIR"