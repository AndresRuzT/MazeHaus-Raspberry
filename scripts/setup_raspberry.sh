#!/usr/bin/env bash
# ==============================================================================
# MazeHaus / FingerMaze - Automated Setup Script for Raspberry Pi 4 (ARM64)
# ==============================================================================
set -e

echo "=========================================================="
echo " Instalando dependencias del sistema para Raspberry Pi OS"
echo "=========================================================="

sudo apt update
sudo apt install -y \
    curl \
    git \
    v4l-utils \
    libgl1 \
    libglib2.0-0 \
    libasound2

# Ensure user is in the video group to access USB camera
sudo usermod -aG video "$USER"

echo ""
echo "=========================================================="
echo " Verificando herramienta uv..."
echo "=========================================================="

if ! command -v uv &> /dev/null; then
    echo "Instalando uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "=========================================================="
echo " Sincronizando entorno virtual con Python 3.12 y librerías"
echo "=========================================================="

# Sincroniza entorno virtual de uv
uv sync

echo ""
echo "=========================================================="
echo " Descargando modelo Hand Landmarker..."
echo "=========================================================="

uv run python scripts/download_model.py

echo ""
echo "=========================================================="
echo " Verificando cámara y diagnóstico de entorno..."
echo "=========================================================="

uv run python scripts/check_environment.py

echo ""
echo "=========================================================="
echo " [¡LISTO!] Todo configurado exitosamente."
echo " Para iniciar el juego ejecuta:"
echo "   uv run python -m fingermaze"
echo " o en pantalla completa:"
echo "   uv run python -m fingermaze --fullscreen"
echo "=========================================================="
