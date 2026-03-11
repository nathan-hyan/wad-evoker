#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

cd "$SCRIPT_DIR"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[wad-evoker] Creating virtual environment..."
    if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
        if command -v apt-get &>/dev/null; then
            PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            echo "[wad-evoker] Installing python${PY_VER}-venv..."
            sudo apt-get install -y "python${PY_VER}-venv"
            python3 -m venv "$VENV_DIR"
        else
            echo "[wad-evoker] ERROR: Could not create virtual environment. Please install python3-venv manually." >&2
            exit 1
        fi
    fi
fi

source "$VENV_DIR/bin/activate"

echo "[wad-evoker] Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[wad-evoker] Launching..."
python3 main.py
