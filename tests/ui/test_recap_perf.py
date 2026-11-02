"""P8: cache recap_pile dan perhitungan di luar STATE_LOCK."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from scad_ui import server as ui_mod


def _request(base: str, method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(
        f"{base}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_recap_pile_second_call_is_cache_hit(ui_server):
    ui_mod.reset_recap_cache()
    base = ui_server["base"]
    status, _ = _request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    before = ui_mod.recap_cache_stats()
    s1, body1 = _request(base, "GET", "/api/pile/P1-1/recap")
    assert s1 == 200
    assert body1.get("ok") is True
    mid = ui_mod.recap_cache_stats()
    assert mid["misses"] >= before["misses"] + 1
    s2, body2 = _request(base, "GET", "/api/pile/P1-1/recap")
    assert s2 == 200
    assert body2.get("ok") is True
    after = ui_mod.recap_cache_stats()
    assert after["hits"] >= mid["hits"] + 1
    # hit kedua tidak menambah miss
    assert after["misses"] == mid["misses"]


def test_other_request_not_blocked_during_group_recap(ui_server):
    """Request ringan (GET /api/project) tetap bisa selama group recap berjalan."""
    base = ui_server["base"]
    status, _ = _request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200

    results: dict[str, object] = {}

    def do_recap():
        results["recap"] = _request(base, "GET", "/api/group/BP-P1/recap")

    def do_project():
        # sedikit jeda agar recap mulai dulu
        time.sleep(0.05)
        t0 = time.perf_counter()
        results["project"] = _request(base, "GET", "/api/project")
        results["project_dt"] = time.perf_counter() - t0

    t_recap = threading.Thread(target=do_recap)
    t_proj = threading.Thread(target=do_project)
    t_recap.start()
    t_proj.start()
    t_recap.join(timeout=60)
    t_proj.join(timeout=60)
    assert t_recap.is_alive() is False
    assert t_proj.is_alive() is False
    assert results["recap"][0] == 200
    assert results["project"][0] == 200
    # GET project seharusnya tidak menunggu seluruh recap (batas longgar)
    assert float(results["project_dt"]) < 2.0

def test_recap_path_without_id_returns_404_not_hang(ui_server):
    import urllib.error, urllib.request
    for p in ("/api/pile//recap", "/api/pile/recap", "/api/group//recap"):
        try:
            urllib.request.urlopen(ui_server["base"] + p, timeout=3)
            raise AssertionError(f"{p}: seharusnya 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404, p