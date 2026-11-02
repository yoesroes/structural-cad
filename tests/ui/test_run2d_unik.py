"""A4: /run-2d tidak boleh menimpa keluaran request lain (nama SVG unik, pruning terbatas)."""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from pathlib import Path

from scad_ui import server as ui_mod

PILES = ["P1-1", "P1-2", "P1-5", "P1-8"]  # P1-2/5/8 punya override: geometri 2D berbeda


def _post(base: str, path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_concurrent_run2d_returns_distinct_files_with_own_content(ui_server):
    base = ui_server["base"]
    # Baseline berurutan: isi SVG yang benar untuk tiap pile.
    expected: dict[str, str] = {}
    for pid in PILES:
        status, body = _post(base, "/run-2d", {"pile_id": pid})
        assert status == 200 and body["ok"] is True
        expected[pid] = Path(body["path"]).read_text(encoding="utf-8")

    # Permintaan bersamaan untuk semua pile.
    results: dict[str, dict] = {}
    errors: list[BaseException] = []

    def worker(pid: str) -> None:
        try:
            status, body = _post(base, "/run-2d", {"pile_id": pid})
            assert status == 200
            results[pid] = body
        except BaseException as exc:  # noqa: BLE001 - dikumpulkan lalu dinyatakan gagal
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(pid,)) for pid in PILES]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=180)
    assert not errors, errors

    paths = [results[pid]["path"] for pid in PILES]
    assert len(set(paths)) == len(paths), "path SVG bersamaan harus unik (A4)"
    for pid in PILES:
        content = Path(results[pid]["path"]).read_text(encoding="utf-8")
        assert content == expected[pid], f"isi SVG {pid} tertimpa request lain"


def test_run2d_output_name_is_unique_and_not_legacy_fixed_name(ui_server):
    status, body = _post(ui_server["base"], "/run-2d", {"pile_id": "P1-1"})
    assert status == 200
    name = Path(body["path"]).name
    assert name != "run-2d.svg"
    assert name.startswith("run-2d-") and name.endswith(".svg")


def test_prune_run2d_keeps_only_newest(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_mod, "DATA_ROOT", tmp_path)
    base_time = time.time() - 1000
    for i in range(ui_mod.RUN_2D_KEEP + 5):
        f = tmp_path / f"run-2d-{i:03d}.svg"
        f.write_text("x", encoding="utf-8")
        os.utime(f, (base_time + i, base_time + i))
    (tmp_path / "project.json").write_text("{}", encoding="utf-8")
    (tmp_path / "lain.svg").write_text("x", encoding="utf-8")

    ui_mod._prune_run_2d()

    left = sorted(p.name for p in tmp_path.glob("run-2d-*.svg"))
    assert len(left) == ui_mod.RUN_2D_KEEP
    assert left[0] == "run-2d-005.svg" and left[-1] == f"run-2d-{ui_mod.RUN_2D_KEEP + 4:03d}.svg"
    assert (tmp_path / "project.json").exists() and (tmp_path / "lain.svg").exists()
