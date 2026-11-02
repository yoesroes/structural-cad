"""Evaluator ekspresi aman untuk parameter Structural CAD.

Angka dikembalikan sebagai float. String harus berawalan '='.
Parse memakai ast — tanpa eval/exec.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Any, Callable, Mapping

_MAX_LEN = 200
_MAX_DEPTH = 20

_BIN_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type, Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Fungsi bawaan; d_of / zone_length / shape_param hanya dari argumen functions
_BUILTIN_FUNCS: dict[str, Callable[..., float]] = {
    "min": min,
    "max": max,
    "ceil": math.ceil,
    "floor": math.floor,
    "round": round,
    "abs": abs,
    "sqrt": math.sqrt,
}

_ALLOWED_FUNC_NAMES = frozenset(_BUILTIN_FUNCS) | frozenset(
    {"d_of", "zone_length", "shape_param"}
)


class ExprError(ValueError):
    """Ekspresi tidak valid atau tidak dapat dievaluasi."""


def _to_finite_float(value: Any, context: str) -> float:
    """Konversi value ke float finite; lempar ExprError bila gagal."""
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ExprError(
            f"Nilai tidak dapat dikonversi ke float ({value!r}) dalam {context}"
        ) from exc
    if not math.isfinite(result):
        raise ExprError(
            f"Nilai tidak finite ({value!r}) dalam {context}"
        )
    return result


def evaluate(
    value: Any,
    variables: Mapping[str, float] | None = None,
    functions: Mapping[str, Callable[..., float]] | None = None,
) -> float:
    """Evaluasi nilai numerik atau ekspresi berawalan '=' menjadi float.

    Parameters
    ----------
    value:
        int/float dikembalikan sebagai float. str harus berawalan '='.
    variables:
        Peta nama variabel -> angka (mis. d, diameter, cover).
    functions:
        Fungsi tambahan, khususnya d_of dan zone_length.
    """
    if isinstance(value, bool):
        raise ExprError(f"Nilai boolean tidak diizinkan sebagai ekspresi: {value!r}")
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ExprError(f"Nilai numerik tidak finite: {value!r}")
        return float(value)
    if not isinstance(value, str):
        raise ExprError(f"Tipe nilai tidak didukung: {type(value).__name__}")

    text = value.strip()
    if not text.startswith("="):
        raise ExprError(
            f"String ekspresi harus berawalan '=', diterima: {value!r}"
        )
    body = text[1:].strip()
    if not body:
        raise ExprError(f"Ekspresi kosong: {value!r}")
    if len(body) > _MAX_LEN:
        raise ExprError(
            f"Ekspresi terlalu panjang (>{_MAX_LEN} karakter): {value!r}"
        )

    try:
        tree = ast.parse(body, mode="eval")
    except SyntaxError as exc:
        raise ExprError(f"Sintaks ekspresi tidak valid: {value!r}") from exc

    vars_map = dict(variables or {})
    funcs_map = dict(_BUILTIN_FUNCS)
    if functions:
        for name, fn in functions.items():
            if name in _ALLOWED_FUNC_NAMES:
                funcs_map[name] = fn

    result = _eval_node(tree.body, vars_map, funcs_map, depth=0, source=value)
    return _to_finite_float(result, f"ekspresi {value!r}")


# Fungsi yang menerima argumen string (nama id / parameter)
_STRING_ARG_FUNCS = frozenset({"d_of", "zone_length", "shape_param"})


def check_expression(
    text: str,
    allowed_names: set[str] | None = None,
    allowed_funcs: set[str] | None = None,
) -> list[str]:
    """Periksa sintaks, node AST, dan nama ekspresi tanpa mengevaluasinya.

    Konstanta string hanya diizinkan sebagai argumen `d_of`, `zone_length`,
    atau `shape_param`. Argumen kata kunci ditolak.
    """
    errors: list[str] = []
    if not isinstance(text, str) or not text.strip().startswith("="):
        return ["String ekspresi harus berawalan '='"]
    body = text.strip()[1:].strip()
    if not body:
        return ["Ekspresi kosong"]
    try:
        tree = ast.parse(body, mode="eval")
    except SyntaxError as exc:
        return [f"Sintaks ekspresi tidak valid: {exc.msg}"]
    names = set(allowed_names or ()) | {"pi"}
    funcs = set(allowed_funcs or ()) | _ALLOWED_FUNC_NAMES
    allowed_bin = tuple(_BIN_OPS)
    allowed_unary = tuple(_UNARY_OPS)

    def visit(node: ast.AST, *, allow_string: bool = False) -> None:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or node.value is None:
                errors.append("Konstanta tidak diizinkan")
                return
            if isinstance(node.value, str):
                if not allow_string:
                    errors.append(
                        "Konstanta string hanya diizinkan sebagai argumen "
                        "d_of/zone_length/shape_param"
                    )
                return
            if isinstance(node.value, (int, float)):
                return
            errors.append("Konstanta tidak diizinkan")
            return
        if isinstance(node, ast.Name):
            if node.id not in names:
                errors.append(f"Variabel tidak dikenal '{node.id}'")
            return
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, allowed_bin):
                errors.append("Operator biner tidak diizinkan")
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, allowed_unary):
                errors.append("Operator unary tidak diizinkan")
            visit(node.operand)
            return
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in funcs:
                errors.append("Fungsi tidak dikenal atau tidak diizinkan")
                return
            string_ok = node.func.id in _STRING_ARG_FUNCS
            for arg in node.args:
                visit(arg, allow_string=string_ok)
            if node.keywords:
                errors.append("Argumen kata kunci tidak diizinkan")
            return
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            errors.append(f"Node AST tidak didukung: {type(node).__name__}")
            return
        errors.append(f"Node AST tidak didukung: {type(node).__name__}")

    visit(tree.body)
    return errors


def _eval_node(
    node: ast.AST,
    variables: dict[str, float],
    functions: dict[str, Callable[..., float]],
    depth: int,
    source: str,
) -> float:
    if depth > _MAX_DEPTH:
        raise ExprError(f"Ekspresi terlalu dalam (>{_MAX_DEPTH}): {source!r}")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return _to_finite_float(node.value, f"konstanta dalam {source!r}")
        raise ExprError(
            f"Konstanta tidak diizinkan ({node.value!r}) dalam {source!r}"
        )

    if isinstance(node, ast.Name):
        name = node.id
        if name.startswith("_"):
            raise ExprError(f"Nama berawalan '_' tidak diizinkan dalam {source!r}")
        if name == "pi":
            return float(math.pi)
        if name not in variables:
            raise ExprError(
                f"Variabel tidak dikenal '{name}' dalam ekspresi {source!r}"
            )
        return _to_finite_float(
            variables[name], f"variabel '{name}' dalam {source!r}"
        )

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise ExprError(f"Operator tidak diizinkan dalam {source!r}")
        left = _eval_node(node.left, variables, functions, depth + 1, source)
        right = _eval_node(node.right, variables, functions, depth + 1, source)
        if op_type is ast.Div and right == 0.0:
            raise ExprError(f"Pembagian nol dalam ekspresi {source!r}")
        try:
            result = _BIN_OPS[op_type](left, right)
        except (OverflowError, ZeroDivisionError, ValueError, TypeError) as exc:
            raise ExprError(f"Operasi aritmetika gagal dalam {source!r}: {exc}") from exc
        if isinstance(result, complex):
            raise ExprError(f"Hasil kompleks tidak diizinkan dalam {source!r}")
        try:
            finite = math.isfinite(result)
        except (TypeError, ValueError) as exc:
            raise ExprError(f"Hasil bukan angka real dalam {source!r}") from exc
        if not finite:
            raise ExprError(f"Hasil tidak finite dalam ekspresi {source!r}")
        return float(result)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ExprError(f"Operator unary tidak diizinkan dalam {source!r}")
        operand = _eval_node(node.operand, variables, functions, depth + 1, source)
        try:
            result = _UNARY_OPS[op_type](operand)
        except OverflowError as exc:
            raise ExprError(f"Hasil di luar jangkauan dalam {source!r}") from exc
        return _to_finite_float(result, f"operator unary dalam {source!r}")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ExprError(f"Panggilan fungsi tidak valid dalam {source!r}")
        fname = node.func.id
        if fname.startswith("_") or fname not in _ALLOWED_FUNC_NAMES:
            raise ExprError(
                f"Fungsi tidak diizinkan '{fname}' dalam ekspresi {source!r}"
            )
        if fname not in functions:
            raise ExprError(
                f"Fungsi '{fname}' tidak tersedia dalam ekspresi {source!r}"
            )
        if node.keywords:
            raise ExprError(
                f"Argumen kata kunci tidak diizinkan dalam {source!r}"
            )
        args: list[Any] = []
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                args.append(arg.value)
            else:
                args.append(
                    _eval_node(arg, variables, functions, depth + 1, source)
                )
        try:
            result = functions[fname](*args)
        except Exception as exc:
            raise ExprError(
                f"Gagal memanggil '{fname}' dalam ekspresi {source!r}: {exc}"
            ) from exc
        return _to_finite_float(
            result, f"hasil fungsi '{fname}' dalam {source!r}"
        )

    # Tolak eksplisit: atribut, subscript, lambda, dll.
    if isinstance(node, (ast.Attribute, ast.Subscript, ast.Lambda,
                         ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
                         ast.List, ast.Tuple, ast.Dict, ast.Set,
                         ast.JoinedStr, ast.FormattedValue)):
        raise ExprError(f"Bentuk ekspresi tidak diizinkan dalam {source!r}")

    raise ExprError(f"Node AST tidak didukung ({type(node).__name__}) dalam {source!r}")
