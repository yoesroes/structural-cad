"""Antarmuka plugin elemen struktur (metadata saja pada v1)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jsonschema import Draft202012Validator

from scad.issues import Issue

_REGISTRY: dict[str, "ElementPlugin"] = {}


class ElementPlugin(ABC):
    type_id: str
    type_version: int

    @abstractmethod
    def params_schema(self) -> dict[str, Any]:
        """JSON Schema objek parameter (setara $defs di scad.schema.json)."""

    def default_params(self) -> dict[str, Any]:
        """Nilai awal parameter yang valid; bukan rekomendasi desain."""
        raise NotImplementedError("Plugin harus menyediakan default_params()")

    @abstractmethod
    def faces(self) -> list[str]:
        """Nama muka acuan untuk penempatan tulangan."""

    @abstractmethod
    def overridable_params(self) -> list[str]:
        """Parameter yang boleh ditimpa per instance pile."""

    @abstractmethod
    def local_frame_doc(self) -> str:
        """Penjelasan kerangka koordinat lokal (Bahasa Indonesia)."""


def register_plugin(cls: type[ElementPlugin]) -> type[ElementPlugin]:
    """Daftarkan kelas plugin; gagal bila type_id sudah ada."""
    inst = cls()
    tid = inst.type_id
    if not tid:
        raise ValueError("type_id plugin tidak boleh kosong")
    if tid in _REGISTRY:
        raise ValueError(f"Plugin sudah terdaftar: '{tid}'")
    _REGISTRY[tid] = inst
    return cls


def get_plugin(type_id: str) -> ElementPlugin:
    if type_id not in _REGISTRY:
        raise KeyError(
            f"Tipe elemen tidak dikenal: '{type_id}'. "
            f"Tersedia: {list_plugins()}"
        )
    return _REGISTRY[type_id]


def list_plugins() -> list[str]:
    return sorted(_REGISTRY.keys())


def validate_params(type_id: str, params: dict[str, Any]) -> list[Issue]:
    """Validasi params terhadap params_schema() plugin; path relatif /params."""
    plugin = get_plugin(type_id)
    schema = plugin.params_schema()
    validator = Draft202012Validator(schema)
    issues: list[Issue] = []
    for err in sorted(validator.iter_errors(params), key=lambda e: list(e.path)):
        parts = ["/params"] + [str(p) for p in err.absolute_path]
        path = "/".join(parts) if len(parts) > 1 else "/params"
        issues.append(
            Issue(
                level="error",
                code="SCHEMA",
                path=path,
                message=f"Skema parameter: {err.message}",
            )
        )
    return issues


def _clear_registry_for_tests() -> None:
    """Hanya untuk tes yang perlu mendaftarkan ulang."""
    _REGISTRY.clear()
