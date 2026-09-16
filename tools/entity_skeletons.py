#!/usr/bin/env python3
"""
entity_skeletons.py - which SKELETONS a container assigns, and which resource assigns each one.

Characters and gear are assembled by build tables: each row lists the resources
that make an item up. This tool walks a `.data` container, finds every row
component that assigns a `Skeleton`, names the resource that holds it, and - if
you point it at your install - tells you which of those rigs carry Reflex3
**bone physics** and how much.

That matters because bone physics is the re-bindable kind: a garment's motion
lives in an add-on skeleton, and the garment's own build table names it by
64-bit ID. See reference/skeleton-reflex3-physics.md.

    python entity_skeletons.py 23_-_TEAMMATE_Template.data \
        --install "D:\\SteamLibrary\\steamapps\\common\\Ghost Recon Breakpoint"

    python entity_skeletons.py 23_-_TEAMMATE_Template.data --grep Kilt   # holder or rig name
    python entity_skeletons.py 22_-_PLAYER_Template.data                  # IDs only, no install needed

READ-ONLY.

WHERE AN ASSIGNMENT LIVES (verified 2026-09-16 from ATK 1.3.1's BuildRow.Read /
DynamicProperty / Handle, and on real files):

    BuildRow component:  i32  Index           which column this component fills
                         u32  DataType        0x24AECB7C == CRC32("Skeleton")
                         u32  Type            0x00120000 = Handle
                         u32  Unk00           0 in every one seen
                         u8   (ignored)       ATK discards it on read, writes 0
                         u64  ClassID         the skeleton assigned

The same Skeleton DataType also appears in BuildColumn declarations as a
`Reference` (Type 0x001C0000, 26 B): those carry ClassID 0 in every one of 2,046
checked - an empty typed column, not an assignment - and are skipped here. Every
Handle found resolved to a real skeleton (3,966 of 3,966 across PLAYER_Template
and both TEAMMATE_Template copies).

⚠️ CORRECTED 2026-09-16. Before then this tool read the u32 AFTER the ClassID
as the assignment's "slot". That u32 is the NEXT component's Index - or, after a
row's last component, the start of whatever follows (hence the stray 1792, 2816,
3328, 4864 "slots"). It also attributed each assignment to the nearest string
before it in the whole decompressed block, which is how the 2026-08-14 notes
came to credit PLAYER_Template's EntityBuilder, and PLAYER_SkelAddons, with rigs
that live in other resources. The ClassIDs were always right.

Swap the ClassID and you swap which rig - and therefore which physics - the item
uses. Garment rigs are assigned from the garment's own table (Player_Kilt_Addon
from TP_PANT_Kilt); player-wide rigs from PLAYER_SkelAddons.
"""
import sys, os, struct, zlib, re, glob, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import data_inspect as di                                            # noqa: E402
from skeleton_reflex import skeleton_entries, reflex_blob, EMPTY     # noqa: E402

SKELETON_TYPE_ID = zlib.crc32(b"Skeleton")                 # 615435132
HANDLE = 0x00120000                                         # DynamicProperty Type
REF_PREFIX = struct.pack("<III", SKELETON_TYPE_ID, HANDLE, 0) + b"\x00"

SkeletonRef = collections.namedtuple("SkeletonRef", "offset index class_id")


def skeleton_refs(payload):
    """Yield SkeletonRef(offset, index, class_id) for each Handle-typed Skeleton
    component in one resource's payload. `offset` is where the component's Index
    starts."""
    pos = 0
    while True:
        i = payload.find(REF_PREFIX, pos)
        if i < 0:
            return
        pos = i + 1
        if i < 4 or i + len(REF_PREFIX) + 8 > len(payload):
            continue
        index, = struct.unpack_from("<i", payload, i - 4)
        cid, = struct.unpack_from("<Q", payload, i + len(REF_PREFIX))
        yield SkeletonRef(i - 4, index, cid)


def index_skeletons(install):
    """{class_id: (name, forge_path, offset, length)} for every Skeleton in the install."""
    out = {}
    for p in sorted(glob.glob(os.path.join(install, "*.forge"))):
        try:
            for fid, name, offset, ln in skeleton_entries(p):
                out.setdefault(fid, (name, p, offset, ln))
        except Exception:
            continue
    return out


def physics_size(hit, oodle):
    """Bytes of Reflex3 constraint data in a skeleton, or -1 if unreadable."""
    _, forge, offset, ln = hit
    with open(forge, "rb") as f:
        f.seek(offset)
        try:
            return reflex_blob(f.read(ln), oodle)[1]
        except Exception:
            return -1


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    install = override = pattern = None
    if "--install" in argv:
        k = argv.index("--install"); install = argv[k + 1]; del argv[k:k + 2]
    if "--oodle" in argv:
        k = argv.index("--oodle"); override = argv[k + 1]; del argv[k:k + 2]
    if "--grep" in argv:
        k = argv.index("--grep"); pattern = re.compile(argv[k + 1], re.I); del argv[k:k + 2]
    if len(argv) < 2:
        print(__doc__)
        return

    path = argv[1]
    oodle = di.Oodle(di.find_oodle(path, override or
                                   (os.path.join(install, "oo2core_7_win64.dll") if install else None)))
    if not oodle.ok:
        print("  ! no Oodle DLL found - pass --oodle path\\to\\oo2core_7_win64.dll")
        return

    _meta, files = di.read_container(path, oodle)
    resources, end = di.walk(files)
    lookup = index_skeletons(install) if install else {}
    refs = [(r, ref) for r in resources for ref in skeleton_refs(r.payload)]
    if pattern:
        refs = [(r, ref) for r, ref in refs
                if pattern.search(r.name) or pattern.search(lookup.get(ref.class_id, ("",))[0])]

    print("=" * 96)
    print(f"FILE: {os.path.basename(path)}   {len(resources):,} resources")
    if end != len(files):
        print(f"  !! container walk stopped at byte {end:,} of {len(files):,} - results are INCOMPLETE")
    holders = len({r.offset for r, _ in refs})
    print(f"  {len(refs)} Skeleton assignment(s) in {holders} resource(s)"
          + (f" matching {pattern.pattern!r}" if pattern else ""))
    print("=" * 96)
    if not refs:
        print("  none")
        return
    if not lookup:
        print("  (pass --install <GRB folder> to resolve names and physics sizes)\n")
    print(f"    {'held by':<40} {'index':>5}  {'skeleton':<40} {'bone physics':>12}")
    sizes, unknown = {}, 0
    for r, ref in refs:
        hit = lookup.get(ref.class_id)
        if not lookup:
            print(f"    {r.name[:40]:<40} {ref.index:>5}  {ref.class_id:<40}")
            continue
        if not hit:
            unknown += 1
            print(f"    {r.name[:40]:<40} {ref.index:>5}  {'<id ' + str(ref.class_id) + ' not found>':<40}")
            continue
        if ref.class_id not in sizes:
            sizes[ref.class_id] = physics_size(hit, oodle)
        blen = sizes[ref.class_id]
        phys = f"{blen:,} B" if blen > EMPTY else ("-" if blen >= 0 else "?")
        print(f"    {r.name[:40]:<40} {ref.index:>5}  {hit[0][:40]:<40} {phys:>12}")
    if lookup:
        moving = sum(1 for _, ref in refs if sizes.get(ref.class_id, -1) > EMPTY)
        print(f"\n  {moving} of {len(refs)} assigned rigs carry bone physics"
              + (f"; {unknown} ID(s) not found in this install" if unknown else ""))
        print("  A rig with physics is the part that MOVES - hair, straps, a coat, a beard.")


if __name__ == "__main__":
    main(sys.argv)
