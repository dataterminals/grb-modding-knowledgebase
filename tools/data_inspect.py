#!/usr/bin/env python3
"""
data_inspect.py - list the typed resources inside a GRB `.data` container.

A `.data` (one forge entry, unpacked to `<id>_-_<name>.data`) is a compressed
container of one-or-more typed resources. This tool decodes the container format
and prints, for each resource: its name, 64-bit ClassID, and its resource TYPE
(e.g. Mesh, TextureMap, BuildTable, Cloth) - resolved from the type id.

    python data_inspect.py  some.data  [more.data ...]  [--all]

Containers with more than 40 resources print a per-type count and the first 40;
`--all` lists every one. Other tools import `walk()` from here, so the container
format lives in exactly one place.

Background: docs/02-forge-file-format.md (container + compression),
docs/03-data-and-resources.md, reference/resource-type-ids.md.

HOW IT WORKS (verified from decompiled ATK v1.3.1, and against real files):
- A GRB `.data` = two `CompressedFileData` blocks: [metadata/index][file payloads].
- Each CompressedFileData: uint64 magic, 7-byte CompressionInfo (int16 ver,
  byte algo, uint16, uint16), int32 blockCount, blockCount*(int32 uncomp,
  int32 comp) block-info, then blocks of [uint32 adler32][comp bytes].
  A block with uncomp==comp is stored raw; else it's compressed.
- GRB uses algorithm 3 = Oodle Mermaid (SuperFast), 32 KB blocks. To read
  compressed blocks this tool loads the game's `oo2core_7_win64.dll` (Windows).
  Point --oodle at it, or it auto-searches up from the .data path and common
  spots. If a block is raw, no DLL is needed.
- The decompressed files block is a flat stream of resources, each framed

      uint32 TypeId | int32 len | int32 nameLen | name | FileHeader | payload

  TypeId == CRC32(typeName); we reverse it via the KNOWN_TYPES list below.
  The FileHeader sits BETWEEN the name and the payload and NEITHER length counts
  it: one 0x00 byte normally, or 12 * int32@+4 + 8 bytes when its first byte is
  0x01. The `len` bytes of payload that follow begin with the resource's own
  uint64 ClassID. Names can be empty (nameLen == 0).

CORRECTED 2026-09-16: until then this tool read `len` bytes starting AT the
FileHeader, one byte early. A container's first resource still read plausibly
and every later one was garbage, so a multi-resource container looked like one
resource plus a blob of noise. Measured with the fix, TEAMMATE_Template holds
2,451 resources, not 2, and the gameplay DBContainer 61,426, not 1 (see
meta/research-log.md). `walk()` now reports where it stopped - a complete walk
ends exactly on the last byte of the block - so a partial read cannot pass as
the whole container again.
"""
import sys, os, struct, zlib, ctypes, collections

MAGIC = 1154322941026740787  # CompressedFileData magic (0x1004FA9957FBAA33)

# Known Anvil/GRB resource type NAMES -> id is CRC32(name). Extend freely.
KNOWN_TYPE_NAMES = [
    "Mesh", "HairMesh", "CompiledMesh", "MeshData", "MeshPrimitive", "SubMesh",
    "Skeleton", "Bone", "LODSelector", "LODDescriptor", "FacialSolverData",
    "TextureMap", "CompiledMip", "CompiledTextureMap", "TextureSet", "Material",
    "BuildTable", "EntityBuilder", "EntityGroupBuilder", "LocalizationPackage",
    "Animation", "Event", "Entity", "GraphicObject",
    # cloth / soft-body physics
    "Cloth", "SoftBody", "MotionSoftBody", "ClothLOD", "MotionClothLOD",
    "SoftBodyLOD", "MotionSoftBodyLOD", "ClothState", "MotionClothState",
    "SoftBodyState", "MotionSoftBodyState", "ClothSettings", "SoftBodySettings",
    "ClothActionSettings", "SoftBodyConstraint", "SoftBodyVertexMapping",
]
TYPE_BY_ID = {zlib.crc32(n.encode("ascii")): n for n in KNOWN_TYPE_NAMES}

# One resource from a container's files block.
#   offset  - where its record starts in the decompressed files block
#   header  - the FileHeader bytes: b"\x00", or the 12*n+8 extended form
#   payload - the `len` bytes after the header; starts with its own ClassID
Resource = collections.namedtuple("Resource", "offset type_id name header payload")


def find_oodle(start, override=None):
    if override and os.path.isfile(override):
        return override
    d = os.path.dirname(os.path.abspath(start))
    for _ in range(8):  # walk up looking for the game dir
        cand = os.path.join(d, "oo2core_7_win64.dll")
        if os.path.isfile(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


class Oodle:
    def __init__(self, dll):
        self.ok = False
        if not dll:
            return
        try:
            oo = ctypes.WinDLL(dll)
            f = oo.OodleLZ_Decompress
            f.restype = ctypes.c_longlong
            f.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p,
                          ctypes.c_longlong, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                          ctypes.c_void_p, ctypes.c_longlong, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong, ctypes.c_int]
            self.f, self.ok = f, True
        except Exception as e:
            self.err = str(e)

    def decompress(self, src, rawlen):
        out = ctypes.create_string_buffer(rawlen)
        n = self.f(src, len(src), out, rawlen, 1, 0, 0, None, 0, None, None, None, 0, 3)
        if n != rawlen:
            raise RuntimeError(f"Oodle returned {n}, expected {rawlen}")
        return out.raw[:rawlen]


def read_cfd(b, off, oodle):
    """Read one CompressedFileData at off. Returns (data, next_off, info)."""
    magic, = struct.unpack_from("<Q", b, off); off += 8
    ver, = struct.unpack_from("<h", b, off); off += 2
    algo = b[off]; off += 1
    off += 4  # two uint16 block-size fields
    nblocks, = struct.unpack_from("<i", b, off); off += 4
    infos = []
    for _ in range(nblocks):
        un, = struct.unpack_from("<i", b, off); off += 4
        cn, = struct.unpack_from("<i", b, off); off += 4
        infos.append((un, cn))
    out = bytearray()
    for un, cn in infos:
        off += 4  # adler32
        blk = b[off:off + cn]; off += cn
        if un == cn:
            out += blk
        elif oodle and oodle.ok:
            out += oodle.decompress(blk, un)
        else:
            raise RuntimeError("compressed block but no Oodle DLL available "
                               "(pass --oodle path\\to\\oo2core_7_win64.dll)")
    info = dict(magic_ok=(magic == MAGIC), version=ver, algo=algo, blocks=nblocks)
    return bytes(out), off, info


def read_container(path, oodle):
    """Decompress a .data. Returns (metadata block, files block)."""
    return read_container_bytes(open(path, "rb").read(), oodle)


def read_container_bytes(b, oodle):
    """Decompress a .data already in memory. Returns (metadata block, files block).

    Same two chained compressed-file-descriptors as `read_container`; separate so
    a caller holding a container it read straight out of a forge - never unpacked
    to disk - can use it. `rig_census.py` reaches meshes in the 23 GB resources
    forge this way."""
    meta, off, _ = read_cfd(b, 0, oodle)
    files, _, _ = read_cfd(b, off, oodle)
    return meta, files


def header_len(files, h):
    """Length of the FileHeader that starts at `h`.

    One byte, unless that byte is 0x01: then 12 * int32@+4 + 8 bytes. In the
    ~72,000 resources checked on 2026-09-16 the long form occurs 17 times, all in
    the gameplay DBContainer (`Animation` resources such as RamonPC_RTA_opening),
    and ATK's own unpack writes it in front of the payload verbatim."""
    if files[h] != 1:
        return 1
    count, = struct.unpack_from("<i", files, h + 4)
    return 12 * count + 8


def walk(files):
    """Every resource in a decompressed files block, and where the walk stopped.

    Returns (resources, end). A complete walk has end == len(files). Anything
    else means a frame this reader does not understand, and the caller must say
    so rather than present a partial list as the container."""
    out, o = [], 0
    while o + 12 <= len(files):
        tid, length, slen = struct.unpack_from("<Iii", files, o)
        h = o + 12 + slen
        if slen < 0 or length < 0 or h >= len(files):
            break
        try:
            end = h + header_len(files, h) + length
        except struct.error:
            break
        if end > len(files) or end <= h:
            break
        hl = end - length - h
        out.append(Resource(o, tid, files[o + 12:h].decode("latin-1", "replace"),
                            files[h:h + hl], files[h + hl:end]))
        o = end
    return out, o


def class_id(res):
    """The resource's own 64-bit ClassID - the first 8 bytes of its payload."""
    return struct.unpack_from("<Q", res.payload, 0)[0] if len(res.payload) >= 8 else None


def type_name(tid):
    return TYPE_BY_ID.get(tid, f"#{tid}")


def inspect(path, oodle, show_all=False, limit=40):
    b = open(path, "rb").read()
    lines = ["=" * 70, f"FILE: {os.path.basename(path)}   ({len(b):,} bytes)"]
    try:
        meta, off, ia = read_cfd(b, 0, oodle)
        files, off, ib = read_cfd(b, off, oodle)
    except Exception as e:
        lines.append(f"  Could not parse container: {e}")
        return "\n".join(lines) + "\n"
    lines.append(f"  container: version={ia['version']} algorithm={ia['algo']} "
                 f"(3=Oodle Mermaid) metaBlocks={ia['blocks']} fileBlocks={ib['blocks']}")
    res, end = walk(files)
    lines.append(f"  typed resources: {len(res):,}")
    if end != len(files):
        lines.append(f"  !! walk stopped at byte {end:,} of {len(files):,} - "
                     f"this list is INCOMPLETE")
    shown = res
    if len(res) > limit and not show_all:
        counts = collections.Counter(type_name(r.type_id) for r in res)
        top = ", ".join(f"{k} x{v:,}" for k, v in counts.most_common(15))
        more = len(counts) - 15
        lines.append(f"  by type: {top}" + (f", ... {more} more types" if more > 0 else ""))
        lines.append(f"  first {limit} of {len(res):,} (--all lists every one):")
        shown = res[:limit]
    for r in shown:
        long_header = f"  (+{len(r.header)} B header)" if len(r.header) != 1 else ""
        lines.append(f"    - {r.name or '<unnamed>'}")
        lines.append(f"        type={type_name(r.type_id)}  (id {r.type_id})  "
                     f"ClassID={class_id(r)}  {len(r.payload):,} B{long_header}")
    return "\n".join(lines) + "\n"


def main(argv):
    try:  # resource names can contain bytes the console codec can't encode
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    override = None
    if "--oodle" in argv:
        i = argv.index("--oodle"); override = argv[i + 1]; del argv[i:i + 2]
    show_all = "--all" in argv
    paths = [a for a in argv[1:] if a != "--all"]
    if not paths:
        print(__doc__); return
    oodle = Oodle(find_oodle(paths[0], override))
    if not oodle.ok:
        print("(note: no Oodle DLL loaded - only raw/uncompressed blocks will read)\n")
    for p in paths:
        print(inspect(p, oodle, show_all=show_all))


if __name__ == "__main__":
    main(sys.argv)
