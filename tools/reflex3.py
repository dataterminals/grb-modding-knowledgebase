#!/usr/bin/env python3
"""
reflex3.py - decode the Reflex3 bone-physics constraints inside a GRB skeleton.

Reflex3 is what makes hair, ponytails, backpack straps, weapon slings and scarves
move without any cloth simulation. This tool opens a Skeleton resource and prints
the constraints: how each bone is allowed to swing, in degrees, plus its mass,
spring, damping and gravity parameters.

    python reflex3.py 1889064665537_-_Player_Kilt_Addon.data
    python reflex3.py Tsec_Herzog_Hair_Skeleton.data --raw        # every record
    python reflex3.py Watch_Skeleton.data --names hashes.txt      # bone NAMES, not numbers

`--names` takes the plain-text dictionary produced by atk_hashes.py, or
reference/grb-bone-names.tsv. It resolves the standard biped bones (Spine2,
LeftForeArm, Head) but not most of GRB's bespoke dangle-bone names - enough to
see what a rig ATTACHES to.

READ-ONLY.

FORMAT (reverse-engineered 2026-08-14, rewritten 2026-09-20 from a self-delimiting
parse of all 204 distinct blobs in an install; see
reference/skeleton-reflex3-physics.md). ATK cannot read this: its parser validates
Mirage's constants and is gated behind `Version != Game.Mirage`, so for GRB it keeps
the blob as an opaque Base64 lump.

    blob   := u32 magic 0x12341234 | u32 version 3012000 | record*

    record := u8 type | head | body

    head   := BoneInfo                      types 5 6 7 8 19 20 21 24
            | u8 count | BoneInfo           types 9 11   (count = constrained objects)
            | u32 v | 1 matrix              type 23      (v = 2 or 3; a 69-byte marker)

    BoneInfo := u32 BoneID | u32 ParentBoneID | [pstr Name if BoneID == 0xFFFFFFFF]
                | 4 x 64-byte matrix        (5 for the physics record, type 21)

BoneID/ParentBoneID are CRC32 of the exact-case bone name. A BoneID of 0xFFFFFFFF
means the bone is referenced BY NAME (a body bone the add-on rig does not own -
"Spine2", "LeftShoulder", "T_BackPack"), and a length-prefixed string follows.
For the physics record the five matrices are [local bind, local current,
character-space frame of the PARENT bone, swing rest, swing rest]; the rest frame
equals the local bind in 1,194 of 1,362 records. The character-space frame is the
parent's bind transform in the character's ground-origin frame: a 90-degree turn
about the vertical axis plus a per-character height (0.964 m on the regular male
body).

Type 21 - the physics record (verified on all 1,362 in the game; 1,353 land on
the next record's type byte exactly, the other 9 on a record of a type this
parser only scans for):

    body := 5 x { u8 gate ; if gate == 1: f32 min, f32 max }
                slots 1-3: slide X/Y/Z, METRES (|v| <= 0.0025 in vanilla)
                slots 4-5: swing axis 1 and 2, RADIANS
            f32 x 9   [mass*, spring*, slide damping*, p3, GRAVITY 9.8,
                       gravity factor*, wind factor*, 0, 0]   (* = inferred name)
            [64-byte matrix]   present in 5 of 1,362; detected, not announced

Type 6 - hinge (verified: 470 of 472 delimit exactly):
    body := u8 n | n x { BoneInfo target ; f32 weight (percent, sums to 100) }
            | u8 | u8 | quat | u8 | u32

Type 23 is a 69-byte marker (`u32 2 | identity`) that precedes an orientation
record. Types 5/19/24 have fixed shapes this parser checks and falls back from;
types 7/9/11/20/8 are located by scanning for the next valid record head. The
scan is exact for the record that follows a physics or hinge record.
"""
import sys, os, struct, math, zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from data_inspect import read_cfd, Oodle, find_oodle          # noqa: E402

REFLEX3_HASH_PAT = struct.pack("<I", 2386539642)
BLOB_MAGIC, BLOB_VERSION = 0x12341234, 3012000

# header bytes before the first matrix, and matrix count of the constrained bone info
H = {5: 9, 6: 9, 7: 9, 8: 9, 9: 10, 11: 10, 19: 9, 20: 9, 21: 9, 23: 5, 24: 9}
M = {5: 4, 6: 4, 7: 4, 8: 4, 9: 4, 11: 6, 19: 4, 20: 4, 21: 5, 23: 1, 24: 4}
COUNT_BYTE = {9, 11}                       # types whose head carries a u8 count
KNOWN = set(H)
# Types the forward scan may lock onto. Type 8 is left out: its one-byte head
# (`08 | ids | matrix`) matches inside the bodies of types 5/6/7/9 hundreds of
# times, and the one verified type-8 record sits right after an exactly
# delimited physics record, where no scan is needed.
SCANNABLE = KNOWN - {8}
# names ATK knows; the rest GRB uses but ATK never modelled
NAMES = {6: "HingeVector", 7: "LookAt", 9: "Orientation (pose-driven)",
         11: "Position", 21: "Physics (swing/slide/gravity)", 23: "marker",
         24: "ball-joint physics (scarf/straps)", 19: "attachment-like"}
PHYSICS_TYPE = 21
BONE_OFFSET = {9: 1, 11: 1}                # BoneID sits one byte later (after the count)
BONE_CLASS_HASH = struct.pack("<I", 2507411529)   # CRC32("Bone")
BONE_NAME_AFTER_HASH = 4                          # Bone.Name sits 4 B past the class hash
PARAM_NAMES = ["mass*", "spring*", "slide damping*", "p3", "gravity",
               "gravity factor*", "wind factor*", "p7", "p8"]


def _ortho3(f, tol=1e-2):
    rows = [f[0:3], f[4:7], f[8:11]]
    for r in rows:
        if any(math.isnan(x) or math.isinf(x) for x in r):
            return False
        if abs(math.sqrt(sum(x * x for x in r)) - 1.0) > tol:
            return False
    for a in range(3):
        for c in range(a + 1, 3):
            if abs(sum(rows[a][k] * rows[c][k] for k in range(3))) > tol:
                return False
    return True


def is_matrix(b, o):
    """Is there a 64-byte 4x4 affine at o?"""
    try:
        f = struct.unpack_from("<16f", b, o)
    except struct.error:
        return False
    return (_ortho3(f) and abs(f[15] - 1.0) < 1e-3
            and all(abs(f[12 + k]) < 1e-3 for k in range(3))
            and not any(abs(f[i]) > 1e4 for i in (3, 7, 11)))


def _pstr(b, o):
    """Length-prefixed printable string at o, or None."""
    n = b[o] if o < len(b) else 0
    if 1 <= n <= 64 and o + 1 + n <= len(b) and all(32 <= c < 127 for c in b[o + 1:o + 1 + n]):
        return b[o + 1:o + 1 + n].decode()
    return None


def _read_bi(b, o, nmats=None):
    """BoneInfo at o -> (dict, end). nmats None = take every matrix that follows."""
    if o + 8 > len(b):
        raise ValueError("truncated bone info")
    bone, parent = struct.unpack_from("<II", b, o)
    q, name = o + 8, None
    if bone == 0xFFFFFFFF:
        name = _pstr(b, q)
        if name is None:
            raise ValueError("by-name bone info without a name")
        q += 1 + len(name)
    if not is_matrix(b, q):
        raise ValueError("bone info without its matrices")
    if nmats is None:                          # greedy: every valid matrix that follows
        k = 1
        while is_matrix(b, q + 64 * k):
            k += 1
    else:                                      # fixed count: only the first is validated,
        k = nmats                              # the rest frame may carry scale (7 records)
        if q + 64 * k > len(b):
            raise ValueError("bone info runs past the end of the blob")
    mats = [struct.unpack_from("<16f", b, q + 64 * j) for j in range(k)]
    return {"bone": bone, "parent_bone": parent, "bone_name": name, "mats": mats}, q + 64 * k


def _is_record_start(b, o, scanning=True):
    """A known type byte followed by a valid bone-info head (or a type-23 marker).
    While scanning, rare types whose heads collide with other records' bodies
    are not accepted (see SCANNABLE)."""
    if o >= len(b):
        return False
    t = b[o]
    if t not in (SCANNABLE if scanning else KNOWN):
        return False
    if t == 23:
        return is_matrix(b, o + 5)
    p = o + 1 + (1 if t in COUNT_BYTE else 0)
    if p + 8 > len(b):
        return False
    q = p + 8
    if struct.unpack_from("<I", b, p)[0] == 0xFFFFFFFF:
        s = _pstr(b, q)
        if s is None:
            return False
        q += 1 + len(s)
    # the whole bone info must fit: a type byte that happens to sit before one
    # valid matrix near the end of the blob is not a record (this was the one
    # blob the 2026-08-14 walk could not finish)
    return is_matrix(b, q) and q + 64 * (M[t] if t != 11 else 1) <= len(b)


def _decode_physics(b, p):
    """Type-21 body at p -> (fields, end). Raises if the gates are not 0/1."""
    slots = []
    for _ in range(5):
        gate = b[p]; p += 1
        if gate == 1:
            slots.append(struct.unpack_from("<2f", b, p)); p += 8
        elif gate == 0:
            slots.append(None)
        else:
            raise ValueError(f"physics gate byte {gate}")
    params = struct.unpack_from("<9f", b, p); p += 36
    extra = None
    if is_matrix(b, p):                       # 5 of 1,362 carry one; nothing announces it
        extra = struct.unpack_from("<16f", b, p); p += 64
    out = {"slots": slots, "slide": slots[:3], "swing": slots[3:],
           "limits": [s for s in slots[3:] if s],       # swing pairs, radians (compat)
           "flags": tuple(1 if s else 0 for s in slots),
           "params": params, "gravity": params[4], "mass": params[0], "spring": params[1],
           "slide_damping": params[2], "p3": params[3], "gravity_factor": params[5],
           "wind_factor": params[6], "extra_matrix": extra}
    return out, p


def _decode_hinge(b, p):
    n = b[p]; p += 1
    targets = []
    for _ in range(n):
        t, p = _read_bi(b, p, 4)
        t["weight"] = struct.unpack_from("<f", b, p)[0]; p += 4
        targets.append(t)
    a, c = b[p], b[p + 1]; p += 2
    quat = struct.unpack_from("<4f", b, p); p += 16
    e = b[p]; p += 1
    d = struct.unpack_from("<I", b, p)[0]; p += 4
    return {"targets": targets, "hinge_bytes": (a, c, e), "hinge_quat": quat, "hinge_u32": d}, p


def _decode_targets_fixed(b, p, trailer, per_target_extra=0):
    """u8 n | n x { BoneInfo(4), f32 weight [, matrix] } | trailer bytes  (types 5, 19)."""
    n = b[p]; p += 1
    targets = []
    for _ in range(n):
        t, p = _read_bi(b, p, 4)
        t["weight"] = struct.unpack_from("<f", b, p)[0]; p += 4
        if per_target_extra:
            if not is_matrix(b, p):
                raise ValueError("expected a matrix after the target weight")
            p += 64
        targets.append(t)
    return {"targets": targets}, p + trailer


def _decode_t24(b, p):
    p += 16                                   # vec4: (?, min, max, 0)
    gate = b[p]; p += 1
    if gate != 1:
        raise ValueError("type-24 with no target")
    t, p = _read_bi(b, p, 4)
    return {"targets": [t]}, p + 131


_BODY = {21: _decode_physics, 6: _decode_hinge, 24: _decode_t24,
         5: lambda b, p: _decode_targets_fixed(b, p, 22),
         19: lambda b, p: _decode_targets_fixed(b, p, 69, per_target_extra=1)}


def parse_blob(blob):
    """Yield dicts describing each constraint record, in file order.

    Keys: type, offset, size, header, matrices, tail, error, bone, parent_bone,
    bone_name, mats, exact (True when the record delimited itself and landed on
    the next record), plus the type-specific fields from the decoders above."""
    if len(blob) < 8:
        return
    pos, n = 8, len(blob)
    while pos < n:
        t = blob[pos]
        if t not in KNOWN:
            yield {"type": t, "offset": pos, "error": "unknown constraint type"}
            return
        rec = {"type": t, "offset": pos, "error": None, "exact": False, "bone": None,
               "parent_bone": None, "bone_name": None, "count": None}
        try:
            if t == 23:
                rec["marker"] = struct.unpack_from("<I", blob, pos + 1)[0]
                if not is_matrix(blob, pos + 5):
                    raise ValueError("marker without its matrix")
                rec["mats"] = [struct.unpack_from("<16f", blob, pos + 5)]
                body = pos + 69
            else:
                p = pos + 1
                if t in COUNT_BYTE:
                    rec["count"] = blob[p]; p += 1
                bi, body = _read_bi(blob, p, M[t] if t != 11 else None)
                rec.update(bi)
        except ValueError as e:
            yield dict(rec, error=str(e))
            return
        rec["header"] = blob[pos + 1:pos + H[t]]
        rec["matrices"] = len(rec.get("mats", []))
        end = None
        dec = _BODY.get(t)
        if dec:
            try:
                fields, e = dec(blob, body)
                if e <= n and (e == n or _is_record_start(blob, e, scanning=False)):
                    rec.update(fields); end = e; rec["exact"] = True
            except (ValueError, struct.error, IndexError):
                pass
        if end is None:                       # fall back: scan for the next record head
            nxt = next((c for c in range(body, n) if _is_record_start(blob, c)), None)
            end = nxt if nxt is not None else n
        rec["tail"] = blob[body:end]
        rec["size"] = end - pos
        yield rec
        pos = end


def load_name_dictionary(path):
    """CRC32 -> name. Accepts either a plain name-per-line list (atk_hashes.py
    output) or a `hash<TAB>name<TAB>...` table (reference/grb-bone-names.tsv).
    Plain lists are hashed exact/lower/upper, the way ATK builds its map."""
    out = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.rstrip("\r\n")
            if not s or s.startswith("#"):
                continue
            if "\t" in s:                       # pre-resolved table
                a, b = s.split("\t")[:2]
                if a.isdigit():
                    out.setdefault(int(a), b)
                    continue
                s = b
            for v in (s, s.lower(), s.upper()):
                out.setdefault(zlib.crc32(v.encode("utf-8")) & 0xFFFFFFFF, v)
    return out


def bone_name_hashes(payload, before):
    """The uint32 Bone.Name of every bone declared before `before` in a Skeleton payload."""
    out, pos = set(), 0
    while True:
        k = payload.find(BONE_CLASS_HASH, pos)
        if k < 0 or k > before:
            return out
        pos = k + 4
        if k + BONE_NAME_AFTER_HASH + 4 <= len(payload):
            out.add(struct.unpack_from("<I", payload, k + BONE_NAME_AFTER_HASH)[0])


def load_blob(path, oodle):
    """-> (constraint blob, set of the skeleton's real bone-name hashes)."""
    raw = open(path, "rb").read()
    _, off, _ = read_cfd(raw, 0, oodle)
    files, off, _ = read_cfd(raw, off, oodle)
    i = files.find(REFLEX3_HASH_PAT)
    if i < 0:
        return None, set()
    n = struct.unpack_from("<i", files, i + 4)[0]
    return files[i + 8:i + 8 + n], bone_name_hashes(files, i)


def _deg(pair):
    return f"[{math.degrees(pair[0]):+.0f},{math.degrees(pair[1]):+.0f}]" if pair else "-"


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raw_mode = "--raw" in argv
    if raw_mode:
        argv.remove("--raw")
    override = names_path = None
    if "--oodle" in argv:
        k = argv.index("--oodle"); override = argv[k + 1]; del argv[k:k + 2]
    if "--names" in argv:
        k = argv.index("--names"); names_path = argv[k + 1]; del argv[k:k + 2]
    if len(argv) < 2:
        print(__doc__)
        return
    dictionary = load_name_dictionary(names_path) if names_path else {}

    path = argv[1]
    oodle = Oodle(find_oodle(path, override))
    if not oodle.ok:
        print("  ! no Oodle DLL found - pass --oodle path\\to\\oo2core_7_win64.dll")
        return
    blob, bones = load_blob(path, oodle)
    print("=" * 78)
    print(f"FILE: {os.path.basename(path)}")
    if blob is None:
        print("  no Reflex3SkeletonConstraints - is this a Skeleton .data?")
        return
    if len(blob) <= 8:
        print(f"  Reflex3 blob is {len(blob)} B (header only) -> this skeleton has NO bone physics")
        return
    magic, version = struct.unpack_from("<II", blob, 0)
    print(f"  blob {len(blob):,} B   magic=0x{magic:08X} version={version}"
          + ("" if magic == BLOB_MAGIC else "   ! unexpected magic"))
    print("=" * 78)

    recs = list(parse_blob(blob))
    good = [r for r in recs if not r.get("error")]
    exact = sum(1 for r in good if r.get("exact"))
    counts = {}
    for r in good:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    print(f"  {len(good)} constraint record(s); {exact} delimited exactly, "
          f"{len(good) - exact} located by scan")
    print("  by type: " + ", ".join(
        f"{t}={c}" + (f" ({NAMES[t]})" if t in NAMES else "") for t, c in sorted(counts.items())))

    def label(v):
        return dictionary.get(v, f"{v:08x}") if dictionary else f"{v:08x}"

    if bones:
        ids = [r["bone"] for r in good if r.get("bone") not in (None, 0xFFFFFFFF)]
        known = sum(1 for b in ids if b in bones)
        print(f"  skeleton declares {len(bones)} bone(s); "
              f"{known}/{len(ids)} constraint BoneIDs resolve to one of them")
    named = []
    for r in good:
        for t in [r] + r.get("targets", []):
            if t.get("bone_name") and t["bone_name"] not in named:
                named.append(t["bone_name"])
    if named:
        print("  body bones referenced by name: " + ", ".join(named))

    phys = [r for r in good if r["type"] == PHYSICS_TYPE and "params" in r]
    if phys:
        wid = 20 if dictionary else 10
        print(f"\n  {len(phys)} PHYSICS record(s) - each drives one bone "
              f"('+' = its parent is the previous record's bone, i.e. a chain):")
        print(f"    {'#':>3}  {'bone':>{wid}} {'<- parent':>{wid}}  "
              f"{'swing 1':<11} {'swing 2':<11} {'slide':<6} {'mass*':>5} {'spring*':>7} "
              f"{'damp*':>5} {'p3':>4} {'grav':>5}  {'height':>6}")
        prev = None
        for i, r in enumerate(phys if raw_mode else phys[:40]):
            chain = "+" if prev == r["parent_bone"] else " "
            mark = "*" if bones and r["bone"] in bones else " "
            sl = "".join(a for a, s in zip("xyz", r["slide"]) if s) or "-"
            p = r["params"]
            print(f"    {i:>3}{mark}{chain}{label(r['bone']):>{wid}} {label(r['parent_bone']):>{wid}}  "
                  f"{_deg(r['swing'][0]):<11} {_deg(r['swing'][1]):<11} {sl:<6} {p[0]:>5g} {p[1]:>7g} "
                  f"{p[2]:>5g} {p[3]:>4g} {p[4]:>5g}  {r['mats'][2][11]:>6.2f}")
            prev = r["bone"]
        if not raw_mode and len(phys) > 40:
            print(f"    ... and {len(phys) - 40} more (--raw for all)")
        print("    swing limits in degrees; slide = which axes may translate; "
              "height = the parent frame's z in character space")
        print("    * = inferred field name (see reference/skeleton-reflex3-physics.md)")
        if bones:
            print("    (* after # = BoneID matches a bone declared by this skeleton)")

    other = [r for r in good if r["type"] != PHYSICS_TYPE]
    if other and raw_mode:
        print(f"\n  {len(other)} non-physics record(s):")
        for r in other[:60]:
            tg = r.get("targets")
            extra = ""
            if tg:
                extra = "  targets: " + ", ".join(
                    (t["bone_name"] or label(t["bone"])) + (f" w={t['weight']:g}" if "weight" in t else "")
                    for t in tg)
            elif r["type"] == 23:
                extra = f"  v={r.get('marker')}"
            elif r.get("count") is not None:
                extra = f"  count={r['count']}"
            print(f"    @0x{r['offset']:06x}  type={r['type']:<3} "
                  f"{NAMES.get(r['type'], '(not modelled by ATK)'):<34} "
                  f"size={r['size']:<6}{'exact' if r['exact'] else 'scan '}{extra}")
    for r in recs:
        if r.get("error"):
            print(f"\n  ! stopped at 0x{r['offset']:06x}: {r['error']} (type {r['type']})")


if __name__ == "__main__":
    main(sys.argv)
