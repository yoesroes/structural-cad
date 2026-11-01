# Mesin geometri

## from_v1 API

- `build_bar_groups(doc, pile_id)`
- `recap_pile` / `recap_group`

Cabang: bored_pile (`place_rebar`, H5) | pile_cap template P1–P6 (H3).

## H5

B5 cincin Z0; B2 spiral menerus `by_zone`; R87 v2; `shape_param`.
Panjang helix = hipotenusa (`helix_cut_length_segment`).

## RULE_SPACING

Dihitung di XY untuk mark sama; cincin B5 berbagi (x,y) dapat memicu peringatan.

## Bentuk totals `recap_group` (P5 / T4)

`recap_group` mengagregasi baris rekap per pile dengan kunci **`(mark, cut_length_mm)`**
(cut dibulatkan 3 desimal). Mark yang punya beberapa panjang potong (mis. B4 pada P1
karena kedalaman berbeda, atau P6 pada pile_cap) muncul sebagai **beberapa baris**.

Tiap baris totals memuat: `mark`, `id` (= mark), `diameter`, `count`, `length_mm`,
`cut_length_mm`, `geometry_length_mm`, `total_length_mm`, `total_length_m`, `weight_kg`.

Invarian: `count * cut_length_mm == total_length_mm` (toleransi 1e-3 mm).
Urutan stabil: urutan kemunculan mark, lalu panjang potong menurun.
