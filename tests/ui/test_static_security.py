"""Regresi F1: static hanya boleh menyajikan berkas di dalam direktori static."""
from __future__ import annotations

import http.client
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer

import pytest

from scad_ui import server as ui_mod
from scad_ui.server import Handler


def _request(port: int, path: str) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


@pytest.fixture
def static_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "ok.txt").write_text("aset sah\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("rahasia\n", encoding="utf-8")
    try:
        (static_dir / "outside.txt").symlink_to(outside)
    except OSError:
        pytest.skip("Symlink tidak didukung oleh filesystem pengujian")
    monkeypatch.setattr(ui_mod, "STATIC_DIR", static_dir)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def test_static_rejects_traversal_and_outside_symlink(static_server: int):
    for path in (
        "/static//etc/passwd",
        "/static/%2e%2e/README.md",
        "/static/../README.md",
        "/static/%2Fetc%2Fpasswd",
        "/static/outside.txt",
    ):
        assert _request(static_server, path) == 404, path


def test_static_serves_valid_asset_with_query(static_server: int):
    assert _request(static_server, "/static/ok.txt?v=1") == 200
