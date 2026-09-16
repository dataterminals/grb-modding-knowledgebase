#!/usr/bin/env python3
"""
atk_bridge.py - call ATK's own format engine from Python, headlessly.

ATK has no CLI, but `AnvilToolkit.dll` is an ordinary .NET library and the WPF
application is only a shell over it. This module loads that library into CPython
via pythonnet and reads GRB resources with ATK's *own* readers - which makes ATK
usable as a second, independent opinion against this repo's hand-written parsers.

    python atk_bridge.py <file.data> [more.data ...]
    python atk_bridge.py <donor.data> --import new.glb    # check a write-back
    python atk_bridge.py <file.data> --xml out.xml        # ATK's XML round-trip

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
  - an ATK install                (found by searching; --atk <dir>, or
                                   $GRB_ATK to name it exactly)
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
    `.data` and walks it, and only one resource's FileHeader + payload - the
    bytes ATK's own unpack would write to a file - is handed to ATK. That is what
    makes the comparison independent - and it avoids `DataFile` entirely.

`mesh.Failed` - RESOLVED 2026-09-16. This module used to warn that ATK "wants
exactly ONE byte more than the resource payload holds" and padded every read with
a zero byte. It was our slicer, not ATK: the old container walk started each
payload one byte early (on the FileHeader) and so cut off the payload's last
byte, which the pad then replaced. The Walker coat's last payload byte is 0x00,
which is why the padded read was byte-identical. With the corrected walk the
read ends exactly on the payload, `Failed` is False with no pad, and `pad`
defaults to 0. `Read` still swallows other exceptions (gate 2), so check the
geometry, not only the flag.
"""
import os
import sys
import struct
import importlib.util

_REPO_TOOLS = os.path.dirname(os.path.abspath(__file__))

_state = {"started": False, "asm": None, "System": None, "armed": False}


# --------------------------------------------------------------------------
# finding the install - this is not the only machine
# --------------------------------------------------------------------------
# The machines this repo gets worked on disagree about drive letters: one keeps
# ATK and the game on D:, the other has ATK on E: and the game on H:. A
# hardcoded default makes the tool look broken on whichever machine it was not
# written on, so search instead - the same thing tools/blender/grbblend.py
# already does for Blender.

_WIN_DRIVES = "CDEFGHIJKLMNOPQRSTUVWXYZ"


def _drive_roots():
    """Drive roots that exist, C: first. Empty off Windows."""
    if os.name != "nt":
        return []
    roots = ["%s:%s" % (d, os.sep) for d in _WIN_DRIVES]
    return [r for r in roots if os.path.isdir(r)]


def candidate_atk_dirs():
    """Every directory that looks like an ATK install, best guess first.

    "Looks like" = holds `AnvilToolkit.dll`. The DIRECTORY is what callers want,
    never the exe: `Libs` (gate 1) and `Lists` (gate 7) resolve relative to it,
    and `start()` reads `AnvilToolkit.runtimeconfig.json` out of it."""
    seen, out = set(), []

    def add(d):
        if not d:
            return
        d = os.path.abspath(d)
        if d not in seen and os.path.isfile(os.path.join(d, "AnvilToolkit.dll")):
            seen.add(d)
            out.append(d)

    add(os.environ.get("GRB_ATK"))

    home = os.path.expanduser("~")
    parents = [os.path.join(home, d) for d in ("Desktop", "Downloads", "Documents")]
    for root in _drive_roots():
        parents += [root,
                    os.path.join(root, "Program Files"),
                    os.path.join(root, "Program Files (x86)"),
                    os.path.join(root, "Games"),
                    os.path.join(root, "Modding"),
                    os.path.join(root, "Tools")]

    for parent in parents:
        try:                                  # unreadable or disconnected drive
            entries = sorted(os.listdir(parent))
        except OSError:
            continue
        for entry in entries:
            if "anvil" in entry.lower():
                add(os.path.join(parent, entry))
    return out


def find_atk(explicit=None):
    """Resolve the ATK install directory, once per process.

    Order: an explicit path, then whatever is already cached, then $GRB_ATK,
    then a search. The failure raises EnvironmentError naming everywhere it
    looked - a 2026-07-09 session searched three places, concluded ATK "was not
    found on disk", and wrote that into the research log as a blocker, where it
    sat for a month."""
    if explicit:
        if not os.path.isfile(os.path.join(explicit, "AnvilToolkit.dll")):
            raise EnvironmentError(
                "no AnvilToolkit.dll in %s\n"
                "Point --atk (or GRB_ATK) at the folder holding it." % explicit)
        return os.path.abspath(explicit)
    if _state.get("atk_dir"):
        return _state["atk_dir"]
    found = candidate_atk_dirs()
    if not found:
        raise EnvironmentError(
            "Could not find an Anvil Toolkit install - a folder holding "
            "AnvilToolkit.dll.\n"
            "Looked at: $GRB_ATK, then every drive root plus Program Files, "
            "Program Files (x86), Games, Modding, Tools,\n"
            "and your Desktop / Downloads / Documents, for any folder whose "
            "name contains \"anvil\".\n"
            "Pass --atk <dir>, or set the GRB_ATK environment variable.")
    _state["atk_dir"] = found[0]
    return found[0]


def candidate_grb_installs():
    """Every Ghost Recon Breakpoint install on this machine, best guess first.

    Identified by `GRB.exe`, which rejects the stub directories Steam leaves
    behind on libraries the game is no longer installed to."""
    seen, out = set(), []

    def add(d):
        if not d:
            return
        d = os.path.abspath(d)
        if d not in seen and os.path.isfile(os.path.join(d, "GRB.exe")):
            seen.add(d)
            out.append(d)

    add(os.environ.get("GRB_INSTALL"))
    for root in _drive_roots():
        for lib in ("SteamLibrary",
                    os.path.join("Program Files (x86)", "Steam"),
                    "Steam", "Games"):
            add(os.path.join(root, lib, "steamapps", "common",
                             "Ghost Recon Breakpoint"))
        add(os.path.join(root, "Ubisoft", "Ghost Recon Breakpoint"))
        add(os.path.join(root, "Program Files (x86)", "Ubisoft",
                         "Ubisoft Game Launcher", "games",
                         "Ghost Recon Breakpoint"))
    return out


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
    atk = find_atk(atk_dir)
    dll = os.path.join(atk, "AnvilToolkit.dll")
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
    """Decompress a .data with THIS REPO's reader and list its typed resources
    as dicts: name, type_id, type_name, class_id, header, payload (bytes).

    `header` is the FileHeader that sits between a resource's name and its
    payload, counted by neither length; `payload` starts with the ClassID. Their
    concatenation is exactly what ATK's own unpack writes to a file. Deliberately
    does not use ATK's DataFile - that one writes to disk."""
    di = _data_inspect()
    oodle = di.Oodle(di.find_oodle(path))
    _meta, files = di.read_container(path, oodle)
    res, end = di.walk(files)
    if end != len(files):
        raise ValueError(f"{os.path.basename(path)}: container walk stopped at byte "
                         f"{end:,} of {len(files):,} - refusing to pick from a partial list")
    return [{"name": r.name, "type_id": r.type_id, "type_name": di.type_name(r.type_id),
             "class_id": di.class_id(r), "header": r.header, "payload": r.payload,
             "header_len": len(r.header)} for r in res]


def read_typed(path, type_name, atk_type, index=0, pad=0, atk_dir=None, name=None):
    """Read one typed resource out of a .data using ATK's own reader.

    `type_name` selects the resource inside the container (as `data_inspect`
    names it), `name` narrows that to one resource by name - containers such as
    TEAMMATE_Template hold thousands of BuildTables - and `index` picks among
    what is left. `atk_type` is the full ATK type to construct. ATK is handed the
    resource's FileHeader + payload, the same bytes its own unpack would write;
    `pad` zero bytes are appended after them (see the module docstring)."""
    System, _asm = start(atk_dir)
    arm()
    from System.IO import MemoryStream, BinaryReader, StringWriter
    from System import Array, Byte

    res = resources(path)
    hits = [r for r in res if r["type_name"] == type_name
            and (name is None or r["name"] == name)]
    if not hits:
        raise ResourceNotFound(
            f"no {type_name} resource{' named ' + name if name else ''} in "
            f"{os.path.basename(path)} (found {len(res):,} resources)")
    hit = hits[index]

    grb = game()
    stream = bytes(hit["header"]) + bytes(hit["payload"]) + b"\x00" * pad
    br = BinaryReader(MemoryStream(Array[Byte](stream)))
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


def default_search_dirs():
    """Where `find_skeletons_for` looks when the caller names no directory.

    The `Extracted` folders beside whichever GRB install this machine has -
    ATK's own unpack target. Returns [] when nothing has been unpacked yet,
    which surfaces as "no skeletons found" rather than a crash."""
    out = []
    for install in candidate_grb_installs():
        for forge in ("DataPC.forge", "DataPC_Resources.forge"):
            d = os.path.join(install, "Extracted", forge)
            if os.path.isdir(d):
                out.append(d)
    return out


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
    for d in (search_dirs or default_search_dirs()):
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


# --------------------------------------------------------------------------
# The import side. See the 2026-09-09 research-log entry for why every one of
# these corrections is needed; none of them is cosmetic.
# --------------------------------------------------------------------------

_COLS = ["Color0", "Color1", "Color2", "Color3", "Color4"]
_UVS = ["TEXCOORD_0", "TEXCOORD_1", "TEXCOORD_2", "TEXCOORD_3", "TEXCOORD_4"]


def _glb_summary(path):
    """Read a GLB's JSON chunk directly. Two things ATK will not tell you:

    - the vertex count as the FILE has it, before `RemapBuffers` rebuilds the
      list from face traversal and silently drops any vertex no face references
      (`Tsec_Madera_Coat_LOD0`: 12,502 -> 12,498);
    - whether the file carries any colour or UV channels at all, which is the
      condition behind ATK's two modal import warnings.

    A GLB is a 12-byte header then chunks; chunk 0 is the JSON document. A plain
    `.gltf` is that document on its own."""
    import json
    with open(path, "rb") as fh:
        if fh.read(4) == b"glTF":
            fh.seek(12)
            length = struct.unpack("<I", fh.read(4))[0]
            kind = fh.read(4)
            if kind != b"JSON":
                raise ValueError(f"{path}: first GLB chunk is {kind!r}, not JSON")
            doc = json.loads(fh.read(length).decode("utf-8"))
        else:
            fh.seek(0)
            doc = json.loads(fh.read().decode("utf-8"))
    acc = doc.get("accessors", [])
    verts, attrs = 0, set()
    for m in doc.get("meshes", []):
        for prim in m.get("primitives", []):
            a = prim.get("attributes", {})
            attrs.update(a)
            if "POSITION" in a:
                verts += acc[a["POSITION"]].get("count", 0)
    # glTF standardises COLOR_n/TEXCOORD_n; extras take an underscore prefix,
    # and ATK's GetVertexColor also accepts its own COL.000 spelling.
    bare = [k.lstrip("_") for k in attrs]
    return {
        "vertices": verts,
        "meshes": len(doc.get("meshes", [])),
        "attributes": sorted(attrs),
        "has_color": any(k.startswith(("COLOR_", "COL.")) for k in bare),
        "has_uv": any(k.startswith("TEXCOORD_") for k in bare),
    }


def _write_prep(mesh):
    """Replicate `Mesh.WriteToFile`'s prologue - WITHOUT writing anything.

    WriteToFile's first act is to normalise vertex zero for `base.Version` and
    only then take the format from it:

        Vertices[0].Joints.MaxCount = 8;         // GRB
        Vertices[0].Version = 3;  UVScale = 16f; // GRB
        Vertices[0].Color3 = Color4 = TEXCOORD_4 = null;
        if (Joints.Count == 0) Vertices[0].Binormals = null;
        VertexFormat = Vertices[0].Format;

    Doing it here means `write_preview` reports the format the file would really
    get, not the one the importer happened to leave behind. It is idempotent -
    WriteToFile redoes exactly this - so a prepped mesh is not a damaged one.

    ⚠️ GRB only. Every other game nulls a different set, and running the wrong
    set is the whole 2026-09-09 finding."""
    if str(mesh.Version) != "GhostReconBreakpoint":
        raise ValueError(f"_write_prep is GRB-only; mesh.Version is {mesh.Version}")
    v0 = mesh.Vertices[0]
    v0.Joints.MaxCount = 8
    v0.Version = 3
    mesh.UVScale = 16.0
    v0.Color3 = None
    v0.Color4 = None
    v0.TEXCOORD_4 = None
    if v0.Joints.Count == 0:
        v0.Binormals = None
    return mesh


def write_preview(mesh):
    """What WriteToFile would compute for this mesh: (format, game id, stride).

    These are literally its three lines - `Vertices[0].Format`, then
    `GetGameSpecificVertexFormat`, then `GetVertexFormatSize` - evaluated
    without touching a stream. Call `_write_prep` first."""
    System, _asm = start()
    from System import Int32, Enum
    M = "AnvilToolkit.FileTypes.AnvilNext.Models."
    p_fmt = T("AnvilToolkit.Common.Vertex").GetProperty("Format")
    raw = p_fmt.GetValue(mesh.Vertices[0])
    # pythonnet hands a boxed enum back as an int; re-box it or reflection refuses
    fmt = Enum.ToObject(T("AnvilToolkit.Utils.VertexFormat"), Int32(int(raw)))
    gameval = game(str(mesh.Version))
    gsvf = int(T(M + "VertexFormatsMap")
               .GetMethod("GetGameSpecificVertexFormat").Invoke(None, [gameval, fmt]))
    stride = int(T(M + "VertexFormatSizes")
                 .GetMethod("GetVertexFormatSize").Invoke(None, [gameval, Int32(gsvf)]))
    return str(raw), gsvf, stride


def import_gltf(glb_path, donor=None, index=0, atk_dir=None, verbose=False):
    """Import a GLB through ATK's own importer, corrected against a donor mesh.

    `AnvilGLTF.FromGLTF` alone does NOT give you a mesh you can write back. It
    needs three corrections, each of which is silent when missing:

      1. `DataStorage.ActiveGame` must be GRB, or `MeshFromGLTF` runs its Black
         Flag branch and drops a colour channel from any skinned mesh. `arm()`
         handles this one for you.
      2. `mesh.Version` is hardcoded to `Game.BlackFlag` by `MeshFromGLTF`
         (`ScimitarClassReader.New(Game.BlackFlag, ...)`) and never assigned.
         `Mesh.WriteToFile` switches on `base.Version` in ten places, so an
         uncorrected mesh writes itself out as a Black Flag mesh.
      3. **The importer does not reconstruct a vertex format - it normalises
         one.** Every skinned GRB mesh comes back as ColorCount 3 / UVCount 4
         whatever went in, because ATK's glTF *writer* pads all five UV and all
         five colour channels unconditionally and nothing in the GLB says which
         were real. So the channel counts must come from the DONOR, and that is
         what `donor` is for. Most GRB garments already sit at (3, 4) and appear
         to round-trip perfectly, which is how this hid for so long.

    Trimming vertex zero is enough, and is not a shortcut: `WriteVertexData`
    writes *every* vertex against the single mesh-level `VertexFormat`, which
    comes from vertex zero alone. Slots trimmed there are simply not written;
    slots missing on other vertices are padded by `GetUVs()`/`GetColors()`.

    ⚠️ Do not read a format off `FromGLTF`'s output and believe it. The importer
    preps `Vertices[0]` and *then* calls `RemapBuffers`, which rebuilds the list
    in face-traversal order - so the one prepped vertex is wherever that put it.
    Measured: the Walker coat's stayed at index 0, the selftest poncho's landed
    at index **67**, leaving a raw (5 colour, 5 UV) vertex at index 0. Writing is
    unaffected, because `WriteToFile` re-preps whatever is at index 0 by then;
    only *inspection* is fooled. The `"as_imported"` numbers in the report are
    therefore "whatever is at index 0", not a property of the mesh.

    Returns `(mesh, report)`. `report["ok"]` is True only when a donor was given
    and the format AND stride both match it.

    ⚠️ NOTHING IS WRITTEN. The returned Mesh is a live in-memory object; getting
    it into a `.data` and repacking a forge is still a manual, backed-up step -
    by policy, not by capability. See CLAUDE.md rules 1 and 2."""
    System, _asm = start(atk_dir)
    arm()                    # sets ActiveGame - correction 1
    prime_hashes()

    glb = _glb_summary(glb_path)

    gltf = T("AnvilToolkit.FileTypes.AnvilNext.Models.AnvilGLTF")
    m_from = [m for m in gltf.GetMethods() if m.Name == "FromGLTF"][0]
    from System.IO import StringWriter

    # ⚠️ `MeshFromGLTF` pops a WPF MODAL DIALOG when the GLB has no vertex
    # colours or no UVs - i.e. on exactly the fresh-from-Blender mesh a modder
    # brings. Headless there is no dispatcher, so `WpfMessageBox..ctor()` throws
    # and the whole import dies. Its own `VertexColorMessageShown` guard is
    # useless here: `FromGLTF` resets that flag on entry. The only lever is the
    # setting, so borrow it and hand it straight back. We report the same two
    # conditions ourselves, below, from the GLB - a warning you can grep beats a
    # dialog nobody is there to click.
    #
    # This is an IN-MEMORY property set. `Settings.Save()` is never called here
    # and must not be: that would write ATK's user config.
    S = T("AnvilToolkit.Properties.Settings")
    settings = S.GetProperty("Default").GetValue(None)
    p_sup = S.GetProperty("SuppressMeshViewerImportErrorMessages")
    was = p_sup.GetValue(settings)
    sw = StringWriter()
    System.Console.SetOut(sw)
    try:
        p_sup.SetValue(settings, True)
        meshes = m_from.Invoke(None, [glb_path]).Item1
    finally:
        p_sup.SetValue(settings, was)
        System.Console.SetOut(System.Console.Out)
    said = sw.ToString().strip()
    if meshes.Count == 0:
        raise RuntimeError(f"FromGLTF returned no meshes. ATK said: {said or '(nothing)'}")
    mesh = meshes[index]

    v0 = mesh.Vertices[0]
    report = {
        "glb": glb_path,
        "atk_said": said,
        "glb_carries": glb,
        "meshes_in_file": meshes.Count,
        "vertices": mesh.Vertices.Count,
        "faces": mesh.Faces.Count,
        "bones": mesh.Bones.Count,
        "as_imported": {"colors": v0.ColorCount, "uvs": v0.UVCount,
                        "vertex_version": v0.Version, "game": str(mesh.Version)},
        "warnings": [],
        "ok": False,
    }

    mesh.Version = game()                                    # correction 2

    if not glb["has_color"]:
        report["warnings"].append(
            "the GLB carries NO vertex colour channels. ATK substitutes defaults "
            "(white, white, then black) - and GRB garments use vertex colours, which "
            "docs/10 names as the 'corrupted shading' failure. In the GUI this is a "
            "modal warning; here it is this line.")
    if not glb["has_uv"]:
        report["warnings"].append(
            "the GLB carries NO UV channels. Same story - a modal warning in the GUI, "
            "this line here. The mesh will be untextured.")
    if glb["vertices"] and mesh.Vertices.Count != glb["vertices"]:
        report["warnings"].append(
            f"vertices {glb['vertices']} in the file -> {mesh.Vertices.Count} imported. "
            f"RemapBuffers rebuilds the list from face traversal, so any vertex no face "
            f"references is dropped. Usually harmless; never silent again.")

    if donor is not None:                                    # correction 3
        d = read_mesh(donor, atk_dir=atk_dir)
        dv = d.Vertices[0]
        report["donor"] = {
            "path": donor, "colors": dv.ColorCount, "uvs": dv.UVCount,
            "format": str(d.VertexFormat), "stride": int(d.VertexStride),
            "vertices": d.Vertices.Count, "bones": d.Bones.Count,
        }
        for n in range(dv.ColorCount, 5):
            setattr(v0, _COLS[n], None)
        for n in range(dv.UVCount, 5):
            setattr(v0, _UVS[n], None)
        if mesh.Bones.Count == 0 and d.Bones.Count:
            report["warnings"].append(
                f"this mesh has NO bones; the donor has {d.Bones.Count}. It is unrigged - "
                f"weight-paint it to the donor's rig first (tools/blender/ transfer-weights) "
                f"or it will not deform at all.")
        elif mesh.Bones.Count < d.Bones.Count:
            report["warnings"].append(
                f"bones {d.Bones.Count} -> {mesh.Bones.Count}: the importer keeps only "
                f"bones that carry weight. Whether GRB indexes a mesh's bone table "
                f"positionally is UNTESTED.")
    else:
        report["warnings"].append(
            "no donor given - the channel counts below are ATK's normalised constant "
            "(3 colours / 4 UVs), not a measurement of what this mesh should have. "
            "Pass the .data you are replacing.")

    _write_prep(mesh)
    fmt, gsvf, stride = write_preview(mesh)
    report["corrected"] = {"colors": v0.ColorCount, "uvs": v0.UVCount,
                           "vertex_version": v0.Version, "game": str(mesh.Version)}
    report["write_preview"] = {"format": fmt, "game_format_id": gsvf, "stride": stride}

    if fmt == "Null":
        report["warnings"].append(
            "VertexFormat is Null - the descriptor is not among VertexFormats.Types' 62 "
            "entries. GetVertexFormat RETURNS this rather than throwing, and WriteToFile "
            "assigns it unchecked. Do not write this mesh.")
    if mesh.CompiledMesh is None:
        report["warnings"].append(
            "CompiledMesh is null: the Mesh.VertexFormat setter is a silent no-op in that "
            "state, and WriteToFile dereferences it on its first line.")
    if "donor" in report:
        dfmt, dstride = report["donor"]["format"], report["donor"]["stride"]
        report["ok"] = (fmt == dfmt and stride == dstride)
        if not report["ok"]:
            report["warnings"].append(
                f"does NOT match the donor: format {fmt} vs {dfmt}, "
                f"stride {stride} vs {dstride}.")
    if verbose:
        print_import_report(report)
    return mesh, report


def print_import_report(report):
    d = report.get("donor")
    g = report["glb_carries"]
    print(f"  GLB           {os.path.basename(report['glb'])}")
    print(f"  file carries  {g['vertices']} verts, {g['meshes']} mesh(es), "
          f"colours={g['has_color']} uvs={g['has_uv']}")
    if report["meshes_in_file"] > 1:
        print(f"  meshes        {report['meshes_in_file']} (using index 0)")
    print(f"  Vertices      {report['vertices']}")
    print(f"  Faces         {report['faces']}")
    print(f"  Bones         {report['bones']}"
          + (f"   (donor has {d['bones']})" if d else ""))
    a, c = report["as_imported"], report["corrected"]
    print(f"  at index 0    colours={a['colors']} uvs={a['uvs']} "
          f"vertex.Version={a['vertex_version']} game={a['game']}   (raw)")
    if d:
        print(f"  donor         colours={d['colors']} uvs={d['uvs']}  "
              f"{d['format']} / stride {d['stride']}")
    print(f"  corrected     colours={c['colors']} uvs={c['uvs']} "
          f"vertex.Version={c['vertex_version']} game={c['game']}")
    w = report["write_preview"]
    print(f"  would write   {w['format']}")
    print(f"                game format id {w['game_format_id']}, stride {w['stride']}")
    if d:
        print(f"  MATCHES DONOR {report['ok']}")
    for msg in report["warnings"]:
        print(f"  ! {msg}")
    if report["atk_said"]:
        print(f"  ATK said      {report['atk_said']}")


def prime_filelist(timeout=120.0, atk_dir=None):
    """Load ATK's game file list, so 64-bit IDs render as NAMES instead of numbers.

    `GameFileList.CheckStrings()` looks for `Lists/<ActiveGame>.gfl` at a
    **relative** path - relative to the process working directory - and, not
    finding one, calls `WpfMessageBox.Show` to offer downloading it. Headless
    that is fatal. ATK ships the file at `<ATK>\\Lists\\GhostReconBreakpoint.gfl`
    (6.8 MB), so the fix is to point the working directory at the ATK folder for
    the duration; then the list loads and no dialog is ever constructed.

    Like `HashedData.CheckStrings`, it loads inside a `Task.Run` and returns
    immediately, so this polls until the count settles. ~1,053,000 entries.

    Without this, `Handle.ToXml` and anything else going through
    `XmlUtils.WriteToXMLRef` emits bare decimal IDs - technically correct, and
    unreadable. Returns the number of entries."""
    import time
    System, _asm = start(atk_dir)
    from System.IO import Directory
    gfl = T("AnvilToolkit.Utils.GameFileList")
    field = gfl.GetField("List")
    d = field.GetValue(None)
    if d is not None and d.Count:
        return d.Count
    was = Directory.GetCurrentDirectory()
    Directory.SetCurrentDirectory(find_atk(atk_dir))
    try:
        gfl.GetMethod("CheckStrings").Invoke(None, [])
        t0, last = time.time(), -1
        while time.time() - t0 < timeout:
            d = field.GetValue(None)
            count = 0 if d is None else d.Count
            if count > 0 and count == last:
                return count
            last = count
            time.sleep(0.4)
        return last
    finally:
        Directory.SetCurrentDirectory(was)


def _on_sta(fn):
    """Run fn() on a fresh STA thread and return its value, re-raising errors.

    ⚠️ `ScimitarClass.ToXml` reaches WPF - `WpfMessageBox` at minimum - and WPF
    refuses to initialise outside a single-threaded apartment. pythonnet's CLR
    thread is MTA, so an XML export dies with "The calling thread must be STA"
    before it writes a byte. This is the workaround; priming the file list first
    is what stops the STA thread then *showing* the dialog."""
    System, _asm = start()
    from System.Threading import Thread, ThreadStart, ApartmentState
    box = {}

    def runner():
        try:
            box["value"] = fn()
        except Exception as exc:            # noqa: BLE001 - re-raised below
            box["error"] = exc

    t = Thread(ThreadStart(runner))
    t.SetApartmentState(ApartmentState.STA)
    t.Start()
    t.Join()
    if "error" in box:
        raise RuntimeError(str(box["error"])[:400])
    return box.get("value")


def export_xml(data_path, type_name, atk_type, out_path=None, index=0, atk_dir=None,
               name=None):
    """Export one XML-backed resource to XML, the way ATK's GUI would.

    `EntityBuilder`, `Material`, `TextureSet`, `LODSelector` and friends declare
    `FileActionType.Xml` and carry a `WriteXml()` that returns an `XElement`.
    That is the community's editable round-trip surface, and this reaches it
    without the application.

    Returns the XML string; also writes `out_path` when given. Verified
    2026-09-09 on `PLAYER_Template` (base and patch): 651 KB, 11,234 lines.

    ⚠️ Writes only `out_path`. Point it somewhere that is NOT your install."""
    System, _asm = start(atk_dir)
    arm()
    prime_hashes()
    prime_filelist(atk_dir=atk_dir)
    obj = read_typed(data_path, type_name, atk_type, index=index, atk_dir=atk_dir,
                     name=name)
    from System.IO import StringWriter, Directory
    was = Directory.GetCurrentDirectory()
    Directory.SetCurrentDirectory(find_atk(atk_dir))   # ToXml re-checks the list
    sw = StringWriter()
    System.Console.SetOut(sw)
    try:
        xml = _on_sta(lambda: obj.WriteXml(None).ToString())
    finally:
        System.Console.SetOut(System.Console.Out)
        Directory.SetCurrentDirectory(was)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(xml)
    return xml


# type_name (as data_inspect names it) -> the ATK class that can write it as XML.
# Extend freely; anything whose class declares FileActionType.Xml belongs here.
ATK_XML_TYPES = {
    "EntityBuilder": "AnvilToolkit.FileTypes.AnvilNext.Tables.EntityBuilder",
    "BuildTable": "AnvilToolkit.FileTypes.AnvilNext.Tables.BuildTable",
    "Material": "AnvilToolkit.FileTypes.AnvilNext.Materials.Material",
    "TextureSet": "AnvilToolkit.FileTypes.AnvilNext.Materials.TextureSet",
    "LODSelector": "AnvilToolkit.FileTypes.AnvilNext.Models.LODSelector",
}


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
    print(f"  Failed        {mesh.Failed}")
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
    if "--atk" in args:                  # everything downstream reads the cache
        k = args.index("--atk")
        _state["atk_dir"] = find_atk(args[k + 1])
        del args[k:k + 2]
    out = None
    glb_in = None
    skels = []
    if "--export" in args:
        k = args.index("--export")
        out = args[k + 1]
        del args[k:k + 2]
    if "--import" in args:
        k = args.index("--import")
        glb_in = args[k + 1]
        del args[k:k + 2]
    xml_out = None
    if "--xml" in args:
        k = args.index("--xml")
        xml_out = args[k + 1]
        del args[k:k + 2]
    wanted = None                        # --resource NAME: pick one inside a container
    if "--resource" in args:
        k = args.index("--resource")
        wanted = args[k + 1]
        del args[k:k + 2]
    while "--skeleton" in args:
        k = args.index("--skeleton")
        skels.append(args[k + 1])
        del args[k:k + 2]
    if glb_in and not args:
        # no donor: still useful, but say so loudly
        print("=" * 70)
        print(f"IMPORT: {os.path.basename(glb_in)}  (no donor)")
        import_gltf(glb_in, None, verbose=True)
        return 0
    if not args:
        print(__doc__)
        return 1
    for p in args:
        print("=" * 70)
        if glb_in:
            print(f"IMPORT: {os.path.basename(glb_in)}")
            print(f"  donor       {os.path.basename(p)}")
            _mesh, rep = import_gltf(glb_in, p, verbose=True)
            if not rep["ok"]:
                return 2
            continue
        print(f"FILE: {os.path.basename(p)}")
        if xml_out:
            res = resources(p)
            if wanted is not None:
                res = [r for r in res if r["name"] == wanted]
            if not res:
                print("  no typed resources" + (f" named {wanted!r}" if wanted else ""))
                continue
            tn = res[0]["type_name"]
            atk_type = ATK_XML_TYPES.get(tn)
            if atk_type is None:
                print(f"  no XML export mapping for {tn} - add it to ATK_XML_TYPES")
                continue
            xml = export_xml(p, tn, atk_type, xml_out, name=res[0]["name"])
            print(f"  {res[0]['name']} ({tn}) -> {xml_out} "
                  f"({len(xml):,} chars, {xml.count(chr(10)) + 1:,} lines)")
            continue
        if out:
            path, used = export_gltf(p, out, skels or None, verbose=True)
            print(f"  exported -> {path} ({os.path.getsize(path):,} B)")
            for s in used:
                print(f"    skeleton: {os.path.basename(s)}")
        else:
            summarize(p)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except EnvironmentError as exc:   # no ATK found, or a bad --atk path
        sys.exit(str(exc))            # a message, not a stack trace
