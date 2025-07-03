#!/usr/bin/env bash

set -e

# ===============================
#  INSTALADOR AUTOMÁTICO DE AURA
# ===============================
# Para Arch Linux + Hyprland
# Ejecuta este script en la raíz del repo clonado
# ===============================

# 1. Actualizar el sistema
sudo pacman -Syu --noconfirm

# 2. Instalar dependencias base
sudo pacman -S --needed --noconfirm git base-devel python python-pip nodejs npm ffmpeg espeak sox alsa-utils xdg-desktop-portal-hyprland xdg-desktop-portal wl-clipboard hyprland

# 3. Instalar dependencias opcionales (AUR)
if ! command -v yay &>/dev/null; then
  echo "Instalando yay (AUR helper)..."
  git clone https://aur.archlinux.org/yay.git /tmp/yay
  cd /tmp/yay && makepkg -si --noconfirm
  cd -
fi

yay -S --needed --noconfirm rocm-smi radeontop swhkd ydotool

# 4. Crear entorno virtual Python
if [ ! -d "venv" ]; then
  python -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install elevenlabs

echo "[OK] Dependencias Python instaladas."

# 5. Instalar dependencias Node.js para el frontend
cd stellar-voice-display
npm install
cd ..
echo "[OK] Dependencias Node.js instaladas."

# 6. Instalar Ollama
if ! command -v ollama &>/dev/null; then
  echo "Instalando Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi
ollama serve &
sleep 2
ollama pull llama3 || true

echo "[OK] Ollama instalado y modelo base descargado."

# 7. Recordatorio para la API Key de Gemini
if ! grep -q "GOOGLE_API_KEY" client.py; then
  echo "❗️ Recuerda configurar tu API Key de Gemini en client.py o en tu entorno."
fi

# 8. Permisos de ejecución para scripts
chmod +x start_all.sh shutdown_all.sh

echo "[OK] Scripts de inicio listos."

echo "\n====================================="
echo "✅ Instalación de Aura completada."
echo "====================================="
echo "\nPara iniciar Aura ejecuta:"
echo "  ./start_all.sh"
echo "\nPara apagar Aura ejecuta:"
echo "  ./shutdown_all.sh"
echo "\nLuego abre tu navegador en http://localhost:5173 o usa modo kiosk."
echo "\n💡 Si usas Hyprland, puedes añadir esto a tu hyprland.conf:"
echo '  exec-once = chromium --kiosk http://localhost:5173'
echo "\n¡Disfruta Aura en tu Arch Linux!" 