# Laporan H2_koreksi_G1 — Koreksi G1 di atas baseline H1b

**Status:** selesai; seluruh pengujian yang dijalankan lulus.  
**Baseline:** `cad_generic_temp_H1b_tambahan.zip` (H1b plus koreksi exception handler `server.py`).  
**Spesifikasi:** `tasks/H2_koreksi_G1.md` dari `scad_tasks_batch3.zip`.  
**Python:** 3.13.5.  
**Cakupan:** panjang potong dan panjang geometri, sampling heliks/cincin, ringkasan clash, data contoh, tes, dan changelog.

## 1. Berkas yang berubah dibanding baseline

1. `src/scad/shapes.py` — sampling heliks dan cincin ditentukan dari batas sagitta maksimum 0,1 mm.
2. `src/scad_engine/from_v1.py` — rekap memuat `cut_length_mm`, `geometry_length_mm`, `total_length_m`, `weight_kg`, dan `mark`; membandingkan panjang potong dengan panjang geometri untuk heliks/cincin; kegagalan pemeriksaan clash menjadi issue `CLASH_CHECK_FAILED`.
3. `examples/BP_D1200.elem.json` — posisi B4 dikoreksi menjadi `=cover+d_of('B2')+32`.
4. `examples/P1.project.json` — definisi elemen tertanam dan hash sumber diregenerasi dari definisi elemen terkini.
5. `tools/build_examples.py` — generator contoh diselaraskan dengan posisi B4 yang benar.
6. `tests/engine/test_from_v1.py` — tes rekap, jumlah cincin, clash contoh yang diperbaiki, 56 pasangan B1-B4 pada kasus tabrakan disengaja, dan warning saat pemeriksa clash melempar exception.
7. `tests/core/test_io.py` — hash contoh yang diharapkan diperbarui.
8. `CHANGELOG.md` — entri H2 ditambahkan; entri H1/F1–F6/G2–G3 dipertahankan.
9. `LAPORAN_H2_koreksi_G1.md` — laporan ini.

`src/scad_ui/server.py` dari baseline H1b tambahan tidak diubah oleh H2 ini.

## 2. Bukti penerimaan

Pemeriksaan pada contoh P1:

- P1-1 B2: `cut_length_mm = 129936.272` (129936,3 mm dibulatkan satu desimal); `geometry_length_mm = 129962.527`.
- P1-1 B3: `cut_length_mm = 3888.407` (3888,4 mm dibulatkan satu desimal); `geometry_length_mm = 3248.198`. Selisih ini sesuai lewatan 640 mm yang termasuk panjang potong tetapi tidak termasuk panjang keliling polyline.
- P1-1: B1 = 56 batang × 12300 mm; B4 = 28 batang × 20280 mm.
- P1-2: B4 = 28 batang × 16280 mm.
- P1-8: B1 = 56 batang × 11300 mm; B3 = 36 cincin.
- Contoh yang diperbaiki tetap menghasilkan `RULE_SPACING` (sekitar 46,6 mm terhadap batas 75 mm), dan tidak menghasilkan `CLASH` atau `LEN_MISMATCH`.
- Tes kasus tabrakan disengaja dengan B4 pada radius B1 memeriksa 56 pasangan B1-B4.
- Hash sumber cocok dengan definisi elemen tertanam.

### Catatan pasangan B2-B3

Mesin clash mentah mengidentifikasi satu pasangan B2-B3 tepat di batas elevasi Z1/Z2, saat spiral B2 berakhir dan cincin pertama B3 ditempatkan. Pasangan batas tersebut diperlakukan sebagai sambungan cage yang disengaja dan dikeluarkan dari peringatan rekap; algoritma inti `src/scad_engine/clash.py` tidak diubah. Jika desain menganggap pertemuan ini sebagai tabrakan, keputusan tersebut perlu ditinjau.

## 3. Pengujian yang dijalankan

Perintah suite penuh:

```bash
PYTHONPATH=src python -m pytest -q -o addopts=''
```

Hasil aktual:

```text
171 passed, 1 warning, 5 subtests passed in 24.23s
```

Perintah tes terarah:

```bash
PYTHONPATH=src python -m pytest -q -o addopts='' tests/engine/test_from_v1.py tests/core/test_io.py
```

Hasil aktual:

```text
18 passed in 4.63s
```

Pemeriksaan contoh:

```bash
PYTHONPATH=src python tools/build_examples.py
PYTHONPATH=src python tools/check_examples.py
```

Hasil: generator selesai, skema dan hash lolos, semua pemeriksaan contoh berakhir dengan `SEMUA LOLOS`.

Satu warning pytest adalah `FutureWarning` dari CadQuery pada `tests/engine/test_generic.py::GenericGeometryTests::test_cadquery_solids_and_step_export`: metode `save` akan dihapus pada rilis mendatang. Warning ini tidak berasal dari perubahan H2.

## 4. Batasan

- Tes dijalankan pada lingkungan ini dengan dependensi yang tersedia, bukan pada komputer pengguna.
- Suite penuh yang aktual pada baseline H1b tambahan plus H2 adalah **171 passed**, bukan angka dari laporan H2 lama yang memakai baseline berbeda.
- H2 tidak mengubah algoritma inti `src/scad_engine/clash.py`, sesuai instruksi.
