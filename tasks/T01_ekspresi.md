# T01 — Evaluator ekspresi aman
Baca `00_KONTEKS.md` (butir 6) dulu.
**Tujuan:** `core/scad/expr.py` dengan `evaluate(value, variables=None, functions=None) -> float` dan `ExprError`.
**Aturan:** angka (int/float) dikembalikan apa adanya sebagai float. String HARUS berawalan `=`, selain itu `ExprError`. Parse dengan `ast`, izinkan hanya: angka, `+ - * / ** `, unary minus, kurung, nama variabel, panggilan fungsi berdaftar-putih (min max ceil floor round abs sqrt, `d_of`, `zone_length`) dengan argumen angka atau literal string, dan konstanta `pi`. Tolak atribut, subscript, lambda, komprehensi, f-string, dan nama berawalan `_`. `d_of`/`zone_length` datang dari argumen `functions`. Batasi panjang ekspresi 200 karakter dan kedalaman AST 20. Pembagian nol dan variabel tak dikenal menjadi `ExprError` dengan pesan Indonesia yang menyebut ekspresinya.
**Berkas keluaran:** `core/scad/expr.py`, `core/tests/test_expr.py`.
**Uji wajib:** `=40*d` dengan d=32 -> 1280; `=diameter-2*cover` (1200, 75) -> 1050; `=cover+d_of('B2')` (cover=75, d_of mengembalikan 16) -> 91; `=C/B*pi*(A-d)` dengan nilai angka; `=ceil(2077/300)+1` -> 8. Harus ditolak: `=__import__('os')`, `=a.b`, `=[1][0]`, `=1/0`, `=tak_ada`, `=(`, `40*d` (tanpa '='), `=lambda: 1`.
**Jangan:** memakai `eval`/`exec`.
