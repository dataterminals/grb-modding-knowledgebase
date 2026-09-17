# Reference — Resource-type IDs (the `Extension` field)

Every typed resource inside a `.data` carries a 32-bit **type id** — the first `uint32` of each record in a `.data`'s file table (see [`docs/03-data-and-resources.md`](../docs/03-data-and-resources.md)). For a container's **first** record only, the same id is also the `Extension` field on its `ForgeEntry` (see [`docs/02-forge-file-format.md`](../docs/02-forge-file-format.md)). This file explains how that id is formed and lists the ids that matter for GRB modding.

> ⚠️ **An `Extension` names only a container's first resource** *(verified 2026-09-16, census of all
> 415,024 containers)*. It matches the first record's type id in 415,024 of 415,024. But 89.5 % of
> GRB's 3,935,343 resources are nested, and **1,785 of its 1,852 type ids never come first**, so they
> never appear as any forge entry's `Extension`. A sweep of `Extension`s is not a type census; walk
> the containers.

> **Source:** decompiled ATK v1.3.1 — `ScimitarClassRegistry.ScimitarClasses` (the `uint → Type` map), `HashedData.GetHashedString`, `CRC32.ComputeCRC32`, `DataFile`. **Verified empirically** on 2026-06-30 by parsing real GRB `.data` files (Oodle-decompressed with the game's `oo2core_7_win64.dll`) and matching each resource's embedded id to the CRC32 of its type name. Method/type names are ATK's.

## How a type id is formed (verified)

**A resource-type id is the standard CRC-32 of the ASCII type-name string.**

- Algorithm: standard CRC-32, polynomial `0xEDB88320` (reflected), initial `0xFFFFFFFF`, final XOR `0xFFFFFFFF` — i.e. identical to `zlib.crc32` / Python's `zlib.crc32(name.encode('ascii'))`. (ATK's `CRC32.ComputeCRC32` over `Encoding.ASCII.GetBytes(name)`.)
- Confirmed: `crc32("BuildTable") = 585940579` and `crc32("Mesh") = 1096652136` exactly match the `Extension` embedded in real `.BuildTable` / `.Mesh` resources on disk.

**Resolving an id back to a name** (`HashedData.GetHashedString(uint)`):
1. Look it up in `HashedStrings` — a dictionary built at runtime from an embedded, LZMA2-compressed word list (`AnvilToolkit.Resources.hashes.hl`), CRC-32-hashing each line (and its lower/upper-case forms). This is the same "tens of thousands of hashes" used to name unpacked entries.
2. Else look it up in the small hardcoded `DataStorage.AnvilExtensions` fallback.
3. Else return the number as a string.

So the human name you see as a resource's extension (`.BuildTable`, `.Mesh`, `.Cloth`, …) is just the reverse-lookup of `CRC32(typeName)`. The authoritative id→class map is `ScimitarClassRegistry`.

## Typed-resource byte layout (verified)

Inside a `.data`'s (decompressed) file table, each record is:

```
uint32  TypeId          // = CRC32(typeName); also the ForgeEntry.Extension, for the first record only
int32   PayloadLength   // counts the payload only
int32   NameLength      // 0 is legal: unnamed resources exist
bytes   Name            // NameLength bytes, no terminator (ReadStringEnc32)
bytes   FileHeader      // NOT counted by either length:
                        //   0x00                                  normally (1 byte)
                        //   0x01 | u16 2 | u8 0 | i32 N | N x 12  object-block-allocator table (8 + 12N bytes)
byte[]  Payload         // PayloadLength bytes
        ├─ uint64 ClassID     // the resource's own 64-bit id
        ├─ uint32 Extension   // == TypeId above (redundant, same value)
        └─ … resource data
```

The container's **metadata block** indexes the same records: `u16 count`, then per record
`u64 ClassID | i32 recordSize | u16 k | k × u16`, where `recordSize = 12 + NameLength + FileHeader + PayloadLength`.
`k` is 0 almost everywhere; only world-map containers use 1–4, meaning unknown. A container
that ATK wrote may also end its metadata block with ATK's own LZMA `MetaData` trailer, closed by
`i32 size | u64 MetaData.EndMagic` (`2570475414025252254`). ATK reads only the `u16 count` of a GRB
table.

On unpack, ATK writes each record to `<index>_-_<Name>.<GetHashedString(TypeId)>`, containing
**FileHeader + Payload** — so in an unpacked file the ClassID sits at bytes 1–8 (or at 8 + 12N after
a long header).

> **Verified 2026-09-16** from ATK 1.3.1 (`DataFile.Deserialize`, `DataFile.ReadFileHeader`,
> `ScimitarFile.WriteHeader`) and on real files: walked this way, containers of 1 to 61,426
> resources end exactly on their last byte and agree with their metadata block entry for entry.
> **Corrected:** until then this section placed the FileHeader *inside* `PayloadLength`, which is
> true of other AnvilNext games (they add an extra `01` byte inside the payload) but not of GRB —
> and a parser built on it reads every resource after the first one byte early.
> **Census, the same night:** all 415,024 containers in the 27 forges of an install walk to their
> last byte, and every metadata table agrees — 4,155 world-map tables only once the `k × u16`
> extension is read.

## The ids that matter for GRB modding

Values are decimal (as stored) and hex. Full map: `ScimitarClassRegistry` in the decompiled source.

### Geometry & rigging
| ID (dec) | ID (hex) | Type |
| ---: | --- | --- |
| `1096652136` | `0x415D9568` | **Mesh** |
| `2121000489` | `0x7E6BE629` | HairMesh |
| `4238218645` | `0xFC9E1595` | CompiledMesh |
| `105229237` | `0x0645ABB5` | MeshData |
| `615435132` | `0x24AECB7C` | **Skeleton** |
| `2507411529` | `0x95741049` | Bone |
| `1373399936` | `0x51DC6B80` | LODSelector |
| `3571030336` | `0xD4D99940` | FacialSolverData |

### Skeleton bone-physics (Reflex3)
These are **nested** classes — they live *inside* a `Skeleton` resource as inline objects, so they
never appear as a forge entry's `Extension`. Full write-up:
[`skeleton-reflex3-physics.md`](skeleton-reflex3-physics.md).

| ID (dec) | ID (hex) | Type | In GRB? |
| ---: | --- | --- | --- |
| `2386539642` | `0x8E3FB47A` | **Reflex3SkeletonConstraints** | ✅ inline in **all 2,469** forge-entry skeletons, 512 with real data. Of the 285 skeletons that only occur nested, 4 more hold data and **60 carry none** *(census 2026-09-16)* |
| `3558325132` | `0xD417BB8C` | ReflexSystem | field is read for GRB, never seen inline |
| `3371740159` | `0xC8F8ABFF` | SkeletonPoseGroup | not inline in sampled skeletons |
| `547156082` | `0x209CF072` | SkeletonPose | ” |
| `119336528` | `0x071CEE50` | SkeletonPoseBone | ” |

### Ragdolls & collision capsules
Standalone resources, but **always nested**: none of these is ever a container's first resource,
so none appears as a forge entry's `Extension`. That is why the 2026-08-14 forge-entry sweep marked
`LiteRagdoll` "never". Counted and decoded by the 2026-09-16 (night) census — layouts in
[`meta/research-log.md`](../meta/research-log.md), summary in
[`skeleton-reflex3-physics.md`](skeleton-reflex3-physics.md). Names marked *(dict)* are CRC32 matches
in ATK's name dictionary, with no ATK class behind them.

| ID (dec) | ID (hex) | Type | In GRB? |
| ---: | --- | --- | --- |
| `2299544533` | `0x891043D5` | **LiteRagdoll** | ✅ **637 nested, 88 distinct, all vanilla.** Bone-attached capsule sets: damage triggers on human entities, cloth colliders, animals, drones, raid bosses. ATK's `SupportedGames` excludes GRB |
| `333476854` | `0x13E073F6` | LiteRagdollCapsuleGroupFlags | ✅ embedded in every GRB capsule (16 × bool) |
| `2371068428` | `0x8D53A20C` | LiteRagdollCapsule | ❌ not used — GRB's capsules are the four classes below |
| `572675924` | `0x22225754` | LiteRagdollShape | ❌ not used |
| `2408076648` | `0x8F885568` | LiteRagdollExternalCapsule | ❌ not used |
| `286154434` | `0x110E5EC2` | *(unnamed capsule class)* | ✅ one size float — *inferred* sphere |
| `3736378044` | `0xDEB49ABC` | *(unnamed capsule class)* | ✅ two size floats — *inferred* capsule |
| `3405269372` | `0xCAF8497C` | *(unnamed capsule class)* | ✅ three size floats — *inferred* box |
| `716768756` | `0x2AB905F4` | *(unnamed capsule class)* | ✅ points at a `MeshShape` / `ConvexVerticesShape` / `BoxShape` / `CylinderShape` resource by ClassID |
| `1273385935` | `0x4BE653CF` | **RagdollSkeleton** *(dict)* | ✅ one: `GR_MaleAverage`, referenced by 51 human `Entity` resources, `CHR_PLAYER_TGT` included |
| `1401269008` | `0x5385AB10` | RagdollBoneData *(dict)* | ✅ ×19, inside `GR_MaleAverage` |
| `854659681` | `0x32F11261` | RagdollConstraintData *(dict)* | ✅ ×18, inside `GR_MaleAverage` |
| `4236257670` | `0xFC802986` | RagdollMotorParameters *(dict)* | ✅ ×4, inside `GR_MaleAverage` |
| `2032007014` | `0x791DF766` | RagdollBoneDriveParameters *(dict)* | ✅ ×1, inside `GR_MaleAverage` |

### Textures & materials
| ID (dec) | ID (hex) | Type |
| ---: | --- | --- |
| `2729961751` | `0xA2B7E917` | **TextureMap** |
| `491489187` | `0x1D4B87A3` | CompiledMip |
| `321093609` | `0x13237FE9` | CompiledTextureMap |
| `3608045168` | `0xD70E6670` | **TextureSet** |
| `2244483011` | `0x85C817C3` | **Material** |

### Definitions & data
| ID (dec) | ID (hex) | Type |
| ---: | --- | --- |
| `585940579` | `0x22ECBE63` | **BuildTable** |
| `3966419799` | `0xEC6AC357` | **GraphicObject** |
| `2535097390` | `0x971A842E` | EntityBuilder |
| `2866750051` | `0xAADF2263` | EntityGroupBuilder |
| `1849465967` | `0x6E3C9C6F` | LocalizationPackage |
| `262342271` | `0x0FA3067F` | Animation |

### Cloth / soft-body physics
The GRB **garment cloth** resource is typed **`Cloth`** (not a standalone "ClothPackage" — see below). `SoftBody` / `MotionSoftBody` are sibling physics resource types (tents, flags, other deformables).

| ID (dec) | ID (hex) | Type | Role |
| ---: | --- | --- | --- |
| `3811591354` | `0xE33044BA` | **Cloth** | **top-level GRB garment-cloth resource** |
| `1263847064` | `0x4B54C698` | SoftBody | soft-body deformable |
| `2559966986` | `0x9895FF0A` | MotionSoftBody | modern soft-body |
| `4204051069` | `0xFA94BA7D` | ClothLOD | legacy cloth LOD |
| `693470191` | `0x295583EF` | **MotionClothLOD** | modern (GRB) cloth LOD; holds a **ClothPackage** |
| `2184673235` | `0x823777D3` | SoftBodyLOD | |
| `2655478786` | `0x9E476402` | MotionSoftBodyLOD | holds a ClothPackage |
| `2104190879` | `0x7D6B679F` | ClothState | |
| `1629082830` | `0x6119D4CE` | **MotionClothState** | GRB cloth state; lists the LODs |
| `2822385750` | `0xA83A3056` | SoftBodyState | |
| `3030882726` | `0xB4A799A6` | MotionSoftBodyState | |
| `2152719156` | `0x804FE334` | ClothSettings | |
| `4154975455` | `0xF7A7E4DF` | SoftBodySettings | |
| `1390783109` | `0x52E5AA85` | ClothActionSettings | |
| `4174832450` | `0xF8D6E342` | SoftBodyConstraint | |
| `1656389857` | `0x62BA80E1` | SoftBodyVertexMapping | |

> **There is no `ClothPackage` type id.** `ClothPackage` is a **nested sub-object**, not a top-level resource. The GRB garment-cloth hierarchy (verified) is:
>
> ```
> Cloth  (type id 3811591354)
>   └─ MotionClothState  (1629082830)
>        └─ MotionClothLOD  (693470191)
>             └─ ClothPackage            ← no id; parsed inline
>                  └─ MotionBody[]        ← length-prefixed blobs
>                       └─ MotionSection[] (TLV: uint16 type + uint16 0xECD7 + int32 size)
> ```
>
> The `ClothPackage → MotionBody → MotionSection` layer is the MotionCloth format documented in [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) and [`cloth-section-types.md`](cloth-section-types.md). **Empirically confirmed:** `1687_-_TP_Top_Bodark_Trench_Cloth.data` contains one resource whose embedded `Extension = 3811591354` (`Cloth`).

## The same ids appear inside BuildTable XML (verified)

The type-id space is not confined to `.data` records. In ATK's **BuildTable XML export**, each `DynamicProperty` names its slot's type with the identical `CRC32(typeName)` value, and ATK resolves it into a `HashName` attribute:

```xml
<Value Name="DataType" Type="UInt32" HashName="GraphicObject">3966419799</Value>
<Value Name="DataType" Type="UInt32" HashName="BuildTable">585940579</Value>
```

Both check out: `zlib.crc32(b"GraphicObject") = 3966419799`, `zlib.crc32(b"BuildTable") = 585940579`. So when reading a BuildTable you can decode `DataType` with this table — it tells you what *kind* of resource that slot expects. Layout and worked example: [`buildtable-xml.md`](buildtable-xml.md).

> Note the contrast with **`x`-prefixed names** in the same exports (`x73B5D0A0`, `x67660D91`): those are *field-name* hashes ATK could **not** resolve, printed as `x<HEX>`. A resolved `HashName` means the hash was in the dictionary; an `x…` name means it wasn't.

## Reproducing / extending this table

```python
import zlib
zlib.crc32(b"BuildTable")   # -> 585940579
```

To recover the *complete* id→name set, dump `ScimitarClassRegistry.ScimitarClasses` from the decompiled ATK, or CRC-32 the lines of the embedded `hashes.hl`. To read a resource's id from real bytes, use [`tools/data_inspect.py`](../tools/data_inspect.py).
