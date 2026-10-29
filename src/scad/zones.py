"""Penyelesai zona relatif COF (z=0, positif ke atas)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


class ZoneError(ValueError):
    """Galat penyelesaian zona; atribut code memuat kode galat."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ResolvedZone:
    id: str
    side: str  # "above_cof" | "below_cof"
    length: float
    z_top: float
    z_bottom: float


def _to_finite_float(value: Any, field: str, zid: str | None = None) -> float:
    """Konversi value ke float dan pastikan finite; lempar ZoneError bila gagal."""
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        label = f"zona '{zid}'" if zid is not None else field
        raise ZoneError(
            "SCHEMA",
            f"Nilai {field} untuk {label} tidak dapat dikonversi ke float: {value!r}",
        ) from exc
    if not math.isfinite(result):
        label = f"zona '{zid}'" if zid is not None else field
        raise ZoneError(
            "SCHEMA",
            f"Nilai {field} untuk {label} harus finite (diterima: {value!r})",
        )
    return result


def resolve_zones(
    zones: list[dict[str, Any]],
    depth_below_cof: float,
    zone_lengths: dict[str, float] | None = None,
) -> list[ResolvedZone]:
    """Selesaikan panjang dan rentang z tiap zona.

    Urutan hasil = urutan masukan. Zona above_cof bertumpuk ke atas dari z=0;
    below_cof bertumpuk ke bawah dari z=0.
    """
    if depth_below_cof is None:
        raise ZoneError(
            "ZONE_DEPTH_SHORT",
            f"depth_below_cof harus >= 0 (diterima: {depth_below_cof!r})",
        )
    depth = _to_finite_float(depth_below_cof, "depth_below_cof")
    if depth < 0:
        raise ZoneError(
            "ZONE_DEPTH_SHORT",
            f"depth_below_cof harus >= 0 (diterima: {depth_below_cof!r})",
        )
    overrides = dict(zone_lengths or {})

    # Validasi override ID
    known_ids = {str(z.get("id")) for z in zones}
    for oid in overrides:
        if str(oid) not in known_ids:
            raise ZoneError(
                "REF_MISSING",
                f"zone_lengths mengacu zona tidak dikenal: '{oid}'",
            )

    # Normalisasi side & deteksi rest
    normalized: list[dict[str, Any]] = []
    rest_indices: list[int] = []
    for i, z in enumerate(zones):
        zid = str(z.get("id", ""))
        side = z.get("side") or "below_cof"
        if side not in ("above_cof", "below_cof"):
            raise ZoneError(
                "SCHEMA",
                f"side zona '{zid}' tidak valid: {side!r}",
            )
        length_raw = z.get("length")
        is_rest = length_raw == "rest"
        if is_rest:
            rest_indices.append(i)
        normalized.append(
            {
                "id": zid,
                "side": side,
                "length_raw": length_raw,
                "is_rest": is_rest,
            }
        )

    if len(rest_indices) > 1:
        raise ZoneError(
            "ZONE_REST_POS",
            "Hanya boleh satu zona dengan length 'rest'",
        )
    if len(rest_indices) == 1:
        ri = rest_indices[0]
        # rest harus zona below_cof terakhir dalam daftar
        if normalized[ri]["side"] != "below_cof":
            raise ZoneError(
                "ZONE_REST_POS",
                f"Zona 'rest' ({normalized[ri]['id']}) harus side below_cof",
            )
        for j in range(ri + 1, len(normalized)):
            if normalized[j]["side"] == "below_cof":
                raise ZoneError(
                    "ZONE_REST_POS",
                    f"Zona 'rest' ({normalized[ri]['id']}) harus zona below_cof terakhir",
                )

    # Hitung panjang tetap below_cof (setelah override)
    fixed_below = 0.0
    lengths: dict[int, float] = {}
    for i, nz in enumerate(normalized):
        if nz["is_rest"]:
            continue
        if nz["id"] in overrides:
            length = _to_finite_float(
                overrides[nz["id"]], "zone_lengths override", nz["id"]
            )
        else:
            length = _to_finite_float(
                nz["length_raw"], "length", nz["id"]
            )
        if length <= 0:
            raise ZoneError(
                "ZONE_DEPTH_SHORT",
                f"Panjang zona '{nz['id']}' harus > 0 (diterima: {length})",
            )
        lengths[i] = length
        if nz["side"] == "below_cof":
            fixed_below += length

    if fixed_below > depth + 1e-9:
        raise ZoneError(
            "ZONE_DEPTH_SHORT",
            f"Jumlah zona below_cof tetap ({fixed_below:g}) melebihi "
            f"depth_below_cof ({depth:g})",
        )

    if rest_indices:
        ri = rest_indices[0]
        rest_len = depth - fixed_below
        if rest_len <= 0:
            raise ZoneError(
                "ZONE_DEPTH_SHORT",
                f"Sisa zona 'rest' tidak positif: depth={depth:g}, "
                f"tetap={fixed_below:g}, sisa={rest_len:g}",
            )
        lengths[ri] = rest_len
    else:
        # Tanpa rest: jumlah tetap below boleh sama dengan depth (tidak wajib mengisi penuh)
        pass

    # Tumpuk koordinat
    z_above = 0.0  # ujung atas tumpukan above saat ini (= z_bottom zona above berikutnya)
    z_below = 0.0  # ujung bawah tumpukan below saat ini (= z_top zona below berikutnya)

    result: list[ResolvedZone] = []
    for i, nz in enumerate(normalized):
        length = lengths[i]
        if nz["side"] == "above_cof":
            z_bottom = z_above
            z_top = z_above + length
            z_above = z_top
        else:
            z_top = z_below
            z_bottom = z_below - length
            z_below = z_bottom
        if not math.isfinite(z_top) or not math.isfinite(z_bottom):
            raise ZoneError(
                "SCHEMA",
                f"Koordinat zona '{nz['id']}' tidak finite: "
                f"z_top={z_top!r}, z_bottom={z_bottom!r}",
            )
        result.append(
            ResolvedZone(
                id=nz["id"],
                side=nz["side"],
                length=float(length),
                z_top=float(z_top),
                z_bottom=float(z_bottom),
            )
        )
    return result