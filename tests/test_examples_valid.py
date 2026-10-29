"""Semua contoh root harus berupa dokumen v1 yang valid atau pengecualian eksplisit."""
from __future__ import annotations

import json
from pathlib import Path

from scad.validate import validate_document

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

# Fixture non-dokumen v1 (bukan kind: project/element).
ALLOWLIST_NON_DOCUMENT = {
    "expected_zones.P1.json",
    "ops_golden.json",
    "pilecap.json",
}


def test_legacy_generic_example_is_outside_v1_examples():
    assert not (EXAMPLES / "generic_single_bar.json").exists()
    assert (EXAMPLES / "legacy" / "generic_single_bar.json").is_file()


def test_root_examples_are_v1_documents_or_explicit_fixtures():
    files = sorted(EXAMPLES.glob("*.json"))
    assert files
    seen = set()
    for path in files:
        seen.add(path.name)
        document = json.loads(path.read_text(encoding="utf-8"))
        if path.name in ALLOWLIST_NON_DOCUMENT:
            assert "kind" not in document, path.name
            continue
        assert "kind" in document, f"{path.name} bukan dokumen v1; pindahkan ke daftar-izin"
        issues = validate_document(document)
        errors = [issue for issue in issues if issue.level == "error"]
        assert not errors, "\n".join(
            f"{issue.code} {issue.path}: {issue.message}" for issue in errors
        )
    assert ALLOWLIST_NON_DOCUMENT <= seen
    assert "PC_8400.elem.json" in seen
