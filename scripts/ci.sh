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
# Contoh engine harus sinkron dengan examples/
EX_P1="$ROOT/examples/P1.project.json"
EX_P1_PKG="$ROOT/src/scad_engine/examples/P1.project.json"
EX_PC="$ROOT/examples/pilecap.json"
EX_PC_PKG="$ROOT/src/scad_engine/examples/pilecap.json"
if [[ ! -f "$EX_P1" || ! -f "$EX_P1_PKG" ]] || ! cmp -s "$EX_P1" "$EX_P1_PKG"; then
  echo "GAGAL: P1.project.json tidak sinkron (jalankan scripts/sync_examples.sh)"; FAIL=1
else echo "==> contoh P1 OK"; fi
if [[ ! -f "$EX_PC" || ! -f "$EX_PC_PKG" ]] || ! cmp -s "$EX_PC" "$EX_PC_PKG"; then
  echo "GAGAL: pilecap.json tidak sinkron (jalankan scripts/sync_examples.sh)"; FAIL=1
else echo "==> contoh pilecap OK"; fi
python3 -c "import pytest" 2>/dev/null || { echo "GAGAL: pytest"; FAIL=1; }
python3 -m pytest tests || FAIL=1
python3 tools/check_examples.py || FAIL=1
if command -v node >/dev/null 2>&1; then
  node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts || FAIL=1
else
  echo "LEWATI: node tidak ada"
fi
[[ "$FAIL" -eq 0 ]] && echo "==> CI selesai (lulus)." || { echo "==> CI GAGAL."; exit 1; }
