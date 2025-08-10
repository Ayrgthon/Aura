#!/bin/bash

# Script para monitorear logs de Aura en tiempo real
# Autor: Claude
# Descripción: Permite monitorear los logs de todos los servicios de Aura

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_DIR/logs"

print_usage() {
    echo -e "${BLUE}Uso: $0 [websocket|stats|frontend|all]${NC}"
    echo ""
    echo "Opciones:"
    echo "  websocket  - Monitorear logs del WebSocket Server"
    echo "  stats      - Monitorear logs de System Stats API"
    echo "  frontend   - Monitorear logs del Frontend"
    echo "  all        - Monitorear todos los logs simultáneamente"
    echo ""
    echo "Si no se especifica opción, se mostrará este menú."
}

monitor_single_log() {
    local service=$1
    local logfile=$2
    local color=$3
    
    if [ ! -f "$logfile" ]; then
        echo -e "${RED}[ERROR]${NC} Log file no encontrado: $logfile"
        exit 1
    fi
    
    echo -e "${color}=== Monitoreando $service ===${NC}"
    echo -e "${YELLOW}Archivo: $logfile${NC}"
    echo -e "${YELLOW}Presiona Ctrl+C para salir${NC}"
    echo ""
    
    tail -f "$logfile"
}

monitor_all_logs() {
    echo -e "${CYAN}=== Monitoreando todos los logs de Aura ===${NC}"
    echo -e "${YELLOW}Presiona Ctrl+C para salir${NC}"
    echo ""
    
    # Verificar que existan los archivos de log
    local logs_found=0
    
    if [ -f "$LOGS_DIR/websocket_server.log" ]; then
        logs_found=$((logs_found + 1))
    fi
    
    if [ -f "$LOGS_DIR/system_stats_api.log" ]; then
        logs_found=$((logs_found + 1))
    fi
    
    if [ -f "$LOGS_DIR/frontend.log" ]; then
        logs_found=$((logs_found + 1))
    fi
    
    if [ $logs_found -eq 0 ]; then
        echo -e "${RED}[ERROR]${NC} No se encontraron archivos de log. ¿Están ejecutándose los servicios?"
        echo "Ejecuta './scripts/start_aura.sh' para iniciar los servicios."
        exit 1
    fi
    
    # Usar multitail si está disponible, sino usar tail con etiquetas
    if command -v multitail > /dev/null 2>&1; then
        multitail \
            -l "tail -f $LOGS_DIR/websocket_server.log" \
            -l "tail -f $LOGS_DIR/system_stats_api.log" \
            -l "tail -f $LOGS_DIR/frontend.log"
    else
        echo -e "${YELLOW}[INFO]${NC} multitail no está instalado. Usando tail básico..."
        echo -e "${YELLOW}[TIP]${NC} Instala multitail para una mejor experiencia: sudo apt install multitail"
        echo ""
        
        # Crear un archivo temporal para combinar logs
        temp_file=$(mktemp)
        trap "rm -f $temp_file" EXIT
        
        # Iniciar tail en background para cada log
        if [ -f "$LOGS_DIR/websocket_server.log" ]; then
            tail -f "$LOGS_DIR/websocket_server.log" | sed 's/^/[WebSocket] /' >> "$temp_file" &
        fi
        
        if [ -f "$LOGS_DIR/system_stats_api.log" ]; then
            tail -f "$LOGS_DIR/system_stats_api.log" | sed 's/^/[StatsAPI] /' >> "$temp_file" &
        fi
        
        if [ -f "$LOGS_DIR/frontend.log" ]; then
            tail -f "$LOGS_DIR/frontend.log" | sed 's/^/[Frontend] /' >> "$temp_file" &
        fi
        
        # Mostrar el archivo combinado
        tail -f "$temp_file"
    fi
}

# Verificar que existe el directorio de logs
if [ ! -d "$LOGS_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Directorio de logs no encontrado: $LOGS_DIR"
    echo "¿Están ejecutándose los servicios?"
    exit 1
fi

# Procesar argumentos
case "${1:-help}" in
    websocket|ws)
        monitor_single_log "WebSocket Server" "$LOGS_DIR/websocket_server.log" "$GREEN"
        ;;
    stats|api)
        monitor_single_log "System Stats API" "$LOGS_DIR/system_stats_api.log" "$YELLOW"
        ;;
    frontend|fe)
        monitor_single_log "Frontend" "$LOGS_DIR/frontend.log" "$CYAN"
        ;;
    all)
        monitor_all_logs
        ;;
    help|--help|-h)
        print_usage
        ;;
    *)
        echo -e "${RED}[ERROR]${NC} Opción no válida: $1"
        echo ""
        print_usage
        exit 1
        ;;
esac