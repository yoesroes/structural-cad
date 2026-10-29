"""Operasi berkas project/elemen — murni (tanpa HTTP), path aman di bawah workspace."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scad.io.canonical import sha256_of
from scad.io.files import load_document, save_document
from scad.validate import validate_document

MAX_FILE_BYTES = 5 * 1024 * 1024
ALLOWED_SUFFIXES = frozenset({".project.json", ".elem.json", ".shapes.json"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_under_workspace(workspace: Path, rel_or_abs: str | Path, *, must_exist: bool = False) -> Path:
    """Resolve path; wajib di dalam workspace. ValueError bila di luar / tidak valid."""
    workspace = workspace.resolve()
    raw = Path(rel_or_abs)
    if raw.is_absolute():
        target = raw.resolve()
    else:
        target = (workspace / raw).resolve()
    try:
        if not target.is_relative_to(workspace):
            raise ValueError(f"Path di luar workspace: {rel_or_abs}")
    except AttributeError:
        try:
            target.relative_to(workspace)
        except ValueError as e:
            raise ValueError(f"Path di luar workspace: {rel_or_abs}") from e
    if must_exist and not target.is_file():
        raise ValueError(f"Berkas tidak ditemukan: {rel_or_abs}")
    return target


def check_suffix(path: Path, allowed: set[str] | frozenset[str] = ALLOWED_SUFFIXES) -> None:
    name = path.name
    ok = any(name.endswith(s) for s in allowed)
    if not ok:
        raise ValueError(
            f"Ekstensi tidak diizinkan untuk '{name}'. "
            f"Gunakan: {', '.join(sorted(allowed))}"
        )


def check_size(path: Path) -> None:
    if path.is_file() and path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"Berkas terlalu besar (maks {MAX_FILE_BYTES // (1024*1024)} MB)")


def new_project(project_id: str, name: str) -> dict[str, Any]:
    """Dokumen project v1 kosong yang valid minimal."""
    doc = {
        "kind": "project",
        "schema_version": 1,
        "project": {
            "id": project_id,
            "name": name,
            "datum": {"cof_elevation": 0},
        },
        "settings": {
            "cover_ref": "surface",
            "rules": {"min_clear_spacing": 75},
        },
        "materials": {
            "concrete": {"grade": "fc30", "type": "readymix"},
            "steel": {"grade": "fy420", "type": "ulir"},
        },
        "shapes": {},
        "groups": [],
    }
    errors = [i for i in validate_document(doc) if i.level == "error"]
    if errors:
        raise ValueError(
            "Project baru tidak valid: "
            + "; ".join(f"{i.path}: {i.message}" for i in errors)
        )
    return doc


def new_element(
    type_id: str = "bored_pile",
    name: str = "Elemen baru",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Buat elemen baru memakai default plugin yang valid bila params kosong."""
    if params is None:
        try:
            from scad.plugins import get_plugin

            element_params = get_plugin(type_id).default_params()
        except KeyError:
            element_params = {}
    else:
        element_params = copy.deepcopy(params)
    doc = {
        "kind": "element",
        "schema_version": 1,
        "definition": {
            "type": type_id,
            "type_version": 1,
            "name": name,
            "params": element_params,
            "materials": {
                "concrete": {"grade": "fc30", "type": "readymix"},
                "steel": {"grade": "fy420", "type": "ulir"},
            },
            "zones": [],
            "rebars": [],
        },
        "shapes": {},
    }
    errors = [i for i in validate_document(doc) if i.level == "error"]
    if errors:
        raise ValueError(
            "Elemen baru tidak valid: "
            + "; ".join(f"{i.path}: {i.message}" for i in errors)
        )
    return doc


def open_document(workspace: Path, path: str | Path) -> tuple[dict[str, Any], Path]:
    target = resolve_under_workspace(workspace, path, must_exist=True)
    check_suffix(target)
    check_size(target)
    doc = load_document(target)
    return doc, target


def save_document_at(workspace: Path, path: str | Path, doc: dict[str, Any]) -> Path:
    target = resolve_under_workspace(workspace, path, must_exist=False)
    check_suffix(target)
    errors = [i for i in validate_document(doc) if i.level == "error"]
    if errors:
        raise ValueError(
            "Validasi gagal; berkas tidak ditulis: "
            + "; ".join(f"{i.path}: {i.message}" for i in errors)
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    save_document(target, doc)
    return target


def list_workspace_files(workspace: Path, subdir: str = "") -> list[dict[str, str]]:
    workspace = workspace.resolve()
    if subdir:
        base = (workspace / subdir).resolve()
    else:
        base = workspace
    try:
        if not base.is_relative_to(workspace):
            raise ValueError("dir di luar workspace")
    except AttributeError:
        base.relative_to(workspace)
    if not base.exists():
        return []
    if base.is_file():
        base = base.parent

    out = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if not any(p.name.endswith(s) for s in ALLOWED_SUFFIXES):
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        rel = str(p.resolve().relative_to(workspace.resolve()))
        out.append({"path": rel, "name": p.name})
    return out


def add_element_to_project(
    project: dict[str, Any],
    *,
    element_doc: dict[str, Any] | None = None,
    source_path: str | None = None,
    source_file_label: str | None = None,
    group_id: str,
    count: int,
    naming: dict[str, Any] | None = None,
    layout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Salin definisi elemen ke grup baru + instances grid. Mengembalikan project baru."""
    if count < 1:
        raise ValueError("count harus >= 1")
    if element_doc is None:
        raise ValueError("elemen wajib")
    if element_doc.get("kind") != "element":
        raise ValueError("Dokumen elemen harus kind=element")
    errors = [i for i in validate_document(element_doc) if i.level == "error"]
    if errors:
        raise ValueError(
            "Definisi elemen tidak valid: "
            + "; ".join(f"{i.path}: {i.message}" for i in errors)
        )

    definition_data = copy.deepcopy(element_doc["definition"])
    shapes = element_doc.get("shapes") or {}

    # merge shapes ke project
    new_proj = copy.deepcopy(project)
    proj_shapes = new_proj.setdefault("shapes", {})
    for k, v in shapes.items():
        if k not in proj_shapes:
            proj_shapes[k] = copy.deepcopy(v)

    for g in new_proj.get("groups") or []:
        if g.get("id") == group_id:
            raise ValueError(f"group_id '{group_id}' sudah ada")

    file_label = source_file_label or (Path(source_path).name if source_path else "inline")
    source = {
        "file": file_label,
        "hash": sha256_of(definition_data),
        "added_at": _utc_now(),
        "x_shape_keys": sorted(shapes),
    }

    naming = naming or {}
    pattern = naming.get("pattern") or "P{n}"
    start = int(naming.get("start") or 1)
    layout = layout or {}
    cols = int(layout.get("cols") or count)
    dx = float(layout.get("dx") or 0)
    dy = float(layout.get("dy") or 0)

    instances = []
    for i in range(count):
        n = start + i
        label = pattern.replace("{n}", str(n))
        row, col = divmod(i, cols) if cols > 0 else (0, i)
        # grid: col along x, row along y
        col_i = i % cols
        row_i = i // cols
        instances.append(
            {
                "id": label,
                "x": col_i * dx,
                "y": row_i * dy,
            }
        )

    elem_type = definition_data.get("type") or "bored_pile"
    group = {
        "id": group_id,
        "type": elem_type,
        "name": naming.get("name") or definition_data.get("name") or group_id,
        "definition": {
            "source": source,
            "data": definition_data,
        },
        "defaults": {"params": {}},
        "instances": instances,
    }
    if naming:
        group["naming"] = {"pattern": pattern, "start": start}
    # seed default depth from definition if present
    params = definition_data.get("params") or {}
    if "depth_below_cof" in params:
        group["defaults"]["params"]["depth_below_cof"] = params["depth_below_cof"]

    new_proj.setdefault("groups", []).append(group)
    return new_proj


def source_diff(
    group: dict[str, Any],
    source_elem: dict[str, Any],
    project_shapes: dict[str, Any] | None = None,
) -> list[str]:
    """Daftar path yang berbeda: definition + shapes yang dipakai sumber."""
    data = (group.get("definition") or {}).get("data") or {}
    src_def = source_elem.get("definition") or {}
    diffs: list[str] = []
    for key in sorted(set(data) | set(src_def)):
        if data.get(key) != src_def.get(key):
            path = f"/definition/{key}"
            if path not in diffs:
                diffs.append(path)
    # shapes: bandingkan shape sumber, termasuk shape yang dihapus dari sumber.
    src_shapes = source_elem.get("shapes") or {}
    proj_shapes = project_shapes if project_shapes is not None else {}
    stored_source = (group.get("definition") or {}).get("source") or {}
    owned_keys = stored_source.get("x_shape_keys")
    if not isinstance(owned_keys, list):
        owned_keys = _shape_codes_in_definition(data)
    for sk in sorted(set(owned_keys) | set(src_shapes)):
        if sk not in src_shapes or proj_shapes.get(sk) != src_shapes[sk]:
            diffs.append(f"/shapes/{sk}")
    return diffs


def _shape_codes_in_definition(definition: dict[str, Any]) -> set[str]:
    """Kembalikan shape yang dimiliki definisi lama saat metadata belum ada."""
    return {
        str(shape.get("code"))
        for rebar in definition.get("rebars") or []
        for shape in [rebar.get("shape") or {}]
        if shape.get("code")
    }


def update_group_from_source(
    project: dict[str, Any],
    group_id: str,
    source_elem: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Ganti definition.data dari sumber; pertahankan instances/overrides.

    Override zona yang tidak ada di definisi baru -> issues dan batalkan.
    """
    new_proj = copy.deepcopy(project)
    target = None
    for g in new_proj.get("groups") or []:
        if g.get("id") == group_id:
            target = g
            break
    if target is None:
        raise ValueError(f"Grup '{group_id}' tidak ditemukan")

    old_def = (target.get("definition") or {}).get("data") or {}
    new_def = copy.deepcopy(source_elem["definition"])
    zone_ids = {z.get("id") for z in (new_def.get("zones") or [])}

    issues: list[dict[str, Any]] = []
    for inst in target.get("instances") or []:
        ovr = inst.get("overrides") or {}
        zl = ovr.get("zone_lengths") or {}
        for zid in zl:
            if zid not in zone_ids:
                issues.append(
                    {
                        "level": "error",
                        "code": "OVERRIDE_ZONE_MISSING",
                        "path": f"/groups/{group_id}/instances/{inst.get('id')}/overrides/zone_lengths/{zid}",
                        "message": f"Override zona '{zid}' tidak ada di definisi sumber baru",
                    }
                )

    if issues:
        return project, issues  # batalkan — kembalikan aslinya

    old_source = (target.get("definition") or {}).get("source") or {}
    file_label = old_source.get("file") or "source.elem.json"
    target["definition"] = {
        "source": {
            "file": file_label,
            "hash": sha256_of(new_def),
            "added_at": _utc_now(),
            "x_shape_keys": sorted(source_elem.get("shapes") or {}),
        },
        "data": new_def,
    }
    # Hapus shape yang sebelumnya dimiliki sumber tetapi sudah dihapus dari sumber.
    old_owned = old_source.get("x_shape_keys")
    if not isinstance(old_owned, list):
        old_owned = _shape_codes_in_definition(old_def)
    shapes = new_proj.setdefault("shapes", {})
    new_shapes = source_elem.get("shapes") or {}
    for k in old_owned:
        if k not in new_shapes:
            shapes.pop(k, None)
    # Shape lokal yang bukan milik sumber tetap dipertahankan.
    for k, v in new_shapes.items():
        shapes[k] = copy.deepcopy(v)
    return new_proj, []
