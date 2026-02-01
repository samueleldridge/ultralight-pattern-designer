#!/bin/bash
#
# Start AI Analytics Platform
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting AI Analytics Platform..."
echo ""

cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Run: ./scripts/setup.sh first"
    exit 1
fi

# Start services
echo "📦 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Health check
echo ""
echo "🏥 Running health check..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running"
else
    echo "⏳ Backend still starting..."
fi

echo ""
echo "✨ Platform is starting up!"
echo ""
echo "🌐 Access your platform:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📝 View logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
echo ""
