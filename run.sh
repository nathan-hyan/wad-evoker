#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

cd "$SCRIPT_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo "[wad-evoker] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "[wad-evoker] Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[wad-evoker] Launching..."
python3 main.py
