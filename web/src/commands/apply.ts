/**
 * Penerapan Operation pada dokumen project — murni (tidak mengubah masukan).
 */

import type { Operation, ProjectDoc } from "../types";

export interface ApplyResult {
  doc: ProjectDoc;
  inverse: Operation | null;
}

function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

function findGroupIndex(doc: ProjectDoc, groupId: string): number {
  const groups = doc.groups as any[];
  return groups.findIndex((g) => g?.id === groupId);
}

function findInstanceIndex(group: any, pileId: string): number {
  const instances = group.instances as any[];
  return instances.findIndex((i: any) => i?.id === pileId);
}


function groupDefaultDepth(group: any): number | undefined {
  const v = group?.defaults?.params?.depth_below_cof;
  if (typeof v === "number") return v;
  const d = group?.definition?.data?.params?.depth_below_cof;
  return typeof d === "number" ? d : undefined;
}

function definitionZoneLength(group: any, zoneId: string): number | undefined {
  const zones = group?.definition?.data?.zones as any[] | undefined;
  if (!zones) return undefined;
  const z = zones.find((x) => x?.id === zoneId);
  if (z && typeof z.length === "number") return z.length;
  return undefined;
}

/** Hapus kunci kosong bertingkat pada overrides. */
function pruneOverrides(inst: any): void {
  if (!inst.overrides) return;
  const o = inst.overrides;
  if (o.params && Object.keys(o.params).length === 0) delete o.params;
  if (o.zone_lengths && Object.keys(o.zone_lengths).length === 0) delete o.zone_lengths;
  if (Object.keys(o).length === 0) delete inst.overrides;
}

/**
 * Terapkan op pada salinan doc. Mengembalikan dokumen baru + operasi inverse
 * (atau null bila tidak ada perubahan yang perlu dibatalkan).
 */
export function applyOperation(doc: ProjectDoc, op: Operation): ApplyResult {
  const next = deepClone(doc);
  const groups = next.groups as any[];

  const gi = findGroupIndex(next, op.group);
  if (gi < 0) {
    return { doc: next, inverse: null };
  }
  const group = groups[gi];
  const ii = findInstanceIndex(group, op.pile);
  if (ii < 0) {
    return { doc: next, inverse: null };
  }
  const inst = group.instances[ii];

  switch (op.op) {
    case "set_pile_depth": {
      const prev =
        typeof inst.overrides?.params?.depth_below_cof === "number"
          ? inst.overrides.params.depth_below_cof
          : undefined;
      const defaultDepth = groupDefaultDepth(group);

      // Inverse: bila sebelumnya ada override, set kembali; bila tidak, reset
      let inverse: Operation;
      if (prev !== undefined) {
        inverse = {
          op: "set_pile_depth",
          group: op.group,
          pile: op.pile,
          value: prev,
        };
      } else {
        inverse = { op: "reset_pile_depth", group: op.group, pile: op.pile };
      }

      // Jika nilai sama dengan default grup, hapus penimpaan
      if (defaultDepth !== undefined && op.value === defaultDepth) {
        if (inst.overrides?.params) {
          delete inst.overrides.params.depth_below_cof;
        }
        pruneOverrides(inst);
      } else {
        if (!inst.overrides) inst.overrides = {};
        if (!inst.overrides.params) inst.overrides.params = {};
        inst.overrides.params.depth_below_cof = op.value;
      }

      // Tidak ada perubahan efektif?
      if (prev === undefined && defaultDepth !== undefined && op.value === defaultDepth) {
        return { doc: next, inverse: null };
      }
      if (prev === op.value) {
        return { doc: next, inverse: null };
      }
      return { doc: next, inverse };
    }

    case "reset_pile_depth": {
      const prev =
        typeof inst.overrides?.params?.depth_below_cof === "number"
          ? inst.overrides.params.depth_below_cof
          : undefined;
      if (prev === undefined) {
        return { doc: next, inverse: null };
      }
      const inverse: Operation = {
        op: "set_pile_depth",
        group: op.group,
        pile: op.pile,
        value: prev,
      };
      if (inst.overrides?.params) {
        delete inst.overrides.params.depth_below_cof;
      }
      pruneOverrides(inst);
      return { doc: next, inverse };
    }

    case "set_pile_zone_length": {
      const zones = (group?.definition?.data?.zones as any[]) || [];
      if (!zones.some((z) => z?.id === op.zone)) {
        return { doc: next, inverse: null };
      }
      const prev =
        typeof inst.overrides?.zone_lengths?.[op.zone] === "number"
          ? inst.overrides.zone_lengths[op.zone]
          : undefined;

      let inverse: Operation;
      if (prev !== undefined) {
        inverse = {
          op: "set_pile_zone_length",
          group: op.group,
          pile: op.pile,
          zone: op.zone,
          value: prev,
        };
      } else {
        inverse = {
          op: "reset_pile_zone_length",
          group: op.group,
          pile: op.pile,
          zone: op.zone,
        };
      }

      const defLen = definitionZoneLength(group, op.zone);
      if (defLen !== undefined && op.value === defLen) {
        if (inst.overrides?.zone_lengths) {
          delete inst.overrides.zone_lengths[op.zone];
        }
        pruneOverrides(inst);
      } else {
        if (!inst.overrides) inst.overrides = {};
        if (!inst.overrides.zone_lengths) inst.overrides.zone_lengths = {};
        inst.overrides.zone_lengths[op.zone] = op.value;
      }

      if (prev === undefined && defLen !== undefined && op.value === defLen) {
        return { doc: next, inverse: null };
      }
      if (prev === op.value) {
        return { doc: next, inverse: null };
      }
      return { doc: next, inverse };
    }

    case "reset_pile_zone_length": {
      const zonesR = (group?.definition?.data?.zones as any[]) || [];
      if (!zonesR.some((z) => z?.id === op.zone)) {
        return { doc: next, inverse: null };
      }
      const prev =
        typeof inst.overrides?.zone_lengths?.[op.zone] === "number"
          ? inst.overrides.zone_lengths[op.zone]
          : undefined;
      if (prev === undefined) {
        return { doc: next, inverse: null };
      }
      const inverse: Operation = {
        op: "set_pile_zone_length",
        group: op.group,
        pile: op.pile,
        zone: op.zone,
        value: prev,
      };
      if (inst.overrides?.zone_lengths) {
        delete inst.overrides.zone_lengths[op.zone];
      }
      pruneOverrides(inst);
      return { doc: next, inverse };
    }

    default: {
      // TypeScript exhaustiveness
      const _exhaustive: never = op;
      void _exhaustive;
      return { doc: next, inverse: null };
    }
  }
}
