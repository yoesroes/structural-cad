"""Plugin metadata pile cap."""
from __future__ import annotations

from typing import Any

from scad.plugins.base import ElementPlugin, register_plugin


@register_plugin
class PileCapPlugin(ElementPlugin):
    type_id = "pile_cap"
    type_version = 1

    def params_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "length": {"type": "number", "exclusiveMinimum": 0},
                "width": {"type": "number", "exclusiveMinimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "cover_top": {"type": "number", "minimum": 0},
                "cover_bottom": {"type": "number", "minimum": 0},
                "cover_side_x": {"type": "number", "minimum": 0},
                "cover_side_y": {"type": "number", "minimum": 0},
                "cover_ref": {"enum": ["surface", "centerline"]},
                "lap_nesting": {"enum": ["inside_edge_bars", "bottom_inside", "top_inside"]},
                "lap_ratio_D": {"type": "number", "exclusiveMinimum": 0},
                "lap_mid_height": {"type": "number", "minimum": 0},
            },
            "patternProperties": {"^x_": {}},
            "additionalProperties": False,
            "required": [
                "length",
                "width",
                "height",
                "cover_top",
                "cover_bottom",
                "cover_side_x",
                "cover_side_y",
            ],
        }

    def default_params(self) -> dict[str, Any]:
        """Nilai awal teknis untuk membuat dokumen elemen valid."""
        return {
            "length": 8400,
            "width": 4800,
            "height": 1800,
            "cover_top": 75,
            "cover_bottom": 75,
            "cover_side_x": 75,
            "cover_side_y": 75,
            "cover_ref": "surface",
        }

    def faces(self) -> list[str]:
        return ["top", "bottom", "x-", "x+", "y-", "y+"]

    def overridable_params(self) -> list[str]:
        return []

    def local_frame_doc(self) -> str:
        return (
            "Sudut (0,0,0) di dasar pile cap; sumbu x sepanjang length, "
            "y sepanjang width, z positif ke atas."
        )
