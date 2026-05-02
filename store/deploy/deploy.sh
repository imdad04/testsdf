#!/bin/bash
# Pull + rebuild + restart on the VPS. Idempotent.
set -e
cd "$(dirname "$0")/.."

git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs --tail=50 backend
