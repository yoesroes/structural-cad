"""Regresi: contoh di src/scad_engine/examples harus byte-identik dengan examples/."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_p1_project_examples_byte_identical():
    canonical = ROOT / "examples" / "P1.project.json"
    packaged = ROOT / "src" / "scad_engine" / "examples" / "P1.project.json"
    assert canonical.is_file()
    assert packaged.is_file()
    assert packaged.read_bytes() == canonical.read_bytes()


def test_pilecap_examples_byte_identical():
    canonical = ROOT / "examples" / "pilecap.json"
    packaged = ROOT / "src" / "scad_engine" / "examples" / "pilecap.json"
    assert canonical.is_file()
    assert packaged.is_file()
    assert packaged.read_bytes() == canonical.read_bytes()
