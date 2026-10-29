#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
FAIL=0
python3 -c "import jsonschema" 2>/dev/null || { echo "GAGAL: jsonschema"; FAIL=1; }
SCHEMA_ROOT="$ROOT/schemas/scad.schema.json"
SCHEMA_PKG="$ROOT/src/scad/data/scad.schema.json"
if [[ ! -f "$SCHEMA_ROOT" || ! -f "$SCHEMA_PKG" ]] || ! cmp -s "$SCHEMA_ROOT" "$SCHEMA_PKG"; then
  echo "GAGAL: skema tidak sinkron (schemas/ ↔ src/scad/data/)"; FAIL=1
else echo "==> skema OK"; fi
python3 -c "import pytest" 2>/dev/null || { echo "GAGAL: pytest"; FAIL=1; }
python3 -m pytest tests || FAIL=1
python3 tools/check_examples.py || FAIL=1
[[ "$FAIL" -eq 0 ]] && echo "==> CI selesai (lulus)." || { echo "==> CI GAGAL."; exit 1; }
