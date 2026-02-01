#!/bin/bash
#
# Stop AI Analytics Platform
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🛑 Stopping AI Analytics Platform..."

cd "$PROJECT_ROOT"

docker-compose down

echo ""
echo "✅ Platform stopped"
