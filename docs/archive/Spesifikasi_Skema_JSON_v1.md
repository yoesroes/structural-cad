Spesifikasi Skema JSON v1 — Structural CAD
Draf untuk ditinjau. Belum ada kode. Cakupan: berkas project, berkas elemen, library bentuk tulangan, aturan penyelesaian, validasi, dan versi.
1. Prinsip
• Satu sumber data. File JSON hanya menyimpan keputusan perancang. Posisi tiap batang, panjang potong, rekap, dan gambar adalah hasil turunan dan tidak disimpan.
• Project mandiri. Definisi elemen dan bentuk tulangan yang dipakai disalin ke dalam file project (keputusan: salinan tertanam, diperbarui manual).
• Hanya yang berbeda yang disimpan per pile. Nilai bertingkat: definisi → default grup → penimpaan per pile.
• Ketat. Kunci yang tidak dikenal ditolak, kecuali di bawah meta dan kunci berawalan x_.
• Posisi dinyatakan sebagai aturan (terhadap beton atau tulangan lain), bukan koordinat mentah.
2. Jenis berkas
Berkas
Ekstensi
kind
Isi
Project (lokasi, mis. P1)
.project.json
project
Grup elemen, tabel pile, material, pengaturan
File elemen
.elem.json
element
Satu ElementDefinition yang bisa dipakai ulang
Library bentuk (opsional)
.shapes.json
shape_library
Kumpulan ShapeDef milik user
3. Konvensi umum
• Satuan: panjang dan elevasi dalam mm, sudut dalam derajat. UI boleh menampilkan meter, file tetap mm. Kunci units dicadangkan (v1 hanya "mm").
• ID: string ^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$, unik dalam cakupannya (pile: unik dalam project; tulangan dan zona: unik dalam elemen).
• Ekspresi: nilai numerik boleh berupa string berawalan =, mis. "=40*d". Variabel: parameter elemen (diameter, cover, …), d (diameter batang itu), r (radius dalam bengkok), d_of('B2'), zone('Z1').length, pi. Fungsi: min max ceil floor round. Tidak ada akses atribut, loop, atau pemanggilan lain.
• Koordinat lokal elemen ditetapkan plugin: bored pile = sumbu pile di (0,0), z = 0 di COF, z positif ke atas. Pile cap = sudut (0,0,0) di dasar, x panjang, y lebar, z ke atas.
• Format berkas: UTF-8, indentasi 2 spasi, urutan kunci tetap menurut skema (ramah Git).
4. ElementDefinition
Kunci
Tipe
Keterangan
type
string
ID plugin: bored_pile, pile_cap, …
type_version
integer
Versi skema parameter plugin
name
string
Nama tampilan
params
object
Divalidasi oleh skema plugin (4.4)
materials
Materials
Opsional; menimpa material project
zones
Zone[]
Opsional (4.3)
rebars
RebarItem[]
Daftar tulangan (4.5)
4.1 Materials
"materials": {"concrete": {"grade": "fc30", "type": "readymix"},
              "steel": {"grade": "fy420", "type": "ulir"}}
Nilai berupa string bebas (daftar pilihan ada di konfigurasi aplikasi, bukan di skema). Sebuah RebarItem boleh menimpa steel.
4.3 Zone
Kunci
Aturan
id
wajib, unik
side
above_cof atau below_cof (bawaan). Zona above_cof bertumpuk ke atas dari COF, zona below_cof bertumpuk ke bawah dari COF, urut menurut daftar
length
angka (mm) atau "rest"
Aturan: paling banyak satu "rest", hanya pada zona below_cof terakhir. Zona fleksibel menyerap selisih kedalaman: rest = depth_below_cof − jumlah zona below_cof tetap. Bila depth_below_cof lebih kecil dari jumlah zona tetap: error ZONE_DEPTH_SHORT.
4.4 Parameter plugin
Plugin
Parameter
Keterangan
bored_pile
diameter, depth_below_cof, cover, cover_ref
cover_ref: surface atau centerline
pile_cap
length, width, height, cover_top, cover_bottom, cover_side_x, cover_side_y, cover_ref

Plugin lain (pier, pier head, girder, slab) menambah skema parameternya sendiri; UI membangun formnya dari skema itu.
4.5 RebarItem
Kunci
Tipe
Keterangan
id
string
Wajib, unik. Juga dipakai sebagai mark bawaan
mark
string
Opsional, tampil di gambar dan rekap
shape
{code, version?}
Rujukan ke library (bagian 5)
shape_params
object
Nilai parameter bentuk (angka atau ekspresi). Parameter bertanda from_extent diisi otomatis dari panjang rentang
diameter
number
mm
steel
object
Opsional, menimpa baja
orientation
enum
vertical, horizontal, longitudinal, transverse (sumbu utama bentuk terhadap sumbu lokal elemen)
facing
enum
Arah sisi bengkok: inward (bawaan), outward, up, down, +x, -x, +y, -y
extent
object
zones: daftar zona; extend_start, extend_end: perpanjangan (mm atau ekspresi, mis. "=40*d")
position
Position
4.6
arrangement
Arrangement
4.7
4.6 Position
{"ref": "concrete", "face": "top", "offset_type": "center", "offset": 100}
{"ref": "bar", "bar": "P3", "relation": "below", "gap": 0}
• ref: concrete: face menurut plugin (bored pile: outer; pile cap: top, bottom, x-, x+, y-, y+). offset_type: clear (ke permukaan batang) atau center (ke sumbu). Bawaan mengikuti cover_ref project.
• ref: bar: relation ∈ above, below, inside, outside, left, right. gap adalah jarak bersih antar permukaan (0 = bersentuhan).
• Ketergantungan antar tulangan diurutkan otomatis. Siklus ditolak (POS_CYCLE). Bila batang acuan tidak mencakup seluruh zona batang yang bergantung, atau diameternya berbeda antar zona: POS_REF_AMBIGUOUS.
4.7 Arrangement
{"mode": "single"}
{"mode": "group", "pattern": "linear", "axis": "y", "by": "spacing", "spacing": 100,
 "range": {"from": 100, "to": "=width-100"}, "align": "start", "bundle": 1}
{"mode": "group", "pattern": "polar", "by": "count", "count": 28, "bundle": 2, "start_angle_deg": 0}
• by: count atau spacing (tidak boleh keduanya: ARR_BAD).
• range.from dan range.to adalah posisi sumbu batang pada sumbu pola. Contoh: from 100, to 8300, spacing 100 menghasilkan floor((8300−100)/100)+1 = 83 batang. Dengan satu aturan eksplisit ini, selisih 82 vs 83 tidak lagi bergantung pada konvensi selimut.
• align untuk by: spacing: start (bawaan; sisa jarak di ujung dilaporkan), center (sisa dibagi dua), end, fit (jarak sebenarnya = (to−from)/(n−1) dengan n = ceil((to−from)/spacing)+1, selalu ≤ jarak nominal).
• bundle 1–4: batang menempel bersinggungan di tiap lokasi (mis. 2×28).
• Hasil penyelesaian selalu melaporkan jumlah, jarak sebenarnya, dan sisa ujung.
5. Library bentuk tulangan (ShapeDef)
Kunci
Keterangan
code, version
Kode (mis. R20, 37, RING) dan versi bentuk
name, standard
Nama dan asal (mis. BS8666:37, atau null untuk kustom)
params
[{name, label, default?, from_extent?}]
builder
Cara membangun jalur sumbu (di bawah)
cut_length
Ekspresi rumus panjang potong dari standar, untuk uji silang
cut_tolerance_per_bend
Toleransi selisih rumus vs geometri per bengkok
derived_from, override, add_hooks
Untuk bentuk kustom turunan
Jenis builder v1: straight, polyline_outside (titik berdimensi luar; jalur sumbu diperoleh dengan menggeser d/2 dan membulatkan sudut dengan radius dalam r), helix, ring.
Uji silang panjang. Rumus pada bagan standar adalah pendekatan. Untuk bengkok 90° dengan radius dalam r = 2d, geometri sumbu lebih pendek sekitar 0,07d daripada rumus A + B − 0,5r − d. Karena itu perbandingan memakai toleransi (bawaan 0,25d per bengkok), bukan kesamaan persis.
{"code": "R20", "version": 1, "name": "Lurus", "standard": "BS8666:20",
 "params": [{"name": "A", "label": "Panjang", "from_extent": true}],
 "builder": {"type": "straight", "length": "=A"}, "cut_length": "=A"}

{"code": "R87", "version": 1, "name": "Spiral", "standard": "BS8666:87",
 "params": [{"name": "A", "label": "Diameter luar"}, {"name": "B", "label": "Spasi (pitch)"},
            {"name": "C", "label": "Tinggi", "from_extent": true}],
 "builder": {"type": "helix", "outer_diameter": "=A", "pitch": "=B", "height": "=C"},
 "cut_length": "=C/B*pi*(A-d)",
 "notes": "Simbol pada bagan terbaca 'n'; diasumsikan pi. Verifikasi ke standar."}

{"code": "RING", "version": 1, "name": "O-ring", "standard": null,
 "params": [{"name": "A", "label": "Diameter luar"}, {"name": "lap", "label": "Lewatan", "default": "=40*d"}],
 "builder": {"type": "ring", "outer_diameter": "=A", "lap": "=lap"},
 "cut_length": "=pi*(A-d)+lap"}

{"code": "X-HOOK-135-90", "version": 1, "name": "Lurus, kait 135° (6d) dan 90° (12d)",
 "derived_from": "R20",
 "add_hooks": [{"end": "start", "angle_deg": 135, "tail": "=6*d"},
               {"end": "end", "angle_deg": 90, "tail": "=12*d"}]}
• angle_deg pada kait adalah sudut belok. tail adalah panjang bagian lurus setelah busur bengkok.
• Tingkat library: bawaan (hanya-baca), milik user (.shapes.json), dan salinan di project. Bentuk yang dipakai selalu disalin ke shapes di dalam project atau file elemen, dengan version, supaya project tetap bisa digambar ulang meski library berubah.
6. Berkas project
Kunci
Keterangan
kind, schema_version
"project", 1
project
id, name, datum.cof_elevation (mm)
settings
cover_ref, bend_inside_radius (default ekspresi, by_diameter), rules (batas minimum yang Anda tetapkan: min_clear_spacing, min_cover, max_spiral_spacing; tanpa nilai bawaan)
materials
Material bawaan project
shapes
Salinan ShapeDef yang dipakai
groups
Daftar grup elemen
meta
Waktu dibuat dan diubah, versi aplikasi
Group: id, type, definition, naming (pattern, start), defaults.params, instances.
definition: source (file, hash, added_at, atau null bila dibuat langsung di project) dan data (salinan ElementDefinition). hash = SHA-256 dari JSON kanonik (kunci terurut, tanpa spasi). Status "menyimpang dari sumber" dihitung dengan membandingkan hash, tidak disimpan.
Instance (pile): id, x, y, rotation_deg (opsional), overrides.
Urutan nilai (paling akhir menang): definition.data.params → group.defaults.params → instance.overrides.params. Panjang zona dapat ditimpa lewat overrides.zone_lengths (mis. {"Z2": 7000}). Penimpaan tulangan per pile dicadangkan untuk v2.
7. Contoh
7.1 BP_D1200.elem.json
{
  "kind": "element",
  "schema_version": 1,
  "definition": {
    "type": "bored_pile", "type_version": 1, "name": "Bored pile D1200",
    "params": {"diameter": 1200, "depth_below_cof": 30000, "cover": 75, "cover_ref": "surface"},
    "materials": {"concrete": {"grade": "fc30", "type": "readymix"},
                  "steel": {"grade": "fy420", "type": "ulir"}},
    "zones": [
      {"id": "Z0", "side": "above_cof", "length": 1300},
      {"id": "Z1", "length": 3000},
      {"id": "Z2", "length": 8000},
      {"id": "Z3", "length": "rest"}
    ],
    "rebars": [
      {"id": "B1", "shape": {"code": "R20"}, "diameter": 32, "orientation": "vertical",
       "extent": {"zones": ["Z0", "Z1", "Z2"]},
       "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover+d_of('B2')"},
       "arrangement": {"mode": "group", "pattern": "polar", "by": "count", "count": 28, "bundle": 2}},
      {"id": "B2", "shape": {"code": "R87"}, "diameter": 16, "orientation": "vertical",
       "shape_params": {"A": "=diameter-2*cover", "B": 75},
       "extent": {"zones": ["Z1"]},
       "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover"},
       "arrangement": {"mode": "single"}},
      {"id": "B3", "shape": {"code": "RING"}, "diameter": 16, "orientation": "horizontal",
       "shape_params": {"A": "=diameter-2*cover"},
       "extent": {"zones": ["Z2"]},
       "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover"},
       "arrangement": {"mode": "group", "pattern": "linear", "axis": "z", "by": "spacing", "spacing": 200}},
      {"id": "B4", "shape": {"code": "R20"}, "diameter": 32, "orientation": "vertical",
       "extent": {"zones": ["Z3"], "extend_start": "=40*d"},
       "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover+16"},
       "arrangement": {"mode": "group", "pattern": "polar", "by": "count", "count": 28, "bundle": 1}}
    ]
  }
}
7.2 P1.project.json (disingkat)
{
  "kind": "project",
  "schema_version": 1,
  "project": {"id": "P1", "name": "Pier P1", "datum": {"cof_elevation": 12350}},
  "settings": {"cover_ref": "surface",
               "bend_inside_radius": {"default": "=2*d", "by_diameter": {"19": 38, "16": 32}},
               "rules": {"min_clear_spacing": 75}},
  "materials": {"concrete": {"grade": "fc30", "type": "readymix"},
                "steel": {"grade": "fy420", "type": "ulir"}},
  "shapes": {"R20": {"…": "salinan ShapeDef"}, "R87": {"…": "salinan ShapeDef"}},
  "groups": [{
    "id": "BP-P1", "type": "bored_pile",
    "definition": {"source": {"file": "BP_D1200.elem.json", "hash": "sha256:9f2c…", "added_at": "2026-10-23T09:00:00Z"},
                   "data": {"…": "salinan ElementDefinition (7.1)"}},
    "naming": {"pattern": "P1-{n}", "start": 1},
    "defaults": {"params": {"depth_below_cof": 30000}},
    "instances": [
      {"id": "P1-1", "x": -3000, "y": -3000},
      {"id": "P1-2", "x": 0, "y": -3000, "overrides": {"params": {"depth_below_cof": 26000}}},
      {"id": "P1-3", "x": 3000, "y": -3000}
    ]
  }],
  "meta": {"created": "2026-10-23T09:00:00Z", "app_version": "0.1"}
}
Hasil penyelesaian: P1-1 memiliki Z3 = 30000 − 3000 − 8000 = 19000 mm, P1-2 memiliki Z3 = 15000 mm. Cincin, spiral, panjang batang lurus, dan BBS dihitung ulang per pile.
7.3 Pemetaan pasangan P3/P1 pile cap
Pasangan yang dulu salah berimpit kini dinyatakan eksplisit: P1 "di bawah P3", bersentuhan.
{"id": "P3", "orientation": "longitudinal", "facing": "down",
 "position": {"ref": "concrete", "face": "top", "offset_type": "center", "offset": 100},
 "arrangement": {"mode": "group", "pattern": "linear", "axis": "y", "by": "spacing", "spacing": 100,
                 "range": {"from": 100, "to": "=width-100"}}}
{"id": "P1", "orientation": "transverse", "facing": "down",
 "position": {"ref": "bar", "bar": "P3", "relation": "below", "gap": 0},
 "arrangement": {"mode": "group", "pattern": "linear", "axis": "x", "by": "spacing", "spacing": 100,
                 "range": {"from": 100, "to": "=length-100"}}}
8. Urutan penyelesaian
1. Baca berkas, tolak schema_version yang lebih baru dari aplikasi, migrasikan yang lebih lama di memori.
2. Validasi skema (struktur, tipe, kunci tidak dikenal).
3. Periksa referensi: ID ganda, zona, tulangan, dan bentuk yang dirujuk, serta kecocokan hash salinan dengan sumber (hanya informasi).
4. Per pile: gabungkan parameter (definisi → default grup → penimpaan), selesaikan zona dan zona fleksibel.
5. Evaluasi ekspresi.
6. Selesaikan posisi (urutan ketergantungan) dan susunan, hasilnya daftar instance batang.
7. Bangun jalur sumbu dari bentuk, hitung panjang geometri, bandingkan dengan rumus standar.
8. Hasil turunan: rekap, potongan, pemeriksaan jumlah, spasi, dan bentrok.
9. Validasi dan kode kesalahan
Kode
Tingkat
Arti
SCHEMA
error
Struktur, tipe, atau kunci tidak dikenal
ID_DUP
error
ID ganda dalam cakupannya
REF_MISSING
error
Zona, tulangan, atau bentuk yang dirujuk tidak ada
ZONE_REST_POS
error
"rest" tidak di zona below_cof terakhir, atau lebih dari satu
ZONE_DEPTH_SHORT
error
Kedalaman lebih kecil dari jumlah zona tetap (pile disebut)
EXPR
error
Ekspresi tidak valid atau memakai variabel yang tidak ada
SHAPE_PARAM
error
Parameter bentuk wajib kosong atau tidak valid
POS_CYCLE
error
Posisi saling bergantung melingkar
POS_REF_AMBIGUOUS
error
Acuan batang tidak jelas untuk zona yang berbeda
ARR_BAD
error
Susunan tidak lengkap atau ambigu (count dan spacing bersamaan)
OUT_OF_ELEMENT
error
Batang berada di luar beton
LEN_MISMATCH
peringatan
Panjang geometri vs rumus melebihi toleransi
RULE_SPACING
peringatan
Jarak bersih kurang dari batas proyek
RULE_COVER
peringatan
Selimut kurang dari batas proyek
END_GAP
informasi
Sisa jarak di ujung susunan
HASH_DIFF
informasi
Definisi tertanam berbeda dari file sumber
10. Versi dan migrasi
• schema_version bilangan bulat. Penambahan kunci opsional tidak menaikkan versi. Perubahan yang merusak menaikkan versi dan menyertakan fungsi migrasi.
• Berkas yang dimigrasikan disimpan dengan cadangan .bak.
• type_version (plugin) dan version (bentuk) berjalan sendiri-sendiri.
11. Keputusan terbuka
1. Penimpaan per pile: v1 hanya params dan zone_lengths. Apakah perlu juga diameter atau tulangan berbeda untuk pile tertentu?
2. Rujukan pile cap ke grup pile: posisi pile cap mengikuti tata letak grup bored pile. Dicadangkan untuk v2 (refs).
3. Sistem koordinat project: apakah satu sistem lokal per project (x, y relatif terhadap pusat pier) sudah cukup, atau perlu rotasi per project?
4. Verifikasi rumus bagan: rumus dari gambar (mis. kode 39, 85, dan simbol di kode 87) perlu dicek ke standar sebelum menjadi data bawaan.
