"""Dari JSON pile cap -> BarGroup (P1..P6), plus validasi konfigurasi.

Formasi (sesuai penjelasan perancang):
  - Lapisan dari atas ke bawah: P3 (terluar atas) - P1 ... P5 ... P2 - P4 (terluar bawah).
  - P1, P3 = U terbalik (batang atas, kaki turun); P2, P4 = U (batang bawah, kaki naik).
  - Jarak antar batang tepat bersentuhan: P1 tepat di bawah P3; P2 tepat di atas P4.
  - Kaki P1/P2 (dan P3/P4) bertemu pada lewatan 40D yang berpusat di tengah tinggi.
  - Posisi diukur ke SUMBU batang (cover.reference = "centerline", bawaan);
    "surface" menambah d/2 ke tiap posisi.
  - P6: batang horizontal di 4 sisi; satu ujung kait 135 derajat (ekor 6db), ujung lain
    90 derajat (ekor 12db).
"""
from __future__ import annotations

import math
from typing import Any

from .model import BarGroup, BarProto, Instance, Vec, vadd, vmul, vunit, vsub

TOL = 1e-6


def n_along(span: float, spacing: float) -> int:
    """Jumlah posisi pada jarak `spacing` dalam bentang `span` (rumus tertutup)."""
    if span < -TOL:
        return 0
    return int(math.floor(span / spacing + 1e-9)) + 1


class ConfigError(ValueError):
    pass


def validate_config(cfg: dict[str, Any]) -> None:
    errs: list[str] = []

    def need(d: dict, key: str, where: str, positive: bool = True):
        if key not in d:
            errs.append(f"{where}.{key} wajib ada")
            return None
        v = d[key]
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errs.append(f"{where}.{key} harus angka")
            return None
        if positive and v <= 0:
            errs.append(f"{where}.{key} harus > 0")
        return v

    pc, cov, rb = cfg.get("pilecap", {}), cfg.get("cover", {}), cfg.get("reinforcement", {})
    for k in ("length", "width", "height"):
        need(pc, k, "pilecap")
    for k in ("top", "side_longitudinal", "side_transverse", "bottom_from_working_slab"):
        need(cov, k, "cover")
    for m in ("P1", "P2", "P3", "P4"):
        if m not in rb:
            errs.append(f"reinforcement.{m} wajib ada")
            continue
        need(rb[m], "diameter", f"reinforcement.{m}")
        need(rb[m], "spacing", f"reinforcement.{m}")
    if "P5" in rb:
        for k in ("diameter", "spacing_x", "spacing_y", "inset_from_main_rebar_bounds"):
            need(rb["P5"], k, "reinforcement.P5", positive=(k != "inset_from_main_rebar_bounds"))
    else:
        errs.append("reinforcement.P5 wajib ada")
    if "P6" in rb:
        for k in ("diameter", "spacing"):
            need(rb["P6"], k, "reinforcement.P6")
    else:
        errs.append("reinforcement.P6 wajib ada")
    for m in ("P5", "P6"):
        if m in rb:
            a = rb[m].get("hook_angle_deg", 135)
            if not (0 < a <= 180):
                errs.append(f"reinforcement.{m}.hook_angle_deg harus di (0, 180]")
            conv = rb[m].get("hook_angle_convention", "turn")
            if conv not in ("turn", "included"):
                errs.append(f"reinforcement.{m}.hook_angle_convention harus 'turn' atau 'included'")
    if cov.get("reference", "centerline") not in ("centerline", "surface"):
        errs.append("cover.reference harus 'centerline' atau 'surface'")
    if _lap_cfg(cfg).get("nesting", "inside_edge_bars") not in ("inside_edge_bars", "bottom_inside", "top_inside"):
        errs.append("reinforcement.lap_splice.nesting harus 'inside_edge_bars', 'bottom_inside', atau 'top_inside'")
    for k in ("hook_a_angle_deg", "hook_b_angle_deg"):
        if k in rb.get("P6", {}) and not (0 < rb["P6"][k] <= 180):
            errs.append(f"reinforcement.P6.{k} harus di (0, 180]")
    if rb.get("P6", {}).get("levels_alignment", "fit_between_mats") not in ("fit_between_mats", "center", "bottom"):
        errs.append("reinforcement.P6.levels_alignment harus 'fit_between_mats', 'center', atau 'bottom'")
    if not errs and pc and cov and rb:
        L, W, H = pc["length"], pc["width"], pc["height"]
        d19 = rb["P1"]["diameter"]
        if L - 2 * cov["side_longitudinal"] - d19 <= 0 or W - 2 * cov["side_transverse"] - d19 <= 0:
            errs.append("selimut samping terlalu besar untuk dimensi pile cap")
        if H - cov["top"] - cov["bottom_from_working_slab"] <= 0:
            errs.append("selimut atas + bawah melebihi tinggi pile cap")
    if errs:
        raise ConfigError("Konfigurasi tidak valid:\n  - " + "\n  - ".join(errs))


def hooked_points(a: Vec, b: Vec, tail_a: float, turn_a: float, n_a: Vec,
                  tail_b: float, turn_b: float, n_b: Vec, radius: float = 0.0) -> tuple[Vec, ...]:
    """Batang lurus A->B dengan kait di kedua ujung (boleh berbeda sudut dan panjang ekor).

    turn_* : sudut belok kait (radian). Kait 135 derajat = belok 135 derajat.
    n_*    : arah 'ke dalam' (satuan, tegak lurus batang) untuk kait di A dan di B.
    tail_* : panjang bagian LURUS setelah busur bengkok (mis. 6db atau 12db).
    radius : radius sumbu busur. Titik sudut (perpotongan sumbu) ditaruh pada
             tail + radius*tan(turn/2) dari ujung ekor, sehingga ekor lurus tetap = tail.
    Arah ekor di B: cos(t)*u + sin(t)*n_b ; di A: -cos(t)*u + sin(t)*n_a.
    """
    u = vunit(vsub(b, a))
    ext_a = tail_a + radius * math.tan(turn_a / 2)
    ext_b = tail_b + radius * math.tan(turn_b / 2)
    ta = vadd(a, vmul(vadd(vmul(u, -math.cos(turn_a)), vmul(n_a, math.sin(turn_a))), ext_a))
    tb = vadd(b, vmul(vadd(vmul(u, math.cos(turn_b)), vmul(n_b, math.sin(turn_b))), ext_b))
    return (ta, a, b, tb)


def _turn(spec: dict) -> float:
    ang = float(spec.get("hook_angle_deg", 135))
    conv = spec.get("hook_angle_convention", "turn")
    return math.radians(ang if conv == "turn" else 180.0 - ang)


def _hook_radius(spec: dict) -> float:
    d = float(spec["diameter"])
    return (float(spec.get("hook_bend_diameter_db", 6)) * d + d) / 2     # radius SUMBU


def _lap_cfg(cfg: dict) -> dict:
    return cfg.get("reinforcement", {}).get("lap_splice", cfg.get("lap_splice", {}))


def _off(ref: str, d: float) -> float:
    return 0.0 if ref == "centerline" else d / 2


def _inside_radius_to_cl(cfg: dict, d: float) -> float:
    """bend_radii di JSON (mis. D19: 38) dibaca sebagai radius DALAM; radius sumbu = dalam + d/2."""
    r = cfg.get("bend_radii", {}).get(f"D{d:g}")
    return 0.0 if r is None else float(r) + d / 2


def build_groups(cfg: dict[str, Any]) -> list[BarGroup]:
    validate_config(cfg)
    pc, cov, rb = cfg["pilecap"], cfg["cover"], cfg["reinforcement"]
    L, W, H = float(pc["length"]), float(pc["width"]), float(pc["height"])
    ref = cov.get("reference", "centerline")
    sx, sy = float(cov["side_longitudinal"]), float(cov["side_transverse"])
    d1, d2, d3, d4 = (float(rb[m]["diameter"]) for m in ("P1", "P2", "P3", "P4"))
    nest = _lap_cfg(cfg).get("nesting", "inside_edge_bars")   # lihat blok inset di bawah

    # --- tinggi lapisan (z, sumbu batang) ----------------------------------------
    z3 = H - float(cov["top"]) - _off(ref, d3)                 # P3: 10 cm dari muka atas
    z4 = float(cov["bottom_from_working_slab"]) + _off(ref, d4)   # P4: 25 cm dari dasar
    z1 = z3 - (d3 + d1) / 2                                    # P1 tepat di bawah P3
    z2 = z4 + (d4 + d2) / 2                                    # P2 tepat di atas P4
    ls = _lap_cfg(cfg)
    mid = float(ls.get("mid_height_elevation_from_bottom", H / 2))
    ratio = float(ls.get("ratio_D", 40))
    lap12, lap34 = ratio * max(d1, d2), ratio * max(d3, d4)
    groups: list[BarGroup] = []

    def u_group(mark, dia, spacing, along, first, span_first, inset, run_z, end_z, lap, upright, d_pair):
        """U melintang (along='X': bar sejajar Y, berulang sepanjang X) atau memanjang (along='Y')."""
        r = _inside_radius_to_cl(cfg, dia)
        lim = (L if along == "X" else W) - first
        pos, x = [], first
        while x <= lim + 1e-6:
            pos.append(x)
            x += spacing
        # kaki: bagian luar di `lo`, bagian dalam digeser `inset` ke dalam
        a0, a1 = span_first + inset, (W if along == "X" else L) - span_first - inset
        if along == "X":
            pts = ((0, a0, end_z), (0, a0, run_z), (0, a1, run_z), (0, a1, end_z))
            origins = [(p, 0.0, 0.0) for p in pos]
        else:
            pts = ((a0, 0, end_z), (a0, 0, run_z), (a1, 0, run_z), (a1, 0, end_z))
            origins = [(0.0, p, 0.0) for p in pos]
        proto = BarProto(mark, mark, dia, pts, r)
        span = (L if along == "X" else W) - 2 * first
        return BarGroup(
            mark, dia,
            ("U terbalik (∩), batang atas" if upright else "U (∪), batang bawah")
            + (", sejajar Y, berulang sepanjang X" if along == "X" else ", sejajar X, berulang sepanjang Y"),
            {mark: proto}, [Instance(mark, o, "") for o in origins],
            expected_count=n_along(span, spacing), spacing=spacing,
            notes=f"lewatan {ratio:g}D = {lap:g} mm berpusat di z = {mid:g}; sudah termasuk panjang kaki",
            layout={"axis": along, "first": pos[0], "last": pos[-1],
                    "far_cover_line": lim, "end_gap": lim - pos[-1],
                    "run_z": run_z, "leg_end_z": end_z, "inset_leg": inset})

    fx, fy = sx + _off(ref, d1), sy + _off(ref, d1)           # posisi batang pertama ke sumbu
    lo12, hi12 = mid - lap12 / 2, mid + lap12 / 2
    lo34, hi34 = mid - lap34 / 2, mid + lap34 / 2
    # Posisi kaki (inset ke dalam dari garis cover). Dua jenis susunan:
    #  "inside_edge_bars" (bawaan): P1/P2 bersarang (P2 di dalam P1). Kaki P3 digeser ke dalam sejauh
    #       (d1+d3)/2 agar tidak menembus batang tepi P1 (x=100), dan P4 digeser lagi (d3+d4)/2 agar tidak
    #       bentrok dengan P3 dan batang tepi P2. Semua 83 batang tetap simetris, bebas tabrakan.
    #  "bottom_inside" / "top_inside": tepat sesuai spesifikasi (kaki terluar tetap di garis cover),
    #       tetapi batang tepi P1 (atau P2) bertabrakan dengan kaki P3 (atau P4).
    if nest == "inside_edge_bars":
        in_top, in_bot = 0.0, (d1 + d2) / 2
        in_top34 = (d1 + d3) / 2
        in_bot34 = in_top34 + (d3 + d4) / 2
    elif nest == "bottom_inside":
        in_top, in_bot = 0.0, (d1 + d2) / 2
        in_top34, in_bot34 = 0.0, (d3 + d4) / 2
    elif nest == "top_inside":
        in_top, in_bot = (d1 + d2) / 2, 0.0
        in_top34, in_bot34 = (d3 + d4) / 2, 0.0
    else:
        raise ConfigError("lap_splice.nesting harus 'inside_edge_bars', 'bottom_inside', atau 'top_inside'")
    sp = lambda m: float(rb[m]["spacing"])
    # P1 (∩ atas), P2 (∪ bawah): bar sejajar Y, tersebar sepanjang X
    groups.append(u_group("P1", d1, sp("P1"), "X", fx, fy, in_top, z1, lo12, lap12, True, d1))
    groups.append(u_group("P2", d2, sp("P2"), "X", fx, fy, in_bot, z2, hi12, lap12, False, d2))
    # P3 (∩ atas), P4 (∪ bawah): bar sejajar X, tersebar sepanjang Y
    fx3, fy3 = sx + _off(ref, d3), sy + _off(ref, d3)
    groups.append(u_group("P3", d3, sp("P3"), "Y", fy3, fx3, in_top34, z3, lo34, lap34, True, d3))
    groups.append(u_group("P4", d4, sp("P4"), "Y", fy3, fx3, in_bot34, z4, hi34, lap34, False, d4))

    # ---- P5 : pengikat vertikal berkait, grid (aturan prototipe) ---------------------
    p5 = rb["P5"]
    d5 = float(p5["diameter"])
    inset = float(p5["inset_from_main_rebar_bounds"])
    stx, sty = float(p5["spacing_x"]), float(p5["spacing_y"])
    tail5 = max(float(p5.get("hook_tail_length_diameters", 10)) * d5, 1.0)
    turn5, r5 = _turn(p5), _hook_radius(p5)
    zlo, zhi = z4 + d4 / 2, z3 - d3 / 2
    protos5 = {}
    for key, s_ in (("P5.+", 1.0), ("P5.-", -1.0)):
        pts = hooked_points((0, 0, zlo), (0, 0, zhi), tail5, turn5, (-s_, 0, 0), tail5, turn5, (s_, 0, 0), r5)
        protos5[key] = BarProto(key, "P5", d5, pts, r5)
    inst5, xs5, ys5 = [], [], []
    x = inset
    while x <= L - inset + 1e-6:
        xs5.append(x)
        x += stx
    y = inset
    while y <= W - inset + 1e-6:
        ys5.append(y)
        y += sty
    for xx in xs5:
        for yy in ys5:
            s_pos = (round(xx / stx) + round(yy / sty)) % 2 == 0
            inst5.append(Instance("P5.+" if s_pos else "P5.-", (xx, yy, 0.0), ""))
    groups.append(BarGroup("P5", d5, "Pengikat vertikal, kait di kedua ujung", protos5, inst5,
                           expected_count=n_along(L - 2 * inset, stx) * n_along(W - 2 * inset, sty),
                           spacing=stx,
                           layout={"nx": len(xs5), "ny": len(ys5), "spacing_x": stx, "spacing_y": sty,
                                   "xs": xs5, "ys": ys5}))

    # ---- P6 : tulangan pembagi samping, batang horizontal, kait 135 + 90 -------------
    p6 = rb["P6"]
    d6, sp6 = float(p6["diameter"]), float(p6["spacing"])
    ta_, tb_ = float(p6.get("hook_a_tail_db", 6)) * d6, float(p6.get("hook_b_tail_db", 12)) * d6
    turn_a = math.radians(float(p6.get("hook_a_angle_deg", 135)))
    turn_b = math.radians(float(p6.get("hook_b_angle_deg", 90)))
    r6 = _hook_radius(p6)
    # Level P6. bawaan "fit_between_mats": merata di ruang bebas antara lapisan P2 (bawah) dan P1 (atas),
    # jarak sebenarnya <= jarak nominal. Selisih tinggi `stagger` (= d6) antara sisi-X dan sisi-Y
    # mencegah batang di sudut pada level yang sama saling berimpit.
    mode = p6.get("levels_alignment", "fit_between_mats")
    stagger = d6 if p6.get("stagger_corner_levels", True) else 0.0
    rc = lambda dd: max(_inside_radius_to_cl(cfg, dd), dd / 2 + d6 / 2)     # jarak aman dari sudut bengkok
    z_free_lo = max(z2 + rc(d2), z4 + rc(d4)) + stagger / 2     # di atas busur sudut bawah P2/P4
    z_free_hi = min(z1 - rc(d1), z3 - rc(d3)) - stagger / 2     # di bawah busur sudut atas P1/P3
    free = z_free_hi - z_free_lo
    if "count_per_side" in p6:
        n_lev = int(p6["count_per_side"])
        levels = [z_free_lo + k * free / max(n_lev - 1, 1) for k in range(n_lev)]
    elif mode == "fit_between_mats":
        n_lev = int(math.ceil(free / sp6 - 1e-9)) + 1
        levels = [z_free_lo + k * free / (n_lev - 1) for k in range(n_lev)]
    elif mode == "bottom":
        n_lev = n_along(z3 - z4, sp6)
        levels = [z4 + k * sp6 for k in range(n_lev)]
    else:                                                # "center": jarak nominal, rata di antara P4 dan P3
        n_lev = n_along(z3 - z4, sp6)
        z0 = z4 + ((z3 - z4) - (n_lev - 1) * sp6) / 2
        levels = [z0 + k * sp6 for k in range(n_lev)]
    actual_sp = (levels[-1] - levels[0]) / (len(levels) - 1) if len(levels) > 1 else 0.0
    # bidang batang P6: di sisi dalam kaki terdalam (P2/P4 atau P1/P3)
    leg_in_x = fx3 + max(in_top34, in_bot34)
    leg_in_y = fy + max(in_top, in_bot)
    off_x = leg_in_x + d3 / 2 + d6 / 2
    off_y = leg_in_y + d1 / 2 + d6 / 2
    xa, xb, ya, yb = off_x, L - off_x, off_y, W - off_y
    faces = {
        "y-": ((xa, ya, 0), (xb, ya, 0), (0, 1, 0)),
        "y+": ((xa, yb, 0), (xb, yb, 0), (0, -1, 0)),
        "x-": ((xa, ya, 0), (xa, yb, 0), (1, 0, 0)),
        "x+": ((xb, ya, 0), (xb, yb, 0), (-1, 0, 0)),
    }
    protos6, inst6 = {}, []
    for tag, (a, b, n) in faces.items():
        key = f"P6.{tag}"
        protos6[key] = BarProto(key, "P6", d6, hooked_points(a, b, ta_, turn_a, n, tb_, turn_b, n, r6), r6)
        dz = -stagger / 2 if tag.startswith("y") else stagger / 2
        for zz in levels:
            inst6.append(Instance(key, (0.0, 0.0, zz + dz), tag))
    groups.append(BarGroup(
        "P6", d6, "Tulangan pembagi samping, horizontal di 4 sisi (kait 135° dan 90°)",
        protos6, inst6, expected_count=4 * (int(p6["count_per_side"]) if "count_per_side" in p6 else (
            int(math.ceil(free / sp6 - 1e-9)) + 1 if mode == "fit_between_mats" else n_along(z3 - z4, sp6))),
        spacing=round(actual_sp, 1),
        notes=(f"ekor kait 135° = {ta_:g} mm (6db), kait 90° = {tb_:g} mm (12db); "
               f"jarak nominal {sp6:g} mm, jarak terpasang {actual_sp:.1f} mm"),
        layout={"levels": levels, "faces": list(faces), "per_side": n_lev, "nominal_spacing": sp6,
                "actual_spacing": actual_sp, "free_span": free}))
    return groups
