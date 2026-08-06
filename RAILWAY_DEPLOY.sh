#!/bin/bash

# 🚂 Railway Deployment Script for Telegram Games Mini App

set -e

echo "🚀 Telegram Games Mini App - Railway Deployment"
echo "=================================================="

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Step 1: Login to Railway
echo ""
echo "📝 Step 1: Login to Railway"
echo "You will be redirected to browser. Please authenticate."
railway login

# Step 2: Create/link project
echo ""
echo "🔗 Step 2: Link Railway project"
echo "If you don't have a Railway project, follow the prompt to create one."
railway link

# Step 3: Add backend service
echo ""
echo "📦 Step 3: Adding Backend service"
cd backend

# Deploy backend with Dockerfile
railway up --detach

cd ..

# Step 4: Add MongoDB service
echo ""
echo "🗄️  Step 4: Adding MongoDB"
echo "The MongoDB database will be added automatically via Railway dashboard"
echo "Visit https://railway.app and add MongoDB plugin to your project"

# Step 5: Configure environment variables
echo ""
echo "⚙️  Step 5: Setting environment variables"
echo "You need your Telegram Bot Token. Get it from @BotFather"
echo ""
read -p "Enter your Telegram Bot Token: " TELEGRAM_BOT_TOKEN
export TELEGRAM_BOT_TOKEN

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Bot token is required!"
    exit 1
fi

echo ""
echo "Setting environment variables in Railway..."
railway variable set TELEGRAM_BOT_TOKEN "$TELEGRAM_BOT_TOKEN"
railway variable set NODE_ENV "production"

read -p "Enter your Vercel frontend domain (e.g., my-app.vercel.app): " FRONTEND_DOMAIN
railway variable set CORS_ORIGIN "https://$FRONTEND_DOMAIN"
railway variable set WEB_APP_URL "https://$FRONTEND_DOMAIN"

echo "✅ Environment variables set!"
echo ""

# Step 6: Get Backend URL
echo ""
echo "🎯 Step 6: Get Backend URL"
echo "Backend URL:"
railway open

echo ""
echo "✅ Backend deployment to Railway complete!"
echo ""
echo "Next steps:"
echo "1. Copy the backend URL from above"
echo "2. Deploy frontend to Vercel"
echo "3. Update REACT_APP_WS_URL and REACT_APP_API_URL in Vercel"
echo "4. Register Web App URL in Telegram BotFather"
echo ""
