// KONTRAK: jangan diubah tanpa persetujuan. Dipakai bersama oleh semua tugas UI.
export type Level = "error" | "warning" | "info";
export interface Issue { level: Level; code: string; path: string; message: string }
export interface ResolvedZone { id: string; side: "above_cof" | "below_cof"; length: number; z_top: number; z_bottom: number }
/** overridden berisi "depth_below_cof" dan/atau "zone:<id>" untuk nilai yang menimpa grup */
export interface ResolvedPile { id: string; x: number; y: number; depth_below_cof: number; overridden: string[]; zones: ResolvedZone[] }
export interface ResolvedGroup { id: string; piles: ResolvedPile[] }
export interface ResolveResponse { groups: ResolvedGroup[]; issues: Issue[] }
export type ProjectDoc = Record<string, any>; // bentuk lengkap: schemas/scad.schema.json
export type Operation =
  | { op: "set_pile_depth"; group: string; pile: string; value: number }
  | { op: "reset_pile_depth"; group: string; pile: string }
  | { op: "set_pile_zone_length"; group: string; pile: string; zone: string; value: number }
  | { op: "reset_pile_zone_length"; group: string; pile: string; zone: string };
