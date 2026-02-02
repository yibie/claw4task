#!/bin/bash
# Migrate database on Fly.io without losing data

set -e

echo "🦞 Claw4Task Database Migration"
echo "================================"
echo ""

# Check if flyctl is available
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Please install it first."
    exit 1
fi

echo "📦 Step 1: Creating backup..."
fly ssh console --app claw4task --command "cp /data/claw4task.db /data/claw4task.db.backup.$(date +%Y%m%d_%H%M%S)" 
echo "✅ Backup created"
echo ""

echo "📦 Step 2: Copying migration script..."
fly sftp shell --app claw4task << 'EOF'
put migrate_db.py /data/migrate_db.py
EOF
echo "✅ Migration script uploaded"
echo ""

echo "📦 Step 3: Running migration..."
fly ssh console --app claw4task --command "cd /data && python3 migrate_db.py"
echo ""

echo "📦 Step 4: Verifying migration..."
fly ssh console --app claw4task --command "sqlite3 /data/claw4task.db '.schema tasks' | grep -E 'deliverables|examples|complexity_level'"
echo ""

echo "✅ Migration complete!"
echo ""
echo "📝 Your data is safe. New columns added with default values."
echo "🔄 Restart the app to apply changes:"
echo "   fly apps restart claw4task"
