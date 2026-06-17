#!/bin/bash
# ==============================================================================
# CodeBattle — Development Server Launcher
# Starts backend and frontend in parallel (without Docker)
# Requires: Python 3.12+, Node.js 20+, PostgreSQL, Redis running locally
# ==============================================================================

set -e

echo "🚀 Starting CodeBattle development servers..."

# ── Backend ─────────────────────────────────────────────────────────────────
start_backend() {
    echo "📦 Setting up backend..."
    cd backend

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    fi

    source venv/bin/activate
    pip install -q -r requirements.txt

    echo "🔥 Starting FastAPI backend on http://localhost:8000"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..
    echo $BACKEND_PID > /tmp/codebattle_backend.pid
}

# ── Frontend ─────────────────────────────────────────────────────────────────
start_frontend() {
    echo "📦 Setting up frontend..."
    cd frontend

    if [ ! -d "node_modules" ]; then
        npm install
    fi

    echo "🔥 Starting Next.js frontend on http://localhost:3000"
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo $FRONTEND_PID > /tmp/codebattle_frontend.pid
}

start_backend
start_frontend

echo ""
echo "✅ Both servers are running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and cleanup on exit
trap "kill $(cat /tmp/codebattle_backend.pid) $(cat /tmp/codebattle_frontend.pid) 2>/dev/null" EXIT
wait
