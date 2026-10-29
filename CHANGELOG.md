# Changelog

Riwayat ringkas. Angka tes pada entri lama adalah jejak saat itu, bukan klaim baseline sekarang.

## 2026-10 — F5 / F6

- F5: README diselaraskan dengan layout `src/`; dokumen `docs/ENGINE.md`, `docs/UI.md`, `docs/FILES.md`; `ARCHITECTURE_LAYERS.md` diperbarui; changelog digabung ke file ini.
- F6: `scad.ops.apply_operation` menjadi otoritas edit kedalaman/zona; API `/api/pile/...`; golden `examples/ops_golden.json`.

## 2026-10 — F1–F4

- F1: path traversal static ditutup (`_safe_join`).
- F2: `/run-2d` dan `/run-3d` → 501 jujur; paket `elements/` placeholder dihapus; schema dari `scad.plugins`.
- F3: `.gitignore`; static dirapikan.
- F4: packaging `src/` (`scad`, `scad_engine`, `scad_ui`); entry `scad-ui` / `scad-engine`; tanpa `sys.path` hack.

## Sebelumnya — mesin & UI prototipe

- Generic: centerline reusable, transformasi Euler, CLI + STEP opsional (satu struktur / satu batang).
- UI form penempatan (v3) dan percobaan editor project (v4): **bukan** kontrak data aktif. Kontrak aktif = `kind: project | element | shape_library` di `schemas/scad.schema.json`.
- Pilecap klasik: layout, clash, recap, section2d, cq_export — tetap di `scad_engine`, input `examples/pilecap.json`.

Entri `CHANGELOG_GENERIC.md` / `CHANGELOG_UI.md` digantikan oleh file ini (disimpan di `docs/archive/` bila masih ada salinan).

## 2026-10 — G2 / G3

- G2: `scad.files_ops` + API project/element open-save, add-element, source-diff, update-from-source; `--workspace`.
- G3: `examples/PC_8400.elem.json`; `from_v1` pile_cap memakai layout klasik agar regresi 533 batang / panjang P1–P6 sama; placement v1 penuh masih bertahap.

## 2026-10 — H2 (koreksi G1)

- Rekap G1 memisahkan panjang potong dan panjang polyline sampel, serta menampilkan total meter dan berat baja.
- Heliks dan cincin memakai sampling dengan sagitta maksimum 0,1 mm; laporan mismatch menggunakan toleransi relatif 0,1% untuk kedua bentuk tersebut.
- Ringkasan tabrakan memakai jumlah pasangan sebenarnya dan `by_mark_pair`; kegagalan pemeriksaan dilaporkan sebagai `CLASH_CHECK_FAILED`.
- Contoh B4 digeser ke `=cover+d_of('B2')+32` agar tidak menimpa bundel B1.


## 2026-10 — H2b (hotfix audit)

- Menghapus pengecualian benturan berdasarkan pasangan nama mark; seluruh pasangan tulangan kini tetap diperiksa.
- B3 pada contoh bored pile dikoreksi menjadi spiral R87 dengan pitch 200 mm. Rumus panjang potong R87 diperbaiki untuk menghitung panjang heliks berdasarkan keliling dan komponen aksial pitch.
- Ujung bawah B2 dipendekkan 200 mm melalui `extent.extend_end: -200`, sehingga terpisah 200 mm dari ujung zona B3 dan tidak bertumpang tindih pada transisi contoh.
- Regenerasi contoh P1 beserta hash sumber; tes regresi memastikan benturan B2–B3 yang disengaja tetap dilaporkan.

## 2026-10 — H3

- Pile cap v1: `from_v1` membangun batang dari `PC_8400.elem.json` (rebars + params), **tanpa** `layout.build_groups`.
- Schema `PileCapParams`: `lap_nesting`, `lap_ratio_D`, `lap_mid_height` opsional.
- `PC_8400.elem.json` valid skema; golden P1–P6 = mesin lama (tes).

## 2026-10 — H3 integrasi (mandiri dari layout)

- Builder pile_cap diganti pendekatan data-driven (RebarItem `range` / `leg_inset` / hook params).
- **Tidak** mengimpor helper privat `layout` (`_off`, `hooked_points`, …) maupun `build_groups`.
- Alias param: `lap_nesting`|`leg_layout`, `lap_ratio_D`|`lap_ratio`, `lap_mid_height`|`lap_reference_z`.
- `cover_ref` surface/centerline ditangani lokal.
