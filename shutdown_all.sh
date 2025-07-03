#!/usr/bin/env bash

echo "🔴 Apagando todos los servicios de Aura..."

# Activar entorno virtual para asegurar contexto correcto
source venv/bin/activate 2>/dev/null || true

# Función para matar procesos de forma segura
kill_process() {
    local process_name="$1"
    local pids=$(pgrep -f "$process_name")
    
    if [ -n "$pids" ]; then
        echo "🔫 Matando procesos de $process_name..."
        pkill -f "$process_name"
        sleep 1
        
        # Verificar si aún existen procesos
        local remaining=$(pgrep -f "$process_name")
        if [ -n "$remaining" ]; then
            echo "⚡ Forzando cierre de $process_name..."
            pkill -9 -f "$process_name"
        fi
        echo "✅ $process_name terminado"
    else
        echo "ℹ️  $process_name no estaba corriendo"
    fi
}

# Matar servicios en orden
kill_process "websocket_server_simple.py"
kill_process "websocket_server.py" 
kill_process "system_stats_api.py"
kill_process "python main.py"

# Matar cualquier proceso Python relacionado con Aura
echo "🧹 Limpiando procesos residuales..."
pkill -f "stellar-voice-display"

# Verificar puertos específicos
echo "🔍 Verificando puertos..."
if lsof -i :8765 > /dev/null 2>&1; then
    echo "⚠️  Puerto 8765 aún ocupado, liberando..."
    fuser -k 8765/tcp 2>/dev/null
fi

if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Puerto 8000 aún ocupado, liberando..."
    fuser -k 8000/tcp 2>/dev/null
fi

echo "✅ Todos los servicios de Aura han sido apagados correctamente"
echo "💡 Para reiniciar, ejecuta: ./start_all.sh" 