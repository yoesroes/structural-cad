# Mesin geometri

## from_v1 API

- `build_bar_groups(doc, pile_id)`
- `recap_pile` / `recap_group`

Cabang: bored_pile (`place_rebar`, H5) | pile_cap template P1–P6 (H3).

## Katalog bentuk tulangan (P10)

Pilihan bentuk dipandu oleh plugin sesuai jenis elemen, bukan daftar global di UI.

| Jenis elemen | Tulangan utama (`allowed_shapes`) | Bursting steel |
|---|---|---|
| `bored_pile` | `R20`, `R87`, `RING` | tidak tersedia |
| `pile_cap` | `R20`, `U`, `U-INV`, `X-HOOK-135-90`, `X-HOOK-135-135` | `R87`, `RING` bila `features` memuat `post_tensioning` |

Pada pile cap, `R87` dan `RING` hanya sah bila `purpose` tulangan adalah
`bursting` dan fitur `post_tensioning` aktif. Sengkang persegi belum ditawarkan
karena builder-nya belum tersedia. Bentuk `37` dan hook tidak ditolak global;
validitasnya ditentukan oleh katalog jenis elemen.

Builder yang saat ini dihitung engine hanya `straight`, `helix`, dan `ring`.
`SHAPE_NOT_ALLOWED` berarti bentuk tidak tersedia pada konteks elemen atau
perannya, sedangkan `SHAPE_UNSUPPORTED` berarti bentuk sudah diizinkan tetapi
builder-nya belum didukung engine.

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
