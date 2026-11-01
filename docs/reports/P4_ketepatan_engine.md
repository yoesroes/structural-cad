# Laporan P4 — Ketepatan engine

Tanggal: 2026-11-01 · Basis: P3b (di atas P2c) · Pelaksana: Claude (sandbox, tanpa jaringan)

## Ruang lingkup

Enam temuan engine dari audit: S4 (spiral `by_zone` mengabaikan `extend_*`), S5 (default
`cover_ref` pile cap), nilai 0 dianggap "tidak ada" (`or`), paritas kait P5, radius tekuk U-bar
tetap 38 mm, dan cek spasi bersih yang melewatkan pasangan < 1,5d.

Tidak diubah: server, UI, `examples/`, validator (kecuali skema parameter baru).

## Perubahan

| Berkas | Perubahan |
|--------|-----------|
| `src/scad/placement.py` | `_place_helix_by_zone` menerapkan `extend_start` (+ = naik) pada segmen teratas dan `extend_end` (+ = turun) pada segmen terbawah, memakai pitch zona terluar yang berbatasan; `cut_length` dan geometri ikut; pemendekan melebihi tinggi segmen → `ValueError` |
| `src/scad_engine/from_v1.py` | helper `_first_not_none`; `cover_ref` pile cap: params → `settings.cover_ref` → `surface`; `lap_ratio_D`/`lap_mid_height` tidak lagi memakai rantai `or` (0 sah; `lap_ratio_D <= 0` → `ValueError`); radius tekuk U-bar = `(bend_inside_radius_db + 0.5) * d` (default 2); paritas kait P5 dari indeks grid; `_min_clear_spacing` hanya melewati bundel menempel (`|jarak − d| ≤ 0,5 mm`) dan batang bertumpuk pada z (xy berimpit) |
| `src/scad/plugins/pile_cap.py` | parameter opsional `bend_inside_radius_db` (> 0) |
| `schemas/scad.schema.json`, `src/scad/data/scad.schema.json` | parameter opsional `bend_inside_radius_db`; kedua salinan identik |
| `tests/engine/test_p4_engine_accuracy.py` | 23 kasus tes baru (baru) |

## Keputusan semantik (perlu persetujuan pemilik produk)

1. **Arah `extend_*` pada spiral:** `extend_start` positif memanjangkan ke atas, `extend_end`
   positif memanjangkan ke bawah (sama dengan `extent_z_range`). Perpanjangan memakai pitch zona
   terluar yang berbatasan (atas: zona teratas; bawah: zona terbawah).
2. **Default `cover_ref` pile cap = `surface`** (sama dengan plugin dan project). Dokumen yang
   TIDAK mengisi `cover_ref` bergeser `d/2` (9,5 mm untuk D19). PC_8400 eksplisit `centerline`,
   tidak terpengaruh.
3. **Radius tekuk (D4):** default 2d setara 38 mm HANYA untuk D19. Pile cap berdiameter lain
   mendapat radius berbeda dari sebelumnya (mis. D25: 62,5 mm, sebelumnya 50,5 mm) sehingga
   panjang potong U-bar berubah. Isi `bend_inside_radius_db` bila perlu.
4. **Spasi bersih lebih ketat:** pasangan dengan jarak antara d+0,5 mm dan 1,5d kini dihitung dan
   dapat memunculkan `RULE_SPACING` baru pada project lama. Tidak ada perubahan pada P1 dan PC_8400.

## Regresi (hasil nyata)

- PC_8400: 533 batang; jumlah dan total panjang tiap mark identik dengan mesin klasik. ✔
- Rekap pile cap PC_8400: baris dan issue identik sebelum/sesudah. ✔
- P1-1: B1 56×12.280, B2 466.761,135, B4 28×20.280, B5 17×3.888,407; `RULE_SPACING` 46,6 mm tetap. ✔
- `tools/check_examples.py`: SEMUA LOLOS. Tes TypeScript: 28/28. ✔

## Tes merah sebelum perbaikan

Tes P4 dijalankan pada kode basis (sebelum perbaikan): **12 dari 23 kasus gagal**
(helix ×4, `cover_ref` default, `lap_mid_height=0`, `lap_ratio_D=0`, `cover_ref` tak dikenal,
radius tekuk, paritas P5 inset 300, spasi bersih ×2). 11 kasus lain adalah penjaga regresi
yang memang hijau di kedua versi. Setelah perbaikan: 23/23.

## Mutation check (keluaran nyata)

| Mutasi | Tes yang gagal |
|--------|----------------|
| M1 tinggi segmen tidak disesuaikan `extend_*` | `test_helix_extend_start_lengthens_top_segment_only`, `test_helix_extend_end_lengthens_bottom_segment`, `test_helix_negative_extend_end_shortens`, `test_helix_shortening_beyond_segment_raises` |
| M2 default `cover_ref` kembali `centerline` | `test_cover_ref_default_is_surface_like_plugin_and_project` |
| M3 fallback `settings.cover_ref` dihapus | `test_cover_ref_falls_back_to_project_settings_then_param_wins` |
| M4 `lap_mid_height` kembali rantai `or` | `test_lap_mid_height_zero_is_not_silently_replaced` |
| M5 paritas P5 kembali `round(x/spasi)` | `test_p5_hook_direction_alternates_along_x_and_y` |
| M6 radius tekuk kembali konstanta 38 | `test_bend_inside_radius_db_scales_with_diameter_and_validates` |
| M7 spasi bersih kembali ambang 1,5d | `test_min_clear_spacing_reports_near_overlap_that_old_rule_skipped`, `test_min_clear_spacing_reports_overlapping_bars_as_negative` |
| M8 cek `lap_ratio_D <= 0` dimatikan | `test_lap_ratio_zero_raises` |
| M9 cek "memendekkan spiral" dimatikan | `test_helix_shortening_beyond_segment_raises` |

Catatan proses: percobaan pertama M8/M9 menghapus blok sehingga menimbulkan `IndentationError`
(tes tidak berjalan, terbaca keliru "tidak terdeteksi"). Harness diperbaiki dengan penjaga
`"total kasus" in keluaran` dan mutasi `if False:`; kode produksi dipulihkan dan dibandingkan
byte-per-byte dengan salinan baik setelah setiap putaran.

## Verifikasi

Lingkungan ini tidak punya `pytest`/`jsonschema` dan tidak ada jaringan. Tes dijalankan dengan
shim `pytest` minimal (`raises`, `parametrize`, `approx`, `xfail`) dan stub `jsonschema` dari
`tools/mini_validate.py`. Hasil shim: tes P4 23/23; tes core/engine P3b 60/60 (T4 tetap xfail).

**Wajib dijalankan ulang di mesin Anda dengan pytest asli:**

```bash
PYTHONPATH=src python -m pytest tests
PYTHONPATH=src python tools/check_examples.py
node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts
```

Perkiraan hasil bila basis = 244 lulus: **267 lulus, 1 skip, 3 xfail** (S2 ×2, T4); TS 28/28.
Jika angkanya berbeda, utamakan hasil mesin Anda dan laporkan selisihnya.

## Isu terbuka / catatan

- Bundel 3 batang atau lebih: pasangan terluar (jarak 2d) tetap dibandingkan dan bisa memberi
  jarak bersih semu = d. Sudah ada sebelum P4; belum diubah.
- `PileEnv.cover_ref` pada bored pile masih tidak dipakai (posisi memakai `offset_type`).
- U-bar pile cap berdiameter selain D19 berubah panjangnya (lihat keputusan 3).
