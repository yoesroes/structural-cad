# UI server (`src/scad_ui`)

Server lokal memakai `ThreadingHTTPServer` dari `scad_ui.server` dan dijalankan dengan
perintah `scad-ui`. Halaman aktif adalah `src/scad_ui/static/index.html`; frontend
TypeScript di `web/` dilengkapi bridge modular `static/app.js` yang dimuat oleh halaman aktif.

## Konfigurasi

- Default workspace adalah direktori kerja saat `scad-ui` dijalankan.
- `scad-ui --workspace PATH` membatasi operasi buka/simpan berkas ke `PATH`.
- Data sesi default berada di `output/structural_cad_ui/`, atau di lokasi
  `STRUCTURAL_CAD_DATA` bila variabel lingkungan itu diatur.
- Server dimaksudkan untuk loopback (`127.0.0.1`). Host non-loopback hanya diberi
  peringatan di stderr dan tidak mendapat autentikasi tambahan.

## Endpoint aktif

### GET

| Path | Perilaku |
|------|----------|
| `/`, `/index.html` | Shell HTML |
| `/static/...` | Aset di bawah `static/` saja; traversal URL dan symlink keluar ditolak dengan 404 |
| `/api/project` | Project aktif dari data sesi atau contoh `P1.project.json` |
| `/api/element/<type>/schema` | Metadata plugin: `params_schema`, `faces`, dan `overridable_params` |
| `/api/pile/<id>/recap` | Rekap tulangan pile |
| `/api/group/<id>/recap` | Rekap gabungan satu grup |
| `/api/group/<id>/source-diff` | Perbandingan hash definisi tertanam dengan file sumber |
| `/api/files?dir=` | Daftar file JSON di bawah workspace yang diminta |

### POST

| Path | Body utama | Perilaku |
|------|------------|----------|
| `/api/project/new` | `{id, name}` | Membuat project v1 baru dan menjadikannya project aktif |
| `/api/project/open` | `{path}` | Membuka project JSON di bawah workspace |
| `/api/project/save` | dokumen atau `{doc}` | Validasi lalu menyimpan project aktif secara atomik |
| `/api/project/save-as` | `{path, doc}` | Validasi lalu menyimpan project ke path workspace yang baru |
| `/api/project/add-element` | `{path, group_id, ...}` | Menyalin definisi elemen ke project beserta hash sumber |
| `/api/project/resolve` | `{doc}` | Resolve zona dan pile |
| `/api/validate` | `{doc}` | Mengembalikan daftar `Issue` |
| `/api/pile/<id>/depth` | `{depth}` | Menerapkan operasi kedalaman, menyimpan, lalu mengembalikan `ResolvedPile` |
| `/api/pile/<id>/zone` | `{zone, length}` | Menerapkan operasi panjang zona |
| `/api/pile/<id>/reset` | `{field: "depth"\|"zone:<id>"}` | Menghapus override kedalaman atau zona |
| `/api/element/new` | `{type}` | Membuat file elemen baru dengan default plugin |
| `/api/element/open` | `{path}` | Membuka file elemen di bawah workspace |
| `/api/element/save` atau `/api/element/<id>/save` | `{path, doc}` | Validasi lalu menyimpan file elemen |
| `/api/element/<id>/rebar` | item tulangan | Jalur legacy untuk menambah tulangan ke grup |
| `/api/group/<id>/update-from-source` | `{path}` | Memperbarui definisi tertanam setelah pemeriksaan hash/validasi |
| `/run-2d` | `{doc, pile_id?, cut_x?, cut_y?}` | Menghasilkan SVG section untuk pile target |
| `/run-3d` | `{doc, pile_id?}` | Menghasilkan centerline 3D serializable untuk pile target |

Endpoint yang tidak tercantum mengembalikan 404. Jalur lama `/save-project` sudah
dihapus.

## Kontrak berkas

Project dan elemen harus berupa dokumen v1 dengan `schema_version: 1`. Operasi file
memvalidasi dokumen sebelum menulis dan menggunakan path relatif terhadap workspace;
path keluar workspace ditolak.

## Frontend dan pengujian

`web/src/commands/` berisi logika perintah murni (`SET`, `RESET`, menu file, dan
`applyOperation`) yang diuji dengan `node:test`. `static/app.js` menyediakan API modular
untuk Open, Validate, Save, Run 2D, dan Run 3D pada halaman aktif.
