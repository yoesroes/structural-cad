# Laporan P7 + P7b — Keamanan HTTP dan XSS

**Tanggal:** 2026-11-01  
**Basis:** develop-p3

## P7 (inti)

- Gerbang Host / Origin / Content-Type pada GET & POST
- Header `X-Content-Type-Options: nosniff` + CSP
- `escapeHtml` pada interpolasi data dokumen di `innerHTML`

## P7b (penutup tinjauan)

1. **Tes XSS perilaku (Node):** stub DOM + `renderSidebar` / `renderTable` / `renderProps`
   dengan payload di `project.name`, `group.id`/`type`, `inst.id`, materials grade, shape.code.
   Asersi: tidak ada tag `<img`/`<script` mentah; payload ter-escape (`&lt;` / `&quot;`).
   Pemindai regex tetap sebagai lapis kedua.
2. **CSP + style:** menambah `style-src 'self' 'unsafe-inline'`; **dan** memindahkan ketujuh
   atribut `style` inline ke kelas CSS (`h-first`, `text-muted-inline`, `shape-preview-svg`).
   Tes header memeriksa seluruh direktif CSP.
3. **Guard GET:** Host asing → 400 pada `/` dan `/api/project`; Origin asing → 403;
   DELETE Host asing tanpa side-effect pada disk.
4. **Mutation check (nyata):**

| Mutasi | Tes yang gagal |
|--------|----------------|
| Hapus escape `rootName` | `test_render_functions_escape_payloads_in_node` |
| Hapus escape `pid` | sama |
| Hapus escape `beton`/`baja` | sama |
| Hapus escape `shape` | sama |
| Matikan guard `do_GET` | `test_get_foreign_host_rejected` |
| Hapus direktif `style-src` CSP | `test_security_headers_present` |

## Berkas P7b

- `src/scad_ui/server.py` (CSP)
- `src/scad_ui/static/index.html`, `app.js`, `app.css` (style → kelas)
- `tests/ui/test_security_http.py`
- `docs/UI.md`
- `docs/reports/P7_keamanan_http_xss.md`

## Verifikasi nyata

```text
pytest tests: 291 passed, 1 skipped, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node TS: 28 passed
```
