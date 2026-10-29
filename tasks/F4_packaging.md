# F4 — Pengemasan: tata letak src/, pyproject, tanpa sys.path hack
Prasyarat: F3 selesai. Tugas ini memindahkan banyak berkas; kerjakan sendirian (jangan paralel dengan tugas lain).
**Berkas boleh diubah:** seluruh pohon Python, `pyproject.toml` (baru), `requirements.txt` (hapus atau jadi penunjuk), `web/package.json`, tes.
**Target tata letak:**
```
src/scad/          <- core/scad (hapus core/__init__.py dan core/)
src/scad_engine/   <- pilecap_rebar: model layout section2d clash recap draw cq_export step_audit cli generic generic_cli
src/scad_ui/       <- pilecap_rebar/ui.py (jadi server.py) + static/
src/pilecap_rebar/ <- paket SHIM yang mengekspor ulang scad_engine (DeprecationWarning), agar skrip lama tidak putus
tests/             <- gabungan core/tests dan tests (subfolder core/, engine/, ui/)
```
**Langkah:**
1. `pyproject.toml` (setuptools, layout src): nama `scad`, dependensi inti `jsonschema>=4`; extras `cad = [cadquery>=2.4, ezdxf>=1.1]`, `dev = [pytest]`. Skrip konsol: `scad-ui = scad_ui.server:main`, `scad-engine = scad_engine.cli:main`.
2. Pindahkan berkas, perbaiki impor (relatif di dalam paket, absolut antar paket). Arah impor: `scad_ui -> scad_engine -> scad`; periksa tidak ada kebalikannya (tambahkan tes yang memindai impor dengan `ast`).
3. Hapus SEMUA `sys.path.insert/append` (grep) dan `core/__init__.py`. Satu nama impor saja: `scad`.
4. `web/package.json`: skrip `test` = `node --experimental-strip-types --no-warnings --test src/**/*.test.ts` (tes memakai `node:test`; hapus vitest dari devDependencies bila tidak dipakai).
5. Perbarui path di `tools/`, `tasks/`, README (README penuh disinkronkan di F5; cukup perbaiki perintah yang rusak).
**Kriteria selesai:** dari akar repo pada lingkungan bersih: `pip install -e .[dev]` lalu `pytest -q` menjalankan SEMUA tes Python dan jumlah lolos >= baseline (133); `npm --prefix web test` -> 15 lolos; `scad-ui --help` dan `scad-engine --help` bekerja; `grep -rn "sys.path" src tests` kosong; `python -c "import scad, scad_engine, scad_ui, pilecap_rebar"` berhasil dan `import core` gagal.
**Jangan:** mengubah logika; ini hanya pemindahan dan perapian.
