"""CLI: scad-engine --json examples/pilecap.json --out output"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .clash import find_clashes
from .draw import compose, write_dxf, write_svg
from .layout import build_groups
from .recap import build_recap, reconcile, write_recap
from .section2d import cut_section, default_cut_positions
from .step_audit import audit_file, format_report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scad-engine")
    ap.add_argument("--json", help="konfigurasi pile cap (JSON)")
    ap.add_argument("--out", default="output")
    ap.add_argument("--cut-x", type=float, help="posisi potongan melintang (default: kolom P5 terdekat tengah)")
    ap.add_argument("--cut-y", type=float, help="posisi potongan memanjang")
    ap.add_argument("--no-beyond", action="store_true", help="tanpa garis batang di belakang bidang potong")
    ap.add_argument("--step", choices=["full", "representative", "centerline"],
                    help="tulis STEP (butuh CadQuery); lod = full/representative/centerline")
    ap.add_argument("--audit", help="audit file STEP yang sudah ada, lalu selesai")
    args = ap.parse_args(argv)

    if args.audit:
        print(format_report(audit_file(args.audit)))
        return 0
    if not args.json:
        ap.error("--json wajib (kecuali --audit)")
    cfg = json.loads(Path(args.json).read_text(encoding="utf-8"))
    groups = build_groups(cfg)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pc = cfg["pilecap"]
    L, W, H = float(pc["length"]), float(pc["width"]), float(pc["height"])

    placed = step_counts = None
    if args.step:
        from . import cq_export
        name = "pilecap_rebar_centerline.step" if args.step == "centerline" else "pilecap_rebar_instanced.step"
        step_path = out / name
        if args.step == "centerline":
            placed = cq_export.export_centerline_step(groups, step_path)
        else:
            placed = cq_export.export_step(groups, step_path, lod=args.step, concrete=(L, W, H))
        rep = audit_file(step_path, expected_bars=sum(g.count for g in groups),
                         expected_protos=sum(len(g.protos) for g in groups))
        print(format_report(rep))
        step_counts = rep["instances_by_mark"] or None
        if args.step == "representative":
            placed = step_counts = None      # LOD sebagian: jangan dibandingkan dengan jumlah penuh

    recon = reconcile(groups, placed_3d=placed, step_counts=step_counts)
    clash = find_clashes(groups)
    paths = write_recap(groups, out, recon, clash=clash)
    pos = default_cut_positions(groups, L, W)
    trans = cut_section(groups, "x", args.cut_x if args.cut_x is not None else pos["x"])
    long = cut_section(groups, "y", args.cut_y if args.cut_y is not None else pos["y"])
    prims, layers = compose(L, W, H, trans, long, build_recap(groups), beyond=not args.no_beyond)
    paths["svg"] = write_svg(prims, layers, out / "pilecap_sections.svg")
    try:
        paths["dxf"] = write_dxf(prims, layers, out / "pilecap_sections.dxf")
    except ImportError as exc:
        print("DXF dilewati:", exc)

    for g in groups:
        print(f"{g.mark}: {g.count} batang")
    print("Rekonsiliasi:", "OK" if recon["ok"] else "ADA MISMATCH")
    for w in recon["warnings"]:
        print("  peringatan:", w)
    if clash["total_bar_pairs"]:
        print(f"  TABRAKAN: {clash['total_bar_pairs']} pasangan batang -> "
              + ", ".join(f"{k}={v['bar_pairs']}" for k, v in sorted(clash["by_mark_pair"].items())))
    else:
        print("  tabrakan: tidak ada")
    for s in (trans, long):
        if s.missing:
            print(f"  potongan {s.axis}={s.c:g}: mark TIDAK tampil -> {s.missing}")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    return 0 if recon["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
