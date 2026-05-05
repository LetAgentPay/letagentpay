#!/bin/bash
set -e

# Migrations run separately before container restart (zero-downtime deploy).
# For local/self-hosted: pass --migrate flag to run migrations here.
if [ "$1" = "--migrate" ]; then
    echo "Running core database migrations..."
    cd /app && python -m alembic upgrade head
    # Enterprise migrations (if ee/ exists)
    if [ -f ee/alembic/alembic.ini ]; then
        echo "Running enterprise database migrations..."
        python -m alembic -c ee/alembic/alembic.ini upgrade head
    fi
fi

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 30 --proxy-headers --forwarded-allow-ips='*'
