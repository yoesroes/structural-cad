# Perbaikan kecil tinjauan P6/P7

**Tanggal:** 2026-11-01
**Basis:** develop-p3 (P0–P7 sudah digabung)

## Perubahan

1. **CSP `style-src`** — menambah `style-src 'self' 'unsafe-inline'` agar atribut
   `style="..."` di `index.html` / `app.js` tidak diblokir browser.
2. **update-from-source + resolve** — setelah validasi, jalankan `resolve_project`;
   issue level `error` (mis. `ZONE_DEPTH_SHORT`) membatalkan update (D1/T2), sesi utuh.
3. **`find_source_matches`** — pencocokan **nama berkas persis** (`p.name == basename`),
   bukan pola `rglob(file_name)` agar `*` / `?` / `[` di nama tidak jadi glob.

## Berkas

- `src/scad_ui/server.py`
- `src/scad/files_ops.py`
- `tests/core/test_files_ops.py`
- `tests/ui/test_file_api.py`
- `docs/UI.md`

## Verifikasi

```text
pytest tests: 288 passed, 1 skipped, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node TS: 28 passed
```
