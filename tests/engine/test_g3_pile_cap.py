"""H3: pile cap v1 vs mesin lama (emas di tes saja)."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from scad.validate import validate_document
from scad_engine.from_v1 import build_bar_groups, recap_group, recap_pile
from scad_engine.layout import build_groups
from scad_engine.clash import find_clashes
from scad_engine.recap import build_recap

REPO = Path(__file__).resolve().parents[2]
TOL_L = 0.1
TOL_KG = 0.5


def _legacy(nesting: str | None = None):
    cfg = json.loads((REPO / "examples" / "pilecap.json").read_text(encoding="utf-8"))
    if nesting:
        cfg = json.loads(json.dumps(cfg))
        cfg["reinforcement"]["lap_splice"]["nesting"] = nesting
    return build_groups(cfg)


def _v1_doc(nesting: str | None = None):
    elem = json.loads((REPO / "examples" / "PC_8400.elem.json").read_text(encoding="utf-8"))
    data = json.loads(json.dumps(elem["definition"]))
    if nesting:
        data.setdefault("params", {})["lap_nesting"] = nesting
    return {
        "kind": "project",
        "schema_version": 1,
        "project": {"id": "PC", "name": "PC", "datum": {"cof_elevation": 0}},
        "settings": {"cover_ref": "surface"},
        "shapes": elem.get("shapes") or {},
        "groups": [
            {
                "id": "PC-1",
                "type": "pile_cap",
                "definition": {"data": data},
                "defaults": {},
                "instances": [{"id": "PC-1-1", "x": 0, "y": 0}],
            }
        ],
    }


def test_pc_8400_validates():
    elem = json.loads((REPO / "examples" / "PC_8400.elem.json").read_text(encoding="utf-8"))
    errors = [i for i in validate_document(elem) if i.level == "error"]
    assert errors == [], [e.message for e in errors]


def test_from_v1_does_not_import_build_groups():
    src = (REPO / "src" / "scad_engine" / "from_v1.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                assert alias.name != "build_groups", "from_v1 tidak boleh mengimpor build_groups"
        if isinstance(node, ast.Attribute) and node.attr == "build_groups":
            raise AssertionError("from_v1 tidak boleh memanggil layout.build_groups")


def test_counts_match_legacy():
    legacy = {g.mark: g.count for g in _legacy()}
    v1 = {g.mark: g.count for g in build_bar_groups(_v1_doc(), "PC-1-1")}
    for m in ("P1", "P2", "P3", "P4", "P5"):
        assert v1[m] == legacy[m], (m, v1[m], legacy[m])
    assert sum(v1.values()) == 533


def test_lengths_match_legacy():
    v1_groups = build_bar_groups(_v1_doc(), "PC-1-1")
    by_mark = {g.mark: list(g.protos.values())[0].path_length() for g in v1_groups}
    assert abs(by_mark["P1"] - 11181.2) <= TOL_L
    assert abs(by_mark["P3"] - 11181.2) <= TOL_L
    assert abs(by_mark["P2"] - 10843.2) <= TOL_L
    assert abs(by_mark["P4"] - 10843.2) <= TOL_L
    assert abs(by_mark["P5"] - 2444.5) <= TOL_L
    p6 = next(g for g in v1_groups if g.mark == "P6")
    lengths = sorted({round(pr.path_length(), 1) for pr in p6.protos.values()})
    assert any(abs(L - 8405.7) <= TOL_L for L in lengths)
    assert any(abs(L - 8443.7) <= TOL_L for L in lengths)


def test_recap_and_clash_default():
    groups = build_bar_groups(_v1_doc(), "PC-1-1")
    rows = build_recap(groups)
    total_m = sum(r["total_length_m"] for r in rows)
    total_kg = sum(r["weight_kg"] for r in rows)
    assert abs(total_m - 4338.76) <= 0.05
    assert abs(total_kg - 9214.7) <= TOL_KG
    cl = find_clashes(groups)
    assert cl.get("total_bar_pairs", 0) == find_clashes(_legacy()).get("total_bar_pairs", 0)


def test_bottom_inside_166_pairs():
    groups = build_bar_groups(_v1_doc(nesting="bottom_inside"), "PC-1-1")
    cl = find_clashes(groups)
    assert cl["total_bar_pairs"] == 166


# --- S2 / H3-04: jalur rekap yang dipakai UI (recap_pile / recap_group) ---


def _counts_from_recap_rows(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        m = r["mark"]
        out[m] = out.get(m, 0) + int(r["count"])
    return out


def test_recap_pile_pc_8400_no_depth_below_cof():
    """Jalur recap_pile harus memakai builder H3, bukan PileEnv (depth_below_cof)."""
    doc = _v1_doc()
    result = recap_pile(doc, "PC-1-1")
    assert result["pile_id"] == "PC-1-1"
    counts = _counts_from_recap_rows(result["rows"])
    assert counts.get("P1") == 83
    assert counts.get("P2") == 83
    assert counts.get("P3") == 83
    assert counts.get("P4") == 83
    assert counts.get("P5") == 169
    assert counts.get("P6") == 32
    assert sum(counts.values()) == 533
    total_kg = sum(float(r["weight_kg"]) for r in result["rows"])
    assert abs(total_kg - 9214.7) <= TOL_KG


def test_recap_group_pc_8400():
    doc = _v1_doc()
    result = recap_group(doc, "PC-1")
    assert result["group_id"] == "PC-1"
    assert len(result["piles"]) == 1
    assert result["piles"][0]["pile_id"] == "PC-1-1"
    # totals memakai kunci "id" (bukan "mark")
    counts: dict[str, int] = {}
    for t in result["totals"]:
        key = t.get("mark") or t["id"]
        counts[key] = counts.get(key, 0) + int(t["count"])
    assert sum(counts.values()) == 533
    assert counts.get("P5") == 169
    assert counts.get("P6") == 32


def test_recap_pile_matches_build_bar_groups_counts():
    """Rekap dan builder memakai sumber geometri yang sama."""
    doc = _v1_doc()
    from_builder = {g.mark: g.count for g in build_bar_groups(doc, "PC-1-1")}
    from_recap = _counts_from_recap_rows(recap_pile(doc, "PC-1-1")["rows"])
    assert from_recap == from_builder


def test_recap_pile_unknown_id_raises():
    doc = _v1_doc()
    try:
        recap_pile(doc, "TIDAK-ADA")
    except ValueError as e:
        assert "TIDAK-ADA" in str(e) or "tidak ditemukan" in str(e).lower()
    else:
        raise AssertionError("diharapkan ValueError untuk pile_id tidak ada")


# --- S5: kontrak template P1–P6 ---


def _deep_copy_doc():
    return json.loads(json.dumps(_v1_doc()))


def test_s5_rejects_instance_overrides_params():
    doc = _deep_copy_doc()
    doc["groups"][0]["instances"][0]["overrides"] = {"params": {"length": 4200}}
    try:
        build_bar_groups(doc, "PC-1-1")
    except ValueError as e:
        assert "overrides.params" in str(e)
    else:
        raise AssertionError("diharapkan ValueError untuk instance.overrides.params")


def test_s5_rejects_group_defaults_params():
    doc = _deep_copy_doc()
    doc["groups"][0]["defaults"] = {"params": {"length": 4200}}
    try:
        build_bar_groups(doc, "PC-1-1")
    except ValueError as e:
        assert "defaults.params" in str(e)
    else:
        raise AssertionError("diharapkan ValueError untuk group.defaults.params")


def test_s5_rejects_missing_mark():
    doc = _deep_copy_doc()
    data = doc["groups"][0]["definition"]["data"]
    data["rebars"] = [r for r in data["rebars"] if r["id"] != "P6"]
    try:
        build_bar_groups(doc, "PC-1-1")
    except ValueError as e:
        msg = str(e)
        assert "P6" in msg and ("hilang" in msg or "tidak ditemukan" in msg)
    else:
        raise AssertionError("diharapkan ValueError untuk mark P6 hilang")


def test_s5_rejects_foreign_mark():
    doc = _deep_copy_doc()
    data = doc["groups"][0]["definition"]["data"]
    extra = json.loads(json.dumps(data["rebars"][0]))
    extra["id"] = "PX"
    data["rebars"].append(extra)
    try:
        build_bar_groups(doc, "PC-1-1")
    except ValueError as e:
        assert "PX" in str(e)
    else:
        raise AssertionError("diharapkan ValueError untuk mark asing PX")


def test_s5_rejects_duplicate_mark():
    doc = _deep_copy_doc()
    data = doc["groups"][0]["definition"]["data"]
    data["rebars"].append(json.loads(json.dumps(data["rebars"][0])))
    try:
        build_bar_groups(doc, "PC-1-1")
    except ValueError as e:
        assert "duplikat" in str(e).lower()
    else:
        raise AssertionError("diharapkan ValueError untuk mark duplikat")


def test_s5_rejects_bars_outside_concrete_when_length_shrunk():
    """Range absolut 8300 dengan length 4200 → batang di luar beton → error."""
    doc = _deep_copy_doc()
    data = doc["groups"][0]["definition"]["data"]
    data["params"]["length"] = 4200
    # width tetap 8400; range rebar tetap 100–8300 di JSON
    try:
        build_bar_groups(doc, "PC-1-1")
    except ValueError as e:
        msg = str(e).lower()
        assert "luar beton" in msg or "di luar" in msg
    else:
        raise AssertionError("diharapkan ValueError untuk batang di luar beton")


def test_s5_recap_also_rejects_overrides():
    doc = _deep_copy_doc()
    doc["groups"][0]["instances"][0]["overrides"] = {"params": {"lap_nesting": "bottom_inside"}}
    try:
        recap_pile(doc, "PC-1-1")
    except ValueError as e:
        assert "overrides.params" in str(e)
    else:
        raise AssertionError("recap_pile harus menolak overrides.params")
