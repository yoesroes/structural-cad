"""Tes merah P0 untuk kontrak operasi zona dan evaluator ekspresi."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scad.expr import ExprError, evaluate
from scad.ops import apply_operation


REPO = Path(__file__).resolve().parents[2]


def load_p1() -> dict:
    return json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))


@pytest.mark.xfail(strict=True, reason="S6")
def test_rest_zone_override_is_rejected():
    with pytest.raises(ValueError):
        apply_operation(
            load_p1(),
            {
                "op": "set_pile_zone_length",
                "group": "BP-P1",
                "pile": "P1-1",
                "zone": "Z3",
                "value": 17000,
            },
        )


@pytest.mark.xfail(strict=True, reason="S7")
def test_invalid_power_expressions_raise_expr_error():
    for expression in ("=(0-8)**(1/3)", "=0**-1"):
        with pytest.raises(ExprError):
            evaluate(expression)
