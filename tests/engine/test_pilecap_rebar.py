import copy
import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


from scad_engine.clash import find_clashes, segment_distance
from scad_engine.draw import compose, write_dxf, write_svg
from scad_engine.layout import ConfigError, build_groups, hooked_points, n_along, validate_config
from scad_engine.model import BarGroup, BarProto, Instance
from scad_engine.recap import build_recap, reconcile, unit_weight_kg_per_m, write_recap
from scad_engine.section2d import cut_section, default_cut_positions
from scad_engine.step_audit import audit_text

CFG_PATH = ROOT / "examples" / "pilecap.json"


def cfg():
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def groups(c=None):
    return {g.mark: g for g in build_groups(c or cfg())}


class Counts(unittest.TestCase):
    def test_counts(self):
        g = groups()
        self.assertEqual({m: g[m].count for m in g}, {"P1": 83, "P2": 83, "P3": 83, "P4": 83, "P5": 169, "P6": 32})

    def test_83_bars_needs_centerline_positions(self):
        # first bar at 100 (sumbu) and last at 8300 -> (8400-200)/100+1 = 83
        self.assertEqual(n_along(8400 - 2 * 100, 100), 83)
        c = cfg()
        c["cover"]["reference"] = "surface"            # +d/2 di tiap ujung -> hanya 82
        self.assertEqual(groups(c)["P1"].count, 82)

    def test_formula_equals_enumeration_for_every_mark(self):
        for g in groups().values():
            self.assertEqual(g.expected_count, g.count, g.mark)

    def test_symmetric_layout_no_end_gap(self):
        for m in ("P1", "P2", "P3", "P4"):
            lay = groups()[m].layout
            self.assertAlmostEqual(lay["first"], 100.0)
            self.assertAlmostEqual(lay["last"], 8300.0)
            self.assertAlmostEqual(lay["end_gap"], 0.0)

    def test_p6_eight_per_side_four_sides(self):
        g = groups()["P6"]
        self.assertEqual(g.count, 32)
        self.assertEqual({t: sum(1 for i in g.instances if i.tag == t) for t in ("x+", "x-", "y+", "y-")},
                         {"x+": 8, "x-": 8, "y+": 8, "y-": 8})


class Formation(unittest.TestCase):
    def test_vertical_stacking(self):
        g = groups()
        z = {m: g[m].layout["run_z"] for m in ("P1", "P2", "P3", "P4")}
        self.assertAlmostEqual(z["P3"], 2400.0)        # 10 cm dari muka atas (H=2500)
        self.assertAlmostEqual(z["P4"], 250.0)         # 25 cm di atas dasar
        self.assertAlmostEqual(z["P3"] - z["P1"], 19.0)   # P1 tepat di bawah P3 (bersentuhan)
        self.assertAlmostEqual(z["P2"] - z["P4"], 19.0)   # P2 tepat di atas P4
        self.assertGreater(z["P1"], z["P2"])

    def test_opposite_u_directions(self):
        g = groups()
        for m in ("P1", "P3"):                          # U terbalik: kaki berakhir DI BAWAH batang
            self.assertLess(g[m].layout["leg_end_z"], g[m].layout["run_z"])
        for m in ("P2", "P4"):                          # U: kaki berakhir DI ATAS batang
            self.assertGreater(g[m].layout["leg_end_z"], g[m].layout["run_z"])

    def test_lap_zone_is_40d_centered_at_mid_height(self):
        g = groups()
        lo, hi = g["P1"].layout["leg_end_z"], g["P2"].layout["leg_end_z"]
        self.assertAlmostEqual(hi - lo, 40 * 19)
        self.assertAlmostEqual((lo + hi) / 2, 1250.0)

    def test_p1_path_length_hand_calc(self):
        r = 38 + 19 / 2                                  # bend_radii D19 = radius dalam -> sumbu
        straight = 2 * (2381 - 870) + 8200
        self.assertAlmostEqual(groups()["P1"].protos["P1"].path_length(), straight - 2 * r * (2 - math.pi / 2), places=3)


class Hooks(unittest.TestCase):
    def test_tail_is_straight_length_after_bend(self):
        p6 = groups()["P6"].protos["P6.y-"]
        prims = p6.primitives()
        self.assertEqual([k[0] for k in prims], ["L", "A", "L", "A", "L"])
        self.assertAlmostEqual(math.dist(prims[0][1], prims[0][2]), 6 * 16)      # ekor kait 135
        self.assertAlmostEqual(math.dist(prims[4][1], prims[4][2]), 12 * 16)     # ekor kait 90
        self.assertAlmostEqual(math.degrees(prims[1][1].angle), 135.0)
        self.assertAlmostEqual(math.degrees(prims[3][1].angle), 90.0)
        self.assertAlmostEqual(prims[1][1].radius, 56.0)                         # radius tidak dikecilkan

    def test_p6_path_length_hand_calc(self):
        r = 56.0
        # P6 sisi-Y membentang sepanjang X di antara kaki P4 (x = 100 + 19 + 19 = 138, kaki terdalam):
        # tepi dalam kaki = 138 + 9.5, ditambah jari-jari P6 (8) -> 155.5 dari tiap muka
        main = 8400 - 2 * (100 + 19 + 19 + 19 / 2 + 8)
        expected = (main - r * math.tan(math.radians(67.5)) - r * math.tan(math.radians(45))
                    + 96 + 192 + r * math.radians(135) + r * math.radians(90))
        self.assertAlmostEqual(groups()["P6"].protos["P6.y-"].path_length(), expected, places=3)

    def test_hooked_points_turn_convention(self):
        t135 = hooked_points((0, 0, 0), (0, 0, 1000), 160, math.radians(135), (-1, 0, 0),
                             160, math.radians(135), (1, 0, 0), radius=56)
        self.assertLess(t135[3][2], 1000 + 56 * math.tan(math.radians(67.5)))
        self.assertLess(t135[3][2] - 1000, 56 * math.tan(math.radians(67.5)))     # ekor kembali ke bawah

    def test_p6_levels_clear_of_mats_and_staggered(self):
        g = groups()["P6"]
        lv = g.layout["levels"]
        self.assertEqual(len(lv), 8)
        self.assertLessEqual(g.layout["actual_spacing"], 300.0 + 1e-6)
        self.assertGreater(lv[0], 269 + 47.5)           # di atas busur sudut bawah P2
        self.assertLess(lv[-1], 2381 - 47.5)            # di bawah busur sudut atas P1
        zs = {i.tag: i.origin[2] for i in g.instances if abs(i.origin[2] - (lv[0] - 8)) < 1e-6 or abs(i.origin[2] - (lv[0] + 8)) < 1e-6}
        self.assertAlmostEqual(zs["x-"] - zs["y-"], 16.0)


class Clash(unittest.TestCase):
    def test_segment_distance(self):
        self.assertAlmostEqual(segment_distance((0, 0, 0), (10, 0, 0), (5, 3, 0), (5, 3, 10)), 3.0)
        self.assertAlmostEqual(segment_distance((0, 0, 0), (10, 0, 0), (0, 0, 5), (10, 0, 5)), 5.0)

    @staticmethod
    def _pair(gap):
        pa = BarProto("A", "A", 10, ((0, 0, 0), (100, 0, 0)))
        pb = BarProto("B", "B", 10, ((50, -50, gap), (50, 50, gap)))
        return [BarGroup("A", 10, "", {"A": pa}, [Instance("A", (0, 0, 0))]),
                BarGroup("B", 10, "", {"B": pb}, [Instance("B", (0, 0, 0))])]

    def test_touching_is_not_a_clash_but_overlap_is(self):
        self.assertEqual(find_clashes(self._pair(10.0))["total_bar_pairs"], 0)     # sumbu 10 = r+r -> bersentuhan
        self.assertEqual(find_clashes(self._pair(6.0))["total_bar_pairs"], 1)

    def test_default_formation_has_no_clash(self):
        self.assertEqual(find_clashes(build_groups(cfg()).copy())["total_bar_pairs"], 0)

    def test_strict_spec_nesting_reports_edge_bar_clash(self):
        c = cfg()
        c["reinforcement"]["lap_splice"]["nesting"] = "bottom_inside"
        r = find_clashes(build_groups(c))
        self.assertEqual({k: v["bar_pairs"] for k, v in r["by_mark_pair"].items()}, {"P1-P3": 166})


class Recap(unittest.TestCase):
    def test_weights_and_totals(self):
        rows = {r["mark"]: r for r in build_recap(groups().values()) if r["mark"] == "P1"}
        self.assertAlmostEqual(unit_weight_kg_per_m(19), 2.2257, places=3)
        self.assertAlmostEqual(rows["P1"]["total_length_m"], 83 * 11.1812, delta=0.01)

    def test_reconcile_detects_missing_bar(self):
        g = list(groups().values())
        g[2].instances.pop()
        r = reconcile(g)
        self.assertFalse(r["ok"])
        self.assertEqual([c["mark"] for c in r["checks"] if c["status"] != "OK"], ["P3"])

    def test_reconcile_detects_3d_mismatch(self):
        g = list(groups().values())
        placed = {x.mark: x.count for x in g}
        placed["P5"] -= 3
        r = reconcile(g, placed_3d=placed)
        self.assertEqual([c["mark"] for c in r["checks"] if c["status"] != "OK"], ["P5"])

    def test_writes_files(self):
        with tempfile.TemporaryDirectory() as t:
            g = list(groups().values())
            paths = write_recap(g, Path(t), clash=find_clashes(g))
            for k in ("csv", "json", "md"):
                self.assertTrue(paths[k].stat().st_size > 0)
            self.assertIn("P6", paths["csv"].read_text(encoding="utf-8"))
            self.assertIn("tabrakan", paths["md"].read_text(encoding="utf-8"))


class Sections(unittest.TestCase):
    def setUp(self):
        self.g = list(groups().values())

    def test_cut_position_snaps_to_p5_column(self):
        self.assertEqual(default_cut_positions(self.g, 8400, 8400), {"x": 4200.0, "y": 4200.0})

    def test_transverse_cut_counts_and_levels(self):
        r = cut_section(self.g, "x", 4200.0)
        self.assertEqual(r.dot_count("P3"), 83)
        self.assertEqual(r.dot_count("P4"), 83)
        self.assertEqual(r.dot_count("P6"), 16)                   # 2 sisi sejajar X x 8 level
        self.assertEqual(r.stats["P5"]["inplane"], 13)
        self.assertEqual(r.dot_count("P1"), 0)
        z3 = {z for (h, z, d), v in r.dots.items() if "P3" in v["marks"]}
        z4 = {z for (h, z, d), v in r.dots.items() if "P4" in v["marks"]}
        self.assertEqual(z3, {2400.0})
        self.assertEqual(z4, {250.0})
        self.assertEqual(r.stats["P1"]["inplane"], 1)             # P1 pada x=4200 terletak di bidang

    def test_longitudinal_cut_counts_and_levels(self):
        r = cut_section(self.g, "y", 4200.0)
        self.assertEqual(r.dot_count("P1"), 83)
        self.assertEqual(r.dot_count("P2"), 83)
        self.assertEqual(r.dot_count("P6"), 16)
        self.assertEqual({z for (h, z, d), v in r.dots.items() if "P1" in v["marks"]}, {2381.0})
        self.assertEqual({z for (h, z, d), v in r.dots.items() if "P2" in v["marks"]}, {269.0})

    def test_dot_positions_are_true_bar_positions(self):
        r = cut_section(self.g, "x", 4200.0)
        ys = sorted(h for (h, z, d), v in r.dots.items() if "P3" in v["marks"])
        self.assertAlmostEqual(ys[0], 100.0)
        self.assertAlmostEqual(ys[-1], 8300.0)
        self.assertTrue(all(abs((b - a) - 100.0) < 0.2 for a, b in zip(ys, ys[1:])))

    def test_no_mark_is_missing(self):
        for axis in ("x", "y"):
            r = cut_section(self.g, axis, 4200.0)
            self.assertEqual(r.missing, [], axis)
            self.assertEqual(r.marks_drawn(), {"P1", "P2", "P3", "P4", "P5", "P6"})

    def test_missing_mark_is_reported(self):
        outside = cut_section(self.g, "x", -500.0)
        self.assertEqual(set(outside.missing), {"P1", "P2", "P3", "P4", "P5", "P6"})


class Config(unittest.TestCase):
    def test_valid(self):
        validate_config(cfg())

    def test_invalid_reports_all(self):
        c = cfg()
        c["pilecap"]["length"] = -1
        del c["reinforcement"]["P6"]
        c["reinforcement"]["P5"]["hook_angle_deg"] = 300
        c["cover"]["reference"] = "tengah"
        with self.assertRaises(ConfigError) as cm:
            validate_config(c)
        msg = str(cm.exception)
        for token in ("pilecap.length", "P6", "hook_angle_deg", "cover.reference"):
            self.assertIn(token, msg)


class StepAudit(unittest.TestCase):
    SHARED = ("#1 = PRODUCT('P3_0001','x','',(#9));\n#2 = MANIFOLD_SOLID_BREP('a',#5);\n"
              + "".join(f"#{10 + i} = NEXT_ASSEMBLY_USAGE_OCCURRENCE('{i}','P3_{i:04d}','',#1,#2,$);\n" for i in range(1, 101)))
    DUP = "".join(f"#{i} = MANIFOLD_SOLID_BREP('P3_{i:04d}',#5);\n" for i in range(1, 101))

    def test_shared(self):
        a = audit_text(self.SHARED, expected_bars=100, expected_protos=1)
        self.assertIn("DIBAGI", a["instancing_verdict"])
        self.assertEqual(a["instances_by_mark"], {"P3": 100})

    def test_duplicated(self):
        a = audit_text(self.DUP, expected_bars=100, expected_protos=1)
        self.assertIn("DUPLIKAT", a["instancing_verdict"])


class Drawing(unittest.TestCase):
    def setUp(self):
        g = list(groups().values())
        self.rows = build_recap(g)
        self.t, self.l = cut_section(g, "x", 4200.0), cut_section(g, "y", 4200.0)
        self.prims, self.layers = compose(8400, 8400, 2500, self.t, self.l, self.rows)

    def test_drawn_dots_equal_counted_dots(self):
        self.assertEqual(len([p for p in self.prims if p.kind == "circle"]), len(self.t.dots) + len(self.l.dots))

    def test_table_totals(self):
        texts = [p.text for p in self.prims if p.layer == "TABLE"]
        self.assertTrue(any(t.startswith("JUMLAH: 533 batang") for t in texts))      # 4x83 + 169 + 32

    def test_svg_written(self):
        with tempfile.TemporaryDirectory() as t:
            p = write_svg(self.prims, self.layers, Path(t) / "x.svg")
            self.assertIn("<svg", p.read_text(encoding="utf-8")[:200])

    def test_dxf_writer_runs_with_fake_ezdxf(self):
        """Hanya memastikan jalur kode tanpa error; BUKAN bukti kompatibilitas dengan ezdxf asli."""
        calls = []

        class Layers(dict):
            def new(self, name, dxfattribs=None): self[name] = 1

        class Msp:
            def add_line(self, *a, **k): calls.append("line")
            def add_lwpolyline(self, *a, **k): calls.append("poly")
            def add_circle(self, *a, **k): calls.append("circle")
            def add_text(self, *a, **k): calls.append("text")

        class Doc:
            units = None
            layers = Layers()
            def modelspace(self): return Msp()
            def saveas(self, p): calls.append("save")

        fake = types.ModuleType("ezdxf")
        fake.new = lambda v: Doc()
        fake.units = types.SimpleNamespace(MM=4)
        sys.modules["ezdxf"] = fake
        try:
            write_dxf(self.prims, self.layers, Path("x.dxf"))
        finally:
            del sys.modules["ezdxf"]
        self.assertEqual(calls.count("circle"), len([p for p in self.prims if p.kind == "circle"]))
        self.assertIn("save", calls)


if __name__ == "__main__":
    unittest.main()
