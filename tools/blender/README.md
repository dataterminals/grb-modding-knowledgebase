# 🧊 Blender bridge — drive Blender from a terminal

Blender ships **its own Python interpreter** and can run with **no window at all**.
That means everything you'd normally do by clicking — import a mesh, transfer weight
painting, export a GLB — can also be done from a command line, scripted, repeatable,
and diffable. It also means an AI assistant working alongside you can do those things
directly, and hand you back a report.

That's what this is. `grbblend.py` runs on your side; `_inside.py` runs inside Blender.

> **Read-only where it counts.** Nothing here opens, reads, or writes your GRB install.
> It only touches the files you point it at. The game-file half of the pipeline is still
> ATK's job — see [`../../docs/07-modding-workflow.md`](../../docs/07-modding-workflow.md).

---

## First: is there already a "Blender connector" for GRB?

**Yes, and you already have it — it's glTF.** There is no GRB-specific Blender add-on to
hunt down, and you don't need one:

- **ATK exports and imports meshes as glTF / GLB** (via SharpGLTF), with GLB as its
  default. That's [documented here](../../docs/10-meshes-and-skeletons.md).
- **Blender reads and writes GLB natively.** The `io_scene_gltf2` add-on ships enabled
  in every Blender install.

So the bridge is a **file format both ends already speak**, not a plugin. ATK writes a
GLB, Blender opens it; Blender writes a GLB, ATK reads it. What's missing is not a
connector — it's *tooling around the seam*, which is what this directory adds.

**And on scripting languages:** Blender is **Python only**. There's no Lua in it. (Lua is
what Garry's Mod used — easy crossed wire if that's where your model-rigging experience
comes from.) Blender's Python is a full API over the whole application: `bpy.data` is the
file, `bpy.ops` is every menu command, and both are available headless.

---

## What you need

**Blender.** If `doctor` (below) finds it, you're done. Otherwise get it free from
<https://www.blender.org/download/> or its Steam listing. Any 3.x–5.x should work; the
tool asks each operator what options it accepts rather than assuming, so version drift
mostly takes care of itself.

**Python on your side** — the same one the other tools in `../` use.

If Blender lands somewhere unusual, point at it with `--blender "D:\path\to\blender.exe"`
or set the `GRB_BLENDER` environment variable.

---

## Start here

```
python grbblend.py doctor
```

Finds Blender, prints its version, its bundled Python, and whether the glTF add-on is
present. Fast, and touches nothing.

```
python grbblend.py selftest
```

Proves the whole path works **without any game files**. It builds a fake "coat" (a rigged,
weight-painted cylinder), a fake "poncho" (a cone — different shape, different topology,
no rig), writes both to GLB, transfers the coat's weights and vertex colours onto the
poncho, exports the result, reloads it, and checks the weights actually survived:

```
  [PASS]  coat was rigged
  [PASS]  weights landed on poncho
  [PASS]  every poncho vertex weighted
  [PASS]  vertex colors came across
  [PASS]  survived glb round trip
  [PASS]  weights still complete after round trip
  [PASS]  result has armature

RESULT: PASS - the bridge works end to end.
```

If that passes, your Blender is wired up correctly.

---

## The commands

### `inspect` — what's actually in this GLB?

```
python grbblend.py inspect Coat_LOD0.glb
```

Reports, per mesh: vertex/triangle counts, **UV sets**, **vertex colours** (name, domain,
type), materials, modifiers, vertex groups, **how many bones pull on each vertex**, and
**how many vertices have no weight at all** — plus the armature and its bone list.

It also flags the failure modes [`docs/10`](../../docs/10-meshes-and-skeletons.md) names
by hand:

| It warns when | Because |
| --- | --- |
| no UV layer | ATK warns and fills `(0,0)`; shading and tangents go wrong |
| more than 5 UV sets | GRB meshes carry up to 5 |
| no vertex colours | GRB uses them; a mismatch is the classic "corrupted shading" bug |
| >4 influences per vertex | glTF carries 4 per JOINTS set — the rest are silently dropped |
| any unweighted vertices | they will not deform in game |
| several materials | each becomes its own primitive, each with its own bone limit |

Run this on a mesh **the moment it comes out of ATK**, and again before it goes back in.

> **One thing it deliberately ignores.** Importing a *skinned* GLB makes Blender's own glTF
> importer synthesise a 42-vertex icosphere as a bone-display shape. It is scaffolding, not
> content — it isn't in the file — but until 2026-09-08 it was reported as a second mesh and
> raised a bogus "no vertex colours" warning on **every** rigged GRB garment. It is now
> filtered out (matched on its `glTF_not_exported` collection and its use as a bone custom
> shape, not on its name) and listed on an `ignored:` line so nothing is hidden from you.

### `transfer-weights` — the north-star operation

This is [Sami's move](../../meta/project-goal.md), scripted: take the weight painting off
an in-game garment and put it onto an outside-source mesh.

```
python grbblend.py transfer-weights ^
    --source Vanilla_Coat.glb ^
    --target My_Poncho.glb ^
    --out Poncho_Bound.glb ^
    --with-colors
```

`--source` is the **rigged vanilla garment** exported from ATK. `--target` is your new
mesh. The tool copies every vertex group across, hooks the new mesh to the donor's rig
with an Armature modifier, drops the donor mesh, and writes a GLB.

It prints the target **before and after**, so you can see exactly what changed, and gives
you the number that matters:

```
weight coverage:  100.0% of the new mesh's vertices got a weight
```

**Anything under 100% means unweighted vertices, which will not deform in game.** Usually
the two meshes aren't sitting in the same place, or the new one extends past where the old
one had geometry. Try `--vert-mapping NEAREST`, or line the meshes up first.

Useful flags:

| Flag | What it does |
| --- | --- |
| `--with-colors` | also copy the donor's vertex colours — **GRB reads these** |
| `--with-uvs` | also copy the donor's UV layout (overwrites the new mesh's own) |
| `--vert-mapping` | how new vertices find old ones; default `POLYINTERP_NEAREST` |
| `--keep-source` | leave the donor mesh in the exported scene |
| `--no-bind` | skip the Armature modifier |
| `--source-mesh` / `--target-mesh` | pick a mesh by name (default: the biggest one) |

> **Why `--with-colors` exists.** Transferring weights copies *only* weights. The donor's
> vertex colours stay behind — and a GRB mesh that arrives without the vertex colours its
> slot expects is exactly the "corrupted shading / colours read as UVs" failure
> [`docs/10`](../../docs/10-meshes-and-skeletons.md) describes.

### `run` — your own Python, inside Blender

The escape hatch. Anything the two commands above don't cover:

```
python grbblend.py run --file Coat.glb ^
    --code "result = {'bones': [g.name for g in pick_mesh(list(bpy.data.objects)).vertex_groups]}"
```

Set `result` to whatever you want reported back as JSON. `bpy`, `bmesh`, and all the
helpers (`describe_scene`, `pick_mesh`, `pick_armature`, `export_glb`, `load_file`,
`select_only`) are in scope. `--script foo.py` runs a file instead.

Add `--json` to any command for the raw structured report, and `--verbose` to see
Blender's own console output when something goes wrong.

---

## The add-on — Blender's own sidebar, no terminal needed

If you'd rather never touch a command line, install `grb_blender_addon.py`:

**Blender → Edit → Preferences → Add-ons → the `v` dropdown (top right) → Install from
Disk… → pick `grb_blender_addon.py` → tick its checkbox.**

Then press **`N`** in the 3D viewport and click the **GRB** tab. You get:

- **Live checks** on the selected mesh — UV sets, vertex colours, materials, vertex groups
  — recomputed as you work, red when something's wrong.
- **Check Weights** — the per-vertex pass: bone influences, and how many vertices have no
  weight at all. Behind a button because it costs real time on a big mesh.
- **Select Unweighted** — drops you into Edit Mode with the problem vertices already
  selected, so you can *see* the gap rather than read a number.
- **Transfer Weights to Selected** — the same operation as the CLI, one click. Select your
  new mesh, then shift-select the vanilla garment last so it's active; data flows from
  active to selected.
- **Export GLB for ATK** — presets tangents, vertex colours and every UV set.

> **Verified 2026-08-31 on Blender 5.2.1 LTS:** all four operators and all three panels
> register, and the transfer operator runs correctly headlessly — 3 groups moved, armature
> modifier added, vertex colours copied, analysis reporting accurate.

New to Blender? [`docs/13-blender-for-grb.md`](../../docs/13-blender-for-grb.md) is the
primer — Blender's vocabulary for things you already know from rigging, plus the GRB rules
that bite.

---

## Where this sits in the pipeline

```
     atk_bridge.py              THIS TOOL              atk_bridge.py        ATK / GUI
  forge .data → GLB    →   inspect / edit / rebind  →  GLB → ATK Mesh   →  write back +
     (scripted)                 (scripted here)          (scripted)         repack forge
                                                                          (manual, by policy)
```

**Update (2026-09-08): only the last step is manual now.** ATK is a WPF app with no
command-line interface, but `AnvilToolkit.dll` is an ordinary .NET library and both
directions of its glTF bridge are callable from Python via
[`../atk_bridge.py`](../atk_bridge.py):

- **Export** — `export_gltf()` drives ATK's own SharpGLTF writer headlessly. Verified
  2026-09-01, and again 2026-09-08 on `TP_Tacvest_Walker_Coat_LOD0`.
- **Import** — `AnvilGLTF.FromGLTF(path)` returns `(List<Mesh>, List<ConvexVerticesShape>)`
  and does the whole import internally. First invoked 2026-09-08; see below.

What stays manual is **writing the result back into a `.data` and repacking the forge**.
`Mesh.WriteToFile` and `ForgeFile.Serialize` exist in the same callable surface, but
`atk_bridge.py` is read-only **by policy** — ATK's backup defaults are *application*
settings and do not apply to direct library calls, so a stray write has no safety net. See
CLAUDE.md rules 1 and 2.

---

## What has and hasn't been proven

> **Verified (2026-08-31, this machine):** Blender 5.2.1 LTS runs headless; `io_scene_gltf2`
> is present; the full build → rig → weight-paint → export GLB → import → transfer weights
> and vertex colours onto a different-topology mesh → re-export → reload → verify path
> completes with 100% weight coverage and survives the GLB round trip. That is what
> `selftest` checks, and it passes.

> **Verified (2026-09-08): a real GRB garment completed a full headless round trip.**
> `TP_Tacvest_Walker_Coat_LOD0` went forge `.data` → GLB → back through ATK's own importer.
> **Geometry is preserved exactly** — 1816 vertices and 3263 faces on both sides — and the
> GLB carries everything: 5 UV sets, 5 colour sets, tangents, 4 influences per vertex,
> **0 unweighted vertices**. Two things change on the way back *in*:
>
> | | original `.data` | round-tripped |
> | --- | --- | --- |
> | Bones | 30 | **25** — the importer keeps only bones carrying weights |
> | VertexFormat | `…_Tex2s_Joint4_Col4ub` | `…_Tex2s_Joint4` — `Col4ub` dropped |
>
> That second row is exactly the vertex-format choice
> [`../../docs/10`](../../docs/10-meshes-and-skeletons.md) warns is the step most likely to
> bite. It is now something you can *measure* before shipping rather than discover in game.

> **Still not verified:** whether either of those two changes actually breaks a garment
> in game, and whether a modified mesh writes back into a `.data` cleanly. Nothing has been
> written back to a forge. `RemapBuffers` does **not** rebuild the vertex buffer — it only
> reorders vertices into face order — and where the format is finally decided is still an
> open question. Don't ship on this yet.

> **Out of scope, by design:** this does **not** solve the `.cloth` rebind. Cloth is welded
> to one mesh's exact vertices, and ATK's GRB cloth reader is gated off — **and as of
> 2026-09-08 we know that gate is load-bearing, not conservative.** `SoftBody` is ATK's
> cloth class, but its `SupportedGames` list is AC-family only; adding GRB to it (in memory
> or by patching the DLL) makes the reader misparse — it read 257 "states" from a file that
> really holds 2 cloth LODs, then ran off the end of the stream. GRB cloth is a different
> format family entirely. **Don't try to unlock it that way.** See
> [`../../docs/11-cloth-and-physics.md`](../../docs/11-cloth-and-physics.md) and
> [`../../meta/project-goal.md`](../../meta/project-goal.md). What weight transfer *does*
> serve is the **bone-physics route** (`.skeleton` / Reflex3), which is transferable
> precisely because it's weight-painted rather than vertex-welded:
> [`../../reference/skeleton-reflex3-physics.md`](../../reference/skeleton-reflex3-physics.md).

---

*Files here:* `grbblend.py` (the command line you run), `_inside.py` (the half that runs
inside Blender), `grb_blender_addon.py` (the in-Blender sidebar panel), and `_selftest/`
if you've run the selftest with default paths.
