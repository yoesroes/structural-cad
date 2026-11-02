# Laporan P3 / P3b — Validator arrangement, ekspresi, tipe grup

**Tanggal:** 2026-10-31  
**Repo:** Structural CAD (`develop-p3` + P2c + P3 + P3b)

## Ruang lingkup

- **P3:** `EXPR`, `ARR_BAD` (polar/linear), `TYPE_MISMATCH`, `start_angle_deg`, bungkus `ExprError`
- **P3b:** bersihkan validate, ketatkan nama ekspresi + string konstanta, ketahanan, mutation check, dokumentasi kode galat

## Berkas diubah (P3 + P3b)

| Berkas di repo | Isi |
|----------------|-----|
| `src/scad/expr.py` | `check_expression`; string hanya argumen d_of/zone_length/shape_param; kwargs ditolak |
| `src/scad/validate.py` | EXPR/ARR_BAD/TYPE_MISMATCH; nama runtime; blok ZONE_REST_OVERRIDE rapi; count polar tahan konversi |
| `src/scad/placement.py` | `start_angle_deg`; polar `count < 1` → ValueError |
| `tests/core/test_expr.py` | Unit `check_expression` |
| `tests/core/test_validate.py` | EXPR ketat, ARR_BAD, TYPE_MISMATCH, ketahanan, paritas nama |
| `tests/core/test_core_audit_regressions.py` | (dari P3) |
| `tests/engine/test_engine_audit_regressions.py` | T3 polar / start_angle; S7 ExprError |
| `tasks/00_KONTEKS.md` | `TYPE_MISMATCH` di daftar kode galat |
| `docs/reports/P3_validator_arrangement_ekspresi.md` | Laporan ini |

**Tidak** menyertakan `LAPORAN_P3.md` / `README_P3.md` di root (jangan di-commit bila masih ada di working tree; hapus dulu).

## Perilaku kunci (P3b)

1. **Nama ekspresi** mengikuti runtime placement: `params` elemen + `d`, `pi`, `diameter`, `cover`. **Tanpa** A/B/C/height/width/length/r global.
2. **Konstanta string** hanya sebagai argumen `d_of` / `zone_length` / `shape_param`.
3. **ZONE_REST_OVERRIDE:** id rest dihitung sekali per grup; `z.get('id')`; guard `isinstance(zone_lengths, dict)`; pesan menyebut pile.
4. **ARR_BAD polar:** `by != count` atau `count` tidak bisa di-int atau `< 1` → issue, bukan exception.
5. **placement polar:** `count < 1` → `ValueError` (mesin tidak menghasilkan 0 batang diam-diam).
6. Jalur publik `validate_document`: rebar/zona bukan dict ditangani lewat skema / skip aman. (Helper internal lama `_cross_checks` masih bisa AttributeError bila dipanggil langsung dengan rebar string; tidak terjangkau dari aplikasi.)

## Mutation check (P3b) — keluaran nyata

| Mutasi | Tes yang gagal |
|--------|----------------|
| `check_expression` selalu `return []` | `test_unknown_expression_is_expr_error`, `test_hardcoded_shape_letters_are_expr_on_extend_start`, `test_check_expression_unknown_name` |
| Matikan cabang ARR_BAD polar di validator (`if False`) | `test_polar_spacing_is_arr_bad`, `test_polar_count_invalid_is_arr_bad_not_exception` |
| Matikan ARR_BAD linear | `test_linear_non_z_axis_is_arr_bad` |
| Matikan TYPE_MISMATCH | `test_group_definition_type_mismatch_is_error` |
| `start_angle_deg` → `start_angle` di placement | `test_polar_start_angle_deg_changes_first_origin` |
| Hapus / matikan `if count < 1: raise ValueError(...)` di placement polar | `test_polar_spacing_rejected_with_arr_bad_and_build_raises` (**DID NOT RAISE** pada `build_bar_groups`) |

Semua mutasi dipulihkan setelahnya.

## Verifikasi nyata

```text
pytest tests: 244 passed, 1 skipped, 3 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 28 passed, 0 failed
```

Xfail tersisa: **S2×2**, **T4** (bukan scope P3).

Catatan angka: baseline P2c = 228; P3 menambah tes + membuka xfail T3/S7; P3b menambah unit/paritas → **244** lulus (bukan 235; target 235 adalah perkiraan sebelum tes P3b).

## Asumsi / isu terbuka

- Nama shape-param (A, B, lap) adalah **kunci** di `shape_params`, bukan variabel bebas runtime; ekspresi nilai shape param memakai `diameter`/`cover`/`d`/params.
- Variabel `r` sengaja ditolak sampai D5/S8 (bentuk 37) diputuskan.
- Celah `update-from-source` tetap P6.
