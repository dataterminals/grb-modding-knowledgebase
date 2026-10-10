#!/usr/bin/env python3
"""
havok_tag.py - read Havok binary tagfiles (TAG0) and convert Wildlands MeshShape collision blobs to Breakpoint's.

An Anvil MeshShape resource carries its collision BVH as a Havok tagfile in PhysicsSDKDataPack.SerializedRawData
(layout in grw_entities.py). The triangles themselves stay in the MeshShape's own Vertices/Indices; the tagfile
holds only an hknpExternMeshShapeData: a static AABB tree over those triangles (plus an unused SIMD tree).

    GRW (Havok 2016.1, SDKV 20160100): TAG0 { SDKV, DATA, TYPE { TPTR TSTR TNAM FSTR TBOD THSH TPAD }, INDX { ITEM PTCH } }
    GRB (Havok 2018.2, SDKV 20180200): TAG0 { SDKV, DATA, TCRF, INDX { ITEM PTCH } }

GRB's tagfiles carry no types: TCRF names a type compendium (ID 0x1649375A287AB81B on every sample) that the game
holds elsewhere. Items are the same in both games (measured on 60 random _RT entries of each, 2026-10-10):
    1  hknpExternMeshShapeData   x1    root, 128 bytes at 0
    2  hkcdStaticTree::Codec3Axis6  xN  the tree's nodes, 6 bytes each, at 128
    3  hkcdSimdTree::Node        x2    always empty (every AABB lane +/-3.4028e38, data 0) in both games

What changed between the SDKs:
    root      GRW: aabbTree @32 (nodes array, domain hkAabb @48), simdTree @80 = { vtable 8, nodes array @88 }
              GRB: aabbTree @32 unchanged, simdTree @80 = { nodes array @80, u8 @96 = 1 on every sample }
    Node      GRW 112 bytes (hkcdFourAabb 96 + u32[4]); GRB 128 bytes (16 more, 0 on every sample)
    patches   pointer fix-ups at the two arrays: GRW @32, @88; GRB @32, @80
The tree codec is the same: on the Ghost Room twin TPL_Ground_64m (both games), both trees decode under one rule to
leaf boxes that hold their triangles with ~0.3 m slack (leaf_boxes below). Ubisoft rebuilt the tree for GRB (a
different but equivalent tree), so a converted blob is not byte-identical to GRB's own; it is GRB's format around
GRW's tree. Verified: grb_blob() re-wraps GRB's own trees byte-identically (selftest). Not yet verified in game.

    python havok_tag.py inspect <blob.tag> ...      sections, SDK, items, patches
    python havok_tag.py convert <grw.tag> -o <grb.tag>
READ-ONLY except -o.
"""
import sys, struct, argparse

SDK_GRW, SDK_GRB = b"20160100", b"20180200"
GRB_COMPENDIUM = bytes.fromhex("1bb87a285a374916") + bytes(16)       # TCRF payload on every GRB sample
GRB_TYPES = {"root": 80, "codec": 44, "node": 52, "codec_array": 63, "node_array": 65}   # compendium type indices
FLT_MAX, NEG_FLT_MAX = bytes.fromhex("eeff7f7f"), bytes.fromhex("eeff7fff")   # +/-0x7F7FFFEE (just under FLT_MAX), as written
EMPTY_NODE_GRB = (FLT_MAX * 4 + NEG_FLT_MAX * 4) * 3 + bytes(32)      # hkcdFourAabb (lx hx ly hy lz hz) + 32 B
CONTAINERS = ("TAG0", "TYPE", "INDX", "TCM0")


def sections(b, o=0, end=None, depth=0, out=None):
    """[(depth, tag, flag, offset, size)]. Header: u32 big-endian (flag << 30 | size incl. header), 4-char tag."""
    end = len(b) if end is None else end
    out = [] if out is None else out
    while o + 8 <= end:
        h = struct.unpack_from(">I", b, o)[0]; size = h & 0x3FFFFFFF; tag = b[o + 4:o + 8].decode("latin1")
        if size < 8:
            raise ValueError(f"bad section size {size} at {o}")
        out.append((depth, tag, h >> 30, o, size))
        if tag in CONTAINERS:
            sections(b, o + 8, o + size, depth + 1, out)
        o += size
    return out


def packed(b, o):
    """Havok's variable-length unsigned int (TNAM / TBOD)."""
    x = b[o]
    if not x & 0x80:
        return x, o + 1
    k = x >> 3
    if 0x10 <= k <= 0x17:
        return ((x << 8) | b[o + 1]) & 0x3FFF, o + 2
    if 0x18 <= k <= 0x1B:
        return int.from_bytes(b[o:o + 3], "big") & 0x1FFFFF, o + 3
    if k == 0x1C:
        return int.from_bytes(b[o:o + 4], "big") & 0x7FFFFFF, o + 4
    if k == 0x1D:
        return int.from_bytes(b[o:o + 5], "big") & 0x7FFFFFFFF, o + 5
    if k == 0x1E:
        return int.from_bytes(b[o:o + 8], "big") & 0x7FFFFFFFFFFFFFF, o + 8
    return int.from_bytes(b[o + 1:o + 9], "big"), o + 9


def parse(b):
    """-> dict: sections, sdk, data, items [(type, flags, offset, count)], patches [(type, [offsets])], tcrf,
    and (when the file carries types) type names."""
    secs = sections(b)
    at = {t: (o, s) for _d, t, _f, o, s in secs}

    def body(t):
        o, s = at[t]
        return b[o + 8:o + s]
    r = {"sections": secs, "sdk": body("SDKV") if "SDKV" in at else None, "data": body("DATA") if "DATA" in at else b""}
    if "TCRF" in at:
        r["tcrf"] = body("TCRF")
    if "TSTR" in at and "TNAM" in at:
        tstr = [s.decode("latin1") for s in body("TSTR").rstrip(b"\0").split(b"\0")]
        q = body("TNAM"); n, o = packed(q, 0); names = [None]
        for _ in range(n - 1):
            ni, o = packed(q, o); np_, o = packed(q, o)
            for _ in range(np_):
                _pn, o = packed(q, o); _pv, o = packed(q, o)
            names.append(tstr[ni])
        r["types"] = names
    q = body("ITEM") if "ITEM" in at else b""
    r["items"] = []
    for i in range(0, len(q), 12):
        w, off, cnt = struct.unpack_from("<III", q, i)
        r["items"].append((w & 0xFFFFFF, w >> 24, off, cnt))
    q = body("PTCH") if "PTCH" in at else b""
    r["patches"] = []; o = 0
    while o < len(q):
        t, c = struct.unpack_from("<II", q, o); o += 8
        r["patches"].append((t, list(struct.unpack_from(f"<{c}I", q, o)))); o += 4 * c
    return r


def static_tree(blob):
    """An hknpExternMeshShapeData blob (either game) -> (domain: 32 bytes hkAabb, nodes: 6*N bytes, N)."""
    r = parse(blob); d = r["data"]
    if len(r["items"]) != 4:
        raise ValueError(f"expected 4 items (null, root, tree nodes, simd nodes), got {len(r['items'])}")
    _t, _f, off, n = r["items"][2]
    if r["sdk"] == SDK_GRW:
        simd_ref = 88; nsz = 112
    elif r["sdk"] == SDK_GRB:
        simd_ref = 80; nsz = 128
    else:
        raise ValueError(f"unknown Havok SDK {r['sdk']!r}")
    if struct.unpack_from("<Q", d, 32)[0] != 2 or struct.unpack_from("<Q", d, simd_ref)[0] != 3:
        raise ValueError("root does not reference the tree nodes (item 2) and SIMD nodes (item 3) where expected")
    _t3, _f3, off3, n3 = r["items"][3]
    for i in range(n3):
        node = d[off3 + i * nsz:off3 + (i + 1) * nsz]
        if node[:96] != EMPTY_NODE_GRB[:96] or any(node[96:]):
            raise ValueError("the SIMD tree holds data (never seen in either game); not converted")
    return d[48:80], d[off:off + 6 * n], n


def leaf_boxes(domain, nodes):
    """Decode a Codec3Axis6 tree -> {primitive index: [(min xyz, max xyz)]}. Node: u8 xyz[3] (per axis: high nibble
    h, low nibble l; child min = parent min + h^2 * extent / 226, child max = parent max - l^2 * extent / 226),
    u8 hiData, u16 loData. hiData bit 7 = internal; then (hiData & 0x7F) << 16 | loData = leaves in the left subtree,
    left child = next node, right child = this + 2 * that. A leaf's value is its primitive (triangle) index."""
    lo0 = struct.unpack_from("<3f", domain, 0); hi0 = struct.unpack_from("<3f", domain, 16)
    out = {}; stack = [(0, list(lo0), list(hi0))]
    while stack:
        i, plo, phi = stack.pop()
        xyz = nodes[6 * i:6 * i + 3]; h = nodes[6 * i + 3]; l = struct.unpack_from("<H", nodes, 6 * i + 4)[0]
        ext = [phi[a] - plo[a] for a in range(3)]
        lo = [plo[a] + (xyz[a] >> 4) ** 2 * ext[a] / 226.0 for a in range(3)]
        hi = [phi[a] - (xyz[a] & 15) ** 2 * ext[a] / 226.0 for a in range(3)]
        v = ((h & 0x7F) << 16) | l
        if h & 0x80:
            stack.append((i + 2 * v, lo, hi)); stack.append((i + 1, lo, hi))
        else:
            out.setdefault(v, []).append((lo, hi))
    return out


def _section(tag, payload, leaf=True):
    return struct.pack(">I", (1 << 30 if leaf else 0) | (len(payload) + 8)) + tag + payload


def grb_blob(domain, nodes, n):
    """GRB (2018.2, TCRF) hknpExternMeshShapeData tagfile around a static tree."""
    assert len(domain) == 32 and len(nodes) == 6 * n
    root = bytearray(128)
    struct.pack_into("<Q", root, 32, 2); root[48:80] = domain
    struct.pack_into("<Q", root, 80, 3); root[96] = 1
    off3 = (128 + 6 * n + 15) & ~15
    data = bytes(root) + nodes + bytes(off3 - 128 - 6 * n) + EMPTY_NODE_GRB * 2   # ends at the last node (selftest)
    t = GRB_TYPES
    items = struct.pack("<III", 0, 0, 0) + struct.pack("<III", 0x10 << 24 | t["root"], 0, 1) + \
        struct.pack("<III", 0x20 << 24 | t["codec"], 128, n) + struct.pack("<III", 0x20 << 24 | t["node"], off3, 2)
    ptch = struct.pack("<III", t["codec_array"], 1, 32) + struct.pack("<III", t["node_array"], 1, 80)
    inner = _section(b"SDKV", SDK_GRB) + _section(b"DATA", data) + _section(b"TCRF", GRB_COMPENDIUM) + \
        _section(b"INDX", _section(b"ITEM", items) + _section(b"PTCH", ptch), leaf=False)
    return _section(b"TAG0", inner, leaf=False)


def convert(grw_blob):
    """GRW MeshShape PhysicsSDKDataPack blob -> GRB's format (same tree). Raises ValueError on anything unexpected."""
    r = parse(grw_blob)
    if r["sdk"] != SDK_GRW:
        raise ValueError(f"not a GRW (2016.1) tagfile: SDK {r['sdk']!r}")
    names = r.get("types", [])
    root_t = r["items"][1][0] if len(r["items"]) > 1 else 0
    if not names or root_t >= len(names) or names[root_t] != "hknpExternMeshShapeData":
        raise ValueError(f"root is not hknpExternMeshShapeData ({names[root_t] if names and root_t < len(names) else '?'})")
    return grb_blob(*static_tree(grw_blob))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inspect"); p.add_argument("files", nargs="+")
    p = sub.add_parser("convert"); p.add_argument("file"); p.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv[1:])
    if a.cmd == "inspect":
        for f in a.files:
            b = open(f, "rb").read(); r = parse(b)
            print(f"== {f}: {len(b)} bytes, SDK {r['sdk'].decode() if r['sdk'] else '?'}"
                  + (f", TCRF {r['tcrf'][:8].hex()}" if "tcrf" in r else ""))
            for d, t, fl, o, s in r["sections"]:
                print("  " * (d + 1) + f"{t} @{o} {s} B" + ("" if fl else " (container)"))
            names = r.get("types")
            for i, (t, fl, off, cnt) in enumerate(r["items"]):
                nm = names[t] if names and t < len(names) else f"type #{t}"
                print(f"  item {i}: {nm} flags {fl:#x} @{off} x{cnt}")
            print("  patches:", [(names[t] if names and t < len(names) else t, o) for t, o in r["patches"]])
    else:
        out = convert(open(a.file, "rb").read())
        open(a.out, "wb").write(out)
        print(f"wrote {len(out)} bytes to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
