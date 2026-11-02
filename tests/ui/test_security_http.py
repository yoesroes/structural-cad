"""P7/P7b: gerbang Host/Origin/Content-Type, header keamanan, escapeHtml perilaku."""
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
    base = ui_server["base"]
    status, body = request(base, "POST", "/api/project/open", {"path": "P1.project.json"})
    assert status == 200
    assert body.get("ok") is True


def test_same_origin_with_matching_origin_header(ui_server):
    base = ui_server["base"]
    from urllib.parse import urlparse

    host = urlparse(base).netloc
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
        for directive in (
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "object-src 'none'",
            "base-uri 'none'",
            "frame-ancestors 'none'",
        ):
            assert directive in csp, f"missing {directive} in {csp}"
        response.read()


def test_get_foreign_host_rejected(ui_server):
    """P7b: guard GET menolak Host asing (DNS rebinding)."""
    base = ui_server["base"]
    for path in ("/api/project", "/"):
        status, _ = request(
            base,
            "GET",
            path,
            headers={"Host": "evil.example"},
        )
        assert status == 400, path


def test_get_foreign_origin_rejected(ui_server):
    base = ui_server["base"]
    status, _ = request(
        base,
        "GET",
        "/api/project",
        headers={"Origin": "https://evil.example"},
    )
    assert status == 403


def test_delete_foreign_host_no_side_effect(ui_server):
    path = ui_server["data_root"] / "project.json"
    before = path.read_bytes() if path.exists() else None
    status, _ = request(
        ui_server["base"],
        "DELETE",
        "/api/project",
        headers={"Host": "evil.example", "Content-Type": "application/json"},
    )
    # DELETE tidak di-guard khusus, tetapi endpoint selalu 404
    assert status in {404, 400, 501}
    if before is not None:
        assert path.read_bytes() == before


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
    """Lapis kedua: properti dokumen diinterpolasi harus lewat escapeHtml."""
    src = (REPO / "src/scad_ui/static/app.js").read_text(encoding="utf-8")
    without_canvas = re.sub(
        r"function renderCanvas\(\)\s*\{[\s\S]*?\n  \}",
        "function renderCanvas() {}",
        src,
        count=1,
    )
    risky = re.findall(
        r"\$\{(?!escapeHtml\()([^}]*\b(?:doc|group|params|inst|p|r|mats|pileResolved)\.[^}]*)\}",
        without_canvas,
    )
    risky = [r for r in risky if "escapeHtml" not in r]
    assert risky == [], f"Interpolasi tanpa escapeHtml: {risky}"


def test_render_functions_escape_payloads_in_node():
    """P7b: uji perilaku — render sidebar/tabel/props di Node dengan stub DOM."""
    script = r'''
const fs = require('fs');
const src = fs.readFileSync('src/scad_ui/static/app.js', 'utf8');

// Ekstrak escapeHtml
const mEsc = src.match(/function escapeHtml\(value\)\s*\{[\s\S]*?\n  \}/);
if (!mEsc) { console.error('no escapeHtml'); process.exit(1); }
eval(mEsc[0]);

// Stub DOM minimal
function el(id) {
  return {
    id,
    innerHTML: '',
    textContent: '',
    querySelectorAll() { return []; },
    addEventListener() {},
  };
}
const store = {
  sidebar: el('sidebar'),
  tbody: el('tbody'),
  props: el('props'),
};
global.document = {
  getElementById(id) {
    if (id === 'sidebar') return store.sidebar;
    if (id === 'props') return store.props;
    return el(id);
  },
  querySelector(sel) {
    if (sel.includes('tbody')) return store.tbody;
    return null;
  },
};

// Ekstrak dan jalankan renderSidebar, renderTable, renderProps
// Ambil body fungsi dari sumber (kasar tetapi stabil)
function extractFn(name) {
  const re = new RegExp('function ' + name + '\\([^)]*\\)\\s*\\{');
  const start = src.search(re);
  if (start < 0) throw new Error('missing ' + name);
  let i = src.indexOf('{', start);
  let depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') {
      depth--;
      if (depth === 0) {
        return src.slice(start, i + 1);
      }
    }
  }
  throw new Error('unclosed ' + name);
}

eval(extractFn('statusForPile'));  // helper P8 dipakai renderTable
eval(extractFn('renderSidebar'));
eval(extractFn('renderTable'));
eval(extractFn('renderProps'));

const payload = '<img src=x onerror=alert(1)>';
const payload2 = '"><script>alert(1)</script>';
const doc = {
  project: { name: payload, id: 'X' },
  materials: {
    concrete: { grade: payload },
    steel: { grade: payload2 },
  },
  groups: [{
    id: payload2,
    type: payload,
    definition: {
      data: {
        params: { diameter: 1200, cover: 50, cover_ref: 'surface', depth_below_cof: 30000 },
        materials: {
          concrete: { grade: payload },
          steel: { grade: payload2 },
        },
        rebars: [{
          id: payload,
          diameter: 16,
          shape: { code: payload2 },
          extent: { zones: ['Z1'] },
        }],
      },
    },
    instances: [{ id: payload }],
  }],
};
const resolved = {
  groups: [{
    id: doc.groups[0].id,
    piles: [{
      id: payload,
      x: 0, y: 0,
      depth_below_cof: 30000,
      overridden: [],
      zones: [{ id: 'Z3', length: 'rest' }],
    }],
  }],
  issues: [],
};
let resolveData = resolved;

renderSidebar(doc, resolved);
renderTable(resolved);
renderProps(doc, doc.groups[0], resolved.groups[0].piles[0]);

const blobs = [store.sidebar.innerHTML, store.tbody.innerHTML, store.props.innerHTML];
for (const html of blobs) {
  // Tag mentah tidak boleh muncul (payload harus entity-encoded)
  if (/<img\b/i.test(html) || /<script\b/i.test(html)) {
    console.error('RAW TAG in', html.slice(0, 200));
    process.exit(1);
  }
  // Payload XSS harus ter-escape sebagai entity
  if (!html.includes('&lt;') && !html.includes('&quot;') && !html.includes('&#39;')) {
    console.error('expected escaped payload in', html.slice(0, 200));
    process.exit(1);
  }
  // Pastikan karakter < dari payload tidak lolos mentah
  if (html.includes('<img') || html.includes('<script')) {
    console.error('unescaped payload fragment', html.slice(0, 200));
    process.exit(1);
  }
}
console.log('ok');
'''
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout


def test_no_inline_style_attributes_in_shell():
    """P7b: style inline dipindah ke app.css (index + app.js render)."""
    index = (REPO / "src/scad_ui/static/index.html").read_text(encoding="utf-8")
    app = (REPO / "src/scad_ui/static/app.js").read_text(encoding="utf-8")
    assert 'style="' not in index
    assert 'style="' not in app
