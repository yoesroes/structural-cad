"""Validator dokumen project / element / shape_library."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from scad.issues import Issue
from scad.io.canonical import sha256_of

def _resolve_schema_path() -> Path:
    """Cari skema: data paket terinstal dulu, lalu tree sumber (repo/schemas)."""
    here = Path(__file__).resolve().parent  # .../scad
    candidates: list[Path] = [
        here / "data" / "scad.schema.json",  # wheel / pip install / editable
    ]
    # Tree sumber: core/scad → parents[2] = repo root
    try:
        candidates.append(here.parents[2] / "schemas" / "scad.schema.json")
    except IndexError:
        pass
    try:
        candidates.append(here.parents[1] / "schemas" / "scad.schema.json")
    except IndexError:
        pass
    # importlib.resources (Python 3.9+) jika paket terinstal tanpa file lepas
    try:
        from importlib import resources

        traj = resources.files("scad") / "data" / "scad.schema.json"
        with resources.as_file(traj) as fp:
            if fp.is_file():
                candidates.insert(0, Path(fp))
    except (ImportError, TypeError, FileNotFoundError, ModuleNotFoundError, AttributeError):
        pass
    seen: set[Path] = set()
    for c in candidates:
        try:
            c = c.resolve()
        except OSError:
            continue
        if c in seen:
            continue
        seen.add(c)
        if c.is_file():
            return c
    raise FileNotFoundError(
        "scad.schema.json tidak ditemukan. Coba: pip install -e . "
        "atau pastikan schemas/scad.schema.json ada di root repo "
        "(dan core/scad/data/ disalin lewat scripts/sync_schema.sh)."
    )


_SCHEMA_PATH: Path | None = None  # diisi lazy
_KIND_TO_DEF = {
    "project": "ProjectFile",
    "element": "ElementFile",
    "shape_library": "ShapeLibraryFile",
}

_schema_cache: dict[str, Any] | None = None


def _load_schema() -> dict[str, Any]:
    global _schema_cache, _SCHEMA_PATH
    if _schema_cache is None:
        _SCHEMA_PATH = _resolve_schema_path()
        _schema_cache = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _schema_cache


def _pointer_from_path(path) -> str:
    parts = [""]
    for p in path:
        if isinstance(p, int):
            parts.append(str(p))
        else:
            parts.append(str(p).replace("~", "~0").replace("/", "~1"))
    return "/".join(parts) if len(parts) > 1 else ""


def _schema_issues(doc: dict[str, Any]) -> list[Issue]:
    schema = _load_schema()
    kind = doc.get("kind")
    def_name = _KIND_TO_DEF.get(kind)
    if not def_name:
        return [
            Issue(
                level="error",
                code="SCHEMA",
                path="/kind",
                message=f"kind tidak dikenal: {kind!r}",
            )
        ]

    # Sub-skema + $defs agar $ref internal tetap resolve
    sub = {
        "$schema": schema.get("$schema"),
        "$ref": f"#/$defs/{def_name}",
        "$defs": schema["$defs"],
    }
    validator = Draft202012Validator(sub)
    seen: set[tuple[str, str]] = set()
    issues: list[Issue] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        ptr = _pointer_from_path(err.absolute_path)
        msg = f"Skema: {err.message}"
        key = (ptr, msg)
        if key in seen:
            continue
        seen.add(key)
        issues.append(
            Issue(level="error", code="SCHEMA", path=ptr or "/", message=msg)
        )
    issues.sort(key=lambda i: i.path)
    return issues


def _collect_rebars(definition: dict[str, Any]) -> list[dict[str, Any]]:
    return list(definition.get("rebars") or [])


def _check_id_dup_in_list(items: list[dict], path_prefix: str, issues: list[Issue]) -> None:
    seen: dict[str, int] = {}
    for i, item in enumerate(items):
        iid = item.get("id")
        if not isinstance(iid, str):
            continue
        if iid in seen:
            issues.append(
                Issue(
                    level="error",
                    code="ID_DUP",
                    path=f"{path_prefix}/{i}/id",
                    message=f"ID ganda: '{iid}'",
                )
            )
        else:
            seen[iid] = i


def _zone_rest_issues(zones: list[dict], path_prefix: str, issues: list[Issue]) -> None:
    rest_idxs = [i for i, z in enumerate(zones) if z.get("length") == "rest"]
    if len(rest_idxs) > 1:
        issues.append(
            Issue(
                level="error",
                code="ZONE_REST_POS",
                path=f"{path_prefix}/{rest_idxs[1]}/length",
                message="Lebih dari satu zona dengan length 'rest'",
            )
        )
        return
    if len(rest_idxs) == 1:
        ri = rest_idxs[0]
        side = zones[ri].get("side") or "below_cof"
        if side != "below_cof":
            issues.append(
                Issue(
                    level="error",
                    code="ZONE_REST_POS",
                    path=f"{path_prefix}/{ri}",
                    message="Zona 'rest' harus side below_cof",
                )
            )
            return
        for j in range(ri + 1, len(zones)):
            if (zones[j].get("side") or "below_cof") == "below_cof":
                issues.append(
                    Issue(
                        level="error",
                        code="ZONE_REST_POS",
                        path=f"{path_prefix}/{ri}",
                        message="Zona 'rest' harus zona below_cof terakhir",
                    )
                )
                break


def _pos_cycle_issues(rebars: list[dict], path_prefix: str, issues: list[Issue]) -> None:
    # graph: bar_id -> ref bar_id
    edges: dict[str, str] = {}
    id_to_idx = {r.get("id"): i for i, r in enumerate(rebars) if r.get("id")}
    for r in rebars:
        rid = r.get("id")
        pos = r.get("position") or {}
        if pos.get("ref") == "bar" and pos.get("bar") and rid:
            edges[str(rid)] = str(pos["bar"])

    def cycle_from(start: str) -> list[str] | None:
        seen: list[str] = []
        cur = start
        visiting: set[str] = set()
        while cur in edges:
            if cur in visiting:
                # cycle
                idx = seen.index(cur) if cur in seen else 0
                return seen[idx:] + [cur]
            visiting.add(cur)
            seen.append(cur)
            cur = edges[cur]
            if cur == start:
                return seen + [cur]
        return None

    reported: set[frozenset[str]] = set()
    for start in edges:
        cyc = cycle_from(start)
        if not cyc:
            continue
        key = frozenset(cyc)
        if key in reported:
            continue
        reported.add(key)
        chain = " → ".join(cyc)
        issues.append(
            Issue(
                level="error",
                code="POS_CYCLE",
                path=f"{path_prefix}/{id_to_idx.get(start, 0)}/position",
                message=f"Siklus acuan posisi: {chain}",
            )
        )


def _ref_missing_for_definition(
    definition: dict[str, Any],
    shapes: dict[str, Any],
    path_prefix: str,
    issues: list[Issue],
) -> None:
    zone_ids = {z.get("id") for z in definition.get("zones") or []}
    rebar_ids = {r.get("id") for r in definition.get("rebars") or []}
    for i, r in enumerate(definition.get("rebars") or []):
        # shape code
        shape = r.get("shape") or {}
        code = shape.get("code") if isinstance(shape, dict) else None
        if code and code not in shapes:
            issues.append(
                Issue(
                    level="error",
                    code="REF_MISSING",
                    path=f"{path_prefix}/rebars/{i}/shape",
                    message=f"Bentuk '{code}' tidak ada di shapes",
                )
            )
        # extent zones
        extent = r.get("extent") or {}
        for zi, zid in enumerate(extent.get("zones") or []):
            if zid not in zone_ids:
                issues.append(
                    Issue(
                        level="error",
                        code="REF_MISSING",
                        path=f"{path_prefix}/rebars/{i}/extent/zones/{zi}",
                        message=f"Zona '{zid}' tidak ada di definisi elemen",
                    )
                )
        # position bar
        pos = r.get("position") or {}
        if pos.get("ref") == "bar":
            bar = pos.get("bar")
            if bar not in rebar_ids:
                issues.append(
                    Issue(
                        level="error",
                        code="REF_MISSING",
                        path=f"{path_prefix}/rebars/{i}/position/bar",
                        message=f"Tulangan acuan '{bar}' tidak ada",
                    )
                )


def _cross_checks(doc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    kind = doc.get("kind")

    if kind == "element":
        definition = doc.get("definition") or {}
        shapes = doc.get("shapes") or {}
        _check_id_dup_in_list(
            definition.get("rebars") or [], "/definition/rebars", issues
        )
        _zone_rest_issues(definition.get("zones") or [], "/definition/zones", issues)
        _ref_missing_for_definition(definition, shapes, "/definition", issues)
        _pos_cycle_issues(definition.get("rebars") or [], "/definition/rebars", issues)

    elif kind == "project":
        groups = doc.get("groups") or []
        _check_id_dup_in_list(groups, "/groups", issues)
        shapes = doc.get("shapes") or {}
        all_pile_ids: list[tuple[str, str]] = []
        for gi, g in enumerate(groups):
            instances = g.get("instances") or []
            _check_id_dup_in_list(instances, f"/groups/{gi}/instances", issues)
            for inst in instances:
                if inst.get("id"):
                    all_pile_ids.append((str(inst["id"]), f"/groups/{gi}"))
            # dup across project
            definition = (g.get("definition") or {}).get("data") or {}
            _check_id_dup_in_list(
                definition.get("rebars") or [],
                f"/groups/{gi}/definition/data/rebars",
                issues,
            )
            _zone_rest_issues(
                definition.get("zones") or [],
                f"/groups/{gi}/definition/data/zones",
                issues,
            )
            _ref_missing_for_definition(
                definition, shapes, f"/groups/{gi}/definition/data", issues
            )
            _pos_cycle_issues(
                definition.get("rebars") or [],
                f"/groups/{gi}/definition/data/rebars",
                issues,
            )
            # HASH_DIFF
            source = (g.get("definition") or {}).get("source")
            data = (g.get("definition") or {}).get("data")
            if source is not None and data is not None:
                expected = source.get("hash")
                if expected:
                    actual = sha256_of(data)
                    if actual != expected:
                        issues.append(
                            Issue(
                                level="info",
                                code="HASH_DIFF",
                                path=f"/groups/{gi}/definition/source/hash",
                                message=(
                                    f"Hash definisi berbeda dari sumber "
                                    f"(tersimpan {expected}, hitung {actual})"
                                ),
                            )
                        )

        # pile id unique across project
        seen_piles: dict[str, str] = {}
        for pid, path in all_pile_ids:
            if pid in seen_piles:
                issues.append(
                    Issue(
                        level="error",
                        code="ID_DUP",
                        path=path,
                        message=f"ID pile ganda dalam project: '{pid}'",
                    )
                )
            else:
                seen_piles[pid] = path

    elif kind == "shape_library":
        shapes = doc.get("shapes") or {}
        # shapes may be dict keyed by code
        if isinstance(shapes, list):
            _check_id_dup_in_list(shapes, "/shapes", issues)

    return issues


def validate_document(doc: dict[str, Any]) -> list[Issue]:
    """Validasi skema lalu aturan lintas-referensi. Mengembalikan daftar Issue."""
    if not isinstance(doc, dict):
        return [
            Issue(
                level="error",
                code="SCHEMA",
                path="/",
                message="Dokumen harus objek JSON",
            )
        ]
    issues = _schema_issues(doc)
    if any(i.level == "error" for i in issues):
        return issues
    issues.extend(_cross_checks(doc))
    # urutkan: error dulu, lalu path
    level_order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: (level_order.get(i.level, 9), i.path, i.code))
    return issues
