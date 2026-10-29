# H1b — Hotfix hasil audit H1: elemen baru, penanganan galat server, kode mati

Prasyarat: H1 sudah digabung. Tugas kecil. Baca `00_KONTEKS.md` dan `01_KONTEKS_TAMBAHAN.md`. **Berkas boleh diubah:** `src/scad/files_ops.py`, `src/scad/plugins/` (default parameter), `src/scad_ui/server.py`, `tests/core/test_files_ops.py`, `tests/ui/test_file_api.py`.

**Bukti (uji HTTP langsung pada hasil H1):**

1. `new_element("bored_pile")` dan `new_element("pile_cap")` SELALU melempar `ValueError` karena `params` dibuat `{}` padahal skema mewajibkan `diameter`, `depth_below_cof`, `cover` (bored pile) dan `length`, `width`, `height`, `cover_*` (pile cap). Tes `test_new_element_rejects_invalid_default_document` malah MENGUNCI kegagalan itu. Akibatnya menu File Elemen > Baru tidak bisa bekerja.
2. Handler `api_element_new` dan `api_project_new` tidak menangkap `ValueError`, dan `do_POST` hanya menangkap `JSONDecodeError`. Hasil: `POST /api/element/new {"type":"bored_pile"}` dan `POST /api/project/new {"id":"bad id!"}` MEMUTUS KONEKSI tanpa respons (klien menerima `RemoteDisconnected`).
3. `api_project_save_as` masih memuat kode mati: setelah `save_document_at` (yang kini sudah memvalidasi lalu menulis), `_save_validated(...)` menulis LAGI, ada blok `if not ok: pass` dengan komentar "prefer validate first", dan validasi ulang sesudahnya. Langkah 3 H1 meminta kode mati ini dihapus; laporan H1 menyatakan `server.py` tidak perlu diubah.

**Langkah:**

4. Tiap plugin elemen menyediakan `default_params()` yang valid menurut skemanya (nilai awal wajar, didokumentasikan sebagai nilai awal, bukan rekomendasi desain). `new_element(type_id, name, params=None)` memakai `params` bila diberikan, jika tidak default plugin; tipe tanpa plugin dibiarkan `params={}`. Hasil selalu divalidasi; bila `params` pemanggil tidak valid -> `ValueError` berpesan Indonesia (ini perilaku yang benar untuk masukan buruk, bukan untuk default).
5. Ganti tes yang mengunci kegagalan dengan tes yang melakukan loop atas `list_plugins()`: `new_element(tipe)` valid terhadap skema untuk SEMUA tipe terdaftar; `new_element("bored_pile", params={"diameter": -1})` -> `ValueError`.
6. Server: bungkus pengiriman `do_GET`/`do_POST`/`do_DELETE` dengan penanganan pusat: `ValueError` dan `KeyError` yang berasal dari masukan -> HTTP 400 `{"ok": false, "error": <pesan Indonesia>}`; pengecualian lain -> HTTP 500 `{"ok": false, "error": "Galat internal"}` dengan traceback ditulis ke stderr. Koneksi TIDAK BOLEH diputus tanpa respons.
7. Hapus kode mati di `api_project_save_as`: panggil `save_document_at` sekali, tangkap `ValueError` -> 400 dengan `issues` bila ada, lalu `_set_current`. Tidak ada penulisan ganda.
8. Serahkan hasil sebagai repo lengkap ATAU daftar berkas dengan path relatif dari akar repo (jangan berkas lepas tanpa jalur), beserta satu laporan. **Kriteria selesai (tes HTTP):** `POST /api/element/new` untuk `bored_pile` dan `pile_cap` -> 200 dan `element` valid; `POST /api/project/new {"id":"bad id!"}` -> 400 dengan pesan; pemanggilan yang sengaja memicu pengecualian tak terduga (monkeypatch) -> 500 JSON dan koneksi tetap hidup untuk permintaan berikutnya; save-as dokumen tidak valid tetap 400 tanpa berkas; grep tidak menemukan `_save_validated` di `api_project_save_as`; seluruh tes lama (162 lolos, 1 dilewati sebelum tugas ini) tetap lolos; laporkan angka pytest yang sebenarnya.

### Tambahan

1. Jangan mengakali skema atau tes. Letakkan keputusan ini di bagian batasan perubahan.
2. Pastikan default setiap plugin benar-benar berasal dari plugin. Untuk setiap tipe dalam `list_plugins()`, pastikan `default_params()` menghasilkan parameter yang valid terhadap skema tipe tersebut. Jangan memakai satu dictionary default bersama untuk semua tipe. Setiap pemanggilan harus menghasilkan data yang aman untuk dimodifikasi tanpa mengubah default milik pemanggilan berikutnya.
3. Perjelas kontrak penanganan HTTP. Respons 400 dan 500 harus JSON dengan `Content-Type: application/json`. Kesalahan input menghasilkan HTTP 400; exception tak terduga menghasilkan HTTP 500 dengan pesan generik `"Galat internal"`, sementara traceback ditulis ke `stderr`. Jangan mengirim traceback atau detail internal kepada klien.
4. Uji server tetap hidup setelah HTTP 500. Tes monkeypatch harus mengirim request yang memicu exception tak terduga, memeriksa respons 500 JSON, kemudian mengirim request valid berikutnya pada server yang sama dan memastikan request kedua berhasil.
5. Uji save-as tanpa efek samping. Untuk dokumen tidak valid, pastikan status 400, tidak ada berkas tujuan yang tertulis, dan proyek aktif tidak berpindah ke dokumen yang gagal disimpan. Untuk save-as yang berhasil, pastikan penulisan dilakukan satu kali dan proyek aktif berpindah ke dokumen hasil sesuai kontrak yang ada.
6. Wajib laporkan diff dan hasil tes yang benar-benar dijalankan. Laporan harus memuat daftar file yang berubah dengan path relatif, ringkasan perubahan per file, keluaran asli `pytest -q` beserta baris ringkasan terakhir, serta pesan galat pertama jika ada tes gagal. Jangan mengarang hasil tes dan jangan menyatakan tes lulus jika perintahnya tidak berhasil dijalankan.

Tipe tanpa plugin tetap harus mengikuti perilaku validasi yang sudah ditetapkan oleh kontrak proyek. Jangan otomatis menganggap tipe yang tidak dikenal valid hanya karena `params={}`. Jika kontrak mengharuskan tipe terdaftar, tolak tipe yang tidak dikenal dengan `ValueError` yang jelas. Jangan mengubah perilaku tipe yang sudah didukung tanpa memeriksa implementasi dan spesifikasi.
