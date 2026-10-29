"""Shim: pilecap_rebar.ui -> scad_ui.server."""
from __future__ import annotations

import warnings

warnings.warn(
    "pilecap_rebar.ui deprecated; gunakan scad_ui.server.",
    DeprecationWarning,
    stacklevel=2,
)

from scad_ui.server import *  # noqa: F401,F403
from scad_ui.server import (  # noqa: F401
    DATA_ROOT,
    STATIC_DIR,
    Handler,
    set_data_root,
    main,
    _safe_join,
)
