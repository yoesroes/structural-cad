"""Uji wajib T03 — validator dokumen."""
from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

import pytest


from scad.validate import validate_document

EXAMPLES = REPO_ROOT / "examples"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


def test_examples_have_no_errors():
    for name in ("BP_D1200.elem.json", "P1.project.json", "shapes.builtin.json"):
        issues = validate_document(_load(name))
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], f"{name}: {errors}"


def test_override_diameter_is_schema():
    doc = _load("P1.project.json")
    doc = copy.deepcopy(doc)
    # Override parameter yang tidak diizinkan (hanya depth_below_cof)
    doc["groups"][0]["instances"][0]["overrides"] = {
        "params": {"diameter": 1500}
    }
    codes = _codes(validate_document(doc))
    assert "SCHEMA" in codes


def test_duplicate_rebar_id():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    rebars = doc["definition"]["rebars"]
    rebars.append(copy.deepcopy(rebars[0]))  # same id
    codes = _codes(validate_document(doc))
    assert "ID_DUP" in codes


def test_missing_zone_ref():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    doc["definition"]["rebars"][0]["extent"]["zones"] = ["Z9"]
    codes = _codes(validate_document(doc))
    assert "REF_MISSING" in codes


def test_rest_not_last_below():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    # Z1 becomes rest while Z2/Z3 still below
    doc["definition"]["zones"][1]["length"] = "rest"
    codes = _codes(validate_document(doc))
    assert "ZONE_REST_POS" in codes


def test_position_cycle():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    rebars = doc["definition"]["rebars"]
    # B1 -> B2, B2 -> B1
    rebars[0]["position"] = {"ref": "bar", "bar": "B2", "relation": "inside", "gap": 0}
    rebars[1]["position"] = {"ref": "bar", "bar": "B1", "relation": "outside", "gap": 0}
    codes = _codes(validate_document(doc))
    assert "POS_CYCLE" in codes


def test_hash_diff_info():
    doc = _load("P1.project.json")
    doc = copy.deepcopy(doc)
    # ubah definisi tertanam tanpa update hash
    doc["groups"][0]["definition"]["data"]["name"] = "Diubah"
    issues = validate_document(doc)
    assert any(i.code == "HASH_DIFF" and i.level == "info" for i in issues)


def test_unknown_expression_is_expr_error():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    doc["definition"]["rebars"][0]["position"]["offset"] = "=nama_tidak_ada*2"
    issues = validate_document(doc)
    assert any(i.code == "EXPR" and i.level == "error" for i in issues)


def test_polar_spacing_is_arr_bad():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    doc["definition"]["rebars"][0]["arrangement"] = {
        "mode": "group", "pattern": "polar", "by": "spacing", "spacing": 110
    }
    issues = validate_document(doc)
    assert any(i.code == "ARR_BAD" and i.level == "error" for i in issues)


def test_group_definition_type_mismatch_is_error():
    doc = _load("P1.project.json")
    doc = copy.deepcopy(doc)
    doc["groups"][0]["type"] = "pile_cap"
    issues = validate_document(doc)
    assert any(i.code == "TYPE_MISMATCH" and i.level == "error" for i in issues)



def test_linear_non_z_axis_is_arr_bad():
    doc = _load("BP_D1200.elem.json")
    doc = copy.deepcopy(doc)
    doc["definition"]["rebars"][0]["arrangement"] = {
        "mode": "group", "pattern": "linear", "axis": "x", "by": "spacing", "spacing": 110
    }
    issues = validate_document(doc)
    assert any(i.code == "ARR_BAD" and i.level == "error" for i in issues)


def test_hardcoded_shape_letters_are_expr_on_extend_start():
    """=A*2, =r*2, =height+1, ='a'+1 pada extend_start harus EXPR (P3b)."""
    doc = _load("BP_D1200.elem.json")
    for expr in ("=A*2", "=r*2", "=height+1", "='a'+1"):
        d = copy.deepcopy(doc)
        d["definition"]["rebars"][2]["extent"]["extend_start"] = expr
        issues = validate_document(d)
        assert any(i.code == "EXPR" and i.level == "error" for i in issues), expr


def test_valid_runtime_expressions_still_pass():
    """Ekspresi yang dipakai contoh tetap lolos (paritas runtime)."""
    for name in ("BP_D1200.elem.json", "P1.project.json"):
        issues = validate_document(_load(name))
        assert not any(i.code == "EXPR" and i.level == "error" for i in issues), name


def test_polar_count_invalid_is_arr_bad_not_exception():
    """count < 1 atau count tidak bisa dikonversi → ARR_BAD, bukan exception."""
    from scad.validate import _expression_and_arrangement_issues

    definition = {
        "type": "bored_pile",
        "params": {"diameter": 1200, "cover": 75},
        "rebars": [
            {
                "id": "B1",
                "arrangement": {
                    "mode": "group",
                    "pattern": "polar",
                    "by": "count",
                    "count": "bukan-angka",
                },
            },
            {
                "id": "B2",
                "arrangement": {
                    "mode": "group",
                    "pattern": "polar",
                    "by": "count",
                    "count": 0,
                },
            },
        ],
    }
    issues = _expression_and_arrangement_issues(definition, "/definition", {})
    assert sum(1 for i in issues if i.code == "ARR_BAD") >= 2


def test_malformed_rebar_and_zone_do_not_raise():
    """Dokumen rusak: rebar bukan dict, zona tanpa id — issue/skip, bukan exception."""
    doc = _load("P1.project.json")
    doc = copy.deepcopy(doc)
    data = doc["groups"][0]["definition"]["data"]
    data["rebars"] = [None, "bukan-dict", {"id": "X"}]
    data["zones"] = [{"length": "rest"}, {"id": "Z1", "side": "below_cof", "length": 1000}]
    # tidak boleh melempar
    issues = validate_document(doc)
    assert isinstance(issues, list)


def test_check_expression_parity_with_evaluate_names():
    """check_expression lolos <=> evaluate tidak gagal karena nama (konteks placement)."""
    from scad.expr import check_expression, evaluate, ExprError

    names = {"d", "pi", "diameter", "cover", "depth_below_cof"}
    funcs = {"min", "max", "ceil", "floor", "round", "abs", "sqrt", "d_of", "zone_length", "shape_param"}
    cases_ok = [
        "=40*d",
        "=diameter-2*cover",
        "=cover+d_of('B2')",
        "=zone_length('Z0')",
    ]
    cases_bad = ["=A*2", "=r*2", "=height+1", "=width", "='x'+1", "=unknown*2"]
    runtime_vars = {"d": 16.0, "diameter": 1200.0, "cover": 75.0, "depth_below_cof": 30000.0, "pi": 3.14}

    def d_of(n: str) -> float:
        return 16.0

    def zone_length(z: str) -> float:
        return 1000.0

    rt_funcs = {"d_of": d_of, "zone_length": zone_length}

    for expr in cases_ok:
        assert check_expression(expr, names, funcs) == [], expr
        # evaluate boleh gagal untuk alasan non-nama (fungsi), tapi bukan "Variabel tidak dikenal"
        try:
            evaluate(expr, runtime_vars, rt_funcs)
        except ExprError as e:
            assert "Variabel tidak dikenal" not in str(e), (expr, e)

    for expr in cases_bad:
        msgs = check_expression(expr, names, funcs)
        assert msgs, expr
