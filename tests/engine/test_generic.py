import json
import math
from pathlib import Path
import unittest

from scad_engine.generic import (
    build_bar_centerline, place_bar, structure_from_dict, section_intersections,
    rotation_xyz, rotate, build_structure_solid, build_bar_solid,
)


class GenericGeometryTests(unittest.TestCase):
    def structure(self, kind="pile_cap", origin=(100, 200, 300), rotation=(0, 0, 0)):
        dims = {"length": 1000, "width": 800, "height": 500} if kind == "pile_cap" else {"diameter": 600, "length": 5000}
        return structure_from_dict({"id": "S1", "type": kind, "dimensions": dims, "origin": origin, "rotation_deg": rotation})

    def test_both_structure_types_validate(self):
        self.assertEqual(self.structure("pile_cap").kind, "pile_cap")
        self.assertEqual(self.structure("bored_pile").kind, "bored_pile")

    def test_all_five_bar_shapes_have_centerlines_and_segments(self):
        examples = {
            "straight": {"length": 1000}, "u": {"width": 400, "height": 300},
            "hook_135_90": {"length": 1000, "tail_a": 100, "tail_b": 120},
            "hook_135_135": {"length": 1000, "tail_a": 100, "tail_b": 100},
            "hook_90_90": {"length": 1000, "tail_a": 100, "tail_b": 100},
        }
        for shape, dims in examples.items():
            with self.subTest(shape=shape):
                b = build_bar_centerline(shape, dims, 16, 30)
                self.assertGreaterEqual(len(b["centerline"]), 2)
                self.assertTrue(all(x > 0 for x in b["segment_lengths"]))
                self.assertEqual(b["diameter"], 16)
                try:
                    import cadquery  # noqa: F401
                except ImportError:
                    continue
                placed = place_bar(self.structure(), b, (100, 100, 100))
                self.assertGreater(build_bar_solid(placed).Volume(), 0)

    def test_local_position_and_rotation(self):
        s = self.structure()
        b = build_bar_centerline("straight", {"length": 100}, 16)
        p = place_bar(s, b, (10, 20, 30), (0, 0, 90))
        self.assertAlmostEqual(p["global_points"][0][0], 110, places=7)
        self.assertAlmostEqual(p["global_points"][0][1], 220, places=7)
        self.assertAlmostEqual(p["global_points"][0][2], 330, places=7)
        self.assertAlmostEqual(p["global_points"][1][0], 110, places=7)
        self.assertAlmostEqual(p["global_points"][1][1], 320, places=7)
        self.assertAlmostEqual(p["global_points"][1][2], 330, places=7)

    def test_structure_rotation_applies_after_bar_local_rotation(self):
        s = self.structure(rotation=(0, 0, 90))
        b = build_bar_centerline("straight", {"length": 100}, 12)
        p = place_bar(s, b, (10, 0, 0), (0, 0, 0))
        self.assertAlmostEqual(p["global_points"][0][0], 100, places=7)
        self.assertAlmostEqual(p["global_points"][0][1], 210, places=7)
        self.assertAlmostEqual(p["global_points"][1][0], 100, places=7)
        self.assertAlmostEqual(p["global_points"][1][1], 310, places=7)

    def test_section_intersection(self):
        s = self.structure(origin=(0,0,0))
        b = build_bar_centerline("straight", {"length": 100}, 12)
        p = place_bar(s, b, (0,0,0))
        cuts = section_intersections(p, "x", 50)
        self.assertEqual(len(cuts), 1)
        self.assertAlmostEqual(cuts[0][0], 50, places=7)

    def test_json_example_parameters_are_used(self):
        cfg = json.loads(
            (Path(__file__).resolve().parents[2] / "examples" / "legacy" / "generic_single_bar.json")
            .read_text()
        )
        s = structure_from_dict(cfg["structure"])
        b = build_bar_centerline(cfg["bar"]["shape"], cfg["bar"]["dimensions"], cfg["bar"]["diameter"], cfg["bar"]["bend_radius"])
        p = place_bar(s, b, cfg["bar"]["position_local"], cfg["bar"]["rotation_deg"])
        self.assertEqual(p["diameter"], 16)
        self.assertAlmostEqual(p["global_points"][0][0], 1300, places=7)
        self.assertAlmostEqual(p["global_points"][0][1], 2400, places=7)

    def test_cadquery_solids_and_step_export(self):
        try:
            import cadquery  # noqa: F401
        except ImportError:
            self.skipTest("CadQuery tidak tersedia")
        from tempfile import TemporaryDirectory
        from scad_engine.generic import export_generic_step
        s = self.structure()
        b = build_bar_centerline("straight", {"length": 100}, 12)
        p = place_bar(s, b, (10,20,30))
        self.assertGreater(build_structure_solid(s).Volume(), 0)
        self.assertGreater(build_bar_solid(p).Volume(), 0)
        with TemporaryDirectory() as td:
            path = Path(td) / "test.step"
            result = export_generic_step(s, [p], str(path))
            self.assertEqual(result["bars"], 1)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)
            self.assertLess(path.stat().st_size, 1_000_000, "STEP satu batang seharusnya tetap ringkas")


    def test_rejects_nonfinite_diameter(self):
        with self.assertRaises(ValueError):
            build_bar_centerline("straight", {"length": 100}, float("nan"), 0)
        with self.assertRaises(ValueError):
            build_bar_centerline("straight", {"length": 100}, float("inf"), 0)

    def test_rejects_nonfinite_bend_radius(self):
        with self.assertRaises(ValueError):
            build_bar_centerline("straight", {"length": 100}, 16, float("nan"))

    def test_turn_angles_alias(self):
        b = build_bar_centerline("u", {"width": 400, "height": 300}, 16, 30)
        self.assertIn("turn_angles_deg", b)
        self.assertEqual(b["turn_angles_deg"], b["bend_angles_deg"])


if __name__ == "__main__":
    unittest.main()
