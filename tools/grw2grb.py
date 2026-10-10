#!/usr/bin/env python3
"""
grw2grb.py - convert Ghost Recon Wildlands assets into Ghost Recon Breakpoint's formats.

The two games share one engine branch and one asset database: 6,202 entry IDs are the
same in both installs, so the same asset exists in both serializations. Every rule in
this file was derived from those pairs and is checked the same way: convert the
Wildlands copy and compare it with GRB's own bytes. `selftest` re-runs that check.

    python grw2grb.py selftest                       # validate against both installs
    python grw2grb.py mesh    <GRW entry name|id> -o out_dir [--material ID] [--drop-uv1]
    python grw2grb.py texture <GRW entry name|id> -o out_dir [--with-mips]

`mesh` and `texture` look the entry up across the whole Wildlands install and write a
GRB container (`1_-_<name>.data`), ready to drop into an ATK unpack folder. READ-ONLY
on both installs. Install paths: --grw / --grb, or $GRW_INSTALL / $GRB_INSTALL, or the
SylDesk defaults below. Standard library only (+ the game's Oodle DLL, ATK's lzo.dll).

WHAT CONVERTS (2026-10-10, see meta/research-log.md):
  Mesh        mechanical. 153 of the 1,315 shared meshes come out byte-identical to
              GRB's; every other difference is content Ubisoft re-baked (vertex data,
              extents, UserCategory). Rules in `convert_mesh`.
  TextureMap  mechanical. 219 of 1,378 shared textures byte-identical, 169 more differ
              only in UserCategory; the rest are re-encoded pixels. Rules in
              `convert_texture`.
  CompiledMip byte-identical in both games: copy the payload.
  TextureSet  same format: copy (a reference-kind byte differs per asset, not per game).
  Material    NOT converted field by field. GRB re-templated Wildlands materials (Ubisoft's
              own remap: SHD_Basic -> SHD_BAS_Dielectric*, ...), keeping the same texture
              IDs. `transplant_material` clones a real GRB material on the target template
              and points its texture slots at the Wildlands textures.

Vertex note: in static meshes the position is xyz * w / 32767, where |w| is the mesh's
QuantizationFactor and the sign of w flips per vertex together with xyz (it doubles as the
bitangent sign). Copying vertex bytes is therefore exact; decoding with |w| mirrors them.
"""
import sys, os, re, glob, struct, zlib, ctypes, collections
from ctypes import wintypes

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import data_inspect as di                                              # noqa: E402
import forge_inspect as fi                                             # noqa: E402
from reflex3_write import _compress_cfd                                # noqa: E402

GRW_DEFAULT = r"D:\SteamLibrary\steamapps\common\Wildlands"
GRB_DEFAULT = r"H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"

def _crc(s):
    return zlib.crc32(s.encode("ascii"))

T_MESH, T_TEXTUREMAP, T_COMPILEDMIP = _crc("Mesh"), _crc("TextureMap"), _crc("CompiledMip")
T_TEXTURESET, T_MATERIAL = _crc("TextureSet"), _crc("Material")
H_COMPILED, H_CLUSTERED, H_MESHDATA = _crc("CompiledMesh"), _crc("ClusteredMeshData"), _crc("MeshData")
H_PRIMITIVE, H_INSTANCING = _crc("MeshPrimitive"), _crc("MeshInstancingData")
H_DYNREF = 0x9F1640AF                  # the DynamicReference objects of a Mesh's material list
H_CTM = 0x13237FE9                     # the CompiledTextureMap object inside a TextureMap


# --------------------------------------------------------------------------- memory cap

def memory_cap(mb):
    """Cap this process's memory (Windows Job Object): past `mb`, allocations raise
    MemoryError instead of swapping the machine. Added 2026-10-10 after a throwaway
    analysis script took ~11 GB."""
    if os.name != "nt":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class Basic(ctypes.Structure):
        _fields_ = [("a", ctypes.c_longlong), ("b", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
                    ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("e", wintypes.DWORD),
                    ("f", ctypes.c_size_t), ("g", wintypes.DWORD), ("h", wintypes.DWORD)]

    class Ext(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("IoInfo", ctypes.c_ulonglong * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcess", ctypes.c_size_t), ("PeakJob", ctypes.c_size_t)]

    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    info = Ext(); info.Basic.LimitFlags = 0x100; info.ProcessMemoryLimit = mb << 20
    k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(k32.GetCurrentProcess()))
    memory_cap._job = job


# --------------------------------------------------------------------------- installs

def install_index(root):
    """{entry id: (forge path, ext, name, offset, length)} over a whole install.
    Base forges before their patches, so patches win; DLC subfolders included."""
    paths = glob.glob(os.path.join(root, "*.forge")) + glob.glob(os.path.join(root, "dlc_*", "*.forge"))
    idx = {}
    for p in sorted(paths, key=lambda q: ("_patch_" in q, q)):
        for fid, ext, name, off, ln in fi.forge_entries(p):
            if ext:
                idx[fid] = (p, ext, name, off, ln)
    return idx


class Install:
    def __init__(self, root, oodle):
        self.root, self.oodle, self._idx = root, oodle, None

    @property
    def index(self):
        if self._idx is None:
            self._idx = install_index(self.root)
        return self._idx

    def find(self, key):
        if key.isdigit() and int(key) in self.index:
            return int(key)
        hits = [i for i, v in self.index.items() if v[2] == key]
        if not hits:
            raise SystemExit(f"no entry named {key!r} in {self.root}")
        return hits[0]

    def resources(self, fid):
        """(metadata block, files block, [Resource]) of one entry's container."""
        p, _ext, _name, off, ln = self.index[fid]
        with open(p, "rb") as f:
            f.seek(off); b = f.read(ln)
        meta, files = di.read_container_bytes(b, self.oodle)
        res, end = di.walk(files)
        if end != len(files):
            raise ValueError(f"incomplete container walk for entry {fid}")
        return meta, files, res


# --------------------------------------------------------------------------- containers

def frame(files, r, payload=None):
    """The resource's frame bytes (type, len, name, FileHeader, payload), optionally with a
    new payload. `files` is the decompressed files block `r` came from."""
    slen = struct.unpack_from("<i", files, r.offset + 8)[0]
    name = files[r.offset + 12:r.offset + 12 + slen]
    p = r.payload if payload is None else payload
    return struct.pack("<Iii", r.type_id, len(p), slen) + name + r.header + p


def build_container(frames, oodle_dll, oodle):
    """[(classid, frame bytes)] -> a GRB container: metadata rows {ClassID, frame size, 0},
    files block, both Oodle-compressed by reflex3_write's writer (the 32768/32768 header
    proven in game 2026-10-09). Read back before it is returned."""
    meta = struct.pack("<H", len(frames)) + b"".join(struct.pack("<QiH", c, len(fb), 0) for c, fb in frames)
    files = b"".join(fb for _, fb in frames)
    out = _compress_cfd(meta, oodle_dll) + _compress_cfd(files, oodle_dll)
    m2, f2 = di.read_container_bytes(out, oodle)
    if m2 != meta or f2 != files:
        raise RuntimeError("container round trip failed")
    return out


# --------------------------------------------------------------------------- meshes

class _R:
    def __init__(self, b, o):
        self.b, self.o = b, o

    def take(self, fmt):
        v = struct.unpack_from("<" + fmt, self.b, self.o)
        self.o += struct.calcsize("<" + fmt)
        return v[0] if len(v) == 1 else v

    def obj(self, h):
        a, z, t = struct.unpack_from("<III", self.b, self.o)
        if a & 0xFF000000 != 0xF8000000 or z or t != h:
            raise ValueError(f"expected object {h:#x} at {self.o}")
        self.o += 12

    def skip_blob(self):
        n = self.take("i"); self.o += n

    def skip_array(self, width):
        n = self.take("i"); self.o += width * n


def _find_object(b, h):
    pat = struct.pack("<I", h); k = b.find(pat)
    while k >= 0:
        if k >= 8 and b[k - 5] == 0xF8 and b[k - 4:k] == bytes(4):
            return k - 8
        k = b.find(pat, k + 1)
    raise ValueError(f"object {h:#x} not found")


# Wildlands vertex format -> GRB vertex format, where the layout is byte-identical
# (shared meshes: 0->0 32 B, 2->4 44 B, 6->10 24 B, 8->12 20 B, 9->13 24 B; 1->2 40 B inferred).
# NOT 7: GRW 7 is pos|nrm|tan|col|uv|uv (28 B), GRB 11 is pos|nrm|col|col|uv|uv. Use drop_uv1.
FORMAT_MAP = {0: 0, 1: 2, 2: 4, 6: 10, 8: 12, 9: 13}
INST_BODY = 1 + 2 + 2 + 2 + 2 + 1 + 8 + 256


def _drop_uv1(p):
    """GRW format 7 (28 B) -> GRW format 6 (24 B) by dropping each vertex's second UV set:
    stride fields, per-draw-prim descriptors and vertex offsets (4-byte units) follow."""
    r = _R(p, _find_object(p, H_COMPILED)); r.obj(H_COMPILED); r.skip_blob()
    if r.take("B") == 3:
        raise ValueError("no ClusteredMeshData")
    r.obj(H_CLUSTERED); r.take("i")
    fmt_off = r.o; fmt = r.take("B"); stride_off = r.o; stride = r.take("i")
    if (fmt, stride) != (7, 28):
        raise ValueError(f"drop_uv1 needs format 7 / 28 B, got {fmt} / {stride}")
    r.take("i"); r.take("3f"); r.take("3f"); r.take("i")
    r.skip_array(4)
    nv = r.take("i"); vop = r.o; r.o += 4 * nv
    r.take("B")
    out = bytearray(p[:r.o])
    out[fmt_off] = 6
    struct.pack_into("<i", out, stride_off, 24)
    for j in range(nv):
        v = struct.unpack_from("<i", out, vop + 4 * j)[0]
        struct.pack_into("<i", out, vop + 4 * j, v // 7 * 6)
    n = r.take("i"); vb = p[r.o:r.o + n]; r.o += n
    new_vb = b"".join(vb[i:i + 24] for i in range(0, n, 28))
    out += struct.pack("<i", len(new_vb)) + new_vb
    n = r.take("i"); out += struct.pack("<i", n) + p[r.o:r.o + n]; r.o += n
    n = r.take("i"); pd = bytearray(p[r.o:r.o + n]); r.o += n
    for j in range(0, n, 36):                                  # center, half, stride, count, start
        struct.pack_into("<I", pd, j + 24, 24)
    out += struct.pack("<i", n) + pd
    md = bytearray(p[r.o:])
    m = _R(bytes(md), 0); m.obj(H_MESHDATA); m.take("B")
    if md[m.o] == 7:
        md[m.o] = 6; md[m.o + 1] = 24
    return bytes(out + md)


def convert_mesh(p, material_map=None, default_material=None, drop_uv1=False):
    """Wildlands Mesh payload -> GRB Mesh payload.
      wrapper    drop the GRW-only u32 at payload offset 13
      formats    renumber the vertex format (FORMAT_MAP); vertex and index bytes unchanged
      Clustered  GRB inserts u32 = byte size of the three length-prefixed blobs that follow
      MeshData   GRB inserts u32 = byte size of the two length-prefixed blobs that follow
      tail       GRW 8 bools | 2 GRW-only bools | i32 DecalType | 3 bools | 2 x i32 | i32 UserCategory
                 GRB 8 bools | i32 DecalType | 3 bools | 3 x i32 | u8 | i32 UserCategory
      materials  optional {GRW id: GRB id} remap, or one default for every submesh"""
    if drop_uv1:
        p = _drop_uv1(p)
    mm = material_map or {}
    remap = lambda m: mm.get(m, default_material if default_material is not None else m)
    start = _find_object(p, H_COMPILED)
    out = bytearray(p[:13] + p[17:start])
    r = _R(p, start); r.obj(H_COMPILED); r.skip_blob()
    flag = r.take("B")
    out += p[start:r.o]
    if flag != 3:
        o = r.o; r.obj(H_CLUSTERED); r.take("i"); fo = r.o; fmt = r.take("B")
        r.take("i"); r.take("i"); r.take("3f"); r.take("3f"); r.take("i")
        r.skip_array(4); r.skip_array(4); r.take("B")
        head = bytearray(p[o:r.o]); head[fo - o] = FORMAT_MAP[fmt]
        b0 = r.o
        for _ in range(3):
            r.skip_blob()
        out += head + struct.pack("<I", r.o - b0) + p[b0:r.o]
    o = r.o; r.obj(H_MESHDATA); r.take("B"); fo = r.o; fmt = r.take("B"); r.take("B")
    for _ in range(2):
        for _ in range(r.take("i")):
            r.obj(H_PRIMITIVE); r.o += 24
    head = bytearray(p[o:r.o]); head[fo - o] = FORMAT_MAP[fmt]
    b0 = r.o
    for _ in range(2):
        r.skip_blob()
    out += head + struct.pack("<I", r.o - b0) + p[b0:r.o]
    cnt = r.take("i"); out += struct.pack("<i", cnt)
    for _ in range(cnt):
        hdr = p[r.o:r.o + 12]; r.obj(H_INSTANCING)
        body = bytearray(p[r.o:r.o + INST_BODY]); r.o += INST_BODY
        struct.pack_into("<Q", body, 10, remap(struct.unpack_from("<Q", body, 10)[0]))
        out += hdr + body
    out += p[r.o:r.o + 16]; r.o += 16                      # Platform/SDK version, quantization
    cnt = struct.unpack_from("<i", p, r.o)[0]; out += p[r.o:r.o + 4]; r.o += 4
    for _ in range(cnt):                                   # DynamicReference: 12 B header + 19 B
        out += p[r.o:r.o + 12]; r.o += 12
        body = bytearray(p[r.o:r.o + 19]); r.o += 19
        for k in (2, 11):
            struct.pack_into("<Q", body, k, remap(struct.unpack_from("<Q", body, k)[0]))
        out += body
    g = p[r.o:]
    if len(g) != 29:
        raise ValueError(f"unexpected Wildlands mesh tail length {len(g)}")
    out += g[0:8] + g[10:14] + g[14:17] + g[17:25] + bytes(4) + b"\x00" + g[25:29]
    return bytes(out)


def mesh_materials(p):
    """Material ids of a Mesh's CompiledMeshMaterials list (either game)."""
    out, pat = [], struct.pack("<I", H_DYNREF)
    k = p.find(pat, _find_object(p, H_COMPILED))
    while k >= 0:
        if p[k - 5] == 0xF8 and p[k + 4] == 1:
            out.append(struct.unpack_from("<Q", p, k + 6)[0])
        k = p.find(pat, k + 1)
    return out


# --------------------------------------------------------------------------- textures

def pixel_format(v):
    """GRB inserted one pixel format at 9: 0-8 keep their number, 9 and up shift by one."""
    return v if v < 9 else v + 1


def _ctm_blobs(p, start):
    """Length fields of each inline CompiledTextureMap blob: 48 bytes past the object's type
    hash (12 x u32 PlatformVersion..Alignment, per ATK's GRB reader)."""
    out, pat = [], struct.pack("<I", H_CTM)
    k = p.find(pat, start)
    while k >= 0:
        if k >= 8 and p[k - 5] == 0xF8 and p[k - 4:k] == bytes(4):
            out.append(k + 4 + 48)
        k = p.find(pat, k + 1)
    return out


def convert_texture(p):
    """Wildlands TextureMap payload -> GRB TextureMap payload.
      header     drop the GRW-only Category u32 after MapType (offset 45); remap PixelFormat
      inline     in each CompiledTextureMap, GRB inserts u32 = 4 + L before the blob's i32 L,
                 and the PixelFormat there is remapped too"""
    q = bytearray(p[:45] + p[49:])
    struct.pack_into("<i", q, 25, pixel_format(struct.unpack_from("<i", q, 25)[0]))
    for k in reversed(_ctm_blobs(q, 45)):
        pf = k - 24
        struct.pack_into("<i", q, pf, pixel_format(struct.unpack_from("<i", q, pf)[0]))
        L = struct.unpack_from("<i", q, k)[0]
        if L < 0 or k + 4 + L > len(q):
            raise ValueError(f"implausible CompiledTextureMap blob length {L}")
        q[k:k] = struct.pack("<i", L + 4)
    return bytes(q)


def texture_top_mips(p):
    """CompiledMip ids a Wildlands TextureMap streams its top levels from."""
    n = struct.unpack_from("<i", p, 55)[0]
    return [struct.unpack_from("<Q", p, 59 + 9 * k + 1)[0] for k in range(n)]


# --------------------------------------------------------------------------- materials

def transplant_material(skeleton, class_id, slots):
    """Clone a GRB Material payload and overwrite u64 slots: {payload offset: value}.
    Offset 0 is the ClassID. For GRB's SHD_BAS_DielectricMetallic_v2_TEMP skeleton
    BAS_GEN_MetalRustA the TextureSet is at 25, diffuse at 650 and normal at 719."""
    m = bytearray(skeleton)
    struct.pack_into("<Q", m, 0, class_id)
    for off, v in slots.items():
        struct.pack_into("<Q", m, off, v)
    return bytes(m)


# --------------------------------------------------------------------------- selftest

def selftest(grw, grb, limit=None):
    """convert(GRW) == GRB over the assets both installs ship under one ID."""
    shared = sorted(set(grw.index) & set(grb.index))
    report = {}
    for kind, tid, conv in (("Mesh", T_MESH, None), ("TextureMap", T_TEXTUREMAP, convert_texture)):
        ids = [i for i in shared if grw.index[i][1] == tid][:limit]
        c = collections.Counter()
        for fid in ids:
            try:
                _, _, ra = grw.resources(fid); _, _, rb = grb.resources(fid)
            except Exception:
                c["unreadable"] += 1; continue
            b = {di.class_id(r): r for r in rb}
            for r in ra:
                cid = di.class_id(r)
                if r.type_id != tid or cid not in b:
                    continue
                pa, pb = r.payload, b[cid].payload
                try:
                    if kind == "Mesh":
                        ma, mb = mesh_materials(pa), mesh_materials(pb)
                        out = convert_mesh(pa, dict(zip(ma, mb)) if len(ma) == len(mb) else {})
                    else:
                        out = conv(pa)
                except Exception:
                    c["convert-error"] += 1; continue
                c["identical" if out == pb else ("same length" if len(out) == len(pb) else "re-baked")] += 1
        report[kind] = c
        print(f"{kind:10s} {len(ids):5d} shared entries: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    ok = report["Mesh"]["identical"] > 0 and report["TextureMap"]["identical"] > 0 and \
        not report["Mesh"]["convert-error"] and not report["TextureMap"]["convert-error"]
    print("PASS" if ok else "FAIL",
          "- 'identical' means byte-for-byte GRB; the rest differ in content Ubisoft re-baked")
    return ok


# --------------------------------------------------------------------------- CLI

def _safe(n):
    return re.sub(r'[<>:"/\\|?*]', "_", n)


def main(argv):
    def opt(flag, default=None):
        if flag in argv:
            i = argv.index(flag); v = argv[i + 1]; del argv[i:i + 2]; return v
        return default
    def has(flag):
        if flag in argv:
            argv.remove(flag); return True
        return False
    memory_cap(int(opt("--max-mb", "2048")))
    grw_root = opt("--grw", os.environ.get("GRW_INSTALL", GRW_DEFAULT))
    grb_root = opt("--grb", os.environ.get("GRB_INSTALL", GRB_DEFAULT))
    out_dir = opt("-o", ".")
    material = opt("--material"); limit = opt("--limit")
    drop = has("--drop-uv1"); with_mips = has("--with-mips")
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    dll = os.path.join(grb_root, "oo2core_7_win64.dll")
    oodle = di.Oodle(dll)
    if not oodle.ok:
        raise SystemExit(f"Oodle DLL not found at {dll} (pass --grb <GRB install>)")
    grw, grb = Install(grw_root, oodle), Install(grb_root, oodle)
    cmd, args = argv[0], argv[1:]
    if cmd == "selftest":
        return 0 if selftest(grw, grb, int(limit) if limit else None) else 1
    os.makedirs(out_dir, exist_ok=True)
    def write(name, data):
        path = os.path.join(out_dir, f"1_-_{_safe(name)}.data")
        open(path, "wb").write(data); print(f"wrote {path} ({len(data):,} B)")
    for key in args:
        fid = grw.find(key)
        _, files, res = grw.resources(fid)
        r = next(x for x in res if di.class_id(x) == fid)
        if cmd == "mesh":
            if r.type_id != T_MESH:
                raise SystemExit(f"{key} is not a Mesh")
            p = convert_mesh(r.payload, default_material=int(material) if material else None, drop_uv1=drop)
            write(r.name, build_container([(fid, frame(files, r, p))], dll, oodle))
        elif cmd == "texture":
            if r.type_id != T_TEXTUREMAP:
                raise SystemExit(f"{key} is not a TextureMap")
            write(r.name, build_container([(fid, frame(files, r, convert_texture(r.payload)))], dll, oodle))
            if with_mips:
                for mip in texture_top_mips(r.payload):
                    _, mf, mr = grw.resources(mip)
                    m = next(x for x in mr if di.class_id(x) == mip)
                    write(m.name, build_container([(mip, frame(mf, m))], dll, oodle))
        else:
            raise SystemExit(f"unknown command {cmd!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
