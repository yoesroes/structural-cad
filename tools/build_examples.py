"""Membangun schemas/scad.schema.json dan berkas contoh. Jalankan dari akar folder: python tools/build_examples.py"""
import json, hashlib

NUM = {"oneOf": [{"type": "number"}, {"type": "string", "pattern": "^="}], "description": "angka (mm/derajat) atau ekspresi berawalan '='"}
ID = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$"}
def strict(props, required=(), **extra):
    d = {"type": "object", "properties": props, "patternProperties": {"^x_": {}}, "additionalProperties": False}
    if required: d["required"] = list(required)
    d.update(extra); return d
R = lambda n: {"$ref": f"#/$defs/{n}"}
EXPRS = {"type": "string", "pattern": "^="}
pos = {"type": "number", "exclusiveMinimum": 0}
nn = {"type": "number", "minimum": 0}

defs = {
 "Num": NUM, "Id": ID,
 # H5: pitch spiral boleh {by_zone: {Zid: Num}}
 "NumOrByZone": {"oneOf": [
     R("Num"),
     strict({"by_zone": {"type": "object", "additionalProperties": R("Num"), "minProperties": 1}}, ["by_zone"]),
 ], "description": "angka/ekspresi atau peta pitch per zona"},
 "Materials": strict({"concrete": strict({"grade": {"type": "string"}, "type": {"type": "string"}}),
                      "steel": strict({"grade": {"type": "string"}, "type": {"type": "string"}})}),
 "Zone": strict({"id": R("Id"), "side": {"enum": ["above_cof", "below_cof"]},
                 "length": {"oneOf": [pos, {"const": "rest"}]}}, ["id", "length"]),
 "ShapeRef": strict({"code": {"type": "string", "minLength": 1}, "version": {"type": "integer", "minimum": 1}}, ["code"]),
 "Extent": strict({"zones": {"type": "array", "items": R("Id"), "minItems": 1, "uniqueItems": True},
                   "extend_start": R("Num"), "extend_end": R("Num")}, ["zones"]),
 "PositionConcrete": strict({"ref": {"const": "concrete"},
     "face": {"enum": ["outer", "top", "bottom", "x-", "x+", "y-", "y+", "axis"]},
     "offset_type": {"enum": ["clear", "center"]}, "offset": R("Num")}, ["ref", "face", "offset"]),
 "PositionBar": strict({"ref": {"const": "bar"}, "bar": R("Id"),
     "relation": {"enum": ["above", "below", "inside", "outside", "left", "right"]}, "gap": R("Num")}, ["ref", "bar", "relation"]),
 "Position": {"oneOf": [R("PositionConcrete"), R("PositionBar")]},
 "ArrangementSingle": strict({"mode": {"const": "single"}}, ["mode"]),
 "ArrangementGroup": strict({"mode": {"const": "group"}, "pattern": {"enum": ["linear", "polar"]},
     "axis": {"enum": ["x", "y", "z"]}, "by": {"enum": ["count", "spacing"]},
     "count": {"type": "integer", "minimum": 1}, "spacing": R("Num"),
     "range": strict({"from": R("Num"), "to": R("Num")}),
     "align": {"enum": ["start", "center", "end", "fit"]}, "bundle": {"type": "integer", "minimum": 1, "maximum": 4},
     "start_angle_deg": {"type": "number"}}, ["mode", "pattern", "by"],
     allOf=[{"if": {"properties": {"by": {"const": "count"}}}, "then": {"required": ["count"], "not": {"required": ["spacing"]}}},
            {"if": {"properties": {"by": {"const": "spacing"}}}, "then": {"required": ["spacing"], "not": {"required": ["count"]}}},
            {"if": {"properties": {"pattern": {"const": "linear"}}}, "then": {"required": ["axis"]}}]),
 "Arrangement": {"oneOf": [R("ArrangementSingle"), R("ArrangementGroup")]},
 "RebarItem": strict({"id": R("Id"), "mark": {"type": "string"}, "shape": R("ShapeRef"),
     "shape_params": {"type": "object", "additionalProperties": R("NumOrByZone")}, "diameter": pos,
     "steel": {"$ref": "#/$defs/Materials/properties/steel"},
     "orientation": {"enum": ["vertical", "horizontal", "longitudinal", "transverse"]},
     "facing": {"enum": ["inward", "outward", "up", "down", "+x", "-x", "+y", "-y"]},
     "extent": R("Extent"), "position": R("Position"), "arrangement": R("Arrangement"), "notes": {"type": "string"}},
     ["id", "shape", "diameter", "orientation", "extent", "position", "arrangement"]),
 "BoredPileParams": strict({"diameter": pos, "depth_below_cof": pos, "cover": nn, "cover_ref": {"enum": ["surface", "centerline"]}},
                           ["diameter", "depth_below_cof", "cover"]),
 "PileCapParams": strict({"length": pos, "width": pos, "height": pos, "cover_top": nn, "cover_bottom": nn,
                          "cover_side_x": nn, "cover_side_y": nn, "cover_ref": {"enum": ["surface", "centerline"]}},
                         ["length", "width", "height", "cover_top", "cover_bottom", "cover_side_x", "cover_side_y"]),
 "ElementDefinition": strict({"type": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"}, "type_version": {"type": "integer", "minimum": 1},
     "name": {"type": "string"}, "params": {"type": "object"}, "materials": R("Materials"),
     "zones": {"type": "array", "items": R("Zone")}, "rebars": {"type": "array", "items": R("RebarItem")}},
     ["type", "name", "params", "rebars"],
     allOf=[{"if": {"properties": {"type": {"const": "bored_pile"}}}, "then": {"properties": {"params": R("BoredPileParams")}}},
            {"if": {"properties": {"type": {"const": "pile_cap"}}}, "then": {"properties": {"params": R("PileCapParams")}}}]),
 "Builder": {"oneOf": [
     strict({"type": {"const": "straight"}, "length": R("Num")}, ["type", "length"]),
     strict({"type": {"const": "polyline_outside"}, "points": {"type": "array", "minItems": 2, "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": R("Num")}}, "closed": {"type": "boolean"}}, ["type", "points"]),
     strict({"type": {"const": "helix"}, "outer_diameter": R("Num"), "pitch": R("Num"), "height": R("Num")}, ["type", "outer_diameter", "pitch", "height"]),
     strict({"type": {"const": "ring"}, "outer_diameter": R("Num"), "lap": R("Num")}, ["type", "outer_diameter", "lap"])]},
 "ShapeParam": strict({"name": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*$"}, "label": {"type": "string"},
                       "default": R("Num"), "from_extent": {"type": "boolean"}}, ["name"]),
 "Hook": strict({"end": {"enum": ["start", "end"]}, "angle_deg": {"type": "number", "exclusiveMinimum": 0, "maximum": 180}, "tail": R("Num")}, ["end", "angle_deg", "tail"]),
 "ShapeDef": {"anyOf": [
     strict({"code": {"type": "string"}, "version": {"type": "integer", "minimum": 1}, "name": {"type": "string"}, "standard": {"type": ["string", "null"]},
             "params": {"type": "array", "items": R("ShapeParam")}, "builder": R("Builder"), "cut_length": EXPRS,
             "cut_tolerance_per_bend": R("Num"), "notes": {"type": "string"}}, ["code", "version", "name", "params", "builder"]),
     strict({"code": {"type": "string"}, "version": {"type": "integer", "minimum": 1}, "name": {"type": "string"}, "standard": {"type": ["string", "null"]},
             "derived_from": {"type": "string"}, "override": {"type": "object"}, "add_hooks": {"type": "array", "items": R("Hook")}, "notes": {"type": "string"}},
            ["code", "version", "name", "derived_from"])]},
 "Instance": strict({"id": R("Id"), "x": {"type": "number"}, "y": {"type": "number"}, "rotation_deg": {"type": "number"}, "notes": {"type": "string"},
     "overrides": strict({"params": strict({"depth_below_cof": pos}),
                          "zone_lengths": {"type": "object", "propertyNames": R("Id"), "additionalProperties": pos}})},
     ["id", "x", "y"]),
 "Source": {"oneOf": [{"type": "null"}, strict({"file": {"type": "string"}, "hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                                                  "added_at": {"type": "string"}}, ["file", "hash", "added_at"])]},
 "Group": strict({"id": R("Id"), "type": {"type": "string"}, "name": {"type": "string"},
     "definition": strict({"source": R("Source"), "data": R("ElementDefinition")}, ["source", "data"]),
     "naming": strict({"pattern": {"type": "string"}, "start": {"type": "integer"}}, ["pattern"]),
     "defaults": strict({"params": {"type": "object"}}), "instances": {"type": "array", "items": R("Instance"), "minItems": 1}},
     ["id", "type", "definition", "instances"]),
 "ElementFile": strict({"kind": {"const": "element"}, "schema_version": {"const": 1}, "definition": R("ElementDefinition"),
     "shapes": {"type": "object", "additionalProperties": R("ShapeDef")}, "meta": {"type": "object"}}, ["kind", "schema_version", "definition"]),
 "ShapeLibraryFile": strict({"kind": {"const": "shape_library"}, "schema_version": {"const": 1},
     "shapes": {"type": "array", "items": R("ShapeDef")}, "meta": {"type": "object"}}, ["kind", "schema_version", "shapes"]),
 "ProjectFile": strict({"kind": {"const": "project"}, "schema_version": {"const": 1},
     "project": strict({"id": R("Id"), "name": {"type": "string"}, "datum": strict({"cof_elevation": {"type": "number"}})}, ["id", "name"]),
     "settings": strict({"cover_ref": {"enum": ["surface", "centerline"]},
         "bend_inside_radius": strict({"default": R("Num"), "by_diameter": {"type": "object", "additionalProperties": R("Num")}}),
         "rules": strict({"min_clear_spacing": nn, "min_cover": nn, "max_spiral_spacing": nn})}),
     "materials": R("Materials"), "shapes": {"type": "object", "additionalProperties": R("ShapeDef")},
     "groups": {"type": "array", "items": R("Group")}, "meta": {"type": "object"}},
     ["kind", "schema_version", "project", "groups"]),
}
schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://structural-cad.local/schema/v1/scad.schema.json",
          "title": "Structural CAD v1",
          "description": "Pilih entri menurut 'kind': element | project | shape_library. Aturan lintas-referensi ada di validator, bukan di skema.",
          "oneOf": [R("ElementFile"), R("ProjectFile"), R("ShapeLibraryFile")], "$defs": defs}
json.dump(schema, open("schemas/scad.schema.json", "w"), indent=2, ensure_ascii=False)

def canon(o):
    def norm(v):
        if isinstance(v, float) and v.is_integer(): return int(v)
        if isinstance(v, dict): return {k: norm(x) for k, x in v.items()}
        if isinstance(v, list): return [norm(x) for x in v]
        return v
    return json.dumps(norm(o), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
sha = lambda o: "sha256:" + hashlib.sha256(canon(o).encode("utf-8")).hexdigest()

shapes = [
 {"code": "R20", "version": 1, "name": "Lurus", "standard": "BS8666:20", "params": [{"name": "A", "label": "Panjang", "from_extent": True}],
  "builder": {"type": "straight", "length": "=A"}, "cut_length": "=A"},
 {"code": "R87", "version": 2, "name": "Spiral", "standard": "BS8666:87",
  "params": [{"name": "A", "label": "Diameter luar"}, {"name": "B", "label": "Spasi (pitch)"}, {"name": "C", "label": "Tinggi", "from_extent": True}],
  "builder": {"type": "helix", "outer_diameter": "=A", "pitch": "=B", "height": "=C"},
  "cut_length": "=C/B*sqrt((pi*(A-d))*(pi*(A-d))+B*B)",
  "notes": "R87 v2: B boleh skalar atau {by_zone:{Zid:pitch}}. Panjang potong = jumlah per zona L/pitch*sqrt((pi*(A-d))^2+pitch^2)."},
 {"code": "RING", "version": 1, "name": "O-ring", "standard": None,
  "params": [{"name": "A", "label": "Diameter luar"}, {"name": "lap", "label": "Lewatan", "default": "=40*d"}],
  "builder": {"type": "ring", "outer_diameter": "=A", "lap": "=lap"}, "cut_length": "=pi*(A-d)+lap"},
 {"code": "37", "version": 1, "name": "L", "standard": "BS8666:37",
  "params": [{"name": "A", "label": "Kaki A"}, {"name": "B", "label": "Kaki B"}],
  "builder": {"type": "polyline_outside", "points": [["=B", 0], [0, 0], [0, "=A"]]},
  "cut_length": "=A+B-0.5*r-d", "cut_tolerance_per_bend": "=0.25*d"},
 {"code": "X-HOOK-135-90", "version": 1, "name": "Lurus, kait 135 (6d) dan 90 (12d)", "standard": None, "derived_from": "R20",
  "add_hooks": [{"end": "start", "angle_deg": 135, "tail": "=6*d"}, {"end": "end", "angle_deg": 90, "tail": "=12*d"}]},
]
json.dump({"kind": "shape_library", "schema_version": 1, "shapes": shapes}, open("examples/shapes.builtin.json", "w"), indent=2, ensure_ascii=False)
used = {s["code"]: s for s in shapes if s["code"] in ("R20", "R87", "RING")}
MAT = {"concrete": {"grade": "fc30", "type": "readymix"}, "steel": {"grade": "fy420", "type": "ulir"}}
polar = lambda b: {"mode": "group", "pattern": "polar", "by": "count", "count": 28, "bundle": b}
# H5: Z0 cincin B5; di bawah COF satu spiral B2 menerus (by_zone); B3 dihapus; Z0=1280
definition = {
 "type": "bored_pile", "type_version": 1, "name": "Bored pile D1200",
 "params": {"diameter": 1200, "depth_below_cof": 30000, "cover": 75, "cover_ref": "surface"}, "materials": MAT,
 "zones": [
     {"id": "Z0", "side": "above_cof", "length": 1280},
     {"id": "Z1", "length": 3000},
     {"id": "Z2", "length": 8000},
     {"id": "Z3", "length": "rest"},
 ],
 "rebars": [
  {"id": "B1", "shape": {"code": "R20"}, "diameter": 32, "orientation": "vertical",
   "extent": {"zones": ["Z0", "Z1", "Z2"]},
   "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover+d_of('B2')"},
   "arrangement": polar(2)},
  {"id": "B2", "shape": {"code": "R87"}, "diameter": 16, "orientation": "vertical",
   "shape_params": {
       "A": "=diameter-2*cover",
       "B": {"by_zone": {"Z1": 75, "Z2": 200, "Z3": 300}},
   },
   "extent": {"zones": ["Z1", "Z2", "Z3"]},
   "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover"},
   "arrangement": {"mode": "single"}},
  {"id": "B4", "shape": {"code": "R20"}, "diameter": 32, "orientation": "vertical",
   "extent": {"zones": ["Z3"], "extend_start": "=40*d"},
   "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover+d_of('B2')+32"},
   "arrangement": polar(1)},
  {"id": "B5", "shape": {"code": "RING"}, "diameter": 16, "orientation": "horizontal",
   "shape_params": {"A": "=diameter-2*cover", "lap": "=40*d"},
   "extent": {"zones": ["Z0"]},
   "position": {"ref": "concrete", "face": "outer", "offset_type": "clear", "offset": "=cover"},
   "arrangement": {
       "mode": "group", "pattern": "linear", "axis": "z", "by": "spacing",
       "spacing": "=shape_param('B2','B','Z1')",
       "range": {"from": "=shape_param('B2','B','Z1')", "to": "=zone_length('Z0')"},
   }},
 ]}
json.dump({"kind": "element", "schema_version": 1, "definition": definition, "shapes": used}, open("examples/BP_D1200.elem.json", "w"), indent=2, ensure_ascii=False)

H = sha(definition)
xy = [(-3000, -3000), (0, -3000), (3000, -3000), (-3000, 0), (0, 0), (3000, 0), (-3000, 3000), (0, 3000), (3000, 3000)]
ov = {2: {"params": {"depth_below_cof": 26000}}, 5: {"params": {"depth_below_cof": 28500}},
      8: {"params": {"depth_below_cof": 26000}, "zone_lengths": {"Z2": 7000}}}
piles = []
for i, (x, y) in enumerate(xy, 1):
    p = {"id": f"P1-{i}", "x": x, "y": y}
    if i in ov: p["overrides"] = ov[i]
    piles.append(p)
project = {"kind": "project", "schema_version": 1, "project": {"id": "P1", "name": "Pier P1", "datum": {"cof_elevation": 12350}},
  "settings": {"cover_ref": "surface", "bend_inside_radius": {"default": "=2*d", "by_diameter": {"19": 38, "16": 32}}, "rules": {"min_clear_spacing": 75}},
  "materials": MAT, "shapes": used,
  "groups": [{"id": "BP-P1", "type": "bored_pile", "name": "Bored pile pier P1",
              "definition": {"source": {"file": "BP_D1200.elem.json", "hash": H, "added_at": "2026-10-23T09:00:00Z"}, "data": definition},
              "naming": {"pattern": "P1-{n}", "start": 1}, "defaults": {"params": {"depth_below_cof": 30000}}, "instances": piles}],
  "meta": {"created": "2026-10-23T09:00:00Z", "app_version": "0.1"}}
json.dump(project, open("examples/P1.project.json", "w"), indent=2, ensure_ascii=False)

gold = {}
for p in piles:
    o = p.get("overrides", {})
    depth = o.get("params", {}).get("depth_below_cof", 30000)
    zl = {"Z0": 1280, "Z1": 3000, "Z2": 8000}; zl.update(o.get("zone_lengths", {}))
    z3 = depth - zl["Z1"] - zl["Z2"]
    gold[p["id"]] = {"depth_below_cof": depth, "zones": [
        {"id": "Z0", "side": "above_cof", "length": zl["Z0"], "z_top": zl["Z0"], "z_bottom": 0},
        {"id": "Z1", "side": "below_cof", "length": zl["Z1"], "z_top": 0, "z_bottom": -zl["Z1"]},
        {"id": "Z2", "side": "below_cof", "length": zl["Z2"], "z_top": -zl["Z1"], "z_bottom": -zl["Z1"] - zl["Z2"]},
        {"id": "Z3", "side": "below_cof", "length": z3, "z_top": -zl["Z1"] - zl["Z2"], "z_bottom": -depth}]}
json.dump(gold, open("examples/expected_zones.P1.json", "w"), indent=2)
open("tools/.hash", "w").write(H)
print("hash definisi:", H)
print("panjang Z3 per pile:", {k: v["zones"][3]["length"] for k, v in gold.items()})
