#!/usr/bin/env python3
"""
data_inspect.py - list the typed resources inside a GRB `.data` container.

A `.data` (one forge entry, unpacked to `<id>_-_<name>.data`) is a compressed
container of one-or-more typed resources. This tool decodes the container format
and prints, for each resource: its name, 64-bit ClassID, and its resource TYPE
(e.g. Mesh, TextureMap, BuildTable, Cloth) - resolved from the type id.

    python data_inspect.py  some.data  [more.data ...]

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
- Each resource record: uint32 TypeId, int32 len, len-prefixed Name, payload.
  TypeId == CRC32(typeName); we reverse it via the KNOWN_TYPES list below.
"""
import sys, os, struct, zlib, ctypes

MAGIC = 1154322941026740787  # CompressedFileData magic (0x1004FA9957FBAA33)

# Known Anvil/GRB resource type NAMES -> id is CRC32(name). Extend freely.
KNOWN_TYPE_NAMES = [
    "Mesh", "HairMesh", "CompiledMesh", "MeshData", "MeshPrimitive", "SubMesh",
    "Skeleton", "Bone", "LODSelector", "LODDescriptor", "FacialSolverData",
    "TextureMap", "CompiledMip", "CompiledTextureMap", "TextureSet", "Material",
    "BuildTable", "EntityBuilder", "EntityGroupBuilder", "LocalizationPackage",
    "Animation", "Event",
    # cloth / soft-body physics
    "Cloth", "SoftBody", "MotionSoftBody", "ClothLOD", "MotionClothLOD",
    "SoftBodyLOD", "MotionSoftBodyLOD", "ClothState", "MotionClothState",
    "SoftBodyState", "MotionSoftBodyState", "ClothSettings", "SoftBodySettings",
    "ClothActionSettings", "SoftBodyConstraint", "SoftBodyVertexMapping",
]
TYPE_BY_ID = {zlib.crc32(n.encode("ascii")): n for n in KNOWN_TYPE_NAMES}


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


def type_name(tid):
    return TYPE_BY_ID.get(tid, f"#{tid}")


def inspect(path, oodle):
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
    o, n = 0, 0
    res = []
    while o < len(files) - 12:
        try:
            tid, = struct.unpack_from("<I", files, o); o += 4
            length, = struct.unpack_from("<i", files, o); o += 4
            slen, = struct.unpack_from("<i", files, o); o += 4
            name = files[o:o + slen].decode("latin-1", "replace"); o += slen
            payload = files[o:o + length]; o += length
            if length <= 0 or slen < 0:
                break
            h0 = payload[0] if payload else 0
            hlen = 1 if h0 != 1 else (12 * struct.unpack_from("<i", payload, 4)[0] + 8)
            cid = struct.unpack_from("<Q", payload, hlen)[0]
        except Exception:
            break
        res.append((name, tid, cid, length))
        n += 1
    lines.append(f"  typed resources: {n}")
    for name, tid, cid, length in res:
        lines.append(f"    - {name}")
        lines.append(f"        type={type_name(tid)}  (id {tid})  ClassID={cid}  {length:,} B")
    return "\n".join(lines) + "\n"


def main(argv):
    try:  # resource names can contain bytes the console codec can't encode
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    override = None
    if "--oodle" in argv:
        i = argv.index("--oodle"); override = argv[i + 1]; del argv[i:i + 2]
    paths = argv[1:]
    if not paths:
        print(__doc__); return
    oodle = Oodle(find_oodle(paths[0], override))
    if not oodle.ok:
        print("(note: no Oodle DLL loaded - only raw/uncompressed blocks will read)\n")
    for p in paths:
        print(inspect(p, oodle))


if __name__ == "__main__":
    main(sys.argv)
