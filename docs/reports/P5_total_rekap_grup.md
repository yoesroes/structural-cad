# Laporan P5 — Total rekap grup (T4)

**Tanggal:** 2026-11-01  
**Repo:** Structural CAD (`develop-p3`)

## Ruang lingkup

Perbaiki agregasi `recap_group`: mark dengan beberapa panjang potong tidak lagi digabung
paksa ke panjang pile pertama.

## Berkas diubah

| Berkas | Isi |
|--------|-----|
| `src/scad_engine/from_v1.py` | `recap_group`: kunci `(mark, cut_length_mm)`; urutan stabil; total = count×cut |
| `tests/engine/test_engine_audit_regressions.py` | Hapus xfail T4; tes B4 multi-panjang + paritas berat/count |
| `tests/engine/test_from_v1.py` | `test_recap_group_nine_piles` menjumlah count B1 per baris |
| `docs/ENGINE.md` | Dokumentasi bentuk totals |
| `docs/reports/P5_total_rekap_grup.md` | Laporan ini |

## Perilaku

- Kunci agregasi: `(mark, cut_length_mm` dibulatkan 3 desimal`)`.
- Tiap baris: `mark`, `id` (= mark), count, panjang, total, berat.
- `total_length_mm = count * cut_length_mm` (dihitung ulang agar invarian tepat).
- `weight_kg` = jumlah berat dari pile (paritas berat total).
- Urutan: kemunculan mark, lalu panjang menurun.

## Mutation check

| Mutasi | Tes yang gagal |
|--------|----------------|
| `key = (mark, 0.0)` (abaikan panjang) | `test_group_totals_b4_split_by_cut_length_and_weight_parity` (16280 tidak ada) |
| `total_mm = row["total_length_mm"]` (jumlah mentah) | `test_group_totals_each_row_obey_count_times_cut_length` (selisih 0.027 > 1e-3) |

Dipulihkan setelahnya.

## Verifikasi nyata

```text
pytest tests: 246 passed, 1 skipped, 2 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 28 passed, 0 failed
```

Xfail tersisa pada basis ini: **S2×2** (P7 belum digabung di branch ini). **T4** sudah hijau.

Catatan: bila P7 sudah digabung di working tree Anda, xfail tersisa hanya kosong / T4 sudah tidak ada; angka lulus akan lebih tinggi (~254 bila P7 + P5).

## Asumsi / isu terbuka

- Berat dihitung ulang dari diameter×panjang pada level pile; di totals dipakai jumlah berat pile agar paritas total terjaga, sementara panjang total dihitung ulang dari count×cut.
