"""Potongan 2D yang dihitung EKSAK dari model tulangan (bukan sketsa terpisah).

Untuk setiap instance batang, jalur sumbunya (polyline, busur disampel) dipotong
dengan bidang potong:
  - batang yang MENEMBUS bidang        -> titik (lingkaran berdiameter batang)
  - segmen yang TERLETAK di bidang      -> garis (in-plane)
  - segmen di belakang bidang (terlihat)-> garis (beyond), diproyeksikan
Hasil diduplikasi (batang berbeda yang berimpit di proyeksi digabung, mark-nya
dicatat semua), jadi gambar tidak berisi ratusan garis identik tetapi tidak ada
mark yang hilang. Laporan kelengkapan menyebut mark yang TIDAK tampil.

Konvensi arah pandang:
  axis='x' : potongan melintang pada x=c, dilihat dari +X ke arah -X, sumbu datar = Y.
             Bagian yang dipertahankan: x <= c.
  axis='y' : potongan memanjang pada y=c, dilihat dari -Y ke arah +Y, sumbu datar = X.
             Bagian yang dipertahankan: y >= c.
Sumbu tegak = Z di keduanya.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .model import BarGroup

R1 = 1  # presisi dedup (0,1 mm)


@dataclass
class SectionResult:
    axis: str
    c: float
    dots: dict = field(default_factory=dict)     # (h, z, dia) -> {"marks": set, "n": int}
    lines: dict = field(default_factory=dict)    # (h0, z0, h1, z1) -> {"marks": set, "n": int, "kind": str}
    stats: dict = field(default_factory=dict)    # mark -> {...}
    missing: list = field(default_factory=list)

    def dot_count(self, mark: str) -> int:
        """Jumlah titik potong (sebelum digabung) milik mark ini."""
        return sum(v["by_mark"].get(mark, 0) for v in self.dots.values())

    def marks_drawn(self) -> set[str]:
        out: set[str] = set()
        for v in list(self.dots.values()) + list(self.lines.values()):
            out |= v["marks"]
        return out


def _depth(coord: float, c: float, axis: str) -> float:
    """Koordinat kedalaman: >= 0 berarti bagian yang dipertahankan."""
    return (c - coord) if axis == "x" else (coord - c)


def cut_section(groups: Iterable[BarGroup], axis: str, c: float, tol: float = 0.5) -> SectionResult:
    if axis not in ("x", "y"):
        raise ValueError("axis harus 'x' atau 'y'")
    ai = 0 if axis == "x" else 1
    hi = 1 if axis == "x" else 0                # indeks sumbu datar pada tampilan
    res = SectionResult(axis, c)
    groups = list(groups)

    def add_dot(h, z, d, mark):
        k = (round(h, R1), round(z, R1), d)
        e = res.dots.setdefault(k, {"marks": set(), "n": 0, "by_mark": {}})
        e["marks"].add(mark)
        e["n"] += 1
        e["by_mark"][mark] = e["by_mark"].get(mark, 0) + 1

    def add_line(p, q, mark, kind):
        a, b = (round(p[0], R1), round(p[1], R1)), (round(q[0], R1), round(q[1], R1))
        if a == b:
            return False
        k = (a + b) if a <= b else (b + a)
        e = res.lines.setdefault(k, {"marks": set(), "n": 0, "kind": kind})
        e["marks"].add(mark)
        e["n"] += 1
        if kind == "inplane":
            e["kind"] = "inplane"
        return True

    for g in groups:
        st = {"instances": g.count, "cut": 0, "inplane": 0, "beyond": 0, "end_on": 0}
        for inst in g.instances:
            pts = g.placed_polyline(inst)
            was_cut = was_in = was_beyond = False
            for p, q in zip(pts, pts[1:]):
                wp, wq = _depth(p[ai], c, axis), _depth(q[ai], c, axis)
                pp, qq = (p[hi], p[2]), (q[hi], q[2])
                if abs(wp) <= tol and abs(wq) <= tol:
                    if add_line(pp, qq, g.mark, "inplane"):
                        was_in = True
                elif wp * wq < 0 and abs(wp) > tol and abs(wq) > tol:       # menembus bidang
                    t = wp / (wp - wq)
                    ih = p[hi] + t * (q[hi] - p[hi])
                    iz = p[2] + t * (q[2] - p[2])
                    add_dot(ih, iz, g.diameter, g.mark)
                    was_cut = True
                    keep = pp if wp > 0 else qq                              # sisi yang dipertahankan
                    if add_line((ih, iz), keep, g.mark, "beyond"):
                        was_beyond = True
                elif wp >= -tol and wq >= -tol:                              # seluruhnya di belakang bidang
                    if add_line(pp, qq, g.mark, "beyond"):
                        was_beyond = True
                    elif abs(wp) > tol or abs(wq) > tol:
                        st["end_on"] += 1                                    # tegak lurus, tampak sbg titik
            st["cut"] += was_cut
            st["inplane"] += was_in
            st["beyond"] += was_beyond
        res.stats[g.mark] = st

    drawn = res.marks_drawn()
    res.missing = [g.mark for g in groups if g.mark not in drawn]
    return res


def default_cut_positions(groups: Iterable[BarGroup], L: float, W: float) -> dict[str, float]:
    """Posisi potong bawaan: tengah pile cap, dipindah ke kolom/baris pengikat P5 terdekat
    supaya P5 ikut terletak di bidang potong."""
    cx, cy = L / 2, W / 2
    for g in groups:
        if g.mark == "P5" and g.layout.get("xs"):
            cx = min(g.layout["xs"], key=lambda x: abs(x - L / 2))
            cy = min(g.layout["ys"], key=lambda y: abs(y - W / 2))
    return {"x": cx, "y": cy}
