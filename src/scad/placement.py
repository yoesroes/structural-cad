"""Penempatan tulangan pada bored pile — murni, tanpa impor scad_engine."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from scad.expr import ExprError, evaluate
from scad.shapes import (
    Centerline,
    build_centerline,
    build_helix_multi_pitch,
    cut_length_formula,
    helix_cut_length_segment,
    is_by_zone,
    resolve_by_zone_pitches,
)


@dataclass
class PileEnv:
    """Lingkungan satu pile setelah resolve zona & parameter efektif."""

    diameter: float
    cover: float
    cover_ref: str  # surface | centerline
    depth_below_cof: float
    zones: list[Any]  # ResolvedZone-like: id, side, length, z_top, z_bottom
    params: dict[str, float]
    shapes: dict[str, dict]
    settings: dict[str, Any]
    d_of: dict[str, float]  # id rebar -> diameter
    functions: dict[str, Any] | None = None
    rebars_by_id: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class Placed:
    shape_key: str
    origin: tuple[float, float, float]
    tag: str
    centerline: Centerline
    diameter: float
    cut_length: float | None
    rebar_id: str


def _eval(val: Any, env_vars: dict, functions: dict | None) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    return float(evaluate(val, variables=env_vars, functions=functions))


def zone_map(env: PileEnv) -> dict[str, Any]:
    return {z.id: z for z in env.zones}


def extent_z_range(item: dict, env: PileEnv) -> tuple[float, float]:
    """Kembalikan (z_bottom, z_top) rentang batang (positif ke atas)."""
    extent = item.get("extent") or {}
    zids = extent.get("zones") or []
    zm = zone_map(env)
    if not zids:
        raise ValueError("extent.zones kosong")
    zs = []
    for zid in zids:
        if zid not in zm:
            raise ValueError(f"Zona '{zid}' tidak ada pada pile")
        z = zm[zid]
        zs.append(z.z_bottom)
        zs.append(z.z_top)
    z_bot, z_top = min(zs), max(zs)
    vars_ = {**env.params, "d": float(item["diameter"]), "pi": math.pi}
    funcs = env.functions
    if "extend_start" in extent:
        z_top += _eval(extent["extend_start"], vars_, funcs)
    if "extend_end" in extent:
        z_bot -= _eval(extent["extend_end"], vars_, funcs)
    return z_bot, z_top


def _make_expr_funcs(env: PileEnv, stack: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """d_of, zone_length, shape_param (dengan deteksi siklus)."""
    stack = stack if stack is not None else []

    def d_of(name: str) -> float:
        if name not in env.d_of:
            raise ValueError(f"d_of: id '{name}' tidak dikenal")
        return float(env.d_of[name])

    def zone_length(zid: str) -> float:
        zm = zone_map(env)
        if zid not in zm:
            raise ValueError(f"zone_length: '{zid}' tidak ada")
        return float(zm[zid].length)

    def shape_param(rebar_id: str, param_name: str, zone_id: str | None = None) -> float:
        cycle_keys = [(a, b) for a, b, *_rest in stack]
        if (str(rebar_id), str(param_name)) in cycle_keys:
            raise ExprError(
                f"shape_param: rujukan siklik melibatkan {rebar_id!r}.{param_name!r}"
            )
        if str(rebar_id) not in env.rebars_by_id:
            raise ValueError(f"shape_param: id tulangan '{rebar_id}' tidak dikenal")
        item = env.rebars_by_id[str(rebar_id)]
        sp = item.get("shape_params") or {}
        if param_name not in sp:
            raise ValueError(
                f"shape_param: parameter '{param_name}' tidak ada pada '{rebar_id}'"
            )
        raw = sp[param_name]
        vars_ = {
            **env.params,
            "d": float(item.get("diameter") or 0),
            "pi": math.pi,
            "diameter": env.diameter,
            "cover": env.cover,
        }
        child_stack = stack + [(str(rebar_id), str(param_name), str(zone_id or ""))]
        child_funcs = _make_expr_funcs(env, child_stack)
        if is_by_zone(raw):
            zid = zone_id or "Z1"
            bz = raw.get("by_zone") or {}
            if zid not in bz:
                # fallback: first zone key
                if zone_id is not None:
                    raise ValueError(
                        f"shape_param: by_zone '{rebar_id}.{param_name}' tidak punya zona {zid}"
                    )
                if not bz:
                    raise ValueError("shape_param: by_zone kosong")
                zid = next(iter(bz.keys()))
            return float(
                evaluate(bz[zid], variables=vars_, functions=child_funcs)
                if not isinstance(bz[zid], (int, float))
                else float(bz[zid])
            )
        if isinstance(raw, (int, float)):
            return float(raw)
        return float(evaluate(raw, variables=vars_, functions=child_funcs))

    return {"d_of": d_of, "zone_length": zone_length, "shape_param": shape_param}


def axis_radius(item: dict, env: PileEnv) -> float:
    """Jari-jari sumbu dari muka outer beton."""
    pos = item.get("position") or {}
    D = env.diameter
    d = float(item["diameter"])
    offset_type = pos.get("offset_type") or "clear"
    vars_ = {
        **env.params,
        "d": d,
        "pi": math.pi,
        "diameter": env.diameter,
        "cover": env.cover,
    }
    funcs = _make_expr_funcs(env)
    offset = _eval(pos.get("offset", 0), vars_, funcs)
    if offset_type == "clear":
        return D / 2.0 - offset - d / 2.0
    if offset_type == "center":
        return D / 2.0 - offset
    return D / 2.0 - offset - d / 2.0


def _place_helix_by_zone(
    item: dict,
    env: PileEnv,
    shape_def: dict,
    shape_params: dict,
    d: float,
    funcs: dict,
    vars_: dict,
) -> list[Placed]:
    rid = item["id"]
    extent = item.get("extent") or {}
    zids = list(extent.get("zones") or [])
    if not zids:
        raise ValueError("extent.zones kosong untuk spiral by_zone")
    zm = zone_map(env)
    for zid in zids:
        if zid not in zm:
            raise ValueError(f"Zona '{zid}' tidak ada pada pile")

    env_shapes = {**vars_, "_functions": funcs}
    pitches = resolve_by_zone_pitches(shape_params["B"], zids, env_shapes)

    # A outer diameter
    a_raw = shape_params.get("A")
    if a_raw is None:
        raise ValueError("shape_params.A wajib untuk spiral")
    outer = float(
        a_raw
        if isinstance(a_raw, (int, float))
        else evaluate(a_raw, variables=vars_, functions=funcs)
    )

    # Segmen dari atas (mendekati COF) ke bawah: urutkan zona by z_top descending
    ordered = sorted(zids, key=lambda z: float(zm[z].z_top), reverse=True)
    segments: list[tuple[float, float]] = []
    total_cut = 0.0
    for zid in ordered:
        z = zm[zid]
        height = float(z.z_top) - float(z.z_bottom)
        pitch = pitches[zid]
        segments.append((height, pitch))
        total_cut += helix_cut_length_segment(outer, d, height, pitch)

    z_bot, z_top = extent_z_range(item, env)
    # centerline lokal: z=0 di ujung atas, menurun
    cl = build_helix_multi_pitch(outer, d, segments, z0=0.0, downward=True)
    origin = (0.0, 0.0, z_top)
    return [
        Placed(
            shape_key=f"{rid}:0",
            origin=origin,
            tag=rid,
            centerline=cl,
            diameter=d,
            cut_length=float(total_cut),
            rebar_id=rid,
        )
    ]


def place_rebar(item: dict, env: PileEnv) -> list[Placed]:
    """Hasilkan daftar Placed untuk satu RebarItem."""
    rid = item["id"]
    d = float(item["diameter"])
    shape_ref = item.get("shape") or {}
    code = shape_ref.get("code")
    if not code or code not in env.shapes:
        raise ValueError(f"Bentuk '{code}' tidak ada di project.shapes")
    shape_def = env.shapes[code]
    z_bot, z_top = extent_z_range(item, env)
    height = z_top - z_bot

    vars_ = {
        **env.params,
        "d": d,
        "pi": math.pi,
        "diameter": env.diameter,
        "cover": env.cover,
    }
    funcs = _make_expr_funcs(env)
    shape_params = dict(item.get("shape_params") or {})
    for p in shape_def.get("params") or []:
        if p.get("from_extent") and p["name"] not in shape_params:
            shape_params[p["name"]] = height

    env_shapes = {**vars_, "_functions": funcs}
    btype = (shape_def.get("builder") or {}).get("type")

    # Spiral dengan pitch per zona (R87 v2)
    if btype == "helix" and is_by_zone(shape_params.get("B")):
        return _place_helix_by_zone(
            item, env, shape_def, shape_params, d, funcs, vars_
        )

    cl = build_centerline(shape_def, shape_params, d, env_shapes)
    cut = cut_length_formula(shape_def, shape_params, d, env_shapes)
    # Samakan panjang heliks skalar dengan rumus cut (hipotenusa pitch)
    if btype == "helix" and cut is not None:
        cl = Centerline(
            points=cl.points,
            length=float(cut),
            closed=cl.closed,
            meta=cl.meta,
        )

    arr = item.get("arrangement") or {"mode": "single"}
    mode = arr.get("mode", "single")
    pattern = arr.get("pattern")
    placed: list[Placed] = []

    if mode == "single" or pattern is None and mode != "group":
        if btype == "helix":
            origin = (0.0, 0.0, z_bot)
            placed.append(
                Placed(
                    shape_key=f"{rid}:0",
                    origin=origin,
                    tag=rid,
                    centerline=cl,
                    diameter=d,
                    cut_length=cut,
                    rebar_id=rid,
                )
            )
        elif btype == "straight":
            r = axis_radius(item, env)
            origin = (r, 0.0, z_bot)
            placed.append(
                Placed(
                    shape_key=f"{rid}:0",
                    origin=origin,
                    tag=rid,
                    centerline=cl,
                    diameter=d,
                    cut_length=cut,
                    rebar_id=rid,
                )
            )
        else:
            origin = (0.0, 0.0, z_bot)
            placed.append(
                Placed(
                    shape_key=f"{rid}:0",
                    origin=origin,
                    tag=rid,
                    centerline=cl,
                    diameter=d,
                    cut_length=cut,
                    rebar_id=rid,
                )
            )
        return placed

    if pattern == "polar":
        count = int(arr.get("count") or 0)
        if count < 1:
            raise ValueError("count polar harus >= 1")
        bundle = int(arr.get("bundle") or 1)
        start_angle = float(arr.get("start_angle_deg") or 0.0)
        r = axis_radius(item, env)
        if btype == "straight":
            cl = build_centerline(
                shape_def,
                {**shape_params, "A": height},
                d,
                env_shapes,
            )
            cut = height
        for i in range(count):
            ang = math.radians(start_angle + 360.0 * i / count)
            ca, sa = math.cos(ang), math.sin(ang)
            for b in range(bundle):
                t_off = (b - (bundle - 1) / 2.0) * d
                x = r * ca - t_off * sa
                y = r * sa + t_off * ca
                origin = (x, y, z_bot)
                placed.append(
                    Placed(
                        shape_key=f"{rid}:{i}:{b}",
                        origin=origin,
                        tag=f"{rid}",
                        centerline=cl,
                        diameter=d,
                        cut_length=cut,
                        rebar_id=rid,
                    )
                )
        return placed

    if pattern == "linear" and arr.get("axis") == "z":
        spacing = _eval(arr.get("spacing") or 0, vars_, funcs)
        if spacing <= 0:
            raise ValueError("spacing linear harus > 0")
        rg = arr.get("range") or {}
        zs: list[float] = []
        if "from" in rg or "to" in rg:
            z_from = _eval(rg.get("from", z_bot), vars_, funcs)
            z_to = _eval(rg.get("to", z_top), vars_, funcs)
            if z_from <= z_to:
                z = z_from
                while z <= z_to + 1e-9:
                    zs.append(z)
                    z += spacing
            else:
                z = z_from
                while z >= z_to - 1e-9:
                    zs.append(z)
                    z -= spacing
        else:
            z = z_top
            while z >= z_bot - 1e-9:
                zs.append(z)
                z -= spacing
        for i, zz in enumerate(zs):
            origin = (0.0, 0.0, zz)
            placed.append(
                Placed(
                    shape_key=f"{rid}:{i}",
                    origin=origin,
                    tag=rid,
                    centerline=cl,
                    diameter=d,
                    cut_length=cut,
                    rebar_id=rid,
                )
            )
        return placed

    raise ValueError(f"arrangement tidak didukung: mode={mode} pattern={pattern}")
