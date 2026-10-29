"""G1/H5: angka acuan P1.project.json (sengkang H5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scad_engine.from_v1 import build_bar_groups, recap_group, recap_pile
from scad_engine.clash import find_clashes

REPO = Path(__file__).resolve().parents[2]
DOC = json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))
TOL = 0.5


def _row(recap, rid):
    return next(r for r in recap["rows"] if r["id"] == rid)


def test_p1_1_counts_and_lengths_h5():
    r = recap_pile(DOC, "P1-1")
    assert _row(r, "B1")["count"] == 56
    assert abs(_row(r, "B1")["length_mm"] - 12280) <= TOL
    # Spiral menerus B2
    assert _row(r, "B2")["count"] == 1
    assert abs(_row(r, "B2")["length_mm"] - 466761.1) <= TOL
    assert _row(r, "B4")["count"] == 28
    assert abs(_row(r, "B4")["length_mm"] - 20280) <= TOL
    # Cincin Z0
    assert _row(r, "B5")["count"] == 17
    assert abs(_row(r, "B5")["length_mm"] - 3888.4) <= TOL
    codes = {i["code"] for i in r["issues"]}
    assert "RULE_SPACING" in codes
    assert "LEN_MISMATCH" not in codes
    assert "CLASH" not in codes


def test_p1_2_spiral_and_b4_shorter():
    r = recap_pile(DOC, "P1-2")
    assert _row(r, "B2")["count"] == 1
    assert abs(_row(r, "B2")["length_mm"] - 423264.7) <= TOL
    assert _row(r, "B4")["count"] == 28
    assert abs(_row(r, "B4")["length_mm"] - 16280) <= TOL


def test_p1_8_b1_and_spiral_with_z2_override():
    r = recap_pile(DOC, "P1-8")
    assert _row(r, "B1")["count"] == 56
    assert abs(_row(r, "B1")["length_mm"] - 11280) <= TOL
    # Z2 override 7000 → 35 putaran @200 = 113909.5 (H5)
    # depth 26000 → Z3 = 16000 (bukan 19000); total spiral ≈ 417866
    assert abs(_row(r, "B2")["length_mm"] - 417866.0) <= 1.0
    # komponen Z2 (via selisih terhadap pitch tetap) tidak diurai di rekap;
    # pastikan lebih pendek dari P1-1 (466761) karena Z2 lebih pendek
    assert _row(r, "B2")["length_mm"] < 466761.1 - 1000


def test_recap_group_nine_piles():
    rg = recap_group(DOC, "BP-P1")
    assert len(rg["piles"]) == 9
    b1 = next(t for t in rg["totals"] if t["id"] == "B1")
    assert b1["count"] == 56 * 9


def test_build_bar_groups_total_instances():
    groups = build_bar_groups(DOC, "P1-1")
    total = sum(g.count for g in groups)
    # B1 56 + B2 1 + B4 28 + B5 17
    assert total == 56 + 1 + 28 + 17


def test_recap_has_cut_geometry_total_and_weight_fields():
    r = recap_pile(DOC, "P1-1")
    b2 = _row(r, "B2")
    assert abs(b2["cut_length_mm"] - 466761.1) <= TOL
    assert abs(b2["geometry_length_mm"] - b2["cut_length_mm"]) <= max(
        1.0, b2["cut_length_mm"] * 0.002
    )
    for row in r["rows"]:
        assert row["mark"] == row["id"]
        assert row["total_length_m"] == pytest.approx(
            row["total_length_mm"] / 1000.0, abs=0.001
        )
        assert row["weight_kg"] == pytest.approx(
            row["total_length_m"] * row["diameter"] ** 2 / 162.2, abs=0.002
        )


def test_clash_reports_real_pair_count_for_deliberate_b4_overlap():
    import copy

    doc = copy.deepcopy(DOC)
    definition = doc["groups"][0]["definition"]["data"]
    b4 = next(item for item in definition["rebars"] if item["id"] == "B4")
    b4["position"]["offset"] = "=cover+16"
    result = recap_pile(doc, "P1-1")
    clash = next(issue for issue in result["issues"] if issue["code"] == "CLASH")
    assert clash["total_bar_pairs"] == 56
    assert clash["by_mark_pair"]["B1-B4"]["bar_pairs"] == 56


def test_raw_clashes_p1_1_zero_pairs():
    groups = build_bar_groups(DOC, "P1-1")
    raw = find_clashes(groups)
    assert raw["total_bar_pairs"] == 0
    recap = recap_pile(DOC, "P1-1")
    assert not any(issue["code"] == "CLASH" for issue in recap["issues"])
    assert "RULE_SPACING" in {issue["code"] for issue in recap["issues"]}


def test_clash_checker_failure_is_reported(monkeypatch):
    import scad_engine.from_v1 as module

    def fail(_groups):
        raise RuntimeError("uji gagal")

    monkeypatch.setattr(module, "find_clashes", fail)
    result = module.recap_pile(DOC, "P1-1")
    assert any(i["code"] == "CLASH_CHECK_FAILED" for i in result["issues"])
