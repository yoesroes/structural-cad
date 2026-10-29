"""Uji wajib T03 — validator dokumen."""
from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

import pytest


from scad.validate import validate_document

EXAMPLES = REPO_ROOT / "examples"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


def test_examples_have_no_errors():
    for name in ("BP_D1200.elem.json", "P1.project.json", "shapes.builtin.json"):
        issues = validate_document(_load(name))
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], f"{name}: {errors}"


def test_override_diameter_is_schema():
    doc = _load("P1.project.json")
    doc = copy.deepcopy(doc)
    # Override parameter yang tidak diizinkan (hanya depth_below_cof)
    doc["groups"][0]["instances"][0]["overrides"] = {
        "params": {"diameter": 1500}
    }
    codes = _codes(validate_document(doc))
    assert "SCHEMA" in codes


def test_duplicate_rebar_id():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    rebars = doc["definition"]["rebars"]
    rebars.append(copy.deepcopy(rebars[0]))  # same id
    codes = _codes(validate_document(doc))
    assert "ID_DUP" in codes


def test_missing_zone_ref():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    doc["definition"]["rebars"][0]["extent"]["zones"] = ["Z9"]
    codes = _codes(validate_document(doc))
    assert "REF_MISSING" in codes


def test_rest_not_last_below():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    # Z1 becomes rest while Z2/Z3 still below
    doc["definition"]["zones"][1]["length"] = "rest"
    codes = _codes(validate_document(doc))
    assert "ZONE_REST_POS" in codes


def test_position_cycle():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    rebars = doc["definition"]["rebars"]
    # B1 -> B2, B2 -> B1
    rebars[0]["position"] = {"ref": "bar", "bar": "B2", "relation": "inside", "gap": 0}
    rebars[1]["position"] = {"ref": "bar", "bar": "B1", "relation": "outside", "gap": 0}
    codes = _codes(validate_document(doc))
    assert "POS_CYCLE" in codes


def test_hash_diff_info():
    doc = _load("P1.project.json")
    doc = copy.deepcopy(doc)
    # ubah definisi tertanam tanpa update hash
    doc["groups"][0]["definition"]["data"]["name"] = "Diubah"
    issues = validate_document(doc)
    assert any(i.code == "HASH_DIFF" and i.level == "info" for i in issues)
