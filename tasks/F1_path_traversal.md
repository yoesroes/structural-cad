# F1 — Tutup celah path traversal di server UI
Prasyarat: tidak ada. Baca `00_KONTEKS.md` dan `01_KONTEKS_TAMBAHAN.md`.
**Berkas boleh diubah:** `pilecap_rebar/ui.py`, `tests/test_ui.py`.
**Latar (terbukti saat audit):** `GET /static//etc/passwd` mengembalikan isi `/etc/passwd`. Penyebab: `self.path.replace("/static/", "", 1)` menghasilkan `/etc/passwd`, dan `STATIC_DIR / "/etc/passwd"` di pathlib menjadi path absolut; pengecekan `".."` tidak menangkapnya.
**Langkah:**
1. Perbaiki `serve_static`: buang query string dan fragmen, `urllib.parse.unquote` SEKALI, gabungkan, lalu `target = (STATIC_DIR / rel).resolve()`; hanya layani bila `target.is_file()` dan `STATIC_DIR.resolve()` adalah salah satu induk `target` (`target.is_relative_to(...)` atau setara). Selain itu 404 (tanpa membocorkan alasan).
2. Periksa SEMUA rute yang menyajikan berkas (termasuk `/files/...` untuk keluaran) dan terapkan fungsi pembantu yang sama (`_safe_join(base, rel) -> Path | None`).
3. Bila `--host` bukan loopback (127.0.0.1, ::1, localhost), cetak peringatan jelas ke stderr bahwa server tanpa autentikasi.
**Kriteria selesai (tes baru di `tests/test_ui.py`, server dijalankan di thread dengan port 0 dan urllib):** 404 untuk `/static//etc/passwd`, `/static/%2e%2e/README.md`, `/static/../README.md`, `/static/css/../../README.md`, `/static/%2Fetc%2Fpasswd`, dan untuk symlink di dalam folder static yang menunjuk ke luar (buat di direktori sementara dengan STATIC_DIR di-monkeypatch); 200 untuk `/static/index.html` dan satu aset sah, termasuk dengan `?v=1`; `/` tetap 200. Seluruh tes lain tetap lolos.
**Jangan:** mengubah endpoint `/api/*`.
