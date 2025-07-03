#!/usr/bin/env bash

# Activar entorno virtual
source venv/bin/activate

# Iniciar backend stats API si no está corriendo
if ! pgrep -f "system_stats_api.py" > /dev/null; then
  echo "Iniciando backend system_stats_api.py en puerto 8000..."
  nohup ./venv/bin/python system_stats_api.py > backend_stats.log 2>&1 &
else
  echo "Backend stats API ya está corriendo."
fi

# Iniciar servidor WebSocket si no está corriendo
if ! pgrep -f "websocket_server_simple.py" > /dev/null; then
  echo "Iniciando servidor WebSocket en puerto 8765..."
  nohup ./venv/bin/python websocket_server_simple.py > websocket.log 2>&1 &
else
  echo "Servidor WebSocket ya está corriendo."
fi

# Iniciar frontend si no está corriendo
cd stellar-voice-display
if ! pgrep -f "vite" > /dev/null; then
  echo "Iniciando frontend (npm run dev)..."
  nohup npm run dev > ../frontend.log 2>&1 &
else
  echo "Frontend ya está corriendo."
fi
cd ..

echo "Ambos servicios están activos. Puedes abrir la app en tu navegador." 