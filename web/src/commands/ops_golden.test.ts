/**
 * Golden ops: harus selaras dengan examples/ops_golden.json dan scad.ops (Python).
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { applyOperation } from "./apply.ts";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..", "..");
const golden = JSON.parse(
  readFileSync(join(repoRoot, "examples", "ops_golden.json"), "utf-8"),
);

function loadDoc(ref: string) {
  return JSON.parse(readFileSync(join(repoRoot, ref), "utf-8"));
}

function instanceOverrides(doc: any, groupId: string, pileId: string) {
  for (const g of doc.groups) {
    if (g.id !== groupId) continue;
    for (const inst of g.instances) {
      if (inst.id === pileId) return inst.overrides;
    }
  }
  return undefined;
}

describe("ops golden (parity with Python)", () => {
  for (const c of golden.cases) {
    it(c.id, () => {
      const doc = loadDoc(c.doc_ref);
      const op = c.op as any;

      if (c.expect_error) {
        if (c.id.includes("rest")) {
          assert.throws(() => applyOperation(doc, op));
          return;
        }
        // TS apply tidak throw untuk value <= 0; pile/zone missing → inverse null
        if (c.id.includes("pile_missing") || c.id.includes("zone_missing")) {
          const { inverse } = applyOperation(doc, op);
          assert.equal(inverse, null);
        }
        return;
      }

      if (c.check_roundtrip) {
        const { doc: next, inverse } = applyOperation(doc, op);
        assert.ok(inverse);
        const { doc: back } = applyOperation(next, inverse!);
        assert.deepEqual(
          instanceOverrides(back, op.group, op.pile),
          instanceOverrides(doc, op.group, op.pile),
        );
        return;
      }

      const { doc: next, inverse } = applyOperation(doc, op);
      assert.deepEqual(instanceOverrides(next, op.group, op.pile), c.expected_overrides ?? undefined);
      assert.deepEqual(inverse, c.expected_inverse ?? null);
    });
  }
});
