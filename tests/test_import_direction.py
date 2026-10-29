"""Pastikan arah impor: scad_ui -> scad_engine -> scad (tidak sebaliknya)."""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

FORBIDDEN = {
    "scad": {"scad_engine", "scad_ui", "pilecap_rebar"},
    "scad_engine": {"scad_ui"},
}


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_no_forbidden_import_direction():
    violations = []
    for pkg, banned in FORBIDDEN.items():
        root = SRC / pkg
        if not root.is_dir():
            continue
        for py in root.rglob("*.py"):
            if py.name == "__init__.py" and pkg == "pilecap_rebar":
                continue
            mods = _imports_of(py)
            bad = mods & banned
            if bad:
                violations.append(f"{py.relative_to(SRC)}: {sorted(bad)}")
    assert not violations, "Impor terbalik:\n" + "\n".join(violations)
