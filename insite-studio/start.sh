#!/bin/bash
# Insite Studio - Start script

set -a
[ -f .env ] && source .env
set +a

echo "🚀 Starting Insite Studio..."
echo "📱 Telegram Bot Token: ${TELEGRAM_BOT_TOKEN:0:20}..."
echo "🔑 Gemini API Key: ${GOOGLE_AI_API_KEY:0:20}..."
echo ""
echo "📊 Running API server on port 9123..."
echo "🌐 Access: http://localhost:9123"
echo ""

python3 api_server.py
