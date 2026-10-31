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
