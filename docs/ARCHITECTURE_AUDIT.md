# Audit kepatuhan — ARCHITECTURE_LAYERS.md

Tanggal audit: 2026-10-23

## Ringkasan

**Tidak ada pelanggaran batas lapisan yang mewajibkan perubahan kode.**
Tiga jalur tetap terpisah sesuai aturan dokumen arsitektur.

## Pemeriksaan impor silang

| Dari → Ke | Diizinkan? | Temuan |
|-----------|------------|--------|
| Mesin klasik (`layout`, `model`, `clash`, `recap`, `section2d`, `draw`, `cq_export`, `cli`) → `scad` / `core.scad` | Tidak (sampai port resmi) | **Tidak ada** impor `scad` |
| `generic.py` / `generic_cli.py` → `cq_export` / `model` | Ya (ketergantungan sadar) | Ada; sesuai aturan |
| `ui.py` → `scad.*` | Ya (UI membaca core v1) | Ada (`io.files`, `validate`, `resolve`) |
| `web/src/commands` → mesin klasik / `scad` Python | N/A (TS murni) | Tidak di-bundle ke UI aktif |
| Plugin `core/scad/plugins` | Metadata saja | Tidak menghasilkan centerline/STEP |

## Status tiap lapisan

1. **Mesin pile cap lama** — input masih skema `examples/pilecap.json`; tidak menyentuh `kind: project` v1.
2. **Fondasi generik** — satu struktur + satu batang; bukan solver multi-pile v1.
3. **Core dokumen v1** — expr / io / validate / zones / resolve / plugins; belum bangun geometri tulangan penuh.
4. **UI aktif** — `ui.py` + `index.html` (inline); `app.js` warisan tidak ter-link.
5. **T10** — modul logika di `web/`; status eksplisit di `web/README.md`.

## Port yang masih di roadmap (bukan pelanggaran)

1. Solver posisi generik membaca `RebarItem` v1 → daftar batang.
2. Plugin menghasilkan centerline (bukan hanya metadata).
3. Bungkus `layout.py` di belakang API yang sama; regresi ~533 batang.
4. Satukan ekspor 2D/3D ke satu orkestrator.

Sampai langkah di atas selesai, **tiga lapisan tetap terpisah**.
