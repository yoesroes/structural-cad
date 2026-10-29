"""Uji resolve_project untuk Gelombang C."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


from scad.resolve import resolve_project


def test_resolve_p1():
    doc = json.loads((REPO_ROOT / "examples" / "P1.project.json").read_text(encoding="utf-8"))
    out = resolve_project(doc)
    assert out["groups"]
    piles = {p["id"]: p for p in out["groups"][0]["piles"]}
    assert piles["P1-1"]["depth_below_cof"] == 30000
    assert piles["P1-2"]["depth_below_cof"] == 26000
    z3 = {z["id"]: z for z in piles["P1-8"]["zones"]}["Z3"]
    assert z3["length"] == 16000
    assert "depth_below_cof" in piles["P1-2"]["overridden"]


def _project_with_bad_zone_instance():
    """Dokumen minimal: 2 grup; grup ke-2 punya 2 instance, instance ke-2 gagal zona.

    depth_below_cof=1000, zona below_cof tetap total 3000 -> ZONE_DEPTH_SHORT.
    """
    bad_group = {
        "id": "G2",
        "definition": {
            "data": {
                "zones": [
                    {"id": "Z1", "side": "below_cof", "length": 3000},
                ]
            }
        },
        "defaults": {"params": {"depth_below_cof": 1000}},
        "instances": [
            {"id": "OK-1", "x": 0, "y": 0},
            {"id": "BAD-1", "x": 1000, "y": 0},
        ],
    }
    good_group = {
        "id": "G1",
        "definition": {"data": {"zones": [{"id": "Z1", "side": "below_cof", "length": 500}]}},
        "defaults": {"params": {"depth_below_cof": 500}},
        "instances": [{"id": "OK-0", "x": 0, "y": 0}],
    }
    return {"kind": "project", "schema_version": 1, "groups": [good_group, bad_group]}


def test_zone_error_path_points_to_group_and_instance_index():
    doc = _project_with_bad_zone_instance()
    out = resolve_project(doc)

    zone_errors = [
        i for i in out["issues"]
        if i["code"] == "ZONE_DEPTH_SHORT" and i["path"].startswith("/groups/")
    ]
    assert len(zone_errors) == 1

    # Grup indeks 1, instance indeks 1 (BAD-1)
    assert zone_errors[0]["path"] == "/groups/1/instances/1"
    assert "BAD-1" in zone_errors[0]["message"]


def test_zone_error_path_group_index_zero():
    """Pastikan gi=0 dan ii=0 juga menghasilkan path yang benar."""
    doc = {
        "kind": "project",
        "schema_version": 1,
        "groups": [
            {
                "id": "G1",
                "definition": {
                    "data": {"zones": [{"id": "Z1", "side": "below_cof", "length": 3000}]}
                },
                "defaults": {"params": {"depth_below_cof": 1000}},
                "instances": [{"id": "BAD-0", "x": 0, "y": 0}],
            }
        ],
    }
    out = resolve_project(doc)
    zone_errors = [i for i in out["issues"] if i["code"] == "ZONE_DEPTH_SHORT"]
    assert len(zone_errors) == 1
    assert zone_errors[0]["path"] == "/groups/0/instances/0"


def test_zone_error_path_uses_override_depth():
    """Override depth_below_cof pada instance memicu error di indeks instance yang tepat."""
    doc = {
        "kind": "project",
        "schema_version": 1,
        "groups": [
            {
                "id": "G1",
                "definition": {
                    "data": {"zones": [{"id": "Z1", "side": "below_cof", "length": 3000}]}
                },
                "defaults": {"params": {"depth_below_cof": 5000}},
                "instances": [
                    {"id": "OK-0", "x": 0, "y": 0},
                    {
                        "id": "BAD-1",
                        "x": 1000,
                        "y": 0,
                        "overrides": {"params": {"depth_below_cof": 1000}},
                    },
                ],
            }
        ],
    }
    out = resolve_project(doc)
    zone_errors = [i for i in out["issues"] if i["code"] == "ZONE_DEPTH_SHORT"]
    assert len(zone_errors) == 1
    assert zone_errors[0]["path"] == "/groups/0/instances/1"
    
def test_zone_error_path_points_to_group_and_instance_index():
    doc = _project_with_bad_zone_instance()
    out = resolve_project(doc)

    zone_errors = [
        i for i in out["issues"]
        if i["code"] == "ZONE_DEPTH_SHORT"
        and i["path"] == "/groups/1/instances/1"
    ]
    assert len(zone_errors) == 1
  
