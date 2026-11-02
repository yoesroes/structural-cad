"""P8: statusForPile mengakui error global dan menguji app.js aktual."""
from __future__ import annotations

import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def test_status_for_pile_actual_app_js():
    script = REPO / "tests" / "ui" / "test_status_for_pile.js"
    result = subprocess.run(
        ["node", str(script), "src/scad_ui/static/app.js"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok statusForPile aktual" in result.stdout
