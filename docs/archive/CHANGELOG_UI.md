# Changelog UI — revisi penempatan v3

- Memisahkan field dimensi pile cap dan bored pile berdasarkan pilihan struktur.
- Field bentuk tulangan berubah sesuai tipe; batang lurus tidak meminta lebar/tinggi/radius.
- Menambahkan jenis tulangan tunggal/grup, jumlah, dan spasi sumbu-ke-sumbu.
- Memisahkan orientasi batang (vertikal/horizontal) dari arah distribusi (longitudinal/transversal).
- Menambahkan referensi posisi terhadap permukaan beton atau tulangan acuan, termasuk definisi selimut, diameter referensi, jarak bebas, dan sumbu offset.
- Menambahkan bentuk sengkang ring untuk bored pile. Geometri centerline lingkaran dibuat dari parameter radius; solid ekspor memakai torus native untuk menjaga efisiensi STEP.
- Mempertahankan modul lama `layout.py`, `model.py`, `draw.py`, `section2d.py`, dan `cq_export.py` tanpa mengubah algoritma pilecap lama.
- Verifikasi lokal: `python -m pytest -q` — 50 passed, 2 FutureWarning dari CadQuery. Ekspor STEP grup empat ring berhasil (sekitar 24 KB).

## Batasan

- UI saat ini mengatur satu definisi tulangan per submit; mode grup membuat beberapa instance dari definisi tersebut. Daftar multi-definisi yang bisa dipilih sebagai referensi visual masih tahap berikutnya.
- Referensi ke tulangan lain saat ini diisi melalui koordinat sumbu referensi dan diameter acuan; belum memilih batang dari daftar geometri yang sudah digambar.
- Orientasi grup sama untuk semua batang, sesuai kebutuhan tahap ini. Preview viewport 3D interaktif belum tersedia.


## UI v4 — project-level detailing workflow

- Replaced the one-bar form with an element/project editor and a pre-save reinforcement list with append/delete.
- Added bored-pile-specific shape restrictions (straight, spiral, ring), zones, cut-off level, material/slump/cover fields, and per-definition development/lap lengths.
- Added `File > New/Open/Save`, JSON preview/download/server save, `Run > 2D` schematic SVG, and `Run > 3D` STEP export for supported bored-pile bars.
- Spiral definitions are retained in project JSON; unsupported STEP export is reported clearly.
- Added schema validation and UI/project JSON tests.


> **F5:** Skema `element` / `connection_defaults` / `reinforcement` di changelog ini adalah jejak UI lama; kontrak aktif adalah `kind: project|element` di `schemas/scad.schema.json`.
