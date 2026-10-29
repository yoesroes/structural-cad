"""Model tulangan: SATU sumber data untuk 3D, gambar 2D, dan rekapitulasi.

Konsep:
  - BarProto   : bentuk satu batang (jalur sumbu / centerline) dalam koordinat lokal.
  - Instance   : penempatan satu batang = (kunci proto, titik asal, tag).
  - BarGroup   : semua batang satu mark (P1..P6): proto + daftar instance.

Batang yang berulang TIDAK dibuat sebagai solid terpisah di model; mereka hanya
instance (translasi) dari proto yang sama. Itu yang membuat STEP kecil
(geometri disimpan sekali per proto) dan membuat jumlah batang bisa dihitung
dan diperiksa tanpa membuka CAD.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

Vec = tuple[float, float, float]
EPS = 1e-9


def vsub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vadd(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vmul(a: Vec, k: float) -> Vec:
    return (a[0] * k, a[1] * k, a[2] * k)


def vdot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vlen(a: Vec) -> float:
    return math.sqrt(vdot(a, a))


def vunit(a: Vec) -> Vec:
    n = vlen(a)
    if n < EPS:
        raise ValueError("vektor nol")
    return (a[0] / n, a[1] / n, a[2] / n)


@dataclass(frozen=True)
class Arc3:
    """Busur pembulatan di sudut (3D): dipakai builder CadQuery sebagai busur asli."""
    start: Vec
    mid: Vec
    end: Vec
    center: Vec
    radius: float
    angle: float          # radian, sudut belok


@dataclass(frozen=True)
class BarProto:
    key: str
    mark: str
    diameter: float
    points: tuple[Vec, ...]       # titik sudut jalur sumbu, koordinat lokal
    bend_radius: float = 0.0      # radius SUMBU batang di tiap sudut dalam; 0 = tajam

    def _corner(self, i: int):
        """Info pembulatan di titik ke-i (sudut dalam): (arc | None, sudut belok)."""
        p0, v, p2 = self.points[i - 1], self.points[i], self.points[i + 1]
        din, dout = vunit(vsub(v, p0)), vunit(vsub(p2, v))
        cos_t = max(-1.0, min(1.0, vdot(din, dout)))
        theta = math.acos(cos_t)
        if theta < 1e-6:
            return None, 0.0                       # lurus, bukan sudut
        r = self.bend_radius
        if r <= 0 or theta > math.radians(179):
            return None, theta                     # sudut tajam
        seg_in, seg_out = vlen(vsub(v, p0)), vlen(vsub(p2, v))
        # segmen ujung bebas boleh habis dipakai garis singgung; segmen yang dibagi dua sudut hanya setengahnya
        f_in = 1.0 if i - 1 == 0 else 0.5
        f_out = 1.0 if i + 1 == len(self.points) - 1 else 0.5
        r_eff = min(r, min(f_in * seg_in, f_out * seg_out) / math.tan(theta / 2))
        t = r_eff * math.tan(theta / 2)
        start, end = vsub(v, vmul(din, t)), vadd(v, vmul(dout, t))
        bis = vunit(vsub(dout, din))
        center = vadd(v, vmul(bis, r_eff / math.cos(theta / 2)))
        mid = vadd(center, vmul(vunit(vsub(v, center)), r_eff))
        return Arc3(start, mid, end, center, r_eff, theta), theta

    def primitives(self) -> list[tuple]:
        """Urutan ('L', p0, p1) dan ('A', Arc3) yang menyusun jalur sumbu."""
        out: list[tuple] = []
        cur = self.points[0]
        for i in range(1, len(self.points) - 1):
            arc, theta = self._corner(i)
            v = self.points[i]
            if arc is not None:
                if vlen(vsub(arc.start, cur)) > 1e-7:
                    out.append(("L", cur, arc.start))
                out.append(("A", arc))
                cur = arc.end
            elif theta > 1e-6:                      # sudut tajam
                out.append(("L", cur, v))
                cur = v
        if vlen(vsub(self.points[-1], cur)) > 1e-7:
            out.append(("L", cur, self.points[-1]))
        return out

    def path_length(self) -> float:
        """Panjang jalur sumbu batang (termasuk busur pembulatan)."""
        total = 0.0
        for prim in self.primitives():
            if prim[0] == "L":
                total += vlen(vsub(prim[2], prim[1]))
            else:
                total += prim[1].radius * prim[1].angle
        return total

    def polyline(self, arc_step_deg: float = 15.0) -> list[Vec]:
        """Jalur sumbu sebagai polyline (busur disampel) untuk gambar 2D."""
        pts: list[Vec] = [self.points[0]]
        for prim in self.primitives():
            if prim[0] == "L":
                pts.append(prim[2])
            else:
                a: Arc3 = prim[1]
                n = max(2, math.ceil(math.degrees(a.angle) / arc_step_deg))
                ua = vmul(vsub(a.start, a.center), 1 / a.radius)
                ub = vmul(vsub(a.end, a.center), 1 / a.radius)
                sin_t = math.sin(a.angle)
                for j in range(1, n + 1):
                    s = j / n
                    w1 = math.sin((1 - s) * a.angle) / sin_t
                    w2 = math.sin(s * a.angle) / sin_t
                    pts.append(vadd(a.center, vmul(vadd(vmul(ua, w1), vmul(ub, w2)), a.radius)))
        return pts


@dataclass(frozen=True)
class Instance:
    proto: str
    origin: Vec
    tag: str = ""         # mis. sisi/level, untuk rekap per bagian


@dataclass
class BarGroup:
    mark: str
    diameter: float
    description: str
    protos: dict[str, BarProto]
    instances: list[Instance]
    expected_count: int | None = None      # dari rumus tertutup, TERPISAH dari enumerasi
    spacing: float | None = None
    lap_mm: float = 0.0
    notes: str = ""
    layout: dict = field(default_factory=dict)   # posisi pertama/terakhir, sisa ujung, dll.

    @property
    def count(self) -> int:
        return len(self.instances)

    def placed_polyline(self, inst: Instance, arc_step_deg: float = 15.0) -> list[Vec]:
        return [vadd(p, inst.origin) for p in self.protos[inst.proto].polyline(arc_step_deg)]
