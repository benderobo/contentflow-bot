#!/bin/bash

# ContentFlow Bot - Quick Start Script

set -e

echo "🚀 ContentFlow Bot Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your credentials"
    exit 1
fi

echo "✅ .env configuration found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker not found!"
    echo "📦 Please install Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

echo "✅ Docker found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose not found!"
    echo "📦 Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker Compose found"

# Start services
echo ""
echo "🐳 Starting Docker Compose services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if all services are running
echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ ContentFlow Bot is starting!"
echo ""
echo "📱 Telegram Bot: Look for @8660988275_bot"
echo "🌐 Dashboard: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "💾 Database: localhost:5432"
echo ""
echo "📖 View logs:"
echo "   docker compose logs -f bot"
echo ""
