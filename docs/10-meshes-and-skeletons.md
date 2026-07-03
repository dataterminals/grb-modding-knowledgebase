# 10 — Meshes and skeletons

Meshes are the geometry of weapons, gear, bodies, hair, and props; skeletons rig the animated ones. This doc covers the mesh resource model and the glTF pipeline that bridges Blender and the game.

## The resource types

| Type | What it is |
| --- | --- |
| **Mesh** | Geometry: vertices (position, normals, tangents, binormals, UVs, vertex colors, weights) + index buffer, organized into primitives with material assignments. |
| **Skeleton** | Bone hierarchy (names, parent/child, bind transforms) that skinned meshes weight to. |
| **Cloth / SoftBody / MotionSoftBody** | Physics-deformable variants. ⚠️ For **other** Anvil games ATK can load/export these; for **GRB** its cloth/softbody reader is gated off (`SoftBody.SupportedGames` excludes GRB), so no Mesh-Viewer/GLB/generation — GRB cloth round-trips only as opaque bytes. See [`11-cloth-and-physics.md`](11-cloth-and-physics.md). |

## The glTF/GLB pipeline (the Blender bridge)

ATK exports and imports meshes as **glTF / GLB** (via SharpGLTF), with **GLB as the default**. This is the entire reason Blender works for GRB modding: GLB is a standard interchange format Blender reads and writes natively, and ATK translates between GLB and the game's internal mesh format.

**Export (game → Blender):** open a Mesh in ATK's Mesh Viewer, export to GLB, open in Blender. You get geometry, UVs, vertex colors, and (for skinned meshes) bones.

**Import (Blender → game):** export your edited mesh from Blender as GLB, import it in ATK's Mesh Viewer. ATK then:
- **Recalculates tangents and binormals** on import (1.3.0).
- **Quantizes** vertex data into the game's specific **vertex format** (improved quantization accuracy in 1.3.0).
- **Removes unused bones** on GRB import; normalizes vertex weights.
- Warns on **missing UVs** (and fills a default `(0,0)` if absent) and **missing vertex colors**.
- Can **replace** an existing mesh (matching ID) or load a **standalone GLB** as new content.

## Vertex formats — the sharp edge

GRB uses **multiple, specific vertex formats** (ATK "Rewrote all GRB Vertex Formats" and fixed many GRB-format bugs, including ones where "some GRB mesh formats read vertex colors as UVs"). A vertex format defines exactly how each vertex's attributes are packed (which channels exist, their types, quantization). The practical consequences:

- The replacement mesh must end up in a vertex format the target slot accepts. ATK exposes a **Vertex Format option** on import — don't ignore it.
- **Vertex colors matter** in GRB and are easy to get wrong. ATK supports Blender's two vertex-color naming schemes and uses application-specific accessor names for round-tripping. If your mesh renders with corrupted colors or misread UVs, suspect a vertex-format/vertex-color mismatch.
- Missing/!incorrect **tangents** were a classic crash ("Invalid Tangent"); ATK now recalculates them, but clean Blender normals/UVs make this reliable.

> **Match the donor.** The most reliable new mesh behaves like the one it replaces: same UV sets (GRB meshes can have **up to 5 UV sets**), same vertex-color usage, same rough vertex count budget, same skeleton if skinned.

## LODs (Level of Detail)

Meshes ship as a **LOD set**: `LOD0` (highest detail, close-up) through `LOD3` (lowest, distant). See [`08-naming-conventions.md`](08-naming-conventions.md). Rules of thumb:

- Provide the LODs the original had. If you only replace `LOD0`, the asset reverts to the *old* shape at distance (or pops/disappears).
- A quick-and-dirty mod sometimes copies the high-detail mesh into all LOD slots; correct mods author progressively simpler LODs.
- For hair/face, remember LODs multiply with **headgear variants** (`ForGoggles`, `ForHelmetGoggles`, `ForGazMask`, `ForNVG`, …) — one hairstyle is *(variants × LODs)* mesh resources.

## Skeletons and skinning

- A **Skeleton** resource defines the bones. ATK supports GRB skeletons, opens them in the Mesh Viewer by default, shows a bones list/treeview, and can set a "main skeleton."
- **Skinned meshes** weight vertices to bones. ATK enforces a **per-primitive bone limit** and warns/errors if exceeded — split or re-weight if you hit it.
- ATK can **update bone transforms from a GLB** and export skeletons to GLB/XML/BuildTable. Skinned-mesh import handles weights and bind matrices (several historical fixes around bind matrices and weight writing).
- If a skinned replacement deforms wrongly, suspect: wrong skeleton, bad weights, exceeded bone limit, or a bind-pose mismatch between Blender and the game skeleton.

## BuildTables from the Mesh Viewer

The Mesh Viewer can **generate a BuildTable** from a scene, a mesh, or a skeleton. This is a major convenience for new content: rather than hand-authoring the definition that tells the game how to assemble your asset, you can have ATK emit a starting BuildTable from your imported scene. (BuildTables: [`03-data-and-resources.md`](03-data-and-resources.md).)

> **Note (GRB):** ATK can also generate a BuildTable from a **SoftBody**, but that path — like all of ATK's SoftBody/cloth handling — is **gated off for GRB** (`SoftBody.SupportedGames` excludes GRB), so BuildTable-from-SoftBody is not available for GRB. Mesh/skeleton generation is GRB-enabled. See [`11-cloth-and-physics.md`](11-cloth-and-physics.md).

## Replacing a mesh — the short version

1. In ATK's Mesh Viewer, **export the original mesh (all LODs/variants) to GLB**; note its vertex format, UV sets, vertex-color usage, and skeleton.
2. Edit/replace in Blender, preserving UVs, scale, and rig.
3. Export GLB from Blender.
4. Import in the Mesh Viewer, choosing the right **Vertex Format**; replace the matching ID (or load as new content and generate a BuildTable).
5. Handle **every LOD and headgear variant** the original had.
6. Repack the resources forge (and patch the BuildTable / definition forges if needed); test up close *and* at distance, and under relevant headgear.

## Common failure modes

- **Vertex colors read as UVs / corrupted shading** → vertex-format or vertex-color-naming mismatch.
- **"Invalid Tangent" / crash on import** → bad/missing tangents or UVs in the source.
- **Asset reverts at distance** → missing LOD replacements.
- **Hair looks wrong only with certain headgear** → unhandled `For…` variant.
- **Bad deformation when animated** → skeleton/weight/bone-limit problem.
