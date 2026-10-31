
"""Uji wajib T01 — evaluator ekspresi aman."""
from __future__ import annotations

import math
from pathlib import Path

import pytest


from scad.expr import ExprError, evaluate


def test_literal_numbers():
    assert evaluate(40) == 40.0
    assert evaluate(3.5) == 3.5


def test_40_times_d():
    assert evaluate("=40*d", {"d": 32}) == 1280.0


def test_diameter_minus_cover():
    assert evaluate("=diameter-2*cover", {"diameter": 1200, "cover": 75}) == 1050.0


def test_d_of_function():
    def d_of(mark: str) -> float:
        assert mark == "B2"
        return 16.0

    assert evaluate("=cover+d_of('B2')", {"cover": 75}, {"d_of": d_of}) == 91.0


def test_helix_cut_length_formula():
    # =C/B*pi*(A-d) dengan nilai contoh
    vars_ = {"C": 3000.0, "B": 75.0, "A": 1050.0, "d": 16.0}
    got = evaluate("=C/B*pi*(A-d)", vars_)
    expected = (3000.0 / 75.0) * math.pi * (1050.0 - 16.0)
    assert got == pytest.approx(expected)


def test_ceil_expression():
    assert evaluate("=ceil(2077/300)+1") == 8.0


def test_reject_import():
    with pytest.raises(ExprError):
        evaluate("=__import__('os')")


def test_reject_attribute():
    with pytest.raises(ExprError):
        evaluate("=a.b", {"a": 1})


def test_reject_subscript():
    with pytest.raises(ExprError):
        evaluate("=[1][0]")


def test_reject_division_by_zero():
    with pytest.raises(ExprError, match="nol"):
        evaluate("=1/0")


def test_reject_unknown_variable():
    with pytest.raises(ExprError, match="tak_ada"):
        evaluate("=tak_ada")


def test_reject_incomplete():
    with pytest.raises(ExprError):
        evaluate("=(")


def test_reject_without_equals():
    with pytest.raises(ExprError, match="="):
        evaluate("40*d")


def test_reject_lambda():
    with pytest.raises(ExprError):
        evaluate("=lambda: 1")


def test_unary_and_parens():
    assert evaluate("=-(2+3)*4", {}) == -20.0


def test_zone_length_function():
    def zone_length(zid: str) -> float:
        return {"Z1": 3000.0}[zid]

    assert evaluate("=zone_length('Z1')+10", {}, {"zone_length": zone_length}) == 3010.0


# --- Regresi: variabel non-finite ---


@pytest.mark.parametrize(
    "bad",
    [math.nan, math.inf, -math.inf],
    ids=["nan", "inf", "-inf"],
)
def test_reject_non_finite_variable(bad):
    with pytest.raises(ExprError):
        evaluate("=d*2", {"d": bad})


# --- Regresi: hasil aritmetika overflow / non-finite ---


def test_reject_overflow_multiplication():
    with pytest.raises(ExprError):
        evaluate("=1e308*10")


def test_reject_overflow_power():
    with pytest.raises(ExprError):
        evaluate("=1e308**2")


# --- Regresi: fungsi kustom mengembalikan nilai tidak valid ---


@pytest.mark.parametrize(
    "bad_return",
    [math.inf, None, "abc"],
    ids=["inf", "none", "str"],
)
def test_reject_function_bad_return(bad_return):
    def bad_fn() -> object:
        return bad_return

    with pytest.raises(ExprError):
        evaluate("=bad_fn()", {}, {"bad_fn": bad_fn})


# --- Regresi: variabel berisi string non-numerik ---


def test_reject_non_numeric_string_variable():
    with pytest.raises(ExprError):
        evaluate("=d*2", {"d": "abc"})


# --- Regresi: ekspresi valid tetap bekerja ---


def test_valid_simple_addition():
    assert evaluate("=1+2") == 3.0


def test_valid_sqrt():
    assert evaluate("=sqrt(16)") == 4.0


def test_valid_variable_multiplication():
    assert evaluate("=d*2", {"d": 10}) == 20.0


# --- check_expression (P3b) ---

from scad.expr import check_expression


def test_check_expression_rejects_injection_and_syntax():
    assert check_expression("=__import__('os')", {"d"}, set())
    assert check_expression("=1+", {"d"}, set())  # sintaks rusak
    assert any("tidak dikenal" in m or "tidak diizinkan" in m for m in check_expression("=foo(1)", {"d"}, set()))


def test_check_expression_rejects_kwargs_and_attribute():
    msgs = check_expression("=min(1, x=2)", set(), {"min"})
    assert any("kata kunci" in m for m in msgs)
    msgs = check_expression("=(1).real", set(), set())
    assert msgs  # attribute/node tidak didukung


def test_check_expression_string_constant_only_in_allowed_funcs():
    ok_names = {"d", "cover", "diameter", "pi"}
    funcs = {"d_of", "zone_length", "shape_param", "min"}
    assert check_expression("=d_of('B2')", ok_names, funcs) == []
    assert check_expression("=zone_length('Z0')", ok_names, funcs) == []
    assert check_expression("=shape_param('B2','A','Z1')", ok_names, funcs) == []
    bad = check_expression("='a'+1", ok_names, funcs)
    assert any("string" in m.lower() or "Konstanta string" in m for m in bad)
    bad2 = check_expression("=min('a', 1)", ok_names, funcs)
    assert any("string" in m.lower() or "Konstanta string" in m for m in bad2)


def test_check_expression_unknown_name():
    msgs = check_expression("=A*2", {"d", "cover", "diameter", "pi"}, set())
    assert any("A" in m for m in msgs)
    msgs = check_expression("=r*2", {"d", "cover", "diameter", "pi"}, set())
    assert any("r" in m for m in msgs)
    assert check_expression("=40*d", {"d", "cover", "diameter", "pi"}, set()) == []
