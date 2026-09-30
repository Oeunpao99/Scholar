#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting Scholar API server..."
# Behind nginx: trust its X-Forwarded-* headers so client IPs are real.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
