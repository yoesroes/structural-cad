# Konteks tambahan (batch 2) — BACA SETELAH 00_KONTEKS.md

Hasil audit repo `cad_generic` (23 Okt 2026). Semua tugas di bawah mengacu keadaan ini.

## Keadaan repo SEBELUM F4
```
cad_generic/
  core/scad/            expr.py issues.py zones.py validate.py resolve.py  io/(canonical.py files.py)  plugins/(base.py bored_pile.py pile_cap.py)
  core/tests/           test_expr test_io test_validate test_zones test_plugins test_resolve
  pilecap_rebar/        mesin geometri (model.py layout.py section2d.py clash.py recap.py draw.py cq_export.py step_audit.py cli.py)
                        + generic.py generic_cli.py (prototipe rotasi Euler, STEP umum)
                        + ui.py (server stdlib http.server) + static/ (index.html monolit, css/, js/) + elements/ (placeholder)
  tests/                test_ui.py test_generic.py test_pilecap_rebar.py
  web/src/              types.ts commands/(apply.ts console.ts registry.ts commands.test.ts)  [tes memakai node:test]
  schemas/ examples/ tools/ tasks/ docs/
```
## Keadaan target SETELAH F4 (tugas G memakai tata letak ini)
```
src/scad/          core v1 (dulu core/scad)           — TIDAK boleh mengimpor scad_engine atau scad_ui
src/scad_engine/   mesin geometri (dulu pilecap_rebar tanpa ui/static/elements)
src/scad_ui/       server + static (dulu pilecap_rebar/ui.py dan static/)
tests/             semua tes Python (core, engine, ui)     web/   frontend
```
Arah impor yang diizinkan: `scad_ui -> scad_engine -> scad`. Tidak sebaliknya.

## Fakta hasil audit (jangan diulang sebagai "temuan baru")
- Kontrak (schemas/scad.schema.json, examples/*, web/src/types.ts, tasks/00_KONTEKS.md) identik dengan paket spesifikasi: JANGAN diubah kecuali tugas menyatakan eksplisit; perubahan skema hanya boleh ADITIF dan opsional, disertai pembaruan contoh, tes, dan catatan CHANGELOG.
- Baseline tes (audit, dengan pelari pengganti): Python 133 lolos / 3 dilewati / 0 gagal; TypeScript 15/15. Angka lolos TIDAK boleh turun.
- Bug terbukti: `GET /static//etc/passwd` -> 200 (F1). `/run-2d` dan `/run-3d` melapor ok tanpa hasil (F2). `update_pile_depth` tidak menghapus override yang sama dengan default grup (F6).
- Inti v1 belum tersambung ke mesin geometri: `scad.resolve` hanya menyelesaikan zona (G1 menyambungkan).

## Aturan kerja
- Satu tugas = satu hasil kerja terpisah. Ubah HANYA berkas yang disebut di tugas (ditambah tes). Bila perlu mengubah hal lain, tulis di bagian Catatan laporan.
- Komentar dan pesan galat dalam bahasa Indonesia. Python >= 3.10.
- Jalankan tes sungguhan dan laporkan angka nyata. Jangan menyatakan lolos bila tidak dijalankan. Bila suatu alat tidak ada di lingkunganmu (cadquery, ezdxf, node), katakan apa yang tidak bisa diuji.
- Laporan akhir: (1) berkas diubah/dibuat/dihapus, (2) perintah uji dan hasilnya, (3) keputusan dan asumsi, (4) isu yang tersisa.
- Jangan menambah fitur di luar tugas, jangan menambah dependensi tanpa menyebutnya di laporan.
