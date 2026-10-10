# Notes: the entity layer, Wildlands → Breakpoint (2026-10-10)

Working notes for the Bolivia port: what changes between Ghost Recon Wildlands (GRW) and
Ghost Recon Breakpoint (GRB) in the serialized bytes of **Entity**, **LODSelector**,
**GridCellDataBlock**, the light types (**SpotLight**, **OmniLight**, **AreaLight**) and,
as a stretch, **EntityGroup**. Each rule is labeled *format* (true of every asset: a converter
must apply it) or *content* (Ubisoft re-baked that asset: the value differs, the layout does not).
Meant to be folded into [`research-log.md`](research-log.md).

Everything below was read from the two installs, read-only. The converter built from these
rules is [`tools/grw_entities.py`](../tools/grw_entities.py). It is checked the way
[`tools/grw2grb.py`](../tools/grw2grb.py) checks meshes: **`convert(GRW payload)` compared with
GRB's own payload**, over every resource both games ship under one ClassID.

## Results at a glance

| Type | Twins (same ClassID in both games) | convert(GRW) vs GRB | GRW world sample that converts |
| --- | --- | --- | --- |
| LODSelector | 239 | 17 byte-identical, 222 content-only, 0 unexplained | 3,839 / 3,839 (100%) |
| GridCellDataBlock | 4 | 4 content-only (the layout is the same in both games) | 700 / 700 (100%) |
| SpotLight | 28 | 2 byte-identical, 25 content-only, 1 where GRB *added* a flare | 164 / 164 (100%) |
| OmniLight | 1 | 1 content-only | 659 / 659 (100%) |
| AreaLight | 1 | 1 content-only | 228 / 228 (100%) |
| Entity | 171 | 21 byte-identical, 82 content-only, 0 unexplained; 68 hold a component type with no layout yet (13 of them vehicles) | 3,570 / 3,805 (93.8%): 65.9% with twin-validated rules only, 27.9% also using rules inferred from the world samples |
| EntityGroup | 27 | none decodable yet (every twin holds a component with no layout) | 3,279 / 3,766 (87.1%): 4.9% twin-validated only, 82.2% also inferred (mostly MergedPhysicsComponent, cGameplayDestructibleComponent, PropsPropertiesComponent and the sound components) |

*Content-only* means every byte that differs sits in a field this note classifies as per-asset
content: bounding boxes, light intensities, LOD distances, re-pointed references and similar.
*Unexplained* would mean a format gap; the selftest fails on any.

> **Verified (selftest, 2026-10-10):** the table above is the output of
> `python tools/grw_entities.py selftest --grb-ghostroom <vanilla GRB Ghost Room forge>` (see
> [Tools](#tools)). It reports PASS: no unexplained twin difference, and no conversion error in
> the world sample.

World coverage comes from a sample of the GRW Bolivia forges (`DataPC_GRN_WorldMap.forge` +
`_patch_01`). Every 60th forge entry was read (1,573 entries). Of the resources found, every
5th Entity, 6th LODSelector and 2nd EntityGroup was kept, and every light and GridCellDataBlock.
Scaled by 60, the sample matches the population counts we already had: Entity ≈ 1.14 M,
LODSelector ≈ 1.38 M, EntityGroup ≈ 452 k, OmniLight ≈ 40 k, AreaLight ≈ 14 k, SpotLight ≈ 10 k.

## Where the twins come from

- **Ghost Room:** GRW `DataPC_GRN_GhostRoom(.forge, _patch_01)` against a *vanilla* GRB
  `DataPC_GRN_GhostRoom.forge`. 50 Entity, 26 SpotLight, 4 GridCellDataBlock, 1 OmniLight and
  1 AreaLight. If the install's Ghost Room has been modded, pass a backup of the original with
  `--grb-ghostroom`.
- **Shared entry IDs:** every entry of type Entity, LODSelector, EntityGroup, EntityBuilder or
  MeshShape whose ID exists in both installs (759 entries). All target-type resources inside them
  were paired by ClassID. Ghost Room forges are left out of this pass; the pass above covers them.
- **Totals:** 171 Entity, 239 LODSelector, 28 SpotLight, 27 EntityGroup, 4 GridCellDataBlock,
  1 OmniLight and 1 AreaLight. None of the 471 pairs is byte-identical as shipped.

The twins are mostly props and prefabs. Bolivia's world entities are dominated by
Visual + RigidBodyComponent props, so **world** samples of each game were also decoded to check
that each layout holds beyond the twins. GRB's are from `DataPC_TGT_WorldMap_MaungaNui_Split.forge`.

## Serialization basics (both games)

> **Verified (ATK source + bytes):** ATK's generic object reader
> (`AnvilToolkit.FileTypes.AnvilNext.Schema.BaseTypes.Object.Read`) reads
> `u64 ClassID | u32 type hash | fields`. For types derived from `ManagedObject`, its
> GhostReconBreakpoint branch reads a one-byte `IsManaged` right after the hash; other games read
> it before the ClassID. Wildlands puts that byte where GRB does. Entity, LODSelector, lights,
> GridCellDataBlock and every component carry it.

**Pointers.** These follow ATK's base-type readers; every one was seen in these payloads.

| Kind | Bytes |
| --- | --- |
| `ObjectPtr` | `u8 ptype`, then by ptype: 0/4 an inline object (4 = managed) · 1/2/5 a `u64` id · 3 nothing |
| `Reference` | `u8 ptype`, then by ptype: 0/4 an inline object · 1 `u8 reftype + u64` · 2/5 `u64` · 3 `u8 + u64` (10 bytes when null) |
| `Handle` | `u8 + u64` |
| `SmallArray` / `BigArray` | `u32 count` + items |

**Anonymous inline objects.** An inline object with no ID of its own (BoundingVolume,
LODDescriptor, Color, …) carries the ID `0xF8000000 | n`, where *n* is its ordinal among such
objects in the resource, in serialization order from 0.

> **Verified:** GRB renumbers these ordinals when objects are dropped. The rebound twin's
> BoundingVolume is *n* = 3 in GRW and *n* = 1 in GRB once two LightFlares are gone.
> `Link` pointers (ptype 2) refer to these IDs; for example `MeshInstanceMaterialInfo` points
> back at its `MeshInstanceData` as `0xF8000002`, and they follow the renumbering. A converter
> must renumber in output order and remap links. The writer does this in two passes.

**ATK schema type IDs.** `schema_dump.py`'s base-type table was wrong from ID 23 up. ATK's
`BaseTypeRegistry` gives 23 StaticArray, 24 BigArray, 25 Enum, 26 String, 27 LString,
28 Reference, 29 SmallArray, 30 SloppyHandle, 31 DataDrivenEnum. The AC schemas (ACOrigins ≈ the
Wildlands generation, ACOdyssey ≈ GRB's sibling) were useful for *names*. Their field order and
field set match neither game exactly; for example, Wildlands' `EntityDescriptor` serializes no
fields at all. Every layout below was fixed by the bytes.

## Entity

| Part | GRW | GRB | Rule |
| --- | --- | --- | --- |
| header | ClassID, hash `Entity`, managed `01` | same | copy |
| Hierarchy (`BaseObjectPtr`) | `03` (null) in every sample | same | copy |
| GlobalMatrix | `Mat44` at payload +14 | same | copy |
| Components | `u32 n` + `ObjectPtr<Component>` × n | same framing | convert each component (below) |
| scalar block | **45 B** | **66 B** | see below |
| BoundingVolume | inline: Min `Vec3`, Max `Vec3`, Type `u32` (28 B) | same | copy (values re-baked) |
| EntityDescriptor | inline, **0 serialized fields** | same | copy |
| DataLayerFilter | inline: `SmallArray<DataLayerAction{Handle, u32}>` | same | copy |
| ResetData (`ObjectPtr<GameStateData>`) | `03`, or inline GameStateData | same | copy (see GameStateData) |

**Scalar block, 45 → 66 bytes.** GRW byte *i* → GRB byte *j*:

- GRW 0–16 → GRB 0–16 (flags).
- GRW 17 is dropped. It is `01` in all 171 twins and all 2,701 decoded world entities.
- GRW 18–20 → GRB 17–19.
- GRW 21–24 → GRB 20–23 is a `u32` *category* whose values are **remapped**: 29 → 20 in all 16
  twins that have it, 9 → 4 in the 1 twin that has it, 0 → 0. World GRW values: 29 (51%),
  0 (48%), 12 (0.5%). The GRB value for 12 is unknown, so the converter refuses it. No ATK enum
  has these numbers, so the field name is unknown.
- GRW 25–34 → GRB 24–33 (10 bytes, copied).
- GRW 35–38 → GRB 34–37 (`f32`, usually 1.0).
- **GRB 38–41 is new**: `f32` 1.0 in all twins.
- **GRB 42–57 is new** (16 bytes): zero in 170/171 twins. In GRB world entities, bytes 42–49
  are zero in 83% and bytes 50–57 in 95%; non-zero is content.
- GRW 39–40 `u16 0xFFFF` → GRB 58–61 `u32 0xFFFFFFFF`, in all 171 twins.
- GRW 41–44 → GRB 62–65 (`f32` Scale).

> **Verified:** with these rules and the component rules below, the 103 twins that decode in both
> games come out 21 byte-identical and 82 content-only. The content fields are BoundingVolume
> (Min/Max differ in 35–37), single flags (s6, s17), the category in 3 twins (0 → 20 on laser
> props), GlobalMatrix (2), component `Active` flags and ClassIDs that GRB re-allocated, single LOD
> slots GRB filled, and 3 twins where GRB *removed* a component (an InertComponent once, the
> SoundPropsComponent of `x[WL]_SmallBirdsFlee` and `x[WL]_Bush_Birds`). In 4 twins GRB also switched a
> component between inline (ptype 0, managed byte 1) and inline-managed (ptype 4, managed byte 0).
> It went in both directions, so it is classed as content.

### Components

> **Verified on twins:** Visual (89 pairs), RigidBodyComponent (44), SkeletonComponent (43),
> cEntityMessengerDispatcherComponent (34), GR_cSpawnedEntityPhysicActivator_Terrain (22),
> PilotPatchingComponent (15), PilotActorComponent (15), EventListenerComponent (14),
> PilotMovingNavMeshComponent with the whisker merge (10), GR_cVehicleDebrisComponent (8),
> cProjectileGeneratorComponent (7), cElectricDeviceComponent (5, inside EntityGroup twins),
> MaterialOverrider (2) and cReactiveResponseComponent (1).
> Most of these pairs were checked one component at a time, because vehicles hold about 30
> components each. Each component was decoded where its header sits, paired with its GRB twin by
> ClassID, converted and compared, whatever order each game lists them in.
> **Structure from world samples, values from one twin:** cGameplayDestructibleComponent (see
> below).
> **Inferred from world samples of both games, with no twin to check values:** InertComponent,
> MergedPhysicsComponent, SoundPropsComponent, cSmallLifeTargetComponent, SoundPointsComponent,
> SoundAmbienceStamperComponent, GameStateData. Each of these GRB layouts is now
> boundary-checked against GRB bytes (see [Checking GRB layouts against GRB bytes](#checking-grb-layouts-against-grb-bytes)).

Every component starts with the managed byte, then three bytes `Active`,
`OptimizedForHardwareInstancing`, `ComponentLOD`.

**Visual:** `Object` (Reference), `InstanceData` (ObjectPtr), a 15-byte tail, then `BVScale`
(`Vec4`).

- Tail rule: write zeros. In 2% of GRW world Visuals the tail carries an `f32` at +7, but GRB
  has zeros there in all 2,299 world Visuals.

InstanceData by type:

- **LODSelectorInstance:** `ObjectPtr<LODSelector>` + `StaticArray<ObjectPtr>` of **5 (GRW) →
  8 (GRB)**. Append three null pointers (`03`). This tracks LODSelector's 5 → 8 slots.
- **MeshInstanceData:** `Handle` Mesh, 7 zero bytes, `ObjectPtr<CompiledMeshInstance>`,
  `SmallArray<ObjectPtr<MeshInstanceMaterialInfo>>`, `SmallArray<Mat44>` instance matrices.
  GRB then **inserts `SmallArray<Vec4>`** with one entry per matrix: the vec4, matrix and BV
  counts are equal in all 9,282 GRB world MeshInstanceData. The converter writes zero vec4s;
  GRB's are non-zero in 1,740 of 3,889 instanced ones, which is content. Last comes
  `SmallArray<BoundingVolume>`.
- **CompiledMeshInstance:**
  - GRW: `u8 VertexFormat`, `u32` (0, an empty stream array), `u32 PlatformVersion` (25),
    `u32 SDKVersion` (7), `u64 MeshHash`.
  - GRB: **`u8 VertexFormat` only**. Remap the format with the same table as meshes:
    0→0, 1→2, 2→4, 6→10, 8→12, 9→13. Three twin instances differ here (6↔12, 8↔10); GRB
    re-baked those LOD meshes into another format, so for a mesh ported with `grw2grb.py` the
    table is the right choice.
- **MeshInstanceMaterialInfo:** `ObjectPtr` (a Link back to its MeshInstanceData), `Handle`
  MeshMaterial, `Reference` InstanceMaterial. The same in both games.
- **SplashFXInstanceData:** `ObjectPtr` ParentSplashFX. The same in both games.
- **LightInstance:**
  - GRW: `ObjectPtr` Light, `u8`, a Flare `Reference` with an inline LightFlare, then a second
    inline LightFlare. Each GRW LightFlare is 53 bytes.
  - GRB: `ObjectPtr` Light, 6 × `u8` (the first = GRW's `u8`), `SmallArray<ObjectPtr<LightClippingPlane>>`,
    a Flare `Reference`.
  - Rule: drop both flares, write a null reference, an empty clipping-plane array, and zero for
    the 5 new flags. All 33 twins agree.

**RigidBodyComponent** (and its `RigidBody`):

```text
GRW: comp(3) u32 u32 u32 | GameplaySurfaceNavType{} | RigidBody{ CollisionFilterInfo{u32 Layer, u32 Part, 11×u8},
     Reference Shape, f32 Mass, LinearDamping, AngularDamping, GravityFactor, u8 x0, u8 x1, u32 x2, u8 x3, u32 x4 }
     | Reference ImpactData | 5×u8 | Mat44 EntityInitTransform | f32 MaxLinVel, MaxAngVel | Vec4 LinConstraint, AngConstraint
     | PhysicsActivityZone{ SmallArray<ActivityZoneDesc{u32, f32, f32, 3×u8}> }
GRB: same, except  CollisionFilterInfo has 12×u8 (append 0)
                   RigidBody: + Reference Ref2 after Shape (write null; null in all 9 twins, often set in GRB world)
                   the 5 bytes x0,x1,_,_,x3 become 7: (x0, x1, 0, 0, 0, x3, 1)  then x2, x4 unchanged
                   the 5 flags after ImpactData: (x5, x6, x8, x9, 0); x7 dropped (0 in all 2,414 GRW world samples)
```

> **Verified (9 twin pairs):** all shared fields equal after these rules. The GRB-only flags
> y2–y4 are 1 in 7/9 twins and 0 in 1,867/1,910 GRB world samples, so they are content;
> the converter writes 0.
> **Inferred:** where exactly the all-zero GRW flags land in GRB's longer flag runs. Any
> placement fits the twins, because every one of those values is 0 there.

> **Verified (Cell02757, GRW):** the first `Reference` in RigidBody is the body's **collision
> shape**. Earlier drafts of these notes and the tool called it "Material". All 36 RigidBody refs
> in the cell resolve to a shape resource. 28 point into the cell's own DataBlock (12
> ReferenceListShape, 10 ConvexVerticesShape, 4 BoxShape, 2 MeshShape). The other 8 (4 distinct
> IDs) point at MeshShapes in separate `_RT` entries of `DataPC_GRN_WorldMap.forge`. The converter keeps the
> reference as it is, so converted Entities stay linked to their shapes, provided the shapes are
> transplanted too (see [Physics shapes](#physics-shapes-and-collision-materials)).
> **Unknown:** what GRB's extra reference (`Ref2`) points at. It is null in every twin and is
> written null.

Two more rules came from the vehicle and prop pairs. The bytes are consistent, but what the
fields mean is unknown:

- **Collision layer 12 (vehicles):** GRB clears filter bytes cb2 and cb3. GRW has both at 1 in
  all 24 layer-12 pairs; GRB has both at 0 in all 24. Layer-2 props keep their filter bytes.
- **A vehicle's main body** (layer 12, RigidBody x1 = 1) goes rc0 1 → 2, in 14 of 15 pairs. The
  exception is the UAV drone, which GRB retuned throughout. Turrets and secondary bodies (x1 = 0)
  keep rc0.

> **Content (vehicle pairs):** what is left after these rules is GRB-added `Ref2` references
> (26), component `Active` toggles (14), mass retunes (6, e.g. 4,002 → 3,200, 7,490 → 7,500) and
> one-off flag and enum changes on single props.

**InertComponent** (inferred): comp(3), `u32`, `u32`, RigidBody (rules as above),
GameplaySurfaceNavType, `u8`, then GRW has a `Reference` that GRB does not have, then `u32`.
Rule: drop the reference. The one twin can't be compared, because GRB removed its InertComponent.

**MergedPhysicsComponent** (inferred; EntityGroups merge their children's collision into one):
InertComponent's layout, then `SmallArray<u32>`, then
`SmallArray<MergedCollisionInfo>`. Each MergedCollisionInfo is:

```text
Handle | Reference | Handle | u32 | SmallArray<Handle> shapes | u32 | u32
       | SmallArray<{ Mat44, SmallArray<u32> [, GRB: u8] }> transforms
```

Rules: InertComponent's rules, plus one new GRB byte per transform. It is 0 or 1 in GRB world
samples, about 30% 1, and is written as 0.

**cReactiveResponseComponent** (1 twin): comp(3), two `SmallArray<Handle>`, then in GRW only a
`SmallArray<ObjectPtr<MaterialSetting>>`. It is empty almost everywhere; some destructible lamps
hold one `on_off` setting. GRB has no such array, so the converter drops it.

> **Corrected:** this array was read as a `u32` that is always 0. It surfaced once MaterialSetting
> had a layout and those lamps decoded further.

**SkeletonComponent** (36 twins): comp(3), `Reference` MainSkeleton, `SmallArray<Reference>`
AddonSkeletons. GRW then has an inline `WindForce{u8, f32}` and two bytes, which GRB drops.
In all 36 twins they are `{1, 1.0}`, 0, 0.

**PilotActorComponent** (15 twin pairs): comp(3), 3 flags in GRW / 7 in GRB, a `Reference`.
Flags → `(p0, p1, 1, 1, 1, 1, p2)`; the four new flags are 1 in 14 of 15 pairs.

**EventListenerComponent** (14 twins) and **GR_cSpawnedEntityPhysicActivator_Terrain**
(22 twins): the same layout in both games, copied. The first is comp(3) + an inline
`EventListener` with no fields. The second is comp(3) + `u32` + `Handle`.

**Vehicle and projectile components:**

- **cEntityMessengerDispatcherComponent** (30 pairs): bare comp(3) in both games. In 2 pairs
  GRB flips the managed byte; that is content.
- **cProjectileGeneratorComponent** (7): comp(3) + a `Handle`, the same in both games. In 2 of
  the 7 generators GRB *adds* a cBallisticProjectileComponent (comp(3) + a `Reference`). An added
  component is content; it can't be derived from GRW.
- **GR_cVehicleDebrisComponent** (8): comp(3) + `f32`. The value is 120.0 in GRW and 5.0 in GRB
  on the two heli tail debris. It looks like a lifetime retune, so it is content.
- **PilotPatchingComponent** (15): GRW is comp(3), `u8`, `u8`, `f32` (1.0 or 2.5), 3 × `u8`.
  GRB inserts a `u32` after the two leading bytes; it is 0 in all 16 twins that have one. Whether
  the new field sits before or after the second byte can't be told, because that byte is 0
  everywhere. SB_Rib_Boat (1.0 → 2.5) and the Recon Heli's flags are content.
- **Nav whiskers (the one structural move):**
  - GRW keeps a vehicle's NavMeshWhiskerLinks in their own component. Its type hash is
    `0x31cd6959` and its name is unknown. Its ClassID is one below the vehicle's
    PilotMovingNavMeshComponent.
  - GRB has no such component. It appends three `u8` (1, 1, 1 in all 10 twins) and the
    `SmallArray<NavMeshWhiskerLink>` to **PilotMovingNavMeshComponent** (comp(3) + a
    `Reference` in GRW).
  - A link is `u32 0`, two inline `NavMeshWhiskerSpot{Vec4 LocalPosition}`, `u32 LinkType` (11
    in every link seen), and an `f32` (about 1.5–6) that the ACO schema doesn't list.
  - Rule: drop the GRW component and move its links into the PilotMovingNavMeshComponent.
  - **Verified:** byte-identical to GRB on 8 of 10 vehicles. On the other 2 (SB_Small_Plane
    14 → 4 links, UNI_Armored_SUV 6 → 4) GRB rebuilt the whiskers, which is content.

> **A trap worth knowing:** a component that *looks* like it embeds the next inline object
> (SoundPoints, the spawned-physics activator, PilotActor) usually doesn't. The next object is the
> Entity's next component, and the array count says so. Read the count before nesting.

**MaterialOverrider** (2 twin pairs): comp(3), `SmallArray<OverrideDefinition{Handle, Reference}>`,
then a `u8` flag and a `Handle`. GRB inserts a byte after the flag. That byte is 1 in all 428 GRB
world instances and in both twins; GRW has no such byte. One pair converts byte-identical; the
other differs only by GRB's managed-byte flip (content).

> **Corrected:** an earlier version of this note read the flag + Handle as a 10-byte zero tail
> and appended a 0 at its end. The twins showed both the position and the value were wrong.

**cGameplayDestructibleComponent** (breakable props: fences, crash barriers, signs, trees). No
AC schema. Every field boundary below holds in all 2,383 GRW and 302 GRB world instances (each
decodes through the full layout and ends exactly where the next component starts). The one twin,
ENV-GLO-ALL-PRO-Mortar-Ammo-Big, converts byte-identical.

```text
comp(3) u32 u32 | RigidBody (rules as above) | SmallArray<Reference> parts | SmallArray<Mat44>
| SmallArray<Reference> | f32 (50.0 in 92%) | GameplaySurfaceNavType{} | 4×u8 | 3×f32 | u32 | 7×u8
| GRB only: Reference, u8, Reference (null / 0 / null in all 302)
| u8 u8 | Reference | SoundInstance (see below) | GRB only: 16 bytes, 0 in all 302
| Reference, Reference, f32, u32 (12), f32 (3.0), u32 (16), Reference, f32
| t: 64 bytes in both games, laid out differently
```

The parts and matrix arrays are independent: road signs carry one Mat44 per part; most
destructibles have none.

- **t:** GRW has an `f32` at +38 that is 1.0 in every instance. GRB has `f32` 1.0 at +16 and at
  +46, and a null reference at +52. The twin pairs two values: GRW +44 (an enum, 0–3) = 2 =
  GRB +21, and GRW +16 (0/1) = 1 = GRB +51. The converter copies those two bytes. **Inferred from
  one twin:** in GRB's own world those two bytes are non-zero in only 14 and 1 of 302 instances,
  against 83% and 44% in GRW. GRB's world sample is a different set of props, so this neither
  confirms nor refutes the pairing. GRW's other tail values (a few rare `f32`s and flags) are
  dropped.

**SoundInstance** (inline in destructibles, sound props and electric devices): 8 × `u8`, an
inline `SoundEvent{ SoundID{u32 ShortID}, u32, f32 MaxSqrDistance, u8 IsOccludable }`, then 5
bytes in both games, laid out differently.

- **Tied by the data:** the has-sound byte is GRW j[2] and GRB j[1]. Each equals `si5` (the
  instance has a sound, i.e. a non-zero ShortID) in every decoded SoundInstance of its own game
  (1,283 GRW, 234 GRB). The rule copies GRW j[2] to GRB j[1].
- GRB's j[0] (0, or 6 three times when IsOccludable = 2) and GRW's j[0] (0/3/4) and j[1] have no
  pairing and are dropped.
- In GRB every container adds 16 bytes right after the sound:
  - destructible: zeros in all 302 instances;
  - sound props: the entry's `Vec3` offset and a `u32` (0 in all 216);
  - electric device: the start of its block (below).

> **Corrected:** an earlier version of this note had GRB's SoundInstance end in 21 bytes with the
> Vec3 inside it. The electric device showed the 16 bytes after the first 5 belong to the
> container: there they hold a flag and a colour, not a Vec3. The converted bytes were the same
> either way.

**SoundPropsComponent** (inferred; no AC schema; all 289 GRW and 216 GRB world instances decode
and end where the next component starts):

```text
GRW: comp(3) | SmallArray<SoundPropsComponentParams{ u8, SoundInstance, SoundInstance, Vec3, f32 }> | u8
GRB: comp(3) | SmallArray<SoundPropsComponentParams{ u8, SoundInstance, Vec3, u32, Reference }>
     | SoundBankDependencies{ SmallArray<ObjectPtr<SoundBank{ SoundID, u8, String name }>> }
```

Rule: keep the first SoundInstance and the `Vec3` of each entry, then write `u32` 0 and a null
reference. GRW's second SoundInstance, its `f32` and the trailing `u8` are dropped.
SoundBankDependencies is written empty. GRB lists the banks a sound needs there (names like
`BNK_Veh_Land_SFX`), and GRW has no equivalent to derive them from. **Unverified:** whether GRB
plays a sound whose bank nothing lists. Separately from the format, GRW's sound IDs are not
GRB's: none of the 74 non-zero SoundIDs in the decoded GRW samples appears among GRB's 48. A
ported sound reference points at nothing in GRB unless it is remapped.

**cElectricDeviceComponent** (lamps, searchlights, switchable props; no AC schema). Every boundary
below holds in all 564 GRW and 1,553 GRB world instances: the decode continues past it in every
case, with no error at or after it in either game. 5 twin pairs, all inside EntityGroups: 4 convert
byte-identical. In the fifth, GRB renamed the parameter (`on_off` → `Switch`), re-pointed handles,
added a link and changed colour values; all of that is content.

```text
both: comp(3) | u8 | SmallArray<ObjectPtr<FXCommandData>> | [GRB: u8] | u32 | u32 | u32
      | SmallArray<Handle> lights | SmallArray<Handle> | u8 | u8
      | SmallArray<ObjectPtr<ReactionMaterialSetting{ ObjectPtr<MaterialSetting> A, ObjectPtr<MaterialSetting> B,
                                                     SmallArray<Handle> targets }>>
GRW:  | SmallArray<Handle> t0 | SmallArray<Handle> X1 | SmallArray<Handle> X2 | u8
GRB:  | SmallArray<Handle> X1 | SmallArray<Handle> X2 | u8 | 8×u8 | SoundInstance | 71 bytes
MaterialSetting  GRW: { u32, String name, 29 bytes }   GRB: { String name, u32, 29 bytes }
```

- **MaterialSetting:** the same fields in both games, with the name written first in GRB. The
  names are copied. GRW uses `on_off` and `3: Emissive Color`, GRB `Switch` and `ColorTemp`; they
  name the material's own parameters, which a port brings along.
- **GRB's extra byte** after the FX array is 0 in all 1,553 instances.
- **Handle arrays at the end:** GRB X1 = GRW t0 + X1. That is inferred from the one twin where
  t0 is non-empty; it is empty in all 546 decoded GRW world instances. GRB X2 is written empty:
  it is empty in all 1,553 GRB world instances and in 4 of the 5 twins.
- **GRB-only parts:**
  - The 8 bytes are written 0, GRB's most common value.
  - The SoundInstance is the same empty sound in all 1,553 GRB instances, and is written so.
  - The 71-byte block holds a `u32` flag, an RGBA colour (four `f32`s, usually 1.0), ints −5 and
    5, `f32` 0.75 / 1.25 / 1.0, and a 4-byte tail. It has 419 variants in GRB's world. The
    converter writes the most common one, with the flag 0 and the tail `ff ff ff ff`, as in all 5
    twins. The other tail values look like baked pointers. **Inferred:** whether GRB derives the
    colour or flag from anything a port should carry.

**cReactionResponseComponent** (GRW only): the same layout as cElectricDeviceComponent's GRW
layout minus its final `u8`. All 111 GRW instances decode, and 60 of their groups now decode in
full. cElectricDevice looks like a subclass that adds that byte (it is 1 in every electric device).
GRB's world sample and twins contain no cReactionResponseComponent at all, so the converter
reports it as unsupported (or drops it with `--drop-grw-only`).

> **Verified (sampled):** a scan of every GRB world forge, `DataPC_TGT_WorldMap*` with their
> patches, found none. It read every 5th entry: 221,477 entries and 3.1 M resources. Entries that
> fail to unpack were skipped. The MaungaNui patch was read from a vanilla backup. GRW has the
> component in 60 of ~3,766 sampled groups, so a 1-in-5 sample would have found it at anything
> near that rate. **Inferred:** GRB no longer uses the class in its world. **Open:** what GRB put
> in its place.

**PlayerSpawnActivatorComponent** (1 twin, Player_Start, byte-identical): comp(3) + 5 bytes in
both games, zero in all 65 GRW instances and in the twin; copied. The AC schema lists two
ObjectPtrs and an array, which doesn't match 5 bytes, so they stay an unnamed run.

**Gameplay components missing from GRB's world sample.** GRB's world sample comes from MaungaNui
only, and none of these three appear in it:

- **GR_cRespawnPointComponent** (mapped, inferred values):

  ```text
  GRW (30 B): comp(3) | Handle Point | u8 | u32
  GRB (26 B): comp(3) | Handle Point | u8
  ```

  - Rule: drop the trailing `u32`. It is 4–12 in GRW, a varying value with no GRB slot.
  - `Point` and the `u8` are copied. In both games, `Point` names an object 2 IDs below the
    component in most instances. It is never the Entity itself, and the object isn't in the same
    payload. What it is, and where it is stored, is unknown.
  - **Verified (GRB):** all 1,593 respawn Entities in Bootstrap's `TGT_WorldMap` entry decode
    completely under this layout and re-encode byte-identically. All 46 GRW world Entities
    convert, and GRB pairs it with PlayerSpawnActivatorComponent as GRW does.
  - **Unverified:** GRB keeps its respawn points in the Bootstrap world entry, not in cells. So
    whether GRB registers one inside a transplanted cell is untested.
- **GR_cRallyPointComponent:** GRW is comp(3) + `Handle` + `u8` + `u32` + `SmallArray<Vec4>`
  positions, then nested inline objects (type `0x4a0ad240`), 500–850 bytes in all. GRB's 21
  sampled instances run 146, 764 or 781 bytes. Not mapped in either game.
- **cReactionResponseComponent:** see above.

> **Corrected:** these were first called GRW-only. A scan of GRB's world forges found respawn and
> rally points in GRB's Bootstrap forge (`TGT_WorldMap` and one cell), so GRB has both classes
> and they can be mapped rather than dropped.

**Opt-in drops (`convert --drop-grw-only --strip-physics`, or
`convert(..., drop_grw_only=True, strip_physics=True, manifest=[])`).** By default the converter
refuses an Entity holding a `GRW_ONLY` component and keeps physics.

- `--drop-grw-only` leaves the GRW-only components out.
- `--strip-physics` leaves out RigidBody, Inert, MergedPhysics and GameplayDestructible
  components, for transplants whose collision shapes don't come along.
- `--strip-physics-at MeshShape` (any shape types, comma-separated) strips only the Entities
  whose physics reaches one of those types. It follows every pointer in each physics component,
  and through ReferenceListShape children. Any such Entity loses all of its physics components
  together, so none of its remaining components points at a removed RigidBody. A body Shape that
  can't be found anywhere counts as a hit. Shapes are looked up first in the converted entries,
  then in the GRW forge index, typed by the index's type hash. Out-of-cell ReferenceListShapes
  are read for their children. On Cell02757 it strips 24 components on 16 Entities (the rest of
  the cell keeps Box, Capsule and ConvexVertices collision).

Each dropped component goes into `out_dir/dropped_components.json` with its resource, Entity
ClassID, type, hash and ClassID. If the Entity's ResetData (GameStateData) DescBuffer names a
dropped component, the whole ResetData is nulled, because its DataBuffer is not mapped and the
record can't be cut out. That follows the W5 transplant, which did the same by hand.

- On the GRW world sample, `--drop-grw-only` converts 60 more EntityGroups (cReactionResponse).
  Respawn points no longer need it: they convert.
- On Cell02757, `--strip-physics` drops 36 components and nulls ResetData on 19 Entities.
- Only types with a GRW layout can be dropped, so rally points still block.

**PropsPropertiesComponent** (props, vegetation, rocks; no AC schema, no twin, and no prop name
shared between the two worlds). Field boundaries hold in all 309 GRW and 161 of 162 GRB
instances, each decoding to the next component or the Entity's own fields. The 162nd stops
inside, at an object of unlaid-out type `0x49a09525`.

```text
both: comp(3) | f32 (0.8) | f32 (1.0) | 3×u8 | 6×f32
GRW:  | u8 | u8 | f32 (0/50/75/100)
GRB:  | u32 0 | 3×u8 | f32 | f32 | f32 (0.25)
both: | u8 | f32 FarDistance (400.0) | u8 has-imposter | ObjectPtr<PropsImposterProperties>
GRB:  | u8 | ObjectPtr<PropsOnPropsProperties> | Reference Source
```

- **Head and tail** keep their places and are copied.
- **GRW's middle run** has no known GRB counterpart. GRB's is written with GRB's most common
  values (zeros, then 0.25). **Inferred.**
- **Source** is a Reference whose id is `(ClassID << 20) | 1 << 63`. In GRB it points at the
  component itself (20), its Entity (29) or a shared template (43). The converter points it at the
  component. GRW gives generated sub-objects ClassIDs already in this form (owner `<< 20` |
  index); for those it points at the owner, with the index cleared.
- **PropsImposterProperties** is a fixed **7,437-byte** struct in both games, measured to the next
  component in 217 GRW and 69 GRB instances. Its head matches ACO's ImpostorData closely: flags,
  alpha refs, view counts and four texture References.
  - Only 15 of its 7,437 columns hold a constant in both games that differs between them.
  - GRW's bytes 512–3072 (and 7168–7437) are **uninitialized memory written out as-is**:
    fragments of shader source (`( uint( saturate`), heap-pointer-like values, and small-int arrays
    whose unused tails are garbage. GRB holds clean data there: half zeros and half floats, which
    are atlas UV grids.
  - So the converter **drops the imposter**: has-imposter 0 and a null pointer. That is GRB's own
    form for 93 of 162 props. The prop renders normally but has no far-distance billboard.
  - **Untested idea:** copying the 7,437 bytes verbatim, with its four imposter textures ported.
    The garbage region suggests GRB would read wrong atlas UVs.

**Validation target, Cell02757 (GRW `DataPC_GRN_WorldMap_patch_01`):** all 45 supported resources
convert, with or without the drop options. That is 20 Entities, 4 EntityGroups (the sign group and
AutoGroups 10890, 10891 and 11147, which hold the Santa Muerte statue and the electric poles),
the GridCellDataBlock and 20 LODSelectors. AutoGroup_10891 needed GRW vertex format 7 in a mesh
instance mapped to GRB 10. That matches `grw2grb.py`, which ports format-7 meshes with
`drop_uv1` (7 → 6 → 10), so the mesh must be converted that way.

**cSmallLifeTargetComponent** (inferred): comp(3) + `u32` in both games. The `u32` is 1–8 in GRW
(6 in 62%) and 8 in all 52 GRB instances; it is copied. It is another instance of the trap below
the PilotActor entry: what looks like an embedded object after it is the Entity's next component
(InertComponent in 531 of 615 GRW instances).

**SoundPointsComponent** (inferred): the layout is the same in both games, so it is copied:
comp(3) + `SmallArray<SoundPointsPosition{u32, Vec4, u8}>` + one more inline SoundPointsPosition.

**SoundAmbienceStamperComponent** (inferred values, GRB layout from GRB bytes):

```text
GRW (25 B): comp(3) | Handle Ambience
GRB (57 B): comp(3) | SmallArray< inline object, type hash 0xfb359006 (name unknown):
                                  { Handle Ambience | 16 B } >
```

- The 16 bytes are zero in 156 of 177 GRB stamps. The rest hold what look like a Vec3 offset and
  4 more bytes.
- Rule: wrap GRW's Handle in one stamp object, with the 16 bytes zero.

> **Verified (GRB):** all 172 instances in the GRB world sample parse under this layout (array
> count 1 ×167, 2 ×2, 3 ×3), and each ends where a valid next header or the Entity's own fields
> begin. All 323 GRW instances are 25 bytes. The same ambience Handle values occur in both games.
>
> **Corrected (2026-10-10):** earlier versions of these notes and of the tool gave both games
> GRW's 25-byte layout. Nothing had checked that against GRB bytes: every GRB payload holding
> the component failed to decode, at a misread "type 0x8ae348c2" right after it, which sat
> unexplained in the GRB blocker counts. The converter therefore wrote GRB components 32 bytes
> short. Cell02757's three AutoGroups each carry one or two of them; the sign group and the 5
> crash-barrier Entities carry none. That matches the transplant tests: the 5 Entities loaded
> (W6), and adding the groups crashed GRB on the cell load (W5b). **Inferred:** this short
> component caused that crash. It is the only known layout fault in those groups, but no
> in-game test has confirmed it yet.

**GameStateData** (`Entity.ResetData`, inferred): `u32 PropertyCount`, `BigArray<u8>` DescBuffer,
`BigArray<u8>` DataBuffer, as the AC schema says. The DescBuffer looks alike in both games:
`u32 2`, then `u8, u8 kind, u64 id, u32 type-hash` records. It is copied verbatim. **Unverified:**
whether DataBuffer, a snapshot of the referenced objects' state, needs re-serializing where those
objects' layouts changed (RigidBody did).

## LODSelector

```text
GRW: managed | u8 | u8 | u32 | StaticArray[5] LODDescriptor | SmallArray<Handle> | SmallArray<u32> | 5×u8 | f32 | SmallArray<SkeletonLODBakedInfos>
GRB: managed | u8 | u8 |     | StaticArray[8] LODDescriptor | SmallArray<Handle> | SmallArray<u32> | 7×u8 | f32 | SmallArray<SkeletonLODBakedInfos>
LODDescriptor (24 B, both): Reference Object | f32 SwitchDistance | f32 TransitionZoneSize | f32 FadeTimeMultiplier | u8 | u8
SkeletonLODBakedInfos (both): u32 | u8 | u8
```

> **Verified (239 twins, 3,839 GRW and 4,000 GRB world samples decode completely):**
> - The u32 after the first two bytes is GRW-only; drop it.
> - The first byte is 0 in all GRB twins and is written 0. GRW has 0/1/2 there.
> - **5 → 8 LOD slots:** GRB appends three empty descriptors (null reference, distances
>   **640, 1280, 2560**, the trailing `u8` = 1), in 238 of 239 twins.
> - External LOD references: reference-type byte 0 → 1 in 505 of 511 twin references that point
>   at the same ID in both games. 6 keep 0.
> - Flags 5 → 7: (t0, t1, 0, t2, *new*, t4, 0); GRW t3 has no GRB slot. GRB's byte 4 matches
>   nothing in GRW and is 1 in 55 twins; it is content, written as 0.
>
> **Content:** LOD mesh references (95 slots GRB filled that GRW left empty, 11 the reverse),
> switch distances, the stream-handle and `u32` arrays, the trailing `f32`, and above all
> **SkeletonLODBakedInfos**: the array differs in 166 of 239 twins, mostly empty in GRW against
> 1–7 entries in GRB. They are derived from GRB's skeletons and can't come from GRW. The
> converter keeps GRW's.

## GridCellDataBlock

> **Verified (4 twins, 700 GRW and 658 GRB world samples):** the same layout in both games and
> in the AC schema. That is managed, `BigArray<Reference<ManagedObject>>` Objects,
> `u32 NumberOfObjectsToActivate`, `u64 OwnerRelatedIndex`. References keep reference-type 0 in
> both games. Convert by copying. All 4 twins differ only in content: GRB dropped or re-pointed
> objects in the Ghost Room cells.

## Lights (SpotLight, OmniLight, AreaLight)

In GRW every light of a type has **one fixed shape**: all 164 Spot, 659 Omni and 228 Area
samples. They are built from inline objects (two Colors, a TimeOscillatorData, two LightFlares,
LightCommonShadowSettings, and OmniLightShadowSettings on Omni/Area) with fixed-size runs of
fields between them. GRB without flares, the shape of 27 of 28 Spot twins and both Omni/Area
twins, is also fixed. The rules are byte maps per run, found by matching columns across the
29 light twins.

| Run | GRW → GRB | Rule |
| --- | --- | --- |
| after managed | 19 → 20 B | GRW[0:2] + GRW[6:11] + 2×0 + GRW[12:17] + 3×0 + GRW[17:19] + 0. The GraphicObject `u32` GRW[2:6] is dropped, as in LODSelector. GRW[11] has no GRB slot: it is 1 in 20 twins, and every GRB byte near it is 0. |
| after LightColor | 15 → 50 B | GRW[3:11] (`f32` Intensity, `f32` Luminance) + a 42-byte constant: 16×0, −1.0, 0.0, 1.0, 1.0, null Reference. GRW[0:3] (3 flags) and GRW[11:15] (an `f32`) have no GRB slot. |
| IntensityOscillator → Color2 | 9 + flares + 41 → 66 B | GRW b(9) + 8×0 + c[0:24] + **c[0:8] again** + c[24:41]. Both LightFlares are dropped. In GRB, the 8 bytes after the six `f32` repeat the first two (fade start/end) in all 29 twins. |
| after Color2 | 8 → 8 B | copy |
| after CommonShadowSettings | Spot 34 → 38 B, Omni/Area 131 → 135 B | Spot: append `f32` 10.0. Omni/Area: insert `f32` 10.0 at +12. 10.0 in all twins. |
| OmniLightShadowSettings (+8 B on Area) | same | copy |

> **Content:** Intensity/Luminance (each byte equal in 20–24 of 29 twins), shadow and radius
> `f32`s in the last run (25 Spot twins), the reference at the start of that run (12; possibly
> the cookie texture, by schema order), LightColor (7) and DepthBias (4).
> **Not handled:** GRB's own LightFlare (128 bytes, a different layout) and LightClippingPlane
> arrays on lights. The converter never emits them, and the GRB-side decoder does not read GRB
> lights that have them (24/38 Spot and 321/375 Omni world samples).

## EntityGroup (stretch)

EntityGroup is the Entity layout (above), then `SmallArray<Reference<Entity>>`, with child
entities **inline**, then `SmallArray<Handle>` UIEntitiesDisplayOrder and a `u32`. The
converter applies the Entity rules to the group and to each child, recursing into child
EntityGroups.

> **Verified (GRB bytes):** 2,289 of 3,193 GRB world groups decode completely, and **all 2,289
> re-encode byte-identically**. That covers the children array, UIEntitiesDisplayOrder and the
> trailing `u32`. The rest stop at a component type with no layout, or at a MergedPhysics
> variant (130). For Entities, 3,426 of 4,000 GRB samples decode; 3,357 re-encode identically,
> and the other 69 differ only in anonymous-object ordinals. GRB keeps gaps in some ordinals
> (e.g. `0xF8000042` where serialization order gives `0xF8000002`), and `encode` renumbers.
> **Not validated:** no EntityGroup twin decodes yet. All 27 hold an unlaid-out component.

What GRB groups hold, against GRW's and against our converted ones (world samples):

- **Children are inline in both games**: ObjectPtr type 0, Entity or EntityGroup, with IDs
  unrelated to the group's ID or in the bit-63 generated form.
- **UIEntitiesDisplayOrder** is empty in all 2,289 GRB groups that decode. GRW fills it in 3 of
  3,350, and the converter copies them.
- **PropsPropertiesComponent is rare inside GRB groups:** its type hash occurs in 2 of 3,193 GRB
  group payloads, against 127 of 3,766 in GRW. GRB Entities carry it at GRW's rate (124 of
  4,000). One of the two GRB groups, `AutoGroup_134760`, holds it on two children, with the same
  field values and `Source` form the converter writes. So a group child may carry one.
  **Inferred:** GRB's cook moved most props out of groups.
- Group components with GRW-style generated ClassIDs (`group << 20 | n`, bit 63) occur in both
  games, e.g. GRB `AutoGroup_134760`'s own components.

## Checking GRB layouts against GRB bytes

Twins check converted *values*. A GRB layout can still be wrong where no twin, and no complete
GRB decode, holds the type: the SoundAmbienceStamper fault above hid that way. Two checks now
cover every component the converter emits (GRB world sample plus the GRB side of all twins, no
forge reads):

1. **Round trip.** Decode each GRB payload and re-encode it. Every complete decode must give the
   same bytes. Results: EntityGroup 2,289 / 2,289; Entity 3,426, of which 69 differ only in
   anonymous ordinals.
2. **Boundary audit.** At every GRB occurrence of a component's type hash that follows an inline
   ObjectPtr byte, decode that component alone with the GRB layout. Then check what follows:
   - a header of a known type;
   - or a header-shaped ID (an unknown next component);
   - or the Entity's own fields after its Components array, decoded through the type-checked
     BoundingVolume (the component was the last one).

   A layout of the wrong length lands mid-object instead.

| Component | GRB occurrences | Boundary holds |
| --- | --- | --- |
| Visual | 26,394 | 26,394 |
| MaterialOverrider | 6,987 | 4,038 (see below) |
| InertComponent | 5,854 | 5,854 |
| RigidBodyComponent | 4,272 | 4,272 |
| cElectricDeviceComponent | 1,558 | 1,520 (38 run on: a variant) |
| SoundPointsComponent | 1,406 | 1,406 |
| PilotActorComponent, PilotPatchingComponent | 1,075 each | all |
| MergedPhysicsComponent | 964 | 783 (150 stop at the known GRB variant) |
| cEntityMessengerDispatcherComponent | 443 | 443 |
| EventListenerComponent | 340 | 340 |
| cGameplayDestructibleComponent | 305 | 305 |
| cReactiveResponseComponent | 264 | 264 |
| SkeletonComponent | 269 | 269 |
| SoundPropsComponent | 217 | 217 |
| SoundAmbienceStamperComponent | 172 | 172 (after the correction) |
| PropsPropertiesComponent | 162 | 161 (one stops inside, at unlaid-out type `0x49a09525`) |
| cInterestAreaComponent | 101 | 101 |
| cSmallLifeTargetComponent | 52 | 52 |
| GR_cSpawnedEntityPhysicActivator_Terrain | 21 | 21 |
| PilotMovingNavMeshComponent, GR_cVehicleDebrisComponent, cProjectileGeneratorComponent, PlayerSpawnActivatorComponent | 10, 8, 7, 1 | all |

**Open: MaterialOverrider.** The boundary holds in 4,038 of 6,987 occurrences, including all 475
inside complete GRB decodes; its layout is also twin-validated. The other 2,949 all sit in
payloads that don't decode completely, mostly large `shortRange` groups. There it is followed by
bytes that are neither a header nor Entity fields (`01 00 00 00 00 00 00 00 …`). That is either a
GRB variant or a context the audit misreads. Unexplained. None of Cell02757's groups holds one.

## Physics shapes and collision materials

Converted Entities' RigidBodies reference these resources, so a transplanted cell needs them, or
needs `--strip-physics`. All of Cell02757's physics resources convert, and each output decodes
exactly under the GRB layout: ConvexVerticesShape 11, ReferenceListShape 6, MeshShape 4, BoxShape
3, CapsuleShape 2, CollisionMaterial 1.

| Type | Layout | Evidence | Rule |
| --- | --- | --- | --- |
| ConvexVerticesShape | `u32` UserCategory, `SmallArray<Vec3>` vertices, `SmallArray<u16>` triangle indices, `Reference` material, `f32` ConvexRadius (0.01), `u8` ShrinkByRadius | **Verified:** ATK's GRB reader (`AnvilToolkit.FileTypes.AnvilNext.Physics.ConvexVerticesShape`), and 11 GRW shapes that decode to their exact last byte with it | copy |
| BoxShape | UserCategory, `Vec4` HalfExtents, `Mat44`, `Reference` material (the ACO schema) | 3 GRW and 14 GRB (Cell45147), exact; the GRB ones re-encode byte-identically | copy |
| CapsuleShape | UserCategory, `Vec4` Bottom, `Vec4` Top, `f32` Radius, vertices, indices, `SmallArray<u8>` material indices, `SmallArray<MeshShapeTriangleMaterialData{Reference, CollisionFilterInfo}>`, `Reference` | 2 GRW and 8 GRB, exact; GRB byte-identical | filter infos +1 byte |
| MeshShape | UserCategory, `PhysicsSDKDataPack{BigArray<u8>}`, `u8`, `u8`, then the capsule's triangle arrays, `Vec4` min/max AABB | 4 GRW exact; the Ghost Room twin `TPL_Ground_64m` decodes exactly in both games, and every field except the SDK blob is byte-identical | copy |
| ReferenceListShape | UserCategory, `SmallArray<Reference>` children, `SmallArray<Mat44>`, `SmallArray<Vec4>` scales, `SmallArray<CollisionFilterInfo>`, `Vec4` min/max AABB | 6 GRW and 9 GRB, exact; GRB byte-identical | filter infos +1 byte |
| CollisionMaterial | `Reference` PhysicsCollisionMaterial, `Reference`, CollisionFilterInfo, [GRB: `u32`], Color | 1 GRW and 2 GRB samples, both GRB byte-identical | filter info +1 byte, `u32` 0 inserted; values **inferred** |

> **Verified (GRB, Cell45147 of the vanilla `DataPC_TGT_WorldMap_MaungaNui_Split.forge`):** every
> shape type the converter writes, plus ConvexVerticesShape (4), decodes exactly from GRB's own
> bytes and re-encodes byte-identically. The cell also holds 2 CylinderShapes, a type with no
> layout here (none in Cell02757).

- **ReferenceListShape differs from the ACO schema.** GRW has no UseMaterialFilterInfos,
  MatchingVisuals or IsMutable. It adds per-child scales, and the filter infos come after them.
- **Known gap: MeshShape's PhysicsSDKDataPack is a Havok tagfile** (`TAG0`, `SDKV`, `DATA`), SDK
  2016.1 in GRW and 2018.2 in GRB. The twin's blob is 3,292 bytes in GRW and 928 in GRB. The
  converter copies GRW's, and the selftest reports the twin as "known gap", not content.
  **Unverified:** whether GRB's Havok loads a 2016.1 tagfile. If it doesn't, those meshes need
  re-cooking, or the converter has to drop the MeshShape.
- **Not mapped: PhysicsCollisionMaterial** (no AC schema has it). There are three samples:

  ```text
  GRW Physics_GRN_Rock               (32 B): u32 4    | f32 0.8 | u32 0 | u32 0 | u32 2 | 12 × 0
  GRB Physics_GRN_TestColMat_Default (40 B): u32 4001 | u32 3 | u32 3 | f32 0.8 | 24 × 0
  GRB Physics_GRN_Wood_Solid         (40 B): u32 8    | u32 2 | u32 1 | f32 0.8 | 24 × 0
  ```

  Only the 0.8 pairs up. Better than converting it: point shapes at GRB's own materials (next
  section).

### What a transplanted cell depends on (Cell02757)

> **Reported by the transplant tests (not re-measured here):** GRB cells never hold inline Meshes.
> 0 of 321 sampled GRB cells carry one, against 257 of 600 GRW cells. With a cell's meshes
> inline, GRB hung on the load (W5). With every cell-local mesh promoted to its own entry, the
> hang went away (W5b). So a transplanted cell may carry Entity, EntityGroup, LODSelector,
> GridCellDataBlock and lights, but never Mesh or TextureMap; those go in their own entries.

> **Verified (GRW, by resolving every reference in the cell's 113 resources):** the cell is not
> self-contained. Beyond render meshes (the LODSelectors' LOD meshes, `grw2grb.py`'s side), its
> physics references:
>
> - **6 MeshShapes in their own `_RT` entries** of `DataPC_GRN_WorldMap.forge`. 4 are reached
>   from RigidBody `Shape`, and 2 more only from ReferenceListShape children:
>   - `ENV-GLO-ALL-PRO-Electric-Pole-Wood-Small-A_RT`
>   - `ENV-GLO-ALL-PRO-Road-CrashBarrier-3m-StoneWall-Crumble-B_RT`
>   - `ENV-GLO-ALL-MOD-KIT_WallOldStones-B_CrashBarrier-200x140_BrickCrumble-B_Persistant_RT`
>   - `ENV-GLO-ALL-MOD-KIT_WallOldStones-B_End-200x140_BrickCrumble-B_Persistant_RT`
>   - `ENV-GLO-ALL-PRO-Road-CrashBarrier-End-StoneWall-A_RT` (RefList only)
>   - `ENV-GLO-ALL-PRO-Road_CrashBarrier-2m_StoneWall-Crumble-A_RT` (RefList only)
>
>   All 6 convert with `convert <entry names>`. None of these IDs is a top-level entry in our
>   index of GRB's forges.
> - **4 material IDs that are not top-level entries in either game's forge index.** These are 3
>   CollisionMaterials referenced by Box, Capsule, ConvexVertices and MeshShape `Material` fields
>   (`0x11f1a6a5ff`, `0x11f1a6a63a`, `0x1523930094`), and CollisionMaterial `GRN_Rock`'s second
>   reference (`0x3af3a5ece5`). The cell carries its own `GRN_Rock` CollisionMaterial
>   (`0x11f1a6a643`) and `Physics_GRN_Rock` PhysicsCollisionMaterial (`0x2bf3c9c4f7`).
>
> **Inferred:** the missing materials are embedded resources in other entries, not their own.
> Two of them are within 70 IDs of the cell's `GRN_Rock` (`0x11f1a6a5ff`, `0x11f1a6a63a`). GRB's Ghost Room
> `Physics_GRN_TestColMat_Default` (`0x2bf3c9c5b2`) sits next to GRW's `Physics_GRN_Rock`, which
> suggests GRB kept the GRN material library under the same IDs.
>
> **Verified in part (GRB Cell45147):**
> - `0x11f1a6a63a`, the CollisionMaterial GRW's Box and Capsule shapes reference, is a
>   CollisionMaterial resource in that GRB cell, under the same ID.
> - `0x1523930094` is referenced 10 times from the cell, but not stored in it.
> - GRB's `Physics_GRN_Wood_Solid` is `0x2bf3c9c4f0`, 7 IDs from GRW's `Physics_GRN_Rock`.
>
> So GRB kept at least part of the GRN collision-material library under GRW's IDs.
> **Unverified:** whether GRB has `0x11f1a6a5ff`, `GRN_Rock` and `Physics_GRN_Rock`. None of
> them is in Cell45147. Where GRB has the ID, the shapes can keep their references unchanged.

## What blocks the rest

Component types with no layout. Each world sample that doesn't convert is counted once, under
the first such type it hits (GRW world sample, 2026-10-10):

| Component | EntityGroups | Entities | Notes |
| --- | --- | --- | --- |
| cReactionResponseComponent | 60 | — | GRW layout mapped; none in a 1-in-5 sample of all GRB world forges. Converts with `--drop-grw-only`. |
| SoundRadioReceiverComponent | 59 | — | |
| HoudiniInstancerComponent | 51 | — | |
| GIProbeIndoorVolumeComponent | 41 | — | |
| type `0x101fa7da` (name unknown) | 35 | — | |
| SpaceComponent | 33 | — | |
| SoundDynEchoReflectorComponent | — | 30 | |
| cVehicleParkComponent, SoundWindContextComponent | — | 26 each | |
| FXComponent | 26 | 24 | |
| HoudiniDecalInstancerComponent | 25 | — | |
| type `0x2996ca50` (name unknown) | 24 | — | |

"—" means the type is not among the 14 most common first blockers for that resource type.

Then a long tail. Among the twins, the 13 vehicles each still need about 15 component types:

- **On most vehicles:** GR_cGenericBillboardComponent (17 twins), SoundComponent (GRW, 17),
  cObstacleDetectorComponent (14), cIdentifyByBillboardComponent (GRW only, 14),
  EnvInfluenceComponent (14), WorldParticlesEmitterComponent (9).
- **By vehicle kind:** the drive-physics and vehicle-kind components for cars (6), boats (4)
  and bikes (2).
- **Unnamed:** a few types with no name in any dictionary, e.g. hash `0x915ca1dd`, which both
  games have.

Weapons and projectiles need FXComponent (5), AreaOfEffectFeedbackComponent (5) and
cDangerElementFeedbackComponent (5).

PropsPropertiesComponent is mapped (see its section): the imposter turned out to be a fixed-size struct
with uninitialized memory in it, and is dropped.

## Tools

[`tools/grw_entities.py`](../tools/grw_entities.py) is the converter, standalone, in the style
of `grw2grb.py`:

```text
python grw_entities.py selftest [--world-step 60] [--grb-ghostroom PATH]   # twins + world coverage, PASS/FAIL
python grw_entities.py scan <GRW forge> [--step 60]                         # how much of a forge converts
python grw_entities.py convert <GRW entry name|id> ... -o out_dir            # converted payloads, one file each
    [--drop-grw-only]    leave out GRW-only gameplay components instead of refusing the Entity
    [--strip-physics]    leave out RigidBody, Inert, MergedPhysics and GameplayDestructible components
    [--strip-physics-at MeshShape,...]   ... only on Entities whose physics reaches these shape types
    [--types A,B,...]    convert only these resource types, e.g. BoxShape,CapsuleShape,ConvexVerticesShape
```

`convert` names each output `<ClassID>_<type>_<name>.payload` (decimal ClassID). It also writes
`converted.json`, an index with one record per resource: `class_id`, `class_id_hex`, `type`,
`name`, `entry`, `file`, `bytes`, or a `skipped` reason. A transplant can therefore bring shapes
and Entities in by ClassID. With either drop flag, `dropped_components.json` lists what was
dropped from each Entity, and an Entity whose ResetData names a dropped component gets a null
ResetData.

As a library: `decode(payload, game)`, `encode(tree, game)` (two-pass, link-aware renumbering
of the `0xF8…` objects) and `convert(grw_payload)`, which raises `NeedLayout` for component types
without a layout and `Unsupported` for values no rule covers.

The selftest finds the twins itself from both installs and takes about 30 seconds. It is
read-only, caps its memory at 1.5 GB (`--max-mb`) and streams forges one entry at a time.
Standard library + the game's Oodle DLL + ATK's `lzo.dll`, through `tools/data_inspect.py`.

`convert` writes payloads, not containers. Wrapping them into GRB `.data` containers is
`grw2grb.py`'s `frame` / `build_container`, and that is where a converted-world builder joins
the two.
