#!/bin/bash

set -euo pipefail

echo "Starting Krise Engine..."

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"

cleanup_port() {
    local port="$1"
    local pids

    if ! command -v lsof >/dev/null 2>&1; then
        return
    fi

    pids="$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        echo "Releasing port $port..."
        kill $pids 2>/dev/null || true
        sleep 1
        pids="$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
        if [ -n "$pids" ]; then
            kill -9 $pids 2>/dev/null || true
        fi
    fi
}

# Purge stale venv created in an old backend/.venv location
if [ -f "$VENV_DIR/bin/activate" ] && grep -q "$SCRIPT_DIR/backend/.venv" "$VENV_DIR/bin/activate"; then
    echo "Found stale virtual environment metadata. Recreating .venv..."
    rm -rf "$VENV_DIR"
fi

if [ -x "$VENV_PYTHON" ]; then
    echo "Virtual environment already exists at ./.venv — skipping setup."
else
    # Ask user for package manager preference
    echo ""
    echo "Choose your package manager:"
    echo "1) UV (faster)"
    echo "2) pip (default)"
    echo ""
    read -p "Enter option (1 or 2): " PACKAGE_MANAGER

    # Validate input
    if [ "$PACKAGE_MANAGER" != "1" ] && [ "$PACKAGE_MANAGER" != "2" ]; then
        echo "Invalid option. Defaulting to pip."
        PACKAGE_MANAGER="2"
    fi

    # Handle UV setup if chosen
    if [ "$PACKAGE_MANAGER" == "1" ]; then
        echo "Setting up UV..."
        if ! command -v uv &> /dev/null; then
            if ! command -v pipx &> /dev/null; then
                echo "Installing pipx..."
                python3 -m pip install --user pipx
                export PATH="$PATH:$HOME/.local/bin"
            fi
            echo "Installing uv via pipx..."
            pipx install uv
            export PATH="$PATH:$HOME/.local/bin"
        fi
    fi

    echo "Setting up virtual environment at ./.venv..."
    python3 -m venv "$VENV_DIR"

    echo "Installing backend dependencies..."
    if [ "$PACKAGE_MANAGER" == "1" ]; then
        uv pip install --python "$VENV_PYTHON" -r "$SCRIPT_DIR/backend/requirements.txt"
    else
        "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/backend/requirements.txt"
    fi
    "$VENV_PYTHON" -m playwright install chromium
fi

# Install frontend dependencies only when node_modules is missing
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd "$SCRIPT_DIR/frontend"
    npm install
    cd ..
fi

cleanup_port "$APP_PORT"
cleanup_port 5173

# Start Backend
echo "Starting Backend Server (Port $APP_PORT)..."
bash -c 'cd "$1/backend" && "$2" -m uvicorn app.main:app --host "$3" --port "$4"' _ "$SCRIPT_DIR" "$VENV_PYTHON" "$APP_HOST" "$APP_PORT" &
BACKEND_PID=$!

echo "Starting Frontend Server (Port 5173)..."
# Start Frontend
cd "$SCRIPT_DIR/frontend"
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo ""
echo "Both servers are starting up!"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:$APP_PORT"
echo "Press Ctrl+C to stop both servers."

# Catch Ctrl+C to stop both background processes
trap "echo -e '\nShutting down servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for both processes to keep script running
wait $BACKEND_PID $FRONTEND_PID
