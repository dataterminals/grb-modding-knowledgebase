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

## The resource hierarchy: `Cloth` → … → `ClothPackage`

The **top-level forge resource** for a GRB garment cloth is typed **`Cloth`** (resource-type id `3811591354` = `CRC32("Cloth")` — see [`reference/resource-type-ids.md`](../reference/resource-type-ids.md)), *not* `ClothPackage`. `ClothPackage` is a **nested sub-object**, three levels down. The full chain (verified from `Cloth`/`MotionClothState`/`MotionClothLOD` and confirmed empirically by parsing a real `_Cloth.data`):

```
Cloth                       (type id 3811591354 — the forge resource)
  └─ MotionClothState        (1629082830)
       └─ MotionClothLOD     (693470191)   ← one per LOD
            └─ ClothPackage                 ← nested; no id of its own
                 └─ MotionBody[] → MotionSection[]   ← the format below
```

(`SoftBody` `1263847064` and `MotionSoftBody` `2559966986` are sibling physics resource types for non-garment deformables. There is **no** `ClothPackage` resource-type id — it's always embedded in a LOD.) **Verified:** `1687_-_TP_Top_Bodark_Trench_Cloth.data` holds one resource whose embedded `Extension = 3811591354` (`Cloth`).

### Nested container: `ClothPackage`

Its binary layout (`ClothPackage.Read`/`Write`):

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

## The binding problem — why a vanilla `.cloth` "refuses to take on" a new mesh

This is the question the Tier 1 Imports community is stuck on (SamiPuma): *"we can reference [a `.cloth`] in buildtables, but it refuses to take on."* His test case was **Walker's coat** — weight-paint a new coat mesh, point the BuildTable at the vanilla cloth like the original does, and it simply doesn't simulate.

### Real example (verified on-disk)

Walker's coat is **three coupled resources** in `DataPC.forge` (note: cloth lives in the **main `DataPC` forge, not Resources**):

| File ID | Name | What it is |
| --- | --- | --- |
| `34223` | `TP_Tacvest_Walker_Coat` | small (~0.5 KB) definition — references the render mesh |
| `34224` | `TP_WalkerCoat_Cloth` | a **MotionCloth** resource — **72** sections (0xECD7 magic), ~101 KB |
| `35720` | `Cloth_WalkerCoat` | a **MotionCloth** resource — **102** sections, ~188 KB |

(Naming patterns across the game: `Cloth_<Name>` and `<Name>_Cloth`; many ghillie/coat/dress/strap items have them — `Cloth_HunterCoat`, `IanBlake_TrenchCoat_Cloth`, `FTciv_Dress_MontionCloth` (sic), etc.)

### Diffing the two Walker cloths — they are different-purpose, not redundant

Parsing both resources ([`tools/cloth_inspect.py`](../tools/cloth_inspect.py)) decodes the **body names**, which settle what each is for:

| Resource | Bodies (decoded names) | Purpose |
| --- | --- | --- |
| `34224 TP_WalkerCoat_Cloth` | 1 body: **`Sim_TP_Tacvest_Walker_Coat_LOD1`** | the **gameplay / player-wearable** coat cloth |
| `35720 Cloth_WalkerCoat` | 2 bodies: **`Sim_TPri_CIN__LOD0`** + **`Sim_TPri_CIN_Walker_Coat_LOD1`** | the **cinematic** ("CIN") cloth for cutscene Walker |

So the pair isn't "two takes on the same cloth" — one drives the **wearable gear item** (`TP_Tacvest_Walker_Coat`), the other the **cinematic NPC** (`TPri` = third-person primary character, `CIN` = cinematic), at higher fidelity. The section makeup matches that split (approximate counts):

- **Wearable (`34224`)** carries the full **constraint solver buffers** — `ClothConstraintsSizes`, `ClothConstraints`, `ClothStretchingConstraints(+Count)`, `ClothMeshConstraintsSizes`, `ClothPresets` — and a **ragdoll bone-collider list** embedded in its editor data (`Ragdoll_Head…;LeftArm…Fore…Hand…Shoulder…Neck…Right…`), i.e. the skeleton bones the cloth collides against.
- **Cinematic (`35720`)** adds **wind** (`ClothPropWind` ×4), `ClothEngineLoop`, `BodyTransform`/`BodyColor`, and `ClothAABox` — richer, wind-driven motion for cutscenes — and ships **two LODs** (LOD0 + LOD1).

### The key lead: a cloth body name encodes its target mesh + LOD

Every body is named **`Sim_<TargetMeshName>_LOD<n>`** (e.g. `Sim_TP_Tacvest_Walker_Coat_LOD1`). That is the human-readable trace of the cloth↔mesh binding: a cloth body is authored *for one specific mesh at one specific LOD*. Practical consequences for modding:

- When modding the **wearable** coat, the cloth to study/reuse is **`TP_WalkerCoat_Cloth`** (the `TP_Tacvest_…` gameplay one), **not** the cinematic `Cloth_WalkerCoat`.
- Cloth is **per-LOD**: a garment that simulates at multiple LODs needs a cloth body per mesh LOD, each bound to that LOD's geometry.
- This is why a name-only BuildTable reference is insufficient (see below): the binding is per-mesh-per-LOD, baked into the body.

### Why the BuildTable reference isn't enough

**A `.cloth` is welded to one specific mesh's vertex layout.** A BuildTable reference just *names* which cloth to attach; the actual binding lives **inside the cloth data**, baked for the vanilla mesh's exact geometry:

- `ClothUserData.UserVerticesCount` (4354) — a fixed simulation-vertex count.
- `ClothVerticesCurrentPosition` (4363) — those sim vertices' rest positions, in the **vanilla** mesh's space.
- `ClothConstraints` / `ClothStretchingConstraints` / `ClothMeshConstraints` / `ClothMeshIndexBuffer` — the spring network and sim topology, addressed **by vertex index**.
- `ClothAdditionalVerticesBarycentricCoordinatesData` (4565) — a `ushort[]` mapping **render-mesh vertices onto sim-mesh triangles by barycentric coordinates**. This is the render↔sim binding, and it is computed for the vanilla render mesh's exact vertex order.
- `ClothPerVertexData*` (4529–4532) — per-vertex sim attributes indexed to those same vertices.

When you swap in a **new** coat mesh (different vertex count/order/positions — even if it looks similar), every one of those bakes now points at vertices that don't correspond to your mesh. The engine can't map the sim onto your render geometry, so the cloth **fails to bind and is dropped** → "refuses to take on." The `Mesh` class even carries an `IsGeneratedFromCloth` flag, underscoring that the render mesh and the cloth sim mesh are produced together, not independently.

### The "weight paint" is `MaxDistance`, stored as a vertex color

A key clarification for anyone weight-painting cloth: the value that controls cloth behavior per vertex is **`VertexMaxDistance`** — how far a vertex may move from the skinned/animated pose (**0 = fully pinned** to the body, **higher = free to swing**). When ATK exports a GRB cloth/softbody to **GLB it bakes `VertexMaxDistance` into vertex color `Color1`** (verified in `SoftBody`/`MotionSoftBodyLOD` → GLB conversion). So the cloth "paint" you see/edit in Blender is a **vertex-color channel**, *not* an ordinary skin weight. Painting skin weights alone will not produce cloth motion.

### The tooling gap (why it "can't be used right now")

ATK's cloth **generation** path — `SoftBody.ClothGenerationSettings` (build sim data from a mesh) — has `SupportedGames = AC2 … Syndicate` and **does not include Ghost Recon: Breakpoint**. So ATK can **read, export (GLB/XML), edit, and repack** GRB cloth, but it **cannot regenerate** a GRB cloth's sim mesh + constraints + barycentric mapping for new geometry. That missing "rebind cloth to my mesh" step is exactly what blocks new-garment cloth on GRB today.

## A practical approach to cloth modding (current best guidance)

Ordered by reliability with today's tools:

1. **Tune existing cloth (works now, low risk):** export the `.cloth` to **XML**, edit `ClothProperties` (gravity, damping, friction, stiffness, wind, maxspeed) and/or `ClothDefinition` flags, re-import. No topology change. Great for "this cape is too stiff/floppy/clips."
2. **Reshape, don't re-topologize (works now, with care):** edit the **vanilla** garment mesh **keeping the same vertex count and order** (move/reskin/retexture, don't add/remove/reorder vertices). The vanilla cloth's barycentric + per-vertex mappings still line up, so the cloth should still take on. This is the cloth analogue of "preserve topology when replacing a mesh." Silhouette changes are limited.
3. **Edit the cloth's `MaxDistance` paint (works now):** export the cloth/softbody to GLB, adjust the **`Color1` vertex colors** (MaxDistance) in Blender to change what's pinned vs. free, re-import. Tunes drape/pinning without re-topology.
4. **New garment with brand-new topology (blocked):** requires regenerating the cloth sim + render↔sim mapping for your mesh. ATK has no GRB cloth-generation, so this isn't reliably doable in-tool yet. Workarounds to explore: conform your mesh to the vanilla sim surface and reuse vanilla counts; or build the missing remap step. **This is the frontier.**

> **Bottom line for Sami:** the cloth didn't take on because `Cloth_WalkerCoat` is bound to the *vanilla* coat's vertices, not to a name — your new mesh has different vertices, so the baked mapping is invalid. Until there's a GRB cloth-generation/remap tool, the achievable wins are: **tune** vanilla cloth, **reshape vanilla topology** rather than replace it, and **repaint the MaxDistance (Color1) vertex colors**. Adding cloth to a genuinely new mesh needs the regeneration step ATK doesn't yet do for GRB.

## The render↔sim remap — design, and what ATK already gives us

This is the frontier task (bind a vanilla `.cloth` to a *new* garment mesh). Decompiling the MotionCloth binding path and surveying every GRB cloth turns it from a mystery into a concrete, scoped engineering problem.

### Survey: two binding schemes exist (verified)

Extracting and scanning **all 56 `Cloth`-typed resources in `DataPC.forge`** (via the forge index + Oodle; see [`tools/`](../tools/README.md)) shows GRB garment cloths split into two render↔sim binding schemes:

- **Direct (majority)** — no `ClothAdditionalVertices*` (4561–4565) sections. The simulated mesh vertices *are* the render vertices (1:1), or the render mesh shares the sim vertices. Examples: `IanBlake_TrenchCoat_Cloth` (186 sim verts / 305 tris), `JaceSkell_Jacket_Cloth`, most ghillies.
- **Barycentric (subset)** — carries the `ClothAdditionalVertices*` sections. A low-res **sim mesh** drives extra **render ("additional") vertices** via a per-vertex *triangle + barycentric* binding. Examples: **`TP_WalkerCoat_Cloth`** (the wearable coat — 170 sim verts / 288 tris), `Cloth_HunterCoat`, `Tsec_Madera_Coat_Cloth`, `Cloth_Hunter_Hood`.

> Which scheme a garment uses decides your reskin strategy. **Direct** cloths demand your new mesh keep the sim vertex count *and* index order (constraints are addressed by vertex index). **Barycentric** cloths let the render mesh differ from the sim mesh — but the binding is baked for the vanilla render mesh, which is the remap problem below. You can tell them apart by checking whether the cloth's sections include `ClothAdditionalVertices*` (4561–4565); surfacing that in the cloth tooling is part of the next build.

### The exact binding data (verified from `MotionSectionFactory`)

The sim mesh:
- `ClothUserData.UserVerticesCount` (4354) — sim vertex count `V`.
- `ClothVerticesCurrentPosition` (4363) — `Vector4[(V+15)&~15]`, sim vertex rest positions.
- `ClothMeshIndexBufferSize` (4370) → `ClothMeshIndexBuffer` (4371) — `Triangle[]`, sim topology.

The render↔sim binding (barycentric scheme), sized off `ClothAdditionalVerticesCounters` (4561 = `{AdditionalVerticesBufferSize N, AdditionalVerticesSIMDSize}`):
- `ClothAdditionalVerticesTriangleVerticesCount` (4562) — `byte[N]`, sim verts per binding (typically 3).
- `ClothAdditionalVerticesTriangleFirstVertexIndex` (4563) — `ushort[N]`, start index into the sim index buffer of the bound triangle → the 3 sim verts are `IndexBuffer[first..first+2]`.
- `ClothAdditionalVerticesBarycentricCoordinatesParameters` (4564) — a `SIMDF8` dequant scale/offset.
- `ClothAdditionalVerticesBarycentricCoordinatesData` (4565) — `ushort[]` quantized barycentric weights (SIMD-packed, 8-wide).

### ATK already implements the algorithm — it's just GRB-gated

`Cloth.FromMeshSet(visualMesh, simMesh, settings)` builds a cloth by calling, **per render vertex**, `GenerateVisualMapping` → `FindNearestTriangleWithIndices(simPositions, visualPos)` then `computeTriBarycentricCoords(...)`. That is exactly the remap: for each new render vertex, find the nearest sim triangle and compute its barycentric coordinates. The math (plane projection + area-ratio barycentrics) is in [`Cloth.cs`] `computeTriBarycentricCoords`.

The catch: this generator is **disabled for GRB** — `SoftBody.SupportedGames` is `AC2…Syndicate` only, checked in `FileHandler` before the Mesh-Viewer cloth path — and it emits the **`SoftBodyVertexMapping`** (legacy `ClothLOD`) representation, whereas GRB writes the **packed `ClothAdditionalVertices*` sections** (`MotionClothLOD` → `ClothPackage`). So two gaps remain: (a) the GRB gate, and (b) a converter from the computed mapping to GRB's packed section encoding.

### The remap recipe (to build)

For the **barycentric** scheme, keeping the vanilla sim mesh:
1. Parse the target cloth → sim vertices (4363) + sim triangles (4371) + existing binding sections.
2. Author the new render mesh **in the vanilla mesh's space** (conform it roughly to the vanilla garment surface).
3. For each new render vertex: `FindNearestTriangle` in the sim mesh → `computeTriBarycentricCoords` (ATK's exact method) → `(triangleFirstVertexIndex, verticesCount=3, barycentric)`.
4. Re-encode `ClothAdditionalVerticesCounters/…VerticesCount/…FirstVertexIndex/…BarycentricParameters/…BarycentricData` for the new render-vertex set; leave the sim mesh, constraints, and per-vertex data untouched.
5. Re-serialize the ClothPackage → resource → `.data` → forge.

For the **direct** scheme, there's no barycentric layer to recompute: the new mesh must reuse the vanilla sim vertex count and index order (the "reshape, don't retopologize" path already documented).

**Still to finish (next build):** an accurate section parser/writer (the `MotionSectionFactory` sizing is now known), the mapping→packed-section encoder, and **in-game validation**. The geometry itself is solved (ATK's code).

## Open questions (cloth-specific)

Tracked in [`meta/research-log.md`](../meta/research-log.md):

1. **The render↔sim remap — characterized, build pending.** The algorithm is ATK's own `GenerateVisualMapping` (nearest sim triangle + `computeTriBarycentricCoords`); the encoding target is the packed `ClothAdditionalVertices*` (4561–4565) sections; two binding schemes exist (direct vs barycentric). Remaining: an accurate section writer + mapping encoder + in-game test. See "The render↔sim remap" above.
2. ~~**Two cloth resources per garment**~~ — **answered** (see the Walker diff above): they are different-purpose (gameplay-wearable vs. cinematic), each with per-LOD bodies named `Sim_<Mesh>_LOD<n>`.
3. **A fully accurate MotionCloth parser — sizing rules now known.** [`tools/cloth_inspect.py`](../tools/cloth_inspect.py) is still *approximate* (it magic-scans `0xECD7`). But the exact counter→buffer dependencies are now transcribed from `MotionSectionFactory` (e.g. 4363 sized by `(UserVerticesCount+15)&~15`; 4371 by `ClothMeshIndexBufferSize`; 4562/4563 by `AdditionalVerticesBufferSize`; 4565 by `AdditionalVerticesSIMDSize`; 4531 by `PerVertexDataBufferSize*16`) — see [`reference/cloth-section-types.md`](../reference/cloth-section-types.md). Building the accurate walker (needed for the remap encoder) is now a transcription job, not a research one.
4. **The ragdoll bone-collider list** found in the wearable cloth's editor data (`Ragdoll_Head…;LeftArm…` bone+hash string) — decode its exact structure; it names the skeleton bones the cloth collides against, and is likely part of binding cloth to a character.
5. **BuildTable side:** the exact property/node a BuildTable uses to reference a cloth, and whether the mesh must also carry a cloth link (the `IsGeneratedFromCloth` mesh + a matching `ClothEditorDataClothID`).
6. ~~**`Extension` (resource-type) id** for a ClothPackage in the forge entry table~~ — **answered**: the forge resource is typed **`Cloth`** (`3811591354`); `ClothPackage` is nested and has no id. See the hierarchy above and [`reference/resource-type-ids.md`](../reference/resource-type-ids.md).
7. **Empirical validation:** confirm in-game that XML-tuned `ClothProperties` and repainted `MaxDistance` behave as expected.
