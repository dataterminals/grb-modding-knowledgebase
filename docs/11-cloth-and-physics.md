# 11 — Cloth and physics (`.cloth` / MotionCloth)

Cloth (capes, coats, holsters, straps, pouches, loose fabric — anything that sways) is the GRB modder's white whale: it's the least-documented part of the pipeline and the active focus of the Tier 1 Imports community. This doc reverse-engineers the format **directly from ATK's own reader/writer code** (decompiled from `AnvilToolkit.dll` v1.3.1), so it is verified rather than inferred.

> **Source:** `AnvilToolkit.FileTypes.AnvilNext.Physics.MotionCloth.*` and `…Physics.Cloth*` classes, decompiled with `ilspycmd`. The serialization (`Read`/`Write`) and XML (`ReadXml`/`ToXml`) methods in those classes **are** the file format. Method/field names are ATK's. See [`meta/sources.md`](../meta/sources.md).

## Two cloth lineages

The Anvil engine has had two cloth systems, and ATK implements both:

| System | Classes | Used by |
| --- | --- | --- |
| **Legacy cloth** | `Cloth`, `ClothLOD`, `ClothSettings`, `ClothState`, `ClothActionSettings` | older AC games (AC2–Rogue, Unity, Syndicate) |
| **MotionCloth** (modern) | `ClothPackage` → `MotionBody` → `MotionSection`s | **Origins/Odyssey-era and GRB** |

**GRB uses MotionCloth.** ATK added `ClothPackage` support in v1.3.0, can load Cloth/SoftBody/MotionSoftBody in the Mesh Viewer, export them to GLB, and (per its changelog) "port Unity+ cloth to the older games." The rest of this doc focuses on **MotionCloth**, the GRB-relevant one.

## Top-level container: `ClothPackage`

A GRB cloth resource is a `ClothPackage`. Its binary layout (`ClothPackage.Read`/`Write`):

```
ClothPackage
├── int32   MotionBodyCount
└── for each MotionBody:
      ├── int32  blobLength        // length of this body's bytes
      └── byte[blobLength]         // a MotionBody, parsed independently
```

Each MotionBody is stored as a **length-prefixed blob** and parsed from its own sub-stream. ATK also exposes the whole package as **XML** (`ToXml`/`ReadXml`) with a `<List Name="MotionBodies">` — this XML is the human-editable form.

## A `MotionBody` is a list of sections

```
MotionBody  =  read sections until end-of-stream
```

`MotionBody.Read` simply loops `MotionSectionFactory.ReadSection(...)` until the sub-stream is exhausted. There is no body-level header — a body **is** its ordered list of sections.

## The section format (TLV chunks) — the core of the format

Every section is a tag-length-value chunk with an **8-byte header** (`MotionBody.Write` + `MotionSectionFactory.ReadSection`):

```
┌───────────────────────────────────────────────┐
│ uint16  SectionTypeID    // what kind of section│
│ uint16  0xECD7 (60631)   // magic; MUST match   │
│ int32   SectionSize      // INCLUDES the 8 bytes │
├───────────────────────────────────────────────┤
│ byte[SectionSize - 8]    // the section payload  │
└───────────────────────────────────────────────┘
```

- The constant **`60631` (0xECD7)** validates every section; ATK throws "Error reading Motion sections" if it's wrong. It's the reliable signature for "this is a MotionCloth section."
- `SectionSize` counts the header, so payload length = `SectionSize - 8`.
- **Unknown section types are preserved verbatim** (`UnknownSection`) — ATK round-trips sections it doesn't understand. This is great for safety: editing one section won't corrupt others.

### Sections are interdependent (counts precede buffers)

Many sections are **counters/sizes** that determine how to read a *later* buffer section. ATK looks **backward** through already-read sections to size the next one. Examples from `MotionSectionFactory`:

- `ClothConstraintsSizes` (4364) + `ClothStretchingConstraintsCount` (4381) → size `ClothConstraints` (4365).
- `ClothMeshIndexBufferSize` (4370) → size `ClothMeshIndexBuffer` (4371).
- `ClothUserData` (4354) `.UserVerticesCount` → size `ClothVerticesCurrentPosition` (4363) and `ClothMeshAABBTree` (4382).
- `ClothPerVertexDataCounters` (4530) → size the per-vertex buffers (4531/4532).

> **Practical consequence:** you cannot freely reorder sections or change vertex/constraint counts in isolation. The count sections and the buffer sections must stay consistent. Tuning *scalar properties* (gravity, stiffness, damping…) is safe; changing *topology* (vertex counts, constraints) means keeping every dependent buffer in sync.

## Section type catalogue

Full ID → class map is in [`reference/cloth-section-types.md`](../reference/cloth-section-types.md). The groups:

| ID range | Group | Purpose |
| --- | --- | --- |
| `513` | NamedObjectName | the body's name |
| `3073–3085` | **Body\*** | rigid-body data: type, transform, broadphase, color, island indices |
| `4353–4357` | **Cloth core** | `ClothType`, `ClothUserData`, **`ClothDefinition`** (feature flags), **`ClothProperties`** (tunables) |
| `4359–4366` | Constraints (enable/stiffness, engine loop, current positions, constraint buffers + SIMD) |
| `4369–4388` | Mesh constraints, index buffer, AABB trees, mesh-constraint buffers |
| `4394–4415` | Stretching constraints, **mesh mappings**, **LOD**, **Wind**, **Gravity**, azimuth/inclination/radius animation, constraint scale factor |
| `4433–4465` | **Presets** (named tuning presets), registered colliders count |
| `4529–4532` | Per-vertex data (definition, counters, buffer, SIMD) |
| `4561–4565` | Additional collision vertices (counters, triangle indices, barycentric coords) |
| `4657–4662` | **Editor data** (cloth ID, visibility, enabled colliders, **preset names**) — authoring metadata |
| `4833–4834` | Strips-untwisting indices |

## The two sections modders actually tune

### `ClothProperties` (section 4357) — the simulation knobs

A flat struct of scalar/vector/bool fields (verified field order & defaults from `ClothProperties.Read`):

| Field | Type | Default | Meaning (best understanding) |
| --- | --- | --- | --- |
| `CollisionAgainstPrimitivesAlgorithm` | byte | 1 | collision algorithm selector |
| `VerticesNormalsComputationIsEnabled` | bool | true | recompute normals each frame |
| **`Gravity`** | Vec3 | (0,0,-10) | gravity vector (−Z = down) |
| **`Damping`** | float | 0.05 | velocity damping (higher = stiffer/calmer) |
| `SkinWidth` | float | 0.2 | collision skin thickness |
| `BlendFactor` | float | 1.0 | blend toward animated/skinned pose |
| `StretchingConstraintsCoefficient` | float | 0 | stretch stiffness |
| `ContinuousCollisionIsEnabled` | bool | false | CCD |
| **`Friction`** | float | 0.01 | surface friction |
| `CollisionAgainstDeformableMeshIsEnabled` | bool | false | collide vs. deformable meshes |
| `CollisionAgainstClothIsEnabled` | bool | false | cloth-vs-cloth collision |
| `PriorityForClothClothCollision` | byte | 0 | cloth-cloth priority |
| **`TearingIsEnabled`** / `TearingThreshold` | bool/float | false / 0.01 | cloth tearing |
| `PruningExtent` | float | 10 | spatial pruning extent |
| **`MaxSpeed`** | float | 1000 | clamp on vertex speed |
| `RigidGroupsAreEnabled` | bool | false | rigid vertex groups |
| `MeshMappingTangentSpaceIsEnabled` | bool | false | tangent-space mapping |
| `CollisionWithStrandsIsEnabled` / `…ActivationThreshold` | bool/float | false / 1.1 | hair-strand collision |
| **`ClusteringIsEnabled`** / `ClusteringAligningEffect` / `ClusteringRepulsionForce` | bool/float/float | false / 0.5 / 1.0 | clustering solver |
| `BackStopLimitType` / `BackStopLimitAngle` | int/float | 0 / π | back-stop (prevents poke-through) |
| **`StripsUntwistingIsEnabled`** / `StripsUntwistingStiffness` | bool/float | false / 1.0 | anti-twist for straps |
| `UseSubstepping` / `SubstepTargetDT` / `UseInterpolation` | bool/float/bool | — | solver stepping |
| `ReferenceDisplacement*` (BiasVector, Threshold, BlendFactor, SearchStride) | Vec3/float/float/int | (1,1,1)/1/0/2 | reference-pose displacement |

> **Per-game truncation:** `ClothProperties.Write` stops early for older games — Unity omits everything after `RigidGroupsAreEnabled`; Syndicate omits everything after `MeshMappingTangentSpaceIsEnabled`. GRB writes the **full** struct. This is why ATK's "port cloth to older games" is lossy.
>
> **Forward/back-compatible reads:** `Read` guards every field after the core with `if (Position + n > EndOfSection) return;` — so a shorter section just leaves later fields at default. Lengthening/shortening the section is tolerated by design.

### `ClothDefinition` (section 4356) — the feature flags

A bank of booleans declaring **which solver features the cloth uses**: `UseStructuralConstraints`, `UseShearingConstraints`, `UseBendingConstraints`, `UseBackStopConstraints`, `UseMaxDistanceConstraints`, `UseStretchingConstraints`, `UseCollisionAgainstPrimitive/DeformableMesh/Cloth`, `UseWind`, `UseTearing`, `UseLod`, `UseClustering`, `UseClothOnGPU`, `UseStripsUntwisting`, `UseRegisteredColliders`, `MeshMappingsCount`, etc. (full list in the class).

These flags must **agree with the sections present**: e.g. `UseWind=true` implies a `ClothPropertiesWind` (4397) section exists; `UseClustering=true` pairs with the clustering fields in `ClothProperties`. Flipping a flag without providing/removing the matching data is a likely source of in-game breakage.

## How ATK exposes cloth (your editing surface)

1. **XML export/import.** Every section implements `ToXml`/`ReadXml`, with the element named for its base type and a `Type="<ConcreteClass>"` attribute. So a cloth resource exports to a readable XML tree of sections — **this is where you tune gravity/damping/stiffness/wind by hand.** Round-trips back to binary on import.
2. **Mesh Viewer (GLB).** ATK can load Cloth/SoftBody/MotionSoftBody into the Mesh Viewer and export to GLB to see/edit the cloth mesh geometry; it can also generate a SoftBody BuildTable from the Mesh Viewer.
3. **SoftBody → cloth generation.** The `SoftBody` class has `ClothGenerationSettings` (and `SimVertexDistance`) — ATK can generate cloth simulation data from a softbody/mesh, which is the likely path for *new* cloth rather than hand-writing every buffer section.

## A practical approach to cloth modding (working theory)

Grounded in the format above; treat as the current best workflow, to be confirmed empirically with the community:

1. **Tune existing cloth (safest):** export the `.cloth` to XML, edit `ClothProperties` (gravity, damping, friction, stiffness, wind, maxspeed) and/or toggle `ClothDefinition` flags, re-import. No topology change → low risk. Great for "this cape is too stiff / too floppy / clips too much."
2. **Re-mesh cloth (harder):** changing the cloth mesh means regenerating the dependent buffers (vertices, constraints, mesh constraints, per-vertex data, AABB trees). Prefer the **SoftBody/cloth-generation** path or porting a known-good cloth onto your geometry rather than editing buffer sections by hand.
3. **Attach cloth to a new garment:** the cloth must be wired to the mesh/skeleton via `ClothDefinition.MeshMappingsCount` + `ClothPropertiesMeshMappings` (4395) and the editor data (cloth ID, 4658). This binding is the least-understood part — see open questions.

## Open questions (cloth-specific)

Tracked in [`meta/research-log.md`](../meta/research-log.md):

1. **Mesh/skeleton binding:** exactly how `ClothPropertiesMeshMappings` + `ClothEditorDataClothID` tie a cloth body to a garment mesh and its bones.
2. **New-cloth authoring:** the reliable end-to-end path to add cloth to a garment that has none (SoftBody generation vs. transplanting an existing cloth).
3. **Which resource/`Extension` ID** a `.cloth`/ClothPackage carries in the forge entry table (so it can be found by type) — cross-reference [`02-forge-file-format.md`](02-forge-file-format.md).
4. **Buffer-section internals** (constraints, per-vertex SIMD data) for anyone wanting full re-meshing rather than property tuning.
5. **Empirical validation:** confirm in-game that XML-tuned `ClothProperties` behave as the field names suggest (e.g. `Damping`, `StripsUntwistingStiffness`).
