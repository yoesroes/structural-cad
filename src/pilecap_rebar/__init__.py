"""Shim kompatibilitas: mengekspor ulang scad_engine.

Kode baru sebaiknya mengimpor `scad_engine` atau `scad_ui` langsung.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Paket 'pilecap_rebar' deprecated; gunakan 'scad_engine' atau 'scad_ui'.",
    DeprecationWarning,
    stacklevel=2,
)

from scad_engine import (  # noqa: F401
    BarGroup,
    BarProto,
    Instance,
    ConfigError,
    build_groups,
    validate_config,
    cut_section,
    default_cut_positions,
    build_recap,
    reconcile,
    write_recap,
)
