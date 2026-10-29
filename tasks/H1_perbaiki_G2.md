# H1 — Perbaiki G2 (BLOCKER): project baru, add-element, dan simpan
Prasyarat: tidak ada. Kerjakan SEBELUM tugas lain di batch ini. Baca `00_KONTEKS.md` dan `01_KONTEKS_TAMBAHAN.md`.
**Berkas boleh diubah:** `src/scad/files_ops.py`, `src/scad_ui/server.py`, `tests/core/test_files_ops.py`, `tests/ui/test_file_api.py` (baru).
**Bukti kegagalan (uji HTTP langsung pada server):**
1. `POST /api/project/new` lalu `/api/project/save-as` -> 400 `SCHEMA /settings/units: kunci tidak dikenal`. `new_project()` menaruh `settings.units` yang tidak ada di skema, dan memvalidasi hasilnya lalu MENGABAIKAN galat (`if errors: pass`, komentar "longgarkan").
2. `POST /api/project/add-element` -> selalu 400 `SCHEMA /groups/N: kunci wajib 'type' tidak ada`. `add_element_to_project()` membuat grup tanpa `type` (dan tanpa `name`). Tes unit lolos karena memanggil fungsi langsung dan tidak pernah memvalidasi hasilnya.
3. `api_project_save_as` memanggil `save_document_at` (menulis berkas) LALU memvalidasi; saat validasi gagal, berkas tidak valid tetap ada di workspace (komentar di kode: "save_document_at already wrote — prefer validate first").
**Langkah:**
1. `new_project`: buang `settings.units`; bila hasil tidak valid `raise ValueError` dengan daftar galat (hapus blok `pass`). Hal yang sama untuk `new_element`.
2. `add_element_to_project`: isi `type` dari `definition.type`, `name`, dan `naming` bila diberikan; setelah membangun grup, jalankan `validate_document` dan `raise ValueError` (pesan Indonesia, memuat `issues`) bila ada galat tingkat error. Salinan tertanam, `source{file,hash,added_at}`, dan posisi grid tetap seperti sekarang.
3. Simpan/Simpan Sebagai (project dan elemen): VALIDASI DULU, tulis hanya jika valid, atomik (berkas sementara lalu `os.replace`). Bila gagal: 400, berkas lama utuh, tidak ada berkas baru, tidak ada sisa `.tmp`. Hapus kode mati (`ok, info = _save_validated(...)` yang hasilnya diabaikan).
4. `source-diff`: kembalikan hanya path DAUN yang berbeda (mis. `/definition/name`), bukan juga induknya (`/definition`).
**Kriteria selesai (tes HTTP baru, server di thread, workspace sementara):** alur new -> save-as -> open menghasilkan dokumen identik dan valid; save-as dokumen tidak valid -> 400 DAN berkas tidak ada; add-element `BP_D1200.elem.json` ke `P1.project.json` (grup `BP-NEW`, 4 pile, layout 2 kolom) -> 200, `source.hash` = hash `BP_D1200.elem.json`, posisi (0,0),(3000,0),(0,3000),(3000,3000), dokumen valid; add-element ke project baru kosong -> 200; update-from-source mempertahankan override P1-2/P1-5/P1-8; override tak valid (zona hilang) membatalkan pembaruan dengan `issues`; source-diff setelah mengubah nama definisi memuat `/definition/name` dan tidak memuat `/definition`. Tes unit fungsi juga memanggil `validate_document` pada hasilnya. Semua tes lama tetap lolos.

G2 sudah kamu perbaiki kemarin, tapi tanpa arahan. ulangi lagi pekerjaan perbaikan G2 dengan arahan H1. Apa 01_konteks_tambaha.md ada di kamu?
