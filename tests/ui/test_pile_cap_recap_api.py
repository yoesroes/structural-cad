"""S2 / H3-04: endpoint rekap pile_cap (jalur UI)."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from scad_ui import server as ui_mod
from scad_ui.server import Handler, set_data_root

REPO = Path(__file__).resolve().parents[2]


def _start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}"


def _pc_project() -> dict:
    elem = json.loads((REPO / "examples" / "PC_8400.elem.json").read_text(encoding="utf-8"))
    data = elem["definition"]
    return {
        "kind": "project",
        "schema_version": 1,
        "project": {"id": "PC", "name": "PC", "datum": {"cof_elevation": 0}},
        "settings": {"cover_ref": "surface"},
        "shapes": elem.get("shapes") or {},
        "groups": [
            {
                "id": "PC-1",
                "type": "pile_cap",
                "definition": {"data": data},
                "defaults": {},
                "instances": [{"id": "PC-1-1", "x": 0, "y": 0}],
            }
        ],
    }


def _write_pc(tmp: Path) -> None:
    (tmp / "project.json").write_text(
        json.dumps(_pc_project(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_api_pile_recap_pc_8400(tmp_path: Path):
    prev = ui_mod.DATA_ROOT
    prev_doc = ui_mod.CURRENT_DOC
    server = None
    try:
        ui_mod.CURRENT_DOC = None
        set_data_root(tmp_path)
        _write_pc(tmp_path)
        server, base = _start_server()
        with urllib.request.urlopen(f"{base}/api/pile/PC-1-1/recap", timeout=10) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
        assert body.get("ok") is True
        assert body.get("pile_id") == "PC-1-1"
        counts: dict[str, int] = {}
        for row in body.get("rows") or []:
            m = row["mark"]
            counts[m] = counts.get(m, 0) + int(row["count"])
        assert sum(counts.values()) == 533
        assert counts.get("P5") == 169
        assert counts.get("P6") == 32
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        set_data_root(prev)
        ui_mod.CURRENT_DOC = prev_doc


def test_api_group_recap_pc_8400(tmp_path: Path):
    prev = ui_mod.DATA_ROOT
    prev_doc = ui_mod.CURRENT_DOC
    server = None
    try:
        ui_mod.CURRENT_DOC = None
        set_data_root(tmp_path)
        _write_pc(tmp_path)
        server, base = _start_server()
        with urllib.request.urlopen(f"{base}/api/group/PC-1/recap", timeout=10) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
        assert body.get("ok") is True
        assert body.get("group_id") == "PC-1"
        total = sum(int(t["count"]) for t in body.get("totals") or [])
        assert total == 533
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        set_data_root(prev)
        ui_mod.CURRENT_DOC = prev_doc


def test_api_pile_recap_unknown_returns_400(tmp_path: Path):
    prev = ui_mod.DATA_ROOT
    prev_doc = ui_mod.CURRENT_DOC
    server = None
    try:
        ui_mod.CURRENT_DOC = None
        set_data_root(tmp_path)
        _write_pc(tmp_path)
        server, base = _start_server()
        try:
            urllib.request.urlopen(f"{base}/api/pile/TIDAK-ADA/recap", timeout=10)
            raise AssertionError("diharapkan HTTPError 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
            body = json.loads(e.read().decode())
            assert body.get("ok") is False
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        set_data_root(prev)
        ui_mod.CURRENT_DOC = prev_doc
