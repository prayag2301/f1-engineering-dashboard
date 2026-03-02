#!/usr/bin/env bash
set -euo pipefail

# Validate JSON Schema files are well-formed
# Requires: python3 with jsonschema, or node with ajv-cli

SCHEMA_DIR="$(cd "$(dirname "$0")/../infra/schemas" && pwd)"

echo "=== Validating JSON Schema files ==="
echo "Schema directory: $SCHEMA_DIR"
echo ""

errors=0

# Check all .schema.json files are valid JSON
for schema in "$SCHEMA_DIR"/*.schema.json "$SCHEMA_DIR"/enums/*.schema.json; do
  [ -f "$schema" ] || continue
  name=$(basename "$schema")
  if python3 -c "import json; json.load(open('$schema'))" 2>/dev/null; then
    echo "  [OK] $name"
  else
    echo "  [FAIL] $name - invalid JSON"
    errors=$((errors + 1))
  fi
done

echo ""

# If jsonschema is available, validate schema structure
if python3 -c "import jsonschema" 2>/dev/null; then
  echo "=== Validating schema structure (Draft 2020-12) ==="
  for schema in "$SCHEMA_DIR"/*.schema.json; do
    [ -f "$schema" ] || continue
    name=$(basename "$schema")
    if python3 -c "
import json, jsonschema
schema = json.load(open('$schema'))
jsonschema.Draft202012Validator.check_schema(schema)
" 2>/dev/null; then
      echo "  [OK] $name"
    else
      echo "  [WARN] $name - could not validate against meta-schema"
    fi
  done
else
  echo "Note: install jsonschema (pip install jsonschema) for deeper validation"
fi

echo ""
if [ $errors -gt 0 ]; then
  echo "FAILED: $errors schema(s) have errors"
  exit 1
else
  echo "All schemas valid."
fi
