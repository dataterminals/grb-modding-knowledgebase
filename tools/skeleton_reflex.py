#!/usr/bin/env python3
"""
skeleton_reflex.py - find GRB skeletons that carry Reflex3 bone-physics.

Reflex3 is Anvil's per-bone secondary-motion system: swing/slide constraints with
gravity and wind, evaluated on skeleton bones. It is what moves hair, ponytails,
backpack straps, weapon slings, scarves - and the Bodark trench coat - with no
cloth simulation at all. Unlike `.cloth` (welded to one mesh's vertices), bone
physics is re-bindable by weight-painting, which makes it the practical route for
putting an existing garment's motion onto a NEW mesh.

    # every skeleton in an install, ranked by how much physics it carries
    python skeleton_reflex.py "H:\\SteamLibrary\\steamapps\\common\\Ghost Recon Breakpoint"

    # one forge
    python skeleton_reflex.py DataPC.forge

    # one already-unpacked skeleton .data
    python skeleton_reflex.py 1889064665537_-_Player_Kilt_Addon.data

    --csv out.csv      write the full table
    --oodle <path>     point at oo2core_7_win64.dll (auto-found next to the forge)

READ-ONLY. It never writes to the game.

HOW IT WORKS (verified from decompiled ATK v1.3.1 + all 2,469 skeletons in a
2026-08-14 install; see reference/skeleton-reflex3-physics.md):
- Skeleton.Read() reads a `Reflex3Constraints` ObjectPtr for GRB explicitly. The
  pointer is written as an INLINE object, so the class hash 2386539642 appears in
  the decompressed payload, immediately followed by an int32 blob length.
- A blob of 8 bytes is header-only => that skeleton has NO bone physics.
- Every non-empty blob starts with magic 0x12341234 + version 3012000. ATK cannot
  parse the body: its reader validates Mirage's constants (19620929 / 2 / 5000004)
  and is gated behind `Version != Game.Mirage`, so it keeps the blob as opaque
  Base64 for GRB.
"""
import sys, os, struct, glob

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from data_inspect import read_cfd, Oodle, find_oodle          # noqa: E402

SKELETON_TYPE_ID = 615435132          # CRC32("Skeleton")
REFLEX3_HASH = 2386539642             # CRC32("Reflex3SkeletonConstraints")
REFLEX3_PAT = struct.pack("<I", REFLEX3_HASH)
GRB_BLOB_MAGIC = 0x12341234
GRB_BLOB_VERSION = 3012000
EMPTY = 8                             # header-only blob length


def skeleton_entries(forge_path):
    """Yield (id, name, offset, length) for every Skeleton-typed entry in a forge."""
    with open(forge_path, "rb") as f:
        if f.read(8) != b"scimitar":
            raise ValueError("not a .forge (missing 'scimitar' magic)")
        f.seek(9)
        struct.unpack("<I", f.read(4))                 # version
        hdrsize = struct.unpack("<Q", f.read(8))[0]
        f.seek(hdrsize + 32)
        fileset_count = struct.unpack("<I", f.read(4))[0]
        pos = struct.unpack("<q", f.read(8))[0]
        seen = 0
        while pos != -1 and seen < fileset_count:
            f.seek(pos)
            count = struct.unpack("<I", f.read(4))[0]
            f.read(4)                                  # const 2
            off_tbl = struct.unpack("<q", f.read(8))[0]
            nxt = struct.unpack("<q", f.read(8))[0]
            f.read(8)
            info_tbl = struct.unpack("<q", f.read(8))[0]
            f.seek(off_tbl); ob = f.read(count * 20)
            f.seek(info_tbl); ib = f.read(count * 192)
            for r in range(count):
                offset, fid, ln = struct.unpack_from("<qQi", ob, r * 20)
                b = r * 192
                if struct.unpack_from("<I", ib, b + 16)[0] != SKELETON_TYPE_ID:
                    continue
                nm = ib[b + 44:b + 44 + 128]
                z = nm.find(b"\0")
                yield fid, nm[:z if z >= 0 else 128].decode("latin-1", "replace"), offset, ln
            seen += 1
            pos = nxt


def reflex_blob(data_bytes, oodle):
    """(payload_len, blob_len, magic, version) for one .data's bytes. blob_len -1 = absent."""
    _, off, _ = read_cfd(data_bytes, 0, oodle)
    files, off, _ = read_cfd(data_bytes, off, oodle)
    i = files.find(REFLEX3_PAT)
    if i < 0:
        return len(files), -1, None, None
    blob_len = struct.unpack_from("<i", files, i + 4)[0]
    if blob_len >= EMPTY:
        magic, ver = struct.unpack_from("<II", files, i + 8)
    else:
        magic = ver = None
    return len(files), blob_len, magic, ver


def scan(paths, oodle, csv_path=None):
    rows, unreadable = [], 0
    for forge in paths:
        with open(forge, "rb") as fh:
            for fid, name, offset, ln in skeleton_entries(forge):
                fh.seek(offset)
                try:
                    plen, blen, magic, ver = reflex_blob(fh.read(ln), oodle)
                except Exception:
                    unreadable += 1
                    continue
                rows.append((os.path.basename(forge), fid, name, plen, blen, magic, ver))

    have = [r for r in rows if r[4] > EMPTY]
    odd = {(r[5], r[6]) for r in have} - {(GRB_BLOB_MAGIC, GRB_BLOB_VERSION)}
    print("=" * 74)
    print(f"  {len(rows)} skeletons read ({unreadable} unreadable)")
    print(f"  {len(have)} carry Reflex3 bone physics; {len(rows) - len(have)} are empty")
    if odd:
        print(f"  !! unexpected blob headers: {sorted(odd)}")
    elif have:
        print(f"  all blobs: magic 0x{GRB_BLOB_MAGIC:08X}  version {GRB_BLOB_VERSION}")
    print("=" * 74)
    print("  A piece named *_Reflex / *_Addon is usually the physics layer for a")
    print("  character or a garment - that is the one to look at.\n")
    for r in sorted(have, key=lambda r: -r[4])[:40]:
        print(f"    {r[4]:>8} B   {r[2][:52]:<52} ({r[0]})")
    if len(have) > 40:
        print(f"    ... and {len(have) - 40} more (use --csv for the full table)")

    if csv_path:
        import csv as _csv
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["forge", "id", "name", "payload_bytes", "reflex_blob_bytes",
                        "blob_magic", "blob_version"])
            for fg, fid, nm, plen, blen, mg, vr in rows:
                w.writerow([fg, fid, nm, plen, blen,
                            f"0x{mg:08X}" if mg is not None else "", vr if vr is not None else ""])
        print(f"\n  wrote {len(rows)} rows to {csv_path}")


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    csv_path = override = None
    if "--csv" in argv:
        k = argv.index("--csv"); csv_path = argv[k + 1]; del argv[k:k + 2]
    if "--oodle" in argv:
        k = argv.index("--oodle"); override = argv[k + 1]; del argv[k:k + 2]
    args = argv[1:]
    if not args:
        print(__doc__)
        return

    target = args[0]
    oodle = Oodle(find_oodle(target, override))
    if not oodle.ok:
        print("  ! no Oodle DLL found - pass --oodle path\\to\\oo2core_7_win64.dll")
        return

    if os.path.isdir(target):
        forges = sorted(glob.glob(os.path.join(target, "*.forge")))
        if not forges:
            print(f"  no .forge files in {target}")
            return
        scan(forges, oodle, csv_path)
    elif target.lower().endswith(".forge"):
        scan([target], oodle, csv_path)
    else:                                                   # a single unpacked .data
        plen, blen, magic, ver = reflex_blob(open(target, "rb").read(), oodle)
        print("=" * 74)
        print(f"FILE: {os.path.basename(target)}   payload {plen:,} B")
        if blen < 0:
            print("  no Reflex3SkeletonConstraints found - is this a Skeleton .data?")
        elif blen <= EMPTY:
            print(f"  Reflex3 blob = {blen} B (header only) -> NO bone physics")
        else:
            print(f"  Reflex3 blob = {blen:,} B  magic=0x{magic:08X} version={ver}")
            print("  -> this skeleton DOES carry per-bone physics constraints")


if __name__ == "__main__":
    main(sys.argv)
