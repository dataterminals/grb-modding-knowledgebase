#!/usr/bin/env python3
"""
grw_cell.py - transplant Ghost Recon Wildlands world cells into a Ghost Recon Breakpoint world cell.

The assembler behind the 2026-10-10 world tests W5-W8 (meta/research-log.md, entries "fourth" and
"fifth"). Takes the objects a GRW cell's GridCell activates, converts them and everything they
reach, and writes files for an ATK unpack folder of the host's _patch_01 forge.

    python grw_cell.py port Cell02757_DataBlock --host Cell45147_DataBlock \
        --patch-forge "D:/GRB_Backups/.../DataPC_TGT_WorldMap_MaungaNui_Split_patch_01.forge" \
        --anchor -4651.07,6228.54 --offset -4,24 \
        [--ground grid.npy --ground-origin -4801,6078 --ground-step 0.5] [--census DIR] -o out_dir

--patch-forge must be the VANILLA patch forge (a backup): its 145 table is the base, and its entry
count numbers the output files (<145 index>_-_PrefetchingFileInfos.PrefetchInfo, then the host cell,
then one file per new entry). Copy the output over the unpack folder and repack with ATK.

RULES IT APPLIES (each learned in game or measured on both installs):
- a GRW cell's GridCell activates Objects[:NumberOfObjectsToActivate]; those are brought
- grw_entities.convert(drop_grw_only, strip_physics); a removed component nulls ResetData
- GRB cells hold no inline Mesh/TextureMap (0/321): every mesh becomes its own entry, carrying
  its Materials and TextureSets (a W5 build with inline meshes hung the game)
- every GRB material references a TextureSet (158/158; null renders magenta): sets are synthesized
  for GRW materials without one, ClassID = material | 1<<45; slots whose texture isn't shipped are nulled
- per-instance material overrides (MaterialOverrider, MeshInstanceMaterialInfo.InstanceMaterial) that
  point at GRW materials not shipped are dropped; the mesh keeps its own material
- groups move rigidly with the height shift taken from their content (AutoGroups keep their origin
  at z = 0); with a ground grid, AutoGroup children are seated on the ground one by one
- host GridCell: refs inserted at its activation boundary, count raised; metadata rows appended
- every shipped ClassID found anywhere in GRB (entry index + optional full census of inner IDs)
  is re-IDed with grw_reid.reid(); every shipped reference must resolve
- 145: the host record (a tree; see prefetch_write) gains the new mesh dependencies (tail 01);
  each mesh entry gets a template + textures record, each texture and mip an empty one

--collision (needs --census) keeps the static-collision components (RigidBody, Inert, MergedPhysics; destructibles
still go). Primitive shapes go inline into the host; MeshShapes become their own entries like GRB's _RT entries, the
Havok blob converted 2016.1 -> 2018.2 (havok_tag.convert) and listed in the host's 145 record (tail 01, empty record
of their own). Collision materials keep their GRW IDs: GRB has the GRN library under the same IDs, so each entry
embeds GRB's own copy of the CollisionMaterial + PhysicsCollisionMaterial it uses (as GRB does), materials in a
global DBContainerEntry are referenced, and any GRB lacks are re-pointed at FALLBACK_MATERIAL. Bodies reaching a
shape that can't ship (no layout, unconvertible blob, not found) lose their physics. Verified offline only.

Materials default to a clone of GRB's BAS_GEN_MetalRustA (template SHD_BAS_DielectricMetallic_v2_TEMP)
with diffuse/normal from the GRW TextureSet, the path proven in game (W6b). --materials learned uses
grw_materials.convert_pair (not yet tested in game).

READ-ONLY on both installs; writes only -o. Caps its own memory (--max-mb, default 2000).
"""
import sys, os, struct, glob, collections, argparse, zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import data_inspect as di                      # noqa: E402
import forge_inspect as fi                     # noqa: E402
import prefetch_inspect as pi                  # noqa: E402
import prefetch_write as pw                    # noqa: E402
import grw2grb as g                            # noqa: E402
import grw_entities as ge                      # noqa: E402
import grw_reid as rid                         # noqa: E402

GRW_DEFAULT = r"D:\SteamLibrary\steamapps\common\Wildlands"
GRB_DEFAULT = r"H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"
TEMPLATE, DEFAULT_NORMAL = 1825790666323, 9          # SHD_BAS_DielectricMetallic_v2_TEMP; "Default Normal Texture"
SKELETON = (1709766182479, 1456070548008)            # GRB entry holding BAS_GEN_MetalRustA, its ClassID
SET_LAYOUT = (276140946872, 71022280543)             # GRW statue container, its FabricCanvasDirt_Set (2 live slots)
SYNTH_TAG = 1 << 45
STRIP = {"RigidBodyComponent", "cGameplayDestructibleComponent", "MergedPhysicsComponent", "InertComponent"}
# --collision keeps the static-collision components (destructibles still go: their debris Parts are never activated)
COLLISION_KEEP = {"RigidBodyComponent", "MergedPhysicsComponent", "InertComponent"}
# --collision: primitive shapes go inline into the host cell like GRB's own; MeshShapes become their own entries like
# GRB's 9,409 _RT entries, their Havok blob converted 2016.1 -> 2018.2 by havok_tag.convert (verified offline only)
SHAPES = ("BoxShape", "CapsuleShape", "ConvexVerticesShape", "ReferenceListShape")
# GRB keeps GRW's GRN collision-material library under the same IDs (census 2026-10-10: GRN_Rock 0x11f1a6a643 and
# Physics_GRN_Rock in 2,069 entries, GRN_Wood_Weak 4,121, GRN_Metal_Fence 2,867, ...), embedding copies next to the
# shapes that use them; materials in a global DBContainerEntry (like 0x1523930094, referenced from both games' _RT
# entries) are only referenced. A material GRB doesn't have is re-pointed at that global one (inferred: a hard surface).
FALLBACK_MATERIAL = 0x1523930094
P8 = lambda x: struct.pack("<Q", x)
U8 = lambda b, o: struct.unpack_from("<Q", b, o)[0]
tn = fi.type_name


class Install:
    """An install's entry index plus container access (patches win, like the game)."""
    def __init__(self, root, oodle, base_only=False):
        self.root, self.oodle = root, oodle
        self.index = g.install_index(root)
        if base_only:
            self.base = {}
            for p in sorted(glob.glob(os.path.join(root, "*.forge"))):
                if "_patch_" in p:
                    continue
                for fid, ext, name, off, ln in fi.forge_entries(p):
                    if ext:
                        self.base[fid] = (p, ext, name, off, ln)

    def by_name(self, name, base=False):
        idx = self.base if base else self.index
        hits = [i for i, v in idx.items() if v[2] == name]
        if not hits:
            raise SystemExit(f"no entry named {name!r} in {self.root}")
        return hits[0]

    def container(self, fid, base=False):
        p, _e, _n, off, ln = (self.base if base else self.index)[fid]
        with open(p, "rb") as f:
            f.seek(off); b = f.read(ln)
        meta, files = di.read_container_bytes(b, self.oodle)
        res, end = di.walk(files)
        assert end == len(files)
        return meta, files, res


def T(*names):
    """Type ids are CRC32 of the type name (resource type_id and index ext alike)."""
    return {zlib.crc32(n.encode("ascii")) for n in names}


MESH, TEX, MIP, LOD, TSET = T("Mesh"), T("TextureMap"), T("CompiledMip"), T("LODSelector"), T("TextureSet")
ENTS, GRID = T("Entity", "EntityGroup"), T("GridCellDataBlock")
SHAPE_T, MESHSHAPE, CMAT = T(*SHAPES), T("MeshShape"), T("CollisionMaterial")


def refs_in(b, pool):
    """IDs from `pool` right after a reference prefix (or a 00 byte) anywhere in b, own ID excluded."""
    out = set()
    for o in range(1, len(b) - 7):
        v = U8(b, o)
        if v in pool and (b[o - 1] == 0 or (o >= 2 and b[o - 2:o] in rid.PREFIXES)):
            out.add(v)
    return out


def pos(o):
    return struct.unpack("<16f", o.f["GlobalMatrix"])[12:15]


def move(o, d):
    m = list(struct.unpack("<16f", o.f["GlobalMatrix"])); m[12] += d[0]; m[13] += d[1]; m[14] += d[2]
    o.f["GlobalMatrix"] = struct.pack("<16f", *m)
    for p in o.f.get("Entities", []):
        if p.obj is not None:
            move(p.obj, d)


def _components(o):
    yield from o.f["Components"]
    for p in o.f.get("Entities", []):
        if p.obj is not None:
            yield from _components(p.obj)


def content(o, out):
    kids = [c.obj for c in o.f.get("Entities", []) if c.obj is not None]
    if kids:
        for k in kids:
            content(k, out)
    else:
        out.append(pos(o))
    return out


# shape types with no layout here; a body reaching one loses its physics (names matched by CRC32)
OTHER_SHAPES = {zlib.crc32(n.encode()): n for n in ("CylinderShape", "SphereShape", "CompoundShape", "HeightFieldShape",
                                                     "ConvexListShape", "TriangleShape", "PlaneShape", "TransformShape",
                                                     "ScaledShape", "MultiSphereShape")}


def blob_ok(payload):
    """Does a GRW MeshShape's Havok blob convert to GRB's format?"""
    import havok_tag as ht
    try:
        w = ge.decode(payload, "grw").f["Wrapper"]; w = w.obj if isinstance(w, ge.Ptr) else w
        ht.convert(w.f["SerializedRawData"])
        return True
    except (ValueError, ge.NeedLayout, ge.Unsupported, struct.error):
        return False


def shape_of(cell, ext=None):
    """For grw_entities' strip_physics_at={"UNSUPPORTED"}: (type name, ReferenceListShape child IDs) for what a body
    can reach. Supported: SHAPES, and MeshShapes whose Havok blob converts, in the cell or in their own _RT entry
    (ext(id) -> True / False, or None when the ID is not a MeshShape entry). Other shape types are UNSUPPORTED; an ID
    found nowhere is None (a body Shape found nowhere strips that Entity's physics)."""
    known = {}
    for cid, r in cell.items():
        t = ge.NAMES.get(r.type_id) or OTHER_SHAPES.get(r.type_id) or f"#{r.type_id:08x}"; kids = []
        if t == "ReferenceListShape":
            kids = [p.id for p in ge.decode(r.payload, "grw").f["List"] if p.obj is None and p.id]
        elif t == "MeshShape":
            t = "MeshShape" if blob_ok(r.payload) else "UNSUPPORTED"
        elif t.endswith("Shape") and t not in SHAPES:
            t = "UNSUPPORTED"
        known[cid] = (t, kids)

    def f(i):
        if i in known:
            return known[i]
        ok = ext(i) if ext is not None else None
        return None if ok is None else ("MeshShape" if ok else "UNSUPPORTED", [])
    return f


def strip(o, dropped, keep=frozenset()):
    gone = STRIP - set(keep)
    left = [p for p in o.f["Components"] if not (p.obj is not None and p.obj.name in gone)]
    for p in o.f["Components"]:
        if p.obj is not None and p.obj.name in gone:
            dropped[p.obj.name] += 1
    if len(left) != len(o.f["Components"]) and "ResetData" in o.f:
        o.f["ResetData"] = ge.Ptr(3); dropped["ResetData nulled"] += 1
    o.f["Components"] = left
    for p in o.f.get("Entities", []):
        if p.obj is not None:
            strip(p.obj, dropped, keep)


class Ground:
    def __init__(self, path=None, origin=None, step=None, fallback=0.0, tbf_root=None):
        self.fallback = fallback
        self.g = None; self.hf = None
        if tbf_root:                                  # GRB terrain itself (tbf_read.Heightfield, verified 2026-10-10)
            import tbf_read
            self.hf = tbf_read.Heightfield(tbf_read.find_files(tbf_root, "tgt"))
        if path:
            import numpy as np
            self.g = np.load(path); self.x0, self.y0 = origin; self.s = step

    def z(self, x, y):
        if self.hf is not None:
            return float(self.hf.z(x, y))
        if self.g is None:
            return self.fallback
        fx, fy = (x - self.x0) / self.s, (y - self.y0) / self.s
        c, r = int(fx // 1), int(fy // 1)
        if not (0 <= r < self.g.shape[0] - 1 and 0 <= c < self.g.shape[1] - 1):
            raise SystemExit(f"({x:.1f}, {y:.1f}) is outside the ground grid")
        tx, ty = fx - c, fy - r
        a, b, cc, d = self.g[r, c], self.g[r, c + 1], self.g[r + 1, c], self.g[r + 1, c + 1]
        return float((a * (1 - tx) + b * tx) * (1 - ty) + (cc * (1 - tx) + d * tx) * ty)


def census_homes(census_dir, ids, ours):
    """{ID: [(forge, kind, entry id, type id, entry name, offset, length)]} for the IDs present anywhere in GRB per the
    full ClassID census (entries + inner resources), ignoring homes in forges our own test builds write. Streams the
    entry table and keeps only the lines it needs."""
    import numpy as np
    if not ids:
        return {}
    rows = np.fromfile(os.path.join(census_dir, "rows.bin"), dtype=np.dtype([("id", "<u8"), ("e", "<u4")]))
    sel = rows[np.isin(rows["id"], np.array(sorted(ids), dtype=np.uint64))]
    del rows
    want = collections.defaultdict(list)
    for i, e in zip(sel["id"].tolist(), sel["e"].tolist()):
        want[e].append(int(i))
    out = collections.defaultdict(list)
    for line in open(os.path.join(census_dir, "entries.tsv"), encoding="utf-8", errors="replace"):
        e = int(line.split("\t", 1)[0])
        if e in want:
            p = line.rstrip("\n").split("\t")
            if not any(o in p[1] for o in ours):
                for i in want[e]:
                    out[i].append(p[1:])
    return dict(out)


def census_hits(census_dir, ids, ours):
    """IDs present anywhere in GRB per the census (see census_homes). Optional; without it only the entry index is
    checked."""
    return set(census_homes(census_dir, ids, ours))


def shape_materials(o):
    """CollisionMaterial IDs a decoded shape references (Material field, MeshShape/Capsule triangle materials)."""
    out = []
    if isinstance(o.f.get("Material"), ge.Ptr) and o.f["Material"].id:
        out.append(o.f["Material"].id)
    for t in o.f.get("TriangleMaterialData", []):
        t = t.obj if isinstance(t, ge.Ptr) else t
        if t.f["Material"].id:
            out.append(t.f["Material"].id)
    return out


def convert_meshshape(payload, remap):
    """GRW MeshShape payload -> GRB: the layout via grw_entities (materials re-pointed per `remap`), the Havok blob via
    havok_tag (ValueError if it can't be converted)."""
    import havok_tag as ht
    o = ge.decode(ge.convert(payload, remap=remap or None), "grb")
    w = o.f["Wrapper"]; w = w.obj if isinstance(w, ge.Ptr) else w
    w.f["SerializedRawData"] = ht.convert(w.f["SerializedRawData"])
    return ge.encode(o, "grb")


def port(a):
    grw = Install(a.grw, a.oodle_grw)
    grb = Install(a.grb, a.oodle_grb, base_only=True)
    dll = os.path.join(a.grb, "oo2core_7_win64.dll")
    import reflex3_write as rw

    # material skeleton and synthesized-set layout, read from the installs (no game bytes in the repo)
    _, _, sres = grb.container(SKELETON[0], base=True)
    skel = next(r.payload for r in sres if di.class_id(r) == SKELETON[1])
    assert U8(skel, 15) == TEMPLATE
    _, lay_files, lres = grw.container(SET_LAYOUT[0])
    layout = next(r for r in lres if di.class_id(r) == SET_LAYOUT[1])
    assert layout.payload[13:15] == b"\x01\x02" and layout.payload[23:25] == b"\x01\x02" and layout.payload[33] == 3
    if a.materials == "learned":
        import grw_materials as gm

    # ------------------------------------------------ GRW cells -> converted, stripped objects
    objs, src, conv_lod, cellres, dropped = collections.OrderedDict(), {}, {}, {}, collections.Counter()
    rt_cache = {}                                    # GRW MeshShape entry -> (resource, files, convertible)

    def ext_shape(i):
        if i not in grw.index or grw.index[i][1] not in MESHSHAPE:
            return None
        if i not in rt_cache:
            _, f, res = grw.container(i)
            r = next((x for x in res if di.class_id(x) == i and x.type_id in MESHSHAPE), None)
            rt_cache[i] = (r, f, r is not None and blob_ok(r.payload))
        return rt_cache[i][2]
    for name in a.cells:
        cid = grw.by_name(name)
        _, cfiles, cres = grw.container(cid)
        cell = {di.class_id(r): r for r in cres}
        gc = ge.decode(next(r for r in cres if r.type_id in GRID).payload, "grw")
        shapes = shape_of(cell, ext_shape) if a.collision else None
        for oid in [p.id for p in gc.f["Objects"][:gc.f["NumberOfObjectsToActivate"]]]:
            r = cell.get(oid)
            if r is None or r.type_id not in ENTS:
                continue
            try:
                if a.collision:
                    out = ge.convert(r.payload, drop_grw_only=True, strip_physics_at={"UNSUPPORTED"},
                                     shape_of=shapes)
                else:
                    out = ge.convert(r.payload, drop_grw_only=True, strip_physics=True)
                o = ge.decode(out, "grb")
            except (ge.NeedLayout, ge.Unsupported) as e:
                print(f"  skip {r.name}: {e}"); continue
            strip(o, dropped, keep=COLLISION_KEEP if a.collision else ())
            objs[oid] = o; src[oid] = (r, cfiles)
        for r in cres:
            cellres[di.class_id(r)] = (r, cfiles)
            if r.type_id in LOD:
                conv_lod[di.class_id(r)] = ge.convert(r.payload)
    if not objs:
        raise SystemExit("nothing to bring")
    print(f"bringing {len(objs)} objects from {len(a.cells)} cell(s); stripped {dict(dropped)}")

    # ------------------------------------------------ placement
    if a.shift:
        # rigid: everything moves by one (dx, dy, dz), for a block whose GRW ground is laid in with the same shift
        # (tbf_patch.py build --shift); props keep their exact height above their own terrain
        for o in objs.values():
            move(o, a.shift)
    if not a.shift:
        ground = Ground(a.ground, a.ground_origin, a.ground_step, fallback=a.anchor[2],
                        tbf_root=a.grb if a.ground_tbf else None)
        every = [p for o in objs.values() for p in content(o, [])]
        cx = sum(p[0] for p in every) / len(every); cy = sum(p[1] for p in every) / len(every)
        dx, dy = a.anchor[0] + a.offset[0] - cx, a.anchor[1] + a.offset[1] - cy
    for oid, o in (objs.items() if not a.shift else ()):
        ps = content(o, [])
        mx = sum(p[0] for p in ps) / len(ps) + dx; my = sum(p[1] for p in ps) / len(ps) + dy
        move(o, (dx, dy, ground.z(mx, my) - min(p[2] for p in ps)))
        if (a.ground or a.ground_tbf) and src[oid][0].name.startswith("AutoGroup"):
            for c in o.f["Entities"]:
                if c.obj is not None and not c.obj.f.get("Entities"):
                    x, y, z = pos(c.obj); move(c.obj, (0.0, 0.0, ground.z(x, y) - z))
    for oid, o in objs.items():
        ps = content(o, [])
        print(f"   {src[oid][0].name[:44]:44s} {len(ps):3d} piece(s), first at ({ps[0][0]:.1f}, {ps[0][1]:.1f}, {ps[0][2]:.1f})")

    # ------------------------------------------------ reach
    top = {oid: ge.encode(o, "grb") for oid, o in objs.items()}
    pool = {i: r for i, (r, _) in cellres.items()}
    lods = {v for b in top.values() for v in refs_in(b, pool) if pool[v].type_id in LOD}
    local_m, ext_m = set(), set()
    for b in list(top.values()) + [conv_lod[l] for l in lods]:
        local_m |= {v for v in refs_in(b, pool) if pool[v].type_id in MESH}
        ext_m |= {v for v in refs_in(b, grw.index) if v not in pool and grw.index[v][1] in MESH}

    def tex_name(t):
        return grw.index[t][2] if t in grw.index else "?"

    synth = {}

    def material(mid, mpool):
        """-> list of (cid, files, resource, payload|('SET', grw payload)), textures used."""
        m = mpool[mid][0].payload
        sets = [v for v in refs_in(m, mpool) if mpool[v][0].type_id in TSET]
        sp = mpool[sets[0]][0].payload if sets else None

        def pick(b):
            texs = {v for v in refs_in(b, grw.index) if grw.index[v][1] in TEX} if b is not None else set()
            d = sorted(t for t in texs if "Diffuse" in tex_name(t) or "Albedo" in tex_name(t))
            n = sorted(t for t in texs if "Normal" in tex_name(t))
            return (d[0] if d else None), (n[0] if n else None)
        # the set holds the object's own maps; textures named in the material itself are shader inputs (terrain
        # blend, detail), used only where the set has no map of that kind
        sd, sn = pick(sp)
        md, mn = pick(m)
        d, n = sd or md, sn or mn
        r, files = mpool[mid]
        if a.materials == "learned":
            mat, ts, rep = gm.convert_pair(m, sp, {}, fallback=1498533326620)
            out = [(mid, files, r, mat)]
            if ts is not None:
                out.append((U8(ts, 0), lay_files, layout, ts))
            used = {v for v in refs_in(mat + (ts or b""), grw.index) if grw.index[v][1] in TEX}
            return out, used
        q = bytearray(g.transplant_material(skel, mid, {650: d or 0, 719: n if n is not None else DEFAULT_NORMAL}))
        out = [(mid, files, r, None)]
        if sets:
            sid = sets[0]; out.append((sid, mpool[sid][1], mpool[sid][0], ("SET", sp)))
        else:
            sid = mid | SYNTH_TAG
            s = bytearray(layout.payload); struct.pack_into("<Q", s, 0, sid); struct.pack_into("<Q", s, 15, d or 0)
            if n is not None:
                struct.pack_into("<Q", s, 25, n)
            else:
                s[23:33] = b"\x03" + bytes(9)
            synth[sid] = bytes(s); out.append((sid, lay_files, layout, bytes(s)))
        struct.pack_into("<Q", q, 25, sid)
        out[0] = (mid, files, r, bytes(q))
        return out, {t for t in (d, n) if t is not None}

    def mesh_payload(p):
        try:
            return g.convert_mesh(p)
        except Exception:
            return g.convert_mesh(p, drop_uv1=True)

    entries, mesh_tex = collections.OrderedDict(), collections.defaultdict(set)
    host_new = collections.OrderedDict((l, (pool[l], cellres[l][1], conv_lod[l])) for l in sorted(lods))
    rt_entries = collections.OrderedDict()           # MeshShape entries, GRB's _RT pattern: [shape, materials...]
    host_mats = collections.OrderedDict()            # GRB's own material copies for the inline shapes
    grb_refs, grb_owned = set(), set()               # GRB materials referenced as they are / shipped as GRB's copies
    if a.collision:
        if not a.census:
            raise SystemExit("--collision needs --census (GRB's collision materials are found through it)")
        local, ext = set(), set()
        for b in top.values():
            local |= {v for v in refs_in(b, pool) if pool[v].type_id in SHAPE_T | MESHSHAPE}
            ext |= {v for v in refs_in(b, grw.index) if v not in pool and ext_shape(v)}
        todo = list(local)
        while todo:                                  # ReferenceListShape children, in the cells or in _RT entries
            v = todo.pop()
            if ge.NAMES.get(pool[v].type_id) == "ReferenceListShape":
                for k in [p.id for p in ge.decode(pool[v].payload, "grw").f["List"] if p.obj is None and p.id]:
                    if k in pool and pool[k].type_id in SHAPE_T | MESHSHAPE:
                        if k not in local:
                            local.add(k); todo.append(k)
                    elif ext_shape(k):
                        ext.add(k)
        src_shape = {v: (pool[v], cellres[v][1]) for v in local}
        src_shape.update({v: rt_cache[v][:2] for v in ext})
        mats = {v: shape_materials(ge.decode(r.payload, "grw")) for v, (r, _f) in src_shape.items()}
        allm = set().union(*mats.values()) if mats else set()
        live_name = os.path.basename(a.patch_forge).replace(".forge", "")
        homes = census_homes(a.census, allm | {FALLBACK_MATERIAL}, (live_name, "GRN_GhostRoom", "Backups"))
        if FALLBACK_MATERIAL not in homes:
            raise SystemExit(f"fallback collision material {FALLBACK_MATERIAL:#x} is not in the GRB census")
        mremap = {m: FALLBACK_MATERIAL for m in allm if m not in homes}
        glob_m = {m for m in allm if m in homes and any(h[4].startswith("DBContainerEntry") for h in homes[m])}

        def donor(m):
            """GRB's own frames for CollisionMaterial m and its PhysicsCollisionMaterial, from one entry holding both."""
            for forge, kind, _fid, _ty, _nm, off, ln in sorted(homes[m], key=lambda h: h[1] == "backup")[:12]:
                try:
                    with open(os.path.join(a.grb, forge), "rb") as fh:
                        fh.seek(int(off)); blob = fh.read(int(ln))
                    _, df = di.read_container_bytes(blob, a.oodle_grb); dres, _ = di.walk(df)
                except Exception:
                    continue
                byid = {di.class_id(x): x for x in dres}
                r = byid.get(m)
                if r is None or r.type_id not in CMAT:
                    continue
                p = ge.decode(r.payload, "grb").f["Physics"].id
                if p in byid:
                    return [(m, df, r), (p, df, byid[p])]
            return None
        embed = {}
        for m in sorted(allm - set(mremap) - glob_m):
            d = donor(m)
            if d is None:
                mremap[m] = FALLBACK_MATERIAL
            else:
                embed[m] = d
        grb_refs |= glob_m | {FALLBACK_MATERIAL}
        grb_owned |= {c for d in embed.values() for c, _f, _r in d}
        for v, (r, f) in sorted(src_shape.items()):
            rm = {k: mremap[k] for k in mats[v] if k in mremap}
            used = [m for m in dict.fromkeys(mats[v]) if m in embed]
            if r.type_id in MESHSHAPE:
                frames = [(v, f, r, convert_meshshape(r.payload, rm))]
                for m in used:
                    frames += [(c, df, dr, dr.payload) for c, df, dr in embed[m] if c not in [x[0] for x in frames]]
                rt_entries[v] = frames
            else:
                host_new[v] = (r, f, ge.convert(r.payload, remap=rm or None))
                for m in used:
                    for c, df, dr in embed[m]:
                        host_mats.setdefault(c, (dr, df, dr.payload))
        kept = collections.Counter(c.obj.name for o in objs.values() for c in _components(o)
                                   if c.obj is not None and c.obj.name in COLLISION_KEEP)
        print(f"collision: kept {dict(kept)}; {len(local) - sum(1 for v in local if pool[v].type_id in MESHSHAPE)} "
              f"shapes inline, {len(rt_entries)} MeshShape entries; materials: {len(embed)} as GRB's own copies, "
              f"{len(glob_m)} global, {len(mremap)} re-pointed at {FALLBACK_MATERIAL:#x}")
    for mid in sorted(local_m) + sorted(ext_m):
        if mid in pool:
            mpool = {i: v for i, v in cellres.items()}; mr, mf = cellres[mid]
        else:
            rec = grw.index[mid]; _, mf, mres = grw.container(mid)
            mpool = {di.class_id(x): (x, mf) for x in mres}; mr = mpool[mid][0]
        frames = [(mid, mf, mr, mesh_payload(mr.payload))]
        for mat in g.mesh_materials(mr.payload):
            fr, used = material(mat, mpool)
            mesh_tex[mid] |= used
            for f in fr:
                if f[0] not in [x[0] for x in frames]:
                    frames.append(f)
        entries[mid] = frames
    textures = set().union(*mesh_tex.values()) if mesh_tex else set()

    # per-instance material overrides (GRW rocks re-skinned to blend with the terrain, BLE_*_TER-*#): the meshes keep
    # their own materials; the overriding materials live in the GRW cell and are not brought
    shipped_m = {c for fr in entries.values() for c, *_ in fr}
    mat_t = T("Material")

    def unshipped(i):
        return i not in shipped_m and ((i in pool and pool[i].type_id in mat_t) or
                                       (i in grw.index and grw.index[i][1] in mat_t))
    gone_over = collections.Counter()

    def drop_overrides(o):
        hit = False
        if o.name == "MeshInstanceMaterialInfo":
            mm, im = o.f["MeshMaterial"], o.f["InstanceMaterial"]
            if im.obj is None and im.id and im.id != mm.id and unshipped(im.id):
                # MeshMaterial is a handle (u8 0 + id), InstanceMaterial a ref (u8 1, u8 0, id)
                o.f["InstanceMaterial"] = ge.Ptr(1, 0, mm.id); gone_over["instance materials"] += 1; hit = True
        if "Components" in o.f:
            keep = []
            for c in o.f["Components"]:
                if c.obj is not None and c.obj.name == "MaterialOverrider":
                    defs = c.obj.f["MaterialOverrides"]
                    left = [d for d in defs if not unshipped((d.obj if isinstance(d, ge.Ptr) else d).f["NewMaterial"].id)]
                    gone_over["overrides"] += len(defs) - len(left)
                    if len(left) != len(defs):
                        hit = True; c.obj.f["MaterialOverrides"] = left
                    if not left:
                        gone_over["MaterialOverrider"] += 1
                        if "ResetData" in o.f:
                            o.f["ResetData"] = ge.Ptr(3)
                        continue
                keep.append(c)
            o.f["Components"] = keep
        for v in o.f.values():
            for p in (v if isinstance(v, list) else [v]):
                if isinstance(p, ge.Ptr) and p.obj is not None:
                    hit |= drop_overrides(p.obj)
                elif isinstance(p, ge.Obj):
                    hit |= drop_overrides(p)
        return hit
    for oid, o in objs.items():
        if drop_overrides(o):
            top[oid] = ge.encode(o, "grb")
    if gone_over:
        print(f"material overrides dropped (meshes keep their own): {dict(gone_over)}")

    def convert_set(sp):
        # slots are 10 bytes from 13: u8 1, u8 rtype, u64 id, or u8 3 + 9 zero bytes (null). GRW writes rtype 2 in
        # cell copies and 1 in mesh-entry copies of the same set; both are kept as they are
        q = bytearray(sp)
        for o in range(13, len(q) - 9, 10):
            if q[o:o + 2] in (b"\x01\x01", b"\x01\x02"):
                if U8(q, o + 2) not in textures:
                    q[o:o + 10] = b"\x03" + bytes(9)
            elif q[o] != 3:
                break
        return bytes(q)

    for mid, frames in entries.items():
        entries[mid] = [(c, f, r, convert_set(p[1]) if isinstance(p, tuple) else p) for c, f, r, p in frames]
    mips = set()
    for t in sorted(textures):
        _, tf, tres = grw.container(t); r = next(x for x in tres if di.class_id(x) == t)
        entries[t] = [(t, tf, r, g.convert_texture(r.payload))]
        for m in g.texture_top_mips(r.payload):
            if m in grw.index:
                _, mf, mres = grw.container(m); mr = next(x for x in mres if di.class_id(x) == m)
                entries[m] = [(m, mf, mr, mr.payload)]; mips.add(m)
    print(f"reach: {len(lods)} LODSelectors, {len(entries) - len(textures) - len(mips)} mesh entries, "
          f"{len(textures)} textures, {len(mips)} mips")

    # ------------------------------------------------ host + re-ID
    hid = grb.by_name(a.host, base=True)
    hmeta, hfiles, hres = grb.container(hid, base=True)
    host_ids = {di.class_id(r) for r in hres}
    shipped = set(objs) | set(host_new) | set(entries) | {c for fr in entries.values() for c, *_ in fr} | \
        set(rt_entries) | {c for fr in rt_entries.values() for c, *_ in fr}
    inner = set()

    def walk(o):
        inner.add(o.id)
        for v in o.f.values():
            for p in (v if isinstance(v, list) else [v]):
                if isinstance(p, ge.Ptr) and p.obj is not None:
                    walk(p.obj)
                elif isinstance(p, ge.Obj):
                    walk(p)
    for o in objs.values():
        walk(o)
    # vanilla GRB = base forges + every patch except the live one we replace (it may hold earlier test builds)
    live = os.path.basename(a.patch_forge)
    vanilla = set(grb.base)
    for pth in glob.glob(os.path.join(a.grb, "*.forge")) + glob.glob(os.path.join(a.grb, "dlc_*", "*.forge")):
        if "_patch_" in pth and os.path.basename(pth) != live:
            vanilla |= {fid for fid, ext, _n, _o, _l in fi.forge_entries(pth) if ext}
    # GRB's own material copies keep their IDs (GRB itself embeds the same material in thousands of entries)
    cand = {i for i in shipped | inner if i is not None and not ge.is_anon(i)} - grb_owned - grb_refs
    collide = {i for i in cand if i in vanilla or i in host_ids}
    if a.census:
        collide |= census_hits(a.census, cand, (live.replace(".forge", ""), "GRN_GhostRoom", "Backups"))
    remap = {i: rid.reid(i) for i in collide}
    assert not (set(remap.values()) & (vanilla | host_ids | shipped))
    R = lambda i: remap.get(i, i)
    print(f"re-ID: {len(remap)}")

    fl = []
    for r in hres:
        p = r.payload
        if r.type_id in GRID:
            o = ge.decode(p, "grb"); k = o.f["NumberOfObjectsToActivate"]
            o.f["Objects"][k:k] = [ge.Ptr(1, 0, R(i)) for i in objs]
            o.f["NumberOfObjectsToActivate"] = k + len(objs)
            p = ge.encode(o, "grb")
        fl.append((di.class_id(r), g.frame(hfiles, r, p)))
    nhost = len(fl)
    for oid in objs:
        r, files = src[oid]; fl.append((R(oid), g.frame(files, r, rid.rewrite(top[oid], remap)[0])))
    for cid, (r, files, p) in host_new.items():
        fl.append((R(cid), g.frame(files, r, rid.rewrite(p, remap)[0])))
    for cid, (r, files, p) in host_mats.items():
        if cid not in host_ids:
            fl.append((cid, g.frame(files, r, p)))
    files_out = b"".join(fb for _, fb in fl)
    m = bytes(hmeta); n = struct.unpack_from("<H", m, 0)[0]; o = 2; rows = []
    for _ in range(n):
        cid, size, k = struct.unpack_from("<QiH", m, o); rows.append((cid, m[o + 14:o + 14 + 2 * k])); o += 14 + 2 * k
    assert o == len(m) and [c for c, _ in rows] == [c for c, _ in fl[:nhost]]
    meta_out = struct.pack("<H", len(fl)) + b"".join(
        struct.pack("<QiH", c, len(fb), len(deps) // 2) + deps for (c, fb), (_, deps) in zip(fl[:nhost], rows)) + b"".join(
        struct.pack("<QiH", c, len(fb), 0) for c, fb in fl[nhost:])
    host_cc = rw._compress_cfd(meta_out, dll) + rw._compress_cfd(files_out, dll)
    m2, f2 = di.read_container_bytes(host_cc, a.oodle_grb); assert m2 == meta_out and f2 == files_out

    entry_files = collections.OrderedDict()
    for eid, frames in list(entries.items()) + list(rt_entries.items()):
        entry_files[R(eid)] = (frames[0][2], g.build_container(
            [(R(c), g.frame(f, r, rid.rewrite(p, remap)[0])) for c, f, r, p in frames], dll, a.oodle_grb))

    # ------------------------------------------------ reference check
    res2, _ = di.walk(f2)
    resolvable = vanilla | {di.class_id(r) for r in res2} | set(entry_files) | grb_refs | grb_owned | {0}
    ent_res = []
    for eid, (_, b) in entry_files.items():
        _, f3 = di.read_container_bytes(b, a.oodle_grb); ent_res += di.walk(f3)[0]
    resolvable |= {di.class_id(x) for x in ent_res}
    grw_ids = set(grw.index) | set(pool) | set(remap.values())
    dangling = collections.Counter()
    for r in list(res2[nhost:]) + ent_res:
        if r.type_id in MESH | TEX | MIP:
            continue
        if r.type_id in MESHSHAPE:                   # its Havok blob is not scanned; its materials are checked decoded
            refs = set(shape_materials(ge.decode(r.payload, "grb")))
        else:
            refs = refs_in(r.payload, grw_ids)
        for v in refs:
            if v not in resolvable and v != di.class_id(r):
                dangling[(f"{tn(r.type_id)} {r.name}", v)] += 1
    if dangling:
        def what(v):
            if v in pool:
                return f"{tn(pool[v].type_id)} {pool[v].name}"
            return f"{tn(grw.index[v][1])} {grw.index[v][2]}" if v in grw.index else "?"
        for (t, v), c in sorted(dangling.items()):
            print(f"   {t} -> {v} ({what(v)}) x{c}")
        raise SystemExit(f"{len(dangling)} dangling reference(s)")

    # ------------------------------------------------ 145
    praw = pi.read_pfi(a.patch_forge) if a.patch_forge.lower().endswith(".forge") else open(a.patch_forge, "rb").read()
    prows, pdata = pw.parse(praw)
    hrec = pw.record_of(praw, hid)
    if hrec is None:
        hrec = pw.record_of(pi.read_pfi(grb.base[hid][0]), hid)
    hrec = bytearray(hrec)
    nh = struct.unpack_from("<H", hrec, 0)[0]; ko = 2 + 11 * nh; k = struct.unpack_from("<H", hrec, ko)[0]
    present = []

    def tree(r, o, k):
        for _ in range(k):
            present.append(U8(r, o)); t1 = r[o + 9]; o += 11
            if t1 == 1:
                mm = struct.unpack_from("<H", r, o)[0]; o = tree(r, o + 2, mm)
            elif t1 != 0:
                raise SystemExit(f"host prefetch record has an undecoded child kind {t1}")
        return o
    assert tree(hrec, ko + 2, k) == len(hrec)
    meshes = [mid for mid in entries if mid not in textures and mid not in mips]
    # GRB cells list their bodies' _RT MeshShape entries like meshes (tail 01 00 00); an _RT entry's own record is empty
    add = [(R(mid), b"\x01\x00\x00") for mid in meshes + list(rt_entries) if R(mid) not in present]
    hrec[ko:ko + 2] = struct.pack("<H", k + len(add)); hrec += b"".join(P8(i) + t for i, t in add)
    records = {R(mid): pw.make_record([(TEMPLATE, pw.TAIL_TEMPLATE)] +
                                      [(R(t), pw.TAIL_TEXTURE) for t in sorted(mesh_tex[mid])]) for mid in meshes}
    records.update({R(i): pw.make_record([]) for i in textures | mips | set(rt_entries)})
    if any(f == hid for f, _, _ in prows):
        rows_ = [(f, (len(hrec) if f == hid else s), (len(pdata) if f == hid else o)) for f, s, o in prows]
        base = pw.wrap(pw.build(rows_, bytes(pdata) + bytes(hrec)))
    else:
        base, records[hid] = praw, bytes(hrec)
    new_pfi = pw.add_raw(base, records)
    assert all(pw.check_blocks(new_pfi))

    # ------------------------------------------------ write
    order = [(fid, name) for fid, _e, name, _o, _l in fi.forge_entries(a.patch_forge)] if a.patch_forge.lower().endswith(".forge") else None
    if order is None:
        raise SystemExit("--patch-forge must be the vanilla patch .forge (numbers the output files)")
    pfi_idx = next(i for i, (fid, _) in enumerate(order) if fid == 145)
    os.makedirs(a.out, exist_ok=True)

    def safe(s):
        return "".join("_" if c in '<>:"/\\|?*' else c for c in s)
    written = [(f"{pfi_idx}_-_PrefetchingFileInfos.PrefetchInfo", new_pfi),
               (f"{len(order)}_-_{safe(a.host)}.data", host_cc)]
    for k, (eid, (r, b)) in enumerate(entry_files.items()):
        written.append((f"{len(order) + 1 + k}_-_{safe(r.name)}.data", b))
    if not a.dry:
        for nm, b in written:
            open(os.path.join(a.out, nm), "wb").write(b)
    print(f"host {len(hres)} -> {len(res2)} resources; {len(entry_files)} new entries; 145 +{len(records)} records "
          f"(host record +{len(add)} deps); dangling 0; {'dry run' if a.dry else f'wrote {len(written)} files to {a.out}'}")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("port")
    p.add_argument("cells", nargs="+")
    p.add_argument("--host", required=True, help="GRB host cell entry name, e.g. Cell45147_DataBlock")
    p.add_argument("--patch-forge", required=True, help="the VANILLA _patch_01 forge of the host's world (a backup)")
    fl3 = lambda s: tuple(float(v) for v in s.split(","))
    p.add_argument("--anchor", type=fl3, help="x,y[,z] in GRB world metres (z = fallback ground)")
    p.add_argument("--shift", type=fl3, help="dx,dy,dz: move everything rigidly (GRW -> GRB metres) instead of "
                                            "anchoring and seating; pair with tbf_patch.py build --shift")
    p.add_argument("--offset", type=fl3, default=(0.0, 0.0), help="dx,dy from the anchor to the cells' content centre")
    p.add_argument("--ground"); p.add_argument("--ground-origin", type=fl3); p.add_argument("--ground-step", type=float)
    p.add_argument("--ground-tbf", action="store_true", help="sample GRB's own terrain (.tbf) instead of a grid")
    p.add_argument("--census", help="GRB ClassID census dir (rows.bin + entries.tsv) for inner-ID collisions")
    p.add_argument("--materials", choices=("clone", "learned"), default="clone")
    p.add_argument("--collision", action="store_true",
                   help="keep static collision: primitive shapes inline, MeshShapes as converted _RT entries (needs --census)")
    p.add_argument("--grw", default=os.environ.get("GRW_INSTALL", GRW_DEFAULT))
    p.add_argument("--grb", default=os.environ.get("GRB_INSTALL", GRB_DEFAULT))
    p.add_argument("--max-mb", type=int, default=2000)
    p.add_argument("--dry", action="store_true")
    p.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv[1:])
    if bool(a.anchor) == bool(a.shift):
        raise SystemExit("pass exactly one of --anchor (seat on GRB ground) and --shift (rigid move)")
    if a.anchor and len(a.anchor) == 2:
        a.anchor = (a.anchor[0], a.anchor[1], 0.0)
    if a.shift and len(a.shift) != 3:
        raise SystemExit("--shift takes dx,dy,dz")
    g.memory_cap(a.max_mb)
    a.oodle_grb = a.oodle_grw = di.Oodle(os.path.join(a.grb, "oo2core_7_win64.dll"))
    if not a.oodle_grb.ok:
        raise SystemExit(f"Oodle DLL not found in {a.grb} (pass --grb <GRB install>)")
    return port(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
