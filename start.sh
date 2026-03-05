#!/bin/bash

echo "Starting Krise Engine..."

# Start Backend
echo "Starting Backend Server (Port 8000)..."
cd backend
# Create venv if it doesn't exist just in case
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
else
    source venv/bin/activate
fi

uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

echo "Starting Frontend Server (Port 5173)..."
# Start Frontend
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo ""
echo "Both servers are starting up!"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "Press Ctrl+C to stop both servers."

# Catch Ctrl+C to stop both background processes
trap "echo -e '\nShutting down servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for both processes to keep script running
wait $BACKEND_PID $FRONTEND_PID
