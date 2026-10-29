# Laporan H1b — Hotfix hasil audit H1

## Ringkasan

H1b dikerjakan di `cad_generic_temp`. H2 tidak dijalankan dan tidak diubah. `tasks/00_KONTEKS.md` serta `tasks/01_KONTEKS_TAMBAHAN.md` dibaca ulang dan digunakan sebagai golden standard.

## Berkas berubah/dibuat

- `src/scad/files_ops.py`
- `src/scad/plugins/base.py`
- `src/scad/plugins/bored_pile.py`
- `src/scad/plugins/pile_cap.py`
- `src/scad_ui/server.py`
- `tests/core/test_files_ops.py`
- `tests/ui/test_file_api.py`
- `tasks/H1b_hotfix.md`
- `LAPORAN_H1b.md`

Tidak ada perubahan pada `schemas/scad.schema.json`, frontend, contoh data, atau berkas H2. Tidak ada schema atau aturan validasi yang dilonggarkan.

## Perubahan per berkas

### `src/scad/plugins/base.py`

Menambahkan kontrak `default_params()`. Method dasar memberi `NotImplementedError` agar plugin test lama yang hanya menguji registrasi tetap kompatibel; setiap plugin bawaan menyediakan implementasi konkretnya sendiri.

### `src/scad/plugins/bored_pile.py`

Menambahkan `default_params()` baru dengan nilai awal valid untuk `diameter`, `depth_below_cof`, `cover`, dan `cover_ref`.

### `src/scad/plugins/pile_cap.py`

Menambahkan `default_params()` baru dengan nilai awal valid untuk `length`, `width`, `height`, seluruh parameter cover, dan `cover_ref`.

Setiap pemanggilan menghasilkan dictionary baru yang aman dimodifikasi tanpa mengubah pemanggilan berikutnya.

### `src/scad/files_ops.py`

`new_element(type_id, name, params=None)` sekarang:

- memakai `default_params()` plugin bila `params` tidak diberikan,
- memakai salinan mendalam `params` bila diberikan,
- mempertahankan `params={}` untuk tipe tanpa plugin,
- selalu memvalidasi dokumen hasil,
- menolak parameter invalid dengan `ValueError` berbahasa Indonesia.

### `src/scad_ui/server.py`

- Menambahkan penanganan exception terpusat untuk `do_GET`, `do_POST`, dan `do_DELETE`.
- `ValueError`/`KeyError` input menghasilkan HTTP 400 JSON.
- Exception tak terduga menghasilkan HTTP 500 JSON dengan pesan generik `Galat internal`.
- Traceback exception tak terduga ditulis ke stderr.
- JSON request invalid ditolak sebagai HTTP 400.
- `api_element_new` meneruskan `params` ke `new_element`.
- `api_project_save_as` sekarang memanggil `save_document_at` satu kali, tanpa `_save_validated`, tanpa penulisan ganda, dan tanpa validasi ulang setelah menulis.

### Tes

- Tes yang sebelumnya mengunci kegagalan `new_element()` diganti menjadi loop atas seluruh `list_plugins()` dan memeriksa dokumen valid.
- Ditambahkan tes parameter bored pile invalid.
- Ditambahkan tes HTTP untuk default `bored_pile` dan `pile_cap`.
- Ditambahkan tes HTTP project ID invalid menghasilkan 400 dan koneksi tetap hidup.
- Ditambahkan tes HTTP exception tak terduga menghasilkan 500 JSON lalu server tetap melayani request berikutnya.
- Ditambahkan tes save-as invalid tidak mengubah project aktif dan tidak membuat file.

## Perintah dan hasil tes

### Tes terarah core/plugin

```bash
PYTHONPATH=src /tmp/cad_venv/bin/pytest -q \
  tests/core/test_files_ops.py tests/core/test_plugins.py -rA
```

Hasil final:

```text
19 passed
0 failed
```

### Tes HTTP H1b

```bash
PYTHONPATH=src /tmp/cad_venv/bin/pytest -q tests/ui/test_file_api.py -rA
```

Hasil final:

```text
11 passed
0 failed
```

### Seluruh suite Python

```bash
PYTHONPATH=src /tmp/cad_venv/bin/pytest -q
```

Exit code:

```text
0
```

Keluaran asli terminal:

```text
........................................................................ [ 42%]
.......................................s........................... [ 82%]
.............................                                            [100%]
```

Dengan pelaporan detail, hasil suite yang sama adalah:

```text
167 passed
0 failed
1 skipped
```

Tes yang dilewati:

```text
tests/engine/test_generic.py:78
CadQuery tidak tersedia
```

`py_compile` untuk seluruh file H1b juga berhasil. Pemeriksaan independensi default plugin menghasilkan 0 error untuk `bored_pile` dan `pile_cap`, serta dictionary params antar pemanggilan berbeda object.

### Kegagalan sementara selama pengembangan

Ada satu kegagalan pada pelaksanaan tes terarah pertama, sebelum perbaikan kompatibilitas plugin selesai. Pesan error pertama:

```text
TypeError: Can't instantiate abstract class Dup without an implementation for abstract method 'default_params'
```

Lokasi tes: `tests/core/test_plugins.py::test_duplicate_register_raises`.

Perbaikannya adalah menjadikan `default_params()` method konkret pada base class yang memberi `NotImplementedError`, sementara plugin bawaan tetap wajib menyediakan implementasi default masing-masing. Setelah perbaikan tersebut, seluruh tes final lulus. H2 tidak dijalankan.

## Batasan perubahan

- Tidak mengakali schema atau tes.
- Tidak menghapus aturan validasi.
- Tidak mengubah berkas di luar cakupan H1b selain task dan laporan ini.
- Tipe tanpa plugin tetap memakai `params={}` sesuai instruksi; validitas akhirnya tetap ditentukan oleh validator dokumen.
- CadQuery tidak tersedia sehingga satu tes tetap skipped.

## Arsip hasil

ZIP perubahan H1b dibuat di luar folder kerja:

```text
cad_generic_temp_H1b_changes.zip
```

Snapshot lengkap workspace juga dibuat:

```text
cad_generic_temp_H1b_snapshot.zip
```
