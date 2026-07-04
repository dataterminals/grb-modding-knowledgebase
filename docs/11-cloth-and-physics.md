# 11 — Cloth and physics (`.cloth` / MotionCloth)

Cloth (capes, coats, holsters, straps, pouches, loose fabric — anything that sways) is the GRB modder's white whale: it's the least-documented part of the pipeline and the active focus of the Tier 1 Imports community. This doc reverse-engineers the format **directly from ATK's own reader/writer code** (decompiled from `AnvilToolkit.dll` v1.3.1), so it is verified rather than inferred.

> **Source:** `AnvilToolkit.FileTypes.AnvilNext.Physics.MotionCloth.*` and `…Physics.Cloth*` classes, decompiled with `ilspycmd`. The serialization (`Read`/`Write`) and XML (`ReadXml`/`ToXml`) methods in those classes **are** the file format. Method/field names are ATK's. See [`meta/sources.md`](../meta/sources.md).

> ## ⚠️ In-game status (2026-07-02) — read before the ATK / tuning sections
> Two things earlier drafts of this doc got wrong. Both are corrected inline below; this is the summary:
> 1. **ATK cannot structurally read GRB cloth.** Its cloth/softbody reader is gated off for GRB (`SoftBody.SupportedGames` excludes `GhostReconBreakpoint`), so there is **no** Mesh-Viewer, GLB export, XML export, or cloth-generation for GRB cloth — ATK only round-trips it as **opaque bytes** on repack. So wherever this doc says "export the cloth to XML/GLB and edit it," that is ATK's capability for its *supported* games, **not GRB**. Editing GRB cloth means raw-section work ([`../tools/motioncloth.py`](../tools/motioncloth.py)) + a **compressed** `.data` repack.
> 2. **Cloth-parameter edits show no in-game effect — but this is UNRESOLVED, confounded by a forge shadow.** Reversing/zeroing gravity (both the §4357 `ClothProperties` field *and* the dedicated §4398 `ClothPropertiesGravity`), zeroing stiffness (§4360), cranking wind (§4397), and freeing MaxDistance all produced **zero** visible change on a genuinely-simulated Tactical Kilt, with edits confirmed read back from the *repacked* `DataPC.forge`. **⚠️ HOWEVER (2026-07-03):** ~44/56 cloths (incl. the kilt) are **duplicated across `DataPC.forge` and a WorldMap base forge** (`DataPC_TGT_WorldMap_Bootstrap_Split.forge`), and we only ever edited the `DataPC` copy. If the game loads the WorldMap copy, these nulls are **shadowing, not runtime-inertness**. So earlier "gravity/params are inert at runtime" claims (incl. the 2026-07-02 "DEFINITIVE") are **DOWNGRADED and unresolved**, pending a confirmed-loaded (complete patch-override) test. Also: patch-overriding a cloth in only one of its two base-forges' patches **hangs the load**. See [`../meta/research-log.md`](../meta/research-log.md) (2026-07-03) and [`../meta/project-goal.md`](../meta/project-goal.md).
>
> Also verified 2026-07-02: a cloth `.data` written with **raw/uncompressed** blocks **crashes GRB at load** — it must be Oodle-compressed (see [`02-forge-file-format.md`](02-forge-file-format.md)). Full detail: [`../meta/research-log.md`](../meta/research-log.md) (2026-07-02).

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
| `4561–4565` | **Additional vertices** — small per-triangle point set, barycentric on sim triangles (likely collision; *not* the render binding — see the render↔sim section) |
| `4657–4662` | **Editor data** (cloth ID, visibility, enabled colliders, **preset names**) — authoring metadata |
| `4833–4834` | Strips-untwisting indices |

## The two sections that carry the tunables

> **⚠️ Runtime-effectiveness caveat (GRB, 2026-07-02).** The fields below are the *authored* tunables, verified from `ClothProperties.Read`. But **editing them in the `ClothProperties` (4357) struct does not necessarily change GRB at runtime** — the `Gravity` field there is **verified inert in-game**. GRB appears to read the **dedicated sibling sections** instead (`ClothPropertiesGravity` 4398, `ClothPropertiesWind` 4397, `ClothPropertiesConstraintsStiffness` 4360 — see [`../reference/cloth-section-types.md`](../reference/cloth-section-types.md)). Which of those are live is under test (Step 1 in [`../meta/next-session.md`](../meta/next-session.md)). Treat the 4357 struct as authoring metadata until a given field is confirmed live.

### `ClothProperties` (section 4357) — the authored simulation knobs

A flat struct of scalar/vector/bool fields (verified field order & defaults from `ClothProperties.Read`):

| Field | Type | Default | Meaning (best understanding) |
| --- | --- | --- | --- |
| `CollisionAgainstPrimitivesAlgorithm` | byte | 1 | collision algorithm selector |
| `VerticesNormalsComputationIsEnabled` | bool | true | recompute normals each frame |
| **`Gravity`** | Vec3 | (0,0,-10) | gravity vector (−Z = down). ⚠️ Editing this showed no in-game effect — but so did editing the dedicated §4398 copy; **both results are confounded by a forge shadow (2026-07-03) and unresolved** (see the status banner). |
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

## How ATK exposes cloth — for its *supported* games (⚠️ NOT GRB)

> **⚠️ None of the three surfaces below run for GRB.** ATK's cloth/softbody reader is gated off for GRB (`SoftBody.SupportedGames` — see "The tooling gap" below), so for GRB cloth these are unavailable; this is what ATK offers for the games it *does* support (AC2…Syndicate). For GRB, edit at the raw-section level ([`../tools/motioncloth.py`](../tools/motioncloth.py)) and repack a **compressed** `.data`.

1. **XML export/import.** Every section implements `ToXml`/`ReadXml`, with the element named for its base type and a `Type="<ConcreteClass>"` attribute. So a cloth resource exports to a readable XML tree of sections — where (for supported games) you tune gravity/damping/stiffness/wind by hand. Round-trips back to binary on import.
2. **Mesh Viewer (GLB).** ATK can load Cloth/SoftBody/MotionSoftBody into the Mesh Viewer and export to GLB to see/edit the cloth mesh geometry; it can also generate a SoftBody BuildTable from the Mesh Viewer.
3. **SoftBody → cloth generation.** The `SoftBody` class has `ClothGenerationSettings` (and `SimVertexDistance`) — ATK can generate cloth simulation data from a softbody/mesh, the likely path for *new* cloth rather than hand-writing every buffer section.

## The binding problem — why a vanilla `.cloth` "refuses to take on" a new mesh

This is the question the Tier 1 Imports community is stuck on (SamiPuma): *"we can reference [a `.cloth`] in buildtables, but it refuses to take on."* His test case was **Walker's coat** — weight-paint a new coat mesh, point the BuildTable at the vanilla cloth like the original does, and it simply doesn't simulate.

### Real example (verified on-disk)

Walker's coat is **three coupled resources** in `DataPC.forge` (note: cloth lives in the **main `DataPC` forge, not Resources**):

| Entry (unpack #) | Name | What it is |
| --- | --- | --- |
| `34223` | `TP_Tacvest_Walker_Coat` | small (~0.5 KB) definition — references the render mesh |
| `34224` | `TP_WalkerCoat_Cloth` | a **MotionCloth** resource — **72** sections (0xECD7 magic), ~101 KB |
| `35720` | `Cloth_WalkerCoat` | a **MotionCloth** resource — **102** sections, ~188 KB |

> The leading numbers here are the **unpacked positional indices** (`<N>_-_<Name>`), **not** the 64-bit file IDs — the real ID is each resource's embedded `ClassID`. See [`03-data-and-resources.md`](03-data-and-resources.md).

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
- `ClothAdditionalVertices*` (4561–4565) — a small set of extra points bound per sim **triangle** by barycentric coordinates (likely collision; *not* the render-mesh binding — see the correction note further below).
- `ClothPerVertexData*` (4529–4532) — per-vertex sim attributes indexed to those same vertices.

When you swap in a **new** coat mesh (different vertex count/order/positions — even if it looks similar), every one of those bakes now points at vertices that don't correspond to your mesh. The engine can't map the sim onto your render geometry, so the cloth **fails to bind and is dropped** → "refuses to take on." The `Mesh` class even carries an `IsGeneratedFromCloth` flag, underscoring that the render mesh and the cloth sim mesh are produced together, not independently.

### The "weight paint" is `MaxDistance`, stored as a vertex color

A key clarification for anyone weight-painting cloth: the value that controls cloth behavior per vertex is **`VertexMaxDistance`** — how far a vertex may move from the skinned/animated pose (**0 = fully pinned** to the body, **higher = free to swing**). In ATK's cloth/softbody GLB export, `VertexMaxDistance` is baked into vertex color `Color1` (verified in `SoftBody`/`MotionSoftBodyLOD` → GLB conversion) — so this cloth "paint" is a **vertex-color channel**, *not* an ordinary skin weight. ⚠️ **But that GLB export does not run for GRB** (the cloth reader is gated off — see "The tooling gap" below), so you can't currently get this Blender view for a GRB cloth through ATK; on GRB, `VertexMaxDistance` lives in the raw per-vertex paint arrays inside the cloth LOD (edit at the section level). Either way, painting ordinary skin weights alone will not produce cloth motion.

### The tooling gap (why it "can't be used right now")

**ATK v1.3.1's hardcoded cloth reader is gated off for GRB** — so the Mesh-Viewer, GLB export, `ToMesh`, and cloth **generation** never run on GRB cloth. `Cloth : SoftBody` uses `SoftBody.Read`, whose very first line throws unless the game is in `SoftBody.SupportedGames` = {AC2, Brotherhood, Revelations, AC3, AC3Remastered, BlackFlag, Rogue, Unity, Syndicate} — **`GhostReconBreakpoint` is not in it**. The exception is caught and the resource is marked `Failed`, so its states/LODs/ClothPackage are never parsed by that path; `FileHandler`'s Mesh-Viewer cloth action checks `SoftBody.SupportedGames` directly and returns empty for GRB. (This is also why the `MotionClothLOD`/`ClothLOD` LOD schemas don't describe GRB's bytes — both LOD families exclude GRB too; see the render↔sim section below.)

> **Two separate ATK paths — and why neither is our cloth route.** Beyond the hardcoded reader (gated off for GRB), ATK has a **schema-driven** XML export/import path (`FileHandler.HandleSchemaXML` → `DataStorage.ActiveSchema.ExportXml`/`ImportXml`) that serializes typed resources generically from a data schema, independent of `SoftBody.SupportedGames`. In principle this *could* reach cloth sections — but it is **not confirmed to work for GRB `Cloth`** (no loaded GRB schema is known to cover it end-to-end), and in practice **every GRB cloth edit to date has gone through the raw-byte tools** ([`../tools/motioncloth.py`](../tools/motioncloth.py)) + a compressed `.data` repack, **not** ATK XML. So treat "tune GRB cloth via ATK XML" as **unverified and unused**, not a working route. *(And even if it worked, editing a value ATK writes doesn't help where the runtime ignores it — e.g. `ClothProperties.Gravity`; see the status banner.)* The schema path also does **not** give mesh-viewer/GLB/**generation**, so the render↔sim rebind for new geometry stays unsolved for GRB either way.

## A practical approach to cloth modding (current best guidance)

Ordered by reliability with today's tools:

1. **Tune existing cloth (research lever, runtime-effect under test):** ATK **cannot XML-export GRB cloth**, so tuning is done by editing the raw MotionCloth sections directly ([`../tools/motioncloth.py`](../tools/motioncloth.py)) and repacking a **compressed** `.data`. ⚠️ **Whether *any* cloth-parameter edit affects GRB at runtime is UNRESOLVED:** gravity (both §4357 and the dedicated §4398), stiffness (§4360), wind (§4397), and MaxDistance all showed **no in-game effect** — but those results are **confounded by a forge shadow** (the cloth is duplicated across `DataPC.forge` and a WorldMap base forge; we edited only one) and remain unconfirmed. Not a reliable knob yet — see the status banner and [`../meta/next-session.md`](../meta/next-session.md).
2. **Reshape, don't re-topologize (the soundest route):** edit the **vanilla** garment mesh **keeping the same vertex count and order** (move/reskin/retexture, don't add/remove/reorder vertices). The vanilla cloth's index-addressed constraints + per-vertex mappings still line up, so the cloth should still take on. This is the cloth analogue of "preserve topology when replacing a mesh." Silhouette changes are limited.
3. **Edit the cloth's `MaxDistance` paint (raw-section; ATK GLB path unavailable for GRB):** `VertexMaxDistance` (per-vertex pin↔free) is the drape/pinning control. ATK's GLB `Color1` route for editing it **does not run for GRB** (cloth reader gated off), so on GRB it must be edited in the raw per-vertex paint arrays at the section level. Runtime effect on GRB is **untested** (same open question as the tunables above).
4. **New garment with brand-new topology (blocked):** requires regenerating the cloth sim + render↔sim mapping for your mesh. ATK has no GRB cloth-generation, so this isn't reliably doable in-tool yet. Workarounds to explore: conform your mesh to the vanilla sim surface and reuse vanilla counts; or build the missing remap step. **This is the frontier.**

> **Bottom line for Sami:** the cloth didn't take on because `Cloth_WalkerCoat` is bound to the *vanilla* coat's vertices, not to a name — your new mesh has different vertices, so the baked mapping is invalid. The reliably-achievable win today is **reshape the vanilla garment while preserving its sim-cage vertex count and order** (constraints are index-addressed). Parameter *tuning* is possible only via raw-section edits + a compressed repack, and **whether ANY cloth-parameter edit moves GRB cloth at runtime is UNRESOLVED** — every param tested (gravity §4357/§4398, stiffness §4360, wind §4397, MaxDistance) showed no effect, but confounded by a forge shadow (2026-07-03). Adding cloth to genuinely new topology needs a render↔sim rebind step that isn't solved for GRB. **But note (per Sami's actual goal, [`../meta/project-goal.md`](../meta/project-goal.md)): the real objective is *rebinding* cloth to a new mesh, not tuning — and a promising alternative is GRB's ATK-readable `.skeleton` bone-physics path.** *(Note: the XML/GLB cloth workflows this doc references are ATK's capability for its **supported** games — they don't run for GRB.)*

## The render↔sim remap — design, and what ATK already gives us

> **⚠️ Update (2026-07-01, later) — the "4561–4565 is the render↔sim binding" claim below is WRONG; corrected here.** After parsing the real render mesh (`TP_Tacvest_Walker_Coat_LOD0.Mesh`) I can rule that model out. What actually holds:
> - **The render mesh is far larger than the cloth's "additional vertices."** Walker LOD0 render mesh = **1816 vertices / 3263 triangles** (verified three ways: vertex-buffer size ÷ stride, max index = 1815, `MeshPrimitive.NumVertices` = 1816); LOD1 = 956. The cloth's `ClothAdditionalVertices*` describe only **62** (LOD0) / 114 (LOD1) points. So `render ≠ sim + additional` (1816 ≠ 170 + 62), and **4561–4565 is *not* the full render↔sim binding.**
> - **The render mesh is an ordinary skeleton-skinned mesh.** Its per-vertex skinning is **two-bone** (weights sum to 255 for all 1816 verts) with bone indices spanning only **0..23** — a skeleton, not the 170 sim vertices. So the render mesh does **not** store a per-vertex binding to the sim mesh.
> - The 62 "additional vertices" reconstruct (barycentric on sim triangles) to points **on the sim surface** but do **not** coincide with render vertices (nearest render vert ≈ 2% of mesh scale away, same offset as the sim verts themselves). They are a small **per-triangle** set — consistent with ATK's literal class name *"additional **collision** vertices."* Their exact role is unconfirmed.
> - What is **still correct** below and stands: ATK can't read GRB cloth at all (the `SoftBody.SupportedGames` gate); the byte-exact 4561–4565 **structure/sizing/decode** (CSR + the per-LOD-normalized quantization); and `tools/motioncloth.py`.
>
> **⚠️ IN-GAME UPDATE (2026-07-01): the model is UNTESTED in-game (inconclusive tests — a wrong-subset edit).** Live tests edited ghillie cloths (wrap twist/collapse, 10×-reversed gravity), verified applied to the running forge — all showed no visible change. But the edits covered only **11 of ~33 base ghillie cloths** (the wrapped subset), and the tester's specific ghillie very plausibly uses one of the other 22 (no patch/mod overrides the base ghillie cloths, so wrong-*file* is the likely cause). The tester confirms ghillie strands **do** respond to movement and wind — i.e. they **are** cloth-simulated — so an earlier "ghillie strands are skinned" note was **wrong and is retracted.** Net: the null results are **inconclusive (wrong subject/file), not disconfirming.** **"Wrap = render driver" is neither confirmed nor disproven — still untested.** To make it clean: edit *all* ghillie cloths (or the tester's exact item), gravity-control first (must billow a working cloth), then wrap-collapse. See [`meta/research-log.md`](../meta/research-log.md) (2026-07-01 "RETRACTION" entry). The static findings below stand; their runtime role is simply not yet validated.
>
> **⚠️ Update (2026-07-02):** further testing sharpened two things here. (a) The ghillie strands are **pinned** (`VertexMaxDistance ≈ 0`) — they move from skinned motion, not free sim — so they were a poor wrap subject regardless. (b) The "run the `--gravity` control first" advice is now unreliable: editing the gravity field showed no in-game effect (later found to be confounded by a forge shadow, 2026-07-03 — see the status banner), so it can't serve as a positive control. Gravity testing has moved to the **dedicated section 4398** (see the status banner at the top and [`../meta/next-session.md`](../meta/next-session.md)). The wrap-as-render-driver question remains **in-game unvalidated**.
>
> **Net (static analysis — now downgraded, see the in-game update above): the render↔sim wrap appears STORED in the cloth.** Each cloth LOD carries, *after* its sim `ClothPackage`, a large per-LOD block (~35 KB for Walker LOD0) holding the render mesh's data — including a **per-render-vertex binding to ~3 nearby sim vertices** (fixed ~20-byte records; the render vertex count 1816 prefixes it). Evidence: the region holds ~5833 sim-valued indices ≈ 1816 render verts × 3; the records are a **fixed 20-byte layout** — `[u16 flag][6× u16][3× u16 sim vertex index]` — and the 3 sim indices per record form **tight local triangles** (median spread ≈ 1.5 sim-edge-lengths, vs. mesh-scale for random triples). Reconstructing `Σ wₖ·simP[idxₖ]` lands ≈0.013 from a render vertex (the sim↔render frame offset). So the render mesh follows the sim mesh via a **stored wrap** (render vert → local sim triangle + weights), *not* runtime proximity. ~70% of render verts (**1268**/1816 — the exact record count confirmed below; an earlier phase-scan estimate of 1361 is superseded) are bound; the rest are likely rigid/skeleton-only. This is the real render↔sim binding — the `4561–4565` "additional vertices" are a separate small collision set. The block layout is `[small header][reindex-grouping table][1268 wrap records]`: exactly **1268 contiguous 20-byte records** (one per *bound* render vertex — ~70% of the 1816), preceded by a `0xFFFF`-delimited table that groups the 1268 record indices into ~547 buckets (loosely sim-vertex-related). **Still to decode:** the **6-u16 weight encoding** (doesn't decode as a plain normalized barycentric — sums to ~1.2–1.5, ~0 correlation with the nearest render vert's barycentric) and the **record↔render-vertex correspondence** (records carry no render index; ordered by the grouping table, not mesh-buffer order). These are entangled and hit a static-analysis wall — the exact bucket key isn't pinned (169 buckets share a common sim vertex but only 72 distinct). **Best path now: an in-game round-trip** — write a best-effort encoder (new render vert → nearest sim triangle + barycentric, in the confirmed `[flag][weights][3 sim idx]` form) and validate by loading in GRB. See [`meta/research-log.md`](../meta/research-log.md) (the 2026-07-01 "hunt the wrap" / "Wrap record structure" / "Wrap block sub-structure" entries). The subsections below are kept for the verified 4561–4565 section-format details; their *interpretation* ("additional = render verts") is superseded.

This is the frontier task (bind a vanilla `.cloth` to a *new* garment mesh). The sections below document what's verified about the cloth's own data; the render-driving mechanism itself is the open piece.

### Survey: two binding schemes exist (verified)

Extracting and scanning **all 56 `Cloth`-typed resources in `DataPC.forge`** (via the forge index + Oodle; see [`tools/`](../tools/README.md)) shows GRB garment cloths split into two render↔sim binding schemes:

- **Plain (majority)** — no `ClothAdditionalVertices*` (4561–4565) sections. Just the sim mesh + constraints. Examples: `IanBlake_TrenchCoat_Cloth` (186 sim verts / 305 tris), `JaceSkell_Jacket_Cloth`, most ghillies.
- **With additional-vertices (subset)** — also carries the `ClothAdditionalVertices*` sections: `A` extra points bound per-triangle to the sim mesh (barycentric). Examples: **`TP_WalkerCoat_Cloth`** (170 sim verts / 288 tris, `A`=62), `Cloth_HunterCoat`, `Tsec_Madera_Coat_Cloth`, `Cloth_Hunter_Hood`.

> ⚠️ *An earlier version of this section called these "direct vs barycentric render↔sim binding" schemes and claimed the second binds the render mesh to the sim mesh. That is wrong (see the correction note above): the render mesh is a separate, much larger, skeleton-skinned mesh in both cases, and the additional-vertices sections are a small per-triangle point set (likely collision), not the render binding.* The **Cloth Inspector** currently labels these "DIRECT / BARYCENTRIC" — that wording should be revised. What still holds for reskinning: constraints are addressed by sim-vertex index, so a reshape must preserve the **sim** mesh's vertex count and order.

### The exact binding data (verified from `MotionSectionFactory`)

The sim mesh:
- `ClothUserData.UserVerticesCount` (4354) — sim vertex count `V`.
- `ClothVerticesCurrentPosition` (4363) — `Vector4[(V+15)&~15]`, sim vertex rest positions.
- `ClothMeshIndexBufferSize` (4370) → `ClothMeshIndexBuffer` (4371) — `Triangle[]`, sim topology.

**The `ClothAdditionalVertices*` sections** describe **`A` extra points bound per-triangle to the sim mesh** by barycentric coordinates. ⚠️ *These are a small set (62 on Walker LOD0), not the render mesh — see the correction note above; their role (likely collision) is unconfirmed.* The layout is a compact per-triangle (CSR) form, sized off `ClothAdditionalVerticesCounters` (4561 = `{AdditionalVerticesBufferSize N, AdditionalVerticesSIMDSize M}`). Verified on Walker LOD0 (170 sim verts, 288 sim tris): `N = 288 = triangle count`, `A = 62`, `M = 64`. The section format itself (below) is byte-exact and stands regardless of what the points are used for:
- `ClothAdditionalVerticesTriangleVerticesCount` (4562) — `byte[N]`, indexed **per sim triangle**: how many additional points sit on triangle *t*. `sum = A`.
- `ClothAdditionalVerticesTriangleFirstVertexIndex` (4563) — `ushort[N]`, indexed **per sim triangle**: the first additional-point index for triangle *t* (CSR offset into the `A`-length list). `4563[last] + 4562[last] = A`. Triangle *t*'s 3 sim verts are `IndexBuffer(4371)[3t .. 3t+2]`.
- `ClothAdditionalVerticesBarycentricCoordinatesParameters` (4564) — a `SIMDF8` = 3 floats `{Scale, Offset, Magic}`. `Scale` is a **per-LOD normalization** (`Scale = maxStoredWeight / 255`), and `Magic = Scale·255` = that max. It is **not** a fixed ½ bound: Walker LOD0 = `{0.0020564, ≈0, 0.5244}`, LOD1 = `{0.0029458, ≈0, 0.7512}`.
- `ClothAdditionalVerticesBarycentricCoordinatesData` (4565) — `ushort[M]`, **one ushort per additional vertex** (M = `A` padded up to a multiple of 8; tail padded with `0xFFFF`). **Decode:** split each ushort into two bytes; `weight = byte·Scale + Offset` gives **two** of the triangle's three barycentric weights (at fixed vertex slots, in the sim index-buffer's vertex order), and the third weight = `1 − u − v`. Verified on Walker: every stored weight is `≤ Magic` (0/62 and 0/114 exceed), the tail is all `0xFFFF`, and reconstructing each additional vertex's rest position from the sim rest positions (4363) lands **inside the sim-mesh bbox for all of them**. *(Inferred, needs the render mesh or an in-game trial to pin: the exact slot permutation — which two of the three vertices are stored, which byte is which, and which is derived. The derived third is **not** consistently the largest weight, so the encoding uses a fixed per-triangle vertex order, not magnitude sorting.)*

### What a reskin encoder needs — and the open blocker

An earlier draft here described an encoder that recomputes `ClothAdditionalVertices*` for a new render mesh. **That plan was based on the wrong model** (see the correction note above): 4561–4565 is a small per-triangle point set, not the render mesh's binding, so re-encoding it would not rebind a new garment. The genuine binding was since **located** (see the "Net" note above): the cloth stores a **per-render-vertex wrap** — ~1268 fixed 20-byte records — in the per-LOD block *after* the sim `ClothPackage`, each binding a render vertex to ~3 local sim vertices (+ weights). Two things still block a reskin encoder: **(1)** the record's **weight encoding** and the record↔render-vertex correspondence are only partly decoded, and **(2)** the wrap's role as the actual runtime render driver is **in-game unvalidated** (the one direct edit-test hit pinned ghillie strands — an invalid subject — see the in-game update above). Settling (2) on a genuinely-simulated, player-viewable garment is the prerequisite before investing in the encoder.

**Still-useful pieces for whenever the mechanism is settled:**
- **The GRB render `Mesh` format is now parseable** (see the research log): `Mesh` → `CompiledMesh` → `ClusteredMeshData`, vertex format `Pos3s_Norm4ub_…` (stride 36; position = `int16 × QuantizationFactor`), two-bone skeleton skinning. This is what let us disprove the model, and it's the tool for validating any future binding hypothesis against real geometry.
- **ATK's barycentric math** (`FindNearestTriangleWithIndices` + `computeTriBarycentricCoords` in `Cloth.cs`) is a ready reference if a proximity wrap turns out to be the mechanism — but note ATK's generator emits the `SoftBodyVertexMapping` form for Unity/Syndicate, which GRB doesn't use.
- **The 4561–4565 section encoding is byte-exact** (CSR + per-LOD-normalized quantization, above) via [`tools/motioncloth.py`](../tools/motioncloth.py), should those points ever need editing.

**Reshape-in-place still works** without any of this: for cloths where you keep the vanilla **sim** mesh's vertex count and index order (constraints are index-addressed), you can move/reskin/retexture — the "reshape, don't retopologize" path documented above.

## Open questions (cloth-specific)

Tracked in [`meta/research-log.md`](../meta/research-log.md):

1. **How does a GRB MotionCloth drive its render mesh? — CANDIDATE MECHANISM (stored wrap located; in-game UNVALIDATED).** The render mesh is a separate, larger, skeleton-skinned mesh (Walker LOD0: 1816 verts vs 170 sim). The cloth stores a strong candidate for the render↔sim binding as a **per-render-vertex wrap** in its per-LOD block after the sim `ClothPackage`: ~1268 fixed 20-byte records, each tying a render vert → ~3 nearby sim vertices (+ weights), supported by the local-triangle geometry test (see the "Net" note above). **Not yet confirmed as the runtime driver** — the one direct in-game edit-test hit pinned ghillie strands (an invalid subject), so the wrap's live role is still open. Remaining: (a) validate in-game on a genuinely-simulated, player-viewable garment; (b) decode the record **weight encoding** + the render-vertex-order correspondence — then a reskin encoder can regenerate the wrap (nearest sim triangle + barycentric, ATK's `computeTriBarycentricCoords` math) for a new mesh. Verified along the way: the GRB render `Mesh` format is parseable (`ClusteredMeshData`, `Pos3s` stride-36, int16×QuantizationFactor, two-bone skeleton skinning).
2. ~~**Two cloth resources per garment**~~ — **answered** (see the Walker diff above): they are different-purpose (gameplay-wearable vs. cinematic), each with per-LOD bodies named `Sim_<Mesh>_LOD<n>`.
3. ~~**A fully accurate MotionCloth parser.**~~ — **built.** [`tools/motioncloth.py`](../tools/motioncloth.py) walks sections by their self-declared sizes (validated against `MotionSectionFactory`'s counter→buffer rules in [`reference/cloth-section-types.md`](../reference/cloth-section-types.md)) and round-trips byte-for-byte. The Cloth Inspector uses it (accurate counts + additional-vertices detection). Remaining cloth-tool work is the *write/encode* side for the remap, not parsing.
4. **The ragdoll bone-collider list** found in the wearable cloth's editor data (`Ragdoll_Head…;LeftArm…` bone+hash string) — decode its exact structure; it names the skeleton bones the cloth collides against, and is likely part of binding cloth to a character.
5. **BuildTable side:** the exact property/node a BuildTable uses to reference a cloth, and whether the mesh must also carry a cloth link (the `IsGeneratedFromCloth` mesh + a matching `ClothEditorDataClothID`).
6. ~~**`Extension` (resource-type) id** for a ClothPackage in the forge entry table~~ — **answered**: the forge resource is typed **`Cloth`** (`3811591354`); `ClothPackage` is nested and has no id. See the hierarchy above and [`reference/resource-type-ids.md`](../reference/resource-type-ids.md).
7. **Empirical validation (in progress, 2026-07-02):** partially answered — the `ClothProperties.Gravity` field (section 4357) is **verified inert at runtime**, and there is **no ATK XML path** for GRB cloth (so "XML-tuned `ClothProperties`" isn't the test). Reframed: confirm in-game whether the **dedicated** sections (`ClothPropertiesGravity` 4398, `ClothPropertiesWind` 4397, `ClothPropertiesConstraintsStiffness` 4360) and the per-vertex **`MaxDistance`** paint are runtime-effective — edited at the raw-section level and repacked as a compressed `.data`. Step 1 (4398 gravity on the Tactical Kilt) is in [`../meta/next-session.md`](../meta/next-session.md).
