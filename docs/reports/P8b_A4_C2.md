# P8b — A4 nama SVG unik + C2 tes XSS atribut

**Basis:** integrate-p6-p8 @ 3b3ce1a

## A4
- `/run-2d` menulis `run-2d-{uuid}.svg` (bukan `run-2d.svg` tetap)
- Prune: simpan 20 file terbaru (`RUN_2D_KEEP`)
- Tes concurrent: path berbeda, isi SVG sesuai pile

## C2
- `xss_attr_harness.js`: payload atribut + zones/depth; parse tag/atribut
- `test_xss_attr.py`: hijau pada kode normal; parametrize mutation (hapus escape `"`, `<`, `&`, sink zones, dll.) harus gagal

## Verifikasi
```
pytest: 310 passed, 1 skipped, 5 subtests passed
check_examples: SEMUA LOLOS
node TS: 28 passed
xss harness: ok
```
