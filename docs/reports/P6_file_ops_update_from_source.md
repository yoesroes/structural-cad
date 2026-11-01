# Laporan P6 — File ops dan update-from-source

**Tanggal:** 2026-11-01  
**Repo:** Structural CAD (`develop-p3`)

## Ruang lingkup

- Default depth saat update-from-source
- TYPE_MISMATCH sumber ≠ group.type
- Validasi hasil sebelum commit sesi
- list_workspace_files aman terhadap symlink keluar
- Batas count/cols/dx/dy
- Ambigu pencarian sumber (multi-match)
- Celah D6: override zona yang menjadi rest setelah update

## Berkas diubah

| Berkas | Isi |
|--------|-----|
| `src/scad/files_ops.py` | list skip symlink; find_source_matches; add_element bounds; update depth/TYPE/D6 |
| `src/scad_ui/server.py` | source-diff & update-from-source: multi-match 400; validasi sebelum `_set_current` |
| `tests/core/test_files_ops.py` | Tes symlink, count/layout, TYPE_MISMATCH, DEFAULT_KEPT, ZONE_REST |
| `tests/ui/test_file_api.py` | E2E D6 update-from-source; multi-match source-diff |
| `docs/reports/P6_file_ops_update_from_source.md` | Laporan ini |

## Perilaku kunci

1. **defaults.depth_below_cof:** ikut definisi baru bila default == nilai definisi lama; jika pengguna mengubah, pertahankan + Issue `info` `DEFAULT_KEPT`.
2. **TYPE_MISMATCH:** sumber dengan `definition.type` ≠ `group.type` → batalkan.
3. **ZONE_REST_OVERRIDE (D6):** override pada zona yang kini `rest` → batalkan, sesi tidak berubah.
4. **list_workspace_files:** path yang resolve di luar workspace dilewati (bukan raise).
5. **add_element:** `1 ≤ count ≤ 1000`, `cols ≥ 1`, `dx`/`dy` finite.
6. **Pencarian sumber:** diurutkan; >1 kecocokan → 400 + daftar path relatif.

## Mutation check

| Mutasi | Tes yang gagal |
|--------|----------------|
| Matikan cabang TYPE_MISMATCH | `test_update_from_source_type_mismatch` |
| Matikan cabang ZONE_REST_OVERRIDE | `test_update_from_source_rejects_rest_override_d6` |
| Symlink luar → raise ValueError | `test_list_workspace_skips_symlink_outside` |

## Verifikasi nyata

```text
pytest tests: 251 passed, 1 skipped, 3 xfailed, 5 subtests passed
tools/check_examples.py: SEMUA LOLOS
node web/src/commands/*.test.ts: 28 passed, 0 failed
```

Xfail pada basis clone (tanpa P5/P7): S2×2, T4. Setelah P5+P7 digabung, xfail tersisa kosong.

## Asumsi / isu terbuka

- Issue info `DEFAULT_KEPT` dikembalikan di body sukses (`issues`) saat update berhasil dengan default yang dipertahankan.
- `find_source_matches` hanya mempertimbangkan berkas di dalam workspace (resolve relative_to).
