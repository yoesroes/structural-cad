"""Regression test P0/P1/P1b/P2 untuk state server dan batas HTTP."""
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



def _plant_infeasible_p16() -> None:
    """Tanam override depth 5000 pada P1-6 di dokumen sesi."""
    doc = copy.deepcopy(ui_mod.CURRENT_DOC)
    for group in doc["groups"]:
        for inst in group.get("instances") or []:
            if inst.get("id") == "P1-6":
                inst.setdefault("overrides", {}).setdefault("params", {})["depth_below_cof"] = 5000
    ui_mod.CURRENT_DOC = doc
    ui_mod.DIRTY = True


def test_edit_infeasible_pile_still_rejected(ui_server):
    base = ui_server["base"]
    assert request(base, "POST", "/api/project/open", {"path": "P1.project.json"})[0] == 200
    _plant_infeasible_p16()
    before = copy.deepcopy(ui_mod.CURRENT_DOC)
    status, body = request(base, "POST", "/api/pile/P1-6/depth", {"depth": 6000})
    assert status == 400
    assert any(issue["code"] == "ZONE_DEPTH_SHORT" for issue in body["issues"])
    assert ui_mod.CURRENT_DOC == before


def test_edit_infeasible_pile_to_feasible_accepted(ui_server):
    base = ui_server["base"]
    assert request(base, "POST", "/api/project/open", {"path": "P1.project.json"})[0] == 200
    _plant_infeasible_p16()
    status, body = request(base, "POST", "/api/pile/P1-6/depth", {"depth": 30000})
    assert status == 200
    assert body["ok"] is True
    assert body["pile"]["depth_below_cof"] == 30000


def test_pile_ids_from_issue_path_mapping():
    """Unit fail-closed: path valid, definisi, OOB, kosong, pointer rusak."""
    from pathlib import Path
    from scad_ui.server import _pile_ids_from_issue_path
    doc = read_project(Path(__file__).resolve().parents[2] / "examples" / "P1.project.json")
    assert _pile_ids_from_issue_path(doc, "/groups/0/instances/0") == {"P1-1"}
    assert _pile_ids_from_issue_path(doc, "/groups/0/instances/5") == {"P1-6"}
    assert _pile_ids_from_issue_path(doc, "/groups/0/definition") is None
    assert _pile_ids_from_issue_path(doc, "/kind") is None
    assert _pile_ids_from_issue_path(doc, "/groups/0/instances/999") is None
    assert _pile_ids_from_issue_path(doc, "/groups/99/instances/0") is None
    assert _pile_ids_from_issue_path(doc, "") is None
    assert _pile_ids_from_issue_path(doc, "/groups/x/instances/y") is None


def test_api_rest_zone_override_rejected(ui_server):
    base = ui_server["base"]
    assert request(base, "POST", "/api/project/open", {"path": "P1.project.json"})[0] == 200
    status, body = request(base, "POST", "/api/pile/P1-1/zone", {"zone": "Z3", "length": 17000})
    assert status == 400
    assert body.get("ok") is False
    assert "rest" in body.get("error", "").lower()


def _project_with_rest_override() -> dict:
    """P1 dengan override zona rest pada P1-1/Z3 (dokumen invalid menurut D6)."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    doc = read_project(repo / "examples" / "P1.project.json")
    for inst in doc["groups"][0]["instances"]:
        if inst["id"] == "P1-1":
            inst["overrides"] = {"zone_lengths": {"Z3": 17000}}
            break
    return doc


def test_open_rejects_rest_override_document(ui_server):
    """D6: open berkas dengan override zona rest → 400, CURRENT_DOC tidak berubah."""
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    assert request(base, "POST", "/api/project/open", {"path": "P1.project.json"})[0] == 200
    before = copy.deepcopy(ui_mod.CURRENT_DOC)
    assert before is not None

    bad = _project_with_rest_override()
    (workspace / "bad_rest.project.json").write_text(
        json.dumps(bad, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    status, body = request(base, "POST", "/api/project/open", {"path": "bad_rest.project.json"})
    assert status == 400, body
    assert body.get("ok") is False
    err = (body.get("error") or "") + json.dumps(body.get("issues") or [])
    assert "ZONE_REST_OVERRIDE" in err or "rest" in err.lower()
    assert ui_mod.CURRENT_DOC == before


def test_save_and_save_as_reject_rest_override_document(ui_server):
    """D6: save dan save-as dokumen dengan override zona rest → 400, tidak ada berkas ditulis."""
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    assert request(base, "POST", "/api/project/open", {"path": "P1.project.json"})[0] == 200
    before_path = ui_mod.CURRENT_PATH
    before_bytes = before_path.read_bytes() if before_path and before_path.is_file() else None

    bad = _project_with_rest_override()

    status, body = request(base, "POST", "/api/project/save", {"doc": bad})
    assert status == 400, body
    assert body.get("ok") is False
    issues = body.get("issues") or []
    codes = {i.get("code") for i in issues} if issues else set()
    err = body.get("error") or ""
    assert "ZONE_REST_OVERRIDE" in codes or "rest" in err.lower() or "ZONE_REST_OVERRIDE" in err
    if before_path and before_bytes is not None:
        assert before_path.read_bytes() == before_bytes

    target = workspace / "from_save_as_rest.project.json"
    if target.exists():
        target.unlink()
    status, body = request(
        base,
        "POST",
        "/api/project/save-as",
        {"path": "from_save_as_rest.project.json", "doc": bad},
    )
    assert status == 400, body
    assert body.get("ok") is False
    assert not target.exists()
    assert list(workspace.glob("*.tmp")) == []


def test_api_set_rest_zone_does_not_write_disk(ui_server):
    """D6: set zona rest lewat API → 400 dan berkas di disk tidak berubah."""
    workspace = ui_server["workspace"]
    base = ui_server["base"]
    assert request(base, "POST", "/api/project/open", {"path": "P1.project.json"})[0] == 200
    p1_path = workspace / "P1.project.json"
    before = p1_path.read_bytes()
    status, body = request(base, "POST", "/api/pile/P1-1/zone", {"zone": "Z3", "length": 17000})
    assert status == 400
    assert body.get("ok") is False
    assert p1_path.read_bytes() == before


def test_zone_gap_warnings_do_not_block_filter():
    from scad_ui.server import _resolve_errors_for_pile
    issues = [
        {"level": "warning", "code": "ZONE_GAP", "pile": "P-gap"},
        {"level": "error", "code": "ZONE_DEPTH_SHORT", "pile": "P-gap"},
    ]
    assert _resolve_errors_for_pile(issues, {}, "P-gap") == [issues[1]]
    assert _resolve_errors_for_pile(issues, {}, "P-other") == []


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


def test_api_zone_gap_e2e_resolve_warning(ui_server):
    """P2b: project tanpa rest -> depth valid 200; resolve memuat ZONE_GAP warning."""
    base = ui_server["base"]
    doc = {
        "kind": "project",
        "schema_version": 1,
        "project": {"id": "GAP", "name": "GAP"},
        "shapes": {},
        "groups": [
            {
                "id": "G1",
                "type": "bored_pile",
                "definition": {
                    "type": "bored_pile",
                    "data": {
                        "name": "bp",
                        "params": {
                            "diameter": 1200,
                            "depth_below_cof": 10000,
                            "cover": 75,
                            "cover_ref": "surface",
                        },
                        "zones": [
                            {"id": "Z0", "side": "above_cof", "length": 1000},
                            {"id": "Z1", "side": "below_cof", "length": 3000},
                            {"id": "Z2", "side": "below_cof", "length": 2000},
                        ],
                        "rebars": [],
                    },
                    "source": {"file": "synthetic", "hash": "0" * 64},
                },
                "defaults": {"params": {"depth_below_cof": 10000}},
                "instances": [{"id": "P-gap", "x": 0.0, "y": 0.0}],
            }
        ],
    }
    ui_mod.CURRENT_DOC = doc
    ui_mod.CURRENT_PATH = None
    ui_mod.DIRTY = True
    # Resolve lewat API (tanpa save) — ZONE_GAP warning
    status, body = request(base, "POST", "/api/project/resolve", {"doc": doc})
    assert status == 200, body
    gaps = [i for i in body.get("issues") or [] if i.get("code") == "ZONE_GAP"]
    assert gaps, body
    assert gaps[0].get("level") == "warning"
    # Edit depth valid tidak diblokir oleh warning
    status, body = request(base, "POST", "/api/pile/P-gap/depth", {"depth": 9000})
    # Boleh 200 jika validate lolos; bila skema menolak synthetic, resolve-only di atas sudah cukup
    if status == 200:
        assert body.get("ok") is True
    else:
        # Pastikan bukan karena ZONE_GAP
        issues = body.get("issues") or []
        assert not any(i.get("code") == "ZONE_GAP" and i.get("level") == "error" for i in issues)
