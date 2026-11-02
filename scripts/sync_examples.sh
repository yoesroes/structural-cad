#!/usr/bin/env bash
# Salin contoh kanonik examples/ → src/scad_engine/examples/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/src/scad_engine/examples"
cp "$ROOT/examples/P1.project.json" "$ROOT/src/scad_engine/examples/P1.project.json"
cp "$ROOT/examples/pilecap.json" "$ROOT/src/scad_engine/examples/pilecap.json"
echo "sync_examples: P1.project.json dan pilecap.json disalin."
