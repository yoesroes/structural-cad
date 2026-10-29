# web/ — Perintah TypeScript

Modul logika murni (`src/commands/`), belum di-bundle ke UI monolit `scad_ui/static/index.html`.

## Uji

```bash
node --experimental-strip-types --no-warnings --test src/**/*.test.ts
```

Skrip `npm test` di `package.json` memanggil perintah yang sama (bukan Vitest).

## Isi

| Path | Peran |
|------|--------|
| `src/types.ts` | Kontrak Operation / ResolveResponse |
| `src/commands/apply.ts` | applyOperation (selaras `scad.ops`) |
| `src/commands/console.ts` | Parser SET/RESET |
| `src/commands/registry.ts` | Menu File Project / Elemen |

Jangan mengimpor modul ini ke `scad_engine` atau pipeline STEP. Lihat `docs/ARCHITECTURE_LAYERS.md`.
