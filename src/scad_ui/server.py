"""UI lokal Structural CAD: server HTTP dengan arsitektur modular.

Halaman aktif: static/index.html (skrip inline).
static/js/app.js saat ini LEGACY (tidak di-link dari index).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

_PACKAGE_DIR = Path(__file__).resolve().parent
# src/scad_ui -> src -> repo root
_REPO_ROOT = _PACKAGE_DIR.parent.parent
_SOURCE_TREE = (_REPO_ROOT / "examples").is_dir() and (
    (_REPO_ROOT / "src" / "scad").is_dir() or (_REPO_ROOT / "schemas").is_dir()
)

from scad.io.files import save_document
from scad.validate import validate_document


def _default_data_root() -> Path:
    """Direktori data UI: tree sumber → <repo>/output/...; instalasi → ~/.structural-cad/ui."""
    import os

    env = os.environ.get("STRUCTURAL_CAD_DATA")
    if env:
        return Path(env).expanduser().resolve()
    if _SOURCE_TREE:
        return (_REPO_ROOT / "output" / "structural_cad_ui").resolve()
    return (Path.home() / ".structural-cad" / "ui").resolve()


DATA_ROOT = _default_data_root()
STATIC_DIR = _PACKAGE_DIR / "static"
WORKSPACE = Path.cwd().resolve()
CURRENT_PATH: Path | None = None
CURRENT_DOC: dict | None = None
DIRTY = False
CURRENT_ELEMENT_PATH: Path | None = None
CURRENT_ELEMENT: dict | None = None
EXAMPLES_DIR = (
    _REPO_ROOT / "examples"
    if _SOURCE_TREE
    else (_PACKAGE_DIR.parent / "scad_engine" / "examples")
)
ROOT = DATA_ROOT  # alias

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
MAX_REQUEST_BODY_BYTES = 5 * 1024 * 1024
STATE_LOCK = threading.RLock()
_KEEP_PATH = object()


def _safe_join(base: Path, rel: str) -> Path | None:
    """Gabungkan base + rel aman. Kembalikan Path absolut hanya jika berkas di dalam base.

    - Buang query/fragmen (rel sebaiknya sudah bersih).
    - unquote sekali.
    - Tolak path kosong, absolut, atau yang keluar dari base (termasuk symlink ke luar).
    """
    if rel is None:
        return None
    # Ambil path saja bila masih ada query/fragmen
    rel = urlsplit(rel).path
    rel = unquote(rel)
    # Hilangkan leading slash agar Path tidak menganggap absolut
    rel = rel.lstrip("/\\")
    if not rel or rel in (".",):
        return None
    try:
        base_resolved = base.resolve()
        target = (base_resolved / rel).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    # Python 3.9+: is_relative_to; fallback untuk kompatibilitas
    try:
        if not target.is_relative_to(base_resolved):
            return None
    except AttributeError:
        try:
            target.relative_to(base_resolved)
        except ValueError:
            return None
    if not target.is_file():
        return None
    return target


def set_data_root(path: str | Path) -> Path:
    global DATA_ROOT, ROOT
    DATA_ROOT = Path(path).resolve()
    ROOT = DATA_ROOT
    return DATA_ROOT


def set_workspace(path: str | Path) -> Path:
    global WORKSPACE
    WORKSPACE = Path(path).resolve()
    return WORKSPACE


def _default_project_path() -> Path:
    """Urutan: examples paket/repo, lalu salinan di DATA_ROOT bila ada."""
    for candidate in (
        EXAMPLES_DIR / "P1.project.json",
        _PACKAGE_DIR / "examples" / "P1.project.json",
        _REPO_ROOT / "examples" / "P1.project.json",
    ):
        if candidate.is_file():
            return candidate
    return EXAMPLES_DIR / "P1.project.json"


def _load_current_project() -> dict:
    """Muat project sesi, DATA_ROOT, atau contoh P1.project.json."""
    global CURRENT_DOC
    if CURRENT_DOC is not None:
        return CURRENT_DOC
    saved = DATA_ROOT / "project.json"
    if saved.exists():
        CURRENT_DOC = json.loads(saved.read_text(encoding="utf-8"))
        return CURRENT_DOC
    example = _default_project_path()
    if example.exists():
        CURRENT_DOC = json.loads(example.read_text(encoding="utf-8"))
        return CURRENT_DOC
    CURRENT_DOC = {
        "kind": "project",
        "schema_version": 1,
        "project": {"id": "P1", "name": "Project P1", "datum": {"cof_elevation": 0}},
        "settings": {"cover_ref": "surface"},
        "materials": {
            "concrete": {"grade": "fc30", "type": "readymix"},
            "steel": {"grade": "fy420", "type": "ulir"},
        },
        "shapes": {},
        "groups": [],
    }
    return CURRENT_DOC


def _set_current(
    doc: dict,
    path: Path | None | object = _KEEP_PATH,
    dirty: bool = False,
) -> None:
    """Set dokumen aktif; path omitted means keep, None explicitly clears it."""
    global CURRENT_DOC, CURRENT_PATH, DIRTY
    CURRENT_DOC = doc
    if path is not _KEEP_PATH:
        CURRENT_PATH = path
    DIRTY = dirty


def _validation_errors(doc: dict) -> list[dict]:
    """Kembalikan issue level error sebagai list dict JSON-friendly."""
    errors: list[dict] = []
    for issue in validate_document(doc):
        if issue.level == "error":
            errors.append(
                {
                    "level": issue.level,
                    "code": issue.code,
                    "path": issue.path,
                    "message": issue.message,
                }
            )
    return errors


def _save_validated(doc: dict, target: Path) -> tuple[bool, dict]:
    """Validasi lalu simpan via save_document.

    Mengembalikan (True, {"path": ...}) bila sukses, atau
    (False, {"error": ..., "issues": [...]}) bila validasi gagal.
    Exception dari save_document dibiarkan naik ke pemanggil.
    """
    errors = _validation_errors(doc)
    if errors:
        return False, {
            "error": "Validasi gagal; perubahan tidak disimpan",
            "issues": errors,
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    save_document(target, doc)
    return True, {"path": str(target)}


def _commit(doc: dict, target: Path | None = None) -> tuple[bool, dict]:
    """Validasi, simpan, lalu commit state aktif secara atomik.

    Bila project belum punya path (CURRENT_PATH is None) dan target adalah
    fallback DATA_ROOT/project.json, berkas tetap ditulis tetapi CURRENT_PATH
    tetap None dan DIRTY tetap True agar status "belum bernama" / Simpan As
    tidak hilang. CURRENT_PATH dan DIRTY=False hanya diset bila target sama
    dengan CURRENT_PATH yang sudah ada (project bertajuk).
    """
    previous_path = CURRENT_PATH
    if target is None:
        target = previous_path if previous_path is not None else DATA_ROOT / "project.json"
    ok, info = _save_validated(doc, target)
    if ok:
        if previous_path is not None and target == previous_path:
            _set_current(doc, path=target, dirty=False)
        elif previous_path is None:
            # Project tanpa judul: jangan mengisi path dari fallback scratch.
            _set_current(doc, path=None, dirty=True)
        else:
            # Target eksplisit berbeda dari path aktif (jarang untuk _commit).
            _set_current(doc, path=target, dirty=False)
    return ok, info


def _pile_ids_from_issue_path(doc: dict, path: str) -> set[str] | None:
    """Petakan JSON Pointer issue ke id pile, atau None bila bukan path instance.

    None = issue global / pointer tidak bisa dipetakan (fail-closed) → pemanggil memblokir.
    Pointer rusak, indeks di luar jangkauan, atau id hilang → None, bukan set() kosong.
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if len(parts) >= 4 and parts[0] == "groups" and parts[2] == "instances":
        try:
            gi = int(parts[1])
            ii = int(parts[3])
            inst = ((doc.get("groups") or [])[gi].get("instances") or [])[ii]
            pid = inst.get("id")
            if not pid:
                return None
            return {pid}
        except (ValueError, IndexError, TypeError, KeyError, AttributeError):
            return None
    return None


def _resolve_errors_for_pile(
    resolve_issues: list, doc: dict, pile_id: str
) -> list:
    """Saring error resolve yang menyangkut pile yang diedit atau issue global.

    Error pada pile lain tidak menghalangi edit pile yang sehat.
    """
    relevant: list = []
    for issue in resolve_issues or []:
        if issue.get("level") != "error":
            continue
        pile_field = issue.get("pile")
        if pile_field is not None:
            if pile_field == pile_id:
                relevant.append(issue)
            continue
        concerned = _pile_ids_from_issue_path(doc, issue.get("path") or "")
        if concerned is None:
            # Issue global (bukan path instance) — tetap blokir.
            relevant.append(issue)
        elif pile_id in concerned:
            relevant.append(issue)
    return relevant


class Handler(BaseHTTPRequestHandler):
    def _handle_request_exception(self, exc: Exception) -> None:
        """Kirim error JSON tanpa memutus koneksi dan tanpa membocorkan detail internal."""
        if isinstance(exc, (ValueError, KeyError)):
            self.send_json({"ok": False, "error": str(exc)}, 400)
            return
        traceback.print_exc(file=sys.stderr)
        self.send_json({"ok": False, "error": "Galat internal"}, 500)

    def do_GET(self):
        with STATE_LOCK:
            try:
                self._dispatch_get()
            except Exception as exc:
                self._handle_request_exception(exc)

    def _dispatch_get(self):
        if self.path.startswith("/static/"):
            self.serve_static()
            return
        if self.path in ("/", "/index.html"):
            self.serve_index()
            return
        if self.path == "/api/project":
            self.get_project()
            return
        # GET /api/element/<type>/schema
        if self.path.startswith("/api/element/") and self.path.endswith("/schema"):
            parts = [p for p in self.path.split("/") if p]
            # ["api", "element", "<type>", "schema"]
            if len(parts) >= 4:
                self.get_element_schema(parts[2])
                return
        # GET /api/pile/<id>/recap  (G1)
        if self.path.startswith("/api/pile/") and self.path.endswith("/recap"):
            parts = [p for p in self.path.split("/") if p]
            if len(parts) >= 4:
                self.api_pile_recap(parts[2])
                return
        # GET /api/group/<id>/recap  (G1)
        if self.path.startswith("/api/group/") and self.path.endswith("/recap"):
            parts = [p for p in self.path.split("/") if p]
            if len(parts) >= 4:
                self.api_group_recap(parts[2])
                return
        # GET /api/group/<id>/source-diff  (G2)
        if self.path.startswith("/api/group/") and self.path.endswith("/source-diff"):
            parts = [p for p in self.path.split("/") if p]
            if len(parts) >= 4:
                self.api_source_diff(parts[2])
                return
        # GET /api/files?dir=
        if self.path.startswith("/api/files"):
            self.api_list_files()
            return
        self.send_error(404, "Not found")

    def do_POST(self):
        with STATE_LOCK:
            try:
                self._dispatch_post()
            except Exception as exc:
                self._handle_request_exception(exc)

    def _dispatch_post(self):
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except (TypeError, ValueError):
            self.send_json({"ok": False, "error": "Content-Length tidak valid"}, 400)
            return
        if length < 0:
            self.send_json({"ok": False, "error": "Content-Length tidak valid"}, 400)
            return
        if length > MAX_REQUEST_BODY_BYTES:
            self.send_json(
                {"ok": False, "error": f"Request terlalu besar (maks {MAX_REQUEST_BODY_BYTES} byte)"},
                413,
            )
            return
        body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise ValueError("JSON request tidak valid") from exc

        if self.path == "/api/project/save":
            self.save_project(data)
            return
        if self.path == "/api/project/resolve":
            self.resolve_project(data)
            return
        if self.path == "/api/validate":
            self.validate_doc(data)
            return
        if self.path.startswith("/api/element/") and self.path.endswith("/rebar"):
            parts = self.path.split("/")
            self.add_rebar(parts[3], data)
            return
        if self.path.startswith("/api/pile/"):
            parts = [p for p in self.path.split("/") if p]
            # api pile <id> depth|zone|reset
            if len(parts) >= 4:
                pile_id, action = parts[2], parts[3]
                if action == "depth":
                    self.api_pile_depth(pile_id, data)
                    return
                if action == "zone":
                    self.api_pile_zone(pile_id, data)
                    return
                if action == "reset":
                    self.api_pile_reset(pile_id, data)
                    return

        if self.path == "/api/project/new":
            self.api_project_new(data)
            return
        if self.path == "/api/project/open":
            self.api_project_open(data)
            return
        if self.path == "/api/project/save-as":
            self.api_project_save_as(data)
            return
        if self.path == "/api/project/add-element":
            self.api_add_element(data)
            return
        if self.path == "/api/element/new":
            self.api_element_new(data)
            return
        if self.path == "/api/element/open":
            self.api_element_open(data)
            return
        if self.path == "/api/element/save" or (
            self.path.startswith("/api/element/") and self.path.endswith("/save")
        ):
            self.api_element_save(data)
            return
        if self.path.startswith("/api/group/") and self.path.endswith("/update-from-source"):
            parts = [p for p in self.path.split("/") if p]
            if len(parts) >= 4:
                self.api_update_from_source(parts[2], data)
                return

        if self.path == "/run-2d":
            self.run_2d(data)
            return
        if self.path == "/run-3d":
            self.run_3d(data)
            return

        self.send_json({"ok": False, "error": "Endpoint not found"}, 404)

    def do_DELETE(self):
        try:
            self.send_json({"ok": False, "error": "Endpoint not found"}, 404)
        except Exception as exc:
            self._handle_request_exception(exc)

    @staticmethod
    def _run_input(data: dict) -> tuple[dict, str]:
        """Ambil dokumen dan pile target untuk pipeline engine UI."""
        doc = data.get("doc") if isinstance(data.get("doc"), dict) else _load_current_project()
        errors = _validation_errors(doc)
        if errors:
            raise ValueError(
                "Dokumen tidak valid: "
                + "; ".join(f"{i['path']}: {i['message']}" for i in errors)
            )
        pile_id = data.get("pile_id")
        if not pile_id:
            for group in doc.get("groups") or []:
                instances = group.get("instances") or []
                if instances:
                    pile_id = instances[0].get("id")
                    break
        if not pile_id:
            raise ValueError("Project tidak memiliki instance pile")
        return doc, str(pile_id)

    def run_2d(self, data: dict):
        """Jalankan pipeline section/drawing dan kembalikan SVG hasilnya."""
        try:
            from scad_engine.draw import compose, write_svg
            from scad_engine.from_v1 import build_bar_groups
            from scad_engine.recap import build_recap
            from scad_engine.section2d import cut_section, default_cut_positions

            doc, pile_id = self._run_input(data)
            groups = build_bar_groups(doc, pile_id)
            definition = next(
                g["definition"]["data"]
                for g in doc.get("groups") or []
                if any(i.get("id") == pile_id for i in g.get("instances") or [])
            )
            params = definition.get("params") or {}
            if all(key in params for key in ("length", "width", "height")):
                length, width, height = (
                    float(params["length"]),
                    float(params["width"]),
                    float(params["height"]),
                )
            else:
                # Bored pile memakai diameter/depth, bukan dimensi pile-cap.
                diameter = float(params.get("diameter", 1000))
                length = width = max(diameter * 2, 1000.0)
                height = float(params.get("depth_below_cof", 1000))
            cuts = default_cut_positions(groups, length, width)
            trans = cut_section(groups, "x", float(data.get("cut_x", cuts["x"])))
            longitudinal = cut_section(groups, "y", float(data.get("cut_y", cuts["y"])))
            prims, layers = compose(
                length, width, height, trans, longitudinal, build_recap(groups)
            )
            target = DATA_ROOT / "run-2d.svg"
            target.parent.mkdir(parents=True, exist_ok=True)
            write_svg(prims, layers, target)
            self.send_json({"ok": True, "pile_id": pile_id, "path": str(target), "format": "svg"})
        except (KeyError, TypeError, ValueError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)

    def run_3d(self, data: dict):
        """Jalankan pipeline geometri dan kembalikan centerline 3D serializable."""
        try:
            from scad_engine.from_v1 import build_bar_groups

            doc, pile_id = self._run_input(data)
            groups = build_bar_groups(doc, pile_id)
            bars = []
            for group in groups:
                for instance in group.instances:
                    proto = group.protos[instance.proto]
                    bars.append(
                        {
                            "mark": group.mark,
                            "diameter": group.diameter,
                            "origin": list(instance.origin),
                            "points": [list(point) for point in proto.points],
                        }
                    )
            self.send_json({"ok": True, "pile_id": pile_id, "format": "centerline", "bars": bars})
        except (KeyError, TypeError, ValueError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)

    def serve_static(self):
        # self.path bisa berisi query (?v=1); ambil path saja
        raw = urlsplit(self.path).path
        if not raw.startswith("/static/"):
            self.send_error(404, "File not found")
            return
        rel = raw[len("/static/") :]
        file_path = _safe_join(STATIC_DIR, rel)
        if file_path is None:
            self.send_error(404, "File not found")
            return
        mime_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".html": "text/html",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".json": "application/json",
        }
        mime = mime_types.get(file_path.suffix.lower(), "application/octet-stream")
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def serve_index(self):
        index_file = STATIC_DIR / "index.html"
        if not index_file.exists():
            self.send_error(404, "index.html not found")
            return
        data = index_file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def get_project(self):
        try:
            project = _load_current_project()
            source = "saved" if (DATA_ROOT / "project.json").exists() else "example"
            self.send_json({"ok": True, "project": project, "source": source})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def resolve_project(self, data):
        try:
            from scad.resolve import resolve_project as resolve_fn

            doc = data.get("doc") or data
            if not doc or doc.get("kind") != "project":
                doc = _load_current_project()
            result = resolve_fn(doc)
            self.send_json({"ok": True, **result})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def validate_doc(self, data):
        try:
            doc = data.get("doc") or data
            issues = validate_document(doc)
            self.send_json(
                {
                    "ok": True,
                    "issues": [
                        {
                            "level": i.level,
                            "code": i.code,
                            "path": i.path,
                            "message": i.message,
                        }
                        for i in issues
                    ],
                }
            )
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def get_element_schema(self, elem_type: str):
        """Skema plugin dari scad.plugins (menggantikan form HTML elements/)."""
        try:
            from scad.plugins import get_plugin

            plugin = get_plugin(elem_type)
            self.send_json(
                {
                    "ok": True,
                    "type": plugin.type_id,
                    "type_version": plugin.type_version,
                    "params_schema": plugin.params_schema(),
                    "faces": plugin.faces(),
                    "overridable_params": plugin.overridable_params(),
                }
            )
        except KeyError:
            self.send_json(
                {"ok": False, "error": f"Tipe elemen tidak dikenal: '{elem_type}'"},
                404,
            )
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def save_project(self, data):
        """POST /api/project/save — path opsional; validasi selalu sebelum tulis."""
        from scad.files_ops import resolve_under_workspace, check_suffix

        try:
            doc = data.get("doc") if isinstance(data.get("doc"), dict) else (
                data if data.get("kind") else _load_current_project()
            )
            path = data.get("path")
            if path:
                target = resolve_under_workspace(WORKSPACE, path, must_exist=False)
                check_suffix(target)
            elif CURRENT_PATH is not None:
                target = CURRENT_PATH
            else:
                target = DATA_ROOT / "project.json"
            ok, info = _save_validated(doc, target)
            if not ok:
                self.send_json({"ok": False, **info}, 400)
                return
            _set_current(doc, path=target, dirty=False)
            self.send_json({"ok": True, "path": info["path"], "dirty": False})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def add_rebar(self, elem_id, data):
        try:
            project = copy.deepcopy(_load_current_project())
            found = False
            for group in project.get("groups", []):
                if group.get("id") == elem_id:
                    definition = (group.get("definition") or {}).setdefault("data", {})
                    rebars = definition.setdefault("rebars", [])
                    rebars.append(data)
                    found = True
                    break
            if not found:
                self.send_json(
                    {"ok": False, "error": f"Elemen '{elem_id}' tidak ditemukan di project"},
                    404,
                )
                return
            ok, info = _commit(project)
            if not ok:
                self.send_json({"ok": False, **info}, 400)
                return
            self.send_json({"ok": True})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def _apply_pile_op_and_respond(self, pile_id: str, op: dict):
        """Terapkan ops.apply_operation, validasi, simpan, balas ResolvedPile."""
        from scad.ops import apply_operation, _find_pile_location
        from scad.resolve import resolve_project

        try:
            project = _load_current_project()
            # Lengkapi group bila belum ada
            if "group" not in op or not op.get("group"):
                gid, _, _ = _find_pile_location(project, pile_id)
                op = {**op, "group": gid, "pile": pile_id}
            else:
                op = {**op, "pile": pile_id}

            new_doc, _inverse = apply_operation(project, op)
            resolved = resolve_project(new_doc)
            resolve_issues = resolved.get("issues") or []
            resolve_errors = _resolve_errors_for_pile(resolve_issues, new_doc, pile_id)
            if resolve_errors:
                self.send_json(
                    {
                        "ok": False,
                        "error": "Resolve gagal; perubahan tidak disimpan",
                        "issues": resolve_errors,
                    },
                    400,
                )
                return
            ok, info = _commit(new_doc)
            if not ok:
                self.send_json({"ok": False, **info}, 400)
                return
            pile_out = None
            for g in resolved.get("groups") or []:
                for pl in g.get("piles") or []:
                    if pl.get("id") == pile_id:
                        pile_out = pl
                        break
                if pile_out is not None:
                    break
            self.send_json({"ok": True, "pile": pile_out})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e), "issues": []}, 400)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_pile_depth(self, pile_id, data):
        depth = data.get("depth")
        if depth is None:
            self.send_json({"ok": False, "error": "Field depth wajib"}, 400)
            return
        self._apply_pile_op_and_respond(
            pile_id,
            {"op": "set_pile_depth", "group": data.get("group"), "pile": pile_id, "value": depth},
        )

    def api_pile_zone(self, pile_id, data):
        zone = data.get("zone")
        length = data.get("length")
        if zone is None or length is None:
            self.send_json({"ok": False, "error": "Field zone dan length wajib"}, 400)
            return
        self._apply_pile_op_and_respond(
            pile_id,
            {
                "op": "set_pile_zone_length",
                "group": data.get("group"),
                "pile": pile_id,
                "zone": zone,
                "value": length,
            },
        )

    def api_pile_reset(self, pile_id, data):
        field = data.get("field")
        if field == "depth":
            op = {"op": "reset_pile_depth", "group": data.get("group"), "pile": pile_id}
        elif isinstance(field, str) and field.startswith("zone:"):
            zone = field.split(":", 1)[1]
            op = {
                "op": "reset_pile_zone_length",
                "group": data.get("group"),
                "pile": pile_id,
                "zone": zone,
            }
        else:
            self.send_json(
                {"ok": False, "error": 'Field harus "depth" atau "zone:<id>"'},
                400,
            )
            return
        self._apply_pile_op_and_respond(pile_id, op)


    def api_list_files(self):
        from urllib.parse import parse_qs, urlsplit
        from scad.files_ops import list_workspace_files

        qs = parse_qs(urlsplit(self.path).query)
        sub = (qs.get("dir") or [""])[0]
        try:
            files = list_workspace_files(WORKSPACE, sub)
            self.send_json({"ok": True, "workspace": str(WORKSPACE), "files": files})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_project_new(self, data):
        from scad.files_ops import new_project

        pid = data.get("id") or "P1"
        name = data.get("name") or pid
        doc = new_project(str(pid), str(name))
        _set_current(doc, path=None, dirty=True)
        self.send_json({"ok": True, "project": doc, "path": None, "dirty": True})

    def api_project_open(self, data):
        from scad.files_ops import open_document

        path = data.get("path")
        if not path:
            self.send_json({"ok": False, "error": "Field path wajib"}, 400)
            return
        try:
            doc, target = open_document(WORKSPACE, path)
            if doc.get("kind") != "project":
                self.send_json({"ok": False, "error": "Berkas bukan project"}, 400)
                return
            _set_current(doc, path=target, dirty=False)
            self.send_json(
                {
                    "ok": True,
                    "project": doc,
                    "path": str(target.relative_to(WORKSPACE)),
                    "dirty": False,
                }
            )
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_project_save_as(self, data):
        from scad.files_ops import save_document_at

        path = data.get("path")
        if not path:
            self.send_json({"ok": False, "error": "Field path wajib"}, 400)
            return
        doc = data.get("doc") if isinstance(data.get("doc"), dict) else _load_current_project()
        try:
            errors = _validation_errors(doc)
            if errors:
                self.send_json(
                    {"ok": False, "error": "Validasi gagal; berkas tidak ditulis", "issues": errors},
                    400,
                )
                return
            target = save_document_at(WORKSPACE, path, doc)
            _set_current(doc, path=target, dirty=False)
            self.send_json(
                {
                    "ok": True,
                    "path": str(target.relative_to(WORKSPACE)),
                    "dirty": False,
                }
            )
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_add_element(self, data):
        from scad.files_ops import add_element_to_project, open_document

        group_id = data.get("group_id")
        count = int(data.get("count") or 1)
        if not group_id:
            self.send_json({"ok": False, "error": "group_id wajib"}, 400)
            return
        try:
            element_doc = data.get("element")
            source_path = data.get("path")
            label = None
            if source_path:
                element_doc, target = open_document(WORKSPACE, source_path)
                label = target.name
            if not element_doc:
                self.send_json({"ok": False, "error": "path atau element wajib"}, 400)
                return
            project = _load_current_project()
            new_proj = add_element_to_project(
                project,
                element_doc=element_doc,
                source_path=source_path,
                source_file_label=label,
                group_id=group_id,
                count=count,
                naming=data.get("naming"),
                layout=data.get("layout"),
            )
            errors = _validation_errors(new_proj)
            if errors:
                self.send_json(
                    {"ok": False, "error": "Validasi gagal setelah add-element", "issues": errors},
                    400,
                )
                return
            _set_current(new_proj, dirty=True)
            grp = next(g for g in new_proj["groups"] if g["id"] == group_id)
            self.send_json(
                {
                    "ok": True,
                    "group": grp,
                    "source": grp["definition"]["source"],
                    "dirty": True,
                }
            )
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_element_new(self, data):
        from scad.files_ops import new_element

        global CURRENT_ELEMENT, CURRENT_ELEMENT_PATH
        doc = new_element(
            data.get("type") or "bored_pile",
            data.get("name") or "Elemen baru",
            params=data.get("params"),
        )
        CURRENT_ELEMENT = doc
        CURRENT_ELEMENT_PATH = None
        self.send_json({"ok": True, "element": doc})

    def api_element_open(self, data):
        from scad.files_ops import open_document

        global CURRENT_ELEMENT, CURRENT_ELEMENT_PATH
        path = data.get("path")
        if not path:
            self.send_json({"ok": False, "error": "path wajib"}, 400)
            return
        try:
            doc, target = open_document(WORKSPACE, path)
            if doc.get("kind") != "element":
                self.send_json({"ok": False, "error": "Berkas bukan element"}, 400)
                return
            CURRENT_ELEMENT = doc
            CURRENT_ELEMENT_PATH = target
            self.send_json(
                {
                    "ok": True,
                    "element": doc,
                    "path": str(target.relative_to(WORKSPACE)),
                }
            )
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_element_save(self, data):
        from scad.files_ops import resolve_under_workspace, check_suffix

        global CURRENT_ELEMENT, CURRENT_ELEMENT_PATH
        path = data.get("path") or (
            str(CURRENT_ELEMENT_PATH.relative_to(WORKSPACE))
            if CURRENT_ELEMENT_PATH
            else None
        )
        doc = data.get("doc") or data.get("element") or CURRENT_ELEMENT
        if not path or not doc:
            self.send_json({"ok": False, "error": "path dan dokumen elemen wajib"}, 400)
            return
        try:
            if not isinstance(doc, dict) or doc.get("kind") != "element":
                raise ValueError("Dokumen harus kind=element")
            if not path.endswith(".elem.json"):
                raise ValueError("Simpan elemen harus berakhiran .elem.json")
            errors = _validation_errors(doc)
            if errors:
                self.send_json(
                    {"ok": False, "error": "Validasi gagal; berkas tidak ditulis", "issues": errors},
                    400,
                )
                return
            target = resolve_under_workspace(WORKSPACE, path, must_exist=False)
            check_suffix(target)
            ok, info = _save_validated(doc, target)
            if not ok:
                self.send_json({"ok": False, **info}, 400)
                return
            CURRENT_ELEMENT = doc
            CURRENT_ELEMENT_PATH = target
            self.send_json({"ok": True, "path": str(target.relative_to(WORKSPACE))})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_source_diff(self, group_id: str):
        from scad.files_ops import open_document, source_diff

        project = _load_current_project()
        group = next((g for g in project.get("groups") or [] if g.get("id") == group_id), None)
        if not group:
            self.send_json({"ok": False, "error": f"Grup '{group_id}' tidak ditemukan"}, 404)
            return
        src = (group.get("definition") or {}).get("source") or {}
        file_name = src.get("file")
        if not file_name:
            self.send_json({"ok": False, "error": "Grup tidak punya source.file"}, 400)
            return
        # cari di workspace
        matches = list(WORKSPACE.rglob(file_name))
        if not matches:
            self.send_json({"ok": False, "error": f"Berkas sumber '{file_name}' tidak ada di workspace"}, 404)
            return
        try:
            elem, _ = open_document(WORKSPACE, str(matches[0].relative_to(WORKSPACE)))
            diffs = source_diff(group, elem, project_shapes=project.get("shapes") or {})
            self.send_json({"ok": True, "group_id": group_id, "diffs": diffs, "source_file": file_name})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_update_from_source(self, group_id: str, data):
        from scad.files_ops import open_document, update_group_from_source

        project = _load_current_project()
        group = next((g for g in project.get("groups") or [] if g.get("id") == group_id), None)
        if not group:
            self.send_json({"ok": False, "error": f"Grup '{group_id}' tidak ditemukan"}, 404)
            return
        path = data.get("path")
        if not path:
            src = (group.get("definition") or {}).get("source") or {}
            file_name = src.get("file")
            matches = list(WORKSPACE.rglob(file_name)) if file_name else []
            if not matches:
                self.send_json({"ok": False, "error": "path sumber wajib"}, 400)
                return
            path = str(matches[0].relative_to(WORKSPACE))
        try:
            elem, _ = open_document(WORKSPACE, path)
            new_proj, issues = update_group_from_source(project, group_id, elem)
            if issues:
                self.send_json(
                    {"ok": False, "error": "Override tidak valid; pembaruan dibatalkan", "issues": issues},
                    400,
                )
                return
            _set_current(new_proj, dirty=True)
            self.send_json({"ok": True, "project": new_proj, "dirty": True})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)


    def api_pile_recap(self, pile_id: str):
        """G1: rekap batang per pile dari dokumen v1."""
        try:
            from scad_engine.from_v1 import recap_pile

            project = _load_current_project()
            result = recap_pile(project, pile_id)
            self.send_json({"ok": True, **result})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def api_group_recap(self, group_id: str):
        """G1: rekap batang per grup (semua pile)."""
        try:
            from scad_engine.from_v1 import recap_group

            project = _load_current_project()
            result = recap_group(project, group_id)
            self.send_json({"ok": True, **result})
        except ValueError as e:
            self.send_json({"ok": False, "error": str(e)}, 400)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 400)

    def send_json(self, obj, status=200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print("[Structural CAD UI]", fmt % args)


def main(argv=None):
    ap = argparse.ArgumentParser(description="UI lokal Structural CAD")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument(
        "--data-dir",
        default=None,
        help="Direktori penyimpanan project.json (default: <repo>/output/structural_cad_ui)",
    )
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument(
        "--workspace",
        default=None,
        help="Root path aman untuk open/save (default: CWD)",
    )
    a = ap.parse_args(argv)

    if a.data_dir:
        set_data_root(a.data_dir)
    if a.workspace:
        set_workspace(a.workspace)
    else:
        set_workspace(Path.cwd())

    if a.host not in _LOOPBACK_HOSTS:
        ap.error(
            f"host non-loopback '{a.host}' ditolak: UI hanya boleh diakses melalui loopback"
        )

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    url = f"http://{a.host}:{a.port}/"
    print(f"Structural CAD UI: {url}")
    print(f"Data directory: {DATA_ROOT}")
    print(f"Workspace: {WORKSPACE}")
    print(f"Default example: {_default_project_path()}")
    print("Ctrl+C untuk berhenti")

    if not a.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nUI dihentikan.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
