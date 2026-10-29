"""Builder CadQuery: SATU solid per proto, lalu ditempatkan sebagai instance (assembly).

BELUM DIUJI (CadQuery tidak tersedia di lingkungan penulisan). Setelah dijalankan,
periksa hasilnya dengan step_audit (python -m pilecap_rebar.cli --audit file.step).

Prinsip pengecil ukuran STEP:
  1. Satu solid per proto (<= 10 solid untuk pile cap ini), bukan satu per batang.
  2. Penempatan lewat cq.Assembly + cq.Location pada OBJEK SOLID YANG SAMA, sehingga
     penulis XCAF dapat menyimpan geometri sekali dan menulis NEXT_ASSEMBLY_USAGE_OCCURRENCE.
  3. Sudut kait/bengkok memakai busur asli (torus), bukan polyline sampel kasar.
  4. Mode lod: 'full' | 'representative' (awal/tengah/akhir tiap proto) | 'centerline' (hanya
     kurva sumbu, tanpa solid; paling kecil).
"""
from __future__ import annotations

from pathlib import Path

from .model import BarGroup, BarProto, vsub, vunit

COLORS = {"P1": (0.84, 0.15, 0.16), "P2": (0.72, 0.53, 0.04), "P3": (0.12, 0.31, 0.85),
          "P4": (0.09, 0.75, 0.81), "P5": (0.17, 0.63, 0.17), "P6": (0.78, 0.08, 0.52)}


def _path_wire(proto: BarProto):
    import cadquery as cq
    V = lambda p: cq.Vector(*p)
    edges = []
    for prim in proto.primitives():
        if prim[0] == "L":
            edges.append(cq.Edge.makeLine(V(prim[1]), V(prim[2])))
        else:
            a = prim[1]
            edges.append(cq.Edge.makeThreePointArc(V(a.start), V(a.mid), V(a.end)))
    return cq.Wire.assembleEdges(edges)


def proto_solid(proto: BarProto):
    """Solid hasil sweep lingkaran sepanjang jalur sumbu (garis + busur asli)."""
    import cadquery as cq
    first = proto.primitives()[0]
    p0, p1 = (first[1], first[2]) if first[0] == "L" else (first[1].start, first[1].mid)
    plane = cq.Plane(origin=cq.Vector(*proto.points[0]), normal=cq.Vector(*vunit(vsub(p1, p0))))
    path = cq.Workplane(obj=_path_wire(proto))
    return cq.Workplane(plane).circle(proto.diameter / 2).sweep(path, isFrenet=True).val()


def _select(g: BarGroup, lod: str):
    if lod != "representative":
        return list(g.instances)
    by_proto: dict[str, list] = {}
    for inst in g.instances:
        by_proto.setdefault(inst.proto, []).append(inst)
    out = []
    for lst in by_proto.values():
        out += [lst[0], lst[len(lst) // 2], lst[-1]] if len(lst) > 2 else lst
    return out


def build_assembly(groups: list[BarGroup], lod: str = "full", concrete: tuple | None = None):
    """Mengembalikan (cq.Assembly, jumlah_penempatan_per_mark)."""
    import cadquery as cq
    assy = cq.Assembly(name="pilecap")
    placed: dict[str, int] = {}
    if concrete:
        L, W, H = concrete
        assy.add(cq.Workplane("XY").box(L, W, H, centered=False), name="concrete",
                 color=cq.Color(0.8, 0.8, 0.8, 0.3))
    for g in groups:
        solids = {k: proto_solid(p) for k, p in g.protos.items()}      # satu solid per proto
        for i, inst in enumerate(_select(g, lod), 1):
            assy.add(solids[inst.proto], loc=cq.Location(cq.Vector(*inst.origin)),
                     name=f"{g.mark}_{i:04d}", color=cq.Color(*COLORS.get(g.mark, (0.3, 0.3, 0.3))))
            placed[g.mark] = placed.get(g.mark, 0) + 1
    return assy, placed


def export_step(groups: list[BarGroup], path: str | Path, lod: str = "full",
                concrete: tuple | None = None) -> dict[str, int]:
    assy, placed = build_assembly(groups, lod, concrete)
    assy.save(str(path), exportType="STEP")
    return placed


def export_centerline_step(groups: list[BarGroup], path: str | Path) -> dict[str, int]:
    """STEP berisi kurva sumbu saja (tanpa solid): ukuran sangat kecil, cocok untuk cek tata letak."""
    import cadquery as cq
    from cadquery import exporters
    wires, placed = [], {}
    for g in groups:
        base = {k: _path_wire(p) for k, p in g.protos.items()}
        for inst in g.instances:
            wires.append(base[inst.proto].moved(cq.Location(cq.Vector(*inst.origin))))
            placed[g.mark] = placed.get(g.mark, 0) + 1
    exporters.export(cq.Compound.makeCompound(wires), str(path))
    return placed
