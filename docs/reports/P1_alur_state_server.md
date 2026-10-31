# Laporan P1 / P1b / P1c — Alur state server

Tanggal: 2026-10-31  
Repo: Structural CAD (pasca H5 + P0/P1/P1b/P1c)

## Ruang lingkup

- **T1** — Alur state server dan edit pile berurutan (termasuk path yang dibuka)
- **T2** — Penolakan edit zona/kedalaman tidak feasibel
- **S1** — `add_rebar` tidak meracuni state sesi
- **P1b** — `_commit` project tanpa judul; filter error resolve per pile; konsolidasi tes; arah T3; S2 save-as
- **P1c** — Mutation check T2 (gerbang resolve); tes lawan filter; fail-closed pointer; unit helper path; rapikan laporan

Tidak ada perubahan schema, engine geometri, atau format project JSON.  
`save_project` / Simpan project tanpa judul **tidak** diubah (backlog P8).

## Perubahan implementasi

### `_commit` (P1 + P1b)

Urutan: validasi → simpan → baru `_set_current`.

Bila `CURRENT_PATH` sebelumnya `None` dan target fallback `DATA_ROOT/project.json`, dokumen tetap ditulis tetapi **`CURRENT_PATH` tetap `None`** dan **`DIRTY` tetap `True`**. Path dan `DIRTY=False` hanya diset bila target sama dengan `CURRENT_PATH` yang sudah ada.

### `add_rebar` (S1)

`copy.deepcopy` dari dokumen sesi; commit hanya lewat `_commit`.

### `_apply_pile_op_and_respond` (T1/T2 + P1b)

Memakai `_commit`. Error resolve disaring lewat `_resolve_errors_for_pile`.

### `_pile_ids_from_issue_path` (P1b + P1c)

Pointer `/groups/{gi}/instances/{ii}` dipetakan ke id pile.  
Pointer rusak, indeks di luar jangkauan, atau id hilang → **`None`** (fail-closed: dianggap global, memblokir). Tidak membuang issue dengan `set()` kosong.

## Tes

### Fixture

Fixture `ui_server` (dari P0 di `tests/conftest.py`) memulihkan seluruh global server. Fixture `http_workspace` dihapus pada P1b.

### Regression aktif

| ID | Tes | File |
|----|-----|------|
| T1 | Dua edit depth, tiga operasi berurutan, path dibuka | `tests/ui/test_state_regression.py` |
| T2 | Depth 5000 pada P1-6 → 400 + `ZONE_DEPTH_SHORT` | sama |
| S1 | Rebar invalid → 400, sesi utuh | sama |
| P1b | Untitled: path None + dirty True; save-as mengisi path | sama |
| P1b/P1c | P1-6 infeasibel; edit P1-1 → 200 | sama |
| P1c | P1-6 infeasibel; edit P1-6 → 6000 → 400 | sama |
| P1c | P1-6 infeasibel; edit P1-6 → 30000 → 200 (override boleh terpangkas ke default) | sama |
| P1c | Unit `_pile_ids_from_issue_path` (valid, definisi, OOB, kosong) | sama |

`test_update_from_source_invalid_zone_cancels` menunjuk pile **`P1-1`** secara eksplisit.

### Xfail (strict)

- S2 ×2 (save + save-as), S6, S7, T3 ×2, T4

## Mutation check

### 1) Gating resolve (P1c — bukti T2)

Mutasi: komentari blok `if resolve_errors:` di `_apply_pile_op_and_respond` (gerbang resolve mati; commit tetap jalan).

```text
pytest ...::test_t2_unfeasible_depth_is_rejected_without_disk_change
# MUTASI: FAILED — assert 200 == 400
# (POST /api/pile/P1-6/depth dengan depth 5000 diterima)
# PULIH: PASSED
```

### 2) `_commit` / path (P1b)

Mutasi: selalu tulis `DATA_ROOT/project.json` dan `_set_current(path=target)` tanpa menghormati untitled.

```text
test_t1_opened_path_is_edit_target — FAILED (edit tidak masuk file workspace)
test_untitled_project_keeps_path_none_after_pile_edit — FAILED (CURRENT_PATH terisi scratch)
# PULIH: keduanya PASSED
```

Catatan: mutasi (2) tidak mematahkan T2 karena gerbang resolve masih aktif — itu sebab P1c menambah mutasi (1).

## Berkas yang berubah (P1b + P1c)

- `src/scad_ui/server.py`
- `tests/ui/test_state_regression.py`
- `tests/ui/test_file_api.py`
- `docs/reports/P1_alur_state_server.md`

`tests/conftest.py` tidak diubah pada P1b/P1c (milik P0). Laporan jejak lama T1–T2/P0/P1 di `docs/reports/` tetap ada; acuan status adalah berkas ini.

## Verifikasi

```bash
PYTHONPATH=src python -m pytest tests -q
PYTHONPATH=src python tools/check_examples.py
node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts
```

Hasil aktual (P1c):

```text
pytest tests: 212 passed, 1 skipped, 7 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 26 passed, 0 failed
```

## Asumsi dan isu terbuka

- Field `pile` pada issue resolve ditunda ke **P2**.
- `save_project` untitled → path scratch: backlog **P8**.
- S2, S6, S7, T3, T4: backlog P2/P3/P5/P7.
- CadQuery tidak terpasang → 1 skip di `test_generic.py`.
