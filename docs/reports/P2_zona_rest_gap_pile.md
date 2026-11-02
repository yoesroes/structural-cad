# Laporan P2 / P2b — Override zona rest, ZONE_GAP, issue per pile

**Tanggal:** 2026-10-31  
**Repo:** Structural CAD

## Ruang lingkup

- **S6 / P2** — Tolak *set* override zona `rest`; `ZONE_GAP` warning; field `pile` pada issue instance
- **P2b** — Reset zona rest diizinkan jika ada override; skip resolve `pile_cap`; paritas TS + golden; tes P1c diperketat; E2E ZONE_GAP

## Perubahan (berkas diubah)

| Berkas | Isi |
|--------|-----|
| `src/scad/ops.py` | Set rest ditolak; reset rest hanya jika override ada |
| `src/scad/resolve.py` | Field `pile`; `ZONE_GAP`; skip grup `pile_cap` |
| `src/scad/zones.py` | `ZONE_REST_OVERRIDE` (P2) |
| `src/scad/validate.py` | Override rest di instance (P2) |
| `src/scad_ui/server.py` | Filter `pile`; docstring fail-closed |
| `web/src/commands/apply.ts` | Paritas set/reset rest |
| `web/src/commands/ops_golden.test.ts` | Kasus rest melempar error |
| `examples/ops_golden.json` | +`set_rest_zone_error`, +`reset_rest_zone_without_override_error` |
| `tests/core/test_core_audit_regressions.py` | S6, reset-with-override, skip pile_cap, ZONE_GAP |
| `tests/ui/test_state_regression.py` | Path mapping P1c, API rest, ZONE_GAP resolve |
| `docs/UI.md`, `tasks/00_KONTEKS.md` | Kode galat |
| `docs/reports/P2_zona_rest_gap_pile.md` | Laporan ini |

## Mutation check (P2b)

1. **Reset rest dengan override:** mutasi ke “selalu tolak rest pada reset” → `test_rest_zone_reset_clears_existing_override` **FAILED** (`ValueError`). Pulih: PASSED.
2. **Skip pile_cap:** mutasi `if False` pada skip → `test_resolve_skips_pile_cap_without_depth_error` **FAILED** (`ZONE_DEPTH_SHORT` pada PC-1). Pulih: PASSED.
3. **Set rest:** hapus cek `zone_is_rest` pada set → `test_rest_zone_override_is_rejected` **FAILED** (DID NOT RAISE). Pulih: PASSED.

## Verifikasi nyata

```text
pytest tests: 225 passed, 1 skipped, 6 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 28 passed, 0 failed
```

Xfail tersisa: S2×2, S7, T3×2, T4.

## Asumsi

- Golden sukses “reset rest + override” diuji di Python unit (dokumen P1 tidak punya override Z3 bawaan); golden JSON memuat dua kasus error rest.
- Validator tetap menolak dokumen dengan override rest tersimpan; perbaikan lewat `reset_pile_zone_length` dulu.

---

# Laporan P2c — Kunci aturan D6 (zona rest tidak boleh di-override)

**Tanggal:** 2026-10-31  
**Repo:** Structural CAD (`develop-p3`)

## Ruang lingkup

Hanya dokumentasi dan tes. **Tidak ada perubahan perilaku kode produksi.**

Aturan yang dikunci (D6 = opsi B):
- Override pada zona `rest` tidak boleh dibuat lewat edit apa pun.
- Dokumen yang sudah memuatnya tetap invalid: ditolak saat open, save, save-as (HTTP 400).
- Tidak ada pemangkasan otomatis.
- `reset_pile_zone_length` pada zona rest hanya untuk skrip/tes.
- Jalur `update-from-source` ditutup di P6, bukan di sini.

## Berkas diubah

| Berkas | Isi |
|--------|-----|
| `docs/UI.md` | Bagian kode galat zona / keputusan D6 |
| `tasks/00_KONTEKS.md` | Keputusan #8 D6 = opsi B + alasan; kode `ZONE_REST_OVERRIDE` / `ZONE_GAP` |
| `tests/ui/test_state_regression.py` | Tes open / save / save-as / set rest tidak menulis disk |
| `docs/reports/P2_zona_rest_gap_pile.md` | Laporan P2c ini |

## Tes baru (P2c)

- `test_open_rejects_rest_override_document` — open berkas invalid → 400, `CURRENT_DOC` tidak berubah
- `test_save_and_save_as_reject_rest_override_document` — save & save-as → 400, tidak ada berkas ditulis
- `test_api_set_rest_zone_does_not_write_disk` — set zona rest via API → 400, disk tidak berubah
- (sudah ada) reset zona rest tanpa override → error; validate instance → `ZONE_REST_OVERRIDE`

## Mutation check (P2c)

Patch mutasi: di `src/scad/validate.py`, ganti kondisi `if zid in rest_zone_ids:` menjadi `if False and zid in rest_zone_ids:` (mematikan pemeriksaan `ZONE_REST_OVERRIDE`).

```text
# Setelah mutasi:
FAILED tests/ui/test_state_regression.py::test_open_rejects_rest_override_document
  AssertionError: assert 200 == 400
FAILED tests/ui/test_state_regression.py::test_save_and_save_as_reject_rest_override_document
  AssertionError: assert 200 == 400

# Setelah dipulihkan:
PASSED tests/ui/test_state_regression.py::test_open_rejects_rest_override_document
PASSED tests/ui/test_state_regression.py::test_save_and_save_as_reject_rest_override_document
```

## Verifikasi nyata (P2c)

```text
pytest tests: 228 passed, 1 skipped, 6 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 28 passed, 0 failed
```

Xfail tersisa: S2×2, S7, T3×2, T4 (tidak berubah).

## Asumsi / isu terbuka

- Tidak ada perubahan kode produksi; perilaku penolakan sudah ada sejak P2 (`load_document` + `_validation_errors` / `_save_validated`).
- Celah `update-from-source` tetap backlog P6 sesuai prompt.
