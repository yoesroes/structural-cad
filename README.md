# Structural CAD

Aplikasi **lokal** untuk mendefinisikan **satu stasiun pier** (bored pile → pile cap; nanti pier / pier head) beserta tulangannya.

- Satu file project = satu lokasi (mis. `P1.project.json`), bukan jembatan penuh.
- JSON adalah sumber kebenaran; 2D / 3D / rekap adalah hasil turunan.
- Tanpa cloud, akun, atau HP.

## Instalasi

Python ≥ 3.10.

```bash
pip install -e ".[dev]"
pip install -e ".[cad]"     # opsional
```

## Menjalankan

```bash
scad-ui
scad-engine --json examples/pilecap.json --out output
bash scripts/ci.sh
```

Verifikasi: jalankan `bash scripts/ci.sh` (venv `[dev]`, Node ≥ 22 untuk tes TypeScript).

## Status fitur (jujur)

| Fitur | Status |
|-------|--------|
| Load / validate / resolve | berfungsi |
| Edit kedalaman & zona | berfungsi; resolve error **pada pile yang diedit** memblokir |
| Open / Save / Save-as | berfungsi |
| update-from-source | berfungsi; **D1:** issue resolve error **global** membatalkan update (sesi tidak berubah) |
| Rekap pile / grup | berfungsi |
| POST /run-2d, /run-3d | menghasilkan berkas/JSON; UI belum menampilkan SVG |
| Keamanan HTTP + escapeHtml | berfungsi |
| UI shell | berfungsi (menu belum siap: disabled) |
| Katalog bentuk tulangan per elemen | berfungsi; bursting steel memakai flag `post_tensioning` |
| CadQuery / ezdxf | extras `[cad]` |

## CI

- Lokal: `bash scripts/ci.sh`
- GitHub Actions: Node **22**, Python 3.12

## Dokumentasi

`tasks/00_KONTEKS.md`, `docs/UI.md`, `docs/ENGINE.md`, `docs/STATUS_P0_P8.md`, `docs/archive/ARCHITECTURE_AUDIT.md`, `docs/reports/`, `CHANGELOG.md`.

Kontrak: `schemas/scad.schema.json`.

### Bentuk tulangan yang ditawarkan

| Elemen | Bentuk utama | Bentuk bursting steel |
|---|---|---|
| `bored_pile` | `R20`, `R87`, `RING` | — |
| `pile_cap` | `R20`, `U`, `U-INV`, `X-HOOK-135-90`, `X-HOOK-135-135` | `R87`, `RING` bila `post_tensioning` aktif |

Daftar ini berasal dari plugin dan dipakai API/UI; bentuk yang tidak relevan
tidak ditampilkan. Pada pile cap, bursting steel harus memakai
`purpose: "bursting"`. Sengkang persegi belum tersedia karena builder geometri
belum ada.
