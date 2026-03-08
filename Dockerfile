FROM python:3.11-slim

WORKDIR /app

# System deps for aiosqlite, chromadb, and PyNaCl (voice)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest pytest-asyncio

# Copy source
COPY . .

# Persistent storage: SQLite DB + ChromaDB live here
# Mount a volume at /app/data for persistence across restarts
RUN mkdir -p /app/data

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default: run the Discord bot
CMD ["python", "-m", "bot.main"]
