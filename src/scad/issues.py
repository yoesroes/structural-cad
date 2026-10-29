"""Issue validasi dokumen Structural CAD."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    level: str  # error | warning | info
    code: str
    path: str  # JSON Pointer
    message: str
