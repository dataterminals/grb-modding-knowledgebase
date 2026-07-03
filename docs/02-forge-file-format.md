# 02 — The `.forge` file format

A `.forge` is the top-level archive container for Anvil/Scimitar game data. Think of it as a **virtual filesystem in a single file**: a header, a body of (usually compressed) data entries, and an index that maps **64-bit file IDs** to those entries. GRB ships ~25 forge files (see [`reference/forge-inventory.md`](../reference/forge-inventory.md)); together they hold essentially the entire game.

> **Authoritative reference:** ATK is the community's working implementation of this format (its code literally has a "Scimitar Class"). Where this document and ATK's behavior disagree, **ATK is correct** and this doc should be fixed. The binary details below are what has been *directly observed* on a real GRB install plus what is *generally known* about Anvil forges; field-by-field layout beyond the header is flagged as not-yet-verified.

## Verified header bytes

Hex dump of the first bytes of `DataPC_patch_01.forge` from a real GRB install:

```
00000000  73 63 69 6D 69 74 61 72 00 1B 00 00 00 1A 04 00   scimitar........
00000010  00 00 00 00 00 10 00 00 00 00 00 00 00 01 00 00   ................
```

What we can read directly:

| Offset | Bytes | Interpretation |
| --- | --- | --- |
| `0x00` | `73 63 69 6D 69 74 61 72` | ASCII **`scimitar`** — the magic / signature. Every GRB forge starts with this. |
| `0x08` | `00` | Null / flag byte. |
| `0x09` | `1B 00 00 00` | **Version = 27** (`0x1B`), little-endian int32. (GRB / Origins-Odyssey-era forges.) |
| `0x0D` | `1A 04 00 00 00 00 00 00` | A 64-bit little-endian offset = **0x41A (1050)** — points into the forge's table region. |

> **Verified (now from ATK source, not just the hex):** magic = `scimitar`, version = 27, little-endian, 64-bit offsets/IDs. The `0x41A`/`1050` value is the **header size field**; ATK reads the header as `ReadBytes((int)headerSize - 21)`.

### Verified header layout (from `ForgeFile.Serialize27` / `Deserialize27`)

ATK's own reader/writer for GRB (version 27) lays the header out exactly like this:

| Field | Type | Value (GRB) | Notes |
| --- | --- | --- | --- |
| Magic | null-terminated string | `scimitar\0` | 9 bytes |
| Version | uint32 | **27** | (Origins/Odyssey=28, Mirage/Valhalla=29, Ezio/AC1=25) |
| HeaderSize | int64 | **1050** | the `0x41A` we saw in the hex |
| (constant) | int64 | 16 | |
| (constant) | int32 | 1 | |
| *padding* | — | skip 1017 bytes | header is mostly reserved/zeroed |
| EntriesCount | int32 | N | total entries in the forge |
| (constant) | int32 | 2 | |
| *padding* | — | skip 12 bytes | |
| (index hints) | int32 ×3 | -1 / N / N | entry-count bookkeeping |
| FileSetCount | int32 | M | number of "FileSets" (see below) |
| FirstFileSetOffset | int64 | **1094** | where the index begins |

After the header at offset **1094** comes the **FileSet table**. GRB splits entries into **FileSets of up to 5000 entries each** (a historical limit; ATK chains them via offsets). Each FileSet contains an array of **ForgeEntry** records.

### Verified entry record (`ForgeEntry`)

Each entry has two parts in two parallel tables:

**Offset-table record** (what locates the data):

| Field | Type | Notes |
| --- | --- | --- |
| Offset | int64 | byte offset of the entry's data in the forge |
| ID | **uint64** | the 64-bit file ID (uint32 for old Ezio games) |
| LengthOnDisk | int32 | compressed/stored size |

Record size is **192 bytes** for GRB-era forges (188 for older). The second, **info/metadata table** record (`ForgeEntry.ReadInfo`) carries: `LengthOnDisk`, `UMACHash` (uint64), `EngineVersion`, **`Extension` (uint32 — the resource *type* id)**, revision numbers, `Parent`, `TimeStamp`, **`Name`** (null-terminated, padded to 127 bytes), SCC status fields, `MetaFileKey` (class id), and `IsHidden`. When `Name` is empty, ATK falls back to the file ID — this is the `<ID>_-_<Name>` you see on unpack.

> **Key takeaway for modding:** a forge entry is *nothing but* `{ID, offset, size, type, name, timestamp}`. There is **no field tying an entry to a particular forge or to siblings** — identity is the ID alone. This is the technical basis for the load-time merge and for why the "three-forge split" is a convention, not a requirement (see [`05-three-forge-model.md`](05-three-forge-model.md) and [`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md)).

## The conceptual structure

Across the Anvil forge family, the format is consistently shaped like this:

```
┌───────────────────────────────────────────────┐
│ HEADER                                         │
│   "scimitar" + version + offsets to tables     │
├───────────────────────────────────────────────┤
│ DATA BODY                                       │
│   many compressed "chunks" — the actual         │
│   resource bytes for each entry                 │
├───────────────────────────────────────────────┤
│ FILE TABLE / INDEX                              │
│   one record per entry:                         │
│     • 64-bit FILE ID  (the stable handle)       │
│     • offset into the data body                 │
│     • compressed + uncompressed sizes           │
│     • name hash / resource type info            │
└───────────────────────────────────────────────┘
```

The **file ID** is the key concept. It is a stable 64-bit handle for a resource. The game and other resources reference assets *by ID*, not by filename. This is what makes the patch-override mechanism work: a patch forge that contains an entry with the *same ID* as a base entry will, at load time, take precedence (see [`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md)).

> ATK exposes these IDs in the forge index, but **the number in an unpacked filename `<N>_-_<Name>.data` is a positional index, not the file ID** — `FileSet.cs` writes `SetIndex*5000 + i`. The real 64-bit file ID (`ForgeEntry.ID`) equals the resource's **embedded `ClassID`** and is what references resolve against; see [`03-data-and-resources.md`](03-data-and-resources.md). The name is resolved from a hash dictionary ATK ships (it has added "around 35000 new hashes" and more across versions — many names are known, some remain numeric).

## Compression

Forge data entries are compressed. The relevant facts:

- GRB's resources forge is dominated by **Oodle** compression (the engine ships `oo2core_7_win64.dll` in the game directory; ATK ships its own Oodle handling). ATK's changelog references "Fixed Oodle crash when unpacking multiple files at once."
- ATK additionally links a stack of codecs (LZMA / fast-lzma2, LZ4, Zstandard/`libzstd`, LZO, 7-zip) — the Anvil family has used different codecs across games and entry types.
- **GRB-specific behavior:** ATK historically made *GRB data files always serialize uncompressed* (changelog 1.2.7), then later (1.2.9) *"Enabled GRB data file compression… you must enable compression in settings."* The default ATK config now ships with `EnableCompression = True`. This matters when repacking: see [`07-modding-workflow.md`](07-modding-workflow.md).

> **⚠️ Correction (2026-07-02, in-game verified):** for GRB this is **not** a mere preference — a `.data` written with **raw / uncompressed** blocks **crashes or hangs GRB at load** (it parses fine in ATK, but the game rejects it). A game-loadable GRB `.data` must be **Oodle-Mermaid-compressed** (`Version 3, Algorithm 3`, 32 KB blocks, per-block `adler32` seeded **0** — see the container spec below). Both a hand-written forge writer *and* a clean ATK repack fail identically when fed raw-block entries and succeed with compressed ones. So compression is a **load-safety requirement**, not a toggle you can leave off. See [`meta/research-log.md`](../meta/research-log.md) (2026-07-02).

> **Inferred:** that the base-game GRB resource entries are Oodle-compressed. Confirmed indirectly by the presence of `oo2core_7_win64.dll` and `compressed_oodle_compression_state.bin` in the game directory and ATK's Oodle code path.

### Verified: the `.data` block-compression container (`CompressedFileData` / `DataBlock`)

Decompiling ATK's `DataFile`, `CompressedFileData`, `DataBlock`, `CompressionInfo` and `Manager` (v1.3.1) resolves exactly how a `.data` entry's bytes are compressed — and it was **verified empirically** by parsing real GRB `.data` files and Oodle-decompressing them with the game's `oo2core_7_win64.dll`.

A GRB `.data` payload is **two consecutive `CompressedFileData` blocks**: first a small **metadata/index block**, then the **file-payloads block**. (Older AC games prefix a prefetch/int32 region; GRB has none.) Each `CompressedFileData` is:

| Field | Type | Notes |
| --- | --- | --- |
| Magic | uint64 | `1154322941026740787` (`0x1004FA9957FBAA33`); mismatch ⇒ "file could be locked" |
| CompressionInfo | 7 bytes | `int16 Version`, `byte Algorithm`, `uint16`, `uint16` (block-size fields) |
| BlockCount | int32 | (older games: int16) |
| BlockInfo[BlockCount] | 8 bytes each | `int32 UncompressedSize`, `int32 CompressedSize` (older: uint16 pairs) |
| Blocks[BlockCount] | — | each = `uint32 adler32` + `byte[CompressedSize]` |

Per block: if `UncompressedSize == CompressedSize` the block is **stored raw**; otherwise decompress to `UncompressedSize` with the codec named by `CompressionInfo.Algorithm`.

**GRB specifics** (`DataStorage.DataVersions[GhostReconBreakpoint] = (Version 3, Algorithm 3, Block 32768, …)`):
- Blocks are **32 768 bytes uncompressed** max.
- `Manager.GetCompressionAlgorithm` maps GRB's algorithm index: `0`=LZO1X, `1`=LZO1X999, `2`=LZO2A, **`3`=Oodle Mermaid (SuperFast)**, `4`=Oodle Mermaid (Optimal3). ATK writes **algorithm 3** by default, and can read any of `0–4`.

> **Verified (empirical):** parsing `1687_-_TP_Top_Bodark_Trench_Cloth.data` showed magic OK, `Version 3 / Algorithm 3`, a 44-byte raw metadata block, and five 32 768-byte payload blocks Oodle-compressed to ~17–24 KB each — decompressed correctly via `oo2core_7_win64.dll`. This **confirms and refines** the Oodle inference above: GRB `.data` compression is **Oodle Mermaid in 32 KB blocks with a per-block adler32**, at the `.data` (not forge) layer. See [`03-data-and-resources.md`](03-data-and-resources.md) for the surrounding container and [`tools/data_inspect.py`](../tools/data_inspect.py).

## Companion / sidecar files inside forges

When ATK unpacks a forge you will also encounter special entries:

- **GlobalMetaFile** — written out with extension `.MetaFile` (older ATK versions used `.data`; the README explicitly notes the rename). Holds forge-wide metadata.
- **PrefetchingFileInfos** — written out as `.PrefetchInfo`. Streaming/prefetch hints. ATK added GRB `PrefetchingFileInfos` support in 1.2.9.
- **Dependency** files — `.dependency`; ATK auto-deletes them for games that don't need them and lists `dependency` among its ignored extensions.

## `.data` vs `.forge`

ATK treats `.forge` **and** `.data` as unpackable containers — "To unpack/repack a `.forge` or a `.data` file, simply select it…". A forge unpacks into a folder of `.data` entries; a `.data` entry can itself be unpacked into its typed resources. That nesting is covered next in [`03-data-and-resources.md`](03-data-and-resources.md).

## Open binary-format questions

Items 1–4 below were **resolved** by decompiling ATK (2026-06-30) — see the verified layouts above. Remaining:

1. ~~Exact header layout~~ — **resolved** (`ForgeFile.Serialize27`).
2. ~~Index/entry record layout~~ — **resolved** (`ForgeEntry`).
3. ~~Per-entry **compression descriptor**~~ — **resolved** (`CompressedFileData`/`DataBlock`, verified empirically). See "Verified: the `.data` block-compression container" above.
4. ~~The full **`Extension` (resource-type) id → type** table~~ — **resolved**: the id is `CRC32(typeName)` and the map is `ScimitarClassRegistry`. GRB garment cloth is typed **`Cloth`** (id `3811591354`); there is no standalone `ClothPackage` id (it's nested). Full table + method: [`reference/resource-type-ids.md`](../reference/resource-type-ids.md).
5. The precise **GlobalMetaFile** and **PrefetchingFileInfos** schemas.

The ground truth for all of these is ATK's source. See [`04-anvil-toolkit.md`](04-anvil-toolkit.md) for how it was decompiled.
