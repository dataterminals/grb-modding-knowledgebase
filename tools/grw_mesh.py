#!/usr/bin/env python3
"""
grw_mesh.py - read a Ghost Recon Wildlands render Mesh without ATK.

ATK has no Wildlands (its `Game` enum has no member for it), so `atk_bridge.py`
cannot read these meshes. This tool reads them directly: vertex positions,
normals, UVs and skinning, plus the triangle list, and can write an OBJ to look
at in Blender.

    python grw_mesh.py  CN_Primary_ElYayo_Poncho_LOD0.data
    python grw_mesh.py --forge "D:\\...\\Wildlands\\DataPC_patch_01.forge" CN_Primary_ElYayo_Poncho_LOD0
    python grw_mesh.py  mesh.data --obj poncho.obj

A `.data` comes from `data_inspect.py --forge <forge> <name> --extract <dir>`.
READ-ONLY. Standard library only (+ ATK's lzo.dll, through data_inspect).

FORMAT (2026-10-08). ATK v1.3.1's GRB readers, with two fields removed,
read Wildlands to the byte. Every step below is checked to land on the next
object; the tool says so when one does not.

  object header   u32 (0xF8000000 | object number), u32 0, u32 CRC32(type name)
  CompiledMesh    i32 n + n bytes Data; u8 (!= 3: a ClusteredMeshData object follows);
                  MeshData object; i32 n + n MeshInstancingData objects;
                  u32 PlatformVersion; u32 SDKVersion;
                  f32 QuantizationFactor; f32 UVQuantizationFactor
  ClusteredMeshData  i32 DataVersion; u8 VertexFormat; i32 VertexStride; i32 ClusterCount;
                  vec3 Center; vec3 HalfExtend; i32 DrawPrimsCount;
                  i32[] ClusterCountPerDrawPrim; i32[] VertexOffsetPerDrawPrim;
                  bool IsFixedClusterSize; [GRB only: u32];
                  i32 n + VertexBufferData; i32 n + IndexBufferData; i32 n + PrimitiveDescData
  MeshData        bool IsIndexBuffer32Bit; u8 VertexFormat; u8 VertexStride;
                  i32 n + n MeshPrimitive; i32 n + n MeshPrimitive (shadow);
                  [GRB only: u32]; i32 n + VertexBufferData; i32 n + IndexBufferData
  MeshPrimitive   i32 MinIndex, IsUsingDepthOnlyBuffers, NumVertices, StartIndex,
                  PrimitiveCount, Type
  MeshInstancingData  bool ShadowCaster; u16 MaterialType; i16 boneCount; u16 SubMeshIndex;
                  i16 NumVertices; u8; u64 Material; u16 bones[boneCount], padded to 256 B

  vertex          i16 x, y, z, w      position = i16 / 32767 * QuantizationFactor
                                      (w = ATK's Color0)
                  u8 normal[4], tangent[4], binormal[4]    (b / 127.5 - 1; 4th byte = Color1)
                  i16 u, v            uv = i16 / 32767 * UVQuantizationFactor
                  u8 index[J], u8 weight[J]    J = 4 (stride 32) or 8 (stride 40);
                                      weights sum to 255. The format byte for these is
                                      0 and 1; GRB's 1 means a 36-byte Joint4_Col4ub.

COVERAGE (census of the whole install, 2026-10-08): the structure parses on all
46,609 distinct Wildlands meshes. Vertices decode for the two SKINNED layouts,
stride 32 (10,654 meshes) and 40 (7), whose sampled weights all sum to 255.
Static props and world geometry use strides 16, 20, 24, 28, 44 and 52, which
are not mapped; `vertices()` refuses them rather than guess. One 70,549-vertex
mesh (stride 44) has indices that do not read as a plain list.

The position and UV scales were confirmed against the game's own cloth data.
The cloth stores each visible vertex's UV as floats, and these decode to
match them to 1.5e-5. The cloth's mapping also rebuilds these positions to a
median of 0.12-0.45 mm (meta/research-log.md, 2026-10-08).
"""
import sys, os, struct, zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import data_inspect as di                                              # noqa: E402


def _crc(name):
    return zlib.crc32(name.encode("ascii"))


H_COMPILED, H_CLUSTERED, H_MESHDATA = _crc("CompiledMesh"), _crc("ClusteredMeshData"), _crc("MeshData")
H_PRIMITIVE, H_INSTANCING = _crc("MeshPrimitive"), _crc("MeshInstancingData")


class Reader:
    def __init__(self, b, o=0):
        self.b, self.o = b, o

    def take(self, fmt):
        v = struct.unpack_from("<" + fmt, self.b, self.o)
        self.o += struct.calcsize("<" + fmt)
        return v if len(v) > 1 else v[0]

    def blob(self):
        n = self.take("i")
        s = self.o
        self.o += n
        return s, n

    def is_object(self, h):
        if self.o + 12 > len(self.b):
            return False
        a, z, t = struct.unpack_from("<III", self.b, self.o)
        return a & 0xFF000000 == 0xF8000000 and z == 0 and t == h

    def object(self, h, what):
        if not self.is_object(h):
            raise ValueError(f"expected a {what} object at byte {self.o}")
        self.o += 12


def find_object(b, h):
    """First object header of type `h` in the payload. The Mesh wrapper in front
    of CompiledMesh (bones, submeshes, extents) is not parsed - it is located."""
    pat = struct.pack("<I", h)
    k = b.find(pat)
    while k >= 0:
        if k >= 8 and b[k - 5] == 0xF8 and b[k - 4:k] == bytes(4):
            return k - 8
        k = b.find(pat, k + 1)
    return None


def parse(payload):
    """Parse one Mesh resource payload. Returns a dict, or raises ValueError."""
    start = find_object(payload, H_COMPILED)
    if start is None:
        raise ValueError("no CompiledMesh object in this payload")
    r = Reader(payload, start)
    r.object(H_COMPILED, "CompiledMesh")
    r.blob()                                                       # Data
    out = dict(clustered=None)
    if r.take("B") != 3:
        r.object(H_CLUSTERED, "ClusteredMeshData")
        c = dict(data_version=r.take("i"), format=r.take("B"), stride=r.take("i"),
                 clusters=r.take("i"), center=r.take("3f"), half_extend=r.take("3f"),
                 draw_prims=r.take("i"))
        c["clusters_per_prim"] = [r.take("i") for _ in range(r.take("i"))]
        c["vertex_offset_per_prim"] = [r.take("i") for _ in range(r.take("i"))]
        c["fixed_cluster_size"] = r.take("B")
        c["vb"], c["ib"], c["prim_desc"] = r.blob(), r.blob(), r.blob()
        out["clustered"] = c
    r.object(H_MESHDATA, "MeshData")
    md = dict(index32=r.take("B"), format=r.take("B"), stride=r.take("B"))
    for key in ("standard", "shadow"):
        prims = []
        for _ in range(r.take("i")):
            r.object(H_PRIMITIVE, "MeshPrimitive")
            prims.append(dict(zip(("min_index", "depth_only", "num_vertices", "start_index",
                                   "primitive_count", "type"), r.take("6i"))))
        md[key] = prims
    md["vb"], md["ib"] = r.blob(), r.blob()
    out["meshdata"] = md
    inst = []
    for _ in range(r.take("i")):
        r.object(H_INSTANCING, "MeshInstancingData")
        base = r.o
        shadow, mtype, nb, sub, nv = r.take("BHhHh")
        r.take("B")
        mat = r.take("Q")
        bones = [r.take("H") for _ in range(nb)]
        r.o = base + 1 + 2 + 2 + 2 + 2 + 1 + 8 + 256
        inst.append(dict(shadow_caster=shadow, material_type=mtype, submesh=sub,
                         num_vertices=nv, material=mat, bones=bones))
    out["instancing"] = inst
    out["platform_version"], out["sdk_version"] = r.take("II")
    out["quantization"], out["uv_quantization"] = r.take("ff")
    out["compiled_end"] = r.o
    return out


def vertices(payload, m):
    """Decode the vertex buffer. Returns a list of dicts."""
    c = m["clustered"]
    src = c if c and c["vb"][1] else m["meshdata"]
    vb_start, vb_len = src["vb"]
    stride = src["stride"]
    J = {32: 4, 40: 8}.get(stride)
    if J is None:
        raise ValueError(f"vertex stride {stride} is not a skinned layout this reader decodes "
                         f"(32 or 40); static props and world meshes use others")
    qf, uq = m["quantization"], m["uv_quantization"]
    out = []
    for i in range(vb_len // stride):
        o = vb_start + stride * i
        x, y, z, w = struct.unpack_from("<4h", payload, o)
        nrm = [b / 127.5 - 1 for b in payload[o + 8:o + 11]]
        tan = [b / 127.5 - 1 for b in payload[o + 12:o + 15]]
        bin_ = [b / 127.5 - 1 for b in payload[o + 16:o + 19]]
        u, v = struct.unpack_from("<2h", payload, o + 20)
        idx = list(payload[o + 24:o + 24 + J])
        wts = list(payload[o + 24 + J:o + 24 + 2 * J])
        out.append(dict(pos=(x / 32767 * qf, y / 32767 * qf, z / 32767 * qf), color0=w,
                        normal=nrm, tangent=tan, binormal=bin_,
                        uv=(u / 32767 * uq, v / 32767 * uq), joints=idx, weights=wts))
    return out


def indices(payload, m):
    """The index buffer as u16 or u32 values, as stored."""
    c = m["clustered"]
    src = c if c and c["ib"][1] else m["meshdata"]
    s, n = src["ib"]
    if m["meshdata"]["index32"]:
        return list(struct.unpack_from(f"<{n // 4}I", payload, s))
    return list(struct.unpack_from(f"<{n // 2}H", payload, s))


def load(path=None, forge=None, name=None):
    """-> (resource name, payload) for the first Mesh in a .data, or a forge entry."""
    if forge:
        hits = list(di.forge_lookup(forge, [name]))
        if not hits:
            raise SystemExit(f"{name} is not an entry of {forge}")
        raw = hits[0][2]
    else:
        raw = open(path, "rb").read()
    _meta, files = di.read_container_bytes(raw, di.Oodle(di.find_oodle(forge or path)))
    for r in di.walk(files)[0]:
        if di.type_name(r.type_id) == "Mesh":
            return r.name, r.payload
    raise SystemExit("no Mesh resource in that container")


def write_obj(path, verts, idx):
    with open(path, "w", encoding="ascii") as f:
        f.write("# Ghost Recon Wildlands mesh, decoded by grw_mesh.py\n")
        for v in verts:
            f.write("v %.6f %.6f %.6f\n" % v["pos"])
        for v in verts:
            f.write("vt %.6f %.6f\n" % (v["uv"][0], 1.0 - v["uv"][1]))
        for v in verts:
            f.write("vn %.4f %.4f %.4f\n" % tuple(v["normal"]))
        for k in range(0, len(idx) - 2, 3):
            a, b, c = idx[k] + 1, idx[k + 1] + 1, idx[k + 2] + 1
            f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")


def report(name, payload):
    m = parse(payload)
    verts = vertices(payload, m)
    idx = indices(payload, m)
    c = m["clustered"]
    src = c if c and c["vb"][1] else m["meshdata"]
    lo = [min(v["pos"][a] for v in verts) for a in range(3)]
    hi = [max(v["pos"][a] for v in verts) for a in range(3)]
    sums = {sum(v["weights"]) for v in verts}
    L = ["=" * 70, f"MESH: {name}",
         f"  {len(verts):,} vertices, {len(idx) // 3:,} triangles, stride {src['stride']}, "
         f"format byte {src['format']}" + ("  (clustered)" if c and c["vb"][1] else ""),
         f"  QuantizationFactor {m['quantization']}   UVQuantizationFactor {m['uv_quantization']:.6f}",
         "  bounds  " + "  ".join(f"{'xyz'[a]} [{lo[a]:.3f}, {hi[a]:.3f}]" for a in range(3)),
         f"  skin weights per vertex sum to {sorted(sums)}"
         + ("" if sums == {255} else "   <- not all 255: the joint layout guess is wrong"),
         f"  index max {max(idx) if idx else '-'} (of {len(verts)} vertices)"
         + ("" if not idx or max(idx) < len(verts) else "   <- out of range: not a plain triangle list"),
         f"  submeshes {len(m['instancing'])}; bones per submesh "
         + ", ".join(str(len(i["bones"])) for i in m["instancing"])]
    return "\n".join(L), verts, idx


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = list(argv[1:])

    def opt(flag):
        if flag not in args:
            return None
        k = args.index(flag); v = args[k + 1]; del args[k:k + 2]
        return v

    forge, obj = opt("--forge"), opt("--obj")
    if not args:
        print(__doc__); return 1
    for a in args:
        name, payload = load(forge=forge, name=a) if forge else load(path=a)
        text, verts, idx = report(name, payload)
        print(text)
        if obj:
            write_obj(obj, verts, idx)
            print(f"  wrote {obj}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
