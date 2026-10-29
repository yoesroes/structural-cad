"""Rekapitulasi tulangan terpasang + rekonsiliasi jumlah.

Semua angka diturunkan dari BarGroup yang sama dengan yang dipakai untuk 3D dan
gambar 2D. Rekonsiliasi membandingkan beberapa jalur HITUNG yang berbeda:
  1. rumus tertutup dari parameter          (expected_count)
  2. enumerasi instance di model             (count)
  3. jumlah penempatan di 3D / isi file STEP (opsional, dari builder / step_audit)
Bila ada yang berbeda, status = MISMATCH dan laporan menyebut mark-nya.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from .model import BarGroup

STEEL_KG_PER_M_FACTOR = 162.2        # berat per meter = d^2 / 162,2 (d dalam mm)


def unit_weight_kg_per_m(d_mm: float) -> float:
    return d_mm * d_mm / STEEL_KG_PER_M_FACTOR


def build_recap(groups: Iterable[BarGroup]) -> list[dict]:
    rows: list[dict] = []
    for g in groups:
        by_len: dict[float, list] = defaultdict(list)
        for inst in g.instances:
            by_len[round(g.protos[inst.proto].path_length(), 1)].append(inst)
        for plen, insts in sorted(by_len.items()):
            cut = plen + g.lap_mm
            n = len(insts)
            rows.append({
                "mark": g.mark,
                "description": g.description,
                "diameter_mm": g.diameter,
                "spacing_mm": g.spacing,
                "count": n,
                "path_length_mm": plen,
                "lap_mm": g.lap_mm,
                "cut_length_mm": round(cut, 1),
                "total_length_m": round(n * cut / 1000.0, 3),
                "weight_kg": round(n * cut / 1000.0 * unit_weight_kg_per_m(g.diameter), 1),
                "breakdown": dict(Counter(i.tag for i in insts if i.tag)),
                "notes": g.notes,
            })
    return rows


def reconcile(groups: Iterable[BarGroup], placed_3d: dict[str, int] | None = None,
              step_counts: dict[str, int] | None = None) -> dict:
    """Bandingkan jumlah dari beberapa jalur hitung. Mengembalikan {'ok': bool, 'checks': [...], 'warnings': [...]}."""
    checks, warnings = [], []
    for g in groups:
        entry = {"mark": g.mark, "formula": g.expected_count, "model": g.count}
        status = "OK"
        if g.expected_count is not None and g.expected_count != g.count:
            status = "MISMATCH"
        if placed_3d is not None:
            entry["placed_3d"] = placed_3d.get(g.mark, 0)
            if entry["placed_3d"] != g.count:
                status = "MISMATCH"
        if step_counts is not None:
            entry["in_step_file"] = step_counts.get(g.mark, 0)
            if entry["in_step_file"] != g.count:
                status = "MISMATCH"
        entry["status"] = status
        checks.append(entry)
        gap = g.layout.get("end_gap")
        if gap is not None and gap > 0.5:
            warnings.append(
                f"{g.mark}: batang terakhir berhenti {gap:.1f} mm sebelum garis selimut seberang "
                f"(spasi {g.spacing:g} mm) -> susunan tidak simetris; periksa apakah disengaja")
    return {"ok": all(c["status"] == "OK" for c in checks), "checks": checks, "warnings": warnings}


def write_recap(groups: list[BarGroup], out_dir: Path, recon: dict | None = None,
                basename: str = "pilecap", clash: dict | None = None) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_recap(groups)
    recon = recon if recon is not None else reconcile(groups)
    paths = {}

    # CSV: kolom diselaraskan dengan BBS bored pile (mark, description, count, path/lap/cut)
    p = out_dir / f"{basename}_recap.csv"
    cols = ["mark", "description", "diameter_mm", "spacing_mm", "count", "path_length_mm",
            "lap_mm", "cut_length_mm", "total_length_m", "weight_kg"]
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    paths["csv"] = p

    p = out_dir / f"{basename}_recap.json"
    p.write_text(json.dumps({"rows": rows, "reconciliation": recon, "clash": clash}, indent=2, ensure_ascii=False),
                 encoding="utf-8")
    paths["json"] = p

    tot_n = sum(r["count"] for r in rows)
    tot_len = sum(r["total_length_m"] for r in rows)
    tot_w = sum(r["weight_kg"] for r in rows)
    md = ["# Rekapitulasi tulangan terpasang", "",
          "| Mark | Ø (mm) | Jumlah | Panjang jalur (mm) | Lewatan (mm) | Panjang potong (mm) | Total (m) | Berat (kg) |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        md.append(f"| {r['mark']} | {r['diameter_mm']:g} | {r['count']} | {r['path_length_mm']:g} | "
                  f"{r['lap_mm']:g} | {r['cut_length_mm']:g} | {r['total_length_m']:.2f} | {r['weight_kg']:.1f} |")
    md.append(f"| **Σ** | | **{tot_n}** | | | | **{tot_len:.2f}** | **{tot_w:.1f}** |")
    md += ["", "Rincian per bagian (tag):"]
    for r in rows:
        if r["breakdown"]:
            md.append(f"- {r['mark']}: " + ", ".join(f"{k} = {v}" for k, v in sorted(r["breakdown"].items())))
    md += ["", "## Rekonsiliasi jumlah", "",
           "| Mark | Rumus | Model | 3D | File STEP | Status |", "|---|---:|---:|---:|---:|---|"]
    for c in recon["checks"]:
        md.append(f"| {c['mark']} | {c['formula']} | {c['model']} | {c.get('placed_3d', '-')} | "
                  f"{c.get('in_step_file', '-')} | {c['status']} |")
    if recon["warnings"]:
        md += ["", "Peringatan:"] + [f"- {w}" for w in recon["warnings"]]
    if clash is not None:
        md += ["", "## Pemeriksaan tabrakan antar batang", ""]
        if clash["total_bar_pairs"] == 0:
            md.append("Tidak ada pasangan batang yang bertabrakan (bersentuhan tepat tidak dihitung).")
        else:
            md.append(f"{clash['total_bar_pairs']} pasangan batang bertabrakan:")
            for k, v in sorted(clash["by_mark_pair"].items()):
                md.append(f"- {k}: {v['bar_pairs']} pasangan, tumpang tindih maks {v['max_overlap_mm']} mm "
                          f"(contoh: {'; '.join(v['examples'])})")
    md += ["", "Catatan: panjang = panjang jalur sumbu batang (termasuk busur kait); belum memuat "
               "lewatan, pembulatan potong, atau toleransi fabrikasi."]
    p = out_dir / f"{basename}_recap.md"
    p.write_text("\n".join(md) + "\n", encoding="utf-8")
    paths["md"] = p
    return paths
