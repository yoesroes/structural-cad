# Laporan F1–F4

**Lokasi kerja:** `/home/workdir/artifacts/cad_f1_f4/`  
**Folder asli `cad_generic/` tidak diubah.**

## 1. Berkas diubah / dibuat / dihapus

### F1 — Path traversal
- Diubah: `pilecap_rebar/ui.py` → (setelah F4) `src/scad_ui/server.py`
  - Fungsi `_safe_join(base, rel)`
  - `serve_static` memakai resolve + `is_relative_to`
  - Peringatan stderr bila `--host` non-loopback
- Diubah: `tests/test_ui.py` → `tests/ui/test_ui.py` (tes HTTP port 0)

### F2 — Hapus placeholder
- Dihapus: seluruh `pilecap_rebar/elements/`
- `/run-2d`, `/run-3d` → HTTP 501 `NOT_IMPLEMENTED`
- `/save-project` dihapus (404)
- `GET /api/element/<type>/schema` dari `scad.plugins.get_plugin`
- Tes yang memakai `elements.registry` diganti ke plugin scad

### F3 — Kebersihan
- Baru: `.gitignore`
- Dihapus dari `static/`: mockup duplikat, `Spesifikasi_*.md` (pindah `docs/archive/`), `css/`, `js/` (tidak direferensikan `index.html`)
- Cache `__pycache__` / `.pytest_cache` dibersihkan

### F4 — Packaging src/
```
src/scad/           (ex core/scad)
src/scad_engine/    (ex pilecap_rebar tanpa ui/static/elements)
src/scad_ui/        (server.py + static/)
src/pilecap_rebar/  (shim + DeprecationWarning)
tests/core|engine|ui/
```
- `pyproject.toml` baru (nama paket `scad`, skrip `scad-ui`, `scad-engine`)
- Semua `sys.path` di `src/` dan `tests/` dihapus
- `web/package.json` test → `node --experimental-strip-types --test`
- Legacy: `core_LEGACY_pre_F4/`, `pilecap_rebar_LEGACY_pre_F4/` (boleh dihapus setelah review)

## 2. Hasil uji

| Suite | Hasil |
|-------|--------|
| `pip install -e .[dev]` lalu `pytest` | **141 passed, 3 skipped** (≥ baseline 133) |
| `node --experimental-strip-types --test src/**/*.test.ts` (web) | **15/15 pass** |
| `scad-ui --help` / `scad-engine --help` | OK |
| `import scad, scad_engine, scad_ui, pilecap_rebar` | OK |
| `import core` | gagal (diharapkan) |
| `grep -rn sys.path src tests` | kosong |

## 3. Asumsi / keputusan
- Aset `static/css` dan `static/js` dihapus karena `index.html` 100% inline.
- Shim `pilecap_rebar` tetap ada agar impor lama tidak putus (dengan DeprecationWarning).
- Folder legacy pre-F4 disimpan dengan suffix `_LEGACY_pre_F4` di dalam work tree (bukan di `cad_generic`).

## 4. Isu tersisa
- F5 (sinkron README) belum dikerjakan.
- F6 (satukan edit kedalaman) belum.
- G1 (v1 → batang) belum — inti masih terputus dari geometri.
- CadQuery/ezdxf tidak diuji di lingkungan ini (tes terkait di-skip).
