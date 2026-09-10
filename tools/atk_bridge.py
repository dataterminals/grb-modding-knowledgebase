#!/usr/bin/env python3
"""
atk_bridge.py - call ATK's own format engine from Python, headlessly.

ATK has no CLI, but `AnvilToolkit.dll` is an ordinary .NET library and the WPF
application is only a shell over it. This module loads that library into CPython
via pythonnet and reads GRB resources with ATK's *own* readers - which makes ATK
usable as a second, independent opinion against this repo's hand-written parsers.

    python atk_bridge.py <file.data> [more.data ...]

Verified 2026-09-01 against `TP_Tacvest_Walker_Coat_LOD0/LOD1` - ATK's mesh
reader agrees with the independent parse recorded on 2026-07-01 (1816 verts /
3263 tris and 956 / 1631). See `meta/research-log.md`.

    >>> import atk_bridge
    >>> mesh = atk_bridge.read_mesh("87874_-_TP_Tacvest_Walker_Coat_LOD0.data")
    >>> mesh.Vertices.Count, mesh.Faces.Count
    (1816, 3263)

⚠️ READ-ONLY BY POLICY. `ForgeFile.Serialize`, `Mesh.WriteToFile` and friends are
in this same surface, and ATK's backup defaults (`CreateBackups`, ...) are
*application settings* - they do NOT apply to direct library calls. Nothing here
writes, and `DataFile` is deliberately never used: its `Deserialize` unpacks to
an `Extracted\\` folder and calls `CreateBackup`, i.e. it writes to your install.
Keep it that way unless CLAUDE.md rules 1 and 2 are satisfied explicitly.

REQUIREMENTS (all already present on the 2026-08-31 dev machine, unplanned):
  - pythonnet + clr_loader        (pip install pythonnet)
  - .NET 9 runtime                (ATK targets it; brought up from ATK's own
                                   AnvilToolkit.runtimeconfig.json)
  - an ATK install                (default D:\\Anvil Toolkit, or set GRB_ATK)
  - the game's oo2core_7_win64.dll for Oodle, found by data_inspect.py

HOW IT WORKS (five things that are each load-bearing):
 1. ATK's dependencies live in `<ATK>\\Libs`, which .NET will not probe on its
    own. Without an AssemblyResolve handler pointing there, `GetTypes()` throws
    ReflectionTypeLoadException and you silently lose types. With it, all 1245
    types load and there are zero loader errors.
 2. `ScimitarClass.ClassReader` is initialised from the *public static field*
    `DataStorage.GlobalScimitarClassReader`, which only the GUI populates. Left
    null, `Mesh.Read` dies with a NullReferenceException the moment it reads its
    first sub-object - and `Read` CATCHES that, sets `Failed = true`, and returns
    a half-built object. `arm()` sets the field; it must be set BEFORE any
    ScimitarClass is constructed.
 3. `HashedData.CheckStrings()` - which resolves every hash to a name - kicks its
    load off inside a `Task.Run` and returns IMMEDIATELY. The first caller
    therefore dereferences a still-null dictionary and gets a NullReferenceException.
    It is a startup RACE, not a missing file; the GUI wins it by loading early.
    `prime_hashes()` starts it and waits for the count to settle (~820,000 names,
    about a second). Anything that names things - `ScimitarClass.ClassName`,
    `MeshBone.NameString`, `AnvilGLTF.CreateGLTF` - needs this first.
 4. `DataStorage.ActiveGame` is a plain `public static Game` with NO initialiser,
    and `Game.Null` is -1 - so an unset field defaults to `(Game)0`, which is
    `Game.BlackFlag`. Only `MainWindow` and `GameSelector` ever assign it, i.e.
    only when a human picks a game in the GUI. The read helpers below dodge it by
    passing `game()` explicitly, but 68 files consult the global, and
    `AnvilGLTF.MeshFromGLTF` is one of them: left unset it runs its Black Flag
    branch over a GRB mesh and silently drops a colour channel. `arm()` sets it.
 5. The container layer is ours, not ATK's: `data_inspect.py` decompresses the
    `.data` and slices out the resource payload, and only the payload is handed
    to ATK. That is what makes the comparison independent - and it avoids
    `DataFile` entirely.

⚠️ `mesh.Failed` IS NOT A SUCCESS SIGNAL for GRB meshes in ATK 1.3.1. The reader
wants exactly ONE byte more than the resource payload holds, so it always ends
with "Unable to read beyond the end of the stream" and `Failed = True` even
though every field parsed correctly. `read_mesh` appends one zero pad byte, after
which `Failed` is False and the geometry is byte-identical either way. Whether
that byte is an ATK over-read or a container subtlety is UNRESOLVED - see the
research log. Do not "fix" it by trusting `Failed` blindly in either direction.
"""
import os
import sys
import struct
import importlib.util

ATK_DIR = os.environ.get("GRB_ATK", r"D:\Anvil Toolkit")
_REPO_TOOLS = os.path.dirname(os.path.abspath(__file__))

_state = {"started": False, "asm": None, "System": None, "armed": False}


class ResourceNotFound(LookupError):
    """The .data has no resource of the requested type.

    A plain LookupError on purpose: a library must not raise SystemExit, or a
    caller sweeping many files with `except Exception` gets killed by the first
    container that happens to hold something else."""


def _data_inspect():
    """Load this repo's own container reader as a module."""
    spec = importlib.util.spec_from_file_location(
        "data_inspect", os.path.join(_REPO_TOOLS, "data_inspect.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def start(atk_dir=None):
    """Bring up .NET, load AnvilToolkit.dll with <ATK>\\Libs on the probe path.

    Returns (System, assembly). Idempotent."""
    atk = atk_dir or ATK_DIR
    dll = os.path.join(atk, "AnvilToolkit.dll")
    if not os.path.isfile(dll):
        raise EnvironmentError(f"AnvilToolkit.dll not found at {dll}\n"
                               f"Set GRB_ATK to your ATK folder.")
    if not _state["started"]:
        import clr_loader
        from pythonnet import set_runtime
        set_runtime(clr_loader.get_coreclr(
            runtime_config=os.path.join(atk, "AnvilToolkit.runtimeconfig.json")))
        _state["started"] = True

    import clr  # noqa: F401  (pythonnet's import hook; must precede System)
    import System
    from System.Reflection import Assembly
    from System import ResolveEventHandler

    libs = os.path.join(atk, "Libs")

    def _resolve(sender, args):  # .NET will not probe Libs\ by itself
        name = args.Name.split(",")[0]
        for d in (libs, atk):
            p = os.path.join(d, name + ".dll")
            if os.path.isfile(p):
                try:
                    return Assembly.LoadFrom(p)
                except Exception:
                    pass
        return None

    if _state["asm"] is None:
        System.AppDomain.CurrentDomain.AssemblyResolve += ResolveEventHandler(_resolve)
        _state["asm"] = Assembly.LoadFrom(dll)
        _state["System"] = System
    return _state["System"], _state["asm"]


def types(asm=None):
    """All loaded types, plus any loader exceptions (should be empty)."""
    asm = asm or _state["asm"]
    from System.Reflection import ReflectionTypeLoadException
    try:
        return list(asm.GetTypes()), []
    except ReflectionTypeLoadException as e:
        return [t for t in e.Types if t is not None], list(e.LoaderExceptions or [])


def T(name):
    """Resolve an ATK type by full name."""
    t = _state["asm"].GetType(name)
    if t is None:
        raise KeyError("type not found: " + name)
    return t


def game(name="GhostReconBreakpoint"):
    System = _state["System"]
    return System.Enum.Parse(T("AnvilToolkit.Utils.Game"), name)


def arm(active_game="GhostReconBreakpoint"):
    """Set the two GUI-only statics that ATK's format engine reads from anywhere.

    1. `DataStorage.GlobalScimitarClassReader` - every ScimitarClass copies it
       into its instance ClassReader field. Must be set BEFORE constructing
       anything, or reads fail with a swallowed NullReference.
    2. `DataStorage.ActiveGame` - which game the engine believes is open.

    ⚠️ ActiveGame has no initialiser and `Game.Null` is -1, so unset it reads as
    `(Game)0` = **BlackFlag**: a real game with real, wrong code paths, and
    nothing throws. Verified 2026-09-09: with it unset, `AnvilGLTF.MeshFromGLTF`
    takes its BlackFlag branch on a GRB mesh and, because the coat is skinned,
    hits `if (Joints.Count != 0) Vertices[0].Color2 = null;` - which is the
    entire "importer drops a colour channel" defect. Setting it restores
    ColorCount 3. See the 2026-09-09 research-log entry."""
    if _state["armed"]:
        return
    System = _state["System"]
    reader = System.Activator.CreateInstance(
        T("AnvilToolkit.FileTypes.AnvilNext.ScimitarClassReader"))
    DS = T("AnvilToolkit.Utils.DataStorage")
    DS.GetField("GlobalScimitarClassReader").SetValue(None, reader)
    DS.GetField("ActiveGame").SetValue(None, game(active_game))
    _state["armed"] = True


def prime_hashes(timeout=60.0):
    """Load ATK's embedded hash->name dictionary and WAIT for it.

    `HashedData.CheckStrings()` fires a `Task.Run` and returns at once, so a
    naive caller races it and hits a NullReferenceException. Poll until the
    count stops growing. Returns the number of names loaded.

    Note this is plateau detection, not a completion signal - ATK exposes no
    'done' flag. ~820,000 names in about a second on the dev machine, which is
    3x what `atk_hashes.py` extracts from the same file by hand."""
    import time
    System, _asm = start()
    hd = T("AnvilToolkit.Utils.HashedData")
    field = hd.GetField("HashedStrings")
    hd.GetMethod("CheckStrings").Invoke(None, [])
    t0, last = time.time(), -1
    while time.time() - t0 < timeout:
        d = field.GetValue(None)
        count = 0 if d is None else d.Count
        if count > 0 and count == last:
            return count
        last = count
        time.sleep(0.3)
    return last


def hashed_string(value):
    """Resolve one CRC32 hash to a name, or the number back as a string."""
    System, _asm = start()
    return T("AnvilToolkit.Utils.HashedData") \
        .GetMethod("GetHashedString").Invoke(None, [System.UInt32(value)])


def resources(path):
    """Decompress a .data with THIS REPO's reader and yield its typed resources
    as dicts: name, type_id, type_name, class_id, payload (bytes).

    Deliberately does not use ATK's DataFile - that one writes to disk."""
    di = _data_inspect()
    raw = open(path, "rb").read()
    oodle = di.Oodle(di.find_oodle(path))
    _meta, off, _ = di.read_cfd(raw, 0, oodle)
    files, _off, _ = di.read_cfd(raw, off, oodle)
    out, o = [], 0
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
            cid, = struct.unpack_from("<Q", payload, hlen)
        except Exception:
            break
        out.append({"name": name, "type_id": tid, "type_name": di.type_name(tid),
                    "class_id": cid, "payload": payload, "header_len": hlen})
    return out


def read_typed(path, type_name, atk_type, index=0, pad=1, atk_dir=None):
    """Read one typed resource out of a .data using ATK's own reader.

    `type_name` selects the resource inside the container (as `data_inspect`
    names it); `atk_type` is the full ATK type to construct. `pad` zero bytes are
    appended - see the module docstring on the one-byte tail."""
    System, _asm = start(atk_dir)
    arm()
    from System.IO import MemoryStream, BinaryReader, StringWriter
    from System import Array, Byte

    res = resources(path)
    hits = [r for r in res if r["type_name"] == type_name]
    if not hits:
        raise ResourceNotFound(
            f"no {type_name} resource in {os.path.basename(path)} "
            f"(found: {[r['type_name'] for r in res]})")
    payload = hits[index]["payload"]

    grb = game()
    br = BinaryReader(MemoryStream(Array[Byte](bytes(payload) + b"\x00" * pad)))
    System.Console.SetOut(StringWriter())   # ATK logs swallowed errors to stdout
    T("AnvilToolkit.FileTypes.AnvilNext.Containers.DataFile") \
        .GetMethod("ReadFileHeader").Invoke(None, [br, grb])
    sc = System.Activator.CreateInstance(
        T("AnvilToolkit.FileTypes.AnvilNext.ScimitarClass"),
        [br, grb, System.UInt32(0)])
    return System.Activator.CreateInstance(T(atk_type), [br, sc])


def read_mesh(path, index=0, atk_dir=None):
    """Read one Mesh resource out of a .data using ATK's own reader.

    Returns the live AnvilToolkit Mesh object with Vertices/Faces populated."""
    mesh = read_typed(path, "Mesh",
                      "AnvilToolkit.FileTypes.AnvilNext.Models.Mesh",
                      index=index, atk_dir=atk_dir)
    if not mesh.Vertices.Count:      # ReadFromFile populates these on success;
        mesh.ReadVertexData()        # on the failure path it may not have.
        mesh.ReadIndexData()
    return mesh


def read_skeleton(path, index=0, atk_dir=None):
    """Read one Skeleton resource out of a .data using ATK's own reader.

    ⚠️ ATK parses the skeleton's structure (`Bones`, hierarchy) for GRB, but NOT
    its Reflex3 constraint blob - that parser is gated behind
    `Version != Game.Mirage`, so `Reflex3Constraints` stays an opaque lump.
    Use [`reflex3.py`](reflex3.py) for the bone physics."""
    return read_typed(path, "Skeleton",
                      "AnvilToolkit.FileTypes.AnvilNext.Models.Skeleton",
                      index=index, atk_dir=atk_dir)


DEFAULT_SEARCH = [
    r"D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint\Extracted\DataPC.forge",
    r"D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint\Extracted\DataPC_Resources.forge",
]


def find_skeletons_for(mesh, search_dirs=None, verbose=False):
    """Which skeleton .data files supply this mesh's bones?

    `CreateGLTF` refuses a skinned mesh whose bones it cannot find ("Missing
    skeleton! Bone X not found"), and a GRB garment's bones are usually split
    across TWO rigs: the character skeleton plus a garment addon (the Walker coat
    needs `Skeleton_Harmony_Reflex` for 24 of its 30 and `Vest_Generic_Addon` for
    the other 6). Greedily picks a covering set.

    Slow - it decompresses every candidate. Returns (paths, still_missing).

    ⚠️ It picks by BONE COVERAGE ALONE, and several character rigs share the same
    biped bone names. Ties are broken arbitrarily, so it may hand you
    `Skeleton_Female_Cinematic_162_Reflex` for a mesh the game actually wears on
    something else. The bone names and hierarchy will be right - which is all the
    weight transfer needs - but the REST POSE and proportions may not be the ones
    that garment was authored against. If you care how it looks in Blender, pass
    `--skeleton` explicitly."""
    import glob
    want = {b.Name for b in mesh.Bones}
    cands = []
    for d in (search_dirs or DEFAULT_SEARCH):
        cands += glob.glob(os.path.join(d, "*Skeleton*.data"))
        cands += glob.glob(os.path.join(d, "*Addon*.data"))
    scored = []
    for p in sorted(set(cands)):
        try:
            sk = read_skeleton(p)
        except (ResourceNotFound, Exception):
            continue
        have = {b.Name for b in sk.Bones}
        if want & have:
            scored.append((len(want & have), p, have))
    scored.sort(key=lambda x: -x[0])
    chosen, covered = [], set()
    for _n, p, have in scored:
        if want <= covered:
            break
        if have - covered & have:            # contributes something new
            gain = (want & have) - covered
            if gain:
                chosen.append(p)
                covered |= gain
                if verbose:
                    print(f"    + {os.path.basename(p)} (+{len(gain)} bones)")
    return chosen, want - covered


def export_gltf(data_path, out_path, skeleton_paths=None, search_dirs=None,
                verbose=False):
    """Export one GRB mesh .data to a .glb using ATK's own glTF writer.

    VERIFIED 2026-09-01 on TP_Tacvest_Walker_Coat_LOD0: 1816 verts / 3263 tris,
    5 UV sets, 5 colour sets, 271 skin joints - written by SharpGLTF, no GUI.

    ⚠️ Writes `out_path`. Point it somewhere that is NOT your game install."""
    System, _asm = start()
    arm()
    prime_hashes()          # CreateGLTF names nodes; unprimed it NullReferences
    from System.Collections.Generic import List, Dictionary
    from System import String
    from System.IO import StringWriter

    mesh = read_mesh(data_path)
    if skeleton_paths is None:
        if verbose:
            print("  searching for skeletons that supply this mesh's bones...")
        skeleton_paths, missing = find_skeletons_for(mesh, search_dirs, verbose)
        if missing:
            raise LookupError(
                f"could not find skeletons for {len(missing)} of the mesh's bones: "
                f"{sorted(missing)[:8]}")

    T_Mesh = T("AnvilToolkit.FileTypes.AnvilNext.Models.Mesh")
    T_Skel = T("AnvilToolkit.FileTypes.AnvilNext.Models.Skeleton")
    T_Soft = T("AnvilToolkit.FileTypes.AnvilNext.Physics.SoftBody")
    T_Trk = T("AnvilToolkit.FileTypes.AnvilNext.Schema.BaseTypes.AnimTrack")
    meshes = List[T_Mesh]()
    meshes.Add(mesh)
    skels = List[T_Skel]()
    for p in skeleton_paths:
        skels.Add(read_skeleton(p))

    gltf = T("AnvilToolkit.FileTypes.AnvilNext.Models.AnvilGLTF")
    method = [m for m in gltf.GetMethods()
              if m.Name == "CreateGLTF" and len(m.GetParameters()) == 5][0]
    sw = StringWriter()
    System.Console.SetOut(sw)
    try:
        method.Invoke(None, [out_path, meshes, skels, List[T_Soft](),
                             Dictionary[String, Dictionary[String, List[T_Trk]]]()])
    finally:
        System.Console.SetOut(System.Console.Out)
    if not os.path.isfile(out_path):
        raise RuntimeError(f"CreateGLTF wrote nothing. ATK said: {sw.ToString().strip()}")
    return out_path, skeleton_paths


def summarize(path):
    mesh = read_mesh(path)
    vb = bytes(mesh.VertexBuffer)
    stride = mesh.VertexStride
    idx = [int(c) for f in mesh.Faces for c in (f.Index.x, f.Index.y, f.Index.z)]
    infl = {}
    for k in range(len(vb) // stride):
        n = sum(1 for i in range(4) if vb[k * stride + 28 + i] > 0)
        infl[n] = infl.get(n, 0) + 1
    print(f"  ClassID       {mesh.ID}")
    print(f"  Failed        {mesh.Failed}   (see docstring - not a success signal)")
    print(f"  VertexFormat  {mesh.VertexFormat}")
    print(f"  VertexStride  {stride}")
    print(f"  Vertices      {mesh.Vertices.Count}")
    print(f"  Faces         {mesh.Faces.Count}")
    print(f"  index range   {min(idx)}..{max(idx)}")
    print(f"  Bones         {mesh.Bones.Count}")
    print(f"  SubMeshes     {mesh.SubMeshes.Count}")
    print(f"  Clustered     {mesh.IsUsingClusteredData}")
    print(f"  influences/vertex  {dict(sorted(infl.items()))}")
    n = prime_hashes()
    named = [(b.Name, b.NameString) for b in mesh.Bones]
    real = [s for _h, s in named if s and not s.isdigit()]
    print(f"  bone names    {len(real)}/{len(named)} resolve "
          f"against ATK's {n:,}-name dictionary")
    if real:
        print(f"                {', '.join(real)}")


def main(argv):
    args = list(argv[1:])
    out = None
    skels = []
    if "--export" in args:
        k = args.index("--export")
        out = args[k + 1]
        del args[k:k + 2]
    while "--skeleton" in args:
        k = args.index("--skeleton")
        skels.append(args[k + 1])
        del args[k:k + 2]
    if not args:
        print(__doc__)
        return 1
    for p in args:
        print("=" * 70)
        print(f"FILE: {os.path.basename(p)}")
        if out:
            path, used = export_gltf(p, out, skels or None, verbose=True)
            print(f"  exported -> {path} ({os.path.getsize(path):,} B)")
            for s in used:
                print(f"    skeleton: {os.path.basename(s)}")
        else:
            summarize(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
