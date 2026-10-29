# Structural CAD

Aplikasi **lokal** untuk mendefinisikan **satu stasiun pier** (bored pile → pile cap; nanti pier / pier head) beserta tulangannya.

- Satu file project = satu lokasi (mis. `P1.project.json`), bukan jembatan penuh.
- JSON adalah sumber kebenaran; 2D / 3D / rekap adalah hasil turunan.
- Tanpa cloud, akun, atau HP.

## Instalasi

Python ≥ 3.10.

```bash
pip install -e ".[dev]"     # jsonschema + pytest
pip install -e ".[cad]"     # opsional: CadQuery, ezdxf (STEP/DXF)
```

Dependensi juga tercermin di `requirements.txt` / `requirements-dev.txt` / `requirements-cad.txt` (penunjuk ke pyproject).

## Menjalankan

```bash
scad-ui                              # http://127.0.0.1:8765
scad-engine --json examples/pilecap.json --out output
pytest -q
node --experimental-strip-types --no-warnings --test web/src/**/*.test.ts
```

Diverifikasi: `scad-ui --help` OK; `scad-engine --help` OK; **pytest 200 passed, 1 skipped** (H3+H5; jalankan ulang di mesin Anda).

## Peta folder

```
src/scad/           dokumen v1 (expr, io, validate, zones, plugins, resolve, ops)
src/scad_engine/    mesin geometri (layout, clash, recap, STEP, generic, from_v1)
src/scad_ui/        server HTTP + static/
src/pilecap_rebar/  shim deprecated
tests/              core/, engine/, ui/
schemas/ examples/ web/ docs/ tools/ tasks/
```

## Status fitur (jujur)

| Fitur | Status |
|-------|--------|
| Load / validate / resolve project v1 | berfungsi |
| Edit kedalaman & zona (ops + API) | berfungsi |
| Plugin metadata bored_pile / pile_cap | berfungsi |
| UI shell monolit (index.html) | sebagian |
| Open/Save project path arbitrer | berfungsi (`/api/project/{open,save,save-as}`) |
| 2D / 3D dari project v1 | belum (501) |
| Rekap / SVG / STEP dari `pilecap.json` lama | berfungsi (mesin klasik) |
| Pile cap v1 template P1–P6 (builder + rekap engine/API) | berfungsi (H3; lihat `docs/H3_RELEASE.md`) |
| Pile cap v1 generik (mark/bentuk bebas) | belum (S7 ditunda) |
| Jembatan v1 → batang (bored pile) | berfungsi (G1/H2) |
| Sengkang bored: cincin Z0 + spiral by_zone (R87 v2) | berfungsi (H5; lihat `LAPORAN_H5.md`) |
| CadQuery STEP / ezdxf DXF | bergantung extras `[cad]` |

## Dokumentasi

| File | Isi |
|------|-----|
| `tasks/00_KONTEKS.md` | Keputusan final (wajib) |
| `docs/ARCHITECTURE_LAYERS.md` | Batas lapisan setelah F4 / H3 / H5 |
| `docs/FILES.md` | Project vs elemen, hash |
| `docs/UI.md` | Endpoint server yang benar-benar ada |
| `docs/ENGINE.md` | Mesin tulangan v1, klasik & generic |
| `docs/H3_KONTRAK_PILE_CAP.md` | Kontrak pile_cap (S4) |
| `docs/H3_RELEASE.md` | Catatan rilis perbaikan H3 |
| `docs/H3_STATUS_PERUBAHAN.md` | Status tahap H3/H5 |
| `LAPORAN_H3.md` | Laporan rilis H3 |
| `LAPORAN_H5.md` | Laporan sengkang bored pile H5 |
| `CHANGELOG.md` | Riwayat ringkas |

Kontrak data: `schemas/scad.schema.json`, contoh `examples/P1.project.json`.
