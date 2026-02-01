#!/bin/bash
#
# Stop the direct-running services
#

PROJECT_ROOT="/Users/sam-bot/.openclaw/workspace/ai-analytics-platform"

echo "🛑 Stopping AI Analytics Platform..."

if [ -f "$PROJECT_ROOT/.backend.pid" ]; then
    kill $(cat "$PROJECT_ROOT/.backend.pid") 2>/dev/null && echo "✅ Backend stopped"
    rm -f "$PROJECT_ROOT/.backend.pid"
fi

if [ -f "$PROJECT_ROOT/.frontend.pid" ]; then
    kill $(cat "$PROJECT_ROOT/.frontend.pid") 2>/dev/null && echo "✅ Frontend stopped"
    rm -f "$PROJECT_ROOT/.frontend.pid"
fi

echo "✅ All services stopped"
