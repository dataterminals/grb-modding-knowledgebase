# 07 — The end-to-end modding workflow

This is the practical loop a GRB modder runs: from an idea in Blender to patch forges in the game directory. It ties together the concepts from docs 02–06. Steps that mutate real game data carry a ⚠️.

> **Golden rule:** never repack or overwrite a forge without a backup. ATK creates backups by default, but verify it before any ⚠️ step.

## Overview

```
 (1) AUTHOR            (2) EXPORT            (3) IMPORT                (4) REPACK            (5) LIVE
 Blender model    →    glTF/GLB + DDS   →   import into the forge →  repack the forge   →  already in your
 / texture edit        (standard formats)    via ATK (replace/add)    in place via ATK      GRB install
```

## 1. Author the asset (Blender)

Cosmetic mods start in **Blender**: model a new mesh, or edit an existing one exported from the game, and/or paint textures. Reference assets come *out of the game first* — you unpack a forge, find the original mesh/texture, export it, and use it as the basis so your replacement matches the game's scale, UVs, and rigging.

Key constraints to respect (because the engine and ATK enforce them):
- **Vertex data**: meshes need correct normals/tangents/binormals and UVs. ATK recalculates tangents/binormals on glTF import and warns on missing UVs/vertex colors, but clean Blender data avoids surprises.
- **Skinning**: skinned meshes must weight to the correct **skeleton/bones**; ATK enforces per-primitive bone limits and removes unused bones on GRB import.
- **LODs**: the game expects multiple levels of detail (`LOD0` highest → `LOD3` lowest). See [`10-meshes-and-skeletons.md`](10-meshes-and-skeletons.md).
- **Vertex colors**: GRB uses them; Blender's two color-naming schemes are both handled by ATK, but be deliberate about them.

## 2. Export to interchange formats

- **Meshes → glTF / GLB.** GLB is ATK's default mesh format. This is the Blender↔ATK bridge (via SharpGLTF). Export with the conventions ATK expects (application-specific vertex-color accessor names for best round-tripping — ATK handles this on its side).
- **Textures → DDS (recommended) / PNG / TGA / JPG.** DDS is preferred because it gives explicit control over **pixel format**, **mips**, and **gamma** (see [`09-textures.md`](09-textures.md)). ATK will accept any image format and can generate mips on import, but DDS is the controlled path.

## 3. Import into the forge ⚠️

Import your authored asset into the game's data via ATK. Mechanically:

1. **Unpack** the relevant base/working forge in ATK (or work in an existing unpacked mod folder).
2. Find the target resource by name/ID in the Game Explorer.
3. **Replace** it: double-click a texture to open the Texture Viewer and *Replace*, or drag-and-drop the new file onto the entry; for meshes, use the **Mesh Viewer** to import the GLB (it can replace a mesh with a matching ID, or load a standalone GLB).
4. For new content, **mint IDs** (Hash Converter) and create the entries; generate/patch the **BuildTable** so the game knows how to assemble your asset. The Mesh Viewer can export a BuildTable from a scene/mesh/skeleton.
5. Keep the three layers consistent (item / gameplay / resources) — see [`05-three-forge-model.md`](05-three-forge-model.md).

> **Why it's more than a copy:** the raw Blender output isn't game data; ATK *converts and embeds* it — quantizing vertices into the game's vertex format, packing the DDS into a TextureMap with the right header/mips/gamma, and writing it into the container with a file ID. That conversion-and-embedding is what "import" means here.

## 4. Repack ⚠️

Repack the unpacked folder back into its `.forge` — **in your actual game install**. In the normal workflow ATK is pointed straight at the GRB install and rewrites the forge *in place*, so for your own machine repacking **is** installing (see step 5). Notes for GRB:
- **Keep `EnableCompression` ON.** A GRB `.data` written with **raw/uncompressed** blocks **crashes/hangs the game at load** (verified 2026-07-02) — it parses in ATK but the game rejects it. This is a load-safety requirement, not a tunable; see [`02-forge-file-format.md`](02-forge-file-format.md). (Historical note: ATK once serialized GRB data uncompressed by default, then made compression a setting; for GRB you must leave it on.)
- **The unpacked folder is a *persistent* working source, not a per-edit scratch.** Unpack a forge to `Extracted\<forge>\` **once**, then edit/add/remove entries there and repack **from it incrementally over time** — you do *not* re-unpack each session (ATK won't unpack over an existing folder, and only re-creates its forge backup on a *fresh* extract). ⚠️ **Before repacking a forge you have *not* been actively maintaining in `Extracted\`, verify `Extracted\` still matches the *live* forge** (a stale working folder whose live forge gained mods by another path will **revert those mods** on repack — a real incident, 2026-07-02). If it has diverged, re-extract that one forge once to resync, then edit incrementally. See [`meta/research-log.md`](../meta/research-log.md).
- You repack the forge that holds the target entries — usually the `*_patch_01` set for gear/weapons (see [`05-three-forge-model.md`](05-three-forge-model.md)). (Cloth is the exception — it lives in the base `DataPC.forge`; see [`11-cloth-and-physics.md`](11-cloth-and-physics.md).)

Backups: ATK writes `.bak` files and/or `Backups` folders (`CreateBackups`, `CreateDataBackups`, `CreateFileBackups` default `True`). Note `OverwriteFileBackups` also defaults `True`, and `AddDateToBackups` defaults `False` — so backups overwrite rather than accumulate by date unless you change that. Forges are multi-GB original game data; keep your own clean copy of anything irreplaceable.

## 5. Install ⚠️ (usually already done)

In practice there's **no separate install step**: modders point ATK at their real GRB install and unpack/repack its forges directly, so a mod is live the moment you repack (step 4). Over time a working install just **accumulates many mods repacked into the same forge files** — that's what a "modded install" *is* (e.g. a long-running live install has had dozens of mods repacked into its forges).

- **You edit the install's forges in place**, not a standalone file. Whole forge files are rarely passed around — they're huge and represent your machine's accumulated state.
- **Sharing a mod** means sharing its **`.data` entries** (often as an unpacked mod folder, like the Nexus corpus). Whoever installs it imports those entries into *their* forges with ATK and repacks — the same in-place flow.
- **Combining mods is the normal, cumulative case**, not an edge case: you keep adding entries to the same forge and repacking. Because everything lands in one forge, **two mods that change the same file ID truly conflict** — only one can win. Check for that up front by diffing the two mods' forges with the **Forge Inspector** ([`tools/`](../tools/README.md)).
- **Always keep a clean backup** of each forge before you start repacking into it (the install's `Backups\` / `_GRBbackups\` folders exist for exactly this) — a bad repack otherwise means re-downloading multi-GB files.

## 6. Test in-game

Launch GRB and verify the asset appears correctly at all LODs/distances and under the headgear/attachment variants it has (faces and hair have many variants — `ForGoggles`, `ForHelmetGoggles`, `ForGazMask`, `ForNVG`, etc.; see [`08-naming-conventions.md`](08-naming-conventions.md)). If it's invisible or wrong, the usual suspects are: mismatched IDs across forges, missing LOD/variant entries, wrong vertex format, or a BuildTable still pointing at old resources.

## The loop, compressed

> **First time on a forge:** back up the forge → unpack it once to a persistent `Extracted\<forge>\` working folder.
> **Each edit thereafter:** find by ID → export reference → edit in Blender → export glTF/DDS → import/replace in ATK (compression ON) → fix BuildTable + IDs (keep the layers consistent) → repack **from the same working folder** in place → test → repeat.
>
> You **re-unpack only** if the working folder has drifted from the live forge (see the ⚠️ in step 4) — not every session.
