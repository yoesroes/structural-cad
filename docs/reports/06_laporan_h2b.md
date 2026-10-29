# LAPORAN H2b — Hotfix audit clash hard-coded

## 1. Baseline dan berkas berubah

Baseline: `cad_generic_temp_H2_koreksi_G1.zip` (H1b dan H2 sudah tergabung).

Berkas perubahan kode/data:
- `src/scad_engine/from_v1.py`
- `examples/BP_D1200.elem.json`
- `examples/P1.project.json` (hash sumber diperbarui)
- `tools/build_examples.py`
- `tests/engine/test_from_v1.py`
- `tests/core/test_io.py` (hash baru)
- `CHANGELOG.md`
- `LAPORAN_H2b.md` (laporan ini)

Tidak ada perubahan schema atau frontend.

## 2. Perbaikan

- Menghapus `by_pair.pop("B2-B3", None)` dan komentar pengecualiannya. Hasil `find_clashes` mentah tidak lagi disaring berdasarkan nama mark.
- B3 ditetapkan sebagai spiral `R87` dengan pitch **200 mm**, sesuai koreksi. B2 tetap spiral `R87` dengan pitch 75 mm.
- B2 memakai `extent.extend_end: -200`. Implementasi `extent_z_range` membuat nilai negatif ini memendekkan batas bawah B2 ke atas 200 mm: batas B2 berubah dari z = -3000 mm menjadi z = -2800 mm, sedangkan B3 dimulai pada z = -3000 mm. Ini memisahkan ujung dua spiral pada data contoh tanpa pengecualian clash berbasis nama.
- Rumus panjang potong R87 di `tools/build_examples.py` diperbaiki agar memperhitungkan keliling lintasan dan komponen aksial pitch: `n × sqrt((pi × (A-d))² + pitch²)`. Rumus keliling saja tidak cukup akurat untuk pitch B3 sebesar 200 mm dan menghasilkan `LEN_MISMATCH` pada geometri sampel.
- Regenerasi `BP_D1200.elem.json` dan `P1.project.json`. Hash definisi: `sha256:b48399a3cbd89e552ed520210f34158248ec4e4d65028c9606418ddeef171b6f`; hash sumber pada proyek cocok.
- Tes regresi memastikan clash mentah P1-1 nol, rekap tidak mengeluarkan `CLASH`, `RULE_SPACING` tetap ada, dan dua mark B2/B3 yang sengaja dibuat berimpit tetap dilaporkan.
- Pencarian literal B1/B2/B3/B4 pada kode Python non-tes di `src/` tidak menemukan hasil.

## 3. Hitung manual P1

Diameter lintasan sumbu heliks: `A-d = (1200 - 2×75) - 16 = 1034 mm`.

Rumus panjang heliks yang digunakan:
`L = (H/p) × sqrt((pi×1034)² + p²)`.

- **P1-1:** B2 tinggi efektif 2800 mm, pitch 75 mm → 37⅓ putaran; panjang teoritis ≈ 121306,2 mm. B3 tinggi 8000 mm, pitch 200 mm → 40 putaran; panjang teoritis ≈ 130182,3 mm.
- **P1-2:** B3 tetap tinggi 8000 mm, pitch 200 mm → 40 putaran; panjang teoritis ≈ 130182,3 mm. B4 tetap 16280 mm.
- **P1-8:** override Z2 = 7000 mm; B3 pitch 200 mm → 35 putaran; panjang teoritis ≈ 113909,5 mm. B1 tetap 11300 mm.

Jumlah putaran di atas dihitung manual dari tinggi dibagi pitch. Panjang teoritis dihitung dari geometri heliks, bukan disalin dari keluaran rekap. B3 adalah satu objek heliks per pile, sehingga `count = 1` (bukan jumlah cincin).

## 4. Hasil pytest aktual

Perintah penuh:

`PYTHONPATH=src python -m pytest -q -o addopts=''`

Hasil aktual:

`173 passed, 1 warning, 5 subtests passed in 17.15s`

Warning tunggal adalah `FutureWarning` CadQuery bahwa metode `save` akan dihapus pada rilis mendatang.

Probe/tes P1-1:
- `find_clashes(build_bar_groups(...))`: 0 pasangan clash mentah.
- `recap_pile`: tidak ada issue `CLASH`.
- `RULE_SPACING` tetap muncul karena jarak bersih antarbundel B1 masih di bawah aturan minimum 75 mm.
- Tes regresi memastikan benturan B2-B3 yang sengaja dibuat tetap terlaporkan tanpa penyaringan nama.

## 5. Catatan

- B3 memakai pitch 200 mm sesuai koreksi pengguna; B2 tetap 75 mm.
- Perubahan ujung B2 sebesar 200 mm adalah parameter contoh untuk menghindari clash pada data demonstrasi; bukan aturan universal untuk semua desain.
- Tes dijalankan di lingkungan pengerjaan. Jalankan ulang di lingkungan lokal untuk verifikasi dependensi lokal.
