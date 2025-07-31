#!/bin/bash

echo "🧹 LIMPIANDO SISTEMA AURA"
echo "========================="

# Matar todos los procesos de Aura
echo "🔪 Matando procesos por nombre..."
pkill -f "python.*system_stats_api.py" 2>/dev/null || true
pkill -f "python.*websocket_server.py" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true

# Matar procesos por puerto
echo "🔪 Liberando puertos..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8766 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Esperar un poco
sleep 3

# Verificar que los puertos estén libres
echo "🔍 Verificando puertos..."
if ss -tln | grep -q ":8000 "; then
    echo "⚠️  Puerto 8000 aún ocupado"
    ss -tln | grep ":8000 "
else
    echo "✅ Puerto 8000 libre"
fi

if ss -tln | grep -q ":8766 "; then
    echo "⚠️  Puerto 8766 aún ocupado"
    ss -tln | grep ":8766 "
else
    echo "✅ Puerto 8766 libre"
fi

if ss -tln | grep -q ":5173 "; then
    echo "⚠️  Puerto 5173 aún ocupado"
    ss -tln | grep ":5173 "
else
    echo "✅ Puerto 5173 libre"
fi

echo "✅ Limpieza completada"