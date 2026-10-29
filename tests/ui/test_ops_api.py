"""Tes API pile memakai scad.ops (F6)."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from scad_ui import server as ui_mod
from scad_ui.server import Handler, set_data_root

REPO = Path(__file__).resolve().parents[2]


def _start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}"


def _write_p1(tmp: Path) -> None:
    doc = json.loads((REPO / "examples" / "P1.project.json").read_text(encoding="utf-8"))
    (tmp / "project.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def test_api_pile_depth_same_as_default_no_overrides(tmp_path: Path):
    prev = ui_mod.DATA_ROOT
    server = None
    try:
        set_data_root(tmp_path)
        _write_p1(tmp_path)
        server, base = _start_server()
        req = urllib.request.Request(
            f"{base}/api/pile/P1-1/depth",
            data=json.dumps({"depth": 30000}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        assert body["ok"] is True
        saved = json.loads((tmp_path / "project.json").read_text(encoding="utf-8"))
        inst = next(i for g in saved["groups"] for i in g["instances"] if i["id"] == "P1-1")
        assert not (inst.get("overrides") or {}).get("params", {}).get("depth_below_cof")
        assert "depth_below_cof" not in (body.get("pile") or {}).get("overridden", [])
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        set_data_root(prev)


def test_api_pile_reset_zone_p1_8(tmp_path: Path):
    prev = ui_mod.DATA_ROOT
    server = None
    try:
        set_data_root(tmp_path)
        _write_p1(tmp_path)
        server, base = _start_server()
        req = urllib.request.Request(
            f"{base}/api/pile/P1-8/reset",
            data=json.dumps({"field": "zone:Z2"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        assert body["ok"] is True
        saved = json.loads((tmp_path / "project.json").read_text(encoding="utf-8"))
        inst = next(i for g in saved["groups"] for i in g["instances"] if i["id"] == "P1-8")
        assert "Z2" not in ((inst.get("overrides") or {}).get("zone_lengths") or {})
        assert inst["overrides"]["params"]["depth_below_cof"] == 26000
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        set_data_root(prev)
