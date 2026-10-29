# F2 — Hapus endpoint dan modul placeholder
Prasyarat: F1 selesai (berkas `ui.py` sama; kerjakan berurutan).
**Berkas boleh diubah:** `pilecap_rebar/ui.py`, `pilecap_rebar/elements/` (dihapus), `tests/test_ui.py`.
**Latar:** `/run-2d` dan `/run-3d` mengembalikan `ok: true` ("STEP tersimpan; 0 batang") padahal `elements/boredpile.py` hanya mencetak teks dan tidak membuat berkas. `/save-project` menduplikasi `/api/project/save` dengan format lama. `elements/` adalah sistem registri kedua yang bersaing dengan `core/scad/plugins`.
**Langkah:**
1. `/run-2d` dan `/run-3d` -> HTTP 501 dengan `{"ok": false, "code": "NOT_IMPLEMENTED", "error": "Akan tersedia setelah G1/G5"}`.
2. Hapus rute `/save-project` dan fungsi lama yang tidak lagi dipakai (`_validate_project`, `_run_2d`, `_run_3d`, `run_2d`, `run_3d` bila tidak ada pemakai lain; periksa dengan grep).
3. Hapus paket `pilecap_rebar/elements/`. Ganti `GET /api/element/<type>/form` (HTML) dengan `GET /api/element/<type>/schema` -> `{"ok": true, "type": ..., "params_schema": ..., "faces": [...], "overridable_params": [...]}` yang diambil dari `scad.plugins.get_plugin`; tipe tak dikenal -> 404 `{"ok": false, "error": "..."}`.
4. `generic.py`, `generic_cli.py`, dan `tests/test_generic.py` TETAP (rotasi Euler dipakai G1).
**Kriteria selesai:** tidak ada impor `elements` yang tersisa (grep); tes: `/run-2d` dan `/run-3d` -> 501; `/save-project` -> 404; `/api/element/bored_pile/schema` memuat `depth_below_cof` di `overridable_params`; `/api/element/xyz/schema` -> 404; semua tes lain tetap lolos (sebutkan tes yang kamu hapus/ubah karena memverifikasi perilaku palsu).
