# Paket spesifikasi dan tugas — Structural CAD v1

Isi:
- `schemas/scad.schema.json` — JSON Schema (satu berkas, entri menurut `kind`)
- `examples/` — `BP_D1200.elem.json`, `P1.project.json` (9 bored pile, 3 di antaranya menimpa kedalaman/zona), `shapes.builtin.json`, `expected_zones.P1.json`
- `web/src/types.ts` — kontrak tipe TypeScript
- `docs/mockup/` — mockup layar (HTML statis)
- `tasks/` — `00_KONTEKS.md` (WAJIB dibaca setiap AI) dan 10 prompt tugas T01-T10
- `tools/` — `check_examples.py` (jalankan: `python tools/check_examples.py`), `mini_validate.py`, `build_examples.py`

## Cara membagi
Berikan ke tiap AI: folder ini + `00_KONTEKS.md` + SATU file tugas. Tugas saling lepas (hanya memakai kontrak), jadi bisa dikerjakan paralel.

| Tugas | Isi | Bergantung pada kontrak |
|---|---|---|
| T01 | evaluator ekspresi | - |
| T02 | kanonik, hash, I/O berkas | - |
| T03 | validator dokumen | T02 (hash) |
| T04 | penyelesai zona | - |
| T05 | plugin elemen (metadata) | - |
| T06 | server lokal + OpenAPI | T02, T03, T04 |
| T07 | kerangka UI statis | - |
| T08 | tabel pile interaktif | types.ts |
| T09 | form dari JSON Schema | skema |
| T10 | registri perintah + konsol | types.ts |

Urutan penggabungan yang disarankan: T01, T02, T04, T05 -> T03 -> T06; T07, T09, T10 -> T08.

## Perbedaan dari dokumen spesifikasi
- Pemanggilan `zone('Z1').length` diganti fungsi `zone_length('Z1')` (spesifikasi melarang akses atribut).
- Keputusan baru: antar pile hanya `depth_below_cof` dan `zone_lengths` yang boleh berbeda (skema menolak yang lain).

## Status verifikasi
Skema dan contoh diuji dengan `tools/mini_validate.py` (validator minimal buatan sendiri, BUKAN paket `jsonschema`): contoh lolos, 11 mutasi salah ditolak. Skema belum dijalankan dengan `jsonschema` resmi; tugas T03 akan melakukannya.
