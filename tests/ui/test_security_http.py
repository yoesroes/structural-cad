"""P7: gerbang Host/Origin/Content-Type, header keamanan, escapeHtml."""
from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def request(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    *,
    headers: dict[str, str] | None = None,
    raw_body: bytes | None = None,
) -> tuple[int, dict | str]:
    data = raw_body if raw_body is not None else (
        None if body is None else json.dumps(body).encode("utf-8")
    )
    request_headers = dict(headers or {})
    if body is not None and "Content-Type" not in request_headers:
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{base}{path}", data=data, headers=request_headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read().decode("utf-8")
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, raw


def test_foreign_host_rejected_without_write(ui_server):
    path = ui_server["data_root"] / "project.json"
    before = path.read_bytes()
    status, body = request(
        ui_server["base"],
        "POST",
        "/api/project/save",
        headers={"Host": "evil.example", "Content-Type": "application/json"},
        raw_body=b"{}",
    )
    assert status == 400
    assert path.read_bytes() == before


def test_foreign_origin_rejected_without_write(ui_server):
    path = ui_server["data_root"] / "project.json"
    before = path.read_bytes()
    status, body = request(
        ui_server["base"],
        "POST",
        "/api/project/save",
        headers={
            "Origin": "https://evil.example",
            "Content-Type": "application/json",
        },
        raw_body=b"{}",
    )
    assert status == 403
    assert path.read_bytes() == before


def test_text_plain_rejected_without_write(ui_server):
    path = ui_server["data_root"] / "project.json"
    before = path.read_bytes()
    status, body = request(
        ui_server["base"],
        "POST",
        "/api/project/save",
        headers={"Content-Type": "text/plain"},
        raw_body=b"{}",
    )
    assert status == 415
    assert path.read_bytes() == before


def test_same_origin_post_still_works(ui_server):
    """Permintaan normal (Host loopback, Content-Type JSON, tanpa Origin) tetap lolos gerbang."""
    base = ui_server["base"]
    # Host diisi otomatis oleh urllib ke 127.0.0.1:<port>
    status, body = request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    assert body.get("ok") is True


def test_same_origin_with_matching_origin_header(ui_server):
    base = ui_server["base"]
    # origin harus http://<Host>; urllib set Host ke 127.0.0.1:port
    from urllib.parse import urlparse

    host = urlparse(base).netloc  # 127.0.0.1:port
    status, body = request(
        base,
        "POST",
        "/api/project/open",
        {"path": "P1.project.json"},
        headers={
            "Content-Type": "application/json",
            "Origin": f"http://{host}",
        },
    )
    assert status == 200
    assert body.get("ok") is True


def test_security_headers_present(ui_server):
    base = ui_server["base"]
    req = urllib.request.Request(f"{base}/api/project")
    with urllib.request.urlopen(req, timeout=5) as response:
        headers = {k.lower(): v for k, v in response.headers.items()}
        assert headers.get("x-content-type-options") == "nosniff"
        csp = headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        response.read()


def test_escape_html_node():
    """Uji Node: escapeHtml menetralkan payload XSS klasik."""
    app_js = (REPO / "src/scad_ui/static/app.js").read_text(encoding="utf-8")
    assert "function escapeHtml" in app_js
    script = r"""
const fs = require('fs');
const src = fs.readFileSync('src/scad_ui/static/app.js', 'utf8');
const m = src.match(/function escapeHtml\(value\)\s*\{[\s\S]*?\n  \}/);
if (!m) { console.error('escapeHtml not found'); process.exit(1); }
eval(m[0]);
const samples = [
  ['<script>alert(1)</script>', '&lt;script&gt;alert(1)&lt;/script&gt;'],
  ['a&b', 'a&amp;b'],
  ['"q"', '&quot;q&quot;'],
  ["x'y", 'x&#39;y'],
];
for (const [inp, exp] of samples) {
  const got = escapeHtml(inp);
  if (got !== exp) {
    console.error('fail', inp, got, exp);
    process.exit(1);
  }
}
console.log('ok');
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout


def test_app_js_innerhtml_templates_use_escape_html():
    """Gagal bila properti dokumen diinterpolasi ke template tanpa escapeHtml."""
    src = (REPO / "src/scad_ui/static/app.js").read_text(encoding="utf-8")
    without_canvas = re.sub(
        r"function renderCanvas\(\)\s*\{[\s\S]*?\n  \}",
        "function renderCanvas() {}",
        src,
        count=1,
    )
    # Hanya flag ${expr} yang mengakses properti objek dokumen secara langsung
    # dan belum dibungkus escapeHtml(...). textContent aman (tidak dicek di sini).
    risky = re.findall(
        r"\$\{(?!escapeHtml\()([^}]*\b(?:doc|group|params|inst|p|r|mats|pileResolved)\.[^}]*)\}",
        without_canvas,
    )
    risky = [r for r in risky if "escapeHtml" not in r]
    assert risky == [], f"Interpolasi tanpa escapeHtml: {risky}"
