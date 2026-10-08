#!/usr/bin/env python3
"""
data_inspect.py - list the typed resources inside a GRB (or Ghost Recon Wildlands)
`.data` container.

A `.data` (one forge entry, unpacked to `<id>_-_<name>.data`) is a compressed
container of one-or-more typed resources. This tool decodes the container format
and prints, for each resource: its name, 64-bit ClassID, and its resource TYPE
(e.g. Mesh, TextureMap, BuildTable, Cloth) - resolved from the type id.

    python data_inspect.py  some.data  [more.data ...]  [--all]

ATK cannot unpack Wildlands, so a container can also be read straight out of a
forge, by entry name or decimal ID (read-only on the forge):

    python data_inspect.py --forge DataPC.forge Cloth_UNP_ElYayo_Poncho 372745115222
    python data_inspect.py --forge DataPC.forge Cloth_UNP_ElYayo_Poncho --extract out_dir

`--extract` also copies each matched entry's container bytes, unchanged, to
`out_dir/<name>.data`, so the other tools have a file to read.

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
- Ghost Recon Wildlands (added 2026-10-08) writes CompressedFileData VERSION 1:
  the block-info pairs are uint16, not int32, and the algorithm is LZO - 1
  (LZO1X-999) in its base and patch forges, 0 (LZO1X) in its DLC forges. The
  game ships no decoder, so this tool borrows ATK's own `Libs/lzo.dll` (found
  like atk_bridge.find_atk: $GRB_ATK, then a search; or pass --lzo). The files
  block after decompression is framed exactly like GRB's below.
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
import sys, os, re, struct, zlib, ctypes, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:          # siblings (forge_inspect, atk_bridge) even under `python -I`
    sys.path.insert(0, _HERE)

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
    "LiteRagdoll",          # the cloth's collision body, third resource of a cloth container
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


# CompressionInfo's algorithm byte (ATK v1.3.1 Manager.GetCompressionAlgorithm).
# GRB writes 3; Wildlands writes 1 in base/patch forges and 0 in DLC forges.
ALGORITHMS = {0: "LZO1X", 1: "LZO1X-999", 2: "LZO2A",
              3: "Oodle Mermaid", 4: "Oodle Mermaid Optimal3"}
LZO_ALGOS = (0, 1, 2)


class Lzo:
    """LZO decoder for Wildlands containers, from ATK's native `Libs/lzo.dll`.

    LZO1X and LZO1X-999 differ only on the compressing side; both decode with
    lzo1x_decompress_safe. LZO2A has its own decoder. The `_safe` variants
    bounds-check the output, so a wrong guess fails instead of overrunning."""

    _FUNCS = {0: "lzo1x_decompress_safe", 1: "lzo1x_decompress_safe",
              2: "lzo2a_decompress_safe"}

    def __init__(self, dll):
        self.ok, self.fns = False, {}
        if not dll:
            return
        try:
            lib = ctypes.CDLL(dll)
            for algo, name in self._FUNCS.items():
                f = getattr(lib, name)
                f.restype = ctypes.c_int
                f.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p,
                              ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
                self.fns[algo] = f
            self.ok = True
        except Exception as e:
            self.err = str(e)

    def decompress(self, algo, src, rawlen):
        out = ctypes.create_string_buffer(rawlen)
        n = ctypes.c_size_t(rawlen)
        rc = self.fns[algo](src, len(src), out, ctypes.byref(n), None)
        if rc != 0 or n.value != rawlen:
            raise RuntimeError(f"LZO returned {rc} with {n.value} bytes, expected {rawlen}")
        return out.raw[:rawlen]


def find_lzo(override=None):
    """ATK's lzo.dll: an explicit path, else <ATK install>/Libs/lzo.dll."""
    if override:
        return override if os.path.isfile(override) else None
    try:
        import atk_bridge          # local import: atk_bridge imports this module
        cand = os.path.join(atk_bridge.find_atk(), "Libs", "lzo.dll")
    except (ImportError, EnvironmentError):
        return None
    return cand if os.path.isfile(cand) else None


_lzo = {}


def default_lzo():
    """The process-wide LZO decoder, located on first use. Only Wildlands
    containers need it, so a GRB-only run never goes looking for ATK."""
    if "dec" not in _lzo:
        _lzo["dec"] = Lzo(find_lzo())
    return _lzo["dec"]


def read_cfd(b, off, oodle, lzo=None):
    """Read one CompressedFileData at off. Returns (data, next_off, info).

    `oodle` decodes GRB blocks; `lzo` decodes Wildlands blocks and defaults to
    ATK's lzo.dll, found on first need."""
    magic, = struct.unpack_from("<Q", b, off); off += 8
    ver, = struct.unpack_from("<h", b, off); off += 2
    algo = b[off]; off += 1
    off += 4  # two uint16 block-size fields
    nblocks, = struct.unpack_from("<i", b, off); off += 4
    # version 1 (Wildlands) stores each block's sizes as uint16, version 3 (GRB) as int32
    fmt = "<HH" if ver == 1 else "<ii"
    width = struct.calcsize(fmt)
    infos = [struct.unpack_from(fmt, b, off + width * k) for k in range(nblocks)]
    off += width * nblocks
    out = bytearray()
    for un, cn in infos:
        off += 4  # adler32
        blk = b[off:off + cn]; off += cn
        if un == cn:
            out += blk
        elif algo in LZO_ALGOS:
            dec = lzo or default_lzo()
            if not dec.ok:
                raise RuntimeError("LZO-compressed block (Wildlands) but no lzo.dll found "
                                   "(pass --lzo <ATK>/Libs/lzo.dll, or set GRB_ATK)")
            out += dec.decompress(algo, blk, un)
        elif oodle and oodle.ok:
            out += oodle.decompress(blk, un)
        else:
            raise RuntimeError("compressed block but no Oodle DLL available "
                               "(pass --oodle path\\to\\oo2core_7_win64.dll)")
    info = dict(magic_ok=(magic == MAGIC), version=ver, algo=algo, blocks=nblocks)
    return bytes(out), off, info


def read_container(path, oodle, lzo=None):
    """Decompress a .data. Returns (metadata block, files block)."""
    return read_container_bytes(open(path, "rb").read(), oodle, lzo)


def read_container_bytes(b, oodle, lzo=None):
    """Decompress a .data already in memory. Returns (metadata block, files block).

    Same two chained compressed-file-descriptors as `read_container`; separate so
    a caller holding a container it read straight out of a forge - never unpacked
    to disk - can use it. `rig_census.py` reaches meshes in the 23 GB resources
    forge this way."""
    meta, off, _ = read_cfd(b, 0, oodle, lzo)
    files, _, _ = read_cfd(b, off, oodle, lzo)
    return meta, files


def forge_lookup(forge_path, wanted):
    """Yield (id, name, container bytes) for forge entries whose name or decimal
    ID is in `wanted`. Read-only: seeks to each matched entry and reads it."""
    import forge_inspect                # local import keeps a plain .data run light
    keys = set(wanted)
    with open(forge_path, "rb") as f:
        for fid, _ext, name, offset, length in forge_inspect.forge_entries(forge_path):
            if name in keys or str(fid) in keys:
                f.seek(offset)
                yield fid, name, f.read(length)


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
    return inspect_bytes(f"FILE: {os.path.basename(path)}", b, oodle, show_all, limit)


def inspect_bytes(label, b, oodle, show_all=False, limit=40):
    lines = ["=" * 70, f"{label}   ({len(b):,} bytes)"]
    try:
        meta, off, ia = read_cfd(b, 0, oodle)
        files, off, ib = read_cfd(b, off, oodle)
    except Exception as e:
        lines.append(f"  Could not parse container: {e}")
        return "\n".join(lines) + "\n"
    algo = ALGORITHMS.get(ia["algo"], "unknown")
    lines.append(f"  container: version={ia['version']} algorithm={ia['algo']} "
                 f"({algo}) metaBlocks={ia['blocks']} fileBlocks={ib['blocks']}")
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
    def opt(flag):
        if flag not in argv:
            return None
        i = argv.index(flag); v = argv[i + 1]; del argv[i:i + 2]
        return v

    override, forge, extract, lzo_dll = opt("--oodle"), opt("--forge"), opt("--extract"), opt("--lzo")
    if lzo_dll:
        _lzo["dec"] = Lzo(find_lzo(lzo_dll))
    show_all = "--all" in argv
    args = [a for a in argv[1:] if a != "--all"]
    if not args:
        print(__doc__); return
    # A missing Oodle only matters for GRB's compressed blocks, and read_cfd
    # says so when it meets one; Wildlands needs no Oodle at all.
    oodle = Oodle(find_oodle(forge or args[0], override))
    if not forge:
        for p in args:
            print(inspect(p, oodle, show_all=show_all))
        return
    if extract:
        os.makedirs(extract, exist_ok=True)
    found = set()
    for fid, name, b in forge_lookup(forge, args):
        found.update((name, str(fid)))
        print(inspect_bytes(f"ENTRY: {name}  id={fid}  [{os.path.basename(forge)}]",
                            b, oodle, show_all=show_all))
        if extract:
            safe = re.sub(r'[<>:"/\\|?*]', "_", name) or str(fid)
            out = os.path.join(extract, f"{safe}.data")
            with open(out, "wb") as f:
                f.write(b)
            print(f"  extracted -> {out}\n")
    missing = [a for a in args if a not in found]
    if missing:
        print(f"not in {os.path.basename(forge)}: {', '.join(missing)}")


if __name__ == "__main__":
    main(sys.argv)
