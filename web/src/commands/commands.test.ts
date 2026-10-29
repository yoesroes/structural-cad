/**
 * Uji wajib T10 — registri perintah, parser konsol, applyOperation.
 * Dijalankan dengan: node --experimental-strip-types --test src/commands/commands.test.ts
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parseConsole } from "./console.ts";
import { applyOperation } from "./apply.ts";
import { buildMenu, COMMANDS } from "./registry.ts";
import type { ProjectDoc, Operation } from "../types.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "../../../");
const projectPath = resolve(ROOT, "examples/P1.project.json");

function loadProject(): ProjectDoc {
  return JSON.parse(readFileSync(projectPath, "utf-8"));
}

describe("parseConsole", () => {
  it("SET P1-1 DEPTH 27000 -> op benar", () => {
    const doc = loadProject();
    const r = parseConsole("SET P1-1 DEPTH 27000", doc);
    assert.equal(r.ok, true);
    if (!r.ok) return;
    assert.deepEqual(r.op, {
      op: "set_pile_depth",
      group: "BP-P1",
      pile: "P1-1",
      value: 27000,
    });
  });

  it("tidak peka huruf besar-kecil", () => {
    const doc = loadProject();
    const r = parseConsole("set p1-1 depth 27000", doc);
    assert.equal(r.ok, true);
    if (!r.ok) return;
    assert.equal(r.op.op, "set_pile_depth");
  });

  it("SET P1-99 DEPTH 1000 gagal dengan pesan Indonesia", () => {
    const doc = loadProject();
    const r = parseConsole("SET P1-99 DEPTH 1000", doc);
    assert.equal(r.ok, false);
    if (r.ok) return;
    assert.match(r.message, /P1-99/);
    assert.match(r.message, /tidak ditemukan/i);
  });

  it("nilai non-positif ditolak", () => {
    const doc = loadProject();
    assert.equal(parseConsole("SET P1-1 DEPTH 0", doc).ok, false);
    assert.equal(parseConsole("SET P1-1 DEPTH -5", doc).ok, false);
    assert.equal(parseConsole("SET P1-1 DEPTH abc", doc).ok, false);
  });

  it("SET / RESET ZONE", () => {
    const doc = loadProject();
    const setZ = parseConsole("SET P1-8 ZONE Z2 7000", doc);
    assert.equal(setZ.ok, true);
    if (setZ.ok) {
      assert.deepEqual(setZ.op, {
        op: "set_pile_zone_length",
        group: "BP-P1",
        pile: "P1-8",
        zone: "Z2",
        value: 7000,
      });
    }
    const resetZ = parseConsole("RESET P1-8 ZONE Z2", doc);
    assert.equal(resetZ.ok, true);
    if (resetZ.ok) {
      assert.deepEqual(resetZ.op, {
        op: "reset_pile_zone_length",
        group: "BP-P1",
        pile: "P1-8",
        zone: "Z2",
      });
    }
  });

  it("RESET P1-2 DEPTH", () => {
    const doc = loadProject();
    const r = parseConsole("RESET P1-2 DEPTH", doc);
    assert.equal(r.ok, true);
    if (!r.ok) return;
    assert.deepEqual(r.op, {
      op: "reset_pile_depth",
      group: "BP-P1",
      pile: "P1-2",
    });
  });
});

describe("applyOperation", () => {
  it("SET P1-1 DEPTH 27000 menulis override", () => {
    const doc = loadProject();
    const op: Operation = {
      op: "set_pile_depth",
      group: "BP-P1",
      pile: "P1-1",
      value: 27000,
    };
    const { doc: next } = applyOperation(doc, op);
    assert.equal(doc.groups[0].instances[0].overrides, undefined);
    const inst = next.groups[0].instances.find((i: any) => i.id === "P1-1");
    assert.equal(inst.overrides.params.depth_below_cof, 27000);
  });

  it("SET P1-1 DEPTH 30000 (sama default grup) tidak meninggalkan overrides", () => {
    const doc = loadProject();
    const mid = applyOperation(doc, {
      op: "set_pile_depth",
      group: "BP-P1",
      pile: "P1-1",
      value: 27000,
    }).doc;
    const { doc: next } = applyOperation(mid, {
      op: "set_pile_depth",
      group: "BP-P1",
      pile: "P1-1",
      value: 30000,
    });
    const inst = next.groups[0].instances.find((i: any) => i.id === "P1-1");
    assert.equal(inst.overrides, undefined);
  });

  it("RESET P1-2 DEPTH menghapus override", () => {
    const doc = loadProject();
    const p2before = doc.groups[0].instances.find((i: any) => i.id === "P1-2");
    assert.equal(p2before.overrides.params.depth_below_cof, 26000);

    const { doc: next } = applyOperation(doc, {
      op: "reset_pile_depth",
      group: "BP-P1",
      pile: "P1-2",
    });
    const p2 = next.groups[0].instances.find((i: any) => i.id === "P1-2");
    assert.equal(p2.overrides, undefined);
  });

  it("inverse dari set mengembalikan dokumen yang toEqual aslinya", () => {
    const doc = loadProject();
    const op: Operation = {
      op: "set_pile_depth",
      group: "BP-P1",
      pile: "P1-1",
      value: 27000,
    };
    const { doc: changed, inverse } = applyOperation(doc, op);
    assert.ok(inverse);
    const { doc: restored } = applyOperation(changed, inverse!);
    assert.deepEqual(restored, doc);
  });

  it("inverse dari reset mengembalikan override semula", () => {
    const doc = loadProject();
    const { doc: changed, inverse } = applyOperation(doc, {
      op: "reset_pile_depth",
      group: "BP-P1",
      pile: "P1-2",
    });
    assert.ok(inverse);
    const { doc: restored } = applyOperation(changed, inverse!);
    assert.deepEqual(restored, doc);
  });

  it("SET ZONE dan inverse", () => {
    const doc = loadProject();
    const op: Operation = {
      op: "set_pile_zone_length",
      group: "BP-P1",
      pile: "P1-1",
      zone: "Z2",
      value: 7500,
    };
    const { doc: changed, inverse } = applyOperation(doc, op);
    const inst = changed.groups[0].instances.find((i: any) => i.id === "P1-1");
    assert.equal(inst.overrides.zone_lengths.Z2, 7500);
    const { doc: restored } = applyOperation(changed, inverse!);
    assert.deepEqual(restored, doc);
  });
});

describe("buildMenu / registry", () => {
  it("tanpa project item Simpan nonaktif", () => {
    const menu = buildMenu({ hasProject: false, dirty: false, hasElementFile: false });
    const file = menu.find((m) => m.label === "File");
    assert.ok(file);
    const project = file!.children?.find((c) => c.label === "Project");
    assert.ok(project);
    const save = project!.children?.find((c) => c.label === "Simpan");
    assert.ok(save);
    assert.equal(save!.enabled, false);
  });

  it("dengan project dirty, Simpan aktif", () => {
    const menu = buildMenu({ hasProject: true, dirty: true, hasElementFile: false });
    const file = menu.find((m) => m.label === "File");
    const project = file!.children?.find((c) => c.label === "Project");
    const save = project!.children?.find((c) => c.label === "Simpan");
    assert.equal(save!.enabled, true);
  });

  it("COMMANDS memuat item File Project dan File Elemen", () => {
    const ids = COMMANDS.map((c) => c.id);
    assert.ok(ids.includes("project.new"));
    assert.ok(ids.includes("project.save"));
    assert.ok(ids.includes("element.open"));
    assert.ok(ids.includes("project.addElementFile"));
  });
});
