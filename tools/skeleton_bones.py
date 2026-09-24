#!/usr/bin/env python3
"""
skeleton_bones.py - add bones to a GRB Skeleton resource, in the game's own layout.

A bone-physics rig for a new garment needs bones that no vanilla skeleton has.
ATK cannot make a skeleton from a Blender glTF (checked 2026-09-21: AnvilGLTF only
reads bone nodes for meshes), so this writes the Bone records directly, using the
layout ATK's Bone.Read/Bone.Write define for GRB, and leaves everything else in
the skeleton payload byte for byte as it was.

    python skeleton_bones.py Player_Kilt_Addon.data --spec rig.json --out kilt_plus.data

The spec's "bones" list, in parent-before-child order:

    {"bones": [
        {"name": "T_Test_Anchor", "parent": "Hips",          "pos": [0.0, 0.0, -0.20]},
        {"name": "RFX_Test_01",   "parent": "T_Test_Anchor", "pos": [0.10, 0.0, 0.0]},
        {"name": "RFX_Test_02",   "parent": "RFX_Test_01",   "pos": [0.10, 0.0, 0.0]}
    ]}

`pos` is the bone's LOCAL position (metres, in its parent's frame); `rot` is an
optional local rotation quaternion [x, y, z, w] (identity when absent). Names are
hashed with CRC32 exactly as the game does; parents may be names already in the
skeleton or bones earlier in the list. Global transforms are composed from the
parent chain. New bones get the next free local object IDs and are appended after
the existing bones; the skeleton's other objects, keys and the Reflex3 blob are
untouched (the mod-shipped holster rigs keep their keys after re-parenting a bone,
and the game runs).

Validate the result with ATK's own reader through atk_bridge.read_skeleton, and
with reflex3.py once a blob is generated. READ-ONLY on the game: writes only --out.
"""
import sys, os, struct, json, zlib, re

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from data_inspect import read_cfd, walk, Oodle, find_oodle          # noqa: E402
import reflex3_write as W                                             # noqa: E402

BONE_HASH = 2507411529
BONE_HASH_B = struct.pack("<I", BONE_HASH)
SKELETON_TYPE = 615435132


def crc(s):
    return zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF


# ----------------------------------------------------------------- quaternion helpers (x, y, z, w)
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    """Rotate vector v by unit quaternion q."""
    x, y, z, w = q
    qv = (x, y, z)
    t = [2 * (qv[1] * v[2] - qv[2] * v[1]), 2 * (qv[2] * v[0] - qv[0] * v[2]), 2 * (qv[0] * v[1] - qv[1] * v[0])]
    return (v[0] + w * t[0] + (qv[1] * t[2] - qv[2] * t[1]),
            v[1] + w * t[1] + (qv[2] * t[0] - qv[0] * t[2]),
            v[2] + w * t[2] + (qv[0] * t[1] - qv[1] * t[0]))


# ----------------------------------------------------------------- bone records
def bone_record_span(payload, k):
    """(start, end) of the Bone record whose class hash sits at k: from its leading
    u8 through its ChildrenCount. Mirrors Bone.Read for GRB with no modifiers."""
    start = k - 9                                   # u8 | u64 id | u32 hash
    o = k + 8
    for _ in range(2):                              # Parent, Mirror pointers
        kind = payload[o]; o += 1
        if kind in (1, 2):
            o += 8
    o += 64                                         # four 16-byte transforms
    o += 2                                          # SolvingPriority, EnvInfluence
    o += 4                                          # MirroringType
    nmod = struct.unpack_from("<i", payload, o)[0]; o += 4
    if nmod:
        raise ValueError("a bone with modifiers; this writer does not model them")
    ndep = struct.unpack_from("<i", payload, o)[0]; o += 4 + 4 * ndep
    o += 8                                          # WrinkleCategory, WrinkleFactor
    o += 4                                          # Index, ChildrenCount
    return start, o


def build_bone(local_id, name_hash, parent_id, gpos, grot, lpos, lrot, index, children,
               wrinkle_category, wrinkle_factor, w4):
    b = bytearray(b"\x00") + struct.pack("<Q", local_id) + BONE_HASH_B + struct.pack("<I", name_hash)
    b += b"\x02" + struct.pack("<Q", parent_id)      # parent: a link to a local id
    b += b"\x03"                                     # mirror: null
    b += struct.pack("<4f", *gpos, w4) + struct.pack("<4f", *grot)
    b += struct.pack("<4f", *lpos, w4) + struct.pack("<4f", *lrot)
    b += b"\x00\x00"                                 # SolvingPriority, EnvInfluence
    b += struct.pack("<i", 0)                        # MirroringType
    b += struct.pack("<i", 0)                        # modifiers
    b += struct.pack("<i", 0)                        # dependencies
    b += struct.pack("<if", wrinkle_category, wrinkle_factor)
    b += struct.pack("<HH", index, children)
    return bytes(b)


def add_bones(payload, spec_bones):
    """Return (new payload, notes). The skeleton's bone count, the parents'
    ChildrenCount and the new bones' Index are set; nothing else moves."""
    bones = W.parse_bones(payload)
    if not bones:
        raise ValueError("no Bone records found")
    spans = [bone_record_span(payload, b["off"]) for b in bones]
    first, last_end = spans[0][0], spans[-1][1]
    # the payload is: u64 ClassID | u32 class hash | u8 1 | u32 SkeletonType | u32 count | bones...
    # so the first record starts at 21; the records must be contiguous
    if first != 21 or any(spans[i][1] != spans[i + 1][0] for i in range(len(spans) - 1)):
        raise ValueError("unexpected bone record layout; refusing to edit")
    head = payload[:first]
    if struct.unpack_from("<I", payload, 8)[0] != SKELETON_TYPE or payload[12] != 1:
        raise ValueError("payload does not carry the Skeleton class hash and the GRB marker byte")
    ntotal = struct.unpack_from("<I", payload, 17)[0]
    if ntotal != len(bones):
        raise ValueError(f"bone count {ntotal} != records found {len(bones)}")
    tail = payload[last_end:]
    # sample conventions from the existing bones
    w4 = bones[0]["gpos"][3]
    wrinkle = struct.unpack_from("<if", payload, spans[0][1] - 12)
    used = {b["id"] for b in bones}
    for m in re.finditer(rb"[\x00-\xff]\x00\x00\xf8\x00\x00\x00\x00", payload):
        used.add(struct.unpack_from("<Q", payload, m.start())[0])
    next_id = max(used) + 1
    by_name = {b["name"]: b for b in bones}
    by_id = {b["id"]: b for b in bones}

    def bump_ancestors(b):
        """ChildrenCount is the size of the bone's subtree (all descendants), as ATK's
        CalculateChildrenCount computes it: Hips on the kilt is 3 with one direct child."""
        p = by_id.get(b["parent"])
        while p is not None:
            p["children"] += 1
            p = by_id.get(p["parent"])

    for b in bones:
        b["children"] = 0
    for b in bones:                                  # existing counts, recomputed
        bump_ancestors(b)
    new, notes = [], []
    for i, s in enumerate(spec_bones):
        name = crc(s["name"]) if not s["name"].startswith("0x") else int(s["name"], 16)
        pname = s["parent"]
        ph = crc(pname) if not pname.startswith("0x") else int(pname, 16)
        parent = by_name.get(ph)
        if parent is None:
            raise ValueError(f"bone {i} ({s['name']}): parent {pname} is not in the skeleton or earlier in the list")
        if name in by_name:
            raise ValueError(f"bone {i} ({s['name']}) already exists in the skeleton")
        lpos = tuple(float(v) for v in s["pos"])
        lrot = tuple(float(v) for v in s.get("rot", [0, 0, 0, 1]))
        grot = qmul(parent["grot"][:4], lrot)
        gpos = tuple(a + c for a, c in zip(parent["gpos"][:3], qrot(parent["grot"][:4], lpos)))
        b = {"id": next_id, "name": name, "parent": parent["id"], "gpos": gpos + (w4,), "grot": grot,
             "lpos": lpos + (w4,), "lrot": lrot, "children": 0, "index": len(bones) + len(new)}
        by_name[name] = b; by_id[next_id] = b; new.append(b); next_id += 1
        bump_ancestors(b)
        notes.append(f"{s['name']} ({name:08x}) <- {pname}  local {lpos}  global {tuple(round(v, 4) for v in gpos)}  id {b['id']:#x}")
    # re-emit existing bones with updated ChildrenCount (only that field changes)
    out = bytearray(head)
    struct.pack_into("<I", out, 17, len(bones) + len(new))
    for b, (s0, s1) in zip(bones, spans):
        rec = bytearray(payload[s0:s1])
        struct.pack_into("<H", rec, len(rec) - 2, by_id[b["id"]]["children"])
        out += rec
    for b in new:
        out += build_bone(b["id"], b["name"], b["parent"], b["gpos"][:3], b["grot"], b["lpos"][:3], b["lrot"],
                          b["index"], b["children"], wrinkle[0], wrinkle[1], w4)
    out += tail
    return bytes(out), notes


def skeleton_payload(data_path, oodle):
    raw = open(data_path, "rb").read()
    _, o, _ = read_cfd(raw, 0, oodle); files, _, _ = read_cfd(raw, o, oodle)
    res, end = walk(files)
    idx = next(i for i, r in enumerate(res) if r.type_id == SKELETON_TYPE)
    return res[idx].payload


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = argv[1:]
    if not args:
        print(__doc__); return
    oodle_dll = spec_path = out = None
    if "--oodle" in args:
        k = args.index("--oodle"); oodle_dll = args[k + 1]; del args[k:k + 2]
    if "--spec" in args:
        k = args.index("--spec"); spec_path = args[k + 1]; del args[k:k + 2]
    if "--out" in args:
        k = args.index("--out"); out = args[k + 1]; del args[k:k + 2]
    src = args[0]
    dll = find_oodle(src, oodle_dll); oodle = Oodle(dll)
    if not oodle.ok:
        print("  ! no Oodle DLL found - pass --oodle path\\to\\oo2core_7_win64.dll"); return
    payload = skeleton_payload(src, oodle)
    bones = W.parse_bones(payload)
    print(f"{os.path.basename(src)}: {len(bones)} bones, payload {len(payload):,} B")
    if not spec_path:
        for b in bones:
            print(f"   {b['name']:08x} <- {(by := {x['id']: x for x in bones}).get(b['parent'], {}).get('name', 0):08x}  local {tuple(round(v, 4) for v in b['lpos'][:3])}")
        return
    spec = json.load(open(spec_path, encoding="utf-8"))
    new_payload, notes = add_bones(payload, spec["bones"])
    print(f"added {len(spec['bones'])} bone(s); payload {len(payload):,} -> {len(new_payload):,} B")
    for n in notes:
        print("   ", n)
    check = W.parse_bones(new_payload)
    assert len(check) == len(bones) + len(spec["bones"]), "re-read bone count is wrong"
    if out:
        W.splice_payload(src, new_payload, out, dll)
        print(f"wrote {out}; re-read and verified. Validate with atk_bridge.read_skeleton, then give it")
        print("  physics with reflex3_write.py --generate.")


if __name__ == "__main__":
    main(sys.argv)
