"""Kontrak P10: katalog bentuk per jenis elemen dan bursting steel."""
from __future__ import annotations

import json
from pathlib import Path

from scad.plugins import get_plugin
from scad.shapes import build_centerline
from scad.validate import validate_document

REPO = Path(__file__).resolve().parents[2]


def load(name: str) -> dict:
    return json.loads((REPO / "examples" / name).read_text(encoding="utf-8"))


def codes(doc: dict) -> list[str]:
    return [issue.code for issue in validate_document(doc)]


def test_plugin_shape_catalogs_are_context_specific():
    bored = get_plugin("bored_pile")
    cap = get_plugin("pile_cap")
    assert bored.allowed_shapes(set()) == ["R20", "R87", "RING"]
    assert bored.bursting_shapes() == []
    assert cap.allowed_shapes(set()) == ["R20", "U", "U-INV", "X-HOOK-135-90", "X-HOOK-135-135"]
    assert cap.bursting_shapes() == ["R87", "RING"]


def test_bored_pile_rejects_shapes_outside_catalog():
    doc = load("BP_D1200.elem.json")
    doc["definition"]["rebars"][0]["shape"]["code"] = "37"
    assert "SHAPE_NOT_ALLOWED" in codes(doc)

    doc = load("BP_D1200.elem.json")
    doc["definition"]["rebars"][0]["shape"]["code"] = "X-HOOK-135-90"
    assert "SHAPE_NOT_ALLOWED" in codes(doc)

    doc = load("BP_D1200.elem.json")
    doc["definition"]["rebars"][0]["shape"]["code"] = "U"
    assert "SHAPE_NOT_ALLOWED" in codes(doc)


def test_pile_cap_allows_existing_hook_shapes():
    doc = load("PC_8400.elem.json")
    assert "SHAPE_NOT_ALLOWED" not in codes(doc)


def test_pile_cap_rejects_spiral_and_ring_as_main():
    doc = load("PC_8400.elem.json")
    doc["definition"]["rebars"][0]["shape"]["code"] = "R87"
    assert "SHAPE_NOT_ALLOWED" in codes(doc)

    doc = load("PC_8400.elem.json")
    doc["definition"]["rebars"][0]["shape"]["code"] = "RING"
    assert "SHAPE_NOT_ALLOWED" in codes(doc)


def test_pile_cap_bursting_requires_feature_and_purpose():
    doc = load("PC_8400.elem.json")
    data = doc["definition"]
    data["features"] = ["post_tensioning"]
    doc["shapes"]["RING"] = load("BP_D1200.elem.json")["shapes"]["RING"]
    data["rebars"][0]["shape"]["code"] = "RING"
    data["rebars"][0]["purpose"] = "bursting"
    assert "SHAPE_NOT_ALLOWED" not in codes(doc)

    doc["definition"]["rebars"][0]["purpose"] = "main"
    assert "SHAPE_NOT_ALLOWED" in codes(doc)

    doc = load("PC_8400.elem.json")
    doc["shapes"]["RING"] = load("BP_D1200.elem.json")["shapes"]["RING"]
    doc["definition"]["rebars"][0]["shape"]["code"] = "RING"
    doc["definition"]["rebars"][0]["purpose"] = "bursting"
    assert "SHAPE_NOT_ALLOWED" in codes(doc)


def test_legacy_examples_remain_valid_without_optional_flags():
    for name in ("BP_D1200.elem.json", "PC_8400.elem.json", "P1.project.json"):
        errors = [i for i in validate_document(load(name)) if i.level == "error"]
        assert errors == [], (name, errors)


def test_unsupported_builder_message_mentions_code_and_supported_builders():
    shape = {"code": "37", "builder": {"type": "polyline_outside"}}
    try:
        build_centerline(shape, {}, 16, {})
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("builder yang tidak didukung seharusnya gagal")
    assert "37" in message
    assert "straight" in message and "helix" in message and "ring" in message
