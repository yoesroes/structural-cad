# Laporan Pekerjaan P1 — Alur State Server

Tanggal: 2026-10-31
Repo: `final_scad_h5/Structural cad`

## Ruang lingkup

P1 mengerjakan:

- **T1 — Alur state server dan edit pile berurutan**
- **S1 — Mutasi `add_rebar` yang dapat meracuni state sesi**

Tidak ada perubahan pada engine, schema, UI, atau format response JSON.

## Perubahan implementasi

### Helper `_commit`

Ditambahkan helper tunggal pada `src/scad_ui/server.py`:

```text
_commit(doc, target=None)
```

Urutannya:

1. Memilih target `CURRENT_PATH` jika ada.
2. Menggunakan `DATA_ROOT/project.json` sebagai fallback.
3. Menjalankan validasi.
4. Menyimpan dokumen.
5. Hanya setelah save berhasil memanggil `_set_current()`.

Dengan urutan ini, kegagalan validasi atau save tidak mengganti `CURRENT_DOC`, `CURRENT_PATH`, atau `DIRTY`.

### T1 — Edit pile

`_apply_pile_op_and_respond()` sekarang menggunakan `_commit(new_doc)`.

Regression test mencakup:

- dua edit depth pada pile berbeda;
- edit pada project yang dibuka dari path workspace;
- rangkaian tiga operasi: depth → zone → reset;
- pemeriksaan state melalui `GET /api/project`;
- pemeriksaan dokumen di disk.

### S1 — `add_rebar`

`add_rebar()` sekarang:

- memakai `copy.deepcopy()` dari dokumen sesi;
- menerapkan perubahan hanya pada salinan;
- memvalidasi salinan melalui `_commit()`;
- tidak mengubah state aktif jika validasi gagal;
- tetap dapat menyimpan dokumen berikutnya setelah operasi invalid ditolak.

## Regression test yang diaktifkan

Test berikut tidak lagi `xfail`:

```text
test_s1_invalid_rebar_does_not_poison_session
```

Test tersebut memverifikasi bahwa:

1. rebar invalid menghasilkan HTTP 400;
2. `CURRENT_DOC` tetap sama;
3. operasi save berikutnya tetap berhasil.

## Berkas yang berubah pada P1

- `src/scad_ui/server.py`
  - helper `_commit`;
  - copy-on-write pada `add_rebar`;
  - penggunaan `_commit` pada edit pile.
- `tests/ui/test_state_regression.py`
  - menghapus xfail S1;
  - menambahkan test tiga operasi berurutan untuk T1.
- `LAPORAN_P1.md`
  - laporan ini.

Berkas P0 lain tetap dipertahankan.

## Verifikasi

### Test terarah

```bash
pytest tests/ui/test_state_regression.py tests/ui/test_ops_api.py tests/ui/test_file_api.py -q
```

Hasil:

```text
23 passed, 1 xfailed
```

`xfail` tersebut adalah S2, yang memang belum dikerjakan pada P1.

### Syntax check

```bash
python3 -m py_compile src/scad_ui/server.py tests/ui/test_state_regression.py tests/ui/test_ops_api.py
```

Hasil: berhasil.

### Full Python suite

```bash
python -m pytest tests -rxX
```

Hasil:

```text
209 passed, 1 skipped, 6 xfailed, 5 subtests passed
```

Xfail yang masih terbuka:

```text
S2, S6, S7, T3 (2 test), T4
```

Test yang di-skip:

```text
tests/engine/test_generic.py:81 — CadQuery tidak tersedia
```

### Examples

```bash
python tools/check_examples.py
```

Hasil:

```text
SEMUA LOLOS
```

### TypeScript

```bash
node --experimental-strip-types --no-warnings --test web/src/commands/*.test.ts
```

Hasil:

```text
26 passed, 0 failed
```

## Kompatibilitas dan asumsi

- Dokumen project JSON lama tetap digunakan.
- Target save project yang sudah dibuka tetap `CURRENT_PATH`.
- Project tanpa path tetap memakai `DATA_ROOT/project.json`.
- Perilaku autosave edit pile dipertahankan sehingga `DIRTY=False` setelah commit berhasil.
- Tidak ada perubahan hasil perhitungan pile cap atau engine klasik.
- CadQuery tidak tersedia; test terkait tidak diklaim lulus.
