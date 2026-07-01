# 03 — `.data` containers and typed resources

If a `.forge` is the archive, a **`.data`** entry is one item inside it — and crucially, a `.data` is itself a **container**. Unpacking a forge gives you `.data` files; unpacking a `.data` gives you one or more **typed resources**. This two-level nesting is the heart of how GRB data is organized.

## The naming you'll see when unpacked

When ATK unpacks a forge, each entry is written to disk as:

```
<decimalFileID>_-_<ResolvedName>.data
```

Real examples from unpacked GRB forges:

```
0_-_Game Bootstrap Settings.data
1003_-_RA01_Boss_Wyvern_LOCOSEPARATED_EntTem.data
30091_-_WI_HDG_P12_Main.data
107094_-_FTP_Head_Angel_DiffuseMap_PC_Mip0.data
```

- The leading number is the **64-bit file ID** in decimal (`0`, `1003`, `30091`, …). This is the stable handle the game uses.
- The name after `_-_` is **resolved from ATK's hash dictionary**. Known hashes get human names; unknown ones fall back to the numeric ID. ATK has accumulated tens of thousands of GRB/Anvil hashes over its releases.

## Nesting: a `.data` holds typed resources

Unpack a `.data` and you get the actual engine resources, each with a **type-specific extension**. A concrete observed example:

```
23_-_TEAMMATE_Template.data/          ← a .data container (file ID 23)
    └── 295_-_Head_Hisp_Kunal.BuildTable   ← a typed resource inside it
```

Here the `.data` named `TEAMMATE_Template` contains a `BuildTable` resource. A single `.data` can contain multiple resources (a mesh plus its material reference, several BuildTable fragments, etc.).

> **Mental model:** `forge → many .data entries → each .data → one-or-more typed resources`. The forge is the shipping container; the `.data` is a box; the typed resources are the contents.

### Verified: how a `.data` is stored, and how each resource's type is tagged

Decompiling ATK's `DataFile` (v1.3.1), verified by parsing real files:

- A `.data` payload is a **compressed container**: two `CompressedFileData` blocks (a metadata/index block, then the file-payloads block). For GRB the blocks are **Oodle Mermaid in 32 KB chunks** with a per-block adler32 — full layout in [`02-forge-file-format.md`](02-forge-file-format.md). You cannot read the inner resources without decompressing (unless a block happens to be stored raw). [`tools/data_inspect.py`](../tools/data_inspect.py) does this with the game's Oodle DLL.
- Inside (decompressed), each resource record is `uint32 TypeId · int32 Length · string Name · Payload`, where the payload begins `[FileHeader][uint64 ClassID][uint32 Extension]…`. **`Extension` == `TypeId`**, and it is the resource's type — a `CRC32` of the type-name string (e.g. `CRC32("BuildTable") = 585940579`, `CRC32("Mesh") = 1096652136`). ATK reverse-resolves it to the extension you see on unpack. Full id↔type table: [`reference/resource-type-ids.md`](../reference/resource-type-ids.md).

## Typed resource files

The typed resources are where modding actually happens. ATK recognizes a long list of them and, for many, can export to an editable format (XML, glTF, DDS) and re-import. The most relevant for GRB cosmetic modding:

| Resource type | What it is | ATK can edit via |
| --- | --- | --- |
| **Mesh** | 3D geometry (weapons, gear, bodies, hair) | export/import **glTF/GLB** |
| **Skeleton** | Bone hierarchy for skinned meshes | glTF, XML |
| **TextureMap** | A texture (diffuse, normal, etc.), with mips | DDS / PNG / TGA / JPG |
| **TextureSet** | Named bundle of TextureMap slots for a material | XML |
| **Material** | Shader parameters + texture references | XML |
| **MaterialTemplate** | Reusable material definition | (hashes resolved) |
| **BuildTable** | Data-driven "recipe" assembling an entity/item from parts, meshes, materials, etc. | XML |
| **EntityBuilder** / **EntityGroupBuilder** | Entity assembly definitions | XML |
| **LocalizationPackage** | Text/strings | XML |
| **PrefetchingFileInfos** | Streaming/prefetch hints (sidecar) | — |
| **GlobalMetaFile** | Forge-wide metadata (sidecar, `.MetaFile`) | — |
| **Cloth / SoftBody / MotionSoftBody** | Physics-driven deformable assets | glTF / XML |
| **FacialSolverData** | Facial animation solving data | (supported 1.3.0) |

A fuller catalog with notes is in [`reference/resource-types.md`](../reference/resource-types.md).

## BuildTables: the glue

**BuildTables** deserve special attention because they are how GRB *assembles* a thing from its parts, and they are what you most often edit (besides the raw mesh/texture) to make a mod appear in-game.

A BuildTable is a serialized binary object graph. Hex from a real one (`295_-_Head_Hisp_Kunal.BuildTable`):

```
00000000  00 50 51 30 A6 9A 01 00 00 63 BE EC 22 01 08 00   .PQ0.....c.."...
00000010  00 00 00 00 00 F8 00 00 00 00 08 96 83 36 05 00   .............6..
```

Notice the recurring 8-byte pattern `50 51 30 A6 9A 01 00 00` — these are **64-bit file references** (IDs of other resources the BuildTable points at). A BuildTable is essentially a node graph of references: "this head = this mesh + this material + this texture set + these properties." ATK can export BuildTables to **XML**, which is human-editable, and recompile them back.

> This is why mods so often ship a tiny BuildTable `.data` *and* a heavy Resources `.data`: the BuildTable says "use my new mesh/texture," and the Resources forge supplies the actual bytes. See [`05-three-forge-model.md`](05-three-forge-model.md).

## File IDs are the real identity

Throughout GRB data, **the file ID — not the name — is the identity.** Names are a convenience layer ATK adds for humans. Consequences worth internalizing:

- Two resources can resolve to the same human name but have different IDs (e.g. `LOD0`/`LOD1`/`LOD2`/`LOD3` variants of one mesh).
- A **replacement** mod keeps an existing ID and swaps the bytes. A **new-content** mod introduces new IDs (and often uses placeholder IDs like `77777` during authoring — see [`08-naming-conventions.md`](08-naming-conventions.md)).
- Patch override at load time is keyed on the ID. Get the ID wrong and the game simply won't pick up your asset.

## Practical notes

- ATK's `IgnoredExtensions` default is `dependency;bak;dds;obj;glb;xml;ignored` — these are exactly the *workspace* files you generate while modding (exports, backups). ATK hides them in its Game Explorer so they don't clutter the view of real resources.
- ATK stores temp files smaller than ~1 MB in RAM during unpacking for speed (changelog 1.2.3), and moved compression/decompression "fully to RAM" (1.2.5) — relevant if you're scripting around it and wondering where intermediate files went.
