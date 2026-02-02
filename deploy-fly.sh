#!/bin/bash
# Claw4Task Fly.io Deployment Script

set -e

# Add fly to PATH
export PATH="$HOME/.fly/bin:$PATH"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🦞 Claw4Task Fly.io Deployment${NC}"
echo "=============================="
echo ""

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo -e "${YELLOW}🔑 Please login to Fly.io first:${NC}"
    echo "   fly auth login"
    exit 1
fi

echo -e "${GREEN}✅ Logged in as:$(fly auth whoami)${NC}"
echo ""

# Check if volume exists
echo "📦 Checking persistent volume..."
if ! fly volumes list --app claw4task 2>/dev/null | grep -q "data"; then
    echo -e "${YELLOW}Creating volume 'data'...${NC}"
    fly volumes create data --app claw4task --region sin --size 1
else
    echo -e "${GREEN}✅ Volume exists${NC}"
fi
echo ""

# Deploy
echo "🚀 Deploying..."
fly deploy --app claw4task

echo ""
echo -e "${GREEN}==============================${NC}"
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "🌐 Your app is live at:"
echo -e "   ${YELLOW}https://claw4task.fly.dev${NC}"
echo ""
echo "📊 Check status:"
echo "   fly status --app claw4task"
echo ""
echo "📜 View logs:"
echo "   fly logs --app claw4task"
echo ""
