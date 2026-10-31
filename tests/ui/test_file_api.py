"""Tes HTTP G2/H1 dengan fixture ui_server bersama (P1b: tanpa http_workspace)."""
from __future__ import annotations

import copy
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from scad.io.canonical import sha256_of
from scad.validate import validate_document
from scad_ui import server as ui_mod
from scad_ui.server import Handler

REPO = Path(__file__).resolve().parents[2]


def _request(base: str, method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def _valid_errors(doc: dict) -> list:
    return [issue for issue in validate_document(doc) if issue.level == "error"]


def _instance(project: dict, pile_id: str) -> dict:
    return next(
        inst
        for group in project["groups"]
        for inst in group["instances"]
        if inst["id"] == pile_id
    )


def test_project_new_save_as_open_roundtrip(ui_server):
    base = ui_server["base"]
    status, created = _request(base, "POST", "/api/project/new", {"id": "NEW", "name": "New"})
    assert status == 200
    assert _valid_errors(created["project"]) == []

    status, saved = _request(
        base,
        "POST",
        "/api/project/save-as",
        {"path": "NEW.project.json", "doc": created["project"]},
    )
    assert status == 200
    assert saved["path"] == "NEW.project.json"

    status, opened = _request(base, "POST", "/api/project/open", {"path": "NEW.project.json"})
    assert status == 200
    assert opened["project"] == created["project"]
    assert _valid_errors(opened["project"]) == []


def test_project_new_clears_previous_path_before_save(ui_server):
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    status, _ = _request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200

    status, created = _request(base, "POST", "/api/project/new", {"id": "NEW", "name": "New"})
    assert status == 200
    status, saved = _request(base, "POST", "/api/project/save", {"doc": created["project"]})
    assert status == 200
    assert saved["path"] == str((ui_mod.DATA_ROOT / "project.json"))
    assert json.loads((workspace / "P1.project.json").read_text(encoding="utf-8"))["project"]["id"] == "P1"
    assert json.loads((ui_mod.DATA_ROOT / "project.json").read_text(encoding="utf-8"))["project"]["id"] == "NEW"


def test_project_open_rejects_structurally_invalid_document(ui_server):
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    invalid = workspace / "invalid.project.json"
    invalid.write_text(json.dumps({"kind": "project", "schema_version": 1}), encoding="utf-8")
    status, body = _request(base, "POST", "/api/project/open", {"path": invalid.name})
    assert status == 400
    assert body["ok"] is False
    assert "/project" in body["error"] or "project" in body["error"]


def test_project_save_as_invalid_does_not_create_file(ui_server):
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    invalid = {"kind": "project", "schema_version": 1}
    status, body = _request(
        base,
        "POST",
        "/api/project/save-as",
        {"path": "invalid.project.json", "doc": invalid},
    )
    assert status == 400
    assert body["ok"] is False
    assert not (workspace / "invalid.project.json").exists()
    assert list(workspace.glob("*.tmp")) == []


def test_project_save_as_invalid_keeps_active_project(ui_server):
    base = ui_server["base"]
    status, created = _request(base, "POST", "/api/project/new", {"id": "ACTIVE", "name": "Active"})
    assert status == 200
    active = created["project"]
    status, _ = _request(
        base,
        "POST",
        "/api/project/save-as",
        {"path": "bad.project.json", "doc": {"kind": "project", "schema_version": 1}},
    )
    assert status == 400
    assert ui_mod.CURRENT_DOC == active
    assert not (ui_server["workspace"] / "bad.project.json").exists()


def test_element_new_defaults_are_valid_for_supported_plugins(ui_server):
    base = ui_server["base"]
    for type_id in ("bored_pile", "pile_cap"):
        status, body = _request(base, "POST", "/api/element/new", {"type": type_id})
        assert status == 200
        assert body["element"]["definition"]["type"] == type_id
        assert _valid_errors(body["element"]) == []


def test_project_new_invalid_input_returns_400_and_connection_survives(ui_server):
    base = ui_server["base"]
    status, body = _request(base, "POST", "/api/project/new", {"id": "bad id!"})
    assert status == 400
    assert body["ok"] is False
    assert "error" in body

    status, body = _request(base, "POST", "/api/project/new", {"id": "GOOD", "name": "Good"})
    assert status == 200
    assert body["project"]["project"]["id"] == "GOOD"


def test_unexpected_http_exception_returns_500_and_server_survives(ui_server, monkeypatch):
    base = ui_server["base"]

    def boom(self, data):
        raise RuntimeError("detail internal yang tidak boleh dikirim")

    monkeypatch.setattr(Handler, "api_project_new", boom)
    status, body = _request(base, "POST", "/api/project/new", {"id": "FAIL"})
    assert status == 500
    assert body == {"ok": False, "error": "Galat internal"}

    monkeypatch.undo()
    status, body = _request(base, "POST", "/api/project/new", {"id": "AFTER", "name": "After"})
    assert status == 200
    assert body["project"]["project"]["id"] == "AFTER"


def test_add_element_to_existing_project_validates_and_places_grid(ui_server):
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    status, _ = _request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    status, body = _request(
        base,
        "POST",
        "/api/project/add-element",
        {
            "path": "BP_D1200.elem.json",
            "group_id": "BP-NEW",
            "count": 4,
            "naming": {"pattern": "N-{n}", "start": 1},
            "layout": {"cols": 2, "dx": 3000, "dy": 3000},
        },
    )
    assert status == 200
    assert body["source"]["hash"] == sha256_of(
        json.loads((workspace / "BP_D1200.elem.json").read_text(encoding="utf-8"))["definition"]
    )
    assert [(i["x"], i["y"]) for i in body["group"]["instances"]] == [
        (0.0, 0.0),
        (3000.0, 0.0),
        (0.0, 3000.0),
        (3000.0, 3000.0),
    ]
    status, project_response = _request(base, "GET", "/api/project")
    assert status == 200
    assert _valid_errors(project_response["project"]) == []


def test_add_element_to_new_empty_project(ui_server):
    base = ui_server["base"]
    status, _ = _request(base, "POST", "/api/project/new", {"id": "EMPTY", "name": "Empty"})
    assert status == 200
    status, body = _request(
        base,
        "POST",
        "/api/project/add-element",
        {"path": "BP_D1200.elem.json", "group_id": "BP-NEW", "count": 1},
    )
    assert status == 200
    assert body["group"]["type"] == "bored_pile"
    status, project_response = _request(base, "GET", "/api/project")
    assert status == 200
    assert _valid_errors(project_response["project"]) == []


def test_update_from_source_preserves_existing_overrides(ui_server):
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    status, opened = _request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    before = opened["project"]
    source = json.loads((workspace / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    source["definition"]["name"] = "Bored pile updated"
    (workspace / "BP_D1200.elem.json").write_text(json.dumps(source), encoding="utf-8")

    status, body = _request(
        base,
        "POST",
        "/api/group/BP-P1/update-from-source",
        {"path": "BP_D1200.elem.json"},
    )
    assert status == 200
    assert body["project"]["groups"][0]["definition"]["data"]["name"] == "Bored pile updated"
    after_instances = body["project"]["groups"][0]["instances"]
    before_instances = before["groups"][0]["instances"]
    for pile_id in ("P1-2", "P1-5", "P1-8"):
        old = next(i for i in before_instances if i["id"] == pile_id)
        new = next(i for i in after_instances if i["id"] == pile_id)
        assert new.get("overrides") == old.get("overrides")


def test_update_from_source_invalid_zone_cancels(ui_server):
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    status, opened = _request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    original = copy.deepcopy(opened["project"])
    target = next(
        inst
        for group in original["groups"]
        for inst in group["instances"]
        if inst["id"] == "P1-1"
    )
    target["overrides"] = {"zone_lengths": {"MISSING": 1}}
    ui_mod.CURRENT_DOC = original
    source = json.loads((workspace / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    source["definition"]["name"] = "Should not apply"
    (workspace / "BP_D1200.elem.json").write_text(json.dumps(source), encoding="utf-8")

    status, body = _request(
        base,
        "POST",
        "/api/group/BP-P1/update-from-source",
        {"path": "BP_D1200.elem.json"},
    )
    assert status == 400
    assert body["issues"]
    assert ui_mod.CURRENT_DOC == original


def test_source_diff_returns_leaf_definition_path_only(ui_server):
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    status, _ = _request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    source = json.loads((workspace / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    source["definition"]["name"] = "Different name"
    (workspace / "BP_D1200.elem.json").write_text(json.dumps(source), encoding="utf-8")

    status, body = _request(base, "GET", "/api/group/BP-P1/source-diff")
    assert status == 200
    assert "/definition/name" in body["diffs"]
    assert "/definition" not in body["diffs"]
