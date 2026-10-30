# Laporan Pekerjaan P0 — Baseline dan Tes Merah

Tanggal: 2026-10-31
Repo: `final_scad_h5/Structural cad`

## Tujuan

P0 menambahkan pengaman pengujian sebelum pekerjaan perbaikan lanjutan:

- fixture server UI yang mengisolasi seluruh global state;
- migrasi test API pile ke fixture tersebut;
- regression test untuk temuan T1, T2, S1, S2, T3, T4, S6, dan S7;
- test merah `xfail(strict=True)` untuk temuan yang belum diperbaiki;
- baseline test suite dan validasi examples.

Kode produksi tidak diubah pada P0.

## Fixture isolasi

Fixture `ui_server` pada `tests/conftest.py`:

- membuat `workspace` dan `data_root` sementara;
- menyalin `examples/P1.project.json` ke `data/project.json` dan workspace;
- menyalin `BP_D1200.elem.json` ke workspace;
- menjalankan `ThreadingHTTPServer` pada port 0;
- menyimpan dan memulihkan seluruh state server:
  `DATA_ROOT`, `ROOT`, `WORKSPACE`, `CURRENT_PATH`, `CURRENT_DOC`, `DIRTY`,
  `CURRENT_ELEMENT`, dan `CURRENT_ELEMENT_PATH`.

`tests/ui/test_ops_api.py` telah dimigrasikan untuk memakai fixture tersebut.

## Regression test

Regression test yang sudah lulus sebagai kontrak aktif:

- T1: dua edit depth pada pile berbeda terlihat di disk dan `GET /api/project`.
- T1: setelah Open dari path workspace, edit disimpan ke file yang dibuka dan tidak mengubah file data root.
- T2: depth `5000` pada P1-6 ditolak dengan `ZONE_DEPTH_SHORT` dan disk tidak berubah.

Temuan yang masih terbuka dicatat sebagai `xfail(strict=True)`:

- S1: invalid rebar tidak boleh meracuni state sesi.
- S2: Host/Origin/Content-Type asing harus ditolak.
- T3: polar `by:spacing` harus menghasilkan `ARR_BAD`/tidak boleh menghilangkan batang.
- T3: `start_angle_deg` harus menggeser origin batang pertama.
- T4: setiap row total harus memenuhi `count * cut_length_mm == total_length_mm`.
- S6: override zona `rest` harus ditolak.
- S7: ekspresi pangkat invalid harus menghasilkan `ExprError`.

Nama file audit dibuat unik agar pytest tidak mengalami konflik import module:

- `tests/engine/test_engine_audit_regressions.py`
- `tests/core/test_core_audit_regressions.py`

## Status xfail

Rencana P0 asli menargetkan 10 xfail untuk kasus a–j. Pada repo saat ini, tiga kasus tersebut sudah diperbaiki pada checkpoint T1–T2 sebelumnya:

- T1 dua edit berurutan;
- T1 edit pada file yang dibuka;
- T2 depth tidak feasible.

Ketiganya dijalankan sebagai test biasa dan lulus. Karena itu hasil yang benar pada repo saat ini adalah **7 xfailed**, bukan 10 xfailed. Test yang sudah lulus tidak ditandai xfail secara artifisial.

## Berkas diubah/dibuat

- `tests/conftest.py` — fixture `ui_server` baru.
- `tests/ui/test_ops_api.py` — migrasi ke fixture bersama.
- `tests/ui/test_state_regression.py` — regression state server, T1, T2, S1, dan S2.
- `tests/engine/test_engine_audit_regressions.py` — regression T3 dan T4.
- `tests/core/test_core_audit_regressions.py` — regression S6 dan S7.
- `LAPORAN_P0.md` — laporan ini.

Tidak ada file produksi pada `src/` yang diubah dalam P0.

## Perintah verifikasi dan hasil nyata

### Full Python suite

```bash
python -m pytest tests -rxX
```

Hasil:

```text
207 passed, 1 skipped, 7 xfailed, 5 subtests passed
```

Test yang di-skip:

```text
tests/engine/test_generic.py:81 — CadQuery tidak tersedia
```

### Pemeriksaan examples

```bash
python tools/check_examples.py
```

Hasil:

```text
SEMUA LOLOS
```

### Test TypeScript

```bash
node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts
```

Hasil:

```text
26 passed, 0 failed
```

## Asumsi dan isu terbuka

- P0 dikerjakan pada repo yang sudah memuat perbaikan T1–T2. Oleh sebab itu kasus T1/T2 diperlakukan sebagai regression test lulus, bukan xfail.
- Tidak ada perubahan schema, engine, UI produksi, atau format project JSON.
- CadQuery tidak tersedia; test yang membutuhkan CadQuery tetap skip dan tidak diklaim lulus.
- Tujuh xfail menjadi daftar kerja untuk P1/P2/P3/P5/P7 berikutnya sesuai rencana perbaikan.
