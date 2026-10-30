"""Fixture bersama untuk pengujian server lokal Structural CAD."""
from __future__ import annotations

import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from scad_ui import server as ui_mod
from scad_ui.server import Handler


REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def ui_server(tmp_path: Path):
    """Server HTTP terisolasi dengan seluruh state global dipulihkan setelah test."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "data"
    data_root.mkdir()
    p1 = json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))
    (workspace / "P1.project.json").write_text(
        json.dumps(p1, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (data_root / "project.json").write_text(
        json.dumps(p1, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    shutil.copy(REPO / "examples" / "BP_D1200.elem.json", workspace / "BP_D1200.elem.json")

    previous = {
        "data_root": ui_mod.DATA_ROOT,
        "root": ui_mod.ROOT,
        "workspace": ui_mod.WORKSPACE,
        "current_path": ui_mod.CURRENT_PATH,
        "current_doc": ui_mod.CURRENT_DOC,
        "dirty": ui_mod.DIRTY,
        "current_element": ui_mod.CURRENT_ELEMENT,
        "current_element_path": ui_mod.CURRENT_ELEMENT_PATH,
    }
    ui_mod.set_workspace(workspace)
    ui_mod.set_data_root(data_root)
    ui_mod.CURRENT_PATH = None
    ui_mod.CURRENT_DOC = None
    ui_mod.DIRTY = False
    ui_mod.CURRENT_ELEMENT = None
    ui_mod.CURRENT_ELEMENT_PATH = None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield {
            "base": base,
            "workspace": workspace,
            "data_root": data_root,
        }
    finally:
        server.shutdown()
        server.server_close()
        ui_mod.set_data_root(previous["data_root"])
        ui_mod.ROOT = previous["root"]
        ui_mod.set_workspace(previous["workspace"])
        ui_mod.CURRENT_PATH = previous["current_path"]
        ui_mod.CURRENT_DOC = previous["current_doc"]
        ui_mod.DIRTY = previous["dirty"]
        ui_mod.CURRENT_ELEMENT = previous["current_element"]
        ui_mod.CURRENT_ELEMENT_PATH = previous["current_element_path"]
