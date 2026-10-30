"""Tes API pile memakai scad.ops (P0)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def _request(base: str, path: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_api_pile_depth_same_as_default_no_overrides(ui_server):
    status, body = _request(ui_server["base"], "/api/pile/P1-1/depth", {"depth": 30000})
    assert status == 200
    assert body["ok"] is True
    saved = json.loads((ui_server["data_root"] / "project.json").read_text(encoding="utf-8"))
    inst = next(i for g in saved["groups"] for i in g["instances"] if i["id"] == "P1-1")
    assert not (inst.get("overrides") or {}).get("params", {}).get("depth_below_cof")
    assert "depth_below_cof" not in (body.get("pile") or {}).get("overridden", [])


def test_api_pile_reset_zone_p1_8(ui_server):
    status, body = _request(
        ui_server["base"], "/api/pile/P1-8/reset", {"field": "zone:Z2"}
    )
    assert status == 200
    assert body["ok"] is True
    saved = json.loads((ui_server["data_root"] / "project.json").read_text(encoding="utf-8"))
    inst = next(i for g in saved["groups"] for i in g["instances"] if i["id"] == "P1-8")
    assert "Z2" not in ((inst.get("overrides") or {}).get("zone_lengths") or {})
    assert inst["overrides"]["params"]["depth_below_cof"] == 26000
