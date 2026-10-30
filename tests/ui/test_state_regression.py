"""Regression test P0 untuk state server dan batas HTTP."""
from __future__ import annotations

import copy
import json
import urllib.error
import urllib.request

import pytest

from scad_ui import server as ui_mod


def request(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    *,
    headers: dict[str, str] | None = None,
    raw_body: bytes | None = None,
) -> tuple[int, dict]:
    data = raw_body if raw_body is not None else (
        None if body is None else json.dumps(body).encode("utf-8")
    )
    request_headers = dict(headers or {})
    if body is not None and "Content-Type" not in request_headers:
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{base}{path}", data=data, headers=request_headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def read_project(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_t1_two_depth_edits_are_visible_in_disk_and_get(ui_server):
    base = ui_server["base"]
    assert request(base, "POST", "/api/pile/P1-2/depth", {"depth": 25500})[0] == 200
    assert request(base, "POST", "/api/pile/P1-5/depth", {"depth": 25000})[0] == 200

    status, response = request(base, "GET", "/api/project")
    assert status == 200
    instances = {
        item["id"]: item
        for group in response["project"]["groups"]
        for item in group["instances"]
    }
    assert instances["P1-2"]["overrides"]["params"]["depth_below_cof"] == 25500
    assert instances["P1-5"]["overrides"]["params"]["depth_below_cof"] == 25000

    saved = read_project(ui_server["data_root"] / "project.json")
    saved_instances = {
        item["id"]: item
        for group in saved["groups"]
        for item in group["instances"]
    }
    assert saved_instances["P1-2"]["overrides"]["params"]["depth_below_cof"] == 25500
    assert saved_instances["P1-5"]["overrides"]["params"]["depth_below_cof"] == 25000


def test_t1_three_sequential_operations_preserve_disk_and_get(ui_server):
    base = ui_server["base"]
    assert request(base, "POST", "/api/pile/P1-2/depth", {"depth": 25500})[0] == 200
    assert request(
        base,
        "POST",
        "/api/pile/P1-2/zone",
        {"zone": "Z2", "length": 7000},
    )[0] == 200
    assert request(
        base,
        "POST",
        "/api/pile/P1-2/reset",
        {"field": "depth"},
    )[0] == 200

    status, response = request(base, "GET", "/api/project")
    assert status == 200
    instance = next(
        item
        for group in response["project"]["groups"]
        for item in group["instances"]
        if item["id"] == "P1-2"
    )
    assert "depth_below_cof" not in (instance.get("overrides") or {}).get("params", {})
    assert instance["overrides"]["zone_lengths"]["Z2"] == 7000

    saved = read_project(ui_server["data_root"] / "project.json")
    saved_instance = next(
        item
        for group in saved["groups"]
        for item in group["instances"]
        if item["id"] == "P1-2"
    )
    assert "depth_below_cof" not in (saved_instance.get("overrides") or {}).get("params", {})
    assert saved_instance["overrides"]["zone_lengths"]["Z2"] == 7000


def test_t1_opened_path_is_edit_target(ui_server):
    workspace = ui_server["workspace"]
    data_file = ui_server["data_root"] / "project.json"
    data_before = data_file.read_bytes()
    status, body = request(base := ui_server["base"], "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    assert body["path"] == "P1.project.json"

    status, body = request(base, "POST", "/api/pile/P1-2/depth", {"depth": 25500})
    assert status == 200
    assert body["ok"] is True
    assert read_project(workspace / "P1.project.json")["groups"][0]["instances"][1]["overrides"]["params"]["depth_below_cof"] == 25500
    assert data_file.read_bytes() == data_before


def test_t2_unfeasible_depth_is_rejected_without_disk_change(ui_server):
    project_file = ui_server["data_root"] / "project.json"
    before = project_file.read_bytes()
    status, body = request(
        ui_server["base"], "POST", "/api/pile/P1-6/depth", {"depth": 5000}
    )
    assert status == 400
    assert body["ok"] is False
    assert any(issue["code"] == "ZONE_DEPTH_SHORT" for issue in body["issues"])
    assert project_file.read_bytes() == before


def test_s1_invalid_rebar_does_not_poison_session(ui_server):
    base = ui_server["base"]
    status, opened = request(base, "GET", "/api/project")
    assert status == 200
    before = copy.deepcopy(opened["project"])
    status, _ = request(
        base,
        "POST",
        "/api/element/BP-P1/rebar",
        {"id": "BAD", "diameter": -1},
    )
    assert status == 400
    assert ui_mod.CURRENT_DOC == before
    save_status, _ = request(base, "POST", "/api/project/save", {})
    assert save_status == 200


@pytest.mark.xfail(strict=True, reason="S2")
def test_s2_foreign_headers_are_rejected_without_write(ui_server):
    path = ui_server["data_root"] / "project.json"
    before = path.read_bytes()
    base = ui_server["base"]
    cases = [
        {"Host": "evil.example", "Content-Type": "application/json"},
        {"Origin": "https://evil.example", "Content-Type": "application/json"},
        {"Content-Type": "text/plain"},
    ]
    for headers in cases:
        status, _ = request(
            base,
            "POST",
            "/api/project/save",
            headers=headers,
            raw_body=b"{}",
        )
        assert status in {400, 403, 415}
    assert path.read_bytes() == before
