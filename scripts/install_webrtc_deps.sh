#!/bin/bash

echo "🚀 Instalando dependencias WebRTC para Aura..."
echo "================================================"

# Backend dependencies
echo "📦 Instalando dependencias Python..."
source venv/bin/activate

pip install --upgrade pip
pip install aiortc uvloop

# Optional: Install system dependencies for aiortc
if command -v apt-get &> /dev/null; then
    echo "🔧 Instalando dependencias del sistema (Ubuntu/Debian)..."
    sudo apt-get update
    sudo apt-get install -y \
        libavdevice-dev \
        libavfilter-dev \
        libopus-dev \
        libvpx-dev \
        pkg-config
elif command -v yum &> /dev/null; then
    echo "🔧 Instalando dependencias del sistema (CentOS/RHEL)..."
    sudo yum install -y \
        libavdevice-devel \
        libavfilter-devel \
        opus-devel \
        libvpx-devel \
        pkgconfig
elif command -v pacman &> /dev/null; then
    echo "🔧 Instalando dependencias del sistema (Arch Linux)..."
    sudo pacman -S --needed \
        ffmpeg \
        opus \
        libvpx \
        pkgconf
elif command -v brew &> /dev/null; then
    echo "🔧 Instalando dependencias del sistema (macOS)..."
    brew install opus libvpx pkg-config
fi

echo ""
echo "✅ Dependencias WebRTC instaladas!"
echo ""
echo "📋 Para usar el sistema optimizado:"
echo "1. Backend: python src/integration_optimized.py"
echo "2. Frontend: cd frontend && npm run dev"
echo ""
echo "🎯 Características habilitadas:"
echo "- ✅ Audio WebRTC en tiempo real"
echo "- ✅ Manejo anti-feedback del main.py"
echo "- ✅ Optimizaciones de rendimiento"
echo "- ✅ Reconexión automática"
echo ""