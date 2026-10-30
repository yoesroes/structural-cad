# Laporan P1 / P1b — Alur state server

Tanggal: 2026-10-31  
Repo: Structural CAD (pasca H5 + P0/P1/P1b)

## Ruang lingkup

- **T1** — Alur state server dan edit pile berurutan (termasuk path yang dibuka)
- **T2** — Penolakan edit zona/kedalaman tidak feasibel
- **S1** — `add_rebar` tidak meracuni state sesi
- **P1b** — Rapikan `_commit` untuk project tanpa judul; saring error resolve per pile; konsolidasi tes; perbaiki arah tes T3; S2 save-as

Tidak ada perubahan schema, engine geometri, atau format project JSON.

## Perubahan implementasi

### `_commit` (P1 + P1b)

Urutan: validasi → simpan → baru `_set_current`.

P1b: bila `CURRENT_PATH` sebelumnya `None` dan target adalah fallback `DATA_ROOT/project.json`, dokumen tetap ditulis tetapi **`CURRENT_PATH` tetap `None`** dan **`DIRTY` tetap `True`**. Path dan `DIRTY=False` hanya diset bila target sama dengan `CURRENT_PATH` yang sudah ada (project bertajuk).

### `add_rebar` (S1)

Memakai `copy.deepcopy` dari dokumen sesi; commit hanya lewat `_commit`.

### `_apply_pile_op_and_respond` (T1/T2 + P1b)

Memakai `_commit`. Error resolve disaring lewat `_resolve_errors_for_pile`: hanya issue global atau issue yang path-nya mengarah ke instance pile yang diedit yang menolak operasi. Path instance dipetakan dari pointer `/groups/{gi}/instances/{ii}` ke id pile di dokumen (tanpa mengubah `scad.resolve`).

### Helper

- `_pile_ids_from_issue_path`
- `_resolve_errors_for_pile`

## Tes

### Fixture

Satu fixture `ui_server` di `tests/conftest.py` memulihkan seluruh global server. Fixture `http_workspace` dihapus; `tests/ui/test_file_api.py` memakai `ui_server`.

### Regression aktif

| ID | Tes | File |
|----|-----|------|
| T1 | Dua edit depth, tiga operasi berurutan, path dibuka | `tests/ui/test_state_regression.py` |
| T2 | Depth 5000 pada P1-6 → 400 + `ZONE_DEPTH_SHORT`, disk utuh | sama |
| S1 | Rebar invalid → 400, sesi utuh, save berikutnya OK | sama |
| P1b | Project baru → add-element → depth: path None, dirty True; save-as mengisi path | sama |
| P1b | P1-6 infeasibel di sesi; edit P1-1 depth 29000 → 200 | sama |

Duplikat T1/T2 di `test_file_api.py` dihapus. Indeks `instances[n]` diganti pencarian by id. Asersi mengandalkan kode issue (`ZONE_DEPTH_SHORT`), bukan teks pesan penuh.

### Xfail (strict)

- S2: header asing pada `/api/project/save` dan `/api/project/save-as`
- T3: polar `by:spacing` harus `ARR_BAD` + `ValueError` dari `build_bar_groups`; `start_angle_deg`
- T4: total rekap `count * cut_length`
- S6, S7: di `tests/core/test_core_audit_regressions.py`

Tes T3 polar spacing diarahkan ulang sesuai keputusan D2 (ditolak), bukan "batang tetap ada".

## Mutation check (P1b langkah 5)

Sementara pemakaian `_commit` di `_apply_pile_op_and_respond` diganti ke pola lama (selalu tulis `DATA_ROOT/project.json` lalu `_set_current(path=target)`):

- `test_t1_opened_path_is_edit_target` **gagal** (edit tidak masuk file workspace)
- `test_untitled_project_keeps_path_none_after_pile_edit` **gagal** (`CURRENT_PATH` terisi path scratch)
- `test_t2_unfeasible_depth_is_rejected_without_disk_change` tetap lulus karena gerbang resolve masih menolak sebelum tulis

Setelah kode dipulihkan, ketiga tes hijau lagi.

## Berkas yang berubah

- `src/scad_ui/server.py` — `_commit`, filter resolve per pile, helper path issue
- `tests/conftest.py` — (tidak diubah pada P1b; sudah dari P0)
- `tests/ui/test_state_regression.py` — T1/T2/S1 + P1b + S2 save-as
- `tests/ui/test_file_api.py` — migrasi ke `ui_server`, hapus duplikat T1/T2
- `tests/engine/test_engine_audit_regressions.py` — arah tes T3
- `docs/reports/P1_alur_state_server.md` — laporan gabungan ini

Laporan lama T1–T2 / P0 / P1 di `docs/reports/` tetap sebagai jejak sejarah; acuan status adalah berkas ini.

## Verifikasi

Perintah:

```bash
PYTHONPATH=src python -m pytest tests -q
PYTHONPATH=src python tools/check_examples.py
node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts
```

Hasil aktual (mesin audit P1b):

```text
pytest tests: 209 passed, 1 skipped, 7 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 26 passed, 0 failed
```

Xfail: S2×2, S6, S7, T3×2, T4. Skip: CadQuery di `test_generic.py`.

## Asumsi dan isu terbuka

- Issue resolve per pile memakai path JSON Pointer yang sudah ada; field `pile` tidak ditambahkan ke `scad.resolve` (di luar berkas yang diizinkan P1b).
- `save_project` eksplisit masih boleh menulis ke `DATA_ROOT/project.json` dan mengisi path (perilaku Save pada project tanpa judul).
- S2, S6, S7, T3, T4 tetap backlog P2/P3/P5/P7.
- CadQuery tidak tersedia → satu tes engine di-skip.
