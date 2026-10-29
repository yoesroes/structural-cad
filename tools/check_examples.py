"""Memeriksa contoh terhadap skema + aturan lintas-referensi dasar + hash.

Jalankan dari root repo atau: python tools/check_examples.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mini_validate import validate

_SCHEMA = _ROOT / "schemas" / "scad.schema.json"
_SCHEMA_PKG = _ROOT / "core" / "scad" / "data" / "scad.schema.json"
if not _SCHEMA.is_file() and _SCHEMA_PKG.is_file():
    _SCHEMA = _SCHEMA_PKG
S = json.loads(_SCHEMA.read_text(encoding="utf-8"))
load = lambda p: json.loads(Path(p if Path(p).is_absolute() else _ROOT / p).read_text(encoding="utf-8"))
def canon(o):
    def norm(v):
        if isinstance(v, float) and v.is_integer(): return int(v)
        if isinstance(v, dict): return {k: norm(x) for k, x in v.items()}
        if isinstance(v, list): return [norm(x) for x in v]
        return v
    return json.dumps(norm(o), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("OK    " if cond else "GAGAL ") + name)

P, E, L = load("examples/P1.project.json"), load("examples/BP_D1200.elem.json"), load("examples/shapes.builtin.json")
for n, d in (("P1.project.json", P), ("BP_D1200.elem.json", E), ("shapes.builtin.json", L)):
    errs = validate(d, S); check(f"skema valid: {n}", not errs)
    for e in errs[:5]: print("      ", e)
g = P["groups"][0]; data = g["definition"]["data"]
check("hash sumber = hash definisi tertanam", g["definition"]["source"]["hash"] == "sha256:" + hashlib.sha256(canon(data).encode()).hexdigest())
check("definisi tertanam = isi file elemen", data == E["definition"])
check("9 pile P1-1..P1-9", [i["id"] for i in g["instances"]] == [f"P1-{n}" for n in range(1, 10)])
zones = {z["id"] for z in data["zones"]}
check("zona yang dirujuk tulangan ada", all(set(r["extent"]["zones"]) <= zones for r in data["rebars"]))
check("kode bentuk dirujuk ada di project.shapes", all(r["shape"]["code"] in P["shapes"] for r in data["rebars"]))
check("ID tulangan unik", len({r["id"] for r in data["rebars"]}) == len(data["rebars"]))

def mutate(fn):
    d = copy.deepcopy(P); fn(d); return validate(d, S)

def make_linear_without_axis(d):
    """Jadikan arrangement grup linear lalu hapus axis wajib secara aman."""
    arrangement = d["groups"][0]["definition"]["data"]["rebars"][0]["arrangement"]
    arrangement["pattern"] = "linear"
    arrangement.pop("axis", None)

neg = {
 "override diameter per pile ditolak (keputusan: hanya kedalaman & panjang zona)": lambda d: d["groups"][0]["instances"][0].update(overrides={"params": {"diameter": 1000}}),
 "override tulangan per pile ditolak": lambda d: d["groups"][0]["instances"][0].update(overrides={"rebars": {}}),
 "kunci tidak dikenal di tulangan ditolak": lambda d: d["groups"][0]["definition"]["data"]["rebars"][0].update(warna="merah"),
 "count dan spacing bersamaan ditolak": lambda d: d["groups"][0]["definition"]["data"]["rebars"][0]["arrangement"].update(spacing=100),
 "linear tanpa axis ditolak": make_linear_without_axis,
 "panjang zona 0 ditolak": lambda d: d["groups"][0]["definition"]["data"]["zones"][1].update(length=0),
 "bored_pile tanpa depth_below_cof ditolak": lambda d: d["groups"][0]["definition"]["data"]["params"].pop("depth_below_cof"),
 "hash format salah ditolak": lambda d: d["groups"][0]["definition"]["source"].update(hash="abc"),
 "ID dengan spasi ditolak": lambda d: d["groups"][0]["instances"][0].update(id="P1 1"),
 "schema_version 2 ditolak": lambda d: d.update(schema_version=2),
 "ekspresi tanpa '=' pada angka ditolak": lambda d: d["groups"][0]["definition"]["data"]["rebars"][3]["extent"].update(extend_start="40*d"),
}
for name, fn in neg.items(): check(name, mutate(fn))
okx = copy.deepcopy(P); okx["groups"][0]["x_catatan"] = "kunci ekstensi boleh"; check("kunci ekstensi x_ diterima", not validate(okx, S))
print("\nSEMUA LOLOS" if ok else "\nADA YANG GAGAL"); sys.exit(0 if ok else 1)
