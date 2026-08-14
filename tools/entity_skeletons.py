#!/usr/bin/env python3
"""
entity_skeletons.py - read a character/item's SKELETON BUILD SHEET out of an EntityBuilder.

An `EntityBuilder` is what assembles a character or a piece of gear: it lists the
resources that make it up, each as a typed reference. This tool pulls out the
`Skeleton` references and - if you point it at your install - tells you which of
them carry Reflex3 **bone physics** and how much.

That matters because bone physics is the re-bindable kind: a garment's motion
lives in an add-on skeleton, and the EntityBuilder just names it by 64-bit ID.
See reference/skeleton-reflex3-physics.md.

    python entity_skeletons.py 1536663434687_-_PLAYER_Template.data \
        --install "H:\\SteamLibrary\\steamapps\\common\\Ghost Recon Breakpoint"

    python entity_skeletons.py TSec_MIS_Blake.data          # names only, no install needed

READ-ONLY.

RECORD FORMAT (verified 2026-08-14 - 16/16 extracted IDs resolved to real
skeletons across two builders):

    u32  TypeHash   0x24AECB7C == CRC32("Skeleton")
    u16  0x0000
    u8   0x12                      record tag
    6x   0x00
    u64  ClassID                   the resource referenced
    u32  Slot                      attachment slot index

Swap that ClassID and you swap which rig - and therefore which physics - the
item uses. ATK exports EntityBuilders to XML for GRB, so this is editable
through supported tooling, not only in hex.
"""
import sys, os, struct, zlib, re, glob

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from data_inspect import read_cfd, Oodle, find_oodle                 # noqa: E402
from skeleton_reflex import skeleton_entries, reflex_blob, EMPTY     # noqa: E402

SKELETON_TYPE_ID = zlib.crc32(b"Skeleton")                 # 615435132
REF_PREFIX = struct.pack("<I", SKELETON_TYPE_ID) + b"\x00\x00\x12" + b"\x00" * 6
NAME_RE = re.compile(rb"[ -~]{6,}")


def skeleton_refs(payload):
    """Yield (offset, class_id, slot, nearest_preceding_name) for each Skeleton reference."""
    names = [(m.start(), m.group().decode("ascii")) for m in NAME_RE.finditer(payload)]
    pos = 0
    while True:
        i = payload.find(REF_PREFIX, pos)
        if i < 0:
            return
        pos = i + 1
        try:
            cid, slot = struct.unpack_from("<QI", payload, i + len(REF_PREFIX))
        except struct.error:
            return
        before = [n for n in names if n[0] < i]
        yield i, cid, slot, (before[-1][1] if before else "")


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


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    install = override = None
    if "--install" in argv:
        k = argv.index("--install"); install = argv[k + 1]; del argv[k:k + 2]
    if "--oodle" in argv:
        k = argv.index("--oodle"); override = argv[k + 1]; del argv[k:k + 2]
    if len(argv) < 2:
        print(__doc__)
        return

    path = argv[1]
    oodle = Oodle(find_oodle(path, override or
                             (os.path.join(install, "oo2core_7_win64.dll") if install else None)))
    if not oodle.ok:
        print("  ! no Oodle DLL found - pass --oodle path\\to\\oo2core_7_win64.dll")
        return

    raw = open(path, "rb").read()
    _, off, _ = read_cfd(raw, 0, oodle)
    payload, off, _ = read_cfd(raw, off, oodle)

    refs = list(skeleton_refs(payload))
    print("=" * 88)
    print(f"FILE: {os.path.basename(path)}   payload {len(payload):,} B")
    print(f"  {len(refs)} Skeleton reference(s)")
    print("=" * 88)
    if not refs:
        print("  none - is this an EntityBuilder .data?")
        return

    lookup = index_skeletons(install) if install else {}
    if not lookup:
        print("  (pass --install <GRB folder> to resolve names and physics sizes)\n")
        print(f"    {'offset':>8}  {'slot':>5}  {'ClassID':>15}   near")
        for o, cid, slot, near in refs:
            print(f"    {o:>8x}  {slot:>5}  {cid:>15}   {near[:44]}")
        return

    print(f"    {'slot':>5}  {'skeleton':<40} {'bone physics':>14}   assigned near")
    unknown = 0
    for o, cid, slot, near in refs:
        hit = lookup.get(cid)
        if not hit:
            unknown += 1
            print(f"    {slot:>5}  {'<id ' + str(cid) + ' not found>':<40} {'':>14}   {near[:34]}")
            continue
        name, forge, offset, ln = hit
        with open(forge, "rb") as f:
            f.seek(offset)
            try:
                _, blen, _, _ = reflex_blob(f.read(ln), oodle)
            except Exception:
                blen = -1
        phys = f"{blen:,} B" if blen > EMPTY else ("-" if blen >= 0 else "?")
        print(f"    {slot:>5}  {name[:40]:<40} {phys:>14}   {near[:34]}")
    moving = sum(1 for o, cid, s, n in refs
                 if cid in lookup and _has_physics(lookup[cid], oodle))
    print(f"\n  {moving} of {len(refs)} referenced rigs carry bone physics"
          + (f"; {unknown} ID(s) not found in this install" if unknown else ""))
    print("  A rig with physics is the part that MOVES - hair, straps, a coat, a beard.")


def _has_physics(hit, oodle):
    _, forge, offset, ln = hit
    with open(forge, "rb") as f:
        f.seek(offset)
        try:
            return reflex_blob(f.read(ln), oodle)[1] > EMPTY
        except Exception:
            return False


if __name__ == "__main__":
    main(sys.argv)
