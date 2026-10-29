"""G2: files_ops + hash add-element."""
from __future__ import annotations

import json
import copy
from pathlib import Path

import pytest

from scad.files_ops import (
    add_element_to_project,
    new_project,
    new_element,
    open_document,
    resolve_under_workspace,
    save_document_at,
    source_diff,
    update_group_from_source,
)
from scad.io.canonical import sha256_of
from scad.plugins import list_plugins

REPO = Path(__file__).resolve().parents[2]


def test_path_outside_workspace_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="luar workspace"):
        resolve_under_workspace(tmp_path, "/etc/passwd")


def test_roundtrip_save_open(tmp_path: Path):
    doc = new_project("T1", "Tes")
    path = save_document_at(tmp_path, "T1.project.json", doc)
    loaded, target = open_document(tmp_path, "T1.project.json")
    assert loaded["project"]["id"] == "T1"
    assert target == path


def test_bad_extension_rejected(tmp_path: Path):
    doc = new_project("T1", "Tes")
    with pytest.raises(ValueError, match="Ekstensi"):
        save_document_at(tmp_path, "x.txt", doc)


def test_new_element_defaults_are_valid_for_all_plugins():
    from scad.validate import validate_document

    for type_id in list_plugins():
        doc = new_element(type_id)
        errors = [i for i in validate_document(doc) if i.level == "error"]
        assert errors == [], (type_id, errors)


def test_new_element_rejects_invalid_params():
    with pytest.raises(ValueError, match="Elemen baru tidak valid"):
        new_element("bored_pile", params={"diameter": -1})


def test_save_invalid_document_does_not_create_or_overwrite(tmp_path: Path):
    invalid = {"kind": "project", "schema_version": 1}
    with pytest.raises(ValueError, match="Validasi gagal"):
        save_document_at(tmp_path, "invalid.project.json", invalid)
    assert not (tmp_path / "invalid.project.json").exists()

    existing = tmp_path / "existing.project.json"
    original = '{"kind":"project","schema_version":1,"sentinel":true}\n'
    existing.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="Validasi gagal"):
        save_document_at(tmp_path, existing.name, invalid)
    assert existing.read_text(encoding="utf-8") == original


def test_add_element_hash_matches_p1():
    p1 = json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))
    expected = p1["groups"][0]["definition"]["source"]["hash"]
    elem = json.loads((REPO / "examples" / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    proj = new_project("X", "X")
    out = add_element_to_project(
        proj,
        element_doc=elem,
        source_file_label="BP_D1200.elem.json",
        group_id="BP-X",
        count=1,
        naming={"pattern": "P1-{n}", "start": 1},
        layout={"cols": 1, "dx": 0, "dy": 0},
    )
    assert out["groups"][0]["definition"]["source"]["hash"] == expected
    assert out["groups"][0]["definition"]["source"]["hash"] == sha256_of(elem["definition"])


def test_update_preserves_overrides_and_blocks_invalid_zone(tmp_path: Path):
    elem = json.loads((REPO / "examples" / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    proj = new_project("X", "X")
    proj = add_element_to_project(
        proj,
        element_doc=elem,
        source_file_label="BP_D1200.elem.json",
        group_id="BP-X",
        count=3,
        naming={"pattern": "P1-{n}", "start": 1},
    )
    # set overrides like P1-2 depth and P1-3 bad zone
    for inst in proj["groups"][0]["instances"]:
        if inst["id"] == "P1-2":
            inst["overrides"] = {"params": {"depth_below_cof": 26000}}
        if inst["id"] == "P1-3":
            inst["overrides"] = {"zone_lengths": {"ZGONE": 100}}

    # valid update: same elem, but P1-3 has invalid zone -> cancel
    _, issues = update_group_from_source(proj, "BP-X", elem)
    assert issues
    assert any(i["code"] == "OVERRIDE_ZONE_MISSING" for i in issues)

    # remove bad override; update should succeed and keep P1-2
    for inst in proj["groups"][0]["instances"]:
        if inst["id"] == "P1-3":
            inst.pop("overrides", None)
    new_proj, issues = update_group_from_source(proj, "BP-X", elem)
    assert issues == []
    inst2 = next(i for i in new_proj["groups"][0]["instances"] if i["id"] == "P1-2")
    assert inst2["overrides"]["params"]["depth_below_cof"] == 26000


def test_new_project_and_add_validate():
    from scad.validate import validate_document
    elem = json.loads((REPO / "examples" / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    proj = new_project("X", "X")
    errors = [i for i in validate_document(proj) if i.level == "error"]
    assert errors == [], errors
    out = add_element_to_project(
        proj,
        element_doc=elem,
        source_file_label="BP_D1200.elem.json",
        group_id="BP-X",
        count=2,
        naming={"pattern": "P1-{n}", "start": 1},
    )
    assert out["groups"][0]["type"] == "bored_pile"
    errors = [i for i in validate_document(out) if i.level == "error"]
    assert errors == [], [e.message for e in errors]


def test_add_invalid_element_rejected_without_project_change():
    project = new_project("X", "X")
    original = json.loads(json.dumps(project))
    invalid = {"kind": "element", "schema_version": 1, "definition": {}}
    with pytest.raises(ValueError, match="Definisi elemen tidak valid"):
        add_element_to_project(
            project,
            element_doc=invalid,
            group_id="BAD",
            count=1,
        )
    assert project == original


def test_source_diff_detects_shape_change():
    elem = json.loads((REPO / "examples" / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    proj = new_project("X", "X")
    proj = add_element_to_project(
        proj,
        element_doc=elem,
        source_file_label="BP_D1200.elem.json",
        group_id="BP-X",
        count=1,
    )
    # ubah shape di elemen sumber saja
    elem2 = json.loads(json.dumps(elem))
    if "R20" in elem2.get("shapes", {}):
        elem2["shapes"]["R20"] = dict(elem2["shapes"]["R20"])
        elem2["shapes"]["R20"]["builder"] = dict(elem2["shapes"]["R20"].get("builder") or {})
        elem2["shapes"]["R20"]["builder"]["length"] = "=A+1"
    diffs = source_diff(proj["groups"][0], elem2, project_shapes=proj.get("shapes"))
    assert any(d.startswith("/shapes/") for d in diffs) or diffs  # at least some diff if shapes differ


def test_source_diff_and_update_detect_shape_deletion_preserving_local_shape():
    elem = json.loads((REPO / "examples" / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    proj = add_element_to_project(
        new_project("X", "X"),
        element_doc=elem,
        source_file_label="BP_D1200.elem.json",
        group_id="BP-X",
        count=1,
    )
    local_shape = copy.deepcopy(proj["shapes"]["RING"])
    proj["shapes"]["LOCAL"] = local_shape

    elem2 = json.loads(json.dumps(elem))
    elem2["shapes"].pop("R20")
    elem2["definition"]["rebars"] = [
        r for r in elem2["definition"]["rebars"] if r["shape"]["code"] != "R20"
    ]

    diffs = source_diff(proj["groups"][0], elem2, project_shapes=proj["shapes"])
    assert "/shapes/R20" in diffs

    updated, issues = update_group_from_source(proj, "BP-X", elem2)
    assert issues == []
    assert "R20" not in updated["shapes"]
    assert updated["shapes"]["LOCAL"] == local_shape
    assert "R87" in updated["shapes"]
