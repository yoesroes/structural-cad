"""Pemeriksa tabrakan antar batang (jarak sumbu < jumlah jari-jari).

Jalur sumbu tiap batang dipecah menjadi segmen lurus (busur disampel kasar), lalu pasangan segmen
dari batang BERBEDA yang jarak minimumnya < r1 + r2 - tol dianggap bertabrakan. Bersentuhan tepat
(jarak = r1 + r2) BUKAN tabrakan. Mempercepat dengan hash grid.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

from .model import BarGroup, Vec, vadd, vdot, vlen, vmul, vsub


def segment_distance(p1: Vec, q1: Vec, p2: Vec, q2: Vec) -> float:
    """Jarak minimum antar dua segmen 3D (Ericson, Real-Time Collision Detection)."""
    d1, d2, r = vsub(q1, p1), vsub(q2, p2), vsub(p1, p2)
    a, e, f = vdot(d1, d1), vdot(d2, d2), vdot(d2, r)
    eps = 1e-12
    clamp = lambda x: max(0.0, min(1.0, x))
    if a <= eps and e <= eps:
        return vlen(r)
    if a <= eps:
        s, t = 0.0, clamp(f / e)
    else:
        c = vdot(d1, r)
        if e <= eps:
            t, s = 0.0, clamp(-c / a)
        else:
            b = vdot(d1, d2)
            denom = a * e - b * b
            s = clamp((b * f - c * e) / denom) if denom > eps else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t, s = 0.0, clamp(-c / a)
            elif t > 1.0:
                t, s = 1.0, clamp((b - c) / a)
    c1, c2 = vadd(p1, vmul(d1, s)), vadd(p2, vmul(d2, t))
    return vlen(vsub(c1, c2))


def find_clashes(groups: Iterable[BarGroup], tol: float = 0.5, cell: float = 150.0,
                 arc_step_deg: float = 10.0, sample: int = 3) -> dict:
    segs = []                                   # (mark, idx, p, q, radius)
    for g in groups:
        for idx, inst in enumerate(g.instances):
            pts = g.placed_polyline(inst, arc_step_deg)
            for p, q in zip(pts, pts[1:]):
                if vlen(vsub(q, p)) > 1e-6:
                    segs.append((g.mark, idx, p, q, g.diameter / 2))
    grid: dict[tuple, list[int]] = defaultdict(list)
    for i, (_, _, p, q, r) in enumerate(segs):
        lo = [min(p[k], q[k]) - r for k in range(3)]
        hi = [max(p[k], q[k]) + r for k in range(3)]
        for ix in range(int(lo[0] // cell), int(hi[0] // cell) + 1):
            for iy in range(int(lo[1] // cell), int(hi[1] // cell) + 1):
                for iz in range(int(lo[2] // cell), int(hi[2] // cell) + 1):
                    grid[(ix, iy, iz)].append(i)
    seen, bars = set(), {}
    for members in grid.values():
        for ai in range(len(members)):
            for bi in range(ai + 1, len(members)):
                i, j = members[ai], members[bi]
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                m1, k1, p1, q1, r1 = segs[i]
                m2, k2, p2, q2, r2 = segs[j]
                if m1 == m2 and k1 == k2:
                    continue
                depth = (r1 + r2) - segment_distance(p1, q1, p2, q2)
                if depth > tol:
                    key = tuple(sorted(((m1, k1), (m2, k2))))
                    bars[key] = max(bars.get(key, 0.0), depth)
    by_pair: dict[str, dict] = {}
    for ((m1, k1), (m2, k2)), depth in bars.items():
        name = "-".join(sorted((m1, m2)))
        e = by_pair.setdefault(name, {"bar_pairs": 0, "max_overlap_mm": 0.0, "examples": []})
        e["bar_pairs"] += 1
        e["max_overlap_mm"] = round(max(e["max_overlap_mm"], depth), 1)
        if len(e["examples"]) < sample:
            e["examples"].append(f"{m1}#{k1 + 1} x {m2}#{k2 + 1} ({depth:.1f} mm)")
    return {"total_bar_pairs": len(bars), "by_mark_pair": by_pair, "segments": len(segs)}
