#!/bin/bash
# AI Analytics Platform - Mac Setup Script
# Run this in VS Code terminal (bash)

set -e  # Exit on error

echo "🚀 AI Analytics Platform Setup for Mac"
echo "========================================"

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install from: https://docs.docker.com/desktop/install/mac-install/"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install from: https://www.python.org/downloads/"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Install from: https://nodejs.org/"
    exit 1
fi

echo "✅ All prerequisites found"

# Get project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "📁 Project directory: $PROJECT_DIR"

# Step 1: Start infrastructure
echo ""
echo "🐳 Step 1: Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

echo "⏳ Waiting for database to initialize..."
sleep 15

# Verify demo data
echo "🔍 Verifying demo data..."
ORDER_COUNT=$(docker-compose exec -T postgres psql -U postgres -d aianalytics -t -c "SELECT COUNT(*) FROM demo.orders;" 2>/dev/null | xargs)

if [ "$ORDER_COUNT" -eq "38" ]; then
    echo "✅ Demo data loaded: $ORDER_COUNT orders"
else
    echo "⚠️  Demo data may not be fully loaded yet (found $ORDER_COUNT orders, expected 38)"
    echo "   Continuing anyway..."
fi

# Step 2: Backend setup
echo ""
echo "🐍 Step 2: Setting up Python backend..."
cd "$PROJECT_DIR/backend"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "   Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "   Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "   Installing dependencies (this may take 2-3 minutes)..."
pip install -r requirements.txt -q

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "   Creating .env file..."
    cat > .env << 'EOF'
# App settings
DEBUG=true
APP_NAME="AI Analytics Platform"

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aianalytics
REDIS_URL=redis://localhost:6379

# OpenAI - Add your key here
OPENAI_API_KEY=your-openai-key-here
OPENAI_MODEL=gpt-4-0125-preview

# Optional: Clerk Auth (can leave as placeholder for now)
CLERK_SECRET_KEY=sk_test_placeholder
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_placeholder
EOF
    echo "   ✅ .env file created. Edit it to add your OpenAI API key."
else
    echo "   ✅ .env file already exists"
fi

# Step 3: Frontend setup
echo ""
echo "⚛️  Step 3: Setting up Node.js frontend..."
cd "$PROJECT_DIR/frontend"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies (this may take 2-3 minutes)..."
    npm install
else
    echo "   ✅ Dependencies already installed"
fi

# Step 4: Summary
echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Add your OpenAI API key to backend/.env:"
echo "   OPENAI_API_KEY=sk-your-key-here"
echo ""
echo "2. Start the backend (in a new terminal):"
echo "   cd $PROJECT_DIR/backend"
echo "   source venv/bin/activate"
echo "   python -m app.main"
echo ""
echo "3. Start the frontend (in another terminal):"
echo "   cd $PROJECT_DIR/frontend"
echo "   npm run dev"
echo ""
echo "4. Open in browser:"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "5. Test the connection:"
echo "   curl http://localhost:8000/health"
echo ""
echo "📚 Documentation:"
echo "   - MVP-README.md - Quick start guide"
echo "   - STATUS.md - What's implemented"
echo "   - STREAMING.md - How streaming works"
echo ""
