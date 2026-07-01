# Reference — Resource-type IDs (the `Extension` field)

Every typed resource inside a `.data` carries a 32-bit **type id** — the `Extension` field on a `ForgeEntry` (see [`docs/02-forge-file-format.md`](../docs/02-forge-file-format.md)) and the first `uint32` of each record in a `.data`'s file table (see [`docs/03-data-and-resources.md`](../docs/03-data-and-resources.md)). This file explains how that id is formed and lists the ids that matter for GRB modding.

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
uint32  TypeId          // = CRC32(typeName) = the ForgeEntry.Extension
int32   PayloadLength
string  Name            // length-prefixed (ReadStringEnc32)
byte[]  Payload:
        ├─ FileHeader   // 1 byte (=0) normally; if first byte==1: 12*int32@+4 + 8 bytes
        ├─ uint64 ClassID     // the resource's own 64-bit id
        ├─ uint32 Extension   // == TypeId above (redundant, same value)
        └─ … resource data
```

On unpack, ATK writes each record to `<index>_-_<Name>.<GetHashedString(TypeId)>`.

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
| `1373399936` | `0x51DC6B80` | LODSelector |
| `3571030336` | `0xD4D99940` | FacialSolverData |

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

## Reproducing / extending this table

```python
import zlib
zlib.crc32(b"BuildTable")   # -> 585940579
```

To recover the *complete* id→name set, dump `ScimitarClassRegistry.ScimitarClasses` from the decompiled ATK, or CRC-32 the lines of the embedded `hashes.hl`. To read a resource's id from real bytes, use [`tools/data_inspect.py`](../tools/data_inspect.py).
