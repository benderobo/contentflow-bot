#!/bin/bash
# Insite Studio - Start script

set -a
[ -f .env ] && source .env
set +a

echo "🚀 Starting Insite Studio..."
[ -n "$TELEGRAM_BOT_TOKEN" ] && echo "📱 Telegram Bot: Configured" || echo "📱 Telegram Bot: NOT configured"
[ -n "$GOOGLE_AI_API_KEY" ] && echo "🔑 Gemini API: Configured" || echo "🔑 Gemini API: NOT configured"
echo ""
echo "📊 Running API server on port 9123..."
echo "🌐 Access: http://localhost:9123"
echo ""

python3 api_server.py
