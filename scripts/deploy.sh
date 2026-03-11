#!/bin/bash
# Deploy BEIET bot to Oracle Cloud VM
# Usage: ./scripts/deploy.sh

set -e

SERVER="opc@148.116.109.91"
KEY="$HOME/.ssh/oracle-beiet.key"

echo "🚀 Deploying BEIET bot..."

echo "1/2 Pushing to GitHub..."
git push origin main

echo "2/2 Updating server..."
ssh -i "$KEY" "$SERVER" bash << 'REMOTE'
cd beiet-tutor-bot
git fetch --all
git reset --hard origin/main
git clean -fd
sudo docker build -t beiet-bot .
sudo docker rm -f beiet-bot
sudo docker run -d --name beiet-bot --env-file .env -p 7860:7860 -v beiet-data:/app/data --restart unless-stopped beiet-bot bash start.sh
sudo docker logs --tail 20 beiet-bot
REMOTE

echo "✅ Deploy complete!"
