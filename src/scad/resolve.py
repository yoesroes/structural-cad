"""Selesaikan project: kedalaman, zona per pile."""
from __future__ import annotations

from typing import Any

from scad.issues import Issue
from scad.validate import validate_document
from scad.zones import ZoneError, resolve_zones


def resolve_project(doc: dict[str, Any]) -> dict[str, Any]:
    """Kembalikan ResolveResponse: groups[].piles[] + issues."""
    issues = [i for i in validate_document(doc) if i.level == "error"]
    out_groups: list[dict[str, Any]] = []

    if doc.get("kind") != "project":
        return {
            "groups": [],
            "issues": [
                {
                    "level": "error",
                    "code": "SCHEMA",
                    "path": "/kind",
                    "message": "Dokumen harus kind=project",
                }
            ],
        }

    for gi, g in enumerate(doc.get("groups") or []):
        definition = (g.get("definition") or {}).get("data") or {}
        zones_def = definition.get("zones") or []
        defaults = (g.get("defaults") or {}).get("params") or {}
        base_depth = defaults.get("depth_below_cof")
        if base_depth is None:
            base_depth = (definition.get("params") or {}).get("depth_below_cof")

        piles: list[dict[str, Any]] = []
        for ii, inst in enumerate(g.get("instances") or []):
            depth = base_depth
            zone_lengths = None
            overridden: list[str] = []
            ovr = inst.get("overrides") or {}
            if ovr.get("params") and "depth_below_cof" in ovr["params"]:
                depth = ovr["params"]["depth_below_cof"]
                overridden.append("depth_below_cof")
            if ovr.get("zone_lengths"):
                zone_lengths = ovr["zone_lengths"]
                for zid in zone_lengths:
                    overridden.append(f"zone:{zid}")

            pile_issues: list[dict[str, Any]] = []
            zones_out: list[dict[str, Any]] = []
            try:
                if depth is None:
                    raise ZoneError(
                        "ZONE_DEPTH_SHORT",
                        f"Pile {inst.get('id')}: depth_below_cof tidak tersedia",
                    )
                resolved = resolve_zones(zones_def, float(depth), zone_lengths)
                zones_out = [
                    {
                        "id": z.id,
                        "side": z.side,
                        "length": z.length,
                        "z_top": z.z_top,
                        "z_bottom": z.z_bottom,
                    }
                    for z in resolved
                ]
            except ZoneError as e:
                pile_issues.append(
                    {
                        "level": "error",
                        "code": e.code,
                        "path": f"/groups/{gi}/instances/{ii}",
                        "message": str(e),
                    }
                )

            piles.append(
                {
                    "id": inst.get("id"),
                    "x": inst.get("x"),
                    "y": inst.get("y"),
                    "depth_below_cof": depth,
                    "overridden": overridden,
                    "zones": zones_out,
                }
            )
            issues.extend(pile_issues)

        out_groups.append({"id": g.get("id"), "piles": piles})

    # Serialize Issue objects
    ser_issues = []
    for i in issues:
        if isinstance(i, Issue):
            ser_issues.append(
                {"level": i.level, "code": i.code, "path": i.path, "message": i.message}
            )
        elif isinstance(i, dict):
            ser_issues.append(i)

    return {"groups": out_groups, "issues": ser_issues}