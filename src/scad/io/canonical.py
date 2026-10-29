"""JSON kanonik dan hash SHA-256 untuk dokumen Structural CAD."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _normalize(obj: Any) -> Any:
    """Normalkan objek: kunci dict terurut, float bulat -> int, rekursif."""
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, int) and not isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        if obj.is_integer():
            return int(obj)
        return obj
    return obj


def canonical_json(obj: Any) -> str:
    """Serialisasi kanonik: kunci terurut, tanpa spasi, ensure_ascii=False.

    Float bernilai bulat dinormalkan ke int (1200.0 -> 1200).
    """
    return json.dumps(
        _normalize(obj),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_of(obj: Any) -> str:
    """Hash SHA-256 atas canonical_json(obj), berawalan 'sha256:'."""
    payload = canonical_json(obj).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
