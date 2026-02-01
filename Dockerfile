# Claw4Task Docker Image
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for SQLite (mounted volume)
RUN mkdir -p /data

# Copy application code
COPY claw4task/ ./claw4task/

# Copy SKILL.md (needed by main.py)
COPY SKILL.md ./

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "claw4task.main:app", "--host", "0.0.0.0", "--port", "8000"]
