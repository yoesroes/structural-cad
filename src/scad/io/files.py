"""Muat dan simpan dokumen Structural CAD (project / element / shape_library)."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

from scad.validate import validate_document

SCHEMA_VERSION = 1

# Migrasi dari versi lama ke berikutnya; kunci = versi sumber.
# Contoh nanti: MIGRATIONS[1] = callable yang mengubah doc v1 -> v2
MIGRATIONS: dict[int, Callable[[dict], dict]] = {}

_ALLOWED_KINDS = frozenset({"project", "element", "shape_library"})


class SchemaVersionError(ValueError):
    """schema_version dokumen tidak didukung."""


def load_document(path: str | Path) -> dict[str, Any]:
    """Baca dokumen UTF-8, validasi kind/schema_version, terapkan migrasi bila perlu."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    doc = json.loads(text)
    if not isinstance(doc, dict):
        raise ValueError(f"Dokumen harus objek JSON: {p}")

    kind = doc.get("kind")
    if kind not in _ALLOWED_KINDS:
        raise ValueError(
            f"kind harus salah satu dari {sorted(_ALLOWED_KINDS)}, diterima: {kind!r}"
        )

    if "schema_version" not in doc:
        raise ValueError("schema_version wajib ada")
    version = doc["schema_version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError(f"schema_version harus integer, diterima: {version!r}")

    if version > SCHEMA_VERSION:
        raise SchemaVersionError(
            f"schema_version {version} lebih baru dari yang didukung ({SCHEMA_VERSION})"
        )

    # Terapkan migrasi berurutan untuk versi lebih lama
    v = version
    while v < SCHEMA_VERSION:
        migrator = MIGRATIONS.get(v)
        if migrator is None:
            raise SchemaVersionError(
                f"schema_version {version} tidak didukung: tidak ada migrasi "
                f"dari versi {v} ke {v + 1} (didukung: {SCHEMA_VERSION})"
            )
        doc = migrator(doc)
        v += 1
        doc["schema_version"] = v

    errors = [issue for issue in validate_document(doc) if issue.level == "error"]
    if errors:
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in errors)
        raise ValueError(f"Dokumen tidak valid: {p}: {details}")

    return doc


def save_document(path: str | Path, doc: dict[str, Any]) -> None:
    """Simpan dokumen secara atomik; cadangan .bak bila berkas lama ada.

    Indentasi 2 spasi, urutan kunci dipertahankan, ensure_ascii=False, diakhiri newline.
    Bila gagal, berkas lama utuh dan tidak ada sisa .tmp.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    # File sementara di folder yang sama (agar os.replace di filesystem yang sama)
    fd, tmp_name = tempfile.mkstemp(
        prefix=p.name + ".",
        suffix=".tmp",
        dir=str(p.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())

        if p.exists():
            bak = p.with_name(p.name + ".bak")
            shutil.copy2(p, bak)

        os.replace(tmp_path, p)
    except Exception:
        # Bersihkan sisa .tmp; berkas lama (jika ada) tidak disentuh oleh replace yang gagal
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
