"""Uji wajib T04 — penyelesai zona."""
from __future__ import annotations

import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

import pytest


from scad.zones import ResolvedZone, ZoneError, resolve_zones

EXAMPLES = REPO_ROOT / "examples"


def _zones_from_elem():
    elem = json.loads((EXAMPLES / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    return elem["definition"]["zones"]


def _pile_resolved(project, pile_id):
    group = project["groups"][0]
    defaults = group.get("defaults", {}).get("params", {})
    base_depth = defaults.get("depth_below_cof")
    zones = group["definition"]["data"]["zones"]
    inst = next(i for i in group["instances"] if i["id"] == pile_id)
    depth = base_depth
    zone_lengths = None
    if inst.get("overrides"):
        o = inst["overrides"]
        if o.get("params") and "depth_below_cof" in o["params"]:
            depth = o["params"]["depth_below_cof"]
        if o.get("zone_lengths"):
            zone_lengths = o["zone_lengths"]
    return resolve_zones(zones, depth, zone_lengths)


def test_nine_piles_match_expected():
    project = json.loads((EXAMPLES / "P1.project.json").read_text(encoding="utf-8"))
    expected = json.loads((EXAMPLES / "expected_zones.P1.json").read_text(encoding="utf-8"))
    for pile_id, exp in expected.items():
        resolved = _pile_resolved(project, pile_id)
        assert [z.length for z in resolved if z.id == "Z3"][0] == exp["zones"][-1]["length"]
        got = [
            {
                "id": z.id,
                "side": z.side,
                "length": z.length,
                "z_top": z.z_top,
                "z_bottom": z.z_bottom,
            }
            for z in resolved
        ]
        assert got == exp["zones"], f"mismatch {pile_id}"


def test_z3_values():
    project = json.loads((EXAMPLES / "P1.project.json").read_text(encoding="utf-8"))
    cases = {"P1-1": 19000, "P1-2": 15000, "P1-5": 17500, "P1-8": 16000}
    for pid, z3 in cases.items():
        resolved = _pile_resolved(project, pid)
        assert next(z.length for z in resolved if z.id == "Z3") == z3


def test_depth_short():
    zones = _zones_from_elem()
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 10000)
    assert ei.value.code == "ZONE_DEPTH_SHORT"


def test_two_rest():
    zones = [
        {"id": "Z1", "length": "rest"},
        {"id": "Z2", "length": "rest"},
    ]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 5000)
    assert ei.value.code == "ZONE_REST_POS"


def test_only_above_cof():
    zones = [
        {"id": "A1", "side": "above_cof", "length": 500},
        {"id": "A2", "side": "above_cof", "length": 300},
    ]
    r = resolve_zones(zones, depth_below_cof=0)
    assert r[0] == ResolvedZone("A1", "above_cof", 500, 500, 0)
    assert r[1] == ResolvedZone("A2", "above_cof", 300, 800, 500)


def test_no_rest_fixed_equals_depth():
    zones = [
        {"id": "Z1", "length": 3000},
        {"id": "Z2", "length": 7000},
    ]
    r = resolve_zones(zones, 10000)
    assert r[0].z_top == 0 and r[0].z_bottom == -3000
    assert r[1].z_top == -3000 and r[1].z_bottom == -10000
    assert sum(z.length for z in r) == 10000


def test_unknown_zone_length_id():
    zones = _zones_from_elem()
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 30000, {"ZX": 100})
    assert ei.value.code == "REF_MISSING"


# --- Regresi: depth_below_cof non-finite ---


@pytest.mark.parametrize(
    "depth",
    [math.nan, math.inf, -math.inf],
    ids=["nan", "inf", "-inf"],
)
def test_depth_non_finite_rejected(depth):
    zones = [{"id": "Z1", "length": 1000}]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, depth)
    assert ei.value.code == "SCHEMA"


# --- Regresi: panjang zona tetap non-finite ---


@pytest.mark.parametrize(
    "length",
    [math.nan, math.inf, -math.inf],
    ids=["nan", "inf", "-inf"],
)
def test_fixed_zone_length_non_finite_rejected(length):
    zones = [{"id": "Z1", "length": length}]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 10000)
    assert ei.value.code == "SCHEMA"


# --- Regresi: nilai zone_lengths override non-finite ---


@pytest.mark.parametrize(
    "override",
    [math.nan, math.inf, -math.inf],
    ids=["nan", "inf", "-inf"],
)
def test_zone_lengths_override_non_finite_rejected(override):
    zones = [
        {"id": "Z1", "length": 3000},
        {"id": "Z2", "length": 7000},
    ]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 10000, {"Z1": override})
    assert ei.value.code == "SCHEMA"


# --- Regresi: konversi overflow (float(10**400) -> OverflowError) ---


def test_depth_overflow_rejected():
    zones = [{"id": "Z1", "length": 1000}]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 10**400)
    assert ei.value.code == "SCHEMA"


def test_fixed_zone_length_overflow_rejected():
    zones = [{"id": "Z1", "length": 10**400}]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 10000)
    assert ei.value.code == "SCHEMA"


def test_zone_lengths_override_overflow_rejected():
    zones = [
        {"id": "Z1", "length": 3000},
        {"id": "Z2", "length": 7000},
    ]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, 10000, {"Z1": 10**400})
    assert ei.value.code == "SCHEMA"


# --- Regresi: akumulasi koordinat overflow ---


def test_above_cof_coordinate_accumulation_overflow_rejected():
    zones = [
        {"id": "A1", "side": "above_cof", "length": 1e308},
        {"id": "A2", "side": "above_cof", "length": 1e308},
    ]
    with pytest.raises(ZoneError) as ei:
        resolve_zones(zones, depth_below_cof=0)
    assert ei.value.code == "SCHEMA"