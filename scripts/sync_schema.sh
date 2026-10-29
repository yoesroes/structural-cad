#!/usr/bin/env bash
# Salin skema kanonik → salinan paket (wajib sama sebelum release/CI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/schemas/scad.schema.json"
DST="$ROOT/src/scad/data/scad.schema.json"
mkdir -p "$(dirname "$DST")"
cp "$SRC" "$DST"
echo "Disalin: $SRC → $DST"
cmp -s "$SRC" "$DST" && echo "OK (identik)"
