# Laporan H5 — Sengkang bored pile (cincin Z0 + spiral menerus by_zone)

**Tanggal:** 2026-10-28  
**Working directory:** `artifacts/cad_h3`  
**Paket:** `artifacts/cad_h3_revisi.zip`

## Ringkasan

H5 mengubah sengkang bored pile:

| Zona | Perilaku |
|------|----------|
| **Z0** (atas COF) | Cincin **B5** (RING), spasi = pitch spiral Z1 |
| **Z1–Z3** (bawah COF) | Satu spiral **B2** menerus, pitch `by_zone` |

**B3 dihapus** (digabung ke B2). **B4** tetap (longitudinal Z3).

## Berkas diubah

| Path | Perubahan |
|------|-----------|
| `src/scad/expr.py` | Fungsi diizinkan: `shape_param` |
| `src/scad/shapes.py` | `by_zone`, heliks multi-pitch, panjang potong per zona |
| `src/scad/placement.py` | `shape_param`, spiral by_zone, linear `range` |
| `src/scad_engine/from_v1.py` | `PileEnv.rebars_by_id` untuk `shape_param` |
| `schemas/scad.schema.json` + salinan data | `NumOrByZone`; arrangement `range` / spacing ekspresi |
| `examples/P1.project.json`, `BP_D1200.elem.json` | Data H5, hash baru |
| `examples/shapes.builtin.json` | R87 **version 2** |
| `examples/expected_zones.P1.json` | Z0 = 1280 |
| `tests/engine/test_from_v1.py` | Angka H5 |
| `tests/core/test_h5_sengkang.py` | **Baru** |
| `tests/core/test_io.py` | Hash EXPECTED |
| `tools/build_examples.py` | R87 v2 |

## Uji

```bash
cd cad_h3
PYTHONPATH=src pytest tests/engine/test_from_v1.py tests/core/test_h5_sengkang.py -q
# 17 passed

PYTHONPATH=src pytest -q
# 200 passed, 1 skipped
```

## Kriteria H5 (P1-1, diverifikasi)

| Item | Target | Hasil |
|------|--------|-------|
| B5 cincin | 17 @ z=75…1275; cut ≈ 3888.4 | OK |
| B2 spiral total | 466761.1 ± 0.5 | OK |
| B1 | 56 × 12280 | OK |
| B4 | 28 × 20280 | OK |
| Clash mentah | 0 pasangan | OK |
| LEN_MISMATCH | tidak | OK |
| RULE_SPACING B1 | ada | OK |

P1-2 spiral ≈ 423264.7; P1-8 Z2=7000 → komponen Z2 35 putaran (total spiral ≈ 417866 karena Z3 mengecil).

## Asumsi

1. `shape_param('B2','B','Z1')` membaca pitch Z1 dari `by_zone`; argumen zona opsional (default Z1).
2. Spiral by_zone: satu heliks menerus; sudut dilanjutkan antarzona.
3. Tidak ada penyaringan clash berbasis nama.

## Tidak diklaim

- Sengkang di luar pola contoh H5.
- UI khusus editor `by_zone` (data JSON saja).
