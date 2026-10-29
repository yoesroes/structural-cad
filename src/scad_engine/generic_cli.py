"""CLI untuk satu struktur dan satu batang dari konfigurasi JSON."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from .generic import build_bar_centerline, place_bar, structure_from_dict, export_generic_step


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Structural CAD generic: satu struktur + satu tulangan")
    ap.add_argument("--json", required=True, help="file konfigurasi JSON")
    ap.add_argument("--out", help="direktori output; default dari JSON")
    ap.add_argument("--no-step", action="store_true", help="jangan ekspor STEP")
    ns = ap.parse_args(argv)
    cfg = json.loads(Path(ns.json).read_text(encoding="utf-8"))
    structure = structure_from_dict(cfg["structure"])
    bcfg = cfg["bar"]
    bar = build_bar_centerline(bcfg["shape"], bcfg["dimensions"], bcfg["diameter"], bcfg.get("bend_radius", 0))
    placed = place_bar(structure, bar, bcfg.get("position_local", (0,0,0)), bcfg.get("rotation_deg", (0,0,0)))
    outdir = Path(ns.out or cfg.get("output", {}).get("directory", "output/generic"))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "generic_model.json").write_text(json.dumps({"units": cfg.get("units", "mm"), "structure": cfg["structure"], "bar_definition": bar, "placed_bar": placed}, indent=2), encoding="utf-8")
    if cfg.get("output", {}).get("step", True) and not ns.no_step:
        export_generic_step(structure, [placed], str(outdir / "generic_model.step"))
    print(f"Output: {outdir.resolve()}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
