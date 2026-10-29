"""Pembangun centerline bentuk tulangan (R20/R87/RING) — murni, tanpa scad_engine."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from scad.expr import evaluate


@dataclass(frozen=True)
class Centerline:
    points: tuple[tuple[float, float, float], ...]
    length: float
    closed: bool = False
    meta: dict[str, Any] | None = None



def _segments_for_sagitta(radius: float, angle: float, sagitta_mm: float) -> int:
    """Jumlah segmen minimum agar sagitta busur tidak melampaui batas."""
    if radius <= 0 or angle <= 0:
        return 1
    ratio = max(-1.0, min(1.0, 1.0 - sagitta_mm / radius))
    max_angle = 2.0 * math.acos(ratio)
    if max_angle <= 0:
        return max(1, int(math.ceil(angle)))
    return max(1, int(math.ceil(angle / max_angle)))


def _eval_param(val: Any, env: dict[str, Any]) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict) and "by_zone" in val:
        raise ValueError(
            "Parameter bentuk by_zone tidak dapat dievaluasi sebagai skalar tunggal"
        )
    return float(evaluate(val, variables=env, functions=env.get("_functions")))


def is_by_zone(val: Any) -> bool:
    return isinstance(val, dict) and "by_zone" in val and isinstance(val["by_zone"], dict)


def resolve_by_zone_pitches(
    by_zone_val: dict,
    zone_ids: list[str],
    env: dict[str, Any],
) -> dict[str, float]:
    """Evaluasi pitch per zona; semua zone_ids wajib ada; kunci asing ditolak."""
    raw = by_zone_val.get("by_zone") or {}
    if not isinstance(raw, dict):
        raise ValueError("SHAPE_PARAM: by_zone harus objek")
    foreign = sorted(set(raw.keys()) - set(zone_ids))
    if foreign:
        raise ValueError(
            f"SHAPE_PARAM: kunci zona asing pada by_zone: {foreign}"
        )
    missing = sorted(set(zone_ids) - set(raw.keys()))
    if missing:
        raise ValueError(
            f"SHAPE_PARAM: by_zone kurang nilai untuk zona: {missing}"
        )
    out: dict[str, float] = {}
    for zid in zone_ids:
        out[zid] = _eval_param(raw[zid], env)
        if out[zid] <= 0:
            raise ValueError(f"SHAPE_PARAM: pitch zona {zid} harus > 0")
    return out


def helix_cut_length_segment(outer: float, diameter: float, height: float, pitch: float) -> float:
    """Panjang heliks satu segmen: (H/pitch) * sqrt((pi*(A-d))^2 + pitch^2)."""
    if pitch <= 0 or height < 0:
        raise ValueError("pitch/height heliks tidak valid")
    circ = math.pi * (outer - diameter)
    turns = height / pitch
    return turns * math.sqrt(circ * circ + pitch * pitch)


def build_helix_multi_pitch(
    outer: float,
    diameter: float,
    segments: list[tuple[float, float]],
    *,
    z0: float = 0.0,
    downward: bool = True,
) -> Centerline:
    """Heliks menerus: segments = [(height, pitch), ...] dari ujung atas ke bawah.

    Titik di koordinat lokal dengan z dimulai di z0; bila downward, z menurun.
    """
    d = float(diameter)
    r = (outer - d) / 2.0
    if r <= 0:
        raise ValueError("radius heliks tidak valid")
    pts: list[tuple[float, float, float]] = []
    total_cut = 0.0
    angle = 0.0
    z = float(z0)
    # titik awal
    pts.append((r * math.cos(angle), r * math.sin(angle), z))
    for height, pitch in segments:
        height = float(height)
        pitch = float(pitch)
        if height <= 0 or pitch <= 0:
            raise ValueError("segmen heliks height/pitch harus > 0")
        n_turns = height / pitch
        total_cut += helix_cut_length_segment(outer, d, height, pitch)
        n = _segments_for_sagitta(r, n_turns * 2.0 * math.pi, 0.1)
        for i in range(1, n + 1):
            t = i / n
            ang = angle + t * n_turns * 2.0 * math.pi
            zz = z - t * height if downward else z + t * height
            pts.append((r * math.cos(ang), r * math.sin(ang), zz))
        angle += n_turns * 2.0 * math.pi
        z = z - height if downward else z + height
    total_turns = sum(h / p for h, p in segments)
    return Centerline(
        points=tuple(pts),
        length=float(total_cut),
        closed=False,
        meta={
            "segments": segments,
            "outer_diameter": outer,
            "cut_length": total_cut,
            "turns": total_turns,  # agar LEN_MISMATCH memakai toleransi heliks 0,1%
        },
    )


def _resolve_params(shape_def: dict, shape_params: dict | None, diameter: float, env: dict) -> dict[str, float]:
    """Evaluasi shape_params + default dari shape_def.params (nilai skalar saja)."""
    base = dict(env)
    base["d"] = float(diameter)
    out: dict[str, float] = {}
    params_spec = shape_def.get("params") or []
    sp = shape_params or {}
    for p in params_spec:
        name = p["name"]
        if name in sp:
            if is_by_zone(sp[name]):
                continue  # ditangani pemanggil multi-pitch
            out[name] = _eval_param(sp[name], base)
        elif "default" in p:
            out[name] = _eval_param(p["default"], {**base, **out})
        # from_extent diisi pemanggil lewat shape_params
    for k, v in sp.items():
        if k not in out and not is_by_zone(v):
            out[k] = _eval_param(v, {**base, **out})
    return out


def build_centerline(
    shape_def: dict,
    shape_params: dict,
    diameter: float,
    env: dict,
) -> Centerline:
    """Bangun titik 3D lokal centerline dari builder bentuk."""
    builder = shape_def.get("builder") or {}
    btype = builder.get("type")
    resolved = _resolve_params(shape_def, shape_params, diameter, env)
    d = float(diameter)
    local_env = {**env, **resolved, "d": d}

    if btype == "straight":
        length = _eval_param(builder.get("length", resolved.get("A", 0)), local_env)
        # sepanjang +Z dari 0 (pemanggil bisa menggeser origin)
        pts = ((0.0, 0.0, 0.0), (0.0, 0.0, float(length)))
        return Centerline(points=pts, length=float(length), closed=False)

    if btype == "helix":
        outer = _eval_param(builder.get("outer_diameter", resolved.get("A")), local_env)
        pitch = _eval_param(builder.get("pitch", resolved.get("B")), local_env)
        height = _eval_param(builder.get("height", resolved.get("C")), local_env)
        r = (outer - d) / 2.0  # radius sumbu
        if pitch <= 0 or height < 0:
            raise ValueError("pitch/height heliks tidak valid")
        n_turns = height / pitch
        # Batasi sagitta radial maksimum menjadi 0,1 mm agar poligon tidak
        # menyimpang jauh ke dalam kurva dan menghasilkan tabrakan palsu.
        n = _segments_for_sagitta(r, n_turns * 2.0 * math.pi, 0.1)
        pts = []
        for i in range(n + 1):
            t = i / n
            ang = t * n_turns * 2 * math.pi
            z = t * height
            pts.append((r * math.cos(ang), r * math.sin(ang), z))
        # Panjang true heliks (hipotenusa), sama dengan cut_length R87 / H5
        length = helix_cut_length_segment(outer, d, height, pitch)
        return Centerline(
            points=tuple(pts),
            length=float(length),
            closed=False,
            meta={"turns": n_turns, "pitch": pitch, "outer_diameter": outer},
        )

    if btype == "ring":
        outer = _eval_param(builder.get("outer_diameter", resolved.get("A")), local_env)
        lap = _eval_param(builder.get("lap", resolved.get("lap", 0)), local_env)
        r = (outer - d) / 2.0
        n = _segments_for_sagitta(r, 2.0 * math.pi, 0.1)
        pts = []
        for i in range(n + 1):
            ang = 2 * math.pi * i / n
            pts.append((r * math.cos(ang), r * math.sin(ang), 0.0))
        length = math.pi * (outer - d) + lap
        return Centerline(
            points=tuple(pts),
            length=float(length),
            closed=True,
            meta={"outer_diameter": outer, "lap": lap},
        )

    raise ValueError(f"Jenis builder tidak didukung: '{btype}'")


def cut_length_formula(
    shape_def: dict,
    shape_params: dict,
    diameter: float,
    env: dict,
) -> float | None:
    """Evaluasi cut_length bentuk; None bila tidak ada."""
    formula = shape_def.get("cut_length")
    if formula is None:
        return None
    resolved = _resolve_params(shape_def, shape_params, diameter, env)
    local_env = {**env, **resolved, "d": float(diameter)}
    return float(evaluate(formula, variables=local_env, functions=env.get("_functions")))
