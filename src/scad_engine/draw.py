"""Penyusunan gambar 2D (primitif sederhana) + penulis SVG dan DXF.

Primitif dihasilkan dari SectionResult dan tabel rekap yang SAMA dengan yang dipakai
untuk pemeriksaan jumlah, sehingga yang tergambar = yang terhitung.
DXF ditulis dengan ezdxf (import malas). Koordinat model dalam mm, skala 1:1;
layout kertas (viewport, kop gambar) belum termasuk.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable

from .section2d import SectionResult

MARK_COLOR = {"P1": 1, "P2": 2, "P3": 5, "P4": 4, "P5": 3, "P6": 6}
_CSS = {1: "#d62728", 2: "#b8860b", 3: "#2ca02c", 4: "#17becf", 5: "#1f4fd8", 6: "#c71585", 7: "#222222", 8: "#999999"}


@dataclass
class Prim:
    kind: str                       # 'line' | 'circle' | 'text' | 'poly'
    layer: str
    pts: tuple                      # line: (p0,p1) | circle: (c,) | text: (p,) | poly: (p0..pn)
    r: float = 0.0
    text: str = ""
    height: float = 0.0
    thin: bool = False


def _layer_for(marks: set[str]) -> str:
    return "REBAR_" + "_".join(sorted(marks))


def layer_colors(marks: Iterable[str]) -> dict[str, int]:
    out = {"CONCRETE": 8, "DIM": 7, "TEXT": 7, "TABLE": 7}
    for m in marks:
        out[f"REBAR_{m}"] = MARK_COLOR.get(m, 7)
    return out


def _section_prims(sec: SectionResult, ox: float, oy: float, W: float, H: float,
                   title: str, th: float, beyond: bool, layers: dict[str, int]) -> list[Prim]:
    P: list[Prim] = []
    P.append(Prim("poly", "CONCRETE", ((ox, oy), (ox + W, oy), (ox + W, oy + H), (ox, oy + H), (ox, oy))))
    for (h, z, d), v in sec.dots.items():
        lay = _layer_for(v["marks"]) if len(v["marks"]) > 1 else f"REBAR_{next(iter(v['marks']))}"
        layers.setdefault(lay, MARK_COLOR.get(sorted(v["marks"])[0], 7))
        P.append(Prim("circle", lay, ((ox + h, oy + z),), r=d / 2))
    for (h0, z0, h1, z1), v in sec.lines.items():
        if v["kind"] == "beyond" and not beyond:
            continue
        lay = _layer_for(v["marks"]) if len(v["marks"]) > 1 else f"REBAR_{next(iter(v['marks']))}"
        layers.setdefault(lay, MARK_COLOR.get(sorted(v["marks"])[0], 7))
        P.append(Prim("line", lay, ((ox + h0, oy + z0), (ox + h1, oy + z1)), thin=(v["kind"] == "beyond")))
    # judul + dimensi total (garis ekstensi + garis dimensi + teks)
    P.append(Prim("text", "TEXT", ((ox, oy + H + 2.2 * th),), text=title, height=1.5 * th))
    yd = oy - 3 * th
    for x in (ox, ox + W):
        P.append(Prim("line", "DIM", ((x, oy), (x, yd - th))))
    P.append(Prim("line", "DIM", ((ox, yd), (ox + W, yd))))
    P.append(Prim("text", "DIM", ((ox + W / 2 - 2 * th, yd + 0.4 * th),), text=f"{W:g}", height=th))
    xd = ox + W + 3 * th
    for y in (oy, oy + H):
        P.append(Prim("line", "DIM", ((ox + W, y), (xd + th, y))))
    P.append(Prim("line", "DIM", ((xd, oy), (xd, oy + H))))
    P.append(Prim("text", "DIM", ((xd + 0.4 * th, oy + H / 2),), text=f"{H:g}", height=th))
    # keterangan jumlah titik/garis per mark pada potongan ini
    y = oy - 7 * th
    P.append(Prim("text", "TEXT", ((ox, y),), text="Keterangan (jumlah batang tergambar):", height=th))
    for m, st in sec.stats.items():
        y -= 1.6 * th
        P.append(Prim("text", "TEXT", ((ox, y),), height=th, text=(
            f"{m}: titik potong {sec.dot_count(m)} | di bidang {st['inplane']} | di belakang {st['beyond']} "
            f"(dari {st['instances']} batang)")))
    if sec.missing:
        y -= 1.6 * th
        P.append(Prim("text", "TEXT", ((ox, y),), height=th, text="TIDAK TAMPIL: " + ", ".join(sec.missing)))
    return P


def _table_prims(rows: list[dict], ox: float, oy: float, th: float) -> list[Prim]:
    cols = [("MARK", 0), ("Ø", 5), ("JUMLAH", 9), ("PJG POTONG (mm)", 17), ("TOTAL (m)", 31), ("BERAT (kg)", 40)]
    P: list[Prim] = [Prim("text", "TABLE", ((ox, oy),), text="REKAPITULASI TULANGAN TERPASANG", height=1.5 * th)]
    y = oy - 2.4 * th
    for name, off in cols:
        P.append(Prim("text", "TABLE", ((ox + off * th * 1.2, y),), text=name, height=th))
    width = 50 * th * 1.2
    P.append(Prim("line", "TABLE", ((ox, y - 0.4 * th), (ox + width, y - 0.4 * th))))
    for r in rows:
        y -= 1.7 * th
        vals = [r["mark"], f"{r['diameter_mm']:g}", str(r["count"]), f"{r['cut_length_mm']:g}",
                f"{r['total_length_m']:.2f}", f"{r['weight_kg']:.1f}"]
        for (name, off), v in zip(cols, vals):
            P.append(Prim("text", "TABLE", ((ox + off * th * 1.2, y),), text=v, height=th))
    y -= 1.2 * th
    P.append(Prim("line", "TABLE", ((ox, y), (ox + width, y))))
    y -= 1.7 * th
    P.append(Prim("text", "TABLE", ((ox, y),), height=th, text=(
        f"JUMLAH: {sum(r['count'] for r in rows)} batang | {sum(r['total_length_m'] for r in rows):.2f} m | "
        f"{sum(r['weight_kg'] for r in rows):.1f} kg")))
    return P


def compose(L: float, W: float, H: float, trans: SectionResult, long: SectionResult,
            rows: list[dict], gap: float = 1500.0, th: float = 120.0, beyond: bool = True
            ) -> tuple[list[Prim], dict[str, int]]:
    layers = layer_colors({m for s in (trans, long) for m in s.stats})
    prims = _section_prims(trans, 0.0, 0.0, W, H, f"POTONGAN TRANSVERSAL (x = {trans.c:g})  SKALA 1:1",
                           th, beyond, layers)
    prims += _section_prims(long, W + gap, 0.0, L, H, f"POTONGAN LONGITUDINAL (y = {long.c:g})  SKALA 1:1",
                            th, beyond, layers)
    prims += _table_prims(rows, 0.0, -17 * th, th)
    return prims, layers


def bounds(prims: list[Prim]) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for p in prims:
        if p.kind == "circle":
            (cx, cy), = p.pts
            xs += [cx - p.r, cx + p.r]; ys += [cy - p.r, cy + p.r]
        elif p.kind == "text":
            (x, y), = p.pts
            xs += [x, x + 0.6 * p.height * max(1, len(p.text))]; ys += [y, y + p.height]
        else:
            for x, y in p.pts:
                xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def write_svg(prims: list[Prim], layers: dict[str, int], path: Path, width_px: int = 1800) -> Path:
    x0, y0, x1, y1 = bounds(prims)
    pad = 0.02 * max(x1 - x0, y1 - y0)
    vx, vy, vw, vh = x0 - pad, -(y1 + pad), (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{max(1, round(width_px * vh / vw))}" '
           f'viewBox="{vx:.1f} {vy:.1f} {vw:.1f} {vh:.1f}">',
           '<style>.l{fill:none;vector-effect:non-scaling-stroke;stroke-width:1}'
           '.t{fill:none;vector-effect:non-scaling-stroke;stroke-width:.4}</style>',
           f'<rect x="{vx:.1f}" y="{vy:.1f}" width="{vw:.1f}" height="{vh:.1f}" fill="white"/>']
    for p in prims:
        col = _CSS.get(layers.get(p.layer, 7), "#222")
        if p.kind == "line":
            (a, b) = p.pts
            out.append(f'<line class="{"t" if p.thin else "l"}" stroke="{col}" x1="{a[0]:.2f}" y1="{-a[1]:.2f}" '
                       f'x2="{b[0]:.2f}" y2="{-b[1]:.2f}"/>')
        elif p.kind == "poly":
            out.append('<polyline class="l" stroke="%s" points="%s"/>' % (
                col, " ".join(f"{x:.2f},{-y:.2f}" for x, y in p.pts)))
        elif p.kind == "circle":
            (c,) = p.pts
            out.append(f'<circle fill="{col}" stroke="{col}" stroke-width="0.5" cx="{c[0]:.2f}" cy="{-c[1]:.2f}" r="{p.r:.2f}"/>')
        elif p.kind == "text":
            (a,) = p.pts
            out.append(f'<text x="{a[0]:.2f}" y="{-a[1]:.2f}" font-size="{p.height:.1f}" font-family="sans-serif" '
                       f'fill="{col}">{escape(p.text)}</text>')
    out.append("</svg>")
    Path(path).write_text("\n".join(out), encoding="utf-8")
    return Path(path)


def write_dxf(prims: list[Prim], layers: dict[str, int], path: Path) -> Path:
    try:
        import ezdxf
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Ekspor DXF butuh ezdxf: pip install ezdxf") from exc
    doc = ezdxf.new("R2013")
    doc.units = ezdxf.units.MM
    for name, color in layers.items():
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": color})
    msp = doc.modelspace()
    for p in prims:
        attr = {"layer": p.layer}
        if p.kind == "line":
            msp.add_line(p.pts[0], p.pts[1], dxfattribs=attr)
        elif p.kind == "poly":
            msp.add_lwpolyline(list(p.pts), dxfattribs=attr)
        elif p.kind == "circle":
            msp.add_circle(p.pts[0], p.r, dxfattribs=attr)
        elif p.kind == "text":
            msp.add_text(p.text, height=p.height, dxfattribs={**attr, "insert": p.pts[0]})
    doc.saveas(str(path))
    return Path(path)
