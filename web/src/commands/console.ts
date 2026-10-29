/**
 * Parser konsol perintah — logika murni, tanpa React.
 * Sintaks (tidak peka huruf besar-kecil):
 *   SET <pile> DEPTH <mm>
 *   RESET <pile> DEPTH
 *   SET <pile> ZONE <idZona> <mm>
 *   RESET <pile> ZONE <idZona>
 */

import type { Operation, ProjectDoc } from "../types";

export type ParseResult =
  | { ok: true; op: Operation }
  | { ok: false; message: string };

interface PileLocation {
  groupId: string;
  pileId: string;
}

function findPile(doc: ProjectDoc, pileId: string): PileLocation | null {
  const groups = Array.isArray(doc?.groups) ? doc.groups : [];
  const needle = String(pileId).toLowerCase();
  for (const g of groups) {
    const instances = Array.isArray(g?.instances) ? g.instances : [];
    for (const inst of instances) {
      if (String(inst?.id ?? "").toLowerCase() === needle) {
        // Kembalikan ID kanonik dari dokumen (bukan token masukan)
        return { groupId: String(g.id), pileId: String(inst.id) };
      }
    }
  }
  return null;
}

function parsePositiveNumber(token: string): number | null {
  if (token === undefined || token === "") return null;
  const n = Number(token);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

/**
 * Parse satu baris perintah konsol menjadi Operation atau pesan galat (Bahasa Indonesia).
 */
export function parseConsole(line: string, doc: ProjectDoc): ParseResult {
  const trimmed = (line ?? "").trim();
  if (!trimmed) {
    return { ok: false, message: "Perintah kosong." };
  }

  const parts = trimmed.split(/\s+/);
  const verb = (parts[0] ?? "").toUpperCase();

  if (verb === "SET") {
    // SET <pile> DEPTH <mm>
    // SET <pile> ZONE <idZona> <mm>
    if (parts.length < 4) {
      return {
        ok: false,
        message: "Sintaks: SET <pile> DEPTH <mm> atau SET <pile> ZONE <idZona> <mm>.",
      };
    }
    const pileId = parts[1];
    const kind = (parts[2] ?? "").toUpperCase();

    const loc = findPile(doc, pileId);
    if (!loc) {
      return { ok: false, message: `Pile '${pileId}' tidak ditemukan di project.` };
    }

    if (kind === "DEPTH") {
      if (parts.length !== 4) {
        return { ok: false, message: "Sintaks: SET <pile> DEPTH <mm>." };
      }
      const value = parsePositiveNumber(parts[3]);
      if (value === null) {
        return { ok: false, message: `Nilai kedalaman harus angka > 0 (diterima: '${parts[3]}').` };
      }
      return {
        ok: true,
        op: { op: "set_pile_depth", group: loc.groupId, pile: loc.pileId, value },
      };
    }

    if (kind === "ZONE") {
      if (parts.length !== 5) {
        return { ok: false, message: "Sintaks: SET <pile> ZONE <idZona> <mm>." };
      }
      const zoneId = parts[3];
      const value = parsePositiveNumber(parts[4]);
      if (value === null) {
        return { ok: false, message: `Nilai panjang zona harus angka > 0 (diterima: '${parts[4]}').` };
      }
      return {
        ok: true,
        op: {
          op: "set_pile_zone_length",
          group: loc.groupId,
          pile: loc.pileId,
          zone: zoneId,
          value,
        },
      };
    }

    return {
      ok: false,
      message: `Jenis SET tidak dikenal: '${parts[2]}'. Gunakan DEPTH atau ZONE.`,
    };
  }

  if (verb === "RESET") {
    // RESET <pile> DEPTH
    // RESET <pile> ZONE <idZona>
    if (parts.length < 3) {
      return {
        ok: false,
        message: "Sintaks: RESET <pile> DEPTH atau RESET <pile> ZONE <idZona>.",
      };
    }
    const pileId = parts[1];
    const kind = (parts[2] ?? "").toUpperCase();

    const loc = findPile(doc, pileId);
    if (!loc) {
      return { ok: false, message: `Pile '${pileId}' tidak ditemukan di project.` };
    }

    if (kind === "DEPTH") {
      if (parts.length !== 3) {
        return { ok: false, message: "Sintaks: RESET <pile> DEPTH." };
      }
      return {
        ok: true,
        op: { op: "reset_pile_depth", group: loc.groupId, pile: loc.pileId },
      };
    }

    if (kind === "ZONE") {
      if (parts.length !== 4) {
        return { ok: false, message: "Sintaks: RESET <pile> ZONE <idZona>." };
      }
      const zoneId = parts[3];
      return {
        ok: true,
        op: {
          op: "reset_pile_zone_length",
          group: loc.groupId,
          pile: loc.pileId,
          zone: zoneId,
        },
      };
    }

    return {
      ok: false,
      message: `Jenis RESET tidak dikenal: '${parts[2]}'. Gunakan DEPTH atau ZONE.`,
    };
  }

  return {
    ok: false,
    message: `Perintah tidak dikenal: '${parts[0]}'. Gunakan SET atau RESET.`,
  };
}
