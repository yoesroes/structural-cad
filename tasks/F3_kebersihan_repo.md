# F3 — Kebersihan repositori
Prasyarat: F2 selesai.
**Berkas boleh diubah:** `.gitignore` (baru), `pilecap_rebar/static/` (isi), `docs/`, referensi path di README/tes yang terdampak.
**Latar:** `__pycache__/` dan `.pytest_cache/` ikut ter-zip; tidak ada `.gitignore`; di `pilecap_rebar/static/` ada nama berkas dengan spasi dan tanda "–/—" (`Main – Mockup layar.html`, `Dialog– Mockup layar.html`, `Spesifikasi Skema JSON v1 — Structural CAD` tanpa ekstensi) serta duplikat (`main_mockup.html`, `dialog_mockup.html`, `Spesifikasi_Skema_JSON_v1.md`).
**Langkah:**
1. `.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `node_modules/`, `dist/`, `output/`, `*.egg-info/`, `.DS_Store`.
2. Hapus semua `__pycache__` dan `.pytest_cache` dari pohon kerja.
3. Di `static/`: pertahankan HANYA yang direferensikan `index.html` (periksa `css/` dan `js/` dengan grep; yang tidak direferensikan dan bukan mockup -> hapus dan catat). Pindahkan mockup dan dokumen spesifikasi ke `docs/` dengan nama ASCII tanpa spasi (satu salinan per isi; `docs/mockup/Main.dc.html` dan `Dialog.dc.html` sudah ada, jadi salinan di static dibuang). Hapus berkas tanpa ekstensi.
4. Perbarui referensi yang rusak (README, tes).
**Kriteria selesai:** `find . -type f` tidak menampilkan nama dengan spasi atau karakter non-ASCII; tidak ada berkas duplikat isi (periksa dengan md5); `GET /` dan aset `static` tetap 200 (tes F1 lolos); seluruh tes sama seperti sebelum F3; `__pycache__` tidak muncul di daftar berkas yang dilaporkan.
