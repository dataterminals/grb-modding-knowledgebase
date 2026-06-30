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

> **Verified:** magic = `scimitar`, version = 27, little-endian, 64-bit offsets/IDs.
> **Inferred (needs confirmation against ATK source):** the exact field that 0x41A indexes (data-header vs. file-table), and the layout of the index entries.

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

> ATK exposes these IDs directly. When it unpacks a forge, each entry is written out as `<decimalFileID>_-_<ResolvedName>.data`. The decimal number is the file ID; the name is resolved from a hash dictionary ATK ships (it has added "around 35000 new hashes" and more across versions — many names are known, some remain numeric).

## Compression

Forge data entries are compressed. The relevant facts:

- GRB's resources forge is dominated by **Oodle** compression (the engine ships `oo2core_7_win64.dll` in the game directory; ATK ships its own Oodle handling). ATK's changelog references "Fixed Oodle crash when unpacking multiple files at once."
- ATK additionally links a stack of codecs (LZMA / fast-lzma2, LZ4, Zstandard/`libzstd`, LZO, 7-zip) — the Anvil family has used different codecs across games and entry types.
- **GRB-specific behavior:** ATK historically made *GRB data files always serialize uncompressed* (changelog 1.2.7), then later (1.2.9) *"Enabled GRB data file compression… you must enable compression in settings."* The default ATK config now ships with `EnableCompression = True`. This matters when repacking: see [`07-modding-workflow.md`](07-modding-workflow.md).

> **Inferred:** that the base-game GRB resource entries are Oodle-compressed. Confirmed indirectly by the presence of `oo2core_7_win64.dll` and `compressed_oodle_compression_state.bin` in the game directory and ATK's Oodle code path.

## Companion / sidecar files inside forges

When ATK unpacks a forge you will also encounter special entries:

- **GlobalMetaFile** — written out with extension `.MetaFile` (older ATK versions used `.data`; the README explicitly notes the rename). Holds forge-wide metadata.
- **PrefetchingFileInfos** — written out as `.PrefetchInfo`. Streaming/prefetch hints. ATK added GRB `PrefetchingFileInfos` support in 1.2.9.
- **Dependency** files — `.dependency`; ATK auto-deletes them for games that don't need them and lists `dependency` among its ignored extensions.

## `.data` vs `.forge`

ATK treats `.forge` **and** `.data` as unpackable containers — "To unpack/repack a `.forge` or a `.data` file, simply select it…". A forge unpacks into a folder of `.data` entries; a `.data` entry can itself be unpacked into its typed resources. That nesting is covered next in [`03-data-and-resources.md`](03-data-and-resources.md).

## Open binary-format questions

These are tracked in [`meta/research-log.md`](../meta/research-log.md):

1. Exact header layout past offset `0x0D` (table offsets, counts, flags).
2. Index record layout (field order/sizes for ID, offset, sizes, name hash, type).
3. Per-entry compression descriptor (how the codec + chunking is recorded).
4. The precise GlobalMetaFile and PrefetchingFileInfos schemas.

The fastest path to answering these is to inspect ATK's reader/writer code (it is the ground truth). See [`04-anvil-toolkit.md`](04-anvil-toolkit.md) for the binaries involved.
