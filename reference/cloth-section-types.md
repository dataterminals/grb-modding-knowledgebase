# Reference — MotionCloth section types

Complete `SectionTypeID → class` map **as modelled by ATK** — transcribed directly from `MotionSectionFactory.ReadSection` in ATK v1.3.1 (decompiled). Each section in a `MotionBody` starts with `uint16 TypeID`, `uint16 0xECD7 (60631)`, `int32 SizeIncludingHeader`. See [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) for the format.

> IDs are decimal as they appear in the source. Sections not listed fall through to `UnknownSection` (preserved verbatim by ATK). "sized by" means the section's length is computed from an earlier counter section rather than self-describing.

> **⚠️ This map is complete for ATK, NOT for GRB (verified 2026-08-09).** `MotionSectionFactory.ReadSection` has **64** `case` entries, but a sweep of **156 cloth bodies across 81 GRB cloth resources** found **86 distinct section types in use — 22 of which ATK does not model at all.** Those 22 are real, populated GRB sections that fall through to `UnknownSection`; ATK preserves their bytes but cannot interpret them. Because this KB's section knowledge was transcribed *from ATK*, those 22 have been invisible to every earlier pass. See [Sections GRB uses that ATK does not model](#sections-grb-uses-that-atk-does-not-model) below. **✅ Confirmed 2026-09-18: 13 of the 22 carry the render↔sim mesh mapping** — quantization headers, SIMD copies of the wrap's tangent/binormal bytes, and a per-mapping header and target name. See [the decoded block](#the-44034410-block--decoded-2026-09-18-the-rendersim-mesh-mapping).

## Body (rigid) sections

| ID | Class | Notes |
| ---: | --- | --- |
| 513 | `NamedObjectName` | object name |
| 3073 | `BodyType` | |
| 3074 | `BodyIndexInIsland` | |
| 3076 | `BodyUserData` | |
| 3077 | `BodyBroadPhase` | |
| 3078 | `BodyData` | |
| 3080 | `BodyColor` | |
| 3083 | `BodyTransform` | position/orientation |
| 3085 | `BodyIndexInIslandExtra` | |

## Cloth core

| ID | Class | Notes |
| ---: | --- | --- |
| 4353 | `ClothType` | |
| 4354 | `ClothUserData` | holds `UserVerticesCount` (sizes several buffers) |
| 4356 | `ClothDefinition` | **feature flags** (UseWind, UseTearing, UseClustering, …) + `sbyte MeshMappingsCount` at offset **24**. 40 B in all 156 GRB bodies; `MeshMappingsCount` ∈ {1, 2, 3} (see §4395 below). Also carries `UseMeshMappingTangentSpace` (**true in all 156**) and `UseMappingOnGPU`. |
| 4357 | `ClothProperties` | **simulation tunables** (Gravity, Damping, Friction, …) |

## Constraints & solver

| ID | Class | Notes |
| ---: | --- | --- |
| 4359 | `ClothPropertiesConstraintsEnable` | |
| 4360 | `ClothPropertiesConstraintsStiffness` | |
| 4361 | `ClothEngineLoopStepCount` | sizes 4362 |
| 4362 | `ClothEngineLoop` | sized by 4361 (`StepCount`) |
| 4363 | `ClothVerticesCurrentPosition` | `Vector4[]`, sized by `ClothUserData.UserVerticesCount` (rounded up to 16) |
| 4364 | `ClothConstraintsSizes` | 6 sizes; sizes 4365 |
| 4365 | `ClothConstraints` | `IntVector4[]`, sized by 4364 + 4381 |
| 4366 | `ClothConstraintsSIMDF8` | |
| 4378 | `ClothPropertiesConstraintsCorrectionFactors` | |
| 4381 | `ClothStretchingConstraintsCount` | sizes 4365 / 4394 |
| 4394 | `ClothStretchingConstraints` | `short[]`, sized by 4381 |
| 4415 | `ClothConstraintsScaleFactor` | |

## Mesh / geometry

| ID | Class | Notes |
| ---: | --- | --- |
| 4369 | `ClothMeshConstraintsOptimizedCount` | |
| 4370 | `ClothMeshIndexBufferSize` | sizes 4371 |
| 4371 | `ClothMeshIndexBuffer` | `Triangle[]`, sized by 4370 |
| 4373 | `ClothAABox` | bounding box |
| 4382 | `ClothMeshAABBTree` | sized by `ClothUserData` or `ClothMeshIndexBufferSize` depending on 4384/4385 |
| 4384 | `ClothMeshHasVertexAABBTree` | flag controlling 4382 |
| 4385 | `ClothMeshHasTriangleAABBTree` | flag controlling 4382 |
| 4387 | `ClothMeshConstraintsSizes` | sizes 4388 |
| 4388 | `ClothMeshConstraints` | `MeshConstraint[]`, sized by 4387 |

## Properties (tunable sub-sections)

| ID | Class | Notes |
| ---: | --- | --- |
| 4395 | `ClothPropertiesMeshMappings` | **`bool[64]` `MeshMappingsEnabled` — an enable bitmap, NOT a mapping table.** See below. |
| 4396 | `ClothPropertiesLod` | LOD config |
| 4397 | `ClothPropertiesWind` | wind response |
| 4398 | `ClothPropertiesGravity` | `Vector3` gravity (default 0,0,−10) |
| 4399 | `ClothPropertiesAzimuthAnimation` | |
| 4400 | `ClothPropertiesInclinationAnimation` | |
| 4401 | `ClothPropertiesRadiusAnimation` | |

### §4395 `ClothPropertiesMeshMappings` — decoded (verified 2026-08-09)

> **Verified (ATK source + 156-body corpus sweep).** ATK's reader is literally `for (i = 0; i < 64; i++) MeshMappingsEnabled[i] = br.ReadBoolean();` — the payload is a **fixed 64-byte array of booleans**, one per mesh-mapping slot. Payload length is **64 bytes in all 156 bodies**, no exceptions.
>
> **It does not contain any mapping data.** It only says *which* mapping slots are on. In all of vanilla GRB only two distinct values occur:
>
> | `MeshMappingsEnabled` | bodies | `ClothDefinition.MeshMappingsCount` |
> | --- | ---: | --- |
> | slot `0` only | 6 | 1 |
> | slot `0` only | 123 | 2 |
> | slots `0` and `1` | 27 | 3 |
>
> Slots `2–63` are **never** used in vanilla. The engine therefore supports up to **64** mesh mappings per cloth body while shipped content uses 1–2.
>
> **The relationship to `MeshMappingsCount` (§4356) is deterministic but not an identity** — `MMC=1` and `MMC=2` both yield exactly one enabled slot. Why the count exceeds the enabled-slot total for `MMC∈{2,3}` is **unresolved**; a plausible-but-unverified reading is that the final declared slot is implicit/reserved.
>
> **§4395 occurs TWICE per `MotionBody`**, paired with the two `ClothProperties` (§4357) blocks, and **both copies are byte-identical** in every body examined. A tool that edits only the first copy will produce an inconsistent resource.
>
> ⚠️ **Consequence for the rebind goal: this section is not the rebind lever.** It is a gate, not a binding. Whatever the mappings *are*, their payload is stored elsewhere — see [Sections GRB uses that ATK does not model](#sections-grb-uses-that-atk-does-not-model).

## Presets & colliders

| ID | Class | Notes |
| ---: | --- | --- |
| 4433 | `ClothPresets` | |
| 4434 | `ClothPresetsCount` | |
| 4435 | `ClothPresetDefinition` | |
| 4436 | `ClothPresetBufferSize` | |
| 4443 | `ClothPresetDefinitionPerVertexData` | |
| 4444 | `ClothPresetPerVertexDataSize` | |
| 4465 | `ClothRegisteredCollidersCount` | |

## Per-vertex data

| ID | Class | Notes |
| ---: | --- | --- |
| 4529 | `ClothPerVertexDataDefinition` | |
| 4530 | `ClothPerVertexDataCounters` | sizes 4531 / 4532 |
| 4531 | `ClothPerVertexDataBuffer` | `byte[]`, sized by 4530 (`PerVertexDataBufferSize × 16`) |
| 4532 | `ClothPerVertexDataSIMDF8` | sized by 4530 (`PerVertexDataSIMDSize`) |

> **⚠️ GRB per-sim-vertex PAINT is stored separately, and BARE (verified 2026-07-03).** Distinct from the 4529–4532 sections above, the 6 per-sim-vertex *paint* arrays that ATK's `MotionSoftBodyLOD` reader exposes — `VertexMaxDistance`, `BackStop`, `GravityScale`, `Damping`, `SkinWidth`, `Friction` (MaxDistance first) — are **length-prefixed** in ATK's *supported* games, but **GRB writes them BARE: `6 × byte[V]` contiguous** (no length prefixes), the run ending exactly at the enclosing `ClothPackage`'s trailing `int32 blobLen`. So to read/edit `VertexMaxDistance` on a GRB cloth, take the **first `V` bytes** of that `6·V` run. Verified on both Tactical Kilt cloths and both their LODs. (This is `MotionSoftBodyLOD`-level data, *not* a MotionSection TLV — see [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md).)

## Additional vertices (4561–4565) — small per-triangle point set

⚠️ **Not the render↔sim binding.** An earlier version claimed these bound the render mesh to the sim mesh; that's wrong — the render mesh is a separate, much larger, skeleton-skinned mesh (Walker LOD0: 1816 verts vs 170 sim), and these sections describe only **`A` extra points** (62 on Walker LOD0) bound per sim **triangle** by barycentric coords. Role likely collision (ATK's class name is *"additional collision vertices"*); unconfirmed. The **format** below is byte-exact and stands. Stored as a CSR layout indexed **per sim triangle** (`N` = triangle count). Verified on Walker LOD0 (170 sim verts, 288 tris, `A`=62, `M`=64).

| ID | Class | Notes |
| ---: | --- | --- |
| 4561 | `ClothAdditionalVerticesCounters` | `{int32 AdditionalVerticesBufferSize N, int32 AdditionalVerticesSIMDSize M}`; `N` = sim triangle count, `M` = `A` padded to ×8; sizes 4562/4563/4565 |
| 4562 | `ClothAdditionalVerticesTriangleVerticesCount` | `byte[N]`, **per sim triangle**: # additional verts on it (`sum = A`) |
| 4563 | `ClothAdditionalVerticesTriangleFirstVertexIndex` | `ushort[N]`, **per sim triangle**: first additional-vertex index (CSR offset into the `A`-list); `4563[last]+4562[last]=A` |
| 4564 | `ClothAdditionalVerticesBarycentricCoordinatesParameters` | `SIMDF8` = `{Scale, Offset, Magic}`; `Scale` = per-LOD normalization (`maxStoredWeight/255`), `Magic = Scale·255` (Walker LOD0 0.524, LOD1 0.751 — not a fixed ½) |
| 4565 | `ClothAdditionalVerticesBarycentricCoordinatesData` | `ushort[M]`, one per additional vert (tail padded `0xFFFF`); decode = split hi/lo bytes, `weight = byte·Scale + Offset` → two of the triangle's barycentric weights (fixed vertex slots, index-buffer order), third = `1−u−v`. Verified: stored ≤ Magic, reconstructed positions inside sim bbox. Open: the exact slot permutation (render mesh / in-game). |

> Present only in some cloths (e.g. `TP_WalkerCoat_Cloth`); many GRB cloths omit 4561–4565 entirely. Triangle `t`'s 3 sim verts are `ClothMeshIndexBuffer(4371)[3t..3t+2]`. These points are **not** the render-mesh binding (the render mesh is separately skeleton-skinned); how the cloth drives the render mesh is an open question — see [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md).

## Editor metadata (authoring)

| ID | Class | Notes |
| ---: | --- | --- |
| 4657 | `ClothEditorData` | |
| 4658 | `ClothEditorDataClothID` | **null-terminated string; EMPTY in all 156 vanilla bodies.** See below. |
| 4659 | `ClothEditorDataVisibility` | |
| 4661 | `ClothEditorDataCollisionEnabledColliders` | |
| 4662 | `ClothEditorDataPresetsNames` | named presets |

### §4658 `ClothEditorDataClothID` — decoded (verified 2026-08-09)

> **Verified (ATK source + corpus sweep).** ATK reads it as `ClothID = br.ReadNullTerminatedString()` — it is a **string**, not a numeric resource ID. In **all 156 vanilla bodies** the payload is a **single `0x00` byte**, i.e. **the empty string**.
>
> This is **authoring-time editor metadata that GRB ships blank.** It carries no reference to a mesh, a skeleton, or another resource, and it is *not* a `ClassID`. An earlier note in this file described it as "the cloth's editor ID (attachment)" — that framing implied a binding role it does not have.
>
> ⚠️ **Consequence for the rebind goal: this section is not the rebind lever either.** There is nothing here to repoint.

## Strips untwisting

| ID | Class | Notes |
| ---: | --- | --- |
| 4833 | `ClothStripsUntwistingIndicesCount` | sizes 4834 |
| 4834 | `ClothStripsUntwistingIndices` | `ushort[]`, sized by 4833 |

## Sections GRB uses that ATK does not model

> **Verified 2026-08-09** by sweeping every `*Cloth*.data` under the game's `Extracted\` tree: **205 files seen, 81 containing real `ClothPackage`s, 156 `MotionBody`s**. Those bodies use **86 distinct section types**; `MotionSectionFactory.ReadSection` handles **64**. The **22** below are populated in real GRB cloths and have **no ATK class** — they fall through to `UnknownSection`.
>
> This matters more than a gap in a table: everything this KB knows about cloth sections was transcribed from ATK, so **these 22 have never been looked at.** They are the natural place for the render↔sim mapping that §4395 merely *enables* and §4356 merely *counts*.

`V` = sim vertex count, `T` = sim triangle count for the body. "n" = occurrences across the 156-body corpus.

| ID | n | Payload size | Shape |
| ---: | ---: | --- | --- |
| **4374** | 333 | 19 B | **mesh-mapping header** — one per mapping (= `MeshMappingsCount`). `i32 renderCount \| i32 ? \| u8 isRenderMapping \| i32 bound (0 = all) \| …` *(decoded 2026-09-18)* |
| **4376** | 333 | 12 B | **position `(u,v)` quantization** `{scale, min, max}` *(2026-09-18)* |
| **4377** | 333 | 12 B | **position `h` quantization** *(2026-09-18)* |
| **4379** | 333 | 12 B | **normal `(u,v)` quantization** *(2026-09-18)* |
| **4380** | 333 | 12 B | **normal `h` quantization** *(2026-09-18)* |
| **4386** | 183 | 41–43 B | **mapping target name** — `<Mesh>_VIS_0x…` for the render mapping, `Sim_<Mesh>_LOD<n>_0x…` for a LOD↔LOD one *(2026-09-18)* |
| 4389 | 333 | varies (64, 80, 96, …) | multiple of 16; once per mapping group — *not decoded* |
| 4390 | 333 | varies (32, 48, 64, …) | multiple of 16; once per mapping group — *not decoded* |
| 4391 | 333 | varies (64, 80, 96, …) | multiple of 16; once per mapping group — *not decoded* |
| 4392 | 333 | varies (32, 48, 64, …) | multiple of 16; once per mapping group — *not decoded* |
| 4393 | 333 | varies (64, 80, 90, …) | once per mapping group — *not decoded* |
| **4403** | 156 | 12 B | **tangent `(u,v)` quantization** `{scale, min, max}` — ~~counter for 4404~~ |
| **4404** | 156 | varies | **tangent `(u,v)` bytes**, u8, AoSoA-4 — ~~4-byte elements~~ |
| **4405** | 156 | 12 B | **tangent `h` quantization** — ~~counter for 4406~~ |
| **4406** | 156 | varies | **tangent `h` bytes**, u8, one per cloth-driven render vertex |
| **4407** | 156 | 12 B | **binormal `(u,v)` quantization** |
| **4408** | 156 | = 4404 | **binormal `(u,v)` bytes**, AoSoA-4 — ~~second copy of the 4404 pair~~ |
| **4409** | 156 | 12 B | **binormal `h` quantization** |
| **4410** | 156 | = 4406 | **binormal `h` bytes** — ~~second copy of the 4406 pair~~ |
| 4414 | 127 | varies (892, 1372, 2560, …) | large |
| 4445 | 79 | varies (48, 80, 112, …) | |
| 4660 | 63 | varies (1, 216, 258, …) | |

### The 4403–4410 block — DECODED (2026-09-18): the render↔sim mesh mapping

> **Verified on all 156 bodies; geometry verified on 87 distinct cloth LODs / 489,472 render vertices.**
> Tool: [`tools/clothmap.py`](../tools/clothmap.py). Full provenance: the 2026-09-18 entry in
> [`meta/research-log.md`](../meta/research-log.md).

The block is **not** a set of counters and buffers of its own. It is the MotionBody's copy of part of the
**render↔sim wrap** — the per-render-vertex binding that `docs/11` calls *"the stored wrap"*, stored after
each LOD's `ClothPackage`. Every render vertex the cloth drives has one 20-byte record:

```
u8 u[pos,nrm,tan,bin] | u8 v[pos,nrm,tan,bin] | u8 h[pos,nrm,tan,bin] | u16 sim[3] | u16 1
```

Each of the four vertex attributes — **position, normal, tangent, binormal** — is a point `(u, v, h)` on the
record's sim triangle, quantized to one byte per component:

```
value = min + byte × scale          (max − min) / scale = 254.5;  bytes span 0…254
weights (u, v, 1 − u − v)            on (sim[0], sim[1], sim[2])
position = Σ wᵢ (xᵢ + h · nᵢ)        nᵢ = the cage's vertex normals
normal / tangent / binormal = unit(Σ w'ᵢ xᵢ + h' · unit(Σ wᵢ nᵢ) − position)
```

What each section holds:

| section | holds |
| --- | --- |
| **4374** | mapping header: `i32 renderCount`, `i32 ?`, `u8 1` (render mapping), `i32 bound` (**0** when every render vertex is bound) |
| **4376 / 4377** | position `(u,v)` / `h` quantization `{scale, min, max}` |
| **4379 / 4380** | normal `(u,v)` / `h` quantization |
| **4386** | the mapping's target mesh name, `<Mesh>_VIS_0x…` |
| **4403 / 4405** | tangent `(u,v)` / `h` quantization |
| **4404** | tangent `(u,v)` bytes, **AoSoA-4**: `[u of records 0–3][v of records 0–3][u of 4–7]…` |
| **4406** | tangent `h` bytes, one per record |
| **4407 / 4409** | binormal `(u,v)` / `h` quantization |
| **4408** | binormal `(u,v)` bytes, AoSoA-4 |
| **4410** | binormal `h` bytes |

Every pad byte in §4404–4410 — the partial last AoSoA block and the tail up to a multiple of 16 — is that
section's own byte 0. The same 16 quantization floats also sit in the wrap block itself, which is laid out
as a GPU buffer with offsets in dwords; see [`docs/11`](../docs/11-cloth-and-physics.md).

**One §4374…§4380 group per mesh mapping.** A body carries 1, 2 or 3 groups — `{1: 6, 2: 123, 3: 27}`,
exactly the §4356 `MeshMappingsCount` distribution, and `6 + 2·123 + 3·27 = 333` is the occurrence count of
each of these sections. Exactly one group per body is the render mapping (§4374 byte 8 = `1`) and it is
*not always the first* (group 1 in 16 bodies). The others map to **another LOD's sim cage** — their first
`i32` is that LOD's vertex count in all 177, and their §4386, where present, names that LOD's `Sim_…` body.
That is why `MeshMappingsCount` exceeds the §4395 enabled slots: §4395 enables render mappings only.

**Still open:** §4374's second `i32`; §4389–4393 (also once per mapping group, not decoded); where the
LOD↔LOD mappings' own records are; why only tangent and binormal get SIMD copies in the body.

> ⚠️ **Editing rule that falls out of this:** a rebind changes the wrap block **and** §4374, §4376–4380,
> §4386 and §4403–4410 together — they are the same numbers stored twice. Change one without the other and
> the body disagrees with itself.

<details>
<summary>The 2026-08-09 reading, superseded — kept for provenance</summary>



> **Verified:** four `12-byte counter → variable buffer` pairs, present **exactly once per `MotionBody` in all 156 bodies**. `size(4404) == size(4408)` and `size(4406) == size(4410)` in every body, and `size(4404) == 2 × size(4406)` — i.e. **two parallel structures, each a 4-byte-element array alongside a 2-byte-element array of the same length.** That is the classic shape of an index+payload mapping table, and *two* of them echoes the 1–2 enabled slots in §4395.
>
> **Element counts are far larger than the simulation mesh** and do not track `V` or `T` by any fixed ratio:
>
> | Cloth | `V` | `T` | `4404 ÷ 4` |
> | --- | ---: | ---: | ---: |
> | `TP_WalkerCoat_Cloth` LOD0 | 170 | 288 | 636 |
> | `IanBlake_TrenchCoat_Cloth` LOD0 | 186 | 305 | 1124 |
> | `Cloth_ArcturusGhostGhillieHood` LOD0 | 107 | 190 | 18 972 |
>
> ⚠️ **Inferred, NOT confirmed — do not treat as the binding yet.** The decisive check available today came out **negative**: the KB records `TP_WalkerCoat` LOD0 as **1816 render vertices** vs 170 sim, but its `4404` holds **636** elements — so this is *not* a one-entry-per-render-vertex table. It is some intermediate structure of unknown meaning. What is established is only that these buffers are render-scale rather than sim-scale, are structured as paired index/payload arrays, and have never been examined.
>
> **Next step:** these sections have no ATK reader to crib from, so decoding them means working from the bytes directly (as with the wrap records) — start with the 12-byte counters (`4403`/`4405`/`4407`/`4409`, presumably 3×`int32`) and see whether their fields predict the buffer lengths.



</details>
