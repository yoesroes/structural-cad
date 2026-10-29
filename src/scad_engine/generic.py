"""Fondasi geometri CAD struktur generik; terpisah dari algoritma pilecap_rebar lama.

Semua panjang dalam unit konsisten (contoh: mm). Bentuk batang didefinisikan
sebagai centerline lokal; penempatan menerapkan rotasi Euler XYZ lalu translasi.
Sistem struktur memiliki origin dan rotasi sendiri di koordinat global.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

Vec3 = tuple[float, float, float]
Mat3 = tuple[Vec3, Vec3, Vec3]


def _valid_dims(dims: dict, required: tuple[str, ...]) -> None:
    for k in required:
        if k not in dims or not math.isfinite(float(dims[k])) or float(dims[k]) <= 0:
            raise ValueError(f"dimensions.{k} harus > 0")


def _bored_dims(dims): _valid_dims(dims, ("diameter", "length"))
def _pilecap_dims(dims): _valid_dims(dims, ("length", "width", "height"))


STRUCTURE_BUILDERS = {"bored_pile": _bored_dims, "pile_cap": _pilecap_dims}


def register_structure_type(name: str, validator) -> None:
    """Daftarkan tipe struktur baru dengan fungsi validasi dimensinya."""
    if not name or name in STRUCTURE_BUILDERS: raise ValueError(f"Tipe struktur sudah terdaftar/tidak valid: {name!r}")
    STRUCTURE_BUILDERS[name] = validator


def register_bar_shape(name: str, builder) -> None:
    """Daftarkan pembentuk centerline baru: builder(dimensions) -> sequence 3D points."""
    if not name or name in BAR_SHAPES: raise ValueError(f"Bentuk batang sudah terdaftar/tidak valid: {name!r}")
    BAR_SHAPES[name] = builder


def _vec(v, label="vektor") -> Vec3:
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        raise ValueError(f"{label} harus berisi 3 angka")
    out = tuple(float(x) for x in v)
    if not all(math.isfinite(x) for x in out):
        raise ValueError(f"{label} harus finite")
    return out  # type: ignore[return-value]


def rotation_xyz(deg: Vec3) -> Mat3:
    """Matriks rotasi aktif Rz @ Ry @ Rx; sudut input dalam derajat."""
    x, y, z = (math.radians(float(a)) for a in deg)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return ((cz*cy, cz*sy*sx - sz*cx, cz*sy*cx + sz*sx),
            (sz*cy, sz*sy*sx + cz*cx, sz*sy*cx - cz*sx),
            (-sy, cy*sx, cy*cx))


def rotate(p: Vec3, r: Mat3) -> Vec3:
    return tuple(sum(r[i][j] * p[j] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


@dataclass(frozen=True)
class StructureSpec:
    key: str
    kind: str
    origin: Vec3
    rotation_deg: Vec3
    dimensions: dict[str, float]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructureSpec":
        kind = str(data.get("type", ""))
        dims = data.get("dimensions", {})
        if kind not in STRUCTURE_BUILDERS:
            raise ValueError(f"Tipe struktur tidak dikenal: {kind!r}")
        STRUCTURE_BUILDERS[kind](dims)
        return cls(str(data.get("id", kind)), kind, _vec(data.get("origin", (0,0,0)), "origin"),
                   _vec(data.get("rotation_deg", (0,0,0)), "rotation_deg"),
                   {k: float(v) for k, v in dims.items()})

    def local_to_global(self, point: Vec3) -> Vec3:
        return add(rotate(point, rotation_xyz(self.rotation_deg)), self.origin)


def _line(d: dict) -> tuple[Vec3, ...]:
    length = float(d["length"])
    if not math.isfinite(length) or length <= 0:
        raise ValueError("length bentuk lurus harus finite dan > 0")
    return ((0., 0., 0.), (length, 0., 0.))


def _u(d: dict) -> tuple[Vec3, ...]:
    w, h = float(d["width"]), float(d["height"])
    if not (math.isfinite(w) and math.isfinite(h)) or w <= 0 or h <= 0:
        raise ValueError("width dan height bentuk U harus finite dan > 0")
    # Centerline U dalam bidang XY, terbuka ke arah +Y.
    return ((0., h, 0.), (0., 0., 0.), (w, 0., 0.), (w, h, 0.))


def _double_hook(d: dict, angle_a: float, angle_b: float) -> tuple[Vec3, ...]:
    length, ta, tb = float(d["length"]), float(d.get("tail_a", d.get("tail_length", 0))), float(d.get("tail_b", d.get("tail_length", 0)))
    if length <= 0 or ta < 0 or tb < 0: raise ValueError("length harus > 0 dan panjang kait tidak boleh negatif")
    # Anchor berada di (0,0,0) dan (length,0,0); tail adalah panjang lurus setelah tekukan.
    a = (ta * math.cos(math.radians(angle_a)), ta * math.sin(math.radians(angle_a)), 0.)
    b = (length + tb * math.cos(math.radians(180-angle_b)), tb * math.sin(math.radians(180-angle_b)), 0.)
    return (a, (0.,0.,0.), (length,0.,0.), b)


def _hook_135_90(d): return _double_hook(d, 135., 90.)
def _hook_135_135(d): return _double_hook(d, 135., 135.)
def _hook_90_90(d): return _double_hook(d, 90., 90.)

def _ring(d):
    """Centerline ring tertutup pada bidang XY; radius adalah radius centerline."""
    radius = float(d["radius"])
    segments = int(d.get("segments", 48))
    if not math.isfinite(radius) or radius <= 0 or segments < 12:
        raise ValueError("radius ring harus finite dan > 0; segments minimal 12")
    return tuple((radius * math.cos(2*math.pi*i/segments),
                  radius * math.sin(2*math.pi*i/segments), 0.)
                 for i in range(segments + 1))

BAR_SHAPES = {"straight": _line, "u": _u, "hook_135_90": _hook_135_90,
              "hook_135_135": _hook_135_135, "hook_90_90": _hook_90_90,
              "ring": _ring}


def build_bar_centerline(shape: str, dimensions: dict[str, Any], diameter: float,
                         bend_radius: float = 0.) -> dict[str, Any]:
    """Bangun definisi batang tanpa posisi pemasangan.

    Metadata sudut:
    - turn_angles_deg: perubahan arah lintasan antar segmen (bukan sudut kait detailing).
    - bend_angles_deg: alias kompatibilitas = turn_angles_deg (jangan dipakai sebagai
      sudut kait 90/135 sebelum dikonversi eksplisit).
    """
    if shape not in BAR_SHAPES:
        raise ValueError(f"Bentuk batang tidak dikenal: {shape!r}")
    try:
        d = float(diameter)
        br = float(bend_radius)
    except (TypeError, ValueError) as exc:
        raise ValueError("diameter dan bend_radius harus numerik") from exc
    if not math.isfinite(d) or d <= 0:
        raise ValueError(f"diameter harus finite dan > 0 (diterima: {diameter!r})")
    if not math.isfinite(br) or br < 0:
        raise ValueError(f"bend_radius harus finite dan >= 0 (diterima: {bend_radius!r})")
    pts = BAR_SHAPES[shape](dimensions)
    if len(pts) < 2:
        raise ValueError("centerline memerlukan minimal dua titik")
    lengths = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    if any(v <= 1e-9 for v in lengths):
        raise ValueError("segmen centerline tidak boleh nol")
    # turn_angles_deg = sudut perubahan arah (0 = lurus); bukan sudut interior kait
    turn_angles = []
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        u = tuple((b[i] - a[i]) / math.dist(a, b) for i in range(3))
        v = tuple((c[i] - b[i]) / math.dist(b, c) for i in range(3))
        turn = math.degrees(
            math.acos(max(-1.0, min(1.0, sum(u[i] * v[i] for i in range(3)))))
        )
        turn_angles.append(round(turn, 8))
    return {
        "shape": shape,
        "diameter": d,
        "bend_radius": br,
        "centerline": pts,
        "segment_lengths": lengths,
        "turn_angles_deg": turn_angles,
        "bend_angles_deg": turn_angles,  # alias; lihat docstring
        "polyline_length": sum(lengths),
    }


def place_bar(structure: StructureSpec, bar: dict[str, Any], local_position: Vec3,
              rotation_deg: Vec3 = (0.,0.,0.)) -> dict[str, Any]:
    """Terapkan rotasi batang dalam koordinat lokal struktur, lalu transformasi struktur global."""
    p0, rb = _vec(local_position, "local_position"), rotation_xyz(_vec(rotation_deg, "bar rotation"))
    rs = rotation_xyz(structure.rotation_deg)
    local_points = tuple(add(p0, rotate(tuple(pt), rb)) for pt in bar["centerline"])
    global_points = tuple(add(rotate(pt, rs), structure.origin) for pt in local_points)
    return {"structure_id": structure.key, "shape": bar["shape"], "diameter": bar["diameter"],
            "bend_radius": bar["bend_radius"], "local_points": local_points, "global_points": global_points,
            "segment_lengths": [math.dist(a,b) for a,b in zip(global_points, global_points[1:])]}


def build_structure_solid(structure: StructureSpec):
    """Buat solid CadQuery berorientasi dan berposisi global. CadQuery diimpor secara lazy."""
    import cadquery as cq
    d = structure.dimensions
    if structure.kind == "bored_pile":
        solid = cq.Workplane("XY").circle(d["diameter"]/2).extrude(d["length"]).val()
    elif structure.kind == "pile_cap":
        solid = cq.Workplane("XY").box(d["length"], d["width"], d["height"], centered=(False,False,False)).val()
    else:
        raise NotImplementedError(f"Solid builder belum disediakan untuk tipe {structure.kind!r}")
    # CadQuery uses a rigid Location; Euler angles are applied in XYZ order matching rotation_xyz.
    from OCP.gp import gp_Trsf, gp_Mat, gp_XYZ, gp_Vec
    r = rotation_xyz(structure.rotation_deg)
    tr = gp_Trsf()
    tr.SetValues(r[0][0],r[0][1],r[0][2],structure.origin[0],
                 r[1][0],r[1][1],r[1][2],structure.origin[1],
                 r[2][0],r[2][1],r[2][2],structure.origin[2])
    return solid.transformShape(cq.Matrix(tr))


def build_bar_solid(placed: dict[str, Any]):
    """Bangun solid dari centerline; ring memakai torus asli agar STEP tetap ringkas."""
    import cadquery as cq
    pts = tuple(tuple(float(v) for v in p) for p in placed["global_points"])
    if placed.get("shape") == "ring":
        # The sampled first/last points coincide; infer exact circle center and plane.
        ring_pts = pts[:-1] if len(pts) > 3 and math.dist(pts[0], pts[-1]) < 1e-6 else pts
        center = tuple(sum(p[i] for p in ring_pts)/len(ring_pts) for i in range(3))
        radius = math.dist(center, ring_pts[0])
        a = tuple(ring_pts[1][i]-ring_pts[0][i] for i in range(3))
        b = tuple(ring_pts[2][i]-ring_pts[1][i] for i in range(3))
        normal = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
        norm = math.sqrt(sum(v*v for v in normal))
        if norm <= 1e-12: raise ValueError("Tidak dapat menentukan bidang sengkang ring")
        normal = tuple(v/norm for v in normal)
        return cq.Solid.makeTorus(radius, float(placed["diameter"])/2,
                                  pnt=cq.Vector(*center), dir=cq.Vector(*normal))
    from .model import BarProto
    from .cq_export import proto_solid
    proto = BarProto("generic", "GEN", float(placed["diameter"]), pts,
                     float(placed.get("bend_radius", 0.0)))
    return proto_solid(proto)


def export_generic_step(structure: StructureSpec, bars: list[dict[str, Any]], path: str) -> dict[str, int]:
    """Ekspor struktur dan batang sebagai assembly STEP; satu solid tiap definisi batang unik."""
    import cadquery as cq
    assy = cq.Assembly(name=structure.key)
    assy.add(build_structure_solid(structure), name=f"{structure.key}_structure")
    for i, bar in enumerate(bars, 1):
        assy.add(build_bar_solid(bar), name=f"bar_{i:04d}")
    assy.save(path, exportType="STEP")
    return {"structures": 1, "bars": len(bars)}


def structure_from_dict(data: dict[str, Any]) -> StructureSpec:
    return StructureSpec.from_dict(data)


def section_intersections(placed: dict[str, Any], axis: str, coordinate: float, tol: float = 1e-6) -> list[Vec3]:
    """Potongan centerline dengan bidang x=c atau y=c dalam koordinat global."""
    if axis not in ("x", "y"): raise ValueError("axis harus 'x' atau 'y'")
    idx = 0 if axis == "x" else 1
    out: list[Vec3] = []
    pts = placed["global_points"]
    for a, b in zip(pts, pts[1:]):
        da, db = a[idx] - coordinate, b[idx] - coordinate
        if abs(da) <= tol and abs(db) <= tol:
            out.extend((a, b))
        elif abs(da) <= tol:
            out.append(a)
        elif abs(db) <= tol:
            out.append(b)
        elif da * db < 0:
            t = da / (da - db)
            out.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(3)))
    # deduplicate numerically coincident intersection points
    unique = []
    for p in out:
        if not any(math.dist(p, q) <= tol for q in unique): unique.append(p)
    return unique
