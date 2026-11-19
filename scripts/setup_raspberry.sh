#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Installing system dependencies for Raspberry Pi OS"
echo "=========================================================="

sudo apt update
sudo apt install -y \
    curl \
    git \
    v4l-utils \
    libgl1 \
    libglib2.0-0 \
    libasound2

# Add user to the video group for webcam access
sudo usermod -aG video "$USER"

echo ""
echo "=========================================================="
echo " Checking package manager..."
echo "=========================================================="

if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "=========================================================="
echo " Synchronizing Python virtual environment..."
echo "=========================================================="

uv sync

echo ""
echo "=========================================================="
echo " Downloading Hand Landmarker model weights..."
echo "=========================================================="

uv run python scripts/download_model.py

echo ""
echo "=========================================================="
echo " Running environment and camera diagnostics..."
echo "=========================================================="

uv run python scripts/check_environment.py

echo ""
echo "=========================================================="
echo " Setup complete and verified."
echo " To start the game, run:"
echo "   uv run python -m fingermaze"
echo " Or in fullscreen kiosk mode:"
echo "   uv run python -m fingermaze --fullscreen"
echo "=========================================================="
