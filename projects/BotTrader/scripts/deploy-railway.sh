#!/bin/bash

# BotTrader Railway Deployment Script with TimescaleDB
# This script deploys the complete stack to Railway

set -e

echo "🚀 Deploying BotTrader with TimescaleDB to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Login to Railway
echo "📝 Logging into Railway..."
railway login

# Link to project (create if doesn't exist)
echo "🔗 Linking to Railway project..."
railway link

# Set environment variables from .env.railway
echo "⚙️ Setting environment variables..."
railway variables set $(cat .env.railway | grep -v '^#' | xargs)

# Generate a secure password for PostgreSQL if not set
if [ -z "$RAILWAY_POSTGRES_PASSWORD" ]; then
    export RAILWAY_POSTGRES_PASSWORD=$(openssl rand -base64 32)
    railway variables set RAILWAY_POSTGRES_PASSWORD=$RAILWAY_POSTGRES_PASSWORD
    echo "🔐 Generated PostgreSQL password"
fi

# Deploy the services
echo "📦 Deploying services to Railway..."
railway up

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 30

# Check deployment status
echo "✅ Checking deployment status..."
railway status

# Get service URLs
echo "🌐 Service URLs:"
railway open

echo "✨ Deployment complete!"
echo ""
echo "📊 Next steps:"
echo "1. Check the Railway dashboard for service status"
echo "2. Verify TimescaleDB is running: railway logs timescaledb"
echo "3. Run tests: make test-integration"
echo "4. Monitor logs: railway logs -f"
echo ""
echo "🔧 Useful commands:"
echo "  railway logs timescaledb    - View database logs"
echo "  railway logs bottrader-app  - View application logs"
echo "  railway restart             - Restart all services"
echo "  railway down                - Stop all services"