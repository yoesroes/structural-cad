# Laporan Pekerjaan T1–T2

Tanggal pengerjaan: 2026-10-30
Repo: `final_scad_h5/Structural cad`

## Ruang lingkup

Pekerjaan ini menyelesaikan dua tugas pertama Fase 1 sesuai urutan penanganan:

- **T1 — Edit pile hilang dan tidak tersimpan ke berkas yang dibuka**
- **T2 — Edit tidak feasible diterima sebagai `ok: true`**

Baseline engine, kemampuan pile cap, dan hasil perhitungan yang sudah terverifikasi dipertahankan. Tidak ada rewrite engine.

## T1 — State edit pile

### Masalah

Handler `_apply_pile_op_and_respond()` selalu menyimpan hasil operasi ke `DATA_ROOT/project.json` dan tidak memperbarui `CURRENT_DOC`. Akibatnya, setelah project dibuka dari file tertentu, state memory, file aktif, dan hasil `/api/project` dapat berbeda.

### Perbaikan

- Menggunakan `CURRENT_PATH` sebagai target penyimpanan jika project sedang dibuka.
- Tetap menggunakan `DATA_ROOT/project.json` sebagai fallback untuk project yang belum memiliki path.
- Memanggil `_set_current(new_doc, path=target, dirty=False)` hanya setelah validasi dan penyimpanan berhasil.
- Mempertahankan pola autosave endpoint yang sudah ada.
- Menambahkan isolasi state global pada test API operasi pile agar `CURRENT_DOC`, `CURRENT_PATH`, `DIRTY`, dan `DATA_ROOT` tidak bocor antar-test.

### Regression test

`test_pile_edits_update_open_project_state_and_file` memverifikasi:

1. Open `P1.project.json`.
2. Memastikan baseline `P1-2=26000` dan `P1-5=28500`.
3. Edit depth `P1-2` menjadi `25500`.
4. Edit depth `P1-5` menjadi `25000`.
5. Kedua perubahan berbeda dari baseline dan tetap ada di state aktif.
6. Kedua perubahan tersimpan ke file yang dibuka.
7. `DATA_ROOT/project.json` tidak digunakan secara keliru.
8. `CURRENT_PATH` dan `DIRTY` konsisten.

## T2 — Feasibility hasil resolve

### Masalah

Edit seperti depth `5000` pada project P1 dapat menghasilkan `zones: []`, tetapi tetap dikembalikan sebagai HTTP 200 dan `ok: true`. Issue `ZONE_DEPTH_SHORT` dari resolver belum digunakan sebagai keputusan penyimpanan.

### Perbaikan

- Menjalankan `resolve_project(new_doc)` sebelum penyimpanan edit pile.
- Memisahkan issue level `error` dari issue lain.
- Jika terdapat error resolve:
  - mengembalikan HTTP 400;
  - mengembalikan `ok: false`;
  - menyertakan seluruh `issues` dari resolver;
  - tidak menyimpan file;
  - tidak mengubah `CURRENT_DOC`, `CURRENT_PATH`, atau `DIRTY`.
- Dokumen hanya di-commit ke state aktif setelah resolve dan penyimpanan berhasil.
- Issue warning, bila ada tanpa error, tetap tidak memblokir operasi.

### Regression test

`test_pile_edit_rejects_unfeasible_depth_without_mutating_state` memverifikasi:

1. Open `P1.project.json`.
2. Kirim depth `5000` untuk `P1-1`.
3. Response adalah HTTP 400 dan `ok: false`.
4. Response memuat issue `ZONE_DEPTH_SHORT`.
5. `CURRENT_DOC` tidak berubah.
6. File project tidak berubah.
7. `/api/project` tetap mengembalikan dokumen sebelum edit gagal.
8. `CURRENT_PATH` dan `DIRTY` tetap konsisten.

## File yang berubah

- `src/scad_ui/server.py`
  - Perbaikan target penyimpanan dan commit state T1.
  - Validasi resolve sebelum penyimpanan T2.
- `tests/ui/test_file_api.py`
  - Regression test T1.
  - Regression test T2.
- `tests/ui/test_ops_api.py`
  - Fixture isolasi state global untuk test operasi pile.
- `T1-T2.md`
  - Laporan pekerjaan ini.

## Hasil pengujian

Perintah yang benar-benar dijalankan:

```bash
pytest tests/ui/test_file_api.py tests/ui/test_ops_api.py -q
python3 -m py_compile src/scad_ui/server.py tests/ui/test_file_api.py tests/ui/test_ops_api.py
pytest
npm test --prefix web
```

Hasil:

```text
Targeted API tests: 17 passed
Python full suite: 204 passed, 1 skipped, 5 subtests passed
TypeScript/web suite: 26 passed, 0 failed
```

Satu test Python tetap di-skip karena dependency tidak tersedia:

```text
tests/engine/test_generic.py:81 — CadQuery tidak tersedia
```

Tidak ada klaim bahwa test CadQuery lulus; test tersebut berstatus skipped/not run.

## Kompatibilitas dan batasan

- Format project JSON tidak diubah.
- Dokumen project lama tetap dibaca melalui jalur existing.
- Algoritma engine dan perhitungan pile cap tidak diubah.
- T1 masih mempertahankan perilaku autosave endpoint edit pile; karena itu `DIRTY` tetap `False` setelah edit berhasil.
- T2 hanya menolak issue resolve level `error`; warning tidak diblokir pada tugas ini.
