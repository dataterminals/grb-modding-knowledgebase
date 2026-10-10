#!/usr/bin/env python3
"""
terrain_material.py - read Anvil TerrainMaterialBank / TerrainMaterial resources
from Ghost Recon Wildlands (GRW) and Breakpoint (GRB), and convert GRW terrain
materials to GRB's layout by transplanting them onto GRB templates.

    python terrain_material.py list     <forge> <root-cell entry id or name>
    python terrain_material.py convert  --grw-forge F --grw-cell C --grb-forge F --grb-cell C --out DIR
    python terrain_material.py selftest --grw-forge F --grw-cell C --grb-forge F --grb-cell C

Read-only on the forges. `convert` writes one raw GRB TerrainMaterial payload per
GRW bank slot (`<index>_<name>.bin`, 356 B), a GRB-format bank payload
(`TerrainMaterialBank.bin`) that keeps GRW's order, so the `.tbf` material rasters
need no remap, and a `report.json`. Packaging them into a container is a separate
step (see grw2grb.py's build_container).

Where the inputs live (vanilla installs, 2026-10-10):
  GRW: DataPC_GRN_WorldMap_patch_01.forge, entry 116394053711 (Cell21844_DataBlock)
  GRB: DataPC_TGT_WorldMap_Bootstrap_Split.forge,
       entry 10695175151495942175 (MFD_GridCellDataBlock_Cell87380_DataBlock(0x15CE78BD662))

Background and provenance: meta/notes-terrain-tbf.md.

FORMAT (verified on all 169 GRW and 190 GRB materials unless marked):
- Type ids (CRC32 of the name): TerrainMaterialBank 1273578117,
  TerrainMaterial 24265096.
- Bank, identical in both games:
    u64 ClassID | u32 typeId | u8 1 | u32 nDetail | nDetail x ref
    | u32 nMaterials | nMaterials x ref | ref displacement     (ref = u8 kind, u8 0, u64 id)
  A `.tbf` material-raster value k is materials[k].
- TerrainMaterial is fixed-size: GRW 245 B, GRB 356 B. Shared head (0..74):
    u64 ClassID | u32 typeId | 01 00 u64 TextureSet @14 | 5 B @22 | u64 @27
    (unresolved in either game; inferred CompiledData handle) | u32 4 @35
    | 4 x (u8 0, u64 TextureMap) @39 (Diffuse, Normal, Height, Mask1)
  Shared tail: 01 00 u64 ground material @end-18/@end-16 (GRN_Ground_*, IDs shared
  by both games), then u32 Index @end-4 (= bank position, 169/169 and 190/190).
  Hole flag (u8, 1 only on TER-HOLE): GRW @212, GRB @323.
  Tint records, 28 B each (u8 idx, 00 00 f8 00 00 00 00, ed 67 97 a7, 4 x f32):
  GRW 4 at 75+28i (pattern A B A B); GRB 3 at 110+29i (each followed by a u8),
  then 3 at 197+28i.
- INFERRED by value domain (same value sets in both games): GRW f32 @187 <-> GRB @75
  (scale: 1, 0.5, 2 ...), GRW @191 <-> GRB @79 (UV tiling: 200, 100, 20, 400 ...),
  GRW @215/@219/@223 <-> GRB @326/@330/@334 (small signed floats).
  Tint semantics are NOT known: GRW's two colours differ in 154/169 materials,
  GRB's two groups are equal in 137/190. This tool writes GRW colour A to GRB's
  first group and colour B to the second (--tints a to use A for both).
"""
import argparse
import json
import os
import re
import struct
import sys

T_BANK = 1273578117
T_MATERIAL = 24265096
GRW_SIZE, GRB_SIZE = 245, 356
TINT_MARK = bytes.fromhex("ed6797a7")

GRW = dict(size=245, hole=212, ground=229, index=241, scale=187, tiling=191, adj=(215, 219, 223),
           tints=[75 + 28 * i for i in range(4)])
GRB = dict(size=356, hole=323, ground=340, index=352, scale=75, tiling=79, adj=(326, 330, 334),
           tints=[110, 139, 168, 197, 225, 253])


# ---------------------------------------------------------------- banks

def parse_bank(p):
    o = 0
    class_id, type_id = struct.unpack_from("<QI", p, o); o += 12
    flag = p[o]; o += 1

    def refs():
        nonlocal o
        n = struct.unpack_from("<I", p, o)[0]; o += 4
        out = [(p[o + 10 * k], struct.unpack_from("<Q", p, o + 10 * k + 2)[0]) for k in range(n)]
        o += 10 * n
        return out

    details, materials = refs(), refs()
    last = (p[o], struct.unpack_from("<Q", p, o + 2)[0]); o += 10
    if o != len(p) or type_id != T_BANK:
        raise ValueError(f"bank: parsed {o} of {len(p)} bytes, type {type_id}")
    return dict(class_id=class_id, flag=flag, details=details, materials=materials, last=last)


def build_bank(b):
    def refs(rs):
        return struct.pack("<I", len(rs)) + b"".join(struct.pack("<BBQ", k, 0, v) for k, v in rs)
    return (struct.pack("<QIB", b["class_id"], T_BANK, b["flag"]) + refs(b["details"])
            + refs(b["materials"]) + struct.pack("<BBQ", b["last"][0], 0, b["last"][1]))


# ---------------------------------------------------------------- materials

def layout(p):
    if len(p) == GRW_SIZE:
        return GRW
    if len(p) == GRB_SIZE:
        return GRB
    raise ValueError(f"TerrainMaterial of {len(p)} B is neither GRW (245) nor GRB (356)")


def parse_material(p):
    L = layout(p)
    if struct.unpack_from("<I", p, 8)[0] != T_MATERIAL:
        raise ValueError("not a TerrainMaterial")
    for o in L["tints"]:
        if p[o + 8:o + 12] != TINT_MARK:
            raise ValueError(f"tint record marker missing at {o}")
    has_ground = p[L["ground"] - 2:L["ground"]] == b"\x01\x00"
    return dict(
        game="GRW" if L is GRW else "GRB",
        class_id=struct.unpack_from("<Q", p, 0)[0],
        texture_set=struct.unpack_from("<Q", p, 14)[0],
        compiled=struct.unpack_from("<Q", p, 27)[0],
        textures=[struct.unpack_from("<Q", p, 40 + 9 * i)[0] for i in range(4)],
        tints=[struct.unpack_from("<4f", p, o + 12) for o in L["tints"]],
        scale=struct.unpack_from("<f", p, L["scale"])[0],
        tiling=struct.unpack_from("<f", p, L["tiling"])[0],
        adj=[struct.unpack_from("<f", p, o)[0] for o in L["adj"]],
        hole=p[L["hole"]],
        ground=struct.unpack_from("<Q", p, L["ground"])[0] if has_ground else None,
        index=struct.unpack_from("<I", p, L["index"])[0],
    )


def grw_to_grb(grw, template, index, class_id=None, ground=None, id_map=None, tints="ab"):
    """GRB TerrainMaterial (356 B) = GRB `template` with GRW `grw`'s mapped fields.

    Copied from GRW: ClassID (unless class_id), bytes 14..74 (TextureSet, the 5-byte
    field, the @27 handle, the four TextureMaps; ids passed through id_map), scale,
    tiling, the three small floats, Hole, ground (unless ground; GRW materials
    without one keep the template's), and the tints. Index = `index`. All other
    bytes come from the template."""
    if len(grw) != GRW_SIZE or len(template) != GRB_SIZE:
        raise ValueError("need a 245-B GRW material and a 356-B GRB template")
    m = bytearray(template)
    idm = id_map or {}
    struct.pack_into("<Q", m, 0, class_id if class_id is not None else struct.unpack_from("<Q", grw, 0)[0])
    m[12:75] = grw[12:75]
    for o in [14, 27] + [40 + 9 * i for i in range(4)]:
        v = struct.unpack_from("<Q", m, o)[0]
        struct.pack_into("<Q", m, o, idm.get(v, v))
    for a, b in ((GRW["scale"], GRB["scale"]), (GRW["tiling"], GRB["tiling"])) + tuple(zip(GRW["adj"], GRB["adj"])):
        m[b:b + 4] = grw[a:a + 4]
    m[GRB["hole"]] = grw[GRW["hole"]]
    g = ground
    if g is None and grw[GRW["ground"] - 2:GRW["ground"]] == b"\x01\x00":
        g = struct.unpack_from("<Q", grw, GRW["ground"])[0]
    if g is not None:
        m[GRB["ground"] - 2:GRB["ground"]] = b"\x01\x00"
        struct.pack_into("<Q", m, GRB["ground"], g)
    a_rgba = grw[GRW["tints"][0] + 12:GRW["tints"][0] + 28]
    b_rgba = grw[GRW["tints"][1] + 12:GRW["tints"][1] + 28]
    for k, o in enumerate(GRB["tints"]):
        m[o + 12:o + 28] = a_rgba if (k < 3 or tints == "a") else b_rgba
    struct.pack_into("<I", m, GRB["index"], index)
    out = bytes(m)
    parse_material(out)                                   # structural self-check
    return out


# ---------------------------------------------------------------- reading roots

def load_root(forge, cell):
    tools = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, tools)
    import data_inspect as di
    game_dir = os.path.dirname(os.path.abspath(forge))
    oodle = di.Oodle(di.find_oodle(forge))
    for _fid, _name, blob in di.forge_lookup(forge, [str(cell)]):
        meta, files = di.read_container_bytes(blob, oodle)
        res, end = di.walk(files)
        if end != len(files):
            raise ValueError(f"incomplete walk of {cell}")
        return res
    raise SystemExit(f"entry {cell} not found in {forge} ({game_dir})")


def bank_and_materials(res):
    banks = [r for r in res if r.type_id == T_BANK]
    if len(banks) != 1:
        raise ValueError(f"expected one TerrainMaterialBank, found {len(banks)}")
    by_id = {struct.unpack_from("<Q", r.payload, 0)[0]: r for r in res if len(r.payload) >= 8}
    names = {k: r.name for k, r in by_id.items()}
    bank = parse_bank(banks[0].payload)
    mats = [by_id[v] for _, v in bank["materials"]]
    if any(r.type_id != T_MATERIAL for r in mats):
        raise ValueError("bank references something that is not a TerrainMaterial")
    return banks[0], bank, mats, names


def _tokens(name):
    name = re.sub(r"#\w+", "", name.lower())
    stop = {"ter", "roc", "vis", "glo", "yel", "bro", "ora", "red", "gry", "whi", "dar", "gre", "cbs", "tgt"}
    return {w for w in re.split(r"[^a-z]+", name) if w and w not in stop and not re.fullmatch(r"[a-g][a-d]?", w)}


def pick_template(grw_res, grw_fields, grb_mats, ground_alias):
    """Same ground type (after aliasing), then best name-token overlap. Holes -> TER-HOLE."""
    if grw_fields["hole"]:
        return next(r for r in grb_mats if parse_material(r.payload)["hole"])
    pool = [r for r in grb_mats if not r.name.startswith("TER-TGT-") and not parse_material(r.payload)["hole"]]
    g = ground_alias.get(grw_fields["ground"], grw_fields["ground"])
    same = [r for r in pool if parse_material(r.payload)["ground"] == g] or pool
    tw = _tokens(grw_res.name)
    return max(same, key=lambda r: len(tw & _tokens(r.name)) / max(1, len(tw | _tokens(r.name))))


# ---------------------------------------------------------------- commands

def cmd_list(a):
    res = load_root(a.forge, a.cell)
    _, bank, mats, names = bank_and_materials(res)
    print(f"{len(mats)} materials, {len(bank['details'])} detail sets")
    for k, r in enumerate(mats):
        f = parse_material(r.payload)
        print(f"  [{k:3}] {r.name:50} ground {names.get(f['ground'], f['ground'])}"
              f"{'  HOLE' if f['hole'] else ''}  tiling {f['tiling']:g}")


def _ground_alias(grw_names, grb_ground_ids, grb_names):
    """GRW ground ids GRB lacks -> a GRB id (GRN_Ground_Salt -> GRN_Ground_Sand)."""
    by_name = {grb_names.get(i): i for i in grb_ground_ids}
    alias = {}
    for gid, name in grw_names.items():
        if name == "GRN_Ground_Salt" and "GRN_Ground_Sand" in by_name:
            alias[gid] = by_name["GRN_Ground_Sand"]
    return alias


def convert_all(a):
    grw_res, grb_res = load_root(a.grw_forge, a.grw_cell), load_root(a.grb_forge, a.grb_cell)
    _, grw_bank, grw_mats, grw_names = bank_and_materials(grw_res)
    _, _, grb_mats, grb_names = bank_and_materials(grb_res)
    # The GRN_Ground_* objects live in GRW's root cell but not in GRB's; their ids are
    # shared, so GRW's names label GRB's references too.
    grb_names = {**grw_names, **grb_names}
    grb_grounds = {parse_material(r.payload)["ground"] for r in grb_mats}
    grw_grounds = {parse_material(r.payload)["ground"]: None for r in grw_mats}
    alias = _ground_alias({g: grw_names.get(g) for g in grw_grounds if g}, grb_grounds, grb_names)
    out, report = [], []
    for k, r in enumerate(grw_mats):
        f = parse_material(r.payload)
        t = pick_template(r, f, grb_mats, alias)
        g = alias.get(f["ground"])
        if f["ground"] is not None and f["ground"] not in grb_grounds and g is None:
            g = parse_material(t.payload)["ground"]       # unknown to GRB: use the template's
        out.append((k, r.name, grw_to_grb(r.payload, t.payload, k, ground=g, tints=a.tints)))
        report.append(dict(index=k, grw=r.name, template=t.name,
                           grw_ground=grw_names.get(f["ground"], f["ground"]),
                           grb_ground=grb_names.get(g or f["ground"], g or f["ground"]),
                           hole=bool(f["hole"])))
    return grw_bank, out, report, grb_mats


def cmd_convert(a):
    grw_bank, out, report, _ = convert_all(a)
    os.makedirs(a.out, exist_ok=True)
    for k, name, data in out:
        with open(os.path.join(a.out, f"{k:03}_{re.sub(r'[^A-Za-z0-9._-]', '_', name)}.bin"), "wb") as f:
            f.write(data)
    bank = dict(grw_bank, last=(3, 0))        # GRB banks end with a null ref
    with open(os.path.join(a.out, "TerrainMaterialBank.bin"), "wb") as f:
        f.write(build_bank(bank))
    with open(os.path.join(a.out, "report.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(f"wrote {len(out)} GRB TerrainMaterials + TerrainMaterialBank.bin + report.json to {a.out}")


def cmd_selftest(a):
    grw_res, grb_res = load_root(a.grw_forge, a.grw_cell), load_root(a.grb_forge, a.grb_cell)
    ok = {}
    for label, res in (("GRW", grw_res), ("GRB", grb_res)):
        braw, bank, mats, _ = bank_and_materials(res)
        ok[f"{label} bank rebuilds byte-exact"] = build_bank(bank) == braw.payload
        fs = [parse_material(r.payload) for r in mats]
        ok[f"{label} materials parse"] = len(fs)
        ok[f"{label} Index == bank slot"] = sum(f["index"] == k for k, f in enumerate(fs))
        ok[f"{label} holes"] = [r.name for r, f in zip(mats, fs) if f["hole"]]
    grw_bank, out, report, grb_mats = convert_all(a)
    ok["converted"] = len(out)
    ok["converted parse as GRB, Index == slot"] = sum(parse_material(d)["index"] == k for k, _, d in out)
    # twin check: GRW TER-HOLE converted onto GRB TER-HOLE vs GRB TER-HOLE itself
    hole = next((d for k, n, d in out if n == "TER-HOLE"), None)
    grb_hole = next(r.payload for r in grb_mats if r.name == "TER-HOLE")
    if hole:
        diff = [o for o in range(GRB_SIZE) if hole[o] != grb_hole[o]]
        ok["TER-HOLE twin: differing bytes"] = len(diff)
        ok["TER-HOLE twin: differing ranges"] = _ranges(diff)
    for k, v in ok.items():
        print(f"  {k}: {v}")


def _ranges(xs):
    out = []
    for x in xs:
        if out and x == out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return [f"{a}-{b}" if a != b else str(a) for a, b in out]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("forge"); p.add_argument("cell")
    for name in ("convert", "selftest"):
        p = sub.add_parser(name)
        for k in ("--grw-forge", "--grw-cell", "--grb-forge", "--grb-cell"):
            p.add_argument(k, required=True)
        p.add_argument("--tints", choices=("ab", "a"), default="ab")
        if name == "convert":
            p.add_argument("--out", required=True)
    a = ap.parse_args()
    {"list": cmd_list, "convert": cmd_convert, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    main()
