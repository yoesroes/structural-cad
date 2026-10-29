# G1 — Jembatan v1 -> batang (penyelesai posisi + pembangun bentuk)
Prasyarat: F4 selesai. INI langkah yang menyatukan proyek. Baca `docs/` (spesifikasi skema) dan `tasks/00_KONTEKS.md` butir 5-6.
**Tujuan:** dari dokumen project v1 hasilkan batang per pile sebagai `BarGroup` (model di `scad_engine/model.py`) supaya potongan, tabrakan, dan rekap yang sudah ada bisa dipakai. Cakupan: elemen `bored_pile` dengan bentuk `R20` (lurus), `R87` (spiral), `RING`.
**Berkas boleh dibuat/diubah:** `src/scad/shapes.py`, `src/scad/placement.py` (murni, tanpa impor `scad_engine`), `src/scad_engine/from_v1.py`, `src/scad_ui/server.py` (endpoint tambahan), tes.
**Antarmuka:**
```python
# scad/shapes.py
def build_centerline(shape_def: dict, shape_params: dict, diameter: float, env: dict) -> "Centerline"  # titik 3D lokal (+ metadata: panjang geometri, tertutup?)
def cut_length_formula(shape_def, shape_params, diameter, env) -> float | None
# scad/placement.py
def place_rebar(item: dict, env: "PileEnv") -> list["Placed"]   # Placed: shape_key, origin(x,y,z), tag
# scad_engine/from_v1.py
def build_bar_groups(doc: dict, pile_id: str) -> list[BarGroup]
def recap_pile(doc: dict, pile_id: str) -> dict      # {"rows": [...], "issues": [...]}
def recap_group(doc: dict, group_id: str) -> dict    # per pile + total
```
**Aturan:**
- Lingkungan ekspresi: parameter definisi (setelah penimpaan pile), `d`, `d_of(id)`, `zone_length(id)`, `pi`; zona dari `scad.zones.resolve_zones` (z relatif COF, positif ke atas). Rentang batang = gabungan zona di `extent.zones` + `extend_start` (ke atas) / `extend_end` (ke bawah).
- Posisi `ref: concrete, face: outer`: jari-jari sumbu = D/2 - offset - d/2 bila `offset_type: clear`, D/2 - offset bila `center`; `cover_ref` dari params menentukan bawaan.
- Susunan: `polar` (count, bundle tangensial, start_angle), `linear axis z` (posisi z = awal rentang + i*spacing selama <= akhir rentang; dilaporkan jumlah dan sisa), `single` (spiral). Cukup translasi (batang lurus vertikal, cincin, heliks); rotasi tidak perlu.
- Panjang geometri dibandingkan dengan rumus `cut_length` bentuk; selisih di atas toleransi -> Issue `LEN_MISMATCH` (warning). Jarak bersih terkecil antar batang dibanding `settings.rules.min_clear_spacing` -> `RULE_SPACING` (warning). Tabrakan memakai `scad_engine.clash.find_clashes`.
- Endpoint tambahan (aditif): `GET /api/pile/{id}/recap` dan `GET /api/group/{id}/recap`.
**Nilai acuan (hitung tangan, verifikasi ulang) untuk `examples/P1.project.json`, pile P1-1:** B1: 56 batang (28 lokasi x bundel 2), panjang 12300 mm, jari-jari sumbu 493 mm; B2: satu heliks, 40 putaran, panjang rumus C/B*pi*(A-d) = 129936.3 mm; B3: 41 cincin, panjang tiap cincin pi*(A-d)+lap = 3888.4 mm; B4: 28 batang x 20280 mm (Z3 19000 + 40d). P1-2 (kedalaman 26000): B4 = 28 x 16280 mm. P1-8 (Z2 = 7000): B1 = 56 x 11300 mm. Jarak bersih antar bundel B1 sekitar 46.4 mm (< 75) sehingga `RULE_SPACING` HARUS muncul pada contoh.
**Kriteria selesai:** tes memverifikasi angka di atas (toleransi 0,5 mm untuk panjang); jumlah batang total per pile; di zona lewatan z = -10000 mm potongan datar menembus 84 batang (B1 56 + B4 28) jika G5 sudah ada, atau hitung dengan `cut_section` ekstensi sementara; `LEN_MISMATCH` tidak muncul untuk R20/R87/RING contoh; rekap per grup menjumlahkan 9 pile; arah impor `scad -> scad_engine` tidak dilanggar (tes F4 tetap lolos).
