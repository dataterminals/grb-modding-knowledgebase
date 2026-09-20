#!/usr/bin/env python3
"""
reflex3_write.py - write Reflex3 bone-physics blobs: round-trip, edit, generate, splice.

reflex3.py READS a skeleton's bone physics. This tool WRITES it - into a scratch
copy, never into the game. Four jobs:

  round-trip   parse a blob and re-emit it. Byte-exact for every blob in the
               install (the writer's acid test, run with --selftest).
  edit         change fields of physics records in an existing rig:
                 --set-swing  BONE AXIS MIN MAX     swing limits, DEGREES (axis 1 or 2)
                 --set-slide  BONE AXIS MIN MAX     slide limits, METRES (axis x, y or z)
                 --set-param  BONE INDEX VALUE      the nine floats by index (0 = mass*)
                 --set-mass   BONE VALUE            shorthand for index 0
               BONE is a bone name (CRC32 is taken), a hex hash, or `*` for all.
  generate     build a whole blob from a JSON spec of physics records, taking each
               bone's transforms from the skeleton the rig will live in and the
               character-space frame from a body rig (--generate SPEC).
  splice       put the new blob back into a skeleton .data and rebuild the
               container so the game can load it (--out NEW.data). Same-size or not.

    python reflex3_write.py --selftest <GRB install>
    python reflex3_write.py BP_Hill_MEDIUMVEST.data --set-swing 9650dc43 1 -30 30 --out edited.data
    python reflex3_write.py Player_Kilt_Addon.data --generate poncho.json --body Regular_Male_Body_Skl.data --out rig.data
    python reflex3_write.py Player_Kilt_Addon.data --example-spec > spec.json

Every write goes to --out (or stdout for --example-spec). The tool never touches
the file it reads, and every .data it writes is re-read and checked before it is
kept. Putting the result into a forge is a separate, manual step: number it below
the vanilla copy (`1_-_...`) in the unpacked forge folder, back the forge up, and
repack with ATK. See reference/reflex3-chain-templates.md and
reference/install-edit-classes.md before you do.

FORMAT: the physics record and the blob grammar are in reflex3.py's docstring and
reference/skeleton-reflex3-physics.md. Records this tool does not model (types
5 6 7 8 9 11 19 20 23 24) are carried through byte for byte.

MATRICES of a generated physics record (verified 2026-09-20 against vanilla):
  m0 = m1 = m3 = m4 = the bone's local bind transform, from its Bone record
  m2        = W . G_body(attach bone) . G_addon(parent bone)
              W = a 90-degree turn about the vertical axis plus a lift of `h`
              (0.964 m for the regular male body; --h to override)
Whether the runtime reads these or recomputes them from the skeleton is untested.
"""
import sys, os, struct, math, json, zlib, ctypes

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from data_inspect import read_cfd, walk, Oodle, find_oodle, MAGIC          # noqa: E402
import reflex3                                                              # noqa: E402
from reflex3 import parse_blob, is_matrix, REFLEX3_HASH_PAT, BLOB_MAGIC, BLOB_VERSION  # noqa: E402

SKELETON_TYPE = 615435132                 # CRC32("Skeleton")
BONE_CLASS_HASH = struct.pack("<I", 2507411529)
PHYSICS = 21
BLK = 32768                               # CompressedFileData block size GRB uses
MALE_H = 0.964


def crc(s):
    return zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF


# --------------------------------------------------------------------------- skeleton bones
def parse_bones(payload):
    """GRB Bone records of a Skeleton payload (layout from ATK's Bone.Read, GRB branch):
    u8 | u64 local id | u32 hash 2507411529 | u32 Name | ObjectPtr Parent | ObjectPtr Mirror |
    Vector4 GlobalPosition | Quat GlobalRotation | Vector4 LocalPosition | Quat LocalRotation | ...
    A pointer is one byte 03 (null) or 01/02 + u64 (a local id)."""
    out, k = [], payload.find(BONE_CLASS_HASH)
    while k >= 0:
        b = {"id": struct.unpack_from("<Q", payload, k - 8)[0],
             "name": struct.unpack_from("<I", payload, k + 4)[0]}
        o = k + 8
        for fld in ("parent", "mirror"):
            kind = payload[o]; o += 1
            if kind in (1, 2):
                b[fld] = struct.unpack_from("<Q", payload, o)[0]; o += 8
            else:
                b[fld] = None
        b["gpos"] = struct.unpack_from("<4f", payload, o); b["grot"] = struct.unpack_from("<4f", payload, o + 16)
        b["lpos"] = struct.unpack_from("<4f", payload, o + 32); b["lrot"] = struct.unpack_from("<4f", payload, o + 48)
        out.append(b)
        k = payload.find(BONE_CLASS_HASH, k + 4)
    return out


# --------------------------------------------------------------------------- 4x4 helpers
def quat_pos_to_mat(q, t):
    """Row-major 4x4 with the translation in column 3, as the blob stores it."""
    x, y, z, w = q[:4]
    return [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), t[0],
            2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), t[1],
            2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), t[2],
            0.0, 0.0, 0.0, 1.0]


def mul(a, b):
    return [sum(a[4 * i + k] * b[4 * k + j] for k in range(4)) for i in range(4) for j in range(4)]


def frame_W(h):
    return [0.0, 1.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, h, 0.0, 0.0, 0.0, 1.0]


def character_frame(addon_bones, body_bones, parent_name_hash, h=MALE_H):
    """m2 for a physics record: the parent bone's transform in character space."""
    by_name = {b["name"]: b for b in addon_bones}
    roots = [b for b in addon_bones if b["parent"] is None]
    if not roots:
        raise ValueError("the skeleton has no root bone")
    root = roots[0]
    body = {b["name"]: b for b in body_bones}
    if root["name"] not in body:
        raise ValueError(f"the rig's root bone {root['name']:08x} is not a bone of the body rig")
    par = by_name.get(parent_name_hash)
    if par is None:
        raise ValueError(f"parent bone {parent_name_hash:08x} is not declared by the skeleton")
    Gb = quat_pos_to_mat(body[root["name"]]["grot"], body[root["name"]]["gpos"])
    Ga = quat_pos_to_mat(par["grot"], par["gpos"])
    return mul(frame_W(h), mul(Gb, Ga))


# --------------------------------------------------------------------------- physics record bytes
def build_physics(bone, parent, mats, slots, params, extra_matrix=None):
    """u8 21 | ids | 5 matrices | 5 gated slots | 9 floats | [matrix]"""
    if len(mats) != 5 or len(slots) != 5 or len(params) != 9:
        raise ValueError("a physics record has 5 matrices, 5 slots and 9 parameters")
    out = bytearray(b"\x15") + struct.pack("<II", bone, parent)
    for m in mats:
        out += struct.pack("<16f", *m)
    for s in slots:
        if s is None:
            out += b"\x00"
        else:
            out += b"\x01" + struct.pack("<2f", *s)
    out += struct.pack("<9f", *params)
    if extra_matrix is not None:
        out += struct.pack("<16f", *extra_matrix)
    return bytes(out)


def serialize(blob, records):
    """Re-emit a blob from parse_blob records; physics from fields, the rest verbatim."""
    out = bytearray(blob[:8])
    for r in records:
        if r.get("error"):
            raise ValueError(f"cannot serialise a blob with a parse error at {r['offset']}: {r['error']}")
        if r["type"] == PHYSICS and r.get("exact") and "params" in r:
            out += build_physics(r["bone"], r["parent_bone"], r["mats"], r["slots"], r["params"],
                                 r.get("extra_matrix"))
        else:
            out += blob[r["offset"]:r["offset"] + r["size"]]
    return bytes(out)


def roundtrip_ok(blob):
    return serialize(blob, list(parse_blob(blob))) == blob


# --------------------------------------------------------------------------- edits
def _match(rec, sel):
    return sel == "*" or rec["bone"] == sel


def resolve_bone(text, dictionary):
    if text == "*":
        return "*"
    t = text.strip()
    if t.lower().startswith("0x"):
        return int(t, 16)
    if len(t) == 8 and all(c in "0123456789abcdefABCDEF" for c in t):
        return int(t, 16)
    if t.isdigit():
        return int(t)
    return crc(t)


def apply_edits(records, edits, dictionary):
    """edits: list of (kind, bone, args). Returns the number of records touched."""
    n = 0
    for kind, bone, args in edits:
        sel = resolve_bone(bone, dictionary)
        hit = False
        for r in records:
            if r["type"] != PHYSICS or not r.get("exact") or not _match(r, sel):
                continue
            hit = True; n += 1
            if kind == "swing":
                axis, lo, hi = int(args[0]), math.radians(float(args[1])), math.radians(float(args[2]))
                r["slots"][2 + axis] = (lo, hi)
            elif kind == "slide":
                axis = "xyz".index(args[0].lower())
                r["slots"][axis] = (float(args[1]), float(args[2]))
            elif kind == "param":
                p = list(r["params"]); p[int(args[0])] = float(args[1]); r["params"] = tuple(p)
        if not hit:
            raise SystemExit(f"no physics record drives bone {bone}")
    return n


# --------------------------------------------------------------------------- generate
EXAMPLE_SPEC = {
    "_comment": "One four-link strand, the Tsec_Herzog_Hair_Skeleton pattern. Bones must exist in the skeleton "
                "the blob is spliced into; names are hashed with CRC32, or give 8-hex-digit hashes.",
    "h": MALE_H,
    "records": [
        {"bone": "RFX_Poncho_FL_01", "parent": "T_Poncho_FL", "swing1": [-10, 10], "swing2": [0, 25], "mass": 0.4, "p3": 0.6},
        {"bone": "RFX_Poncho_FL_02", "parent": "RFX_Poncho_FL_01", "swing1": [-15, 15], "swing2": [-1, 30], "mass": 0.3, "p3": 0.6},
        {"bone": "RFX_Poncho_FL_03", "parent": "RFX_Poncho_FL_02", "swing1": [-20, 20], "swing2": [-3, 35], "mass": 0.2, "p3": 0.6},
        {"bone": "RFX_Poncho_FL_04", "parent": "RFX_Poncho_FL_03", "swing1": [-25, 25], "swing2": [-5, 40], "mass": 0.1, "p3": 0.6},
    ],
}
DEFAULTS = {"mass": 0.2, "spring": 0.0, "slide_damping": 0.0, "p3": 0.0, "gravity": 9.8,
            "gravity_factor": 1.0, "wind_factor": 1.0, "p7": 0.0, "p8": 0.0}


def generate(spec, addon_bones, body_bones):
    """Physics-only blob from a spec. Returns (blob, notes)."""
    h = float(spec.get("h", MALE_H))
    by_name = {b["name"]: b for b in addon_bones}
    out, notes = bytearray(struct.pack("<II", BLOB_MAGIC, BLOB_VERSION)), []
    for i, r in enumerate(spec["records"]):
        bone = resolve_bone(r["bone"], None); parent = resolve_bone(r["parent"], None)
        b = by_name.get(bone)
        if b is None:
            raise SystemExit(f"record {i}: bone {r['bone']} is not declared by the skeleton")
        if parent not in by_name:
            raise SystemExit(f"record {i}: parent {r['parent']} is not declared by the skeleton")
        L = quat_pos_to_mat(b["lrot"], b["lpos"])
        m2 = character_frame(addon_bones, body_bones, parent, h)
        slots = [None, None, None]
        for key in ("swing1", "swing2"):
            v = r.get(key)
            slots.append((math.radians(v[0]), math.radians(v[1])) if v else None)
        for k, key in enumerate(("slide_x", "slide_y", "slide_z")):
            v = r.get(key)
            if v:
                slots[k] = (float(v[0]), float(v[1]))
        p = [float(r.get(k, DEFAULTS[k])) for k in ("mass", "spring", "slide_damping", "p3", "gravity",
                                                    "gravity_factor", "wind_factor", "p7", "p8")]
        out += build_physics(bone, parent, [L, L, m2, L, L], slots, p)
        notes.append(f"record {i}: {r['bone']} <- {r['parent']}  swing {r.get('swing1')} {r.get('swing2')}  mass {p[0]}  frame z {m2[11]:.3f}")
    return bytes(out), notes


# --------------------------------------------------------------------------- container splice
def _compress_cfd(content, dll):
    """A CompressedFileData block GRB can load: 32 KB chunks, Oodle Mermaid, per-block
    adler32 seeded 0 (same recipe as clothwrap.py, proven on cloth containers)."""
    oo = ctypes.WinDLL(dll)
    comp = oo.OodleLZ_Compress
    comp.restype = ctypes.c_longlong
    comp.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p,
                     ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                     ctypes.c_void_p, ctypes.c_longlong]

    def one(chunk):
        dst = ctypes.create_string_buffer(len(chunk) + 1024)
        n = comp(9, chunk, len(chunk), dst, 4, None, None, None, None, 0)
        return chunk if (n <= 0 or n >= len(chunk)) else dst.raw[:n]

    chunks = [content[i:i + BLK] for i in range(0, len(content), BLK)] or [b""]
    stored = [(len(c), one(c)) for c in chunks]
    hdr = struct.pack("<Q", MAGIC) + struct.pack("<hBHH", 3, 3, 0, BLK) + struct.pack("<i", len(stored))
    for un, cc in stored:
        hdr += struct.pack("<ii", un, len(cc))
    body = bytearray()
    for un, cc in stored:
        body += struct.pack("<I", zlib.adler32(cc, 0) & 0xffffffff) + cc
    return bytes(hdr) + bytes(body)


def _patch_meta(meta, res_index, new_size):
    """metadata block: u16 count | rows { u64 ClassID | i32 recordSize | u16 k | k x u16 }.
    Returns the block with row `res_index` resized; ATK's trailer, if any, is dropped."""
    n = struct.unpack_from("<H", meta, 0)[0]
    o, rows = 2, []
    for i in range(n):
        cid, size, k = struct.unpack_from("<QiH", meta, o)
        row = bytearray(meta[o:o + 14 + 2 * k])
        if i == res_index:
            struct.pack_into("<i", row, 8, new_size)
        rows.append(bytes(row)); o += 14 + 2 * k
    return meta[:2] + b"".join(rows)


def splice(data_path, new_blob, out_path, oodle_dll):
    """Replace the Reflex3 blob of the Skeleton resource in `data_path`; write `out_path`."""
    oodle = Oodle(oodle_dll)
    raw = open(data_path, "rb").read()
    meta, off1, _ = read_cfd(raw, 0, oodle)
    files, off2, _ = read_cfd(raw, off1, oodle)
    res, end = walk(files)
    if end != len(files):
        raise SystemExit("container walk is incomplete; refusing to rebuild it")
    idx = next((i for i, r in enumerate(res) if r.type_id == SKELETON_TYPE and REFLEX3_HASH_PAT in r.payload), None)
    if idx is None:
        raise SystemExit("no Skeleton resource with a Reflex3 blob in this container")
    r = res[idx]
    i = r.payload.find(REFLEX3_HASH_PAT)
    n = struct.unpack_from("<i", r.payload, i + 4)[0]
    new_payload = r.payload[:i + 4] + struct.pack("<i", len(new_blob)) + new_blob + r.payload[i + 8 + n:]
    frames = []
    for j, q in enumerate(res):
        slen = struct.unpack_from("<i", files, q.offset + 8)[0]
        head = files[q.offset:q.offset + 12 + slen]
        if j == idx:
            head = struct.pack("<Iii", q.type_id, len(new_payload), slen) + head[12:]
            frames.append(head + q.header + new_payload)
        else:
            frames.append(head + q.header + q.payload)
    new_files = b"".join(frames)
    slen = struct.unpack_from("<i", files, r.offset + 8)[0]
    new_meta = _patch_meta(meta, idx, 12 + slen + len(r.header) + len(new_payload))
    out = _compress_cfd(new_meta, oodle_dll) + _compress_cfd(new_files, oodle_dll)
    # read it back before keeping it
    m2, o1, _ = read_cfd(out, 0, oodle); f2, o2, _ = read_cfd(out, o1, oodle)
    res2, end2 = walk(f2)
    if f2 != new_files or m2 != new_meta or end2 != len(f2) or o2 != len(out):
        raise SystemExit("round-trip check FAILED - not writing a bad .data")
    open(out_path, "wb").write(out)
    return out_path, len(raw), len(out)


# --------------------------------------------------------------------------- selftest
def selftest(install, oodle_dll):
    """Round-trip every Reflex3 blob in the install's forges."""
    import glob
    from skeleton_reflex import skeleton_entries
    oodle = Oodle(oodle_dll)
    seen, ok, bad, names = set(), 0, [], 0
    for forge in sorted(glob.glob(os.path.join(install, "*.forge"))):
        with open(forge, "rb") as fh:
            for fid, name, off, ln in skeleton_entries(forge):
                fh.seek(off); raw = fh.read(ln)
                try:
                    _, o, _ = read_cfd(raw, 0, oodle); files, _, _ = read_cfd(raw, o, oodle)
                except Exception:
                    continue
                i = files.find(REFLEX3_HASH_PAT)
                if i < 0:
                    continue
                n = struct.unpack_from("<i", files, i + 4)[0]
                if n <= 8:
                    continue
                blob = files[i + 8:i + 8 + n]
                key = zlib.crc32(blob)
                if key in seen:
                    continue
                seen.add(key); names += 1
                try:
                    if roundtrip_ok(blob):
                        ok += 1
                    else:
                        bad.append(name)
                except Exception as e:
                    bad.append(f"{name} ({e})")
    print(f"  {names} distinct blobs; {ok} round-trip byte-exact; {len(bad)} do not: {bad[:10]}")
    return not bad


# --------------------------------------------------------------------------- main
def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = argv[1:]
    if not args:
        print(__doc__); return

    def take(flag, n=1):
        if flag in args:
            k = args.index(flag); v = args[k + 1:k + 1 + n]; del args[k:k + 1 + n]
            return v
        return None

    oodle_dll = (take("--oodle") or [None])[0]
    out = (take("--out") or [None])[0]
    names_path = (take("--names") or [None])[0]
    body_path = (take("--body") or [None])[0]
    h = take("--h")
    spec_path = (take("--generate") or [None])[0]
    example = "--example-spec" in args
    if example:
        args.remove("--example-spec")
    edits = []
    while True:
        v = take("--set-swing", 4)
        if v is None: break
        edits.append(("swing", v[0], v[1:]))
    while True:
        v = take("--set-slide", 4)
        if v is None: break
        edits.append(("slide", v[0], v[1:]))
    while True:
        v = take("--set-param", 3)
        if v is None: break
        edits.append(("param", v[0], v[1:]))
    while True:
        v = take("--set-mass", 2)
        if v is None: break
        edits.append(("param", v[0], ["0", v[1]]))

    if args and args[0] == "--selftest":
        install = args[1]
        dll = oodle_dll or os.path.join(install, "oo2core_7_win64.dll")
        print("Reflex3 writer self-test: every blob in the install, parse -> serialise -> compare")
        sys.exit(0 if selftest(install, dll) else 2)

    if example:
        print(json.dumps(EXAMPLE_SPEC, indent=2)); return

    src = args[0]
    dll = find_oodle(src, oodle_dll)
    oodle = Oodle(dll)
    if not oodle.ok:
        print("  ! no Oodle DLL found - pass --oodle path\\to\\oo2core_7_win64.dll"); return
    dictionary = reflex3.load_name_dictionary(names_path) if names_path else {}
    blob, bones = reflex3.load_blob(src, oodle)
    if blob is None:
        print("  no Reflex3SkeletonConstraints - is this a Skeleton .data?"); return
    raw = open(src, "rb").read()
    _, o, _ = read_cfd(raw, 0, oodle); files, _, _ = read_cfd(raw, o, oodle)
    skel_payload = next(r.payload for r in walk(files)[0] if r.type_id == SKELETON_TYPE and REFLEX3_HASH_PAT in r.payload)
    addon_bones = parse_bones(skel_payload)

    if spec_path:
        if not body_path:
            raise SystemExit("--generate needs --body <body skeleton .data> for the character-space frame")
        braw = open(body_path, "rb").read()
        _, bo, _ = read_cfd(braw, 0, oodle); bfiles, _, _ = read_cfd(braw, bo, oodle)
        body_payload = next(r.payload for r in walk(bfiles)[0] if r.type_id == SKELETON_TYPE)
        spec = json.load(open(spec_path, encoding="utf-8"))
        if h:
            spec["h"] = float(h[0])
        new_blob, notes = generate(spec, addon_bones, parse_bones(body_payload))
        print(f"generated {len(new_blob):,} B, {len(spec['records'])} physics record(s):")
        for s in notes:
            print("   ", s)
    else:
        if len(blob) <= 8:
            print("  this skeleton has no bone physics; use --generate to give it some"); return
        records = list(parse_blob(blob))
        if not roundtrip_ok(blob):
            raise SystemExit("this blob does not round-trip byte-exact; refusing to edit it")
        n = apply_edits(records, edits, dictionary) if edits else 0
        new_blob = serialize(blob, records)
        print(f"blob {len(blob):,} B -> {len(new_blob):,} B; {n} physics record(s) edited; "
              f"{'unchanged' if new_blob == blob else 'changed'}")

    # what the new blob reads like
    recs = list(parse_blob(new_blob))
    if any(r.get("error") for r in recs):
        raise SystemExit("the new blob does not parse cleanly; not writing it")
    phys = [r for r in recs if r["type"] == PHYSICS]
    for r in phys[:12]:
        lab = lambda v: dictionary.get(v, f"{v:08x}")
        print(f"    {lab(r['bone']):>20} <- {lab(r['parent_bone']):<20} swing {reflex3._deg(r['swing'][0]):<11} {reflex3._deg(r['swing'][1]):<11} "
              f"mass {r['params'][0]:g} spring {r['params'][1]:g} p3 {r['params'][3]:g} frame z {r['mats'][2][11]:.2f}")
    if len(phys) > 12:
        print(f"    ... {len(phys) - 12} more")

    if out:
        path, a, b = splice(src, new_blob, out, dll)
        chk, _ = reflex3.load_blob(path, oodle)
        assert chk == new_blob, "the written container does not carry the blob it was given"
        print(f"wrote {path} ({a:,} -> {b:,} B container); re-read and verified.")
        print("  next: number it below the vanilla copy (1_-_...) in the unpacked forge folder, back the")
        print("  forge up, repack with ATK. reference/install-edit-classes.md has what is already proven.")
    elif not spec_path and not edits:
        print("  (nothing to do: give --set-* edits or --generate, and --out to write)")


if __name__ == "__main__":
    main(sys.argv)
