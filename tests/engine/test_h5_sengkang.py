"""H5: shape_param, R87 by_zone, cincin Z0."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scad.expr import ExprError, evaluate
from scad.shapes import (
    helix_cut_length_segment,
    is_by_zone,
    resolve_by_zone_pitches,
)
from scad_engine.from_v1 import build_bar_groups, recap_pile

REPO = Path(__file__).resolve().parents[2]
DOC = json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))
TOL = 0.5


def test_shape_param_scalar():
    def shape_param(rid, name, zone=None):
        assert rid == "B2" and name == "B"
        return 75.0

    assert evaluate("=shape_param('B2','B')", functions={"shape_param": shape_param}) == 75.0


def test_shape_param_cyclic_raises():
    def shape_param(rid, name, zone=None):
        # rujukan ke diri sendiri lewat ekspresi
        return evaluate(
            "=shape_param('B2','B')",
            functions={"shape_param": shape_param},
        )

    with pytest.raises(ExprError):
        evaluate("=shape_param('B2','B')", functions={"shape_param": shape_param})


def test_r87_scalar_pitch_matches_legacy_formula():
    # A=1050, d=16 → pi*(A-d)=3248.141...; H=3000, pitch=75
    outer, d, height, pitch = 1050.0, 16.0, 3000.0, 75.0
    cut = helix_cut_length_segment(outer, d, height, pitch)
    assert abs(cut - 129970.9) <= TOL


def test_by_zone_missing_zone_raises():
    with pytest.raises(ValueError, match="SHAPE_PARAM"):
        resolve_by_zone_pitches(
            {"by_zone": {"Z1": 75, "Z2": 200}},
            ["Z1", "Z2", "Z3"],
            {"pi": 3.141592653589793},
        )


def test_by_zone_foreign_zone_raises():
    with pytest.raises(ValueError, match="SHAPE_PARAM"):
        resolve_by_zone_pitches(
            {"by_zone": {"Z1": 75, "Z2": 200, "Z9": 1}},
            ["Z1", "Z2"],
            {},
        )


def test_is_by_zone():
    assert is_by_zone({"by_zone": {"Z1": 75}})
    assert not is_by_zone(75)


def test_b5_ring_positions_start_at_pitch():
    groups = build_bar_groups(DOC, "P1-1")
    b5 = next(g for g in groups if g.mark == "B5")
    zs = sorted(inst.origin[2] for inst in b5.instances)
    assert len(zs) == 17
    assert abs(zs[0] - 75.0) <= 1e-6
    assert abs(zs[-1] - 1275.0) <= 1e-6
    for i, z in enumerate(zs):
        assert abs(z - 75.0 * (i + 1)) <= 1e-6


def test_no_b3_in_example():
    data = DOC["groups"][0]["definition"]["data"]
    assert not any(r["id"] == "B3" for r in data["rebars"])
    assert any(r["id"] == "B5" for r in data["rebars"])
