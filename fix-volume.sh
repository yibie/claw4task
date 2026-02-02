#!/bin/bash
# Fix volume issue for claw4task

export PATH="$HOME/.fly/bin:$PATH"

echo "🦞 Fixing Volume Issue"
echo "======================"
echo ""

# Check current app
echo "📱 Current app: claw4task"

# Create volumes in ams region (as required by error)
echo ""
echo "📦 Creating volumes in ams region..."
fly volumes create data --app claw4task --region ams --size 1
fly volumes create data --app claw4task --region ams --size 1

echo ""
echo "✅ Volumes created!"
echo ""
echo "🚀 Now deploy with:"
echo "   fly deploy --app claw4task"
