#!/usr/bin/env python3
"""
rig_census.py - which bone-physics rigs actually MOVE a mesh?

GRB's Reflex3 bone physics is the re-bindable half of secondary motion: a mesh
follows a rig by weight painting, while a cloth is welded to one mesh's vertices.
So the question route 2B lives or dies on is *which rigs does vanilla actually
drive a mesh with?* A rig can carry 43 KB of constraints and move nothing, if no
mesh is weighted to the bones those constraints drive - which is exactly what
`Tsec_Trench_AddonSkeleton` turned out to be on 2026-09-16.

This answers it for every rig assigned in a container, by joining three things
that had only ever been joined by hand:

    BuildTable row  ->  Skeleton handle (the rig)       entity_skeletons.py
                    ->  GraphicObject handle(s)         (the meshes)
    Skeleton        ->  Reflex3 driven bones            reflex3.py
    Mesh            ->  Joint4 weights per bone         ATK, via atk_bridge.py

    python rig_census.py --install "H:/SteamLibrary/steamapps/common/Ghost Recon Breakpoint"
    python rig_census.py --install <GRB> 28398_-_TEAMMATE_Template.data --csv out.csv
    python rig_census.py --install <GRB> --all-lods --grep Hair

With no container arguments it does TEAMMATE_Template and PLAYER_Template, which
between them hold every player-wearable item's table.

READ-ONLY. Containers are read straight out of the forges - nothing is unpacked,
nothing is written, no forge is opened for writing.

WHY THE ROW MATTERS, NOT THE TABLE. A table like Hats_forREGULAR holds hundreds
of rows, each a different hat with its own rig and its own mesh. Grouping per
table would pair every hat's mesh with every hat's rig and invent motion that is
not there, so this reads rows through ATK's own BuildTable reader and pairs only
within a row.

WHAT "MOVES" MEANS HERE. A Reflex3 record's head is `u32 BoneID | u32 ParentBoneID`,
both CRC32 of the exact-case bone name (verified 2026-08-14). BoneID is the
*constrained* bone - the one that swings. A mesh moves with the rig only if its
vertices carry weight on those bones; weight on a *parent* means the mesh hangs
off the chain's anchor and stays put. So the verdict counts weight entries on
record-head bones only, and reports parent-only weight separately.

LIMITS, stated rather than hidden:
  * LOD0 only unless --all-lods. On the trench coat all five LODs agreed.
  * A GraphicObject handle usually points at a LODSelector. ATK's own LODSelector
    reader FAILS on GRB (Failed=True, every LOD null), so the mesh IDs are
    recovered by scanning the LODSelector payload for 64-bit values that are Mesh
    containers - which found all five kilt LODs, LOD0 included.
  * The Joint block's offset inside a vertex is PARSED from `VertexFormat` and
    cross-checked against ATK's own decode, never assumed. GRB garments use at
    least strides 32, 36 and 48 with the joints at 24, 24 and 32 - a fixed offset
    reads a stride-48 backpack's normals as weights and calls a fully skinned
    mesh unweighted. On any disagreement the mesh is re-read vertex by vertex
    through ATK's `PackedJoints`, and the row says so.
  * Only rigs that are ASSIGNED by a table in the containers given are counted.
    A physics rig nothing assigns cannot appear.
  * Record heads only. Types 9 and 11 carry a count and constrain up to twelve
    bones per record (the 2026-09-20 grammar); this counts each record's head.
    Counting every one raised 115 of 148 rigs' driven counts and changed no
    verdict (checked 2026-09-22).
"""
import sys, os, re, glob, struct, zlib, collections, time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import data_inspect as di                                          # noqa: E402
import forge_inspect as fi                                         # noqa: E402
import reflex3                                                     # noqa: E402
import atk_bridge as ab                                            # noqa: E402

SKELETON_TYPE_ID = zlib.crc32(b"Skeleton")            # 615435132
GRAPHIC_TYPE_ID = zlib.crc32(b"GraphicObject")        # 3966419799
SOFTBODY_TYPE_ID = zlib.crc32(b"SoftBody")            # 1263847064
BUILDTABLE_TYPE_ID = zlib.crc32(b"BuildTable")
MESH_TYPE_ID = zlib.crc32(b"Mesh")
HANDLE = 0x00120000                                   # DynamicProperty Type

ATK_MESH = "AnvilToolkit.FileTypes.AnvilNext.Models.Mesh"
ATK_BUILDTABLE = "AnvilToolkit.FileTypes.AnvilNext.Tables.BuildTable"

DEFAULT_CONTAINERS = ("TEAMMATE_Template", "PLAYER_Template")


class Install:
    """A GRB install indexed by 64-bit ID, reading containers out of the forges."""

    def __init__(self, root):
        self.root = root
        # find_oodle walks up from the DIRNAME of what it is given, so hand it a
        # path inside the install rather than the install itself
        self.oodle = di.Oodle(di.find_oodle(os.path.join(root, "_")))
        if not self.oodle.ok:
            raise SystemExit("no Oodle DLL found next to the install")
        self.by_id = {}
        self.by_name = {}
        # base forges first, patches after, so a patched entry wins the key
        forges = sorted(glob.glob(os.path.join(root, "*.forge")),
                        key=lambda p: ("patch" in os.path.basename(p).lower(), p))
        self.forges = forges
        for forge in forges:
            try:
                entries = list(fi.forge_entries(forge))
            except Exception:
                continue
            for fid, ext, name, off, ln in entries:
                rec = (forge, ext, name, off, ln)
                self.by_id[fid] = rec
                self.by_name[name] = rec

    def raw(self, cid=None, name=None):
        rec = self.by_id.get(cid) if cid is not None else self.by_name.get(name)
        if rec is None:
            return None, None
        forge, _ext, _nm, off, ln = rec
        with open(forge, "rb") as f:
            f.seek(off)
            return f.read(ln), rec

    def files_block(self, cid=None, name=None):
        raw, rec = self.raw(cid, name)
        if raw is None:
            return None, None
        try:
            _meta, files = di.read_container_bytes(raw, self.oodle)
        except Exception:
            return None, rec
        return files, rec

    def resources(self, cid=None, name=None):
        files, rec = self.files_block(cid, name)
        if files is None:
            return [], rec, False
        try:
            res, end = di.walk(files)
        except Exception:
            return [], rec, False
        return res, rec, end == len(files)


# ---------------------------------------------------------------- rigs

_RIG_CACHE = {}


def rig_physics(inst, cid):
    """{name, physics, driven, parents, bones} for a Skeleton, or None when it
    carries no Reflex3 constraint data."""
    if cid in _RIG_CACHE:
        return _RIG_CACHE[cid]
    files, rec = inst.files_block(cid)
    out = None
    if files is not None:
        blob, bones = reflex3.blob_from_files(files)
        if blob and len(blob) > 8:
            driven, parents, broke = set(), set(), False
            for r in reflex3.parse_blob(blob):
                if r.get("error"):
                    broke = True
                    break
                if r.get("bone") is not None:
                    driven.add(r["bone"])
                if r.get("parent_bone") is not None:
                    parents.add(r["parent_bone"])
            out = {"name": rec[2], "physics": len(blob), "driven": driven,
                   "parents": parents - driven, "bones": bones, "partial": broke}
    _RIG_CACHE[cid] = out
    return out


# ---------------------------------------------------------------- meshes

_GFX_CACHE = {}
_MESH_CACHE = {}


def meshes_behind(inst, cid):
    """The Mesh ClassIDs a GraphicObject handle resolves to.

    Direct when the handle already names a Mesh; otherwise the handle is a
    LODSelector, whose payload is scanned for 64-bit values that are Mesh
    containers. Returns [] when nothing resolves."""
    if cid in _GFX_CACHE:
        return _GFX_CACHE[cid]
    rec = inst.by_id.get(cid)
    if rec is not None and rec[1] == MESH_TYPE_ID:
        _GFX_CACHE[cid] = [cid]
        return _GFX_CACHE[cid]
    res, _rec, _ok = inst.resources(cid)
    out, seen = [], set()
    for r in res:
        if di.class_id(r) != cid:
            continue
        pay = r.payload
        for off in range(0, max(0, len(pay) - 8)):
            v, = struct.unpack_from("<Q", pay, off)
            if v in seen or v < (1 << 30) or v > (1 << 48):
                continue
            e = inst.by_id.get(v)
            if e is not None and e[1] == MESH_TYPE_ID:
                seen.add(v)
                out.append(v)
    _GFX_CACHE[cid] = out
    return out


_ELEM = re.compile(r"^([A-Za-z]+?)(\d+)(us|ui|ub|s|f|b|i)?$")
_UNIT = {"s": 2, "f": 4, "ub": 1, "b": 1, "us": 2, "ui": 4, "i": 4, None: 1}


def joint_offset(fmt, stride):
    """Byte offset of the Joint block inside a vertex, or None.

    `VertexFormat` is a name like `Pos3s_Col1s_Norm3ub_Col1ub_Tan4ub_Binorm4ub_
    Tex2s_Joint4_Col4ub`: each token is <what><count><unit>, and `JointN` is N
    index bytes followed by N weight bytes. Offsets are NOT fixed across
    garments - assuming the Walker coat's 24/28 reads a backpack's normals as
    weights and reports a fully-skinned mesh as unweighted. Returns None unless
    the parsed tokens add up to the mesh's own stride, so a token this does not
    know falls back rather than guessing."""
    off, joint_at, n_joints = 0, None, 0
    for tok in str(fmt).split("_"):
        m = _ELEM.match(tok)
        if not m:
            return None, 0
        what, count, unit = m.group(1), int(m.group(2)), m.group(3)
        if what.lower().startswith("joint"):
            joint_at, n_joints = off, count
            off += count * 2                          # indices, then weights
        else:
            off += count * _UNIT.get(unit, 1)
    if off != int(stride):
        return None, 0
    return joint_at, n_joints


def mesh_weights(inst, cid):
    """(Counter{bone_hash: weight entries}, vertex count, note) for one Mesh."""
    if cid in _MESH_CACHE:
        return _MESH_CACHE[cid]
    res, _rec, _ok = inst.resources(cid)
    hit = next((r for r in res if di.class_id(r) == cid
                and di.type_name(r.type_id) == "Mesh"), None)
    if hit is None:
        hit = next((r for r in res if di.type_name(r.type_id) == "Mesh"), None)
    if hit is None:
        _MESH_CACHE[cid] = (collections.Counter(), 0, "no Mesh resource")
        return _MESH_CACHE[cid]
    try:
        mesh = ab.read_object(hit.header, hit.payload, ATK_MESH)
        fmt = str(mesh.VertexFormat)
        stride = int(mesh.VertexStride)
        vb = bytes(mesh.VertexBuffer)
        bones = [int(b.Name) for b in mesh.Bones]
        nverts = int(mesh.Vertices.Count)
    except Exception as exc:
        _MESH_CACHE[cid] = (collections.Counter(), 0, f"unreadable: {str(exc)[:50]}")
        return _MESH_CACHE[cid]
    if "Joint" not in fmt or not bones:
        _MESH_CACHE[cid] = (collections.Counter(), nverts, f"unskinned ({fmt})")
        return _MESH_CACHE[cid]

    counts = collections.Counter()
    at, nj = joint_offset(fmt, stride) if stride > 0 and vb else (None, 0)
    note = ""
    if at is not None:
        n = len(vb) // stride
        for k in range(n):
            b = k * stride
            for i in range(nj):
                if vb[b + at + nj + i]:               # weight byte
                    j = vb[b + at + i]                # joint index
                    if j < len(bones):
                        counts[bones[j]] += 1
        # cross-check the fast path against ATK's own decode on a few vertices
        if not _agrees(mesh, at, nj, stride, vb, nverts):
            counts, note = collections.Counter(), ""
            at = None
    if at is None:                                    # ATK decodes every vertex
        for k in range(nverts):
            j = mesh.Vertices[k].Joints
            idx, wts = j.Indices, list(j.Weights)
            for i in range(min(len(idx), len(wts))):
                if wts[i] and idx[i] < len(bones):
                    counts[bones[idx[i]]] += 1
        note = "via ATK per-vertex"
    _MESH_CACHE[cid] = (counts, nverts, note)
    return _MESH_CACHE[cid]


def _agrees(mesh, at, nj, stride, vb, nverts, probe=3):
    """Does the buffer-offset decode match ATK's own for the first few vertices?"""
    for k in range(min(probe, nverts, len(vb) // stride if stride else 0)):
        b = k * stride
        mine = [vb[b + at + i] for i in range(nj)]
        try:
            theirs = list(mesh.Vertices[k].Joints.Indices)[:nj]
        except Exception:
            return False
        if mine != [int(x) for x in theirs]:
            return False
    return True


# ---------------------------------------------------------------- the join

def resource_by_id(inst, cid):
    """Any resource, by ClassID, even one nested inside someone else's container.

    The forge index only knows a container's FIRST resource, and 89.5% of GRB's
    resources are not that (census, 2026-09-16). ATK's game file list does know
    them all, and its path is literally forge / container / resource - so when
    the direct lookup misses, the container name comes from there."""
    rec = inst.by_id.get(cid)
    if rec is not None:
        res, _r, _ok = inst.resources(cid)
        hit = next((r for r in res if di.class_id(r) == cid), None)
        if hit is not None:
            return hit
    try:
        path = _file_ref(cid)
    except Exception:
        return None
    parts = str(path).replace("/", "\\").split("\\")
    if len(parts) < 2 or parts[-1] == str(cid):
        return None
    res, _r, _ok = inst.resources(name=parts[-2])
    return next((r for r in res if di.class_id(r) == cid), None)


def _file_ref(cid):
    """ATK's own forge/container/resource path for a 64-bit ID."""
    System = ab._state["System"]
    m = ab.T("AnvilToolkit.Utils.GameFileList").GetMethod("GetFileReference")
    return m.Invoke(None, [System.UInt64(cid)])


_SUB_CACHE = {}


def subtable_graphics(inst, cid):
    """The GraphicObject handles in a sub-table's rows.

    A garment's mesh is not always in the row that names the rig: the Walker
    coat's mesh and cloth sit in `TP_TACVEST_Walker_Coat_Cloth`, a sub-table of
    `TP_VestMedium_Walker`. One level only - deeper nesting is not followed."""
    if cid in _SUB_CACHE:
        return _SUB_CACHE[cid]
    out = []
    hit = resource_by_id(inst, cid)
    if hit is not None and di.type_name(hit.type_id) == "BuildTable":
        try:
            bt = ab.read_object(hit.header, hit.payload, ATK_BUILDTABLE)
            for row in bt.BuildRows:
                for kv in row.Components:
                    c = kv.Value
                    if int(c.Type) == HANDLE and int(c.DataType) == GRAPHIC_TYPE_ID:
                        h = c.Value
                        v = int(h.Value) if h is not None and hasattr(h, "Value") else 0
                        if v:
                            out.append(v)
        except Exception:
            pass
    _SUB_CACHE[cid] = out
    return out


def rows_of(inst, container_name, limit=None):
    """Yield (table_name, row_index, [rigs], [graphic objects], [cloths])."""
    res, _rec, complete = inst.resources(name=container_name)
    if not res:
        print(f"  ! {container_name}: not found in this install")
        return
    if not complete:
        print(f"  ! {container_name}: the container walk did not reach the last "
              f"byte - refusing to census a partial list")
        return
    tables = [r for r in res if di.type_name(r.type_id) == "BuildTable"]
    # cheap byte filter first: only tables that mention a Skeleton Handle at all
    prefix = struct.pack("<III", SKELETON_TYPE_ID, HANDLE, 0)
    tables = [t for t in tables if prefix in t.payload]
    if limit:
        tables = tables[:limit]
    print(f"  {container_name}: {len(res):,} resources, "
          f"{len(tables):,} BuildTables assign a Skeleton")
    for t in tables:
        try:
            bt = ab.read_object(t.header, t.payload, ATK_BUILDTABLE)
            rows = list(bt.BuildRows)
        except Exception as exc:
            print(f"    ! {t.name}: unreadable ({str(exc)[:60]})")
            continue
        for i, row in enumerate(rows):
            rigs, gfx, cloth, subs = [], [], [], []
            for kv in row.Components:
                c = kv.Value
                if int(c.Type) != HANDLE:
                    continue
                h = c.Value
                v = int(h.Value) if h is not None and hasattr(h, "Value") else 0
                if not v:
                    continue
                dt = int(c.DataType)
                if dt == SKELETON_TYPE_ID:
                    rigs.append(v)
                elif dt == GRAPHIC_TYPE_ID:
                    gfx.append(v)
                elif dt == SOFTBODY_TYPE_ID:
                    cloth.append(v)
                elif dt == BUILDTABLE_TYPE_ID:
                    subs.append(v)
            if rigs:
                for s in subs:
                    gfx.extend(subtable_graphics(inst, s))
                yield t.name, i, rigs, gfx, cloth


def census(inst, containers, all_lods=False, limit=None, grep=None):
    """{rig_class_id: aggregate} over every row that assigns a physics rig."""
    agg = {}
    for cname in containers:
        for table, _ri, rigs, gfx, cloth in rows_of(inst, cname, limit):
            meshes = []
            for g in gfx:
                for m in meshes_behind(inst, g):
                    nm = inst.by_id.get(m, (None, None, ""))[2]
                    if all_lods or nm.endswith("_LOD0") or "_LOD" not in nm:
                        meshes.append(m)
            for rig in rigs:
                info = rig_physics(inst, rig)
                if info is None:
                    continue
                if grep and grep.lower() not in (info["name"] + table).lower():
                    continue
                a = agg.setdefault(rig, {
                    "name": info["name"], "physics": info["physics"],
                    "driven": info["driven"], "parents": info["parents"],
                    "partial": info["partial"], "tables": set(), "rows": 0,
                    "meshes": {}, "best": 0, "best_mesh": "", "parent_only": 0,
                    "cloth_rows": 0, "notes": set()})
                a["tables"].add(table)
                a["rows"] += 1
                if cloth:
                    a["cloth_rows"] += 1
                for m in meshes:
                    if m in a["meshes"]:
                        continue
                    counts, nverts, note = mesh_weights(inst, m)
                    name = inst.by_id.get(m, (None, None, str(m)))[2]
                    on_driven = sum(c for b, c in counts.items() if b in a["driven"])
                    on_parent = sum(c for b, c in counts.items() if b in a["parents"])
                    a["meshes"][m] = (name, nverts, on_driven, on_parent, note)
                    if note:
                        a["notes"].add(note.split(":")[0])
                    if on_driven > a["best"]:
                        a["best"], a["best_mesh"] = on_driven, name
                    elif not a["best_mesh"]:
                        a["best_mesh"] = name      # so a zero row still names one
                    a["parent_only"] = max(a["parent_only"], on_parent)
    return agg


def report(agg, csv_path=None):
    rows = sorted(agg.values(), key=lambda a: (-a["best"], -a["physics"]))
    moves = [a for a in rows if a["best"] > 0]
    dead = [a for a in rows if a["best"] == 0 and a["meshes"]]
    unknown = [a for a in rows if a["best"] == 0 and not a["meshes"]]
    W = "=" * 112
    print("\n" + W)
    print(f"RIG CENSUS - {len(rows)} physics-carrying rigs assigned; "
          f"{len(moves)} drive a mesh, {len(dead)} drive none of the meshes in "
          f"their own rows, {len(unknown)} have no mesh to check")
    print(W)
    hdr = (f"{'rig':<40}{'physics':>10}{'driven':>8}{'rows':>6}{'meshes':>8}"
           f"{'wts on driven':>15}  mesh")
    for title, group in (("MOVES A MESH - the donor shortlist", moves),
                         ("NO WEIGHT ON ANY DRIVEN BONE", dead),
                         ("NO MESH IN THE ROW - not evidence either way", unknown)):
        print(f"\n--- {title} ---")
        print(hdr)
        for a in group:
            cl = " +cloth" if a["cloth_rows"] else ""
            print(f"{a['name'][:39]:<40}{a['physics']:>9,}B{len(a['driven']):>8}"
                  f"{a['rows']:>6}{len(a['meshes']):>8}{a['best']:>15,}  "
                  f"{a['best_mesh'][:34]}{cl}")
            if not a["best"] and a["parent_only"]:
                note = f"({a['parent_only']:,} on parents only)"
                print(f"{'':<72}{note:>15}")
    if csv_path:
        import csv
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["rig", "physics_bytes", "driven_bones", "rows", "tables",
                        "mesh", "vertices", "weights_on_driven",
                        "weights_on_parents", "note"])
            for a in rows:
                for _m, (nm, nv, od, op, note) in sorted(a["meshes"].items(),
                                                         key=lambda kv: -kv[1][2]):
                    w.writerow([a["name"], a["physics"], len(a["driven"]), a["rows"],
                                ";".join(sorted(a["tables"]))[:300], nm, nv, od, op,
                                note])
        print(f"\nwrote {csv_path}")


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = list(argv[1:])
    install = csv_path = grep = None
    all_lods = "--all-lods" in args
    if all_lods:
        args.remove("--all-lods")
    if "--install" in args:
        k = args.index("--install"); install = args[k + 1]; del args[k:k + 2]
    if "--csv" in args:
        k = args.index("--csv"); csv_path = args[k + 1]; del args[k:k + 2]
    if "--grep" in args:
        k = args.index("--grep"); grep = args[k + 1]; del args[k:k + 2]
    limit = None
    if "--limit" in args:
        k = args.index("--limit"); limit = int(args[k + 1]); del args[k:k + 2]
    if not install:
        for g in ab.candidate_grb_installs():
            install = g
            break
    if not install:
        print(__doc__)
        return 1
    print(f"install: {install}")
    t0 = time.time()
    inst = Install(install)
    print(f"indexed {len(inst.by_id):,} forge entries from {len(inst.forges)} forges "
          f"({time.time() - t0:.1f}s)")
    ab.start()
    ab.arm()
    ab.prime_hashes()
    ab.prime_filelist()          # resource_by_id needs ATK's forge/container paths
    containers =[os.path.splitext(os.path.basename(a))[0].split("_-_")[-1]
                  for a in args] or list(DEFAULT_CONTAINERS)
    agg = census(inst, containers, all_lods=all_lods, limit=limit, grep=grep)
    report(agg, csv_path)
    print(f"\n{time.time() - t0:.1f}s total")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
