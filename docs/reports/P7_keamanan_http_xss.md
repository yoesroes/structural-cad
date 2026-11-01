# Laporan P7 — Keamanan HTTP dan XSS

**Tanggal:** 2026-11-01  
**Repo:** Structural CAD (`develop-p3`)

## Ruang lingkup

Menutup temuan **S2** (Host/Origin/Content-Type) dan **S9** (XSS innerHTML), plus header keamanan dasar.

## Berkas diubah

| Berkas | Isi |
|--------|-----|
| `src/scad_ui/server.py` | Gerbang Host/Origin/Content-Type; header nosniff + CSP |
| `src/scad_ui/static/app.js` | `escapeHtml()` pada interpolasi data dokumen di innerHTML |
| `tests/ui/test_security_http.py` | Tes baru (Host, Origin, text/plain, header, Node escapeHtml, scan static) |
| `tests/ui/test_state_regression.py` | Hapus xfail S2 (2 tes) |
| `docs/UI.md` | Dokumentasi gerbang + utang teknis `unsafe-inline` |
| `docs/reports/P7_keamanan_http_xss.md` | Laporan ini |

## Perilaku

1. **Host:** hanya `127.0.0.1:<port>`, `localhost:<port>`, `[::1]:<port>` → selain itu **400**.
2. **POST Content-Type:** wajib `application/json` (charset opsional) → selain itu **415**.
3. **Origin:** jika ada, wajib `http://<Host>` → selain itu **403**. Tanpa header CORS.
4. **Header respons:** `X-Content-Type-Options: nosniff`; CSP dengan `script-src 'self' 'unsafe-inline'` (utang teknis karena onclick shell HTML).
5. **XSS:** data dokumen melewati `escapeHtml` sebelum masuk template `innerHTML`.

## Mutation check

| Mutasi | Tes yang gagal |
|--------|----------------|
| Matikan cek Host (`if False and host not in ...`) | `test_foreign_host_rejected_without_write` (200 == 400) |
| Matikan cek Origin (`if False and origin != expected`) | `test_foreign_origin_rejected_without_write` |
| Matikan cek Content-Type | `test_text_plain_rejected_without_write` |

Semua dipulihkan setelahnya.

## Verifikasi nyata

```text
pytest tests: 254 passed, 1 skipped, 1 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 28 passed, 0 failed
```

Xfail tersisa: **T4** saja (S2 sudah hijau).

## Asumsi / isu terbuka

- `unsafe-inline` di CSP tetap diperlukan sampai handler `onclick` diganti event listener (P8/UI).
- `do_DELETE` tidak dilindungi gerbang khusus (endpoint tidak dipakai); bisa diseragamkan nanti.
