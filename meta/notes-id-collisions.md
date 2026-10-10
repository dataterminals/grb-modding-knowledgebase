# Notes — ClassID collisions between Wildlands and Breakpoint, and a re-ID scheme

Working notes for the Bolivia port (2026-10-10, SylDesk), to be folded into
[`research-log.md`](research-log.md). **Read-only on both installs.** Companion tools:
[`tools/id_census.py`](../tools/id_census.py) (the census) and [`tools/grw_reid.py`](../tools/grw_reid.py)
(the scheme and the reference rewriter).

**Question:** Bolivia would ship a set of ClassIDs: everything in GRW's world forges, plus what
those reference in GRW's global forges. Which of them already exist in GRB as **a different
object**? Those must be re-IDed before they go into GRB's forges.

## Summary

- **GRW has 938,225 unique resource ClassIDs**. **24,809 (2.6 %) also exist in GRB**:
  - **15,382 are the same object** (same type and name);
  - **9,427 are a different object** (9,273 renamed or reused, 154 re-typed);
  - the other **913,416 are free**.
- In the **world forges** specifically: 5,072 of 732,452 collide. 1,484 are the same object and
  **3,588 must be re-IDed** (meshes, LODSelectors, collision shapes, textures, entities). **No cell
  (`GridCellDataBlock`) ID collides.**
- **Both games keep plain IDs below 2^42 and never set bit 62 on derived IDs.** So
  `plain | 1<<46` and `derived | 1<<62` give a deterministic, reversible re-ID that is
  **collision-free by construction**. Checked exhaustively: tagging all 938,225 GRW IDs hits
  0 GRB IDs and 0 GRW IDs.
- `grw_reid.rewrite()` applies a remap inside payloads. On GRW's root cell it rewrote 73 ClassIDs
  and 482 references, and held back 12 typed-handle references for review.
- **26 of the 15,382 "same object" IDs are our own staged test content**: the converted Santa
  Muerte statue (mesh, materials, TextureSets, textures, mips), repacked into GRB's
  `DataPC_GRN_GhostRoom.forge` and later `DataPC_TGT_WorldMap_MaungaNui_Split_patch_01.forge` with
  its GRW IDs. Against vanilla GRB the counts are **24,783 shared, 15,356 same object**. Class (b) is
  unaffected.

## Method (verified)

**Container metadata blocks list their resources.** A `.data` container's first compressed block
is `u16 n`, then n × (`u64 ClassID | u32 size | u16 k | k × u16`), in the same order as the
resources in the files block. This was checked against full walks of 390 random containers in both
games: same IDs, same order, 390/390. A forge entry's own ID is always one of its container's
resource IDs. Reading only this block, a few KB per entry, makes a whole-install census cheap.

**Pass 1** (`id_census.py scan`) reads every forge's metadata blocks.
- **GRB:** 35 forge files (the 27 installed plus the 8 in `Backups\`), 4,727,378 rows,
  **1,053,400 unique IDs**, 42 s on NVMe. The `Extracted\` mod sources were skipped. The installed
  `DataPC.forge` is a mod's copy (`UE 2.0`) while `Backups\` holds the earlier one, so the union
  covers vanilla and modded IDs as installed.
- **GRW:** 19 forges, **938,225 unique IDs**, 5 min on the HDD. Every world and global forge read
  with 0 errors. Each forge has 2 non-container entries (the GlobalMetaFile and the prefetch table),
  and a handful of single entries in shader and title-screen forges failed; those were recorded
  by their entry ID.

**Pass 2** (`id_census.py classify`) walks one container per shared ID per side (precedence
patch > base > DLC/backup/other) to read the resource's type and name. That took 9,193 GRB
containers in 15 s and 6,066 GRW containers in 34 s.

**Reproducibility:** the numbers were first produced by scratch scripts, then re-run end to end
through `id_census.py`. The second run gave the same 938,225 / 1,053,400 / 24,809, and all
classes agreed except 8 IDs.
- Those 8 are the staged statue: the Ghost Room forge had been restored to vanilla between scan
  and classify, so their containers were gone.
- **The install changed during this work.** Between the two scans, a backup of MaungaNui's patch
  forge appeared and the installed one grew from 1,404 to 1,423 entries (the bivouac statue
  repack). Its file timestamp stayed at 2026-10-08, so the repack apparently preserves the forge's
  modification time. `classify` therefore re-reads a forge's index and retries when a container
  fails to read at its scanned offset.

| GRW category | unique IDs | also in GRB | (a) same object | (b) different object |
|---|---|---|---|---|
| world (`DataPC_GRN_WorldMap` + patch) | 732,452 | 5,072 | 1,484 | **3,588** |
| global (`DataPC`, `DataPC_extra` + patches) | 155,219 | 21,599 | 14,418 | **7,181** |
| DLC world (`DataPC_GRN_WorldMap_*_dlc`) | 91,635 | 1,947 | 475 | **1,472** |
| DLC global (`DataPC_*_dlc`) | 19,505 | 1,662 | 926 | **736** |
| other (Ghost Room, title screen) | 3,276 | 157 | 83 | **74** |
| **all (deduplicated)** | **938,225** | **24,809** | **15,382** | **9,427** |

An ID can sit in several categories, so the category rows do not add up to the total.
"Global" is a **superset** of what the world references: every GRW global object, not only the
referenced ones. The exact referenced subset would need a reference scan of the world payloads,
which has not been done.

## The classes

- **(a) Same ID, same type, same name: 15,382.** These are mostly engine and shared assets:
  `Default Normal Texture` (0x9), `BlackTexture`, `UnitSphere`, animations, `TextureMapSpec`,
  `XCurve`, and many `DB*` gameplay records (`DBGameContext`, `DBSkillPassive`, `DBNPCTag` …). In the
  world: 299 meshes, 229 textures, `TerrainSplattingNoise_Set`/`_DiffuseMap`, and
  `TerrainProceduralMaterial_0X100EC12B6FB`.
  **Recommendation:** reference GRB's copy and don't ship ours. GRB's copy is already in GRB's
  format, and a shipped copy in a higher-priority forge would override it for all of GRB. Same
  name and type does **not** guarantee the same bytes: of the 1,315 shared meshes, only 153
  convert byte-identical (2026-10-10 second entry). Treat (a) as "same intended object".
- **(b1) Same ID and type, different name: 9,273.** Name similarity ≥ 0.6 splits them:
  - **7,705 are renamed lineage objects.** Ubisoft carried the object over and renamed it, e.g.
    `Seasons` → `TGT_Seasons`, `GFX_Wood_Chips_DiffuseMap` → `…_PC`,
    `VEG-Des-AtlasPricklyCactus01` → `VEG-Res-…`, `x[ENV]_Cloud` → `GFX_Env_Cloud`,
    `TerrainBakingSettings_GR` → `TerrainBakingSettings`.
  - **1,568 are IDs reused for unrelated objects**, e.g. `VEG-Ari-Grass-FrailejonA` →
    `VEG-Res-Pickup-RosalesA` across its whole Set/Material/textures/LODSelector/LOD meshes, and
    `TER-Snow-Flatten-Aa-WHI#E1` → `TER-Grass-Dry-Aa1-CBS` (one of the 9 terrain materials).

  Either way, GRB's object is now a different thing. **Re-ID ours.**
- **(b2) Same ID, different type: 154.** All 154 keep their **name**; only the type hash changed.
  These are schema revisions such as `GR_DBFragGrenadeBehaviourParams_default`,
  `DBWeaponSmith_DBCamoTextureEntry` (39), `DBWeaponSmith_DBColorEntry` (34) and the drone essences.
  One is a derived ID (0x8000000083B80000, unnamed). **Re-ID ours** if shipped. In practice these
  are global gameplay records a port would replace with GRB's own.
- **(c) GRW-only: 913,416.** These are free; keep their IDs.

Type names were resolved via CRC32 and a hash dictionary. `classified.tsv` (one row per shared ID:
class, both types and names, and the forges) is regenerated by `id_census.py classify`.

## The ID space (verified on both full sets)

| | GRB | GRW |
|---|---|---|
| plain IDs (bit 63 clear) | 861,367, all < 2^42 (max `0x25D7D61641A`) | 778,353, all < 2^42 (max `0x261CEC007F3`) |
| plain IDs in [2^42, 2^63) | 0 | 0 |
| derived IDs (bit 63 set) | 192,033; bit 62 never set; top byte `0x94`–`0x9E` | 159,872; bit 62 never set |
| bit-length of plain IDs | 99.6 % in 2^35–2^42 (allocator families) | same |

Derived IDs are `0x8000_0000_0000_0000 | base << 20 | k`, with the base up to 41 bits (GRB) and
k ≤ 240,312. Examples: GRB's `MultiForgeOriginalTargetInjectionInfo` (base = cell ID) and GRW's
per-cell derived resources (e.g. `0x81B18C34DE600000` in `Cell04843`, base = that cell's ID). Only
**one** derived ID collides, and no cell ID does. Formula-derived IDs therefore stay valid as long
as cell IDs keep their GRW values.

## The re-ID scheme (`tools/grw_reid.py`)

```
reid(i) = i | 1<<46    if bit 63 is clear   (plain;   i < 2^42 asserted)
reid(i) = i | 1<<62    if bit 63 is set     (derived)
unreid(i) clears the tag again.
```
- **Deterministic and stable:** a pure function of the GRW ID, with no state or allocation table.
- **Collision-free:** neither game has any ID in either tagged band. Tagging every one of GRW's
  938,225 IDs produced 0 hits in GRB's 1,053,400 IDs and 0 in GRW's own.
- **Apply it to class (b) only.** Class (a) should point at GRB's copy and class (c) keeps its ID.
  The remap is `{i: reid(i) for i in classB}`, 9,427 entries (3,588 in the world forges).
- **Engine caveat (not verified):** nothing shows the engine giving bits 42–62 a meaning, but
  nothing rules it out either. Test one re-IDed object in game before converting at scale. Bit 46
  keeps tagged plain IDs well clear of the derived formula: a plain ID used as a cell base would
  shift out of range, but no cell needs re-IDing anyway.

### The rewriter
`rewrite(payload, remap, strict=True, extra_prefixes=())` finds every 8-byte little-endian
occurrence of a remapped ID. In strict mode it replaces one only at payload offset 0 (the
ClassID) or right after a reference prefix seen in GR formats: `01 00`, `01 01`, `01 02`, `03 00`,
or a single `00` (the TerrainMaterial TextureMap list). Everything else is returned as `skipped`
with its context, because an 8-byte match inside vertex or pixel data can be a coincidence.

**Real-data check, GRW root cell `Cell21844` (3,486 resources):** 73 of its resources have a
class-(b) ClassID. The rewriter made **555 replacements** (73 ClassIDs + 482 references) and held
back **12**. All 12 are in the `x[ENV]_Cloud_*` entities, which reference their FX template
(`x[ENV]_Cloud`, b1 → GRB `GFX_Env_Cloud`) as `8a b0 b8 01` + u64: a typed handle, apparently a
u32 type hash before the ID. They are genuine references, so pass `extra_prefixes=(bytes.fromhex("8ab0b801"),)`
or review them. Expect more such encodings in other entity types; strict mode exists to surface
them.

## Open items
1. The exact set of global objects the world references (a reference scan of the world payloads).
   The superset above is safe but larger than needed.
2. Whether GRB tolerates IDs with bit 46 (or bit 62) set. One in-game test.
3. Typed-handle encodings beyond `8a b0 b8 01 + u64`. Collect them from `skipped` as conversion
   proceeds.
4. Class (a) content: same name and type, but the bytes may differ. Decide per type whether GRB's
   copy is an acceptable stand-in (textures and defaults likely; re-baked meshes are a judgement
   call).
5. The GRB install is modded. Its patch forges and `DataPC.forge` carry mod content, and those IDs
   count as GRB IDs here. On a vanilla install the GRB set could shrink slightly; the tag bands
   would still be empty. Our own staged port objects (the 26 above) also count, so re-run the
   census after restoring vanilla forges, or ignore IDs whose only GRB home is a test-modified
   forge.
6. Converted Bolivia objects that keep their GRW IDs (class c) are safe against GRB but will show
   up as "same object" in any later census once they are installed. Read them as ours, not
   Ubisoft's.
