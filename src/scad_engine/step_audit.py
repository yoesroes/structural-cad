"""Audit file STEP (hanya teks, tanpa CadQuery): ukuran, jumlah entitas, indikasi instancing.

Tujuan: menjawab "kenapa STEP besar?" dengan angka, dan memeriksa ISI file:
  - jumlah MANIFOLD_SOLID_BREP vs jumlah NEXT_ASSEMBLY_USAGE_OCCURRENCE
    (instancing berhasil bila solid ~ jumlah proto, sedangkan penempatan ~ jumlah batang)
  - jumlah batang per mark yang tercatat di file (dari nama instance)
Penamaan instance bergantung pada pembuat file; hitungan per mark adalah heuristik
dan akan kosong bila nama tidak mengikuti pola 'P3_0001'.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ENTITY_RE = re.compile(r"#\d+\s*=\s*([A-Z][A-Z0-9_]*)\s*\(")
INTERESTING = ("MANIFOLD_SOLID_BREP", "ADVANCED_FACE", "CYLINDRICAL_SURFACE", "TOROIDAL_SURFACE",
               "PLANE", "B_SPLINE_SURFACE_WITH_KNOTS", "B_SPLINE_CURVE_WITH_KNOTS", "SURFACE_OF_REVOLUTION",
               "SURFACE_OF_LINEAR_EXTRUSION", "PRODUCT", "NEXT_ASSEMBLY_USAGE_OCCURRENCE")
NAUO_RE = re.compile(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'([^']*)'\s*,\s*'([^']*)'")
PRODUCT_RE = re.compile(r"#\d+\s*=\s*PRODUCT\s*\(\s*'([^']*)'")
MARK_NAME_RE = re.compile(r"^(P\d+)[_.\-]\d+$")


def audit_text(text: str, size_bytes: int | None = None, expected_bars: int | None = None,
               expected_protos: int | None = None) -> dict:
    counts = Counter(ENTITY_RE.findall(text))
    out = {"size_bytes": size_bytes if size_bytes is not None else len(text.encode("utf-8")),
           "entities_total": sum(counts.values()),
           "counts": {k: counts.get(k, 0) for k in INTERESTING}}
    solids, nauo = counts.get("MANIFOLD_SOLID_BREP", 0), counts.get("NEXT_ASSEMBLY_USAGE_OCCURRENCE", 0)
    out["bytes_per_solid"] = round(out["size_bytes"] / solids) if solids else None
    verdict = "tidak dapat ditentukan"
    if expected_bars and expected_protos:
        if nauo >= 0.9 * expected_bars and solids <= 4 * expected_protos + 10:
            verdict = "geometri DIBAGI antar instance (instancing berhasil)"
        elif solids >= 0.9 * expected_bars:
            verdict = "geometri DUPLIKAT per batang (instancing tidak terjadi)"
    out["instancing_verdict"] = verdict

    names = [m.group(2) for m in NAUO_RE.finditer(text)] or [m.group(1) for m in PRODUCT_RE.finditer(text)]
    per_mark: Counter = Counter()
    for n in set(names):
        m = MARK_NAME_RE.match(n)
        if m:
            per_mark[m.group(1)] += 1
    out["instances_by_mark"] = dict(per_mark)
    return out


def audit_file(path: str | Path, **kw) -> dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return audit_text(text, size_bytes=p.stat().st_size, **kw)


def format_report(a: dict) -> str:
    lines = [f"Ukuran file       : {a['size_bytes'] / 1e6:.2f} MB ({a['size_bytes']} byte)",
             f"Total entitas     : {a['entities_total']}"]
    for k, v in a["counts"].items():
        if v:
            lines.append(f"  {k:<30}{v}")
    if a["bytes_per_solid"]:
        lines.append(f"Byte per solid    : {a['bytes_per_solid']}")
    lines.append(f"Instancing        : {a['instancing_verdict']}")
    if a["instances_by_mark"]:
        lines.append("Instance per mark : " + ", ".join(f"{k}={v}" for k, v in sorted(a["instances_by_mark"].items())))
    return "\n".join(lines)
