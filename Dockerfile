FROM python:3.11-slim

WORKDIR /app

# System deps for aiosqlite, chromadb, and PyNaCl
RUN apt-get update && \
    apt-get install -y --no-install-recommends libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Persistent storage
RUN mkdir -p /app/data

# HF Spaces runs as user 1000 — ensure write access
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/user

EXPOSE 7860

CMD ["bash", "start.sh"]
