#!/usr/bin/env python3
"""
reflex3.py - decode the Reflex3 bone-physics constraints inside a GRB skeleton.

Reflex3 is what makes hair, ponytails, backpack straps, weapon slings, scarves -
and the Bodark trench coat - move without any cloth simulation. This tool opens a
Skeleton resource and prints the constraints: how each bone is allowed to swing,
in degrees, plus its gravity and damping parameters.

    python reflex3.py 1889064665537_-_Player_Kilt_Addon.data
    python reflex3.py Tsec_Trench_AddonSkeleton.data --raw     # per-record detail
    python reflex3.py Watch_Skeleton.data --names hashes.txt   # bone NAMES, not numbers

`--names` takes the plain-text dictionary produced by atk_hashes.py. It resolves
the standard biped bones (Spine2, LeftForeArm, Head) but not GRB's bespoke
dangle-bone names - enough to see what a rig ATTACHES to.

READ-ONLY.

FORMAT (reverse-engineered 2026-08-14; see reference/skeleton-reflex3-physics.md).
ATK cannot read this: its parser validates Mirage's constants and is gated behind
`Version != Game.Mirage`, so for GRB it keeps the blob as an opaque Base64 lump.

    blob := u32 magic 0x12341234 | u32 version 3012000 | record*

    record := u8 type
              | [u8 0x01]        only for type 9
              | u32 BoneID       CRC32 of the bone's name
              | u32 ParentBoneID
              | M(type) x 64-byte 4x4 affine matrix (row-major, orthonormal 3x3,
                                                     translation in column 3,
                                                     bottom row 0,0,0,1)
                                 the first one is Reflex3BoneInfo.InitTransform
              | tail (type-specific)

BoneID/ParentBoneID are CRC32 of the exact-case bone name - the same hashing the
game bakes into collider names like `..._Ragdoll_LeftForeArm_2310617728`, which
match CRC32 9/9. Checked against each skeleton's real bone list: 99.7% of records
resolve, against a 0.000% random-value control.

H and M are constant per type (unanimous across 205 first-records; the full walk
consumes 204/205 blobs exactly).

    type  H   M   ATK's Reflex3ConstraintTypeRegistry
      5   9   4   -                      19   9   4   -
      6   9   4   HingeVector            20   9   4   -
      7   9   4   LookAt                 21   9   5   -   <- the physics record
      9  10   4   Orientation            23   5   1   -
                                         24   9   4   -

Type 21 tail (386-byte record; decoded and validated over all 1,354 in the game):

    u8 x3                     flags
    { u8 gate ; if gate: f32 lo, f32 hi }   angular limits, RADIANS
                                            (1262 records carry 2 pairs, 72 carry 1)
    f32 x9                    param block; param[4] is GRAVITY - 9.8 in 1344/1354
"""
import sys, os, struct, math, zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from data_inspect import read_cfd, Oodle, find_oodle          # noqa: E402

REFLEX3_HASH_PAT = struct.pack("<I", 2386539642)
BLOB_MAGIC, BLOB_VERSION = 0x12341234, 3012000

# header bytes and matrix count per constraint type
H = {5: 9, 6: 9, 7: 9, 9: 10, 19: 9, 20: 9, 21: 9, 23: 5, 24: 9}
M = {5: 4, 6: 4, 7: 4, 9: 4, 19: 4, 20: 4, 21: 5, 23: 1, 24: 4}
# names ATK knows; the rest GRB uses but ATK never modelled
NAMES = {6: "HingeVector", 7: "LookAt", 9: "Orientation", 21: "Physics (swing/gravity)"}
PHYSICS_TYPE = 21
# offset of the BoneID uint32 inside `header` (type 9 carries one extra 0x01 byte)
BONE_OFFSET = {9: 1}
BONE_CLASS_HASH = struct.pack("<I", 2507411529)   # CRC32("Bone")
BONE_NAME_AFTER_HASH = 4                          # Bone.Name sits 4 B past the class hash


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


def _is_record_start(b, o):
    t = b[o] if o < len(b) else None
    return t in H and is_matrix(b, o + H[t])


def parse_blob(blob):
    """Yield dicts describing each constraint record."""
    if len(blob) < 8:
        return
    magic, version = struct.unpack_from("<II", blob, 0)
    pos = 8
    while pos < len(blob):
        t = blob[pos]
        if t not in H:
            yield {"type": t, "offset": pos, "error": "unknown constraint type"}
            return
        head = blob[pos + 1:pos + H[t]]
        mat_start = pos + H[t]
        mat_end = mat_start + 64 * M[t]
        if mat_end > len(blob):
            yield {"type": t, "offset": pos, "error": "record runs past end of blob"}
            return
        nxt = next((c for c in range(mat_end, len(blob)) if _is_record_start(blob, c)), None)
        end = nxt if nxt is not None else len(blob)
        rec = {"type": t, "offset": pos, "header": head, "matrices": M[t],
               "tail": blob[mat_end:end], "size": end - pos, "error": None,
               "bone": None, "parent_bone": None}
        d = BONE_OFFSET.get(t, 0)
        if len(head) >= d + 8:
            rec["bone"], rec["parent_bone"] = struct.unpack_from("<II", head, d)
        if t == PHYSICS_TYPE:
            rec.update(_decode_physics(rec["tail"]))
        yield rec
        pos = end


def load_name_dictionary(path):
    """CRC32 -> name, built the way ATK does it (exact, lower- and upper-case)."""
    out = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.rstrip("\r\n")
            if not s:
                continue
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


def _decode_physics(tail):
    """Type-21 tail: 3 flag bytes, gated (lo,hi) angle limits, then 9 floats."""
    out = {"flags": tuple(tail[:3]), "limits": [], "params": None}
    if len(tail) < 36:
        return out
    out["params"] = struct.unpack("<9f", tail[-36:])
    out["gravity"] = out["params"][4]
    mid, o = tail[3:-36], 0
    while o < len(mid):
        gate = mid[o]; o += 1
        if gate == 1 and o + 8 <= len(mid):
            lo, hi = struct.unpack_from("<2f", mid, o); o += 8
            out["limits"].append((lo, hi))
        elif gate != 0:
            break
    return out


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
    consumed = sum(r.get("size", 0) for r in recs if not r.get("error"))
    counts = {}
    for r in recs:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    print(f"  {len(recs)} constraint record(s); "
          f"{consumed + 8:,}/{len(blob):,} bytes accounted for")
    print("  by type: " + ", ".join(
        f"{t}={c}" + (f" ({NAMES[t]})" if t in NAMES else "") for t, c in sorted(counts.items())))

    if bones:
        ids = [r["bone"] for r in recs if r.get("bone") is not None]
        known = sum(1 for b in ids if b in bones)
        print(f"  skeleton declares {len(bones)} bone(s); "
              f"{known}/{len(ids)} constraint BoneIDs resolve to one of them")
        drives = len({r['bone'] for r in recs if r.get('bone') is not None})
        print(f"  constraints drive {drives} distinct bone(s)")

    phys = [r for r in recs if r["type"] == PHYSICS_TYPE and not r.get("error")]
    if phys:
        def label(v):
            return dictionary.get(v, str(v)) if dictionary else str(v)

        wid = 22 if dictionary else 11
        print(f"\n  {len(phys)} PHYSICS constraint(s) - each drives one bone:")
        print(f"    {'#':>4}  {'bone':>{wid}} {'<- parent':>{wid}}  "
              f"{'swing limits (degrees)':<34} {'gravity':>8}  damping/stiffness")
        for n, r in enumerate(phys if raw_mode else phys[:20]):
            lim = "  ".join(f"[{math.degrees(lo):+7.1f}, {math.degrees(hi):+7.1f}]"
                            for lo, hi in r["limits"]) or "(none)"
            p = r.get("params") or ()
            extra = ", ".join(f"{v:g}" for v in p[:4]) if p else ""
            mark = "*" if bones and r.get("bone") in bones else " "
            print(f"    {n:>4}{mark} {label(r.get('bone', 0)):>{wid}} "
                  f"{label(r.get('parent_bone', 0)):>{wid}}  "
                  f"{lim:<34} {r.get('gravity', float('nan')):>8.3f}  {extra}")
        if not raw_mode and len(phys) > 20:
            print(f"    ... and {len(phys) - 20} more (--raw for all)")
        if bones:
            print("    (* = BoneID matches a bone declared by this skeleton)")

    other = [r for r in recs if r["type"] != PHYSICS_TYPE]
    if other and raw_mode:
        print(f"\n  {len(other)} non-physics record(s):")
        for r in other[:40]:
            print(f"    @0x{r['offset']:06x}  type={r['type']:<3} "
                  f"{NAMES.get(r['type'], '(not modelled by ATK)'):<24} "
                  f"matrices={r.get('matrices')} size={r.get('size')}")
    err = [r for r in recs if r.get("error")]
    for r in err:
        print(f"\n  ! stopped at 0x{r['offset']:06x}: {r['error']} (type {r['type']})")


if __name__ == "__main__":
    main(sys.argv)
