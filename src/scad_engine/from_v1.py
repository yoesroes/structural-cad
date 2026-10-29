"""Jembatan dokumen project v1 → BarGroup (mesin geometri)."""
from __future__ import annotations

import math
from typing import Any

from scad.expr import evaluate
from scad.issues import Issue
from scad.placement import PileEnv, Placed, place_rebar
from scad.zones import resolve_zones
from scad_engine.clash import find_clashes
from scad_engine.model import BarGroup, BarProto, Instance, Vec


def _group_and_instance(doc: dict, pile_id: str) -> tuple[dict, dict]:
    for g in doc.get("groups") or []:
        for inst in g.get("instances") or []:
            if inst.get("id") == pile_id:
                return g, inst
    raise ValueError(f"Pile '{pile_id}' tidak ditemukan")


def _effective_params(group: dict, inst: dict) -> dict[str, float]:
    definition = (group.get("definition") or {}).get("data") or {}
    params = dict(definition.get("params") or {})
    defaults = (group.get("defaults") or {}).get("params") or {}
    params.update(defaults)
    ovr = (inst.get("overrides") or {}).get("params") or {}
    params.update(ovr)
    # pastikan numerik
    out = {}
    for k, v in params.items():
        if isinstance(v, (int, float)):
            out[k] = float(v)
        elif isinstance(v, str) and v.startswith("="):
            out[k] = float(evaluate(v, variables={**params, **out}))
        else:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                pass
    return out


def _build_env(doc: dict, group: dict, inst: dict) -> PileEnv:
    definition = (group.get("definition") or {}).get("data") or {}
    params = _effective_params(group, inst)
    depth = params.get("depth_below_cof")
    if depth is None:
        raise ValueError("depth_below_cof tidak tersedia")
    zone_lengths = (inst.get("overrides") or {}).get("zone_lengths")
    zones = resolve_zones(definition.get("zones") or [], float(depth), zone_lengths)
    rebars = list(definition.get("rebars") or [])
    d_of = {r["id"]: float(r["diameter"]) for r in rebars}
    rebars_by_id = {r["id"]: r for r in rebars}
    return PileEnv(
        diameter=float(params["diameter"]),
        cover=float(params.get("cover", 0)),
        cover_ref=str(params.get("cover_ref") or "surface"),
        depth_below_cof=float(depth),
        zones=zones,
        params=params,
        shapes=dict(doc.get("shapes") or {}),
        settings=dict(doc.get("settings") or {}),
        d_of=d_of,
        rebars_by_id=rebars_by_id,
    )


def _placed_to_groups(placed_by_rebar: dict[str, list[Placed]]) -> list[BarGroup]:
    groups: list[BarGroup] = []
    for rid, items in placed_by_rebar.items():
        if not items:
            continue
        d = items[0].diameter
        # proto per shape_key unik (centerline sama bisa digabung)
        protos: dict[str, BarProto] = {}
        instances: list[Instance] = []
        for p in items:
            if p.shape_key not in protos:
                protos[p.shape_key] = BarProto(
                    key=p.shape_key,
                    mark=rid,
                    diameter=d,
                    points=p.centerline.points,
                    bend_radius=0.0,
                )
            instances.append(Instance(proto=p.shape_key, origin=p.origin, tag=p.tag))
        groups.append(
            BarGroup(
                mark=rid,
                diameter=d,
                description=rid,
                protos=protos,
                instances=instances,
            )
        )
    return groups





def _n_along(span: float, spacing: float) -> int:
    return int(math.floor(span / spacing + 1e-9)) + 1


def _hooked_points(
    a: Vec,
    b: Vec,
    tail_a: float,
    turn_a: float,
    n_a: Vec,
    tail_b: float,
    turn_b: float,
    n_b: Vec,
    radius: float,
) -> tuple[Vec, ...]:
    """Polyline batang berkait (dua ujung) — mandiri, tanpa layout."""

    def unit(v: Vec) -> Vec:
        n = math.sqrt(sum(x * x for x in v))
        if n < 1e-12:
            raise ValueError("vektor nol pada kait")
        return (v[0] / n, v[1] / n, v[2] / n)

    def add(x: Vec, y: Vec) -> Vec:
        return (x[0] + y[0], x[1] + y[1], x[2] + y[2])

    def mul(x: Vec, k: float) -> Vec:
        return (x[0] * k, x[1] * k, x[2] * k)

    u = unit((b[0] - a[0], b[1] - a[1], b[2] - a[2]))

    def end(tail: float, turn: float, normal: Vec, at_start: bool) -> Vec:
        along = -math.cos(turn) if at_start else math.cos(turn)
        ext = tail + radius * math.tan(turn / 2)
        return add(
            a if at_start else b,
            mul(add(mul(u, along), mul(normal, math.sin(turn))), ext),
        )

    return (end(tail_a, turn_a, n_a, True), a, b, end(tail_b, turn_b, n_b, False))


_REQUIRED_PILECAP_MARKS = ("P1", "P2", "P3", "P4", "P5", "P6")


def _pilecap_item(definition: dict, rid: str) -> dict:
    for item in definition.get("rebars") or []:
        if item.get("id") == rid:
            return item
    raise ValueError(f"Tulangan pile cap '{rid}' tidak ditemukan")


def _pilecap_assert_contract(group: dict, inst: dict, definition: dict) -> None:
    """Kontrak H3 tahap template: tanpa defaults/overrides params; mark tepat P1–P6."""
    defaults_params = (group.get("defaults") or {}).get("params") or {}
    if defaults_params:
        keys = ", ".join(sorted(str(k) for k in defaults_params.keys()))
        raise ValueError(
            "pile_cap tidak mengizinkan group.defaults.params "
            f"(ditemukan: {keys})"
        )
    ovr = (inst.get("overrides") or {}).get("params") or {}
    if ovr:
        keys = ", ".join(sorted(str(k) for k in ovr.keys()))
        iid = inst.get("id") or "?"
        raise ValueError(
            "pile_cap tidak mengizinkan instance.overrides.params "
            f"(instance '{iid}', ditemukan: {keys})"
        )

    rebars = definition.get("rebars") or []
    ids = [r.get("id") for r in rebars]
    if None in ids or "" in ids:
        raise ValueError("pile_cap: setiap rebar harus punya id mark")
    seen: dict[str, int] = {}
    for mid in ids:
        seen[str(mid)] = seen.get(str(mid), 0) + 1
    dups = sorted(k for k, n in seen.items() if n > 1)
    if dups:
        raise ValueError(f"Mark tulangan pile_cap duplikat: {dups}")

    idset = set(seen)
    required = set(_REQUIRED_PILECAP_MARKS)
    missing = sorted(required - idset)
    if missing:
        raise ValueError(f"Mark tulangan pile_cap wajib hilang: {missing}")
    foreign = sorted(idset - required)
    if foreign:
        raise ValueError(
            "Mark tulangan pile_cap tidak didukung (template P1–P6 saja): "
            f"{foreign}"
        )


def _pilecap_assert_inside_concrete(
    groups: list[BarGroup],
    length: float,
    width: float,
    height: float,
    tol: float = 1.0,
) -> None:
    """Tolak jika titik centerline (origin + proto) di luar kotak beton [0,L]×[0,W]×[0,H].

    Range arrangement tetap absolut — tidak dikonversi diam-diam ke relatif.
    """
    L, W, H = float(length), float(width), float(height)
    for g in groups:
        for inst in g.instances:
            proto = g.protos.get(inst.proto)
            if proto is None:
                raise ValueError(
                    f"pile_cap: proto '{inst.proto}' tidak ada untuk mark {g.mark}"
                )
            ox, oy, oz = (
                float(inst.origin[0]),
                float(inst.origin[1]),
                float(inst.origin[2]),
            )
            for pt in proto.points:
                x = ox + float(pt[0])
                y = oy + float(pt[1])
                z = oz + float(pt[2])
                if not (
                    -tol <= x <= L + tol
                    and -tol <= y <= W + tol
                    and -tol <= z <= H + tol
                ):
                    raise ValueError(
                        f"Batang {g.mark} di luar beton: titik "
                        f"({x:.1f}, {y:.1f}, {z:.1f}) tidak dalam "
                        f"[0, {L:g}]×[0, {W:g}]×[0, {H:g}] mm "
                        f"(arrangement.range absolut tidak disesuaikan otomatis)"
                    )


def _cover_axis_offset(cover_ref: str, diameter: float) -> float:
    """Geser sumbu dari muka beton: surface → d/2, centerline → 0."""
    if cover_ref == "surface":
        return diameter / 2.0
    return 0.0


def _pilecap_groups_v1(definition: dict) -> list[BarGroup]:
    """Bangun pile cap dari params + RebarItem v1 (tanpa helper privat layout)."""
    p = definition.get("params") or {}
    items = {rid: _pilecap_item(definition, rid) for rid in ("P1", "P2", "P3", "P4", "P5", "P6")}
    L, W, H = float(p["length"]), float(p["width"]), float(p["height"])
    d = {rid: float(items[rid]["diameter"]) for rid in items}
    top, bottom = float(p["cover_top"]), float(p["cover_bottom"])
    sx, sy = float(p["cover_side_x"]), float(p["cover_side_y"])
    cover_ref = str(p.get("cover_ref") or "centerline")

    # Alias param: kanonik cad_h3 + nama dari H3 zip
    ratio = float(p.get("lap_ratio_D") or p.get("lap_ratio") or 40)
    mid = float(p.get("lap_mid_height") or p.get("lap_reference_z") or H / 2)
    nest = p.get("lap_nesting") or p.get("leg_layout") or "inside_edge_bars"

    lap12 = ratio * max(d["P1"], d["P2"])
    lap34 = ratio * max(d["P3"], d["P4"])
    # Layer z (sumbu batang)
    z3 = H - top - _cover_axis_offset(cover_ref, d["P3"])
    z4 = bottom + _cover_axis_offset(cover_ref, d["P4"])
    z1 = z3 - (d["P3"] + d["P1"]) / 2
    z2 = z4 + (d["P4"] + d["P2"]) / 2
    lo12, hi12 = mid - lap12 / 2, mid + lap12 / 2
    lo34, hi34 = mid - lap34 / 2, mid + lap34 / 2

    def item_num(rid: str, key: str, default: float) -> float:
        value = (items[rid].get("shape_params") or {}).get(key, default)
        funcs = {"d_of": lambda name: d[str(name)]}
        if isinstance(value, str):
            return float(evaluate(value, variables={"pi": math.pi, **{k: d[k] for k in d}}, functions=funcs))
        return float(value)

    item_inset = {rid: item_num(rid, "leg_inset", 0.0) for rid in ("P1", "P2", "P3", "P4")}
    if nest == "inside_edge_bars":
        in_top, in_bot = item_inset["P1"], item_inset["P2"]
        in_top34, in_bot34 = item_inset["P3"], item_inset["P4"]
    elif nest == "bottom_inside":
        in_top, in_bot, in_top34, in_bot34 = 0.0, item_inset["P2"], 0.0, item_inset["P4"]
    elif nest == "top_inside":
        in_top, in_bot, in_top34, in_bot34 = item_inset["P1"], 0.0, item_inset["P3"], 0.0
    else:
        raise ValueError(
            "lap_nesting/leg_layout harus inside_edge_bars, bottom_inside, atau top_inside"
        )

    groups: list[BarGroup] = []

    def u_group(
        rid: str,
        along_x: bool,
        z_run: float,
        z_end: float,
        inset: float,
        lap: float,
        upright: bool,
    ) -> BarGroup:
        item = items[rid]
        arr = item["arrangement"]
        rg = arr.get("range") or {}
        start = float(rg.get("from", sx if along_x else sy))
        stop = float(rg.get("to", L - sx if along_x else W - sy))
        spacing = float(arr["spacing"])
        positions = [start + i * spacing for i in range(_n_along(stop - start, spacing))]
        first = sx if along_x else sy
        a0, a1 = (
            (sy + inset, W - sy - inset) if along_x else (sx + inset, L - sx - inset)
        )
        if along_x:
            # batang sejajar Y, berulang sepanjang X
            pts = (
                (0.0, a0, z_run),
                (0.0, a0, z_end),
                (0.0, a1, z_end),
                (0.0, a1, z_run),
            )
            origins = [(x, 0.0, 0.0) for x in positions]
        else:
            # batang sejajar X, berulang sepanjang Y
            pts = (
                (a0, 0.0, z_run),
                (a0, 0.0, z_end),
                (a1, 0.0, z_end),
                (a1, 0.0, z_run),
            )
            origins = [(0.0, y, 0.0) for y in positions]
        bend = 38.0 + d[rid] / 2.0  # setara D19 layout bawaan
        proto = BarProto(rid, rid, d[rid], pts, bend)
        return BarGroup(
            rid,
            d[rid],
            "U terbalik (∩), batang atas" if upright else "U (∪), batang bawah",
            {rid: proto},
            [Instance(rid, o) for o in origins],
            expected_count=len(origins),
            spacing=spacing,
            lap_mm=0.0,
            layout={
                "inset_leg": inset,
                "first": first,
                "last": positions[-1] if positions else first,
                "end_gap": (stop - positions[-1]) if positions else 0.0,
                "along": "X" if along_x else "Y",
            },
        )

    # P1/P2 transverse (along X); P3/P4 longitudinal (along Y)
    groups.append(u_group("P1", True, lo12, z1, in_top, lap12, True))
    groups.append(u_group("P2", True, hi12, z2, in_bot, lap12, False))
    groups.append(u_group("P3", False, lo34, z3, in_top34, lap34, True))
    groups.append(u_group("P4", False, hi34, z4, in_bot34, lap34, False))

    # P5 pengikat vertikal
    p5, d5 = items["P5"], d["P5"]
    p5sp = p5.get("shape_params") or {}
    inset = float(p5sp.get("inset", 600))
    p5_spacing = float((p5.get("arrangement") or {}).get("spacing", 600))
    p5_spacing_y = float(
        (p5.get("arrangement") or {}).get("x_spacing_y")
        or p5sp.get("spacing_y")
        or p5_spacing
    )
    xs = [inset + i * p5_spacing for i in range(_n_along(L - 2 * inset, p5_spacing))]
    ys = [inset + i * p5_spacing_y for i in range(_n_along(W - 2 * inset, p5_spacing_y))]
    zlo, zhi = z4 + d["P4"] / 2, z3 - d["P3"] / 2
    hook_tail_db = float(p5sp.get("hook_tail_length_diameters", 10))
    hook_angle = float(p5sp.get("hook_angle_deg", 135))
    hook_bend_db = float(p5sp.get("hook_bend_diameter_db", 6))
    turn5 = math.radians(hook_angle)
    r5 = (hook_bend_db * d5 + d5) / 2
    protos5 = {}
    for key, sign in (("P5.+", 1.0), ("P5.-", -1.0)):
        protos5[key] = BarProto(
            key,
            "P5",
            d5,
            _hooked_points(
                (0.0, 0.0, zlo),
                (0.0, 0.0, zhi),
                hook_tail_db * d5,
                turn5,
                (-sign, 0.0, 0.0),
                hook_tail_db * d5,
                turn5,
                (sign, 0.0, 0.0),
                r5,
            ),
            r5,
        )
    inst5 = [
        Instance(
            "P5.+" if (round(x / p5_spacing) + round(y / p5_spacing_y)) % 2 == 0 else "P5.-",
            (x, y, 0.0),
        )
        for x in xs
        for y in ys
    ]
    groups.append(
        BarGroup(
            "P5",
            d5,
            "Pengikat vertikal, kait di kedua ujung",
            protos5,
            inst5,
            expected_count=len(inst5),
            spacing=p5_spacing,
        )
    )

    # P6 samping
    p6, d6 = items["P6"], d["P6"]
    p6sp = p6.get("shape_params") or {}
    nlev = int(p6sp.get("levels", 8))
    stagger = d6
    free_lo = (
        max(z2 + (6 * d["P2"] + d["P2"]) / 2, z4 + (6 * d["P4"] + d["P4"]) / 2)
        + stagger / 2
    )
    free_hi = (
        min(z1 - (6 * d["P1"] + d["P1"]) / 2, z3 - (6 * d["P3"] + d["P3"]) / 2)
        - stagger / 2
    )
    levels = [free_lo + i * (free_hi - free_lo) / max(nlev - 1, 1) for i in range(nlev)]
    ta_db = float(p6sp.get("hook_a_tail_db", 6))
    tb_db = float(p6sp.get("hook_b_tail_db", 12))
    ta, tb = ta_db * d6, tb_db * d6
    ra = math.radians(float(p6sp.get("hook_a_angle_deg", 135)))
    rb = math.radians(float(p6sp.get("hook_b_angle_deg", 90)))
    bend_db = float(p6sp.get("hook_bend_diameter_db", 6))
    r6 = (bend_db * d6 + d6) / 2
    off_x = sx + max(in_top34, in_bot34) + d["P3"] / 2 + d6 / 2
    off_y = sy + max(in_top, in_bot) + d["P1"] / 2 + d6 / 2
    faces = {
        "y-": ((off_x, off_y, 0.0), (L - off_x, off_y, 0.0), (0.0, 1.0, 0.0)),
        "y+": ((off_x, W - off_y, 0.0), (L - off_x, W - off_y, 0.0), (0.0, -1.0, 0.0)),
        "x-": ((off_x, off_y, 0.0), (off_x, W - off_y, 0.0), (1.0, 0.0, 0.0)),
        "x+": ((L - off_x, off_y, 0.0), (L - off_x, W - off_y, 0.0), (-1.0, 0.0, 0.0)),
    }
    protos6: dict[str, BarProto] = {}
    inst6: list[Instance] = []
    for tag, (a, b, normal) in faces.items():
        key = f"P6.{tag}"
        protos6[key] = BarProto(
            key,
            "P6",
            d6,
            _hooked_points(a, b, ta, ra, normal, tb, rb, normal, r6),
            r6,
        )
        for zz in levels:
            dz = -stagger / 2 if tag.startswith("y") else stagger / 2
            inst6.append(Instance(key, (0.0, 0.0, zz + dz), tag))
    groups.append(
        BarGroup(
            "P6",
            d6,
            "Tulangan pembagi samping, horizontal di 4 sisi",
            protos6,
            inst6,
            expected_count=len(inst6),
            spacing=(levels[-1] - levels[0]) / max(nlev - 1, 1) if levels else 0.0,
        )
    )
    return groups


def _bar_groups_pile_cap(
    doc: dict, group: dict, definition: dict, inst: dict
) -> list[BarGroup]:
    """Entry pile_cap: template P1–P6; tegakkan kontrak H3 sebelum kuantitas."""
    _pilecap_assert_contract(group, inst, definition)
    groups = _pilecap_groups_v1(definition)
    p = definition.get("params") or {}
    try:
        L, W, H = float(p["length"]), float(p["width"]), float(p["height"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(
            "pile_cap: params length/width/height wajib numerik untuk validasi geometri"
        ) from e
    _pilecap_assert_inside_concrete(groups, L, W, H)
    return groups


def build_bar_groups(doc: dict, pile_id: str) -> list[BarGroup]:
    """Dari project v1 + pile_id → daftar BarGroup per mark tulangan."""
    group, inst = _group_and_instance(doc, pile_id)
    definition = (group.get("definition") or {}).get("data") or {}
    typ = definition.get("type")
    if typ == "pile_cap":
        return _bar_groups_pile_cap(doc, group, definition, inst)
    if typ != "bored_pile":
        raise ValueError(f"Tipe elemen tidak didukung untuk batang: {typ}")
    env = _build_env(doc, group, inst)
    by_rebar: dict[str, list[Placed]] = {}
    for item in definition.get("rebars") or []:
        by_rebar[item["id"]] = place_rebar(item, env)
    return _placed_to_groups(by_rebar)


def _min_clear_spacing(groups: list[BarGroup]) -> float | None:
    """Jarak bersih minimum antar *lokasi* (abaikan pasangan dalam bundel: dist ≈ d)."""
    pts = []
    for g in groups:
        for inst in g.instances:
            pts.append((inst.origin[0], inst.origin[1], g.diameter, g.mark))
    if len(pts) < 2:
        return None
    best = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            # Hanya bandingkan lokasi berbeda; bundel tangensial ditangani di bawah.
            if pts[i][3] != pts[j][3]:
                continue
            dx = pts[i][0] - pts[j][0]
            dy = pts[i][1] - pts[j][1]
            dist = math.hypot(dx, dy)
            d = pts[i][2]
            # bundel tangensial: jarak pusat ≈ d → lewati
            if dist < 1.5 * d:
                continue
            clear = dist - d  # chord antar sumbu - d (satu diameter penuh antar permukaan)
            # konsisten dengan acuan 46.4 = chord - 2*(d/2) untuk d sama = chord - d
            if best is None or clear < best:
                best = clear
    return best


def _polyline_length(points: tuple[tuple[float, float, float], ...]) -> float:
    """Panjang aktual polyline sampel, bukan panjang analitik centerline."""
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def _len_mismatch_issues(placed_by_rebar: dict[str, list[Placed]], tol: float = 0.5) -> list[Issue]:
    issues: list[Issue] = []
    for rid, items in placed_by_rebar.items():
        for p in items:
            if p.cut_length is None:
                continue
            geo = _polyline_length(p.centerline.points)
            meta = p.centerline.meta or {}
            shape_type = "helix" if "turns" in meta else "ring" if "lap" in meta else None
            # Panjang potong cincin mencakup lewatan; bandingkan geometri hanya
            # dengan kelilingnya. Heliks memakai toleransi relatif 0,1%.
            expected_geometry = p.cut_length - float(meta.get("lap", 0.0)) if shape_type == "ring" else p.cut_length
            # Kurva R87/RING memakai toleransi relatif 0,1%; bentuk lain 0,5 mm.
            allowed = max(tol, abs(expected_geometry) * 0.001) if shape_type in {"helix", "ring"} else tol
            if abs(geo - expected_geometry) > allowed:
                issues.append(
                    Issue(
                        level="warning",
                        code="LEN_MISMATCH",
                        path=f"/rebars/{rid}",
                        message=(
                            f"Panjang geometri {geo:.3f} mm berbeda dari cut_length "
                            f"{expected_geometry:.3f} mm (Δ={abs(geo-expected_geometry):.3f}; "
                            f"toleransi {allowed:.3f} mm)"
                        ),
                    )
                )
                break  # satu per mark cukup
    return issues


def _recap_issues_from_groups(doc: dict, pile_id: str, bar_groups: list[BarGroup]) -> list[dict]:
    """RULE_SPACING + clash dari BarGroup (satu sumber dengan builder)."""
    issues: list[dict] = []
    rules = (doc.get("settings") or {}).get("rules") or {}
    min_clear = rules.get("min_clear_spacing")
    if min_clear is not None:
        clear = _min_clear_spacing(bar_groups)
        if clear is not None and clear < float(min_clear) - 1e-6:
            issues.append(
                {
                    "level": "warning",
                    "code": "RULE_SPACING",
                    "path": f"/instances/{pile_id}",
                    "message": (
                        f"Jarak bersih minimum antar batang {clear:.1f} mm "
                        f"< min_clear_spacing {min_clear} mm"
                    ),
                }
            )
    try:
        clashes = find_clashes(bar_groups)
        by_pair = dict(clashes.get("by_mark_pair", {}))
        total_pairs = sum(int(info.get("bar_pairs", 0)) for info in by_pair.values())
        if total_pairs:
            summary = ", ".join(
                f"{name}: {int(info.get('bar_pairs', 0))}"
                for name, info in sorted(by_pair.items())
            )
            issues.append(
                {
                    "level": "warning",
                    "code": "CLASH",
                    "path": f"/instances/{pile_id}",
                    "message": f"{total_pairs} pasangan batang bertabrakan ({summary})",
                    "total_bar_pairs": total_pairs,
                    "by_mark_pair": by_pair,
                }
            )
    except Exception as exc:
        issues.append(
            {
                "level": "warning",
                "code": "CLASH_CHECK_FAILED",
                "path": f"/instances/{pile_id}",
                "message": f"Pemeriksaan tabrakan gagal: {type(exc).__name__}: {exc}",
            }
        )
    return issues


def _rows_from_bar_groups(bar_groups: list[BarGroup]) -> list[dict]:
    """Baris rekap dari BarGroup; pecah per panjang potong (mis. P6 dua sisi)."""
    rows: list[dict] = []
    for g in bar_groups:
        by_len: dict[float, list] = {}
        for inst in g.instances:
            plen = round(g.protos[inst.proto].path_length(), 1)
            by_len.setdefault(plen, []).append(inst)
        for plen, insts in sorted(by_len.items()):
            cut = float(plen) + float(g.lap_mm)
            count = len(insts)
            total_mm = cut * count
            total_m = total_mm / 1000.0
            weight = total_m * (float(g.diameter) ** 2 / 162.2)
            rows.append(
                {
                    "id": g.mark,
                    "mark": g.mark,
                    "diameter": g.diameter,
                    "count": count,
                    "length_mm": round(cut, 3),
                    "cut_length_mm": round(cut, 3),
                    "geometry_length_mm": round(float(plen), 3),
                    "total_length_mm": round(total_mm, 3),
                    "total_length_m": round(total_m, 3),
                    "weight_kg": round(weight, 3),
                }
            )
    return rows


def _recap_pile_cap(doc: dict, pile_id: str) -> dict[str, Any]:
    """Rekap pile_cap dari geometri H3 (build_bar_groups), bukan PileEnv bored-pile."""
    bar_groups = build_bar_groups(doc, pile_id)
    issues = _recap_issues_from_groups(doc, pile_id, bar_groups)
    rows = _rows_from_bar_groups(bar_groups)
    return {"pile_id": pile_id, "rows": rows, "issues": issues}


def recap_pile(doc: dict, pile_id: str) -> dict[str, Any]:
    group, inst = _group_and_instance(doc, pile_id)
    definition = (group.get("definition") or {}).get("data") or {}
    if definition.get("type") == "pile_cap":
        return _recap_pile_cap(doc, pile_id)

    env = _build_env(doc, group, inst)
    by_rebar: dict[str, list[Placed]] = {}
    for item in definition.get("rebars") or []:
        by_rebar[item["id"]] = place_rebar(item, env)

    issues: list[dict] = []
    for iss in _len_mismatch_issues(by_rebar):
        issues.append(
            {"level": iss.level, "code": iss.code, "path": iss.path, "message": iss.message}
        )

    bar_groups = _placed_to_groups(by_rebar)
    issues.extend(_recap_issues_from_groups(doc, pile_id, bar_groups))

    rows = []
    for rid, items in by_rebar.items():
        if not items:
            continue
        first = items[0]
        cut = first.cut_length if first.cut_length is not None else first.centerline.length
        geometry = _polyline_length(first.centerline.points)
        count = len(items)
        total_mm = float(cut) * count
        total_m = total_mm / 1000.0
        weight = total_m * (float(first.diameter) ** 2 / 162.2)
        rows.append(
            {
                "id": rid,
                "mark": rid,
                "diameter": first.diameter,
                "count": count,
                "length_mm": round(float(cut), 3),
                "cut_length_mm": round(float(cut), 3),
                "geometry_length_mm": round(float(geometry), 3),
                "total_length_mm": round(total_mm, 3),
                "total_length_m": round(total_m, 3),
                "weight_kg": round(weight, 3),
            }
        )
    return {"pile_id": pile_id, "rows": rows, "issues": issues}


def recap_group(doc: dict, group_id: str) -> dict[str, Any]:
    g = None
    for gg in doc.get("groups") or []:
        if gg.get("id") == group_id:
            g = gg
            break
    if g is None:
        raise ValueError(f"Grup '{group_id}' tidak ditemukan")
    per_pile = []
    totals: dict[str, dict[str, Any]] = {}
    all_issues: list = []
    for inst in g.get("instances") or []:
        pid = inst["id"]
        r = recap_pile(doc, pid)
        per_pile.append(r)
        all_issues.extend(r["issues"])
        for row in r["rows"]:
            key = row["id"]
            if key not in totals:
                totals[key] = {
                    "id": key,
                    "diameter": row["diameter"],
                    "count": 0,
                    "length_mm": row["length_mm"],
                    "cut_length_mm": row["cut_length_mm"],
                    "geometry_length_mm": row["geometry_length_mm"],
                    "total_length_mm": 0.0,
                    "total_length_m": 0.0,
                    "weight_kg": 0.0,
                }
            totals[key]["count"] += row["count"]
            totals[key]["total_length_mm"] += row["total_length_mm"]
            totals[key]["total_length_m"] += row["total_length_m"]
            totals[key]["weight_kg"] += row["weight_kg"]
    return {
        "group_id": group_id,
        "piles": per_pile,
        "totals": [
            {**row, "total_length_m": round(row["total_length_m"], 3), "weight_kg": round(row["weight_kg"], 3)}
            for row in totals.values()
        ],
        "issues": all_issues,
    }
