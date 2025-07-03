#!/usr/bin/env bash

# Iniciar backend si no está corriendo
if ! pgrep -f "system_stats_api.py" > /dev/null; then
  echo "Iniciando backend system_stats_api.py en puerto 8000..."
  nohup python system_stats_api.py > backend.log 2>&1 &
else
  echo "Backend ya está corriendo."
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