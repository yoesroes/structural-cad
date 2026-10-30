"""Regression test P0/P1/P1b untuk state server dan batas HTTP."""
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


def instance_by_id(project: dict, pile_id: str) -> dict:
    return next(
        item
        for group in project["groups"]
        for item in group["instances"]
        if item["id"] == pile_id
    )


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
    instance = instance_by_id(response["project"], "P1-2")
    assert "depth_below_cof" not in (instance.get("overrides") or {}).get("params", {})
    assert instance["overrides"]["zone_lengths"]["Z2"] == 7000

    saved = read_project(ui_server["data_root"] / "project.json")
    saved_instance = instance_by_id(saved, "P1-2")
    assert "depth_below_cof" not in (saved_instance.get("overrides") or {}).get("params", {})
    assert saved_instance["overrides"]["zone_lengths"]["Z2"] == 7000


def test_t1_opened_path_is_edit_target(ui_server):
    workspace = ui_server["workspace"]
    data_file = ui_server["data_root"] / "project.json"
    data_before = data_file.read_bytes()
    status, body = request(
        base := ui_server["base"], "POST", "/api/project/open", {"path": "P1.project.json"}
    )
    assert status == 200
    assert body["path"] == "P1.project.json"

    status, body = request(base, "POST", "/api/pile/P1-2/depth", {"depth": 25500})
    assert status == 200
    assert body["ok"] is True
    saved = read_project(workspace / "P1.project.json")
    assert instance_by_id(saved, "P1-2")["overrides"]["params"]["depth_below_cof"] == 25500
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


def test_untitled_project_keeps_path_none_after_pile_edit(ui_server):
    """P1b: project tanpa judul tetap path=None, DIRTY=True setelah edit pile."""
    base = ui_server["base"]
    status, created = request(base, "POST", "/api/project/new", {"id": "NEW", "name": "New"})
    assert status == 200
    assert ui_mod.CURRENT_PATH is None
    assert ui_mod.DIRTY is True

    status, added = request(
        base,
        "POST",
        "/api/project/add-element",
        {"path": "BP_D1200.elem.json", "group_id": "BP-NEW", "count": 1},
    )
    assert status == 200
    assert ui_mod.CURRENT_PATH is None
    assert ui_mod.DIRTY is True

    status, body = request(base, "POST", "/api/pile/P1/depth", {"depth": 28000})
    assert status == 200
    assert body["ok"] is True
    assert ui_mod.CURRENT_PATH is None
    assert ui_mod.DIRTY is True

    status, saved = request(
        base,
        "POST",
        "/api/project/save-as",
        {"path": "NEW.project.json"},
    )
    assert status == 200
    assert saved["path"] == "NEW.project.json"
    assert ui_mod.CURRENT_PATH == ui_server["workspace"] / "NEW.project.json"
    assert ui_mod.DIRTY is False
    assert instance_by_id(
        read_project(ui_server["workspace"] / "NEW.project.json"), "P1"
    )["overrides"]["params"]["depth_below_cof"] == 28000


def test_edit_healthy_pile_while_other_pile_infeasible(ui_server):
    """P1b: error resolve pada pile lain tidak menolak edit pile sehat."""
    base = ui_server["base"]
    status, _ = request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200

    # Tanpa lewat API: tanam override infeasibel pada P1-6 di dokumen sesi.
    doc = copy.deepcopy(ui_mod.CURRENT_DOC)
    for group in doc["groups"]:
        for inst in group.get("instances") or []:
            if inst.get("id") == "P1-6":
                inst.setdefault("overrides", {}).setdefault("params", {})[
                    "depth_below_cof"
                ] = 5000
    ui_mod.CURRENT_DOC = doc
    ui_mod.DIRTY = True

    status, body = request(base, "POST", "/api/pile/P1-1/depth", {"depth": 29000})
    assert status == 200
    assert body["ok"] is True
    assert instance_by_id(ui_mod.CURRENT_DOC, "P1-1")["overrides"]["params"][
        "depth_below_cof"
    ] == 29000


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


@pytest.mark.xfail(strict=True, reason="S2")
def test_s2_foreign_origin_rejected_on_save_as(ui_server):
    """S2 juga harus menolak Origin asing pada /api/project/save-as."""
    workspace = ui_server["workspace"]
    target = workspace / "evil.project.json"
    if target.exists():
        target.unlink()
    status, _ = request(
        ui_server["base"],
        "POST",
        "/api/project/save-as",
        headers={
            "Origin": "https://evil.example",
            "Content-Type": "application/json",
        },
        body={"path": "evil.project.json"},
    )
    assert status in {400, 403, 415}
    assert not target.exists()
