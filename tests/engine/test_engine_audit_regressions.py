"""Tes merah P0/P1b untuk temuan engine yang belum diperbaiki."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scad.validate import validate_document
from scad_engine.from_v1 import build_bar_groups, recap_group


REPO = Path(__file__).resolve().parents[2]


def load_p1() -> dict:
    return json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))


def rebar(doc: dict, rid: str) -> dict:
    return next(
        item
        for item in doc["groups"][0]["definition"]["data"]["rebars"]
        if item["id"] == rid
    )


def test_polar_spacing_rejected_with_arr_bad_and_build_raises():
    """D2: polar by spacing harus ditolak (ARR_BAD), bukan menghilangkan batang.

    validate_document wajib memunculkan ARR_BAD; build_bar_groups wajib ValueError.
    """
    doc = load_p1()
    rebar(doc, "B1")["arrangement"] = {
        "mode": "group",
        "pattern": "polar",
        "by": "spacing",
        "spacing": 110,
    }
    issues = validate_document(doc)
    assert any(
        getattr(issue, "code", None) == "ARR_BAD" and issue.level == "error"
        for issue in issues
    )
    with pytest.raises(ValueError):
        build_bar_groups(doc, "P1-1")


def test_polar_start_angle_deg_changes_first_origin():
    baseline = build_bar_groups(load_p1(), "P1-1")
    shifted_doc = load_p1()
    rebar(shifted_doc, "B1")["arrangement"]["start_angle_deg"] = 45
    shifted = build_bar_groups(shifted_doc, "P1-1")
    baseline_origin = next(g for g in baseline if g.mark == "B1").instances[0].origin
    shifted_origin = next(g for g in shifted if g.mark == "B1").instances[0].origin
    assert shifted_origin != baseline_origin


def test_group_totals_each_row_obey_count_times_cut_length():
    """T4: setiap baris totals memenuhi count * cut_length_mm == total_length_mm."""
    result = recap_group(load_p1(), "BP-P1")
    for row in result["totals"]:
        assert abs(
            float(row["count"]) * float(row["cut_length_mm"])
            - float(row["total_length_mm"])
        ) <= 1e-3


def test_group_totals_b4_split_by_cut_length_and_weight_parity():
    """T4: B4 muncul beberapa baris (panjang beda); berat total ≈ 76878.6 kg."""
    result = recap_group(load_p1(), "BP-P1")
    b4_rows = [r for r in result["totals"] if r.get("mark") == "B4" or r["id"] == "B4"]
    cuts = sorted({round(float(r["cut_length_mm"]), 3) for r in b4_rows}, reverse=True)
    assert 20280.0 in cuts
    assert 16280.0 in cuts
    assert len(b4_rows) >= 2
    total_weight = sum(float(r["weight_kg"]) for r in result["totals"])
    assert abs(total_weight - 76878.6) <= 0.1
    # jumlah count per mark == jumlah count per pile
    from collections import Counter
    mark_from_totals: Counter[str] = Counter()
    for r in result["totals"]:
        mark_from_totals[str(r.get("mark") or r["id"])] += int(r["count"])
    mark_from_piles: Counter[str] = Counter()
    weight_from_piles = 0.0
    for pile in result["piles"]:
        for row in pile["rows"]:
            mark_from_piles[str(row.get("mark") or row["id"])] += int(row["count"])
            weight_from_piles += float(row["weight_kg"])
    assert mark_from_totals == mark_from_piles
    assert abs(total_weight - weight_from_piles) <= 0.15
