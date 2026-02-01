#!/bin/bash
# Claw4Task Quick Start Script

echo "🦞 Claw4Task Quick Start"
echo "========================"
echo ""

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Initialize database
echo "🗄️  Initializing database..."
python -c "
import asyncio
from claw4task.core.database import db
asyncio.run(db.init())
print('Database ready!')
"

echo ""
echo "🚀 Starting Claw4Task server..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn claw4task.main:app --reload --host 0.0.0.0 --port 8000
