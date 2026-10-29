"""Uji wajib T05 — plugin elemen metadata."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

import pytest


# Pastikan plugin terdaftar
import scad.plugins  # noqa: F401
from scad.plugins.base import (
    ElementPlugin,
    get_plugin,
    list_plugins,
    register_plugin,
    validate_params,
    _clear_registry_for_tests,
)
from scad.plugins import bored_pile, pile_cap  # noqa: F401


def test_list_plugins():
    assert list_plugins() == ["bored_pile", "pile_cap"]


def test_bp_params_from_example_ok():
    elem = json.loads(
        (REPO_ROOT / "examples" / "BP_D1200.elem.json").read_text(encoding="utf-8")
    )
    params = elem["definition"]["params"]
    issues = validate_params("bored_pile", params)
    assert issues == []


def test_missing_depth_errors():
    issues = validate_params(
        "bored_pile",
        {"diameter": 1200, "cover": 75},
    )
    assert any(i.code == "SCHEMA" for i in issues)
    assert any("depth_below_cof" in i.message or "depth_below_cof" in i.path for i in issues)


def test_params_schema_matches_schema_file():
    schema = json.loads(
        (REPO_ROOT / "schemas" / "scad.schema.json").read_text(encoding="utf-8")
    )
    expected = schema["$defs"]["BoredPileParams"]
    got = get_plugin("bored_pile").params_schema()
    assert got == expected


def test_duplicate_register_raises():
    class Dup(ElementPlugin):
        type_id = "bored_pile"
        type_version = 1

        def params_schema(self):
            return {}

        def faces(self):
            return []

        def overridable_params(self):
            return []

        def local_frame_doc(self):
            return ""

    with pytest.raises(ValueError, match="sudah terdaftar"):
        register_plugin(Dup)


def test_unknown_plugin_keyerror():
    with pytest.raises(KeyError, match="tidak dikenal"):
        get_plugin("girder_xyz")


def test_pile_cap_faces_and_overridable():
    p = get_plugin("pile_cap")
    assert p.faces() == ["top", "bottom", "x-", "x+", "y-", "y+"]
    assert p.overridable_params() == []
    assert "dasar" in p.local_frame_doc().lower() or "0,0,0" in p.local_frame_doc()
