#!/usr/bin/env python3
"""
forge_inspect.py - inspect and diff GRB `.forge` archives by their real file IDs.

Reads only a forge's INDEX (no payload decompression, no full unpack), so it's
fast even on the 23 GB resources forge. Two uses:

  * Inspect one forge -> version, entry count, and a resource-type histogram.
        python forge_inspect.py DataPC_patch_01.forge
        python forge_inspect.py DataPC_Resources.forge --csv out.csv   # dump every entry

  * Diff two forges by real file ID -> shared IDs (overrides / mod CONFLICTS),
    and how many are unique to each. This is a mod-conflict / merge checker.
        python forge_inspect.py modA_patch_01.forge modB_patch_01.forge

Why "real file ID": the number in an unpacked filename (`<N>_-_name.data`) is a
positional index, NOT the ID. The true 64-bit ID is `ForgeEntry.ID` in the forge
index (== the resource's embedded ClassID). See reference/resource-type-ids.md
and docs/06-game-load-and-reassembly.md.

Format (verified from ATK v1.3.1 ForgeFile.Deserialize27 / FileSet / ForgeEntry):
header has scimitar magic; at (HeaderSize+32) a uint32 FileSet count and int64
first-FileSet offset; each FileSet: uint32 count, +8 int64 offsetTable, +16 int64
next-FileSet (-1=last), +32 int64 infoTable; offset records are 20 bytes
{i64 Offset, u64 ID, i32 Len}; info records are 192 bytes (Extension @+16, Name @+44).
"""
import sys, struct, zlib

# resource type id = CRC32(typeName); resolve the common GRB ones. Extend freely.
_TYPE_NAMES = [
    "Mesh","HairMesh","CompiledMesh","MeshData","MeshPrimitive","SubMesh","Skeleton",
    "Bone","LODSelector","LODDescriptor","FacialSolverData","TextureMap","CompiledMip",
    "CompiledTextureMap","TextureSet","TextureMapSpec","Material","MaterialTemplate",
    "BuildTable","EntityBuilder","EntityGroupBuilder","Entity","LocalizationPackage",
    "Animation","Event","GlobalMetaFile","PrefetchingFileInfos",
    "Cloth","SoftBody","MotionSoftBody","ClothLOD","MotionClothLOD","SoftBodyLOD",
    "MotionSoftBodyLOD","ClothState","MotionClothState","SoftBodyState","MotionSoftBodyState",
    "ClothSettings","SoftBodySettings","ClothActionSettings","SoftBodyConstraint",
    "SoftBodyVertexMapping","FX","SplashFX","SceneData","TheaterData","DataLayer",
    "GameplayTag","WaveSpawner",
]
TYPE_BY_ID = {zlib.crc32(n.encode("ascii")): n for n in _TYPE_NAMES}
TYPE_BY_ID[0] = "(sidecar)"


def type_name(ext):
    return TYPE_BY_ID.get(ext, f"#{ext}")


def parse_forge_index(path, want_names=True):
    """Return (version, fileset_count, entries) where entries = [(id, ext, name), ...]."""
    with open(path, "rb") as f:
        if f.read(8) != b"scimitar":
            raise ValueError("not a .forge (missing 'scimitar' magic)")
        f.seek(9)
        version = struct.unpack("<I", f.read(4))[0]
        hdrsize = struct.unpack("<Q", f.read(8))[0]
        f.seek(hdrsize + 32)
        fileset_count = struct.unpack("<I", f.read(4))[0]
        pos = struct.unpack("<q", f.read(8))[0]
        entries, seen = [], 0
        while pos != -1 and seen < fileset_count:
            f.seek(pos)
            count = struct.unpack("<I", f.read(4))[0]
            f.read(4)                                    # const 2
            off_tbl = struct.unpack("<q", f.read(8))[0]
            nxt = struct.unpack("<q", f.read(8))[0]      # next fileset (-1 = last)
            f.read(8)                                    # 2x int32 index bookkeeping
            info_tbl = struct.unpack("<q", f.read(8))[0]
            f.seek(off_tbl); ob = f.read(count * 20)
            exts = [0] * count; names = [""] * count
            if want_names:
                f.seek(info_tbl); ib = f.read(count * 192)
                for r in range(count):
                    b = r * 192
                    exts[r] = struct.unpack_from("<I", ib, b + 16)[0]
                    nm = ib[b + 44:b + 44 + 128]
                    z = nm.find(b"\0")
                    names[r] = nm[:z if z >= 0 else 128].decode("latin-1", "replace")
            for r in range(count):
                entries.append((struct.unpack_from("<Q", ob, r * 20 + 8)[0], exts[r], names[r]))
            seen += 1; pos = nxt
    return version, fileset_count, entries


def summary(path):
    v, fc, entries = parse_forge_index(path)
    ids = [e[0] for e in entries]
    dup = len(ids) - len(set(ids))
    hist = {}
    for _, ext, _ in entries:
        t = type_name(ext); hist[t] = hist.get(t, 0) + 1
    L = ["=" * 66, f"FORGE: {path.split(chr(92))[-1].split('/')[-1]}",
         f"  version={v}  filesets={fc}  entries={len(ids)}  duplicate IDs={dup}",
         "  resource types (by count):"]
    for t, c in sorted(hist.items(), key=lambda kv: -kv[1])[:25]:
        L.append(f"    {t:28} {c}")
    if len(hist) > 25:
        L.append(f"    ... and {len(hist)-25} more types")
    return "\n".join(L) + "\n"


def diff(path_a, path_b):
    _, _, ea = parse_forge_index(path_a)
    _, _, eb = parse_forge_index(path_b)
    a = {i: n for i, _, n in ea}
    b = {i: n for i, _, n in eb}
    shared = set(a) & set(b)
    shared_real = {i for i in shared if i not in (16, 145)}  # ignore reserved sidecars
    same = sum(1 for i in shared_real if a[i] == b[i])
    diffn = len(shared_real) - same
    L = ["=" * 66, "FORGE DIFF (by real file ID)",
         f"  A = {path_a.split('/')[-1]}  ({len(a)} entries)",
         f"  B = {path_b.split('/')[-1]}  ({len(b)} entries)",
         "",
         f"  shared IDs (excluding reserved sidecars 16/145): {len(shared_real)}",
         f"    - same name  (A replaces/updates the same resource): {same}",
         f"    - diff name  (same ID reused for different content): {diffn}",
         f"  unique to A: {len(set(a)-set(b))}    unique to B: {len(set(b)-set(a))}",
         ""]
    if shared_real:
        L.append("  >> If A and B are two mods, these shared IDs are CONFLICTS")
        L.append("     (only one can win). If B is a patch of A, they are overrides.")
        L.append("  sample shared IDs:")
        for i in list(shared_real)[:12]:
            tag = "same" if a[i] == b[i] else "DIFF"
            L.append(f"    {tag} id={i}: {a[i][:34]!r} | {b[i][:34]!r}")
    else:
        L.append("  No shared content IDs - these forges don't conflict.")
    return "\n".join(L) + "\n"


def to_csv(path, csv_path):
    _, _, entries = parse_forge_index(path)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write("id,type,name\n")
        for i, ext, n in entries:
            f.write(f'{i},{type_name(ext)},"{n}"\n')
    return f"wrote {len(entries)} rows to {csv_path}"


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    csv_path = None
    if "--csv" in argv:
        k = argv.index("--csv"); csv_path = argv[k + 1]; del argv[k:k + 2]
    args = argv[1:]
    if len(args) == 1:
        print(summary(args[0]))
        if csv_path:
            print(to_csv(args[0], csv_path))
    elif len(args) >= 2:
        print(diff(args[0], args[1]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
