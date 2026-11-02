"""C2: uji perilaku XSS (atribut + tag + entity) pada renderer app.js, beserta uji-diri harness."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "tests" / "ui" / "xss_attr_harness.js"
APP_JS = REPO / "src" / "scad_ui" / "static" / "app.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node tidak tersedia")


def _run(app_js: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(HARNESS), str(app_js)],
        cwd=REPO, capture_output=True, text=True, timeout=30,
    )


def test_renderers_resist_attribute_tag_and_entity_injection():
    result = _run(APP_JS)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


@pytest.mark.parametrize(
    "old,new",
    [
        # escape tanda kutip dihapus: breakout atribut tanpa '<'
        (".replace(/\"/g, '&quot;')\n", ""),
        # escape '<' dihapus
        (".replace(/</g, '&lt;')\n", ""),
        # escape '&' dihapus: entity literal lolos
        (".replace(/&/g, '&amp;')\n", ""),
        # sink konkret yang dulu lolos dari tes P7b
        ("escapeHtml(zones)", "zones"),
        ("${escapeHtml(p.depth_below_cof)} ●", "${p.depth_below_cof} ●"),
        ("const pid = escapeHtml(inst.id);", "const pid = inst.id;"),
        ("escapeHtml(rp.depth_below_cof)", "rp.depth_below_cof"),
    ],
    ids=["tanpa-quot", "tanpa-lt", "tanpa-amp", "zones", "depth-tabel", "pid-atribut", "depth-sidebar"],
)
def test_harness_detects_each_missing_escape(tmp_path, old, new):
    """Mutation check: tiap escape yang dilepas HARUS membuat harness gagal."""
    source = APP_JS.read_text(encoding="utf-8")
    assert old in source, f"pola mutasi tidak ditemukan (app.js berubah?): {old!r}"
    mutated = tmp_path / "app.js"
    mutated.write_text(source.replace(old, new, 1), encoding="utf-8")
    result = _run(mutated)
    assert result.returncode != 0, "harness tidak mendeteksi mutasi"
    assert "GAGAL" in result.stderr
