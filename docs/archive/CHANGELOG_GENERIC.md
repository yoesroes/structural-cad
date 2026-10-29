# Structural CAD Generic — catatan tahap pertama

## Perubahan
- Audit terhadap `pilecap_rebar.zip` yang tertanam dalam `Structural_cad.zip`.
- Penambahan `pilecap_rebar/generic.py` sebagai lapisan baru tanpa mengganti jalur pile cap lama.
- Penambahan model bored pile silindris dan pile cap balok dengan origin dan rotasi struktur.
- Penambahan centerline reusable: `straight`, `u`, `hook_135_90`, `hook_135_135`, `hook_90_90`.
- Penambahan transformasi koordinat, perpotongan centerline bidang x/y, builder solid CadQuery, dan ekspor STEP.
- Penambahan CLI JSON, contoh JSON, tes generik, dan dokumentasi.

## Verifikasi yang dijalankan
- `python -m pytest -q`: 42 passed, satu FutureWarning dari API `Assembly.save` CadQuery.
- CLI generik menghasilkan STEP satu struktur + satu batang; ukuran sekitar 23 KB pada run verifikasi.
- CLI lama `pilecap_rebar.cli` berjalan dengan rekonsiliasi OK dan menghasilkan CSV/JSON/MD, SVG, dan DXF.
- Audit STEP: 2 `MANIFOLD_SOLID_BREP`, 3 `PRODUCT`, 2 `NEXT_ASSEMBLY_USAGE_OCCURRENCE`; tidak ada klaim ukuran universal karena tergantung versi CAD dan geometri.

## Batas tahap ini
- Radius tekuk menjadi parameter input; tidak ada ketentuan standar yang diasumsikan otomatis.
- Bentuk U dan kait saat ini dihasilkan sebagai centerline polyline dengan pembulatan radius pada builder solid yang tersedia. Validasi detailing standar dan panjang potong belum termasuk.
- Tipe struktur baru dapat didaftarkan untuk validasi dimensi, tetapi tipe tambahan memerlukan cabang builder solid sebelum dapat diekspor sebagai STEP.
- Model generic menyasar satu struktur dan satu batang per contoh; susunan tulangan otomatis tidak termasuk.
