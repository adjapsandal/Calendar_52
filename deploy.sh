#!/bin/bash
set -e

echo "==> Pulling latest changes..."
git pull origin main

echo "==> Building images..."
docker compose build --no-cache

echo "==> Running database migrations..."
docker compose run --rm backend alembic upgrade head

echo "==> Restarting services..."
docker compose up -d

echo "==> Cleaning up old images..."
docker image prune -f

echo "==> Done! App is running."
docker compose ps
