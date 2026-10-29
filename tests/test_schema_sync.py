"""Regresi agar skema root dan skema yang dipaketkan selalu identik."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_schema_copies_are_byte_identical():
    canonical = ROOT / "schemas" / "scad.schema.json"
    packaged = ROOT / "src" / "scad" / "data" / "scad.schema.json"
    assert canonical.is_file()
    assert packaged.is_file()
    assert packaged.read_bytes() == canonical.read_bytes()
