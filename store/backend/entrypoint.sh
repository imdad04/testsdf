#!/bin/sh
set -e

echo "[entrypoint] running migrations..."
alembic upgrade head

if [ "$SEED_ON_START" = "1" ]; then
    echo "[entrypoint] seeding..."
    python -m scripts.seed || true
fi

echo "[entrypoint] starting app..."
exec python -m app.main
