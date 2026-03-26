#!/usr/bin/env bash
set -euo pipefail

# F1 Engineering Dashboard — Backfill a Race Weekend
# Usage: ./scripts/backfill_weekend.sh <season> <race>
# Example: ./scripts/backfill_weekend.sh 2026 R05

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <season> <race>"
  echo "Example: $0 2026 R05"
  exit 1
fi

SEASON="$1"
RACE="$2"

echo "=== Backfilling Race Weekend: $SEASON $RACE ==="
echo ""

# Check API is running
if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  echo "ERROR: API is not running. Run ./scripts/bootstrap_local.sh first."
  exit 1
fi

# Check Redis is running
if ! docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
  echo "ERROR: Redis is not running."
  exit 1
fi

echo "[1/4] Dispatching ingest jobs..."
# TODO: Replace with actual scheduler dispatch when implemented
echo "  Would dispatch: ingest -> annotate -> recon -> meshops"
echo "  Season: $SEASON, Race: $RACE"

echo ""
echo "[2/4] Ingesting evidence (placeholder)..."
echo "  Ingest service will process media and articles for $RACE"

echo ""
echo "[3/4] Running annotation (placeholder)..."
echo "  Annotate service will generate hypotheses and callouts"

echo ""
echo "[4/4] Running 3D pipeline (placeholder)..."
echo "  Recon and MeshOps services will process 3D assets"

echo ""
echo "=== Backfill dispatched for $SEASON $RACE ==="
echo "Monitor progress at: http://localhost:3000"
echo ""
