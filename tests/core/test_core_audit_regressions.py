"""Tes regresi audit: S6 zona rest, ZONE_GAP, issue pile (regresi S7 setelah P3)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scad.expr import ExprError, evaluate
from scad.ops import apply_operation
from scad.resolve import resolve_project
from scad.validate import validate_document
from scad.zones import ZoneError, resolve_zones


REPO = Path(__file__).resolve().parents[2]


def load_p1() -> dict:
    return json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))


def test_rest_zone_override_is_rejected():
    """S6: set_pile_zone_length pada zona rest (Z3) harus ValueError."""
    with pytest.raises(ValueError, match="rest"):
        apply_operation(
            load_p1(),
            {
                "op": "set_pile_zone_length",
                "group": "BP-P1",
                "pile": "P1-1",
                "zone": "Z3",
                "value": 17000,
            },
        )


def test_rest_zone_reset_without_override_is_rejected():
    """Reset zona rest tanpa override tersimpan → ValueError."""
    with pytest.raises(ValueError, match="rest"):
        apply_operation(
            load_p1(),
            {
                "op": "reset_pile_zone_length",
                "group": "BP-P1",
                "pile": "P1-1",
                "zone": "Z3",
            },
        )


def test_rest_zone_reset_clears_existing_override():
    """P2b: reset zona rest DIIzinkan bila ada override; validate bersih setelahnya."""
    doc = load_p1()
    for inst in doc["groups"][0]["instances"]:
        if inst["id"] == "P1-1":
            inst["overrides"] = {"zone_lengths": {"Z3": 17000}}
            break
    assert any(i.code == "ZONE_REST_OVERRIDE" for i in validate_document(doc))

    new_doc, inverse = apply_operation(
        doc,
        {
            "op": "reset_pile_zone_length",
            "group": "BP-P1",
            "pile": "P1-1",
            "zone": "Z3",
        },
    )
    assert inverse is not None
    assert inverse["op"] == "set_pile_zone_length"
    inst = next(
        i for g in new_doc["groups"] for i in g["instances"] if i["id"] == "P1-1"
    )
    assert "Z3" not in ((inst.get("overrides") or {}).get("zone_lengths") or {})
    assert not any(i.code == "ZONE_REST_OVERRIDE" for i in validate_document(new_doc))


def test_resolve_zones_rest_override_raises():
    zones = [
        {"id": "Z1", "side": "below_cof", "length": 1000},
        {"id": "Z2", "side": "below_cof", "length": "rest"},
    ]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 5000, {"Z2": 2000})
    assert ei.value.code == "ZONE_REST_OVERRIDE"


def test_validate_rest_override_on_instance():
    doc = load_p1()
    for inst in doc["groups"][0]["instances"]:
        if inst["id"] == "P1-1":
            inst["overrides"] = {"zone_lengths": {"Z3": 17000}}
            break
    issues = validate_document(doc)
    rest_issues = [i for i in issues if i.code == "ZONE_REST_OVERRIDE"]
    assert rest_issues
    assert any("/instances/" in i.path for i in rest_issues)


def test_resolve_instance_issues_carry_pile_and_path():
    doc = load_p1()
    for inst in doc["groups"][0]["instances"]:
        if inst["id"] == "P1-6":
            inst.setdefault("overrides", {}).setdefault("params", {})[
                "depth_below_cof"
            ] = 5000
            break
    out = resolve_project(doc)
    errors = [i for i in out["issues"] if i.get("level") == "error"]
    assert errors
    for issue in errors:
        if issue.get("code") == "ZONE_DEPTH_SHORT":
            assert issue.get("pile") == "P1-6"
            assert issue.get("path", "").startswith("/groups/")
            assert "/instances/" in issue.get("path", "")


def test_zone_gap_warning_when_no_rest_and_short_cover():
    doc = {
        "kind": "project",
        "schema_version": 1,
        "project": {"id": "G", "name": "G"},
        "shapes": {},
        "groups": [
            {
                "id": "G1",
                "type": "bored_pile",
                "definition": {
                    "type": "bored_pile",
                    "data": {
                        "name": "bp",
                        "params": {"diameter": 1200, "depth_below_cof": 10000, "cover": 75},
                        "zones": [
                            {"id": "Z0", "side": "above_cof", "length": 1000},
                            {"id": "Z1", "side": "below_cof", "length": 3000},
                            {"id": "Z2", "side": "below_cof", "length": 2000},
                        ],
                        "rebars": [],
                    },
                },
                "defaults": {"params": {"depth_below_cof": 10000}},
                "instances": [{"id": "P-gap", "x": 0, "y": 0}],
            }
        ],
    }
    out = resolve_project(doc)
    gaps = [i for i in out["issues"] if i.get("code") == "ZONE_GAP"]
    assert gaps
    assert gaps[0]["level"] == "warning"
    assert gaps[0].get("pile") == "P-gap"


def test_resolve_skips_pile_cap_without_depth_error():
    """P2b: grup pile_cap tidak menghasilkan ZONE_DEPTH_SHORT."""
    doc = load_p1()
    # sisipkan grup pile_cap sintetis (hanya untuk resolve, tidak full-schema)
    doc["groups"].append(
        {
            "id": "PC-G",
            "type": "pile_cap",
            "definition": {
                "type": "pile_cap",
                "data": {
                    "name": "cap",
                    "params": {
                        "length": 8400,
                        "width": 8400,
                        "height": 2000,
                        "cover_top": 75,
                        "cover_bottom": 75,
                        "cover_side_x": 75,
                        "cover_side_y": 75,
                    },
                    "zones": [],
                    "rebars": [],
                },
            },
            "instances": [{"id": "PC-1", "x": 0, "y": 0}],
        }
    )
    out = resolve_project(doc)
    pc_errors = [
        i
        for i in out["issues"]
        if i.get("level") == "error"
        and (i.get("pile") == "PC-1" or "PC-G" in (i.get("path") or ""))
        and i.get("code") == "ZONE_DEPTH_SHORT"
    ]
    assert pc_errors == []
    gids = [g["id"] for g in out["groups"]]
    assert "PC-G" in gids


def test_invalid_power_expressions_raise_expr_error():
    for expression in ("=(0-8)**(1/3)", "=0**-1"):
        with pytest.raises(ExprError):
            evaluate(expression)
