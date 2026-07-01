# 07 — The end-to-end modding workflow

This is the practical loop a GRB modder runs: from an idea in Blender to patch forges in the game directory. It ties together the concepts from docs 02–06. Steps that mutate real game data carry a ⚠️.

> **Golden rule:** never repack or overwrite a forge without a backup. ATK creates backups by default, but verify it before any ⚠️ step.

## Overview

```
 (1) AUTHOR            (2) EXPORT            (3) IMPORT                (4) REPACK            (5) INSTALL
 Blender model    →    glTF/GLB + DDS   →   import into the forge →  forge → patch_01.forge → drop into
 / texture edit        (standard formats)    via ATK (replace/add)    via ATK                 GRB game dir
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

Repack the unpacked folder back into a `.forge`. ATK notes for GRB:
- GRB data historically serialized **uncompressed**; **compression is now a setting** (`EnableCompression` defaults `True` in the shipped config). If a repacked mod misbehaves in-game, compression settings are a thing to check.
- ATK won't unpack over an existing unpacked folder (prevents clobbering); manage your working folders accordingly.
- Repacking produces a `*_patch_01.forge` you can distribute.

Backups: ATK writes `.bak` files and/or `Backups` folders (`CreateBackups`, `CreateDataBackups`, `CreateFileBackups` default `True`). Note `OverwriteFileBackups` also defaults `True`, and `AddDateToBackups` defaults `False` — so backups overwrite rather than accumulate by date unless you change that. For anything irreplaceable, keep your own copy.

## 5. Install ⚠️

Place the repacked `DataPC_*_patch_01.forge` file(s) into the GRB install directory alongside the base forges. The game loads them as a patch layer and your overrides take effect (see [`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md)).

- **Always back up the original** `*_patch_01.forge` files you're replacing (the install ships a `Backups\` and `_GRBbackups\` folder pattern for exactly this reason).
- **Combining multiple mods** that each ship `DataPC_Resources_patch_01.forge` requires *merging* their `.data` entries into one patch forge — you can't just drop two files with the same name. Conflicting IDs are true conflicts.

## 6. Test in-game

Launch GRB and verify the asset appears correctly at all LODs/distances and under the headgear/attachment variants it has (faces and hair have many variants — `ForGoggles`, `ForHelmetGoggles`, `ForGazMask`, `ForNVG`, etc.; see [`08-naming-conventions.md`](08-naming-conventions.md)). If it's invisible or wrong, the usual suspects are: mismatched IDs across forges, missing LOD/variant entries, wrong vertex format, or a BuildTable still pointing at old resources.

## The loop, compressed

> Unpack → find by ID → export reference → edit in Blender → export glTF/DDS → import/replace in ATK → fix BuildTable + IDs across the three forges → repack → back up originals → install → test → repeat.
