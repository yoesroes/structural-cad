"""Uji wajib T02 — canonical_json, sha256_of, load/save document."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Paket scad berada di core/

REPO_ROOT = Path(__file__).resolve().parents[2]

from scad.io.canonical import canonical_json, sha256_of  # noqa: E402
from scad.io.files import (  # noqa: E402
    SCHEMA_VERSION,
    SchemaVersionError,
    load_document,
    save_document,
)

EXAMPLES = REPO_ROOT / "examples"
EXPECTED_HASH = (
    "sha256:4c03bb2a8ccd0debe518496c2f1c3669c3b2422f75ea7be05f12df015559c673"
)


def test_sha256_definition_matches_example_and_project():
    elem = json.loads((EXAMPLES / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    definition = elem["definition"]
    h = sha256_of(definition)
    assert h == EXPECTED_HASH

    project = json.loads((EXAMPLES / "P1.project.json").read_text(encoding="utf-8"))
    assert project["groups"][0]["definition"]["source"]["hash"] == h


def test_hash_stable_under_key_reordering():
    elem = json.loads((EXAMPLES / "BP_D1200.elem.json").read_text(encoding="utf-8"))
    definition = elem["definition"]
    # Acak urutan kunci tingkat atas
    reordered = {k: definition[k] for k in reversed(list(definition.keys()))}
    assert sha256_of(reordered) == sha256_of(definition) == EXPECTED_HASH


def test_canonical_float_to_int():
    assert '"n":1200' in canonical_json({"n": 1200.0})
    assert sha256_of({"n": 1200.0}) == sha256_of({"n": 1200})


def test_load_save_load_roundtrip(tmp_path: Path):
    src = EXAMPLES / "P1.project.json"
    doc = load_document(src)
    out = tmp_path / "P1.copy.project.json"
    save_document(out, doc)
    again = load_document(out)
    assert again == doc


def test_save_creates_bak_on_second_write(tmp_path: Path):
    doc = load_document(EXAMPLES / "BP_D1200.elem.json")
    out = tmp_path / "elem.json"
    save_document(out, doc)
    assert out.exists()
    assert not (tmp_path / "elem.json.bak").exists()

    doc2 = dict(doc)
    doc2["meta"] = {"note": "kedua"}
    save_document(out, doc2)
    bak = tmp_path / "elem.json.bak"
    assert bak.exists()
    # .bak berisi versi pertama
    assert json.loads(bak.read_text(encoding="utf-8")) == doc
    assert load_document(out) == doc2


def test_failed_replace_preserves_old_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    doc = load_document(EXAMPLES / "BP_D1200.elem.json")
    out = tmp_path / "elem.json"
    save_document(out, doc)
    original = out.read_text(encoding="utf-8")

    def boom(src, dst):
        raise OSError("simulasi gagal os.replace")

    monkeypatch.setattr(os, "replace", boom)

    doc2 = dict(doc)
    doc2["meta"] = {"x": 1}
    with pytest.raises(OSError):
        save_document(out, doc2)

    assert out.read_text(encoding="utf-8") == original
    # Tidak boleh ada sisa .tmp
    tmps = list(tmp_path.glob("*.tmp"))
    assert tmps == []


def test_schema_version_too_new():
    doc = {
        "kind": "project",
        "schema_version": SCHEMA_VERSION + 1,
        "project": {"id": "X", "name": "X", "datum": {"cof_elevation": 0}},
        "settings": {"cover_ref": "surface"},
        "materials": {
            "concrete": {"grade": "fc30", "type": "readymix"},
            "steel": {"grade": "fy420", "type": "ulir"},
        },
        "shapes": {},
        "groups": [],
    }
    import tempfile
    from pathlib import Path as P

    with tempfile.TemporaryDirectory() as td:
        path = P(td) / "future.project.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(SchemaVersionError):
            load_document(path)


def test_load_rejects_bad_kind(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps({"kind": "unknown", "schema_version": 1}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="kind"):
        load_document(path)


def test_schema_version_old_without_migration(tmp_path: Path):
    doc = {
        "kind": "project",
        "schema_version": 0,
    }
    path = tmp_path / "old.project.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(SchemaVersionError, match="tidak ada migrasi"):
        load_document(path)


def test_schema_version_current_is_accepted(tmp_path: Path):
    from scad.files_ops import new_project

    doc = new_project("CURRENT", "Current")
    assert doc["schema_version"] == SCHEMA_VERSION
    path = tmp_path / "current.project.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    assert load_document(path) == doc
