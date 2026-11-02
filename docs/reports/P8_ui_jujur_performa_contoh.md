# Laporan P8 — UI jujur, performa, sinkron contoh

**Tanggal:** 2026-11-01
**Basis:** develop-p3 (P0–P7)

## Ruang lingkup

S10/S11/S12 + sinkron paket contoh + performa recap.

## Berkas diubah / dibuat

| Berkas | Isi |
|--------|-----|
| `src/scad_ui/static/app.js` | Status dari issue resolve; kanvas tanpa B3 + label skematik; tombol nonaktif |
| `src/scad_ui/static/index.html` | Menu/tombol belum siap: disabled + title; hapus Sesuai keras |
| `src/scad_ui/static/app.css` | Gaya `.mi.disabled` |
| `src/scad_ui/server.py` | Snapshot + recap/run di luar STATE_LOCK; cache LRU recap_pile (32) |
| `src/scad_engine/examples/P1.project.json` | Disalin dari `examples/` (B1,B2,B4,B5) |
| `scripts/sync_examples.sh` | Baru |
| `scripts/ci.sh` | Cek contoh + tes Node |
| `tests/test_examples_sync.py` | Baru |
| `tests/ui/test_recap_perf.py` | Cache hit + request tidak terblokir |
| `docs/reports/P8_ui_jujur_performa_contoh.md` | Laporan ini |

## Perilaku

1. Kolom status: `Sesuai` hanya bila tidak ada issue; selain itu kode issue (error dulu).
2. Kanvas: label *Ilustrasi skematik, bukan data model*; label B3 dihapus.
3. Baru / Buka / Simpan Sebagai / Tambah tulangan: `disabled` + `title="Belum tersedia"`.
4. `GET .../recap` dan `POST /run-2d|/run-3d`: snapshot di dalam kunci, hitung di luar.
5. Cache LRU recap_pile kunci `(sha256_of(doc), pile_id)`.

## Verifikasi nyata

```text
pytest tests: 290 passed, 1 skipped, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node TS: 28 passed
```

## Asumsi / isu terbuka

- Simpan project tanpa judul (catatan P1b) belum disentuh — backlog terpisah bila perlu.
- Cache hanya untuk `recap_pile`; `recap_group` masih menghitung ulang (tetapi di luar lock).
