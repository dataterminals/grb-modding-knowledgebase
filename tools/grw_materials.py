#!/usr/bin/env python3
"""
grw_materials.py - convert Ghost Recon Wildlands (GRW) Materials and their
TextureSets to Breakpoint (GRB), choosing the GRB MaterialTemplate, texture slots
and parameters the way Ubisoft did for the meshes both games share.

    python grw_materials.py templates                         # GRW template -> GRB target, with evidence
    python grw_materials.py convert MAT.bin TS.bin|- OUT.bin [--ts-out TS_OUT.bin] [--map MAP.json]
                                    [--target ID] [--fallback ID]
    python grw_materials.py learn    --grw INSTALL --grb INSTALL  # rebuild grw_materials_rules.json
    python grw_materials.py selftest --grw INSTALL --grb INSTALL  # round-trips + held-out twin check

    from grw_materials import convert_pair
    grb_mat, grb_ts, report = convert_pair(grw_mat_payload, grw_ts_payload_or_None, id_map)
    # id_map = {grw TextureMap id: grb id, or None}; grb_ts is the converted set, or one
    # synthesized from the selectors when GRW had none (GRB renders null sets magenta)

Payloads are raw resource payloads (data_inspect.walk()'s `r.payload`), not
containers. Read-only on the forges. The rule tables live in
grw_materials_rules.json next to this file: `learn` derives them from the twins,
and `templates` prints them. Evidence and open questions: meta/notes-materials.md.

TEXTURE ID MAP: an id in the map becomes map[id]; None or 0 there means "not
shipped" and leaves a null reference (`03` + 9 zero bytes). An id absent from the
map is kept as is (shared class-a and kept class-c ids, see notes-id-collisions.md);
pass strict=True to raise on it instead.

TWINS: a Mesh entry id present in both installs (GRW DataPC*.forge, GRB
DataPC_Resources*.forge; 1,315 on the 2026-10-10 installs). Inside each pair of
containers, a GRW and a GRB Material that reference at least one common
TextureMap (ids >= 4096, so the engine defaults do not count) are a *conversion*.
Positional pairs that share no texture are Ubisoft swapping in a GRB library
material (`*_CONVERT`, BAS_GEN_MetalRustA, ...), not converting, and are ignored.

FORMAT (verified on every harvested material: 409 GRW, 367 GRB; parse -> build is
byte-exact on all that parse, see `selftest`):
  Material  u64 ClassID | u32 0x85C817C3 | u8 1 | FileRef template @13
            | FileRef TextureSet @23 | Mask object @33 (u64 0xF8000000, u32 0xDF5D6C0E,
            u8) | i32 BlendMode @46 | i32 AlphaDisplayMode @50 | flags @54
            | FileRef backface | MaterialMatchMask object (u64 0xF8000001,
            u32 0x92B95F74, 16 B) | [GRW only: i32 Category] | u32 n | n x param
    GRW: 22 flag bytes, Category, params @118.  GRB: 29 flag bytes, params @121.
    GRB flags = GRW[0:10] + 0 + GRW[10:14] + 0 x5 + GRW[14:21] + 0 + GRW[21]
    (ATK's GRB flag order; 5,156/5,170 flag bytes agree over 235 conversions).
  FileRef   u8 1 | u8 IsGlobal | u64 id, or null = 03 00 + 8 zero bytes (10 B).
            Material template refs are written `01 01`, TextureSet refs `01 00`.
  param     u32 nameHash | u32 DataType | u32 Type | u32 unk | value
    nameHash = CRC32 of the template's display label *with* its category prefix,
    e.g. crc32("0: Layer1 Albedo Map") = 0xE81E62B3 (labels are plain strings in
    the MaterialTemplate payloads).
    Type 0x1C0000 Reference: 10 B (kind 1/3) or 9 B (kind 2/5);
    Type 0x130000 inline object: TextureSelector (DataType 0x7D08460D) 53 B,
    UVTransform (0xC52E2125) 46 B, TimeOscillatorData (0xECE5D96C) 36 B (ATK
    reads u32 type + 3 x f32 after the 12-byte object head; 8 more bytes follow
    in both games - the only size that parses all 409 + 367); scalar sizes in SIZES.
  TextureSelector  u64 objectId | u32 0x7D08460D | u8 | i32 method @13
            | i32 mapType @17 | i32 frame @21 | FileRef TextureSet @25
            | FileRef TextureMap @35 | u64 @45
    method 0 = MaterialTextureSet: the TextureMap ref is a cached copy of the
    material TextureSet's slot[mapType] (GRW 749/749 resolvable, GRB 679/679).
    1 = the selector's own TextureSet, 2 = an explicit TextureMap.
  TextureSet (same layout in both games, 202 B)
            u64 ClassID | u32 0xD70E6670 | u8 1 | 18 x FileRef @13 | u8 0 | u64 source
    slots: Diffuse Normal Specular OffsetBump Emissive Transmission Occlusion Mask1
    Mask2 Cookie EnvLighting Generic Diffuse1-5 VectorDisplace (mapType = slot).
"""
import argparse
import collections
import glob
import json
import os
import re
import struct
import sys
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

RULES_PATH = os.path.join(_HERE, "grw_materials_rules.json")

GRW, GRB = "grw", "grb"
MATERIAL_TYPE = 0x85C817C3
TEXTURESET_TYPE = 0xD70E6670
MASK_TYPE = 0xDF5D6C0E
MATCHMASK_TYPE = 0x92B95F74
TEXSEL = 0x7D08460D            # CRC32("TextureSelector")
UVT = 0xC52E2125
OSC = 0xECE5D96C               # TimeOscillatorData: u32 type, f32 frequency, amplitude, time bias, 8 B
REF, OBJ = 0x1C0000, 0x130000
OBJ_SIZES = {TEXSEL: 53, UVT: 46, OSC: 36}
SIZES = {0: 1, 65536: 1, 131072: 1, 196608: 1, 262144: 2, 327680: 2, 393216: 4, 458752: 4,
         524288: 8, 589824: 8, 655360: 4, 720896: 8, 786432: 12, 851968: 16, 917504: 16,
         983040: 36, 1048576: 64, 1114112: 8, 1179648: 9, 1638400: 4}
LAYOUT = {GRW: dict(flags=22, category=True, params=118),
          GRB: dict(flags=29, category=False, params=121)}
NEW_FLAGS = (10, 15, 16, 17, 18, 19, 27)    # GRB flag bytes with no GRW counterpart (0 in all twins)
TS_SLOTS = ("Diffuse Normal Specular OffsetBump Emissive Transmission Occlusion Mask1 Mask2 "
            "Cookie EnvLighting Generic Diffuse1 Diffuse2 Diffuse3 Diffuse4 Diffuse5 "
            "VectorDisplace").split()
LOCAL_OBJ = 0xF8000002          # first free local inline-object id (0xF8000000/1 are Mask/MatchMask)
DEFAULT_TEX = 4096              # ids below this are engine defaults (Default Normal Texture = 9, ...)

# forge entry type ids (CRC32 of the type name)
T_MESH, T_MATERIAL, T_TEXTURESET, T_TEMPLATE = 1096652136, 2244483011, 3608045168, 3170581626


class NoEvidence(ValueError):
    """The GRW template has no twin conversion to learn a GRB target from."""


def _u32(p, o):
    return struct.unpack_from("<I", p, o)[0]


def _u64(p, o):
    return struct.unpack_from("<Q", p, o)[0]


# ---------------------------------------------------------------- references

def read_ref(p, o):
    """(kind, isGlobal, id) of the 10-byte FileReference at o; id 0 for a null ref."""
    return (p[o], p[o + 1], _u64(p, o + 2) if p[o] in (1, 2) else 0)


def ref_bytes(ref):
    kind, glob_, i = ref
    if not i:
        return b"\x03" + bytes(9)
    return bytes([1, glob_]) + struct.pack("<Q", i)


def _ref_len(p, o):
    if p[o] in (1, 3):
        return 10
    if p[o] in (2, 5):
        return 9
    raise ValueError(f"reference kind {p[o]} at {o}")


# ---------------------------------------------------------------- parameters

def parse_params(p, o):
    """The parameter list at o. Returns (params, end); raises on any type it cannot size."""
    n = _u32(p, o); o += 4
    if n > 400:
        raise ValueError(f"parameter count {n}")
    out = []
    for _ in range(n):
        name, dtype, ptype = struct.unpack_from("<III", p, o)
        unk = bytes(p[o + 12:o + 16]); o += 16
        if ptype == REF:
            ln = _ref_len(p, o)
        elif ptype == OBJ:
            ln = OBJ_SIZES.get(dtype)
            if ln is None or _u32(p, o + 8) != dtype:
                raise ValueError(f"inline object DataType {dtype:#x} not supported (param {name:#x})")
        elif ptype in SIZES:
            ln = SIZES[ptype]
        else:
            raise ValueError(f"parameter Type {ptype:#x} not supported (param {name:#x})")
        out.append(dict(name=name, dtype=dtype, ptype=ptype, unk=unk, value=bytes(p[o:o + ln])))
        o += ln
    return out, o


def build_params(params):
    b = bytearray(struct.pack("<I", len(params)))
    for q in params:
        b += struct.pack("<III", q["name"], q["dtype"], q["ptype"]) + q["unk"] + q["value"]
    return bytes(b)


def is_selector(q):
    return q["ptype"] == OBJ and q["dtype"] == TEXSEL


def selector(v):
    """Fields of a 53-byte TextureSelector value."""
    method, map_type, frame = struct.unpack_from("<iii", v, 13)
    return dict(obj=_u64(v, 0), managed=v[12], method=method, map_type=map_type, frame=frame,
                textureset=read_ref(v, 25), texturemap=read_ref(v, 35), tail=bytes(v[45:53]))


def build_selector(s):
    return (struct.pack("<QI", s["obj"], TEXSEL) + bytes([s["managed"]])
            + struct.pack("<iii", s["method"], s["map_type"], s["frame"])
            + ref_bytes(s["textureset"]) + ref_bytes(s["texturemap"]) + s["tail"])


# ---------------------------------------------------------------- material

def parse_material(p, game):
    """A Material payload as a dict (see FORMAT). Raises ValueError on anything unexpected."""
    L = LAYOUT[game]
    if len(p) < L["params"] + 4 or _u32(p, 8) != MATERIAL_TYPE:
        raise ValueError("not a Material")
    if _u32(p, 41) != MASK_TYPE:
        raise ValueError("Mask object not at 33")
    fb = 54 + L["flags"]
    mm = fb + 10
    if _u32(p, mm + 8) != MATCHMASK_TYPE:
        raise ValueError(f"MaterialMatchMask not at {mm} (wrong game?)")
    end = mm + 28
    category = None
    if L["category"]:
        category = bytes(p[end:end + 4]); end += 4
    params, stop = parse_params(p, end)
    if stop != len(p):
        raise ValueError(f"parameters end at {stop}, payload is {len(p)} B")
    return dict(game=game, class_id=_u64(p, 0), managed=p[12], template=read_ref(p, 13),
                textureset=read_ref(p, 23), mask=bytes(p[33:46]), modes=bytes(p[46:54]),
                flags=bytes(p[54:fb]), backface=bytes(p[fb:mm]), matchmask=bytes(p[mm:mm + 28]),
                category=category, params=params)


def build_material(m, game):
    L = LAYOUT[game]
    if len(m["flags"]) != L["flags"]:
        raise ValueError(f"{game} wants {L['flags']} flag bytes, got {len(m['flags'])}")
    b = (struct.pack("<QI", m["class_id"], MATERIAL_TYPE) + bytes([m["managed"]])
         + ref_bytes(m["template"]) + ref_bytes(m["textureset"]) + m["mask"] + m["modes"]
         + m["flags"] + m["backface"] + m["matchmask"])
    if L["category"]:
        b += m["category"] or struct.pack("<i", 5)
    return b + build_params(m["params"])


def grb_flags(grw_flags):
    f = bytearray(grw_flags)
    for k in NEW_FLAGS:
        f.insert(k, 0)
    return bytes(f)


# ---------------------------------------------------------------- texture set

def parse_textureset(p):
    if len(p) != 202 or _u32(p, 8) != TEXTURESET_TYPE:
        raise ValueError("not a 202-byte TextureSet")
    return dict(class_id=_u64(p, 0), managed=p[12],
                slots=[read_ref(p, 13 + 10 * k) for k in range(18)], tail=bytes(p[193:202]))


def build_textureset(t):
    return (struct.pack("<QI", t["class_id"], TEXTURESET_TYPE) + bytes([t["managed"]])
            + b"".join(ref_bytes(r) for r in t["slots"]) + t["tail"])


def ref_flags_from(payloads):
    """{TextureMap id: IsGlobal byte} the way GRB references each texture, from GRB
    ("Material"|"TextureSet", payload) pairs. The byte is a per-texture property in
    both games (613/619 GRB and 749/758 GRW textures always carry one value), and
    Ubisoft changed it for some shared textures, so read it from GRB, not GRW."""
    per = collections.defaultdict(collections.Counter)
    for kind, p in payloads:
        try:
            if kind == "TextureSet":
                refs = parse_textureset(p)["slots"]
            else:
                refs = [selector(q["value"])["texturemap"] for q in parse_material(p, GRB)["params"]
                        if is_selector(q)]
        except ValueError:
            continue
        for r in refs:
            if r[2]:
                per[r[2]][r[1]] += 1
    return {i: c.most_common(1)[0][0] for i, c in per.items()}


def _map_tex(i, id_map, strict, report=None):
    if not i:
        return 0
    if i in id_map:
        j = id_map[i] or 0
        if not j and report is not None:
            report.setdefault("nulled", []).append(i)
        return j
    if strict:
        raise KeyError(f"TextureMap {i} is not in the texture id map")
    return i


def convert_textureset(p, texture_id_map, target=None, drop=None, strict=False, class_id=None,
                       ref_flags=None, report=None):
    """GRW TextureSet -> GRB TextureSet. Same layout; ids go through the map, and the slots
    Ubisoft dropped for this target (Specular, unless the target reads it) become null.
    ref_flags: optional {GRB TextureMap id: IsGlobal byte} (see notes; otherwise GRW's is kept)."""
    t = parse_textureset(p)
    flags = ref_flags or {}
    if drop is None:
        drop = _rules()["targets"].get(str(target), {}).get("drop_slots", _rules()["drop_slots"])
    for k, (kind, g, i) in enumerate(t["slots"]):
        j = 0 if k in drop else _map_tex(i, texture_id_map, strict, report)
        if i and k in drop and report is not None:
            report.setdefault("dropped_slots", []).append(TS_SLOTS[k])
        t["slots"][k] = (1, flags.get(j, g), j) if j else (3, 0, 0)
    if class_id:
        t["class_id"] = class_id
    return build_textureset(t)


# ---------------------------------------------------------------- rules

_RULES = {}


def _rules():
    if "r" not in _RULES:
        if not os.path.isfile(RULES_PATH):
            raise FileNotFoundError(f"{RULES_PATH} missing: run `grw_materials.py learn` first")
        with open(RULES_PATH, encoding="utf-8") as f:
            _RULES["r"] = json.load(f)
    return _RULES["r"]


def choose_template(grw_template, target=None, fallback=None):
    """(GRB template id, reason). The majority target over Ubisoft's conversions of this
    GRW template; `target` overrides; `fallback` is used (and said so) when there is no
    twin evidence, otherwise NoEvidence is raised."""
    if target:
        return int(target), "given"
    row = _rules()["templates"].get(str(grw_template))
    if row:
        (tid, name, n), total = row["targets"][0], row["n"]
        return int(tid), f"{n}/{total} conversions of {row['name']} -> {name}"
    if fallback:
        return int(fallback), f"no twin evidence for GRW template {grw_template}; fallback given"
    raise NoEvidence(f"no twin evidence for GRW template {grw_template}; pass target= or fallback=")


def _resolve(sel, slots):
    """The TextureMap a selector shows: slot[mapType] of the material TextureSet for method 0,
    else its own TextureMap ref (method 1's own set is not resolved here)."""
    if sel["method"] == 0 and slots is not None and 0 <= sel["map_type"] < 18:
        return slots[sel["map_type"]][2]
    return sel["texturemap"][2]


SYNTH_TS_TAG = 1 << 45     # default id of a synthesized TextureSet: material ClassID | this tag


def synthesize_textureset(ts_id, slots, source=None):
    """A 202-byte TextureSet holding {slot index: (IsGlobal, TextureMap id)}, every other slot
    null. `source` defaults to ts_id - 1, the pattern of 213/260 GRW and 212/264 GRB sets."""
    refs = [(3, 0, 0)] * 18
    for k, (g, i) in slots.items():
        refs[k] = (1, g, i)
    return build_textureset(dict(class_id=ts_id, managed=1, slots=refs,
                                 tail=b"\0" + struct.pack("<Q", ts_id - 1 if source is None else source)))


def convert(grw_material_payload, grw_textureset_payload, texture_id_map, **kw):
    """GRW Material payload -> GRB Material payload; see convert_pair, which also returns the
    TextureSet the material needs (and synthesizes one when GRW had none)."""
    return convert_pair(grw_material_payload, grw_textureset_payload, texture_id_map, **kw)[0]


def convert_pair(grw_material_payload, grw_textureset_payload, texture_id_map, target=None,
                 fallback=None, class_id=None, textureset_id=None, strict=False, ref_flags=None,
                 report=None):
    """GRW Material (+ its TextureSet) -> (GRB Material, GRB TextureSet or None, report).

    grw_textureset_payload is the material's own TextureSet (its ref @23), or None.
    - TextureSet given: it is converted (convert_textureset) and returned.
    - Material has no TextureSet (null ref @23): one is synthesized from the selectors'
      direct textures, the way Ubisoft did in all 9 such twins - each texture goes to the
      slot of its GRB label's usual mapType (albedo 0, normal 1) and its selector becomes
      method 0. GRB renders a material with a null set magenta (W6), so this is mandatory.
      Its id is textureset_id, else ClassID | SYNTH_TS_TAG (bit 45; free in both games).
    - Ref present but payload not given (set lives elsewhere): the ref is kept, None returned.
    ref_flags: optional {GRB TextureMap id: IsGlobal byte}, as for convert_textureset.
    report receives what was chosen, copied, defaulted, dropped and nulled."""
    flags = ref_flags or {}
    report = {} if report is None else report
    m = parse_material(grw_material_payload, GRW)
    tid, why = choose_template(m["template"][2], target, fallback)
    rule = _rules()["targets"].get(str(tid))
    if rule is None:
        raise NoEvidence(f"no learned parameter rules for GRB template {tid}; "
                         f"known targets: {sorted(_rules()['targets'])}")
    report.update(template=tid, template_name=rule["name"], why=why)
    slots, ts, synth = None, None, None
    if grw_textureset_payload is not None:
        ts = convert_textureset(grw_textureset_payload, texture_id_map, target=tid, strict=strict,
                                ref_flags=flags, report=report)
        slots = parse_textureset(ts)["slots"]
        report["textureset"] = "converted"
    elif not m["textureset"][2]:
        synth = {}
        report["textureset"] = "synthesized"
    else:
        report["textureset"] = f"external {m['textureset'][2]} (convert it separately)"
    src = {q["name"]: q for q in m["params"]}
    used = {selector(q["value"])["obj"] for q in m["params"] if is_selector(q)}
    fresh = (i for i in range(LOCAL_OBJ, LOCAL_OBJ + 4096) if i not in used)
    taken, out = set(), []
    for h in rule["order"]:
        r = rule["params"][h]
        name, ptype, dtype, unk = int(h), r["ptype"], r["dtype"], bytes.fromhex(r["unk"])
        value = None
        if r["kind"] == "tex":
            q = next((src[int(s)] for s in r["from"] if int(s) in src and is_selector(src[int(s)])), None)
            if q is not None:
                s = selector(q["value"])
                tm = _resolve(s, slots) if slots is not None else _map_tex(
                    s["texturemap"][2], texture_id_map, strict, report)
                if s["method"] != 0:
                    tm = _map_tex(s["texturemap"][2], texture_id_map, strict, report)
                g = flags.get(tm, s["texturemap"][1] or 1)
                role = r["sel"]["map_type"] if r.get("sel") else s["map_type"]
                if synth is not None and tm and 0 <= role < 18 and role not in synth:
                    synth[role] = (g, tm)
                    s.update(method=0, map_type=role, textureset=(3, 0, 0))
                s["texturemap"] = (1, g, tm) if tm else (3, 0, 0)
                if s["obj"] in taken:
                    s["obj"] = next(fresh)
                value = build_selector(s)
                report.setdefault("textures", {})[r["label"]] = (q["name"], tm)
            elif r.get("sel"):
                d = r["sel"]
                tm = slots[d["map_type"]][2] if (slots is not None and d["method"] == 0
                                                 and 0 <= d["map_type"] < 18) else 0
                s = dict(obj=next(fresh), managed=d["managed"], method=d["method"],
                         map_type=d["map_type"], frame=d["frame"], textureset=(3, 0, 0),
                         texturemap=(1, flags.get(tm, d["tm_global"]), tm) if tm else (3, 0, 0),
                         tail=bytes.fromhex(d["tail"]))
                value = build_selector(s)
                report.setdefault("defaulted", []).append(r["label"])
        else:
            q = src.get(name)
            if r["kind"] == "copy" and q is not None and q["ptype"] == ptype and q["dtype"] == dtype:
                value = q["value"]
                if ptype == REF and value[0] == 1:
                    i = _map_tex(_u64(value, 2), texture_id_map, strict, report)
                    value = ref_bytes((1, value[1], i)) if i else ref_bytes((3, 0, 0))
                report.setdefault("copied", []).append(r["label"])
            elif r.get("default") is not None:
                value = bytes.fromhex(r["default"])
                if ptype == OBJ:
                    value = struct.pack("<Q", next(fresh)) + value[8:]
                report.setdefault("defaulted", []).append(r["label"])
        if value is not None:
            if ptype == OBJ:
                taken.add(_u64(value, 0))
            out.append(dict(name=name, dtype=dtype, ptype=ptype, unk=unk, value=value))
    kept = {q["name"] for q in out}
    report["dropped"] = [_rules()["labels"].get(str(q["name"]), f"{q['name']:#010x}")
                         for q in m["params"] if q["name"] not in kept]
    cid = class_id or m["class_id"]
    tsid = textureset_id if textureset_id is not None else m["textureset"][2]
    if synth is not None:
        tsid = textureset_id or (cid | SYNTH_TS_TAG)
        ts = synthesize_textureset(tsid, synth)
        report["synthesized_slots"] = {TS_SLOTS[k]: i for k, (g_, i) in sorted(synth.items())}
    elif ts is not None and textureset_id:
        ts = build_textureset(dict(parse_textureset(ts), class_id=textureset_id))
    g = dict(m, class_id=cid, template=(1, 1, tid),
             textureset=(1, 0, tsid) if tsid else (3, 0, 0), flags=grb_flags(m["flags"]),
             category=None, params=out)
    return build_material(g, GRB), ts, report


# ---------------------------------------------------------------- learning from the twins

def _entries(install, pattern, want_type):
    """{entry id: (forge path, offset, length, name)} for one entry type, over the install
    folder and its dlc_NN subfolders (GRW keeps DLC forges there); patch forges override."""
    import forge_inspect as fi
    out = {}
    forges = sorted(glob.glob(os.path.join(install, pattern)) + glob.glob(os.path.join(install, "dlc_*", pattern)),
                    key=lambda f: ("patch" in os.path.basename(f).lower(), os.path.basename(f).lower()))
    for fp in forges:
        if "vulkan" in os.path.basename(fp).lower():
            continue
        for fid, ext, name, off, ln in fi.forge_entries(fp):
            if ext == want_type:
                out[fid] = (fp, off, ln, name)
    return out


def _resources(rec, oodle):
    import data_inspect as di
    with open(rec[0], "rb") as f:
        f.seek(rec[1]); b = f.read(rec[2])
    _, files = di.read_container_bytes(b, oodle)
    res, end = di.walk(files)
    return res


def _textures(p, game, ts_by_id):
    """Every non-default TextureMap a material shows (its TextureSet + its selectors)."""
    try:
        m = parse_material(p, game)
    except ValueError:
        return None, set()
    out = set()
    ts = ts_by_id.get(m["textureset"][2])
    if ts is not None:
        out |= {r[2] for r in parse_textureset(ts)["slots"] if r[2] >= DEFAULT_TEX}
    for q in m["params"]:
        if is_selector(q):
            i = selector(q["value"])["texturemap"][2]
            if i >= DEFAULT_TEX:
                out.add(i)
    return m, out


def harvest(grw, grb, log=print):
    """Conversion twins: [(grw material, grw TextureSet|None, grb material, grb TextureSet|None)]
    as payloads, plus {template id: name} and every payload seen (for round-trip tests)."""
    import data_inspect as di
    oodle = di.Oodle(di.find_oodle(os.path.join(grb, "x")))
    gw = _entries(grw, "DataPC*.forge", T_MESH)
    gb = _entries(grb, "DataPC_Resources*.forge", T_MESH)
    shared = sorted(set(gw) & set(gb))
    log(f"Mesh entries: GRW {len(gw):,}, GRB {len(gb):,}, shared {len(shared):,}")
    twins, seen, allp = [], set(), {GRW: [], GRB: []}
    for n, fid in enumerate(shared):
        sides = []
        for game, rec, oo in ((GRW, gw[fid], None), (GRB, gb[fid], oodle)):
            res = _resources(rec, oo)
            mats = {_u64(r.payload, 0): r.payload for r in res if r.type_id == T_MATERIAL}
            tss = {_u64(r.payload, 0): r.payload for r in res if r.type_id == T_TEXTURESET}
            allp[game] += [("Material", p) for p in mats.values()] + [("TextureSet", p) for p in tss.values()]
            sides.append((mats, tss))
        (wm, wts), (bm, bts) = sides
        cand = []
        for x, px in wm.items():
            mx, tx = _textures(px, GRW, wts)
            for y, py in bm.items():
                my, ty = _textures(py, GRB, bts)
                if mx and my and tx & ty:
                    cand.append((-len(tx & ty), x, y, mx, my))
        ux, uy = set(), set()
        for _, x, y, mx, my in sorted(cand, key=lambda c: c[:3]):
            if x in ux or y in uy:
                continue
            ux.add(x); uy.add(y)
            if (x, y) not in seen:
                seen.add((x, y))
                twins.append((wm[x], wts.get(mx["textureset"][2]), bm[y], bts.get(my["textureset"][2])))
        if n % 300 == 0:
            log(f"  {n:,}/{len(shared):,} containers, {len(twins)} conversions")
    log(f"{len(twins)} conversions from {len(shared):,} shared Mesh entries")
    return twins, allp, oodle


def template_names(grw, grb, oodle, hashes=()):
    """{template id: name} for both installs, and {label hash: label} for the given hashes
    (CRC32 of every printable string in every MaterialTemplate payload)."""
    names, labels, want = {}, {}, set(hashes)
    for install, oo in ((grw, None), (grb, oodle)):
        recs = _entries(install, "DataPC*.forge", T_TEMPLATE)
        for tid, rec in recs.items():
            names[tid] = rec[3]
            for r in _resources(rec, oo):
                for s in re.findall(rb"[ -~]{2,96}", r.payload):
                    h = zlib.crc32(s)
                    if h in want:
                        labels.setdefault(h, s.decode())
    return names, labels


def learn(twins, names=None, labels=None, min_share=0.5):
    """The rule tables from conversion twins (see notes-materials.md for the reasoning)."""
    names, labels = names or {}, labels or {}
    by_tmpl = collections.defaultdict(collections.Counter)
    per = collections.defaultdict(list)
    bad = 0
    for gp, gts, bp, bts in twins:
        try:
            gm, bm = parse_material(gp, GRW), parse_material(bp, GRB)
        except ValueError:
            bad += 1
            continue
        by_tmpl[gm["template"][2]][bm["template"][2]] += 1
        per[bm["template"][2]].append((gm, gts and parse_textureset(gts), bm, bts and parse_textureset(bts)))

    def shown(m, ts):
        slots = ts["slots"] if ts else None
        return {q["name"]: _resolve(selector(q["value"]), slots) for q in m["params"] if is_selector(q)}

    targets, slot_all = {}, collections.defaultdict(lambda: [0, 0])
    for T, rows in per.items():
        N = len(rows)
        st = collections.defaultdict(lambda: dict(n=0, pos=[], vals=collections.Counter(), unk=collections.Counter(),
                                                  dt=collections.Counter(), src=collections.Counter(),
                                                  both=0, equal=0, sel=collections.Counter(),
                                                  nogrw=collections.Counter()))
        in_grw = collections.Counter()
        slot = collections.defaultdict(lambda: [0, 0])
        for gm, gts, bm, bts in rows:
            gsel, bsel = shown(gm, gts), shown(bm, bts)
            gpar = {q["name"]: q for q in gm["params"]}
            in_grw.update(gpar.keys())
            for i, q in enumerate(bm["params"]):
                s = st[q["name"]]
                s["n"] += 1; s["pos"].append(i / max(1, len(bm["params"]) - 1))
                s["unk"][q["unk"].hex()] += 1; s["dt"][(q["dtype"], q["ptype"])] += 1
                if is_selector(q):
                    v = selector(q["value"])
                    s["sel"][(v["managed"], v["method"], v["map_type"], v["frame"], v["tail"].hex(),
                              v["texturemap"][1] or 1)] += 1
                    t = bsel[q["name"]]
                    for gl, gt in gsel.items():
                        if t and gt == t:
                            s["src"][gl] += 1
                else:
                    s["vals"][q["value"].hex()] += 1
                    if q["name"] in gpar:
                        s["both"] += 1; s["equal"] += gpar[q["name"]]["value"] == q["value"]
                    else:
                        s["nogrw"][q["value"].hex()] += 1
            if gts and bts:
                for k in range(18):
                    if gts["slots"][k][2]:
                        for d in (slot[k], slot_all[k]):
                            d[0] += 1; d[1] += bool(bts["slots"][k][2])
        params = {}
        for h, s in st.items():
            (dtype, ptype), _ = s["dt"].most_common(1)[0]
            r = dict(label=labels.get(h, f"{h:#010x}"), dtype=dtype, ptype=ptype,
                     unk=s["unk"].most_common(1)[0][0], present=f"{s['n']}/{N}")
            if dtype == TEXSEL and ptype == OBJ:
                srcs = [gl for gl, c in s["src"].most_common() if c >= 2 or c == s["src"].most_common(1)[0][1]]
                if in_grw[h] and h not in srcs:
                    srcs.append(h)
                r.update(kind="tex", **{"from": [str(x) for x in srcs]},
                         evidence={labels.get(gl, f"{gl:#010x}"): c for gl, c in s["src"].most_common()})
                if s["n"] / N >= min_share:
                    (mg, me, mt, fr, tail, tg), _ = s["sel"].most_common(1)[0]
                    r["sel"] = dict(managed=mg, method=me, map_type=mt, frame=fr, tail=tail, tm_global=tg)
            else:
                val, c = s["vals"].most_common(1)[0]
                # copy GRW's value only where that reproduces more twins than Ubisoft's usual value
                copy_hits = s["equal"] + (s["nogrw"][val] if s["n"] / N >= min_share else 0)
                if in_grw[h] and s["both"] / in_grw[h] >= min_share and copy_hits >= c:
                    r.update(kind="copy", copied=f"{s['both']}/{in_grw[h]}", equal=f"{s['equal']}/{s['both']}")
                elif s["n"] / N >= min_share:
                    r.update(kind="const")
                else:
                    continue
                r["hits"] = f"copy {copy_hits} / const {c} of {s['n']}"
                if s["n"] / N >= min_share:
                    r.update(default=val, default_share=f"{c}/{s['n']}")
            params[str(h)] = r
        order = sorted(params, key=lambda h: sorted(st[int(h)]["pos"])[len(st[int(h)]["pos"]) // 2])
        targets[str(T)] = dict(name=names.get(T, f"#{T}"), n=N, order=order, params=params,
                               slots={TS_SLOTS[k]: f"{b}/{g} kept" for k, (g, b) in sorted(slot.items())},
                               drop_slots=[k for k, (g, b) in sorted(slot.items()) if g >= 3 and b / g < min_share])
    templates = {}
    for g, c in by_tmpl.items():
        total = sum(c.values())
        templates[str(g)] = dict(name=names.get(g, f"#{g}"), n=total,
                                 targets=[(str(t), names.get(t, f"#{t}"), k) for t, k in c.most_common()])
    drop = [k for k, (g, b) in sorted(slot_all.items()) if g >= 3 and b / g < min_share]
    return dict(about="Learned by grw_materials.py learn from GRW/GRB conversion twins; see meta/notes-materials.md",
                twins=len(twins), unparsed=bad, drop_slots=drop,
                slots={TS_SLOTS[k]: f"{b}/{g} kept" for k, (g, b) in sorted(slot_all.items())},
                templates=templates, targets=targets,
                labels={str(h): v for h, v in sorted(labels.items())})


# ---------------------------------------------------------------- CLI

def _memory_cap(mb):
    try:
        from id_census import memory_cap
        memory_cap(mb)
    except Exception:
        pass


def _all_hashes(twins):
    hs = set()
    for gp, _, bp, _ in twins:
        for p, g in ((gp, GRW), (bp, GRB)):
            try:
                hs |= {q["name"] for q in parse_material(p, g)["params"]}
            except ValueError:
                pass
    return hs


def cmd_learn(a):
    _memory_cap(1200)
    twins, _, oodle = harvest(a.grw, a.grb)
    names, labels = template_names(a.grw, a.grb, oodle, _all_hashes(twins))
    r = learn(twins, names, labels)
    with open(a.out or RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=1)
    print(f"wrote {a.out or RULES_PATH}: {len(r['templates'])} GRW templates, {len(r['targets'])} GRB targets")


def cmd_templates(a):
    r = _rules()
    rows = sorted(r["templates"].items(), key=lambda kv: -kv[1]["n"])
    print(f"{'GRW template id':>16}  {'GRW name':38s} {'n':>4}  GRB target(s) (count)")
    for g, row in rows:
        ts = ", ".join(f"{name} [{tid}] ({k})" for tid, name, k in row["targets"])
        thin = "  << thin" if row["n"] < 3 or row["targets"][0][2] / row["n"] < 0.67 else ""
        print(f"{g:>16}  {row['name'][:38]:38s} {row['n']:4}  {ts}{thin}")


def _load_map(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k, 0): (int(v, 0) if isinstance(v, str) else v) for k, v in raw.items()}


def cmd_convert(a):
    mat = open(a.material, "rb").read()
    ts = open(a.textureset, "rb").read() if a.textureset != "-" else None
    tmap = _load_map(a.map)
    out, ts_out, report = convert_pair(mat, ts, tmap, target=a.target, fallback=a.fallback)
    open(a.out, "wb").write(out)
    if ts_out is not None and a.ts_out:
        open(a.ts_out, "wb").write(ts_out)
    elif ts_out is not None:
        print(f"note: a TextureSet was {report['textureset']}; pass --ts-out to write it")
    print(json.dumps(report, indent=1, default=str))


def _ranges(xs):
    out = []
    for x in xs:
        if out and x == out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return [f"{a}-{b}" if a != b else str(a) for a, b in out]


def compare(ours, theirs, flags=False):
    """Parameter-level comparison of two GRB materials: (same label set, labels missing,
    labels extra, values equal / shared labels, textures equal / selectors shared).
    flags=True also requires the TextureMap refs' IsGlobal bytes to match."""
    k = slice(1, 3) if flags else slice(2, 3)
    a, b = parse_material(ours, GRB), parse_material(theirs, GRB)
    pa, pb = {q["name"]: q for q in a["params"]}, {q["name"]: q for q in b["params"]}
    shared = set(pa) & set(pb)
    def same(h):
        if not is_selector(pb[h]):
            return pa[h]["value"] == pb[h]["value"]
        x, y = selector(pa[h]["value"]), selector(pb[h]["value"])
        return (x["texturemap"][2], x["method"], x["map_type"]) == (y["texturemap"][2], y["method"], y["map_type"])
    eq = sum(1 for h in shared if same(h))
    sel = [h for h in shared if is_selector(pb[h])]
    tex = sum(1 for h in sel if selector(pa[h]["value"])["texturemap"][k] == selector(pb[h]["value"])["texturemap"][k])
    return dict(same_set=set(pa) == set(pb), missing=set(pb) - set(pa), extra=set(pa) - set(pb),
                equal=eq, shared=len(shared), tex=tex, sel=len(sel))


def cmd_selftest(a):
    _memory_cap(1200)
    twins, allp, oodle = harvest(a.grw, a.grb)
    ok = collections.OrderedDict()
    for game in (GRW, GRB):
        n = good = bad = 0
        for kind, p in allp[game]:
            n += 1
            try:
                if kind == "Material":
                    good += build_material(parse_material(p, game), game) == p
                else:
                    good += build_textureset(parse_textureset(p)) == p
            except ValueError:
                bad += 1
        ok[f"{game} round-trip byte-exact"] = f"{good}/{n - bad} (unparsed {bad})"
    names, labels = template_names(a.grw, a.grb, oodle, _all_hashes(twins))
    flags = ref_flags_from(allp[GRB])
    folds = {"in-sample": (twins, twins),
             "held-out A->B": (twins[0::2], twins[1::2]),
             "held-out B->A": (twins[1::2], twins[0::2])}
    for label, (train, test) in folds.items():
        _RULES["r"] = learn(train, names, labels)
        c = collections.Counter()
        for gp, gts, bp, bts in test:
            try:
                gm, bm = parse_material(gp, GRW), parse_material(bp, GRB)
            except ValueError:
                c["unparsed"] += 1
                continue
            c["pairs"] += 1
            try:
                tid, _ = choose_template(gm["template"][2])
                c["template = Ubisoft's"] += tid == bm["template"][2]
            except NoEvidence:
                c["template: no evidence in training half"] += 1
            try:
                ours = convert(gp, gts, {}, target=bm["template"][2])
            except NoEvidence:
                c["target unseen in training half"] += 1
                continue
            c["converted"] += 1
            r = compare(ours, bp)
            c["same parameter set"] += r["same_set"]
            c["params equal"] += r["equal"]; c["params shared"] += r["shared"]
            c["textures equal"] += r["tex"]; c["selectors shared"] += r["sel"]
            c["params missing"] += len(r["missing"]); c["params extra"] += len(r["extra"])
            c["head equal (0..121)"] += ours[:121] == bp[:121]
            c["byte-exact"] += ours == bp
            c["textures + IsGlobal equal, GRB ref flags"] += compare(
                convert(gp, gts, {}, target=bm["template"][2], ref_flags=flags), bp, flags=True)["tex"]
            if not gm["textureset"][2] and bts:
                # Ubisoft synthesized a set here: compare ours (slots, selector method/mapType)
                _, sts, _ = convert_pair(gp, None, {}, target=bm["template"][2])
                c["synthesized sets (GRW had none)"] += 1
                c["  synthesized Diffuse+Normal = Ubisoft's"] += (
                    [r[2] for r in parse_textureset(sts)["slots"][:2]]
                    == [r[2] for r in parse_textureset(bts)["slots"][:2]])
                ours_sel = {q["name"]: selector(q["value"]) for q in parse_material(
                    convert(gp, None, {}, target=bm["template"][2]), GRB)["params"] if is_selector(q)}
                for q in bm["params"]:
                    if is_selector(q) and q["name"] in ours_sel:
                        y, x = selector(q["value"]), ours_sel[q["name"]]
                        c["  selectors: method+mapType = Ubisoft's"] += (x["method"], x["map_type"]) == (y["method"], y["map_type"])
                        c["  selectors compared"] += 1
            if gts and bts:
                c["TextureSets compared"] += 1
                c["TextureSet byte-exact"] += convert_textureset(gts, {}, target=bm["template"][2]) == bts
                c["TextureSet byte-exact, GRB ref flags"] += convert_textureset(
                    gts, {}, target=bm["template"][2], ref_flags=flags) == bts
        ok[label] = dict(c)
    _RULES.pop("r", None)
    for k, v in ok.items():
        print(f"  {k}: {v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("templates")
    p = sub.add_parser("convert")
    p.add_argument("material"); p.add_argument("textureset", help="its TextureSet payload, or -")
    p.add_argument("out"); p.add_argument("--ts-out"); p.add_argument("--map")
    p.add_argument("--target", type=lambda s: int(s, 0)); p.add_argument("--fallback", type=lambda s: int(s, 0))
    for name in ("learn", "selftest"):
        p = sub.add_parser(name)
        p.add_argument("--grw", required=True, help="Wildlands install folder")
        p.add_argument("--grb", required=True, help="Breakpoint install folder")
        if name == "learn":
            p.add_argument("--out", help=f"default {RULES_PATH}")
    a = ap.parse_args()
    {"templates": cmd_templates, "convert": cmd_convert, "learn": cmd_learn,
     "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    main()
