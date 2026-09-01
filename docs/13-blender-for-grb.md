# 13 — Blender for GRB, from a standing start

A primer for someone who has rigged a player model before — in Garry's Mod, Source, or
anywhere else — but has never really used Blender. It assumes you understand **weight
painting** and **bones** conceptually, and skips explaining them. What it gives you is
**Blender's vocabulary and UI for things you already understand**, plus the handful of
GRB-specific rules that will bite you.

Read [`07-modding-workflow.md`](07-modding-workflow.md) for the pipeline this sits inside,
and [`10-meshes-and-skeletons.md`](10-meshes-and-skeletons.md) for what GRB wants from a
mesh. Tooling: [`../tools/blender/README.md`](../tools/blender/README.md).

---

## The translation table

Half of Blender's difficulty is that it names familiar things differently.

| You know it as | Blender calls it | Notes |
| --- | --- | --- |
| Skeleton / rig | **Armature** | An object type, like a mesh. Bones live inside it. |
| Bone weights on a vertex | **Vertex group** | One group *per bone*, named exactly like the bone. A vertex's weight in group `Spine2` is its weight to that bone. |
| Weight painting | **Weight Paint mode** | Same thing, and it edits vertex groups. |
| Binding a mesh to a rig | **Armature modifier** | A modifier on the mesh pointing at the armature. Without it, the weights exist but nothing moves. |
| Material / skin | **Material** | GRB cares how many you have — each becomes a separate draw primitive. |
| UV map | **UV map** | Same word. GRB allows up to 5 per mesh. |
| Smoothing groups | **Shade Smooth / Auto Smooth** | Different mechanism, same purpose. |
| The model file | **`.blend`** | Your working file. Not what the game eats — that's GLB. |

**The one that trips everyone:** in Blender, vertex groups are *just named groups of
vertices with weights*. They only become bone weights because the Armature modifier
matches group names to bone names. Rename a bone and the link silently breaks.

---

## Moving around without rage

This is the actual first blocker, so it goes first.

| Do this | To |
| --- | --- |
| **Middle mouse drag** | Orbit |
| **Shift + middle mouse drag** | Pan |
| **Scroll wheel** | Zoom |
| **Numpad `.`** | **Frame the selected object** — the "where did my model go" fix |
| **Home** | Frame everything |
| **Numpad 1 / 3 / 7** | Front / side / top view |
| **Numpad 5** | Toggle perspective ↔ orthographic |

No middle mouse button? Preferences → Input → **Emulate 3 Button Mouse**, then Alt+drag
orbits.

**If you import something and see nothing:** it's almost always scale. Press `Numpad .`
with it selected. GRB assets can arrive very small or very large relative to Blender's
default grid.

---

## The five areas of the screen

- **3D Viewport** — the big one.
- **Outliner** (top right) — the scene tree. Every object, and the parent/child links.
  This is where you confirm your mesh is actually parented to the armature.
- **Properties editor** (bottom right) — tabs down its left edge. The two you'll live in:
  the **wrench** (Modifiers) and the **green triangle** (Object Data — where vertex groups
  and UV maps are listed).
- **Sidebar** — press **`N`** in the viewport. Item transforms, and where the
  [GRB add-on](../tools/blender/README.md) puts its panel.
- **Toolbar** — press **`T`**. Rarely needed.

Blender's tab bar along the very top (Layout, Modeling, UV Editing, **Scripting**…) swaps
whole screen layouts. They're presets, not modes; nothing is lost by switching.

---

## Object Mode vs Edit Mode

**Tab** toggles between them, and confusing them causes most beginner grief.

- **Object Mode** — you manipulate *whole objects*. Move, rotate, parent, add modifiers.
- **Edit Mode** — you manipulate *the vertices inside one object*. `1` / `2` / `3` switch
  between vertex, edge, and face selection.
- **Weight Paint Mode** — a third mode, for meshes bound to an armature.

The mode dropdown sits top-left of the viewport if the keyboard shortcuts don't stick.

---

## Selected vs Active — this one matters

Blender distinguishes **selected** (orange outline) from **active** (brighter, near-white
outline). The active object is the *last* one you clicked.

Operations that go "from one thing to another" — including **weight transfer** — read
direction from this. The rule for our purposes:

> Click your **new mesh** first. Then **Shift-click the vanilla garment** last, so it is
> active. Data flows **from active → to selected**.

Get this backwards and you'll wipe the donor's weights instead of copying them. It's
undoable (`Ctrl+Z`), but know which way round it goes.

---

## The ten operations you'll actually repeat

1. **Import a GLB** — File → Import → glTF 2.0. This is what ATK gives you.
2. **Frame it** — `Numpad .`
3. **Look at its vertex groups** — Properties → green triangle → Vertex Groups. For a GRB
   garment this list *is* the bone list.
4. **Look at its UV maps** — same panel, just below. GRB allows up to 5.
5. **Check vertex colors** — same panel, Color Attributes. **GRB uses these**; a mesh
   missing them imports with corrupted-looking shading.
6. **Enter Weight Paint mode** — select the mesh, mode dropdown → Weight Paint. Pick a
   vertex group to see its weights. Red = 1.0, blue = 0.0.
7. **Add an Armature modifier** — Properties → wrench → Add Modifier → Deform → Armature,
   then set its Object to the armature.
8. **Parent a mesh to an armature** — select mesh, Shift-select armature, `Ctrl+P` → With
   Automatic Weights (or Empty Groups if you're transferring weights yourself).
9. **Transfer weights** — the GRB add-on's button, or Object → Link/Transfer Data →
   Transfer Mesh Data.
10. **Export a GLB** — File → Export → glTF 2.0, or the add-on's *Export GLB for ATK*
    button, which presets the options ATK wants.

---

## GRB's rules, condensed

These come from [`10-meshes-and-skeletons.md`](10-meshes-and-skeletons.md). The
[GRB add-on](../tools/blender/README.md) checks all of them for you, live.

| Rule | Why |
| --- | --- |
| **Keep UV maps.** Up to 5. | Missing UVs → ATK fills `(0,0)` and shading breaks. |
| **Keep vertex colors.** | GRB reads them. This is the classic corrupted-import bug. |
| **≤4 bone influences per vertex.** | glTF carries 4 per JOINTS set; extras are silently dropped. |
| **No unweighted vertices.** | They will not deform. Ever. |
| **Watch the material count.** | Each material becomes a primitive with its own bone limit. |
| **Match the donor.** | Same UV sets, same vertex-color usage, same skeleton, similar vertex budget as the mesh you're replacing. |
| **Do every LOD.** | Replace only LOD0 and your asset reverts to the old shape at distance. |

> **The one number to watch:** after any weight transfer, *how many vertices ended up with
> no weight at all*. Vertex groups can transfer successfully while large parts of your mesh
> get nothing — and those parts won't move in game. The add-on reports this and can select
> the offending vertices for you.

---

## Undo, and not losing work

- `Ctrl+Z` undoes, generously. Blender's undo stack is deep.
- **Save early as a `.blend`** (`Ctrl+S`). The `.blend` is your working file; GLB is an
  export format and loses things (modifier stacks, unapplied edits, your selection state).
- Blender writes a `.blend1` backup beside your save automatically.
- GLB export does **not** overwrite your `.blend`. They're separate.

---

## The Scripting tab

Blender's entire interface is Python, and the **Scripting** workspace gives you a console
and a text editor with the whole API live. You don't need it to model — but it means any
operation can be handed to you as a snippet to paste and run, rather than as a list of
clicks to follow. Useful when something needs to be done to 400 vertices identically, or
when you want it done exactly the same way twice.

There is no Lua anywhere in Blender; it's Python throughout.

---

## When something looks wrong

| Symptom | Look at |
| --- | --- |
| Imported nothing / empty scene | Wrong file, or it's tiny — press `Numpad .` |
| Mesh is there but black or weirdly shaded | Missing vertex colors, or missing/flipped normals |
| Mesh doesn't move with the rig | No Armature modifier, or its Object field is empty |
| Parts of the mesh stay behind when posed | Unweighted vertices — the add-on can select them |
| Deforms, but wrongly | Bone name mismatch between vertex groups and armature |
| Export rejected by ATK | Vertex format, or missing tangents/UVs |
