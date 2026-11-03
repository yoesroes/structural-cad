# Laporan P10 — Katalog Bentuk Tulangan Berbasis Elemen

Tanggal: 2026-11-03  
Baseline: `work-p9-p10` pada commit `ec8ea8a` (`fix(P9): import sys in example checker`)

## Ringkasan pekerjaan

P10 mengubah pemilihan bentuk tulangan dari daftar global menjadi katalog yang disediakan plugin berdasarkan jenis elemen. UI mengambil katalog dari endpoint schema dan tidak lagi menampilkan pilihan bentuk hard-code.

- `bored_pile`: `R20`, `R87`, `RING`.
- `pile_cap`: `R20`, `U`, `U-INV`, `X-HOOK-135-90`, `X-HOOK-135-135`.
- `pile_cap` memiliki katalog bursting `R87`, `RING`, yang hanya aktif secara valid bila `features` memuat `post_tensioning` dan rebar memakai `purpose: "bursting"`.
- Sengkang persegi belum ditawarkan karena builder belum tersedia.
- `X-HOOK` tidak ditolak global; tetap sah pada pile cap dan tidak masuk katalog bored pile.
- `SHAPE_NOT_ALLOWED` dipakai untuk bentuk/peran yang tidak sesuai konteks.
- `SHAPE_UNSUPPORTED` dipakai bila bentuk sudah diizinkan tetapi builder belum didukung engine.

## Berkas diubah

- `src/scad/plugins/base.py`
- `src/scad/plugins/bored_pile.py`
- `src/scad/plugins/pile_cap.py`
- `src/scad/validate.py`
- `src/scad/shapes.py`
- `schemas/scad.schema.json`
- `src/scad/data/scad.schema.json` (disinkronkan melalui `scripts/sync_schema.sh`)
- `src/scad_ui/server.py`
- `src/scad_ui/static/app.js`
- `src/scad_ui/static/index.html`
- `README.md`
- `docs/ENGINE.md`
- `docs/UI.md`
- `tests/core/test_p10_shape_context.py`
- `tests/ui/test_p10_shape_schema.py`

Schema menambah properti opsional `ElementDefinition.features` dan `RebarItem.purpose`; contoh lama tidak diubah.

## Verifikasi nyata

Perintah Preamble umum:

```text
PYTHONPATH=src /tmp/structural-cad-venv/bin/python -m pytest tests -q -rA
```

Hasil: **319 passed, 1 skipped, 0 failed**. Satu skip adalah `tests/engine/test_generic.py:81` karena CadQuery tidak tersedia.

```text
node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts
```

Hasil: **28 passed, 0 failed, 0 skipped**.

```text
PYTHONPATH=src /tmp/structural-cad-venv/bin/python tools/check_examples.py
```

Hasil: **SEMUA LOLOS**. Hash contoh dan definisi tertanam tetap sinkron.

Regresi pile cap:

```text
PYTHONPATH=src /tmp/structural-cad-venv/bin/python -m pytest tests/engine/test_g3_pile_cap.py tests/engine/test_pilecap_rebar.py -q
```

Hasil: **52 passed, 0 failed**. Ini mencakup regresi `PC_8400` dengan total **533 batang**, jumlah per mark, panjang per mark, rekap, dan clash.

Pemeriksaan tambahan:

- `git diff --check`: lulus.
- `schemas/scad.schema.json` dan `src/scad/data/scad.schema.json`: identik.
- `python3 -m py_compile` pada file produksi dan test P10: lulus.
- Mutation check: gerbang katalog `SHAPE_NOT_ALLOWED` dimatikan sementara; test `test_bored_pile_rejects_shapes_outside_catalog` gagal seperti yang diharapkan (`mutation_exit=1`). File produksi dipulihkan setelah check.

## Asumsi

- Endpoint `GET /api/element/<type>/schema` tidak menerima `features`; endpoint mengembalikan katalog utama dan katalog bursting, sedangkan UI menampilkan katalog bursting hanya bila definisi aktif memiliki `post_tensioning`.
- `purpose` yang tidak ditulis diperlakukan sebagai `main` oleh validator, sesuai default schema.
- Pile cap memakai shape stub builder `straight` yang sudah ada pada `PC_8400`; regresi geometri tidak diubah.

## Isu terbuka

- Sengkang persegi belum dapat ditawarkan sampai builder geometri tersedia.
- UI dialog tambah tulangan masih shell/mockup dan belum menyimpan rebar baru; P10 hanya mengganti sumber daftar pilihan dan penyaringan tampilannya.
- Pemodelan tendon lengkap (posisi, jumlah, dan geometri) tetap tugas lanjutan; P10 hanya memakai flag `post_tensioning`.

## Status Git

Perubahan masih berada di worktree P10 dan **belum di-commit atau di-push**.
