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

HOW IT WORKS (three things that are each load-bearing):
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
 4. The container layer is ours, not ATK's: `data_inspect.py` decompresses the
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
        raise SystemExit(f"AnvilToolkit.dll not found at {dll}\n"
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


def arm():
    """Populate DataStorage.GlobalScimitarClassReader - the GUI-only static that
    every ScimitarClass copies into its instance ClassReader field. Must run
    BEFORE constructing anything, or reads fail with a swallowed NullReference."""
    if _state["armed"]:
        return
    System = _state["System"]
    reader = System.Activator.CreateInstance(
        T("AnvilToolkit.FileTypes.AnvilNext.ScimitarClassReader"))
    T("AnvilToolkit.Utils.DataStorage") \
        .GetField("GlobalScimitarClassReader").SetValue(None, reader)
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


def read_mesh(path, index=0, atk_dir=None):
    """Read one Mesh resource out of a .data using ATK's own reader.

    Returns the live AnvilToolkit Mesh object with Vertices/Faces populated."""
    System, _asm = start(atk_dir)
    arm()
    from System.IO import MemoryStream, BinaryReader, StringWriter
    from System import Array, Byte

    res = resources(path)
    meshes = [r for r in res if r["type_name"] == "Mesh"]
    if not meshes:
        raise SystemExit(f"no Mesh resource in {os.path.basename(path)} "
                         f"(found: {[r['type_name'] for r in res]})")
    payload = meshes[index]["payload"]

    grb = game()
    # +1 pad: ATK 1.3.1's GRB mesh reader wants one byte past the payload. See
    # the module docstring - without it Failed is always True.
    br = BinaryReader(MemoryStream(Array[Byte](bytes(payload) + b"\x00")))
    System.Console.SetOut(StringWriter())   # ATK logs swallowed errors to stdout
    T("AnvilToolkit.FileTypes.AnvilNext.Containers.DataFile") \
        .GetMethod("ReadFileHeader").Invoke(None, [br, grb])
    sc = System.Activator.CreateInstance(
        T("AnvilToolkit.FileTypes.AnvilNext.ScimitarClass"),
        [br, grb, System.UInt32(0)])
    mesh = System.Activator.CreateInstance(
        T("AnvilToolkit.FileTypes.AnvilNext.Models.Mesh"), [br, sc])
    if not mesh.Vertices.Count:      # ReadFromFile populates these on success;
        mesh.ReadVertexData()        # on the failure path it may not have.
        mesh.ReadIndexData()
    return mesh


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
    if len(argv) < 2:
        print(__doc__)
        return 1
    for p in argv[1:]:
        print("=" * 70)
        print(f"FILE: {os.path.basename(p)}")
        summarize(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
