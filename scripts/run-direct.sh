#!/bin/bash
#
# Run AI Analytics Platform directly on VM (no Docker)
# This script installs dependencies and starts both backend and frontend
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="/Users/sam-bot/.openclaw/workspace/ai-analytics-platform"

echo "🚀 AI Analytics Platform - Direct VM Setup"
echo "=========================================="
echo ""

# Get VM IP
VM_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "localhost")
echo "📍 VM IP: $VM_IP"
echo ""

# Check Python
echo "🐍 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi
python3 --version
echo -e "${GREEN}✅${NC} Python OK"
echo ""

# Check Node
echo "📦 Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found${NC}"
    echo "Install with: brew install node"
    exit 1
fi
node --version
echo -e "${GREEN}✅${NC} Node OK"
echo ""

# Install backend dependencies
echo "📥 Installing backend dependencies..."
cd "$PROJECT_ROOT/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅${NC} Backend dependencies installed"
echo ""

# Check/create .env
echo "⚙️  Checking configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Created .env from template${NC}"
    echo -e "${YELLOW}   Edit $PROJECT_ROOT/backend/.env and add your KIMI_API_KEY${NC}"
fi
echo ""

# Install frontend dependencies
echo "📥 Installing frontend dependencies..."
cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps
fi
echo -e "${GREEN}✅${NC} Frontend dependencies installed"
echo ""

# Start services
echo "🚀 Starting services..."
echo ""

# Start backend in background
echo "🟢 Starting backend on http://$VM_IP:8000"
cd "$PROJECT_ROOT/backend"
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PROJECT_ROOT/.backend.pid"
echo -e "${GREEN}✅${NC} Backend started (PID: $BACKEND_PID)"
echo ""

# Wait for backend
sleep 3
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} Backend is responding"
else
    echo -e "${YELLOW}⏳${NC} Backend starting... check logs: tail -f $PROJECT_ROOT/backend.log"
fi
echo ""

# Start frontend in background
echo "🟢 Starting frontend on http://$VM_IP:3000"
cd "$PROJECT_ROOT/frontend"
# Update next.config.js for external access
if ! grep -q "0.0.0.0" next.config.js 2>/dev/null; then
    echo "const nextConfig = { experimental: { appDir: true }, images: { unoptimized: true }, async rewrites() { return [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }]; } }; module.exports = nextConfig;" > next.config.js
fi
nohup npm run dev -- --hostname 0.0.0.0 > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PROJECT_ROOT/.frontend.pid"
echo -e "${GREEN}✅${NC} Frontend started (PID: $FRONTEND_PID)"
echo ""

# Wait for frontend
sleep 5
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║  🎉 AI Analytics Platform is running!                    ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "🌐 Access from this VM:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🌐 Access from your Mac (same network):"
echo "   Frontend: http://$VM_IP:3000"
echo "   Backend:  http://$VM_IP:8000"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f $PROJECT_ROOT/backend.log"
echo "   Frontend: tail -f $PROJECT_ROOT/frontend.log"
echo ""
echo "🛑 To stop:"
echo "   ./scripts/stop-direct.sh"
echo ""
