# Rencana Perbaikan Structural CAD: Sequence dan Prompt untuk AI Pelaksana

Berdasarkan audit 30 Okt 2026. Setiap tugas (P0 sampai P10) berdiri sendiri: tempel **Preamble umum** lalu **prompt tugas** ke AI pelaksana, satu tugas per sesi. Kerjakan sesuai urutan di tabel; tugas yang dependensinya sama boleh paralel.

## 1. Urutan dan dependensi

| ID | Tugas | Menutup temuan | Bergantung pada | Paralel dengan |
| --- | --- | --- | --- | --- |
| P0 | Baseline, isolasi tes, tes merah (xfail strict) | semua (pengaman) | tidak ada | tidak ada |
| P1 | Alur state server | T1, S1 | P0 | tidak ada |
| P2 | Feasibilitas zona dan issue resolve | T2, S6, zona tak penuh | P1 | P7 |
| P3 | Validator: arrangement, ekspresi, tipe grup | T3, S7, S3 (tipe) | P1 | P7 |
| P4 | Ketepatan engine | S4, S5, 4 temuan rendah | P3 | P5, P6 |
| P5 | Total rekap grup | T4 | P3 | P4, P6 |
| P6 | File ops dan update-from-source | S3, 4 temuan rendah | P2, P3 | P4, P5 |
| P7 | Keamanan HTTP dan XSS | S2, S9 | P1 | P2, P3 |
| P8 | UI jujur, performa, paket contoh | S10, S11, S12 | P2, P5, P7 | P9 |
| P9 | Dokumen dan CI | dokumen usang, CI | semua di atas | P8 |
| P10 | Bentuk tulangan (gerbang keputusan) | S8 | D5 diputuskan | P9 |

## 2. Keputusan pemilik produk (jawab sebelum mulai)

Prompt di bawah memakai nilai **rekomendasi**. Bila Anda memilih lain, ubah kalimat yang bersangkutan.

- **D1**: edit yang membuat zona tak feasibel. Rekomendasi: **ditolak** (HTTP 400, tidak disimpan).
- **D2**: polar dengan `by: spacing`. Rekomendasi: **ditolak** dengan error `ARR_BAD`; implementasi jarak busur ditunda.
- **D3**: default `cover_ref` pile cap bila tidak diisi. Rekomendasi: **surface** (sama dengan plugin dan project). PC\_8400 tidak terpengaruh karena eksplisit `centerline`.
- **D4**: radius tekuk U-bar pile cap. Rekomendasi: parameter opsional `bend_inside_radius_db` dengan default 2 (setara 38 mm untuk D19, jadi PC\_8400 identik).
- **D5**: bentuk `37` dan `X-HOOK-135-90`. Rekomendasi jangka pendek: **tolak dengan jelas** (opsi A). Opsi B (implementasi penuh) dikerjakan terpisah.

## 3. Preamble umum (tempel di awal SETIAP prompt)

```
Anda mengerjakan SATU tugas perbaikan di repo Structural CAD (Python >= 3.10;
paket src/scad, src/scad_engine, src/scad_ui; frontend TS di web/).
Baca dulu: tasks/00_KONTEKS.md dan docs/ARCHITECTURE_LAYERS.md.

Aturan:
- Komentar, docstring, dan pesan galat dalam bahasa Indonesia.
- Hanya ubah berkas yang tercantum di 'Berkas boleh diubah'. Jangan menambah fitur lain.
- Arah impor: scad <- scad_engine <- scad_ui (tes tests/test_import_direction.py menjaga ini).
- Jangan ubah schemas/scad.schema.json kecuali tugas menyebutnya; bila diubah, jalankan
  scripts/sync_schema.sh dan python tools/build_examples.py bila perlu, lalu pastikan hash
  contoh di tools/.hash tidak berubah kecuali tugas menyatakan lain.
- Metode: tulis/aktifkan tes DULU dan pastikan gagal sebelum perbaikan, baru perbaiki.
- Setup: pip install -e '.[dev]'
- Perintah verifikasi (jalankan semua, laporkan hasil NYATA):
    python -m pytest tests
    python tools/check_examples.py
    node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts
- Regresi wajib: PC_8400.elem.json tetap 533 batang dengan panjang per mark identik
  dengan mesin lama; rekap P1.project.json tidak berubah kecuali tugas menyebutnya.
- Jangan menyatakan lulus bila tidak dijalankan.

Laporan akhir: (1) berkas diubah, (2) perintah uji + hasil nyata (jumlah lolos/gagal),
(3) asumsi, (4) isu terbuka.
```

## 4. Prompt per tugas

### P0: Baseline, isolasi tes, tes merah

```
TUGAS P0 - Baseline dan tes merah.

Latar: audit menemukan bug yang tidak tertangkap tes karena (a) tiap tes API hanya menjalankan
satu operasi dan (b) tests/ui/test_ops_api.py tidak mereset state global server
(CURRENT_DOC, dst).

Berkas boleh diubah/dibuat: tests/conftest.py (baru), tests/ui/test_ops_api.py,
tests/ui/test_state_regression.py (baru), tests/engine/test_audit_regressions.py (baru),
tests/core/test_audit_regressions.py (baru).

Langkah:
1. Jalankan seluruh suite, catat jumlah lolos/gagal/skip sebagai baseline.
2. Buat fixture `ui_server` di tests/conftest.py: menyimpan lalu memulihkan SEMUA global di
   scad_ui.server (DATA_ROOT, ROOT, WORKSPACE, CURRENT_PATH, CURRENT_DOC, DIRTY,
   CURRENT_ELEMENT, CURRENT_ELEMENT_PATH), memakai tmp_path untuk data dan workspace, menyalin
   examples/P1.project.json ke data/project.json, menjalankan ThreadingHTTPServer port 0.
   Migrasikan test_ops_api.py ke fixture ini.
3. Tulis tes berikut dan tandai @pytest.mark.xfail(strict=True, reason='<ID temuan>'):
   a. T1: dua POST /api/pile/<id>/depth pada pile berbeda; keduanya harus ada di disk DAN di
      GET /api/project.
   b. T1: POST /api/project/open path X di workspace lalu POST depth; berkas X harus berubah,
      DATA_ROOT/project.json tidak dibuat.
   c. T2: depth 5000 pada P1-6 (zona tetap 11000) harus 400 dan disk tidak berubah.
   d. S1: POST /api/element/BP-P1/rebar dengan item tidak valid harus 400 DAN dokumen di
      memori tidak berubah, lalu POST /api/project/save harus 200.
   e. T3: B1 diubah ke polar + by:spacing harus menghasilkan issue error ARR_BAD saat validasi.
   f. T3: arrangement polar dengan start_angle_deg=45 harus menggeser origin batang pertama.
   g. T4: untuk recap_group P1, setiap baris totals harus memenuhi count*cut_length_mm ==
      total_length_mm (toleransi 1e-3 mm).
   h. S6: set_pile_zone_length pada zona 'rest' (Z3) harus ValueError.
   i. S2: POST dengan Host asing, atau Origin asing, atau Content-Type text/plain harus ditolak
      (400/403/415) dan tidak menulis berkas.
   j. S7: evaluate('=(0-8)**(1/3)') dan evaluate('=0**-1') harus raise ExprError.
4. Suite harus hijau (xfail strict dihitung sebagai 'xfailed'). Laporkan 10 xfail.

Jangan memperbaiki kode produksi di tugas ini.
```

### P1: Alur state server (T1, S1)

```
TUGAS P1 - Perbaiki alur state server.

Latar (terbukti): _apply_pile_op_and_respond (server.py ~596-628) menyimpan new_doc ke
DATA_ROOT/project.json tetapi tidak memanggil _set_current, dan mengabaikan CURRENT_PATH.
Akibatnya edit berikutnya dibangun dari dokumen basi (edit hilang), recap/GET membaca dokumen
basi, dan berkas yang dibuka tidak berubah. add_rebar memutasi dokumen sesi SEBELUM validasi,
sehingga sesi rusak bila validasi gagal.

Berkas boleh diubah: src/scad_ui/server.py, tests/ui/*, tests/conftest.py (hanya bila perlu).

Langkah:
1. Buat helper tunggal `_commit(new_doc, target=None)`: target default = CURRENT_PATH bila ada,
   selain itu DATA_ROOT/project.json. Urutan: validasi -> simpan (save_document) -> HANYA bila
   sukses panggil _set_current(new_doc, path=target, dirty=False). Gagal = state tidak berubah.
2. Pakai _commit di _apply_pile_op_and_respond. Operasi memakai dokumen sesi terbaru.
3. add_rebar: kerjakan pada copy.deepcopy dokumen sesi; commit hanya bila valid.
4. Pastikan api_pile_recap, api_group_recap, run_2d, run_3d, get_project membaca CURRENT_DOC
   terbaru (tanpa cache basi).
5. Hapus xfail untuk tes P0 a, b, d dan pastikan lolos. Tambah tes: 3 operasi berurutan
   (depth, zone, reset) lalu cek disk dan GET.

Jangan ubah format respons JSON yang ada.
```

### P2: Feasibilitas zona dan issue resolve (T2, S6, zona tak penuh)

```
TUGAS P2 - Zona: feasibilitas, override 'rest', cakupan.

Latar (terbukti): (1) SET depth 5000 dengan zona tetap 11000 -> HTTP 200 ok:true, zones:[]
dan tersimpan, karena ZoneError dari resolve_project tidak diteruskan; (2) override zona 'rest'
diterima ops dan ditampilkan sebagai overridden tetapi diabaikan resolve_zones;
(3) zona below_cof tanpa 'rest' yang tidak menutup seluruh kedalaman tidak diberi peringatan.
Keputusan D1: edit tak feasibel DITOLAK (400) dan tidak disimpan.

Berkas boleh diubah: src/scad/ops.py, src/scad/zones.py, src/scad/resolve.py,
src/scad/validate.py, src/scad_ui/server.py, tests/core/*, tests/ui/*, docs/UI.md.

Langkah:
1. resolve_project: sertakan `issues` per pile di dict pile (selain list global).
2. server._apply_pile_op_and_respond: setelah apply_operation, jalankan resolve_zones untuk pile
   target; bila ZoneError -> 400 {ok:false, error, code} dan JANGAN simpan.
3. ops.set_pile_zone_length/reset_pile_zone_length: tolak zona dengan length 'rest' (ValueError,
   pesan Indonesia). zones.resolve_zones: override pada zona rest -> ZoneError code
   ZONE_REST_OVERRIDE. validate: instance.overrides.zone_lengths yang menunjuk zona rest -> error
   dengan kode yang sama.
4. resolve_project: bila tidak ada zona 'rest' dan jumlah panjang below_cof < depth, tambahkan
   Issue level 'warning' kode ZONE_GAP (selisih dalam mm). Bukan error.
5. Perbarui docs/UI.md dan daftar kode galat di tasks/00_KONTEKS.md hanya pada bagian
   'Kode galat' (tambahkan ZONE_REST_OVERRIDE, ZONE_GAP). Hapus xfail P0 c dan h.
6. Regresi: examples/expected_zones.P1.json dan examples/ops_golden.json tetap lolos; bila
   golden perlu kasus baru, tambahkan tanpa mengubah kasus lama dan samakan web/ (apply.ts).
```

### P3: Validator: arrangement, ekspresi, tipe grup (T3, S7)

```
TUGAS P3 - Perketat validator dan evaluator.

Latar (terbukti):
- Arrangement polar dengan by:spacing lolos skema tetapi placement membaca hanya `count` ->
  0 batang, B1 hilang dari rekap tanpa peringatan.
- Skema memakai `start_angle_deg`, kode membaca `start_angle` (placement.py ~323).
- validate_document tidak memeriksa ekspresi: '=variabel_tak_ada*2' lolos.
- evaluate('=(0-8)**(1/3)') -> TypeError, evaluate('=0**-1') -> ZeroDivisionError (bukan ExprError).
- group.type='bored_pile' dengan definition.data.type='pile_cap' lolos validasi.
Keputusan D2: polar+by:spacing DITOLAK (ARR_BAD). Linear hanya axis z yang didukung engine.

Berkas boleh diubah: src/scad/expr.py, src/scad/validate.py, src/scad/placement.py,
schemas/scad.schema.json + src/scad/data/scad.schema.json (via sync_schema.sh),
tools/build_examples.py (hanya bila skema berubah), tests/core/*, tests/engine/*.

Langkah:
1. expr.py: bungkus operasi biner/unary; TypeError, ZeroDivisionError, ValueError, hasil
   complex -> ExprError. Tambah fungsi publik `check_expression(text, allowed_names,
   allowed_funcs) -> list[str]` yang hanya memeriksa sintaks dan node AST dan nama yang dikenal
   (tidak mengevaluasi nilai).
2. validate.py: tambah kode EXPR (error) untuk setiap string berawalan '=' yang gagal
   check_expression; nama yang diizinkan = kunci params elemen, d, pi, diameter, cover,
   nama param bentuk (A, B, C, lap, ...), dan fungsi min max ceil floor round abs sqrt d_of
   zone_length shape_param. Tambah ARR_BAD (error): polar wajib by=count dan count>=1; linear
   wajib axis 'z'. Tambah TYPE_MISMATCH (error): group.type != definition.data.type.
3. placement.py: ganti kunci menjadi `start_angle_deg`; count<=0 pada polar -> ValueError (bukan
   hasil kosong).
4. Skema: bila perlu, tambahkan batasan if/then untuk polar; sync skema.
5. Hapus xfail P0 e, f, j. Tambah tes negatif untuk tiap kode baru dan tes bahwa SEMUA
   examples/*.json tetap valid tanpa EXPR palsu.
```

### P4: Ketepatan engine (S4, S5, temuan rendah)

```
TUGAS P4 - Perbaiki ketepatan engine.

Latar (terbukti) dan keputusan:
1. placement._place_helix_by_zone mengabaikan extend_start/extend_end: extend_start=500 hanya
   menggeser seluruh spiral naik 500 mm; extend_end tidak berpengaruh. Semantik yang benar:
   extend_start positif memanjangkan ke atas, extend_end positif memanjangkan ke bawah (sama
   dengan extent_z_range).
2. from_v1._pilecap_groups_v1: cover_ref default 'centerline' (baris ~254) berbeda dari default
   plugin/project 'surface' (D3: ubah default ke 'surface'; fallback ke settings.cover_ref
   bila ada).
3. Rantai `or` memperlakukan 0 sebagai tidak ada (lap_ratio_D, lap_mid_height; baris ~257-259).
4. Paritas kait P5 memakai round(x/spacing) (baris ~396); gagal bila inset bukan kelipatan
   spasi (mis. inset 300, spasi 600 -> semua kait searah).
5. Radius tekuk U-bar tetap 38+d/2 (baris ~331) (D4: parameter opsional bend_inside_radius_db,
   default 2; axis radius = (bend_inside_radius_db + 0.5) * d; D19 tetap 38+9.5).
6. _min_clear_spacing melewati semua pasangan dengan jarak < 1.5d (baris ~523), sehingga
   pelanggaran spasi nyata terlewat. Ganti dengan deteksi bundel eksplisit: lewati hanya pasangan
   yang jaraknya = d dalam toleransi 0.5 mm.

Berkas boleh diubah: src/scad/placement.py, src/scad_engine/from_v1.py, src/scad/plugins/
pile_cap.py (param opsional), skema + sync (param opsional PileCapParams), tests/engine/*.

Kriteria: PC_8400 tetap 533 batang dan panjang per mark identik; RULE_SPACING pada P1
masih muncul dengan nilai 46.6 mm; tes baru: spiral extend_start/extend_end (atas/bawah/cut
length sesuai), cover_ref default, lap_mid_height=0 dipakai apa adanya (bila batang keluar
beton, error yang sudah ada muncul), paritas P5 bergantian untuk inset 300 dan 600.
```

### P5: Total rekap grup (T4)

```
TUGAS P5 - Perbaiki recap_group.

Latar (terbukti): recap_group (from_v1.py ~705-747) mengunci `length_mm`,
`cut_length_mm`, `geometry_length_mm` dari pile pertama, padahal count dan total dijumlah dari
semua pile. Pada P1: B4 count 252 x 20280 != total 4872560 (P1-2, P1-5, P1-8 lebih pendek).
Pile cap: mark P6 punya beberapa panjang tetapi digabung per mark.

Berkas boleh diubah: src/scad_engine/from_v1.py, tests/engine/*, tests/ui/test_pile_cap_recap_api.py,
docs/ENGINE.md, web/src/types.ts (hanya bila tipe rekap ada di sana).

Langkah:
1. Kunci agregasi totals = (mark, cut_length_mm dibulatkan 3 desimal). Hasil: satu baris per
   panjang potong berbeda; tiap baris punya `mark`, `id` (tetap = mark), count, panjang, total,
   berat. Urutkan stabil (urutan mark kemunculan, lalu panjang menurun).
2. Tambahkan invarian di tes: untuk setiap baris, count*cut_length_mm == total_length_mm
   (toleransi 1e-3); jumlah weight_kg totals == jumlah weight_kg semua pile; jumlah count per
   mark == jumlah count per pile.
3. Tambah tes P1: B4 muncul sebagai beberapa baris (20280, 16280, ...), jumlah berat total
   sama dengan sebelum perubahan (76878.6 kg, toleransi 0.1).
4. Hapus xfail P0 g. Dokumentasikan perubahan bentuk totals di docs/ENGINE.md.
```

### P6: File ops dan update-from-source (S3, temuan rendah)

```
TUGAS P6 - Perbaiki update-from-source dan operasi berkas.

Latar (terbukti):
- update_group_from_source tidak menyentuh group.defaults.params.depth_below_cof; default lama
  menimpa definisi baru (24000 diabaikan, tetap 30000).
- Sumber bertipe beda diterima (group.type tetap bored_pile, definition.type menjadi pile_cap).
- api_update_from_source tidak memvalidasi hasil sebelum _set_current.
- list_workspace_files gagal total (ValueError + bocor path absolut) bila ada satu symlink
  yang menunjuk keluar workspace.
- add_element_to_project: count tanpa batas atas; cols/dx/dy tidak divalidasi.
- api_source_diff/api_update_from_source memakai WORKSPACE.rglob(source.file) dan memilih hasil
  pertama tanpa peringatan bila ada beberapa berkas bernama sama.

Berkas boleh diubah: src/scad/files_ops.py, src/scad_ui/server.py, tests/core/test_files_ops.py,
tests/ui/test_file_api.py.

Langkah:
1. update_group_from_source: bila defaults.depth_below_cof == nilai definisi LAMA (tidak
   pernah diubah pengguna) -> set ke nilai definisi baru; bila berbeda (diubah pengguna) ->
   pertahankan dan sertakan Issue level 'info' DEFAULT_KEPT. Tolak (Issue error TYPE_MISMATCH)
   bila element.definition.type != group.type.
2. Server: validasi new_proj (seperti api_add_element) sebelum _set_current; error -> 400.
3. list_workspace_files: lewati (jangan raise) berkas yang resolve() keluar workspace; jangan
   menyertakan path absolut di pesan galat.
4. add_element_to_project: 1 <= count <= 1000; cols >= 1; dx, dy finite (math.isfinite).
5. Pencarian sumber: urutkan hasil; bila lebih dari satu kecocokan -> 400 dengan daftar path
   relatif dan minta `path` eksplisit.
6. Tes untuk setiap poin, termasuk symlink keluar workspace.
```

### P7: Keamanan HTTP dan XSS (S2, S9)

```
TUGAS P7 - Keamanan server lokal dan UI.

Latar (terbukti/dibaca): server menerima POST text/plain dari Origin asing dan Host sembarang
(save-as menulis berkas dari situs lain); tidak ada header keamanan. app.js menyisipkan
project.name, materials.*.grade, shape.code, dst ke innerHTML tanpa escape.

Berkas boleh diubah: src/scad_ui/server.py, src/scad_ui/static/app.js,
src/scad_ui/static/index.html, tests/ui/test_security_http.py (baru), docs/UI.md.

Langkah:
1. Di Handler, sebelum dispatch GET/POST: tolak (400) bila header Host bukan salah satu dari
   127.0.0.1:<port>, localhost:<port>, [::1]:<port>. Untuk POST: wajib
   Content-Type 'application/json' (selain itu 415); bila ada header Origin, wajib sama dengan
   http://<Host> (selain itu 403). Tidak menambah header CORS.
2. Tambahkan pada semua respons: X-Content-Type-Options: nosniff,
   Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; object-src
   'none'; base-uri 'none'; frame-ancestors 'none' (unsafe-inline diperlukan sementara karena
   handler onclick; catat sebagai utang teknis di docs/UI.md).
3. app.js: tambah escapeHtml() dan pakai pada SEMUA interpolasi data dokumen di template
   innerHTML (renderSidebar, renderTable, renderProps), atau pakai textContent bila memungkinkan.
4. Tes: Host asing, Origin asing, text/plain -> ditolak dan tidak menulis berkas; permintaan
   normal (fetch dari halaman sendiri) tetap lolos; tes Node untuk escapeHtml; tes statis
   yang gagal bila ada `${` di template innerHTML tanpa melalui escapeHtml.
5. Hapus xfail P0 i.
```

### P8: UI jujur, performa, paket contoh (S10, S11, S12)

```
TUGAS P8 - UI jujur, performa server, sinkron contoh.

Latar: kolom 'Sesuai' dikodekan keras; kanvas SVG statis berlabel B3 usang; menu Baru/Buka/
Simpan Sebagai dan 'Tambah tulangan' belum berfungsi tetapi tampil aktif; rekap grup 9 pile
memakan 5.2 s sambil memegang STATE_LOCK global (server tidak merespons selama itu);
src/scad_engine/examples/P1.project.json sudah basi (masih B1,B2,B3,B4, hash berbeda).

Berkas boleh diubah: src/scad_ui/static/app.js, index.html, app.css, src/scad_ui/server.py,
src/scad_engine/examples/*, scripts/sync_examples.sh (baru), tests/test_examples_sync.py (baru).

Langkah:
1. Kolom status tabel pile dari pile.issues (hasil P2): 'Sesuai' hanya bila tidak ada issue
   error; selain itu tampilkan kode issue. Hapus hard-code 'Sesuai' di HTML.
2. Kanvas: beri label 'Ilustrasi skematik, bukan data model' ATAU render zona dari data resolve.
   Hapus label B3. Beri atribut disabled dan title='Belum tersedia' pada menu/tombol yang belum
   berfungsi.
3. Server: jalankan perhitungan berat (recap, run_2d, run_3d) di luar STATE_LOCK memakai
   snapshot copy.deepcopy(CURRENT_DOC) yang diambil di dalam lock. Tambahkan cache LRU
   (maks 32) untuk hasil recap_pile berkunci (scad.io.canonical.sha256_of(dokumen), pile_id).
4. scripts/sync_examples.sh menyalin examples/P1.project.json dan examples/pilecap.json ke
   src/scad_engine/examples/; tambah tes byte-identik (pola tests/test_schema_sync.py) dan
   panggil dari scripts/ci.sh.
5. Tes: respons recap kedua untuk dokumen sama lebih cepat (cache hit, cek lewat counter),
   request lain tidak terblokir selama recap (dua thread).
```

### P9: Dokumen dan CI

```
TUGAS P9 - Sinkronkan dokumen dan CI dengan kenyataan kode.

Temuan dokumen usang:
- README: '2D/3D dari project v1: belum (501)' padahal /run-2d dan /run-3d berfungsi; angka
  'pytest 200 passed, 1 skipped' tidak dapat direproduksi.
- docs/UI.md: host non-loopback 'hanya peringatan'; kode menolak (server.py main()).
- server.py docstring: app.js disebut legacy; padahal dimuat index.html.
- docs/ARCHITECTURE_AUDIT.md (23 Okt) sudah usang.
- MANIFEST.in merujuk CHANGELOG_GENERIC.md/CHANGELOG_UI.md yang sudah dipindah ke docs/archive.
- Pesan di validate.py dan tools/check_examples.py masih menyebut core/scad.
- tools/check_examples.py memakai sys.path (bertentangan dengan klaim F4).
- web/package.json punya skrip vitest tanpa dependensinya.
- pytest filterwarnings menyembunyikan semua DeprecationWarning.

Berkas boleh diubah: README.md, docs/*.md, MANIFEST.in, pyproject.toml, scripts/ci.sh,
web/package.json, src/scad/validate.py (hanya pesan/komentar), tools/check_examples.py,
CHANGELOG.md.

Langkah:
1. README: perbarui tabel status fitur berdasarkan kode; ganti angka tes dengan instruksi
   'jalankan scripts/ci.sh'. Tambahkan entri CHANGELOG untuk P0-P8.
2. Perbaiki setiap butir di atas. ARCHITECTURE_AUDIT.md: pindahkan ke docs/archive/ dengan
   catatan tanggal.
3. scripts/ci.sh: tambahkan langkah tes Node dan pengecekan sync contoh/skema; keluar non-nol
   bila ada yang gagal.
4. pyproject: ubah filterwarnings menjadi hanya mengabaikan DeprecationWarning dari modul
   pilecap_rebar.
5. Verifikasi: bash scripts/ci.sh harus lulus; laporkan keluarannya.
```

### P10: Bentuk tulangan (S8), gerbang keputusan D5

```
TUGAS P10 (opsi A, rekomendasi) - Tolak bentuk yang belum didukung dengan jelas.

Latar (terbukti): skema dan examples/shapes.builtin.json memuat bentuk '37'
(builder polyline_outside, cut_length memakai variabel 'r') dan 'X-HOOK-135-90'
(derived_from + add_hooks), tetapi scad.shapes.build_centerline hanya mendukung straight,
helix, ring. Memakainya di bored pile gagal dengan 'Jenis builder tidak didukung'.

Berkas boleh diubah: src/scad/validate.py, src/scad/shapes.py, docs/ENGINE.md, README.md,
tests/core/*, tests/engine/*.

Langkah:
1. Konstanta SUPPORTED_BUILDERS = {'straight','helix','ring'} di scad.shapes.
2. validate_document: untuk elemen/project bertipe bored_pile, bila rebar memakai bentuk yang
   builder-nya tidak didukung (atau turunan/hook), keluarkan Issue level 'error' kode
   SHAPE_UNSUPPORTED dengan path ke rebar. Pile cap tidak terpengaruh.
3. build_centerline: pesan galat menyebut kode bentuk dan builder yang didukung.
4. Dokumentasikan di README/docs/ENGINE.md daftar bentuk yang benar-benar didukung.
5. Tes: bentuk 37 dan X-HOOK pada bored pile -> SHAPE_UNSUPPORTED; R20/R87/RING tidak terpengaruh.

(Opsi B: implementasi penuh polyline_outside, hook, dan variabel r. Minta tugas terpisah
setelah opsi A selesai dan setelah pemilik menetapkan rumus panjang potong yang dipakai.)
```

## 5. Catatan pelaksanaan

- Kerjakan satu tugas per cabang/commit agar regresi mudah ditelusuri; gabungkan hanya bila `scripts/ci.sh` hijau.
- Setelah P1, P2, dan P3 selesai, jalankan ulang audit singkat pada tiga skenario kritis: dua edit berurutan, depth tak feasibel, polar `by: spacing`.
- Jika AI pelaksana menemukan kontradiksi dengan `tasks/00_KONTEKS.md`, ia harus menuliskannya di bagian isu terbuka, bukan mengubah kontrak diam-diam.
