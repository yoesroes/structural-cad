"""Tes merah P0 untuk temuan engine yang belum diperbaiki."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

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


@pytest.mark.xfail(strict=True, reason="T3")
def test_polar_spacing_is_rejected_instead_of_dropping_bars():
    doc = load_p1()
    rebar(doc, "B1")["arrangement"] = {
        "mode": "group",
        "pattern": "polar",
        "by": "spacing",
        "spacing": 110,
    }
    groups = build_bar_groups(doc, "P1-1")
    assert any(group.mark == "B1" for group in groups)


@pytest.mark.xfail(strict=True, reason="T3")
def test_polar_start_angle_deg_changes_first_origin():
    baseline = build_bar_groups(load_p1(), "P1-1")
    shifted_doc = load_p1()
    rebar(shifted_doc, "B1")["arrangement"]["start_angle_deg"] = 45
    shifted = build_bar_groups(shifted_doc, "P1-1")
    baseline_origin = next(g for g in baseline if g.mark == "B1").instances[0].origin
    shifted_origin = next(g for g in shifted if g.mark == "B1").instances[0].origin
    assert shifted_origin != baseline_origin


@pytest.mark.xfail(strict=True, reason="T4")
def test_group_totals_each_row_obey_count_times_cut_length():
    result = recap_group(load_p1(), "BP-P1")
    for row in result["totals"]:
        assert abs(
            float(row["count"]) * float(row["cut_length_mm"])
            - float(row["total_length_mm"])
        ) <= 1e-3
