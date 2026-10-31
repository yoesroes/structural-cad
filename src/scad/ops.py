"""Operasi edit pile (kedalaman / panjang zona) — murni, server = otoritas."""
from __future__ import annotations

import copy
from typing import Any


def _find_group_and_instance(
    doc: dict[str, Any], group_id: str, pile_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    for g in doc.get("groups") or []:
        if g.get("id") != group_id:
            continue
        for inst in g.get("instances") or []:
            if inst.get("id") == pile_id:
                return g, inst
        raise ValueError(f"Pile '{pile_id}' tidak ditemukan di grup '{group_id}'")
    raise ValueError(f"Grup '{group_id}' tidak ditemukan")


def _find_pile_location(doc: dict[str, Any], pile_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Cari pile di semua grup; kembalikan (group_id, group, instance)."""
    for g in doc.get("groups") or []:
        for inst in g.get("instances") or []:
            if inst.get("id") == pile_id:
                return str(g.get("id")), g, inst
    raise ValueError(f"Pile '{pile_id}' tidak ditemukan di project")


def effective_group_depth(group: dict[str, Any]) -> float | None:
    """Nilai kedalaman efektif grup: defaults.params → definition.data.params."""
    defaults = (group.get("defaults") or {}).get("params") or {}
    if "depth_below_cof" in defaults:
        return float(defaults["depth_below_cof"])
    definition = (group.get("definition") or {}).get("data") or {}
    params = definition.get("params") or {}
    if "depth_below_cof" in params:
        return float(params["depth_below_cof"])
    return None


def definition_zone_length(group: dict[str, Any], zone_id: str) -> float | None:
    """Panjang zona tetap dari definisi (bukan 'rest'); None bila tidak ada / rest."""
    definition = (group.get("definition") or {}).get("data") or {}
    for z in definition.get("zones") or []:
        if z.get("id") == zone_id:
            length = z.get("length")
            if isinstance(length, (int, float)):
                return float(length)
            return None
    return None


def zone_exists(group: dict[str, Any], zone_id: str) -> bool:
    definition = (group.get("definition") or {}).get("data") or {}
    return any(z.get("id") == zone_id for z in (definition.get("zones") or []))


def zone_is_rest(group: dict[str, Any], zone_id: str) -> bool:
    """True bila definisi zona memakai length 'rest'."""
    definition = (group.get("definition") or {}).get("data") or {}
    return any(
        z.get("id") == zone_id and z.get("length") == "rest"
        for z in (definition.get("zones") or [])
    )


def _prune_overrides(inst: dict[str, Any]) -> None:
    ovr = inst.get("overrides")
    if not isinstance(ovr, dict):
        return
    params = ovr.get("params")
    if isinstance(params, dict) and len(params) == 0:
        del ovr["params"]
    zl = ovr.get("zone_lengths")
    if isinstance(zl, dict) and len(zl) == 0:
        del ovr["zone_lengths"]
    if len(ovr) == 0:
        del inst["overrides"]


def apply_operation(
    doc: dict[str, Any], op: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Terapkan op pada salinan doc.

    op: {op, group, pile, value?} atau {op, group, pile, zone, value?}
    Mengembalikan (doc_baru, inverse|None).
    Nilai harus > 0. Pile/zona tak dikenal -> ValueError (pesan Indonesia).
    """
    next_doc = copy.deepcopy(doc)
    kind = op.get("op")
    group_id = op.get("group")
    pile_id = op.get("pile")
    if not kind or not group_id or not pile_id:
        raise ValueError("Operasi harus memuat op, group, dan pile")

    group, inst = _find_group_and_instance(next_doc, str(group_id), str(pile_id))

    if kind == "set_pile_depth":
        value = op.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (value > 0):
            raise ValueError("Nilai kedalaman harus angka > 0")
        value = float(value)
        prev = None
        if inst.get("overrides") and isinstance(inst["overrides"].get("params"), dict):
            if "depth_below_cof" in inst["overrides"]["params"]:
                prev = float(inst["overrides"]["params"]["depth_below_cof"])
        default_depth = effective_group_depth(group)

        if prev is not None:
            inverse: dict[str, Any] | None = {
                "op": "set_pile_depth",
                "group": group_id,
                "pile": pile_id,
                "value": prev,
            }
        else:
            inverse = {"op": "reset_pile_depth", "group": group_id, "pile": pile_id}

        if default_depth is not None and value == default_depth:
            if inst.get("overrides") and isinstance(inst["overrides"].get("params"), dict):
                inst["overrides"]["params"].pop("depth_below_cof", None)
            _prune_overrides(inst)
        else:
            ovr = inst.setdefault("overrides", {})
            params = ovr.setdefault("params", {})
            params["depth_below_cof"] = value

        if prev is None and default_depth is not None and value == default_depth:
            return next_doc, None
        if prev is not None and prev == value:
            return next_doc, None
        return next_doc, inverse

    if kind == "reset_pile_depth":
        prev = None
        if inst.get("overrides") and isinstance(inst["overrides"].get("params"), dict):
            if "depth_below_cof" in inst["overrides"]["params"]:
                prev = float(inst["overrides"]["params"]["depth_below_cof"])
        if prev is None:
            return next_doc, None
        inverse = {
            "op": "set_pile_depth",
            "group": group_id,
            "pile": pile_id,
            "value": prev,
        }
        inst["overrides"]["params"].pop("depth_below_cof", None)
        _prune_overrides(inst)
        return next_doc, inverse

    if kind == "set_pile_zone_length":
        zone = op.get("zone")
        value = op.get("value")
        if not zone:
            raise ValueError("Operasi set_pile_zone_length membutuhkan zone")
        if not zone_exists(group, str(zone)):
            raise ValueError(f"Zona '{zone}' tidak ditemukan di definisi grup '{group_id}'")
        if zone_is_rest(group, str(zone)):
            raise ValueError(f"Zona '{zone}' bertipe rest tidak boleh di-override")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (value > 0):
            raise ValueError("Panjang zona harus angka > 0")
        value = float(value)

        prev = None
        if inst.get("overrides") and isinstance(inst["overrides"].get("zone_lengths"), dict):
            if zone in inst["overrides"]["zone_lengths"]:
                prev = float(inst["overrides"]["zone_lengths"][zone])

        if prev is not None:
            inverse = {
                "op": "set_pile_zone_length",
                "group": group_id,
                "pile": pile_id,
                "zone": zone,
                "value": prev,
            }
        else:
            inverse = {
                "op": "reset_pile_zone_length",
                "group": group_id,
                "pile": pile_id,
                "zone": zone,
            }

        def_len = definition_zone_length(group, str(zone))
        if def_len is not None and value == def_len:
            if inst.get("overrides") and isinstance(inst["overrides"].get("zone_lengths"), dict):
                inst["overrides"]["zone_lengths"].pop(zone, None)
            _prune_overrides(inst)
        else:
            ovr = inst.setdefault("overrides", {})
            zl = ovr.setdefault("zone_lengths", {})
            zl[zone] = value

        if prev is None and def_len is not None and value == def_len:
            return next_doc, None
        if prev is not None and prev == value:
            return next_doc, None
        return next_doc, inverse

    if kind == "reset_pile_zone_length":
        zone = op.get("zone")
        if not zone:
            raise ValueError("Operasi reset_pile_zone_length membutuhkan zone")
        if not zone_exists(group, str(zone)):
            raise ValueError(f"Zona '{zone}' tidak ditemukan di definisi grup '{group_id}'")
        prev = None
        if inst.get("overrides") and isinstance(inst["overrides"].get("zone_lengths"), dict):
            if zone in inst["overrides"]["zone_lengths"]:
                prev = float(inst["overrides"]["zone_lengths"][zone])
        # Zona rest: reset diizinkan HANYA untuk menghapus override tersimpan.
        if zone_is_rest(group, str(zone)):
            if prev is None:
                raise ValueError(
                    f"Zona '{zone}' bertipe rest tidak punya override untuk di-reset"
                )
            # lanjut hapus override di bawah
        elif prev is None:
            return next_doc, None
        inverse = {
            "op": "set_pile_zone_length",
            "group": group_id,
            "pile": pile_id,
            "zone": zone,
            "value": prev,
        }
        inst["overrides"]["zone_lengths"].pop(zone, None)
        _prune_overrides(inst)
        return next_doc, inverse

    raise ValueError(f"Operasi tidak dikenal: '{kind}'")
