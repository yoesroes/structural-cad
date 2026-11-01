"""Tes P4: ketepatan engine (spiral extend, cover_ref, nilai nol, paritas P5,
radius tekuk, spasi bersih) + regresi PC_8400 dan P1."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scad.placement import place_rebar
from scad.shapes import helix_cut_length_segment
from scad.validate import validate_document
from scad_engine.from_v1 import (
    _build_env,
    _min_clear_spacing,
    build_bar_groups,
    recap_pile,
)
from scad_engine.layout import build_groups
from scad_engine.model import BarGroup, BarProto, Instance

REPO = Path(__file__).resolve().parents[2]
_DEL = object()  # penanda: hapus kunci dari params


def load(name: str) -> dict:
    return json.loads((REPO / "examples" / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- bored pile
def helix_result(extent_patch: dict):
    doc = load("P1.project.json")
    rebar = doc["groups"][0]["definition"]["data"]["rebars"][1]  # B2 spiral by_zone
    assert rebar["id"] == "B2"
    rebar["extent"].update(extent_patch)
    env = _build_env(doc, doc["groups"][0], doc["groups"][0]["instances"][0])
    placed = place_rebar(rebar, env)[0]
    zs = [placed.origin[2] + p[2] for p in placed.centerline.points]
    return max(zs), min(zs), placed.cut_length, doc


def test_helix_by_zone_baseline_unchanged():
    top, bottom, cut, _ = helix_result({})
    assert top == pytest.approx(0.0, abs=0.5)
    assert bottom == pytest.approx(-30000.0, abs=0.5)
    assert cut == pytest.approx(466761.135, abs=0.01)


def test_helix_extend_start_lengthens_top_segment_only():
    _, _, cut0, _ = helix_result({})
    top, bottom, cut, _ = helix_result({"extend_start": 500})
    assert top == pytest.approx(500.0, abs=0.5)
    assert bottom == pytest.approx(-30000.0, abs=0.5)  # dasar TIDAK bergeser
    # perpanjangan atas memakai pitch zona teratas (Z1 = 75)
    assert cut - cut0 == pytest.approx(helix_cut_length_segment(1050.0, 16.0, 500.0, 75.0), abs=0.01)


def test_helix_extend_end_lengthens_bottom_segment():
    _, _, cut0, _ = helix_result({})
    top, bottom, cut, _ = helix_result({"extend_end": 500})
    assert top == pytest.approx(0.0, abs=0.5)
    assert bottom == pytest.approx(-30500.0, abs=0.5)
    # perpanjangan bawah memakai pitch zona terbawah (Z3 = 300)
    assert cut - cut0 == pytest.approx(helix_cut_length_segment(1050.0, 16.0, 500.0, 300.0), abs=0.01)


def test_helix_negative_extend_end_shortens():
    _, _, cut0, _ = helix_result({})
    _, bottom, cut, _ = helix_result({"extend_end": -500})
    assert bottom == pytest.approx(-29500.0, abs=0.5)
    assert cut0 - cut == pytest.approx(helix_cut_length_segment(1050.0, 16.0, 500.0, 300.0), abs=0.01)


def test_helix_shortening_beyond_segment_raises():
    with pytest.raises(ValueError, match="memendekkan spiral"):
        helix_result({"extend_start": -3001})  # zona Z1 hanya 3000 mm


def test_helix_extend_keeps_geometry_consistent_with_cut_length():
    _, _, _, doc = helix_result({"extend_start": 500, "extend_end": 300})
    issues = recap_pile(doc, "P1-1")["issues"]
    assert not [i for i in issues if i["code"] == "LEN_MISMATCH"]


def test_p1_recap_unchanged_by_p4():
    rows = {r["id"]: r for r in recap_pile(load("P1.project.json"), "P1-1")["rows"]}
    assert (rows["B1"]["count"], rows["B1"]["length_mm"]) == (56, 12280.0)
    assert rows["B2"]["length_mm"] == pytest.approx(466761.135, abs=0.01)
    assert (rows["B4"]["count"], rows["B4"]["length_mm"]) == (28, 20280.0)
    assert (rows["B5"]["count"], rows["B5"]["length_mm"]) == (17, pytest.approx(3888.407, abs=0.01))
    issues = recap_pile(load("P1.project.json"), "P1-1")["issues"]
    spacing = [i for i in issues if i["code"] == "RULE_SPACING"]
    assert len(spacing) == 1 and "46.6" in spacing[0]["message"]


# --------------------------------------------------------------------------- pile cap
def pilecap_project(params_patch=None, p5_patch=None, settings=None) -> dict:
    definition = copy.deepcopy(load("PC_8400.elem.json")["definition"])
    for key, value in (params_patch or {}).items():
        if value is _DEL:
            definition["params"].pop(key, None)
        else:
            definition["params"][key] = value
    for rebar in definition["rebars"]:
        if rebar["id"] == "P5" and p5_patch:
            rebar.setdefault("shape_params", {}).update(p5_patch)
    doc = {
        "kind": "project",
        "schema_version": 1,
        "groups": [
            {
                "id": "G",
                "type": "pile_cap",
                "definition": {"data": definition},
                "instances": [{"id": "C1", "x": 0, "y": 0}],
            }
        ],
    }
    if settings is not None:
        doc["settings"] = settings
    return doc


def mark_group(doc: dict, mark: str) -> BarGroup:
    return next(g for g in build_bar_groups(doc, "C1") if g.mark == mark)


def p3_top_z(doc: dict) -> float:
    return mark_group(doc, "P3").protos["P3"].points[1][2]


def test_pilecap_regression_matches_classic_engine():
    def summary(groups):
        return {
            g.mark: (len(g.instances), round(sum(g.protos[i.proto].path_length() for i in g.instances), 1))
            for g in groups
        }

    new = summary(build_bar_groups(pilecap_project(), "C1"))
    old = summary(build_groups(load("pilecap.json")))
    assert new == old
    assert sum(v[0] for v in new.values()) == 533


def test_cover_ref_default_is_surface_like_plugin_and_project():
    default = p3_top_z(pilecap_project({"cover_ref": _DEL}))
    surface = p3_top_z(pilecap_project({"cover_ref": "surface"}))
    centerline = p3_top_z(pilecap_project({"cover_ref": "centerline"}))
    assert default == surface
    assert centerline - surface == pytest.approx(9.5, abs=1e-6)  # d/2 untuk D19


def test_cover_ref_falls_back_to_project_settings_then_param_wins():
    only_settings = p3_top_z(pilecap_project({"cover_ref": _DEL}, settings={"cover_ref": "centerline"}))
    assert only_settings == p3_top_z(pilecap_project({"cover_ref": "centerline"}))
    param_wins = p3_top_z(pilecap_project({"cover_ref": "surface"}, settings={"cover_ref": "centerline"}))
    assert param_wins == p3_top_z(pilecap_project({"cover_ref": "surface"}))


def test_unknown_cover_ref_raises():
    with pytest.raises(ValueError, match="cover_ref"):
        build_bar_groups(pilecap_project({"cover_ref": "tengah"}), "C1")


def test_lap_mid_height_zero_is_not_silently_replaced():
    # 0 adalah nilai sah: kaki lewatan keluar beton -> error, BUKAN diganti H/2 diam-diam.
    with pytest.raises(ValueError):
        build_bar_groups(pilecap_project({"lap_mid_height": 0}), "C1")


def test_lap_mid_height_explicit_equals_default_half_height():
    omitted = mark_group(pilecap_project({"lap_mid_height": _DEL}), "P1").protos["P1"].points
    explicit = mark_group(pilecap_project({"lap_mid_height": 1250}), "P1").protos["P1"].points
    assert omitted == explicit


def test_lap_ratio_zero_raises():
    with pytest.raises(ValueError, match="lap_ratio_D"):
        build_bar_groups(pilecap_project({"lap_ratio_D": 0}), "C1")


@pytest.mark.parametrize("inset", [600, 300, 450])
def test_p5_hook_direction_alternates_along_x_and_y(inset):
    group = mark_group(pilecap_project(p5_patch={"inset": inset}), "P5")
    by_xy = {(round(i.origin[0], 3), round(i.origin[1], 3)): i.proto for i in group.instances}
    xs = sorted({x for x, _ in by_xy})
    ys = sorted({y for _, y in by_xy})
    for y in ys:
        for a, b in zip(xs, xs[1:]):
            assert by_xy[(a, y)] != by_xy[(b, y)]
    for x in xs:
        for a, b in zip(ys, ys[1:]):
            assert by_xy[(x, a)] != by_xy[(x, b)]


def test_bend_radius_default_equals_previous_constant_for_d19():
    proto = mark_group(pilecap_project(), "P1").protos["P1"]
    assert proto.bend_radius == pytest.approx(38.0 + 9.5)


def test_bend_inside_radius_db_scales_with_diameter_and_validates():
    proto = mark_group(pilecap_project({"bend_inside_radius_db": 3}), "P1").protos["P1"]
    assert proto.bend_radius == pytest.approx((3 + 0.5) * 19.0)
    element = load("PC_8400.elem.json")
    element["definition"]["params"]["bend_inside_radius_db"] = 3
    assert not [i for i in validate_document(element) if i.level == "error"]
    element["definition"]["params"]["bend_inside_radius_db"] = 0
    assert [i for i in validate_document(element) if i.level == "error"]
    with pytest.raises(ValueError, match="bend_inside_radius_db"):
        build_bar_groups(pilecap_project({"bend_inside_radius_db": 0}), "C1")


# --------------------------------------------------------------------------- spasi bersih
def spacing_group(origins, d=20.0, mark="M"):
    protos = {mark: BarProto(mark, mark, d, ((0.0, 0.0, 0.0), (0.0, 0.0, 100.0)))}
    return BarGroup(mark, d, "uji", protos, [Instance(mark, o) for o in origins])


def test_min_clear_spacing_reports_near_overlap_that_old_rule_skipped():
    # jarak pusat 1,2d = 24 mm -> jarak bersih 4 mm (dulu dilewati karena < 1,5d)
    assert _min_clear_spacing([spacing_group([(0, 0, 0), (24.0, 0, 0)])]) == pytest.approx(4.0)


def test_min_clear_spacing_reports_overlapping_bars_as_negative():
    assert _min_clear_spacing([spacing_group([(0, 0, 0), (12.0, 0, 0)])]) == pytest.approx(-8.0)


def test_min_clear_spacing_ignores_touching_bundle_pair():
    assert _min_clear_spacing([spacing_group([(0, 0, 0), (20.0, 0, 0), (120.0, 0, 0)])]) == pytest.approx(80.0)


def test_min_clear_spacing_ignores_bars_stacked_in_z():
    # cincin/spiral: origin xy sama, z berbeda -> bukan pelanggaran spasi
    assert _min_clear_spacing([spacing_group([(0, 0, 0), (0, 0, 75.0), (0, 0, 150.0)])]) is None
