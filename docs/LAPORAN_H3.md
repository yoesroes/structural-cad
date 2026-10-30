# Laporan H3 — G3 sungguhan: pile cap dari definisi v1

**Basis:** `H2b_repo_H4_selesai` → hasil di `artifacts/cad_h3/`  
**Konteks:** `tasks/00_KONTEKS.md`, `01_KONTEKS_TAMBAHAN.md`

## Berkas diubah/dibuat

| Path | Perubahan |
|------|-----------|
| `src/scad_engine/from_v1.py` | Hapus `_bar_groups_pile_cap_legacy` + `layout.build_groups`. Tambah `_v1_definition_to_cfg` + `_pile_cap_geometry_from_cfg` (algoritma setara layout, dipanggil dari rebars/params v1). AST: **tidak** ada `build_groups`. |
| `examples/PC_8400.elem.json` | Valid skema; params `cover_side_x/y`, `lap_nesting`; rebars P1–P6 + shapes stub |
| `schemas/scad.schema.json` + `src/scad/data/scad.schema.json` | `PileCapParams` opsional: `lap_nesting`, `lap_ratio_D`, `lap_mid_height` |
| `src/scad/plugins/pile_cap.py` | Metadata param yang sama |
| `tests/engine/test_g3_pile_cap.py` | Validasi PC_8400, AST, golden vs `layout.build_groups` **hanya di tes** |
| `tests/test_examples_valid.py` | Hapus allowlist invalid untuk PC_8400 |
| `CHANGELOG.md` | Entri H3 |

## Uji

```text
pytest tests/engine/test_g3_pile_cap.py tests/test_examples_valid.py → 8 passed
pytest (penuh) → lihat angka di bawah
```

Golden (toleransi tugas): P1–P4 count 83, P5 169, P6 32 (total 533); panjang P1=P3 11181.2, P2=P4 10843.2, P5 2444.5, P6 8405.7/8443.7; 4338.76 m, 9214.7 kg; `bottom_inside` → 166 clash.

## Keputusan / asumsi

1. Geometri numerik tetap algoritma yang sama dengan mesin lama (helper `hooked_points`, `_off`, dll. diimpor dari `layout`), tetapi **orikestrasi** dari `definition.rebars` + `params`, bukan file `pilecap.json`.
2. Builder bentuk U/hook di `shapes.py` masih stub (`straight`); detail centerline U/kait dihitung di lapisan geometri pile_cap (setara layout) agar angka golden tercapai tanpa tautologi lewat `build_groups`.
3. `lap_nesting` resmi di params (bukan `x_legacy_options`).

## Isu tersisa

- Placement generik G1 (`place_rebar`) belum menafsirkan relasi `ref: bar` untuk pile_cap; jalur pile_cap khusus di `from_v1`.
- Refactor berikutnya: pindahkan geometri U/kait ke `shapes.py` / `placement.py` murni agar tidak bergantung pada helper privat `layout`.
