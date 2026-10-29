# Laporan H1 — Perbaikan G2 (Blocker)

## Ringkasan

Pekerjaan H1 untuk memperbaiki blocker G2 telah selesai pada proyek kerja `cad_generic_temp` (berasal dari `cad_f5_f6_fixed`). Perubahan dibatasi pada backend dan tes H1. Frontend serta dokumentasi tidak diubah.

## Berkas yang diubah atau dibuat

- `src/scad/files_ops.py`
- `tests/core/test_files_ops.py`
- `tests/ui/test_file_api.py` — tes HTTP baru
- `LAPORAN_H1.md` — laporan ini

`src/scad_ui/server.py` diperiksa, tetapi tidak memerlukan perubahan karena jalur save dan save-as yang tersedia sudah memvalidasi sebelum menulis melalui `_save_validated()` dan menggunakan `save_document()` yang atomik.

## Perbaikan

### Project dan element baru

- `new_project()` sekarang menghapus pengabaian error validasi dan melempar `ValueError` jika dokumen hasil tidak valid.
- `new_element()` melakukan validasi yang sama dan melempar `ValueError` jika dokumen hasil tidak valid.

### Add-element

`add_element_to_project()` sekarang:

- memvalidasi dokumen elemen sebelum mengubah project,
- mengisi `groups[].type` dari `definition.type`,
- mengisi `groups[].name`,
- menyimpan `groups[].naming` bila parameter naming diberikan,
- memvalidasi dokumen project hasil operasi,
- menolak hasil invalid dengan pesan error berbahasa Indonesia yang memuat path issue.

Salinan definisi, source hash, timestamp source, serta posisi grid tetap dipertahankan.

### Save dan save-as

Jalur penyimpanan tetap menjalankan validasi sebelum penulisan. Dokumen invalid menghasilkan HTTP 400, tidak membuat file baru, tidak menimpa file existing, dan tidak meninggalkan file sementara. Penulisan dilakukan secara atomik oleh `save_document()`.

### Source diff

`source_diff()` sekarang mengembalikan path daun, misalnya `/definition/name`, dan tidak mengembalikan path induk `/definition` secara bersamaan.

## Tes

### Tes terarah H1

Perintah:

```bash
PYTHONPATH=src /tmp/cad_venv/bin/pytest -q \
  tests/core/test_files_ops.py \
  tests/ui/test_file_api.py -rA
```

Hasil:

```text
18 passed
0 failed
```

Tes HTTP mencakup:

- alur project new → save-as → open,
- save-as dokumen invalid,
- add-element ke project existing,
- add-element ke project baru kosong,
- validasi source hash,
- layout 2 kolom dengan posisi grid,
- preservasi override saat update source,
- pembatalan update karena override zona invalid,
- source-diff hanya menggunakan path daun.

### Seluruh suite Python

Perintah:

```bash
PYTHONPATH=src /tmp/cad_venv/bin/pytest -q -rA
```

Hasil aktual:

```text
162 passed
0 failed
1 skipped
```

Tes yang dilewati:

```text
tests/engine/test_generic.py:78
CadQuery tidak tersedia
```

### Keluaran asli `pytest -q`

Perintah:

```bash
PYTHONPATH=src /tmp/cad_venv/bin/pytest -q
```

Exit code:

```text
0
```

Keluaran asli terminal:

```text
........................................................................ [ 44%]
......................................s............................ [ 85%]
........................                                                 [100%]
```

Pemeriksaan syntax dengan `py_compile` juga berhasil.

## Batasan dan asumsi

- Tidak ada perubahan pada frontend atau dokumentasi.
- `src/scad_ui/server.py` tidak diubah karena implementasi validasi-dulu dan penyimpanan atomik sudah sesuai kriteria H1.
- Tes CadQuery tidak dapat dijalankan penuh karena dependensi CadQuery tidak tersedia di lingkungan audit.

## Arsip hasil

Perbaikan H1 telah dimasukkan ke arsip hasil:

```text
cad_f5_f6_fixed.zip
```
