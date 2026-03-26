#!/usr/bin/env bash
set -euo pipefail

# F1 Engineering Dashboard — Local Bootstrap
# Brings up the full development environment from scratch.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "=== F1 Engineering Dashboard — Local Bootstrap ==="
echo ""

# Step 1: Start infrastructure services
echo "[1/5] Starting infrastructure (postgres, redis, minio)..."
docker compose up -d db redis minio
echo "  Waiting for services to be healthy..."
sleep 3

# Step 2: Start API
echo "[2/5] Starting API server..."
docker compose up -d api
echo "  Waiting for API to be ready..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "  API is ready."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "  ERROR: API did not start within 30 seconds."
    docker compose logs api
    exit 1
  fi
  sleep 1
done

# Step 3: Run DB migrations / create tables
echo "[3/5] Creating database tables..."
docker compose exec -T api python -c "
from backend.database import engine, Base
from backend.models.models import *
Base.metadata.create_all(bind=engine)
print('  Tables created successfully.')
"

# Step 4: Seed database
echo "[4/5] Seeding database..."
SEED_RESULT=$(curl -sf -X POST http://localhost:8000/api/v1/seed/)
echo "  $SEED_RESULT"

# Step 5: Start web frontend
echo "[5/5] Starting web frontend..."
docker compose up -d web

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "  API:     http://localhost:8000/docs"
echo "  Web:     http://localhost:3000"
echo "  MinIO:   http://localhost:9001 (f1admin / f1adminpass)"
echo "  Postgres: localhost:5432 (f1user / f1pass / f1dashboard)"
echo "  Redis:   localhost:6379"
echo ""
echo "To start worker services:"
echo "  docker compose --profile workers up -d"
echo ""
