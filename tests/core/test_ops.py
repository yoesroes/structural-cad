"""Uji scad.ops + golden examples/ops_golden.json."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scad.ops import apply_operation

REPO = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((REPO / "examples" / "ops_golden.json").read_text(encoding="utf-8"))


def _load_doc(ref: str) -> dict:
    return json.loads((REPO / ref).read_text(encoding="utf-8"))


def _instance_overrides(doc: dict, group_id: str, pile_id: str):
    for g in doc["groups"]:
        if g["id"] != group_id:
            continue
        for inst in g["instances"]:
            if inst["id"] == pile_id:
                return inst.get("overrides")
    return None


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["id"])
def test_golden_ops(case: dict):
    doc = _load_doc(case["doc_ref"])
    op = case["op"]
    if case.get("expect_error"):
        with pytest.raises(ValueError):
            apply_operation(doc, op)
        return

    new_doc, inverse = apply_operation(doc, op)

    if case.get("check_roundtrip"):
        assert inverse is not None
        back, _ = apply_operation(new_doc, inverse)
        # overrides for that pile should match original
        o_orig = _instance_overrides(doc, op["group"], op["pile"])
        o_back = _instance_overrides(back, op["group"], op["pile"])
        assert o_orig == o_back
        return

    ovr = _instance_overrides(new_doc, op["group"], op["pile"])
    expected = case.get("expected_overrides")
    assert ovr == expected
    assert inverse == case.get("expected_inverse")


def test_input_not_mutated():
    doc = _load_doc("examples/P1.project.json")
    before = copy.deepcopy(doc)
    apply_operation(doc, {"op": "set_pile_depth", "group": "BP-P1", "pile": "P1-1", "value": 27000})
    assert doc == before
