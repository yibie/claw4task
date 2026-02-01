#!/bin/bash
# Claw4Task Deployment Script for Fly.io

set -e

echo "🦞 Claw4Task Deployment Script"
echo "=============================="
echo ""

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Installing..."
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
fi

echo "✅ Fly CLI found"

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo "🔑 Please login to Fly.io"
    fly auth login
fi

echo "✅ Logged in as: $(fly auth whoami)"
echo ""

# Launch app if not exists
if ! fly status &> /dev/null; then
    echo "🚀 Creating app on Fly.io..."
    fly launch --name claw4task --region sin --no-deploy
else
    echo "✅ App already exists"
fi

# Check database
if ! fly postgres list | grep -q "claw4task-db"; then
    echo "🗄️  Creating PostgreSQL database..."
    fly postgres create --name claw4task-db --region sin
    fly postgres attach --app claw4task claw4task-db
else
    echo "✅ Database exists"
fi

echo ""
echo "🚢 Deploying..."
fly deploy

echo ""
echo "=============================="
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your app is live at:"
echo "   https://claw4task.fly.dev"
echo ""
echo "📊 Check status:"
echo "   fly status"
echo ""
echo "📜 View logs:"
echo "   fly logs"
echo ""
