"""Kontrak P10 untuk schema API dan katalog pilihan bentuk."""
from __future__ import annotations

import json
import urllib.request


def request(base: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_element_schema_exposes_context_shape_catalogs(ui_server):
    bored = request(ui_server["base"], "/api/element/bored_pile/schema")
    assert bored["allowed_shapes"] == ["R20", "R87", "RING"]
    assert bored["bursting_shapes"] == []

    cap = request(ui_server["base"], "/api/element/pile_cap/schema")
    assert cap["allowed_shapes"] == ["R20", "U", "U-INV", "X-HOOK-135-90", "X-HOOK-135-135"]
    assert cap["bursting_shapes"] == ["R87", "RING"]
    assert "R87" not in cap["allowed_shapes"]
    assert "RING" not in cap["allowed_shapes"]


def test_ui_shape_choices_are_not_hardcoded():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    html = (repo / "src/scad_ui/static/index.html").read_text(encoding="utf-8")
    app = (repo / "src/scad_ui/static/app.js").read_text(encoding="utf-8")
    assert "R20 · Lurus" not in html
    assert "R87 · Spiral" not in html
    assert "RING · O-ring" not in html
    assert "allowed_shapes" in app
    assert "bursting_shapes" in app
