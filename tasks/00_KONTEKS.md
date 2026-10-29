# Konteks bersama — Structural CAD (BACA DULU)

## Tujuan
Aplikasi lokal untuk mendefinisikan struktur jembatan (bored pile, pile cap; nanti pier, pier head, girder, slab) beserta tulangannya.
JSON adalah satu-satunya sumber data. Gambar 2D, model 3D, rekap, dan pemeriksaan adalah hasil turunan dan TIDAK disimpan di JSON.

## Keputusan final (jangan diubah)
1. Lokal: backend Python 3.10+, UI web (React + Vite + TypeScript) di 127.0.0.1. Tanpa HP, akun, cloud.
2. Dua jenis berkas: **project** (satu lokasi: P1, A1, ...) dan **file elemen** (definisi yang bisa dipakai ulang). Elemen masuk ke project sebagai **salinan tertanam** (project mandiri; pembaruan manual; hash sumber disimpan).
3. Satu grup (mis. 9 bored pile P1-1..P1-9) memakai satu definisi. Antar pile HANYA boleh berbeda `depth_below_cof` dan `zone_lengths`. Diameter atau tulangan berbeda = grup baru.
4. Satuan mm dan derajat. ID: `^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$`.
5. Zona dihitung dari COF. Zona `above_cof` bertumpuk ke atas, `below_cof` ke bawah. Satu zona `"rest"` (harus zona below_cof TERAKHIR) menyerap sisa kedalaman. Koordinat z relatif COF, positif ke atas.
6. Ekspresi = string berawalan `=`. Variabel: parameter elemen, `d` (diameter batang), `r`, `pi`. Fungsi: min max ceil floor round abs sqrt, `d_of('B2')`, `zone_length('Z1')` (menggantikan notasi `zone('Z1').length` di dokumen spesifikasi). Tanpa akses atribut/loop/pemanggilan lain.
7. Kunci tak dikenal ditolak, kecuali berawalan `x_` atau di bawah `meta`.

## Berkas acuan (jangan diubah)
- `schemas/scad.schema.json` — JSON Schema 2020-12 (entri: `kind` = element | project | shape_library)
- `examples/BP_D1200.elem.json`, `examples/P1.project.json`, `examples/shapes.builtin.json`
- `examples/expected_zones.P1.json` — data uji emas untuk zona
- `docs/mockup/*.html` — mockup layar (HTML statis; pembungkus `<x-dc>` boleh diabaikan)
- `web/src/types.ts` — tipe TypeScript bersama
- `tools/check_examples.py` dan `tools/mini_validate.py` — pemeriksa minimal (bukan pengganti paket `jsonschema`)

## Kode galat
`SCHEMA`(error) `ID_DUP`(error) `REF_MISSING`(error) `ZONE_REST_POS`(error) `ZONE_DEPTH_SHORT`(error) `EXPR`(error) `SHAPE_PARAM`(error) `POS_CYCLE`(error) `POS_REF_AMBIGUOUS`(error) `ARR_BAD`(error) `OUT_OF_ELEMENT`(error) `LEN_MISMATCH`(warning) `RULE_SPACING`(warning) `RULE_COVER`(warning) `END_GAP`(info) `HASH_DIFF`(info).
Pesan galat dalam bahasa Indonesia, menyebut path JSON Pointer (mis. `/groups/0/instances/1/overrides`).

## Kontrak antarmuka Python (paket `scad`, di `core/scad/`)
```python
# issues.py
@dataclass(frozen=True)
class Issue: level: str; code: str; path: str; message: str
# expr.py
class ExprError(ValueError): ...
def evaluate(value, variables=None, functions=None) -> float
# io/canonical.py
def canonical_json(obj) -> str
def sha256_of(obj) -> str            # "sha256:<64 hex>"
# io/files.py
SCHEMA_VERSION = 1
class SchemaVersionError(ValueError): ...
def load_document(path) -> dict
def save_document(path, doc) -> None
# validate.py
def validate_document(doc: dict) -> list[Issue]
# zones.py
class ZoneError(ValueError): code: str
@dataclass(frozen=True)
class ResolvedZone: id: str; side: str; length: float; z_top: float; z_bottom: float
def resolve_zones(zones: list[dict], depth_below_cof: float, zone_lengths: dict | None = None) -> list[ResolvedZone]
# plugins/base.py
class ElementPlugin(ABC): type_id: str; type_version: int
    def params_schema(self) -> dict; def faces(self) -> list[str]
    def overridable_params(self) -> list[str]; def local_frame_doc(self) -> str
def register_plugin(cls); def get_plugin(type_id); def list_plugins() -> list[str]
```

## Kontrak API (server lokal, 127.0.0.1)
```
POST /api/validate         {doc}  -> {issues: Issue[]}
POST /api/project/resolve  {doc}  -> ResolveResponse   (lihat web/src/types.ts)
POST /api/file/open        {path} -> {doc}
POST /api/file/save        {path, doc} -> {ok: true}
```

## Struktur repositori dan kepemilikan
```
structural_cad/
  core/scad/ (expr.py issues.py zones.py validate.py io/ plugins/)   core/tests/
  server/    (main.py openapi.yaml tests/)
  web/src/   (types.ts + komponen)   schemas/  examples/  docs/  tools/
```
Setiap tugas HANYA boleh membuat/mengubah berkas yang tercantum di "Berkas keluaran". Jika kontrak perlu berubah, tulis usulan di bagian Catatan laporan, jangan ubah diam-diam.

## Aturan kerja untuk setiap AI
- Komentar, docstring, dan pesan galat dalam bahasa Indonesia.
- Python >= 3.10. Inti hanya stdlib. Diizinkan: `jsonschema`, `fastapi`, `uvicorn`, `pytest`. Frontend: react, react-dom, vite, typescript, vitest, @testing-library/react. Tanpa library komponen UI.
- Tulis uji, JALANKAN, lalu laporkan hasil nyata (jumlah lolos/gagal). Jangan menyatakan lolos bila tidak dijalankan.
- Jangan menambah fitur di luar tugas.
- Laporan akhir: (1) berkas dibuat, (2) perintah uji + hasil, (3) asumsi, (4) isu/pertanyaan.
