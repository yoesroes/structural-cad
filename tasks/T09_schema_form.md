# T09 — Komponen form dari JSON Schema
Baca `00_KONTEKS.md` dan `schemas/scad.schema.json` (`$defs/BoredPileParams`, `PileCapParams`).
**Tujuan:** `web/src/components/SchemaForm.tsx` yang merender form dari sub-skema JSON Schema (bagian yang dipakai skema ini saja).
**Props:** `schema: object` (sub-skema yang sudah di-resolve, tanpa `$ref`), `value: object`, `onChange: (v: object) => void`, `errors?: {path: string; message: string}[]`, `labels?: Record<string,string>`, `readOnlyKeys?: string[]`.
**Jenis yang harus didukung:** number/integer (dengan `minimum`, `exclusiveMinimum`; kolom angka), string, boolean (kotak centang), `enum` (select), object (kelompok bertingkat), string-atau-angka ("angka atau ekspresi `=`": satu kolom teks yang menyimpan angka bila murni numerik, selain itu string). Kunci wajib bertanda `*`. Galat ditampilkan di bawah field yang bersangkutan (`aria-describedby`). Utilitas `resolveRefs(schema, root)` ikut di berkas ini.
**Berkas keluaran:** `SchemaForm.tsx`, `SchemaForm.test.tsx`, `resolveRefs.ts`.
**Uji wajib:** form `BoredPileParams` menampilkan 4 field (diameter, depth_below_cof, cover, cover_ref); `cover_ref` berupa select dengan pilihan surface/centerline; mengubah diameter memanggil `onChange` dengan angka; `readOnlyKeys=["diameter"]` mengunci field; galat tampil di field benar; `=cover+16` tersimpan sebagai string, `75` sebagai angka.
**Jangan:** mendukung `oneOf`/`anyOf`/`if` (di luar tugas).
