#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/configure.py
docker compose up -d --build
echo "Open http://localhost:${WEB_PORT:-3000}/review. Draft builds run in the Blender worker."
