"""Plugin metadata bored pile."""
from __future__ import annotations

from typing import Any

from scad.plugins.base import ElementPlugin, register_plugin


@register_plugin
class BoredPilePlugin(ElementPlugin):
    type_id = "bored_pile"
    type_version = 1

    def params_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "diameter": {"type": "number", "exclusiveMinimum": 0},
                "depth_below_cof": {"type": "number", "exclusiveMinimum": 0},
                "cover": {"type": "number", "minimum": 0},
                "cover_ref": {"enum": ["surface", "centerline"]},
            },
            "patternProperties": {"^x_": {}},
            "additionalProperties": False,
            "required": ["diameter", "depth_below_cof", "cover"],
        }

    def default_params(self) -> dict[str, Any]:
        """Nilai awal teknis untuk membuat dokumen elemen valid."""
        return {
            "diameter": 1200,
            "depth_below_cof": 30000,
            "cover": 75,
            "cover_ref": "surface",
        }

    def faces(self) -> list[str]:
        return ["outer", "top", "bottom", "axis"]

    def overridable_params(self) -> list[str]:
        return ["depth_below_cof"]

    def local_frame_doc(self) -> str:
        return (
            "Sumbu pile di (0,0); z = 0 di COF; z positif ke atas. "
            "Kedalaman pile diukur ke arah z negatif (below_cof)."
        )
