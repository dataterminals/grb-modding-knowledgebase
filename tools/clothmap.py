#!/usr/bin/env python3
"""
clothmap.py - decode a GRB cloth's render<->sim MESH MAPPING (the "wrap"), completely.

A GRB physics garment is two meshes: a low-res simulation CAGE (a `ClothPackage`)
and the high-res VISIBLE mesh. The visible mesh follows the cage through a stored
mapping - one record per cloth-driven render vertex. This tool reads that mapping,
dequantizes it, and (optionally) proves it by rebuilding the render mesh's own
positions, normals, tangents and binormals from the cage.

    python clothmap.py 34224_-_TP_WalkerCoat_Cloth.data
    python clothmap.py 34224_-_TP_WalkerCoat_Cloth.data --install "H:/.../Ghost Recon Breakpoint"
    python clothmap.py cloth.data --mesh 87874_-_TP_Tacvest_Walker_Coat_LOD0.data --lod 0

READ-ONLY. Decoding needs only the standard library (+ the game's Oodle DLL for a
.data). `--mesh`/`--install` also need ATK via atk_bridge.py, to read the mesh.

FORMAT (decoded 2026-09-18; every structural claim verified on all 156 MotionBodies in
the 81 GRB cloth resources, the geometry on 87 distinct cloth LODs / 489,472 vertices -
see meta/research-log.md). After each LOD's ClothPackage come the arrays
clothwrap.py already walks (TriQuad u16[], sim positions vec3[], sim normals vec3[],
sim indices u16[], an empty list, i32 renderCount), then the mapping block:

  +0    u32 1, u32 0 x12
  +52   u32 bufferSize            in dwords, counted from +56
  +56   u32 tableOffset = 18      in dwords from +56
  +60   u32 recordsOffset         in dwords from +56  (= 18 + ceil(renderCount/2))
  +64   f32 min_uv[4]  f32 scale_uv[4]  f32 min_h[4]  f32 scale_h[4]
                                  columns: position, normal, tangent, binormal
  +128  u16 table[renderCount]    per render vertex: its record index, or 0xFFFF
                                  (= not cloth-driven). Non-FFFF entries run 0,1,2...
                                  - records are in render-vertex order. Padded to 4 B.
        record x bound, 20 B:     u8 u[4] | u8 v[4] | u8 h[4] | u16 sim[3] | u16 1

Dwords and vec4 groups: this is laid out as a GPU buffer.

Each attribute a in (position, normal, tangent, binormal) is a point on the record's
sim triangle (sim[0], sim[1], sim[2]):
    u = min_uv[a] + byte*scale_uv[a],  v likewise,  h = min_h[a] + byte*scale_h[a]
    weights (u, v, 1-u-v)            - NOT (1-u-v, u, v)
    position P = sum_i w_i * (x_i + h * n_i)       n_i = the cage's vertex normals
    normal/tangent/binormal = unit( sum_i w'_i * x_i + h' * unit(sum_i w_i n_i) - P )
                                     the direction points sit at unit distance from P
Bytes span 0..254 and (max-min)/scale = 254.5 in every header.

THE SAME NUMBERS ALSO LIVE IN THE MotionBody, which is why ATK's 22 "unmodelled"
sections were unreadable in isolation:
    §4374      mapping header: i32 renderCount, i32 ?, u8 1, i32 bound (0 if all bound), ...
    §4376/4377 position   (u,v) / h  {scale, min, max}
    §4379/4380 normal     (u,v) / h
    §4403/4405 tangent    (u,v) / h
    §4404      tangent  (u,v) bytes, AoSoA-4: [u0..u3, v0..v3, u4..u7, ...]
    §4406      tangent  h bytes
    §4407/4409 binormal   (u,v) / h
    §4408      binormal (u,v) bytes, AoSoA-4
    §4410      binormal h bytes
Every pad byte in §4404-4410 (partial AoSoA block, 16-byte tail) is the section's byte 0.
A body carries one §4374..4380 group per mesh mapping (= §4356 MeshMappingsCount);
exactly one has the flag set and describes this block. The others point at another
LOD's sim cage (their first i32 is that LOD's vertex count).
"""
import sys, os, struct, math, re

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import motioncloth as mc                                           # noqa: E402

ATTRS = ("position", "normal", "tangent", "binormal")
REC = 20
QUANT_SECTIONS = {  # attribute -> (uv header, h header)
    "position": (4376, 4377), "normal": (4379, 4380),
    "tangent": (4403, 4405), "binormal": (4407, 4409),
}
DATA_SECTIONS = {4404: ("tangent", "uv"), 4406: ("tangent", "h"),
                 4408: ("binormal", "uv"), 4410: ("binormal", "h")}


# ---------------------------------------------------------------- reading

def _i32(b, o):
    return struct.unpack_from("<i", b, o)[0]


def after_package(buf, pkg_end):
    """Walk the arrays between a ClothPackage and its mapping block."""
    o = pkg_end
    out = {}

    def arr(o, elt):
        c = _i32(buf, o)
        return o + 4, c, o + 4 + c * elt

    s, c, o = arr(o, 2)
    out["triquad"] = (s, c)
    s, c, o = arr(o, 12)
    out["pos"] = [struct.unpack_from("<3f", buf, s + 12 * k) for k in range(c)]
    s, c, o = arr(o, 12)
    out["nrm"] = [struct.unpack_from("<3f", buf, s + 12 * k) for k in range(c)]
    s, c, o = arr(o, 2)
    out["indices"] = (s, c)
    out["empty_list"] = _i32(buf, o)
    o += 4
    out["render_count"] = _i32(buf, o)
    o += 4
    out["map_start"] = o
    return out


def read_mapping(buf, pkg_end):
    """Decode one LOD's mapping block. Returns a dict; raises ValueError if the
    self-describing offsets disagree with the layout."""
    pp = after_package(buf, pkg_end)
    o, rc = pp["map_start"], pp["render_count"]
    head = struct.unpack_from("<16i", buf, o)
    base = o + 56
    size, t_off, r_off = head[13], head[14], head[15]
    quant = struct.unpack_from("<16f", buf, o + 64)
    q = {a: dict(min_uv=quant[k], scale_uv=quant[4 + k], min_h=quant[8 + k],
                 scale_h=quant[12 + k]) for k, a in enumerate(ATTRS)}
    table = struct.unpack_from(f"<{rc}H", buf, base + 4 * t_off)
    bound = sum(1 for t in table if t != 0xFFFF)
    r0 = base + 4 * r_off
    end = r0 + REC * bound
    problems = []
    if head[0] != 1 or any(head[1:13]):
        problems.append("header preamble is not 1 + 12 zeros")
    if t_off != 18:
        problems.append(f"table offset {t_off} dwords, expected 18")
    if base + 4 * size != end:
        problems.append(f"buffer size {size} dwords does not end at the last record")
    if r0 != base + 4 * t_off + ((2 * rc + 3) // 4) * 4:
        problems.append("records do not start right after the 4-byte-aligned table")
    if [t for t in table if t != 0xFFFF] != list(range(bound)):
        problems.append("table entries are not 0..bound-1 in order")
    records = []
    for i in range(bound):
        p = r0 + REC * i
        raw = buf[p:p + 12]
        sim = struct.unpack_from("<3H", buf, p + 12)
        tail = struct.unpack_from("<H", buf, p + 18)[0]
        records.append((raw, sim, tail))
    if any(r[2] != 1 for r in records):
        problems.append("a record's trailing u16 is not 1")
    V = len(pp["pos"])
    if any(s >= V for r in records for s in r[1]):
        problems.append("a record points past the sim cage")
    return dict(after=pp, head=head, quant=q, table=table, bound=bound,
                records=records, start=o, rec_start=r0, end=end, problems=problems)


def dequantize(m, i):
    """-> {attr: (u, v, h)} and the sim triangle for record i."""
    raw, sim, _ = m["records"][i]
    out = {}
    for k, a in enumerate(ATTRS):
        q = m["quant"][a]
        out[a] = (q["min_uv"] + raw[k] * q["scale_uv"],
                  q["min_uv"] + raw[4 + k] * q["scale_uv"],
                  q["min_h"] + raw[8 + k] * q["scale_h"])
    return out, sim


# ---------------------------------------------------------------- geometry

def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _len(a): return math.sqrt(_dot(a, a))


def _unit(a):
    n = _len(a)
    return _mul(a, 1.0 / n) if n else a


def skin_record(m, i):
    """Rebuild one render vertex: (position, normal, tangent, binormal)."""
    vals, sim = dequantize(m, i)
    X = [m["after"]["pos"][s] for s in sim]
    N = [m["after"]["nrm"][s] for s in sim]
    u, v, h = vals["position"]
    w = (u, v, 1.0 - u - v)
    P = (0.0, 0.0, 0.0)
    NP = (0.0, 0.0, 0.0)
    for k in range(3):
        P = _add(P, _mul(_add(X[k], _mul(N[k], h)), w[k]))
        NP = _add(NP, _mul(N[k], w[k]))
    NP = _unit(NP)
    dirs = []
    for a in ATTRS[1:]:
        ua, va, ha = vals[a]
        wa = (ua, va, 1.0 - ua - va)
        Q = (0.0, 0.0, 0.0)
        for k in range(3):
            Q = _add(Q, _mul(X[k], wa[k]))
        dirs.append(_unit(_sub(_add(Q, _mul(NP, ha)), P)))
    return (P, *dirs)


# ---------------------------------------------------------------- MotionBody cross-check

def _aosoa4(x, y, fill):
    n = len(x)
    m = (n + 3) // 4 * 4
    x = list(x) + [fill] * (m - n)
    y = list(y) + [fill] * (m - n)
    out = []
    for g in range(0, m, 4):
        out += x[g:g + 4] + y[g:g + 4]
    return out


def _padded(payload, values):
    n = len(values)
    return (len(payload) == (n + 15) // 16 * 16 and list(payload[:n]) == list(values)
            and all(b == payload[0] for b in payload[n:]))


def check_sections(body, m):
    """Does the MotionBody carry the SAME numbers as the block? {name: bool}."""
    res = {}
    groups, cur = [], None
    for s in body.sections:
        if s.type == 4374:
            cur = {4374: s.payload}
            groups.append(cur)
        elif cur is not None and s.type in (4376, 4377, 4379, 4380):
            cur.setdefault(s.type, s.payload)
    rc = m["after"]["render_count"]
    mine = [g for g in groups if len(g[4374]) > 8 and g[4374][8] == 1]
    res["one render mapping group"] = len(mine) == 1
    if mine:
        g = mine[0]
        rcount, _x, _flag, nb = struct.unpack_from("<iiBi", g[4374], 0)
        res["§4374 render count"] = rcount == rc
        res["§4374 bound count (0 = all)"] = nb == (0 if m["bound"] == rc else m["bound"])
        for a in ("position", "normal"):
            uv, hh = QUANT_SECTIONS[a]
            q = m["quant"][a]
            if uv in g and hh in g:
                s1 = struct.unpack("<3f", g[uv])
                s2 = struct.unpack("<3f", g[hh])
                res[f"§{uv}/§{hh} = {a} quant"] = ((s1[0], s1[1]) == (q["scale_uv"], q["min_uv"])
                                                   and (s2[0], s2[1]) == (q["scale_h"], q["min_h"]))
    for a in ("tangent", "binormal"):
        uv, hh = QUANT_SECTIONS[a]
        q = m["quant"][a]
        su, sh = body.find(uv), body.find(hh)
        if su and sh:
            s1, s2 = struct.unpack("<3f", su.payload), struct.unpack("<3f", sh.payload)
            res[f"§{uv}/§{hh} = {a} quant"] = ((s1[0], s1[1]) == (q["scale_uv"], q["min_uv"])
                                               and (s2[0], s2[1]) == (q["scale_h"], q["min_h"]))
    col = {a: k for k, a in enumerate(ATTRS)}
    for t, (a, part) in DATA_SECTIONS.items():
        s = body.find(t)
        if s is None:
            res[f"§{t} present"] = False
            continue
        k = col[a]
        if part == "uv":
            want = _aosoa4([r[0][k] for r in m["records"]],
                           [r[0][4 + k] for r in m["records"]], s.payload[0])
        else:
            want = [r[0][8 + k] for r in m["records"]]
        res[f"§{t} = {a} {part} bytes"] = _padded(s.payload, want)
    return res


# ---------------------------------------------------------------- mesh comparison

def compare_to_mesh(m, mesh):
    """Rebuild every bound render vertex and compare with an ATK Mesh object."""
    scale = float(mesh.Scale)       # ATK's Vertex.Position is BEFORE Mesh.Scale
    verts = list(mesh.Vertices)
    if len(verts) != m["after"]["render_count"]:
        return {"error": f"mesh has {len(verts)} vertices, mapping expects "
                         f"{m['after']['render_count']}"}
    pos_err, ang = [], {a: [] for a in ATTRS[1:]}
    attr_of = {"normal": "Normals", "tangent": "Tangents", "binormal": "Binormals"}
    for r, i in enumerate(m["table"]):
        if i == 0xFFFF:
            continue
        P, *dirs = skin_record(m, i)
        v = verts[r]
        R = (v.Position.x * scale, v.Position.y * scale, v.Position.z * scale)
        pos_err.append(_len(_sub(P, R)) * 1000.0)
        for a, d in zip(ATTRS[1:], dirs):
            t = getattr(v, attr_of[a])
            T = _unit((t.x, t.y, t.z))
            c = max(-1.0, min(1.0, _dot(d, T)))
            ang[a].append(math.degrees(math.acos(c)))
    def pct(xs, p):
        s = sorted(xs)
        return s[min(len(s) - 1, int(p / 100.0 * len(s)))] if s else float("nan")
    out = {"bound": len(pos_err), "pos_median_mm": pct(pos_err, 50),
           "pos_p99_mm": pct(pos_err, 99), "pos_max_mm": max(pos_err) if pos_err else 0}
    for a in ATTRS[1:]:
        out[f"{a}_median_deg"] = pct(ang[a], 50)
        out[f"{a}_flipped"] = sum(1 for x in ang[a] if x > 90) / max(1, len(ang[a]))
    return out


def _find_mesh(install, name, cache={}):
    import rig_census as rc_
    import atk_bridge as ab
    import data_inspect as di
    if "inst" not in cache:
        cache["inst"] = rc_.Install(install)
        ab.start()
        ab.arm()
    res, _rec, _ok = cache["inst"].resources(name=name)
    hit = next((r for r in res if di.type_name(r.type_id) == "Mesh"), None)
    if hit is None:
        return None
    return ab.read_object(hit.header, hit.payload, rc_.ATK_MESH)


# ---------------------------------------------------------------- CLI

def report(path, mesh_path=None, install=None, only_lod=None):
    buf = mc.load_resource_payload(path)
    pkgs = mc.locate_clothpackages(buf)
    print("=" * 78)
    print(f"CLOTH MESH MAPPING: {os.path.basename(path)}  ({len(pkgs)} LOD(s))")
    for lod, p in enumerate(pkgs):
        if only_lod is not None and lod != only_lod:
            continue
        body = p.bodies[0]
        name = mc.body_name(body) or "?"
        m = read_mapping(buf, p.end)
        rc = m["after"]["render_count"]
        print(f"\n  LOD{lod}  body {name}")
        print(f"    sim cage {len(m['after']['pos'])} verts; render mesh {rc} verts, "
              f"{m['bound']} cloth-driven ({100.0 * m['bound'] / max(1, rc):.0f}%), "
              f"{rc - m['bound']} skinned only")
        for a in ATTRS:
            q = m["quant"][a]
            print(f"    {a:<9} u,v in [{q['min_uv']:.4g}, {q['min_uv'] + 254 * q['scale_uv']:.4g}]"
                  f"   h in [{q['min_h']:.4g}, {q['min_h'] + 254 * q['scale_h']:.4g}]")
        print("    layout: " + ("OK" if not m["problems"] else "; ".join(m["problems"])))
        chk = check_sections(body, m)
        bad = [k for k, ok in chk.items() if not ok]
        print(f"    MotionBody carries the same numbers: {sum(chk.values())}/{len(chk)} checks"
              + ("" if not bad else "  FAILED: " + ", ".join(bad)))
        mesh = None
        if mesh_path:
            import atk_bridge as ab
            mesh = ab.read_mesh(mesh_path)
        elif install:
            mm = re.match(r"[Ss]im_(.+?_LOD\d+)_0x", name)
            if mm:
                mesh = _find_mesh(install, mm.group(1))
                if mesh is None:
                    print(f"    (render mesh {mm.group(1)} not found by name)")
        if mesh is not None:
            c = compare_to_mesh(m, mesh)
            if "error" in c:
                print(f"    mesh check: {c['error']}")
            else:
                print(f"    rebuilt from the cage vs the real mesh ({c['bound']} vertices):")
                print(f"      position  median {c['pos_median_mm']:.3f} mm   p99 "
                      f"{c['pos_p99_mm']:.2f} mm   max {c['pos_max_mm']:.2f} mm")
                for a in ATTRS[1:]:
                    fl = c[f"{a}_flipped"]
                    print(f"      {a:<9} median {c[f'{a}_median_deg']:5.2f} deg"
                          + (f"   ({fl:.0%} anti-parallel)" if fl > 0.01 else ""))


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = list(argv[1:])
    mesh_path = install = None
    only_lod = None
    if "--mesh" in args:
        k = args.index("--mesh"); mesh_path = args[k + 1]; del args[k:k + 2]
    if "--install" in args:
        k = args.index("--install"); install = args[k + 1]; del args[k:k + 2]
    if "--lod" in args:
        k = args.index("--lod"); only_lod = int(args[k + 1]); del args[k:k + 2]
    if not args:
        print(__doc__)
        return 1
    for p in args:
        report(p, mesh_path, install, only_lod)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
