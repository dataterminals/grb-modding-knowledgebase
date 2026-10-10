# Notes — terrain `.tbf` nodes, Wildlands v14 vs Breakpoint v16

Working notes for the Bolivia port (2026-10-10, SylDesk), written to be folded into
[`research-log.md`](research-log.md). **Read-only on both installs.** Every number below comes
from parsing the real files with throwaway scripts in the session scratch (memory-capped,
single-node reads). GRB was running during part of this work, so GRB samples were kept small.

Files: GRW `PCgr_terrainlin0/1.tbf` (Wildlands install root); GRB `PCtgt_terrainlin0/1/2.tbf`
(Breakpoint install root).

## Summary

- **Heights use the same codec in both games.** They are 132×132 `int32` samples per node, coded as
  2nd-order raster residuals in `int16`, with an escape that restarts the predictor. Metres =
  `value × range / 2^20`, where `range` is the header float (GRB 1500.0; GRW 3000.0, inferred).
- **GRB's mystery second table half is per-node `(f32 minHeight, f32 maxHeight)` in metres.**
- **Nodes:** row-major per level, 128-sample pitch, a 2-sample apron on every side (132 = 2 + 128 + 2).
  A child's sample `2k` equals its parent's sample `1 + k` exactly, in both games.
- **Block structure is fixed per version** (600/600 GRW and 150/150 GRB random nodes parse
  strictly). v14 → v16 kept the heights, the material-ID raster, the `fe` raster and two of the
  `00` rasters. It **dropped** v14's five zlib "image" layers and three of its five `00` rasters, and
  **added** two Oodle-compressed textures, a BC1 colour map and a BC7 map.
- **Conversion v14 → v16 is half mechanical.** Heights, material IDs and the trailer can be
  re-encoded byte-exactly. The rest must be remapped (material IDs) or synthesized (the BC1 colour
  and BC7 maps). See the last section.

## File header and node table

`FBT\0 | u32 version | u32 a | u32 b | u32 c | f32 heightRange | u32 nodeCount`, then the tables.

| | version | a | b | c | heightRange | nodes | tables after the header |
|---|---|---|---|---|---|---|---|
| GRW lin0/lin1 | 1 | 16 | 2048 | 1024 | 3000.0 | 87,381 (9 levels) | `u64 offset[nodes]` |
| GRB lin0/lin1 | 2 | 32768 | 65536 | 64 | 1500.0 | 349,525 (10 levels) | `u64 offset[nodes]`, then `f32 min, f32 max` × nodes |
| GRB lin2 | 2 | 2703228928 | 1992864825 | 59 | 1500.0 | 349,525 | same layout |

> **Verified:** node `i` of level `L` is at index `(4^L − 1)/3 + row·2^L + col`. This is **row-major
> within each level** (lin0's subset forms clean 3×3 blocks under this rule). An offset of 0 means
> "not in this file". All three GRB files carry the identical min/max table.
>
> **Verified (GRB second half):** each entry is `f32 minHeight, f32 maxHeight` in metres for that
> node's own height grid. For example, tile L9 (248, 338) reads 139.8–149.7 m, and the root reads
> 0–1400.8 m. Decoding the heights (below) reproduces `max` exactly (120/120 nodes). `min` matches
> too, except near sea level: where the decoded minimum is below 0.015 m the table usually reads
> 0.015, though one node reads −0.005. These are no file offsets, which is why they look like
> ~4.8e18 when read as `u64`. No node's max exceeds 1473.4 m, and nothing in the table goes past
> the 1500 m range.
>
> **Inferred (header):** GRB `32768 | 65536 | 64` = world width in metres, samples across at the
> leaf level (512 tiles × 128), and leaf tile size in metres. GRW `16 | 2048 | 1024` reads as 16
> sectors of 1024 m, 2048 leaf samples per sector. Both give a 0.5 m leaf sample spacing. lin2's
> three `u32`s are unexplained.

### Which file holds which node (verified)
- **GRW:** lin1 holds **all** 87,381 nodes. lin0 is a small copy: levels 0, 1 and 4 complete, plus a
  3×3 block around the map centre at every other level. Its offsets equal lin1's.
- **GRB:** lin0 holds levels 0, 1 and **5** complete, plus the central 3×3 at every other level. lin1
  holds everything else (the two are disjoint). lin2 holds a single chain through the tree
  (L1 (0,0) … L6 (16,16), then pairs down to L9 (134,131)/(134,132)). That is one spot in the
  north-west quadrant, unexplained (perhaps the menu or boot location).
- The full level in lin0 is the 1024 m-tile level in both games (GRW L4 = 16×16, GRB L5 = 32×32),
  which fits GRW level L ↔ GRB level L + 1 at equal tile size.

## Node framing (both versions)

```
u16 0xFEED | u16 version (GRW 14, GRB 16) | u8 1 | u32 heightZLen | zlib heights (heightZLen bytes)
then length-prefixed blocks: u32 len | payload
then a 40-byte trailer (no length prefix)
```

### Heights — identical codec in v14 and v16 (verified)
The zlib output is a stream of `int16` tokens decoding to 132×132 = 17,424 `int32` samples in
raster order:
- token `0x7FFF` (the `ff 7f` every height chunk starts with) = **restart**: two `int32` literal
  samples follow;
- any other token `r`: `h[i] = 2·h[i−1] − h[i−2] + r` (2nd-order prediction across row
  boundaries too).

The output is 34,854 B with one restart, plus 6 B per extra restart, which explains the
variable sizes 34,854 / 35,298 / 38,538 / 40,356. The stream consumes exactly the chunk on every
node tested.

- **Scale, verified on GRB:** `metres = value × 1500 / 2^20` (699.05 units per metre). The decoded
  min/max matches the node table's floats on every sampled node.
- **Scale, inferred on GRW:** `value × 3000 / 2^20` by analogy with the header float. That gives the
  GRW root 411–2647 m. Not yet cross-checked against an entity's placed height.
- **Both games keep heights below 2^20** (verified). GRB's raw max is 979,212. GRW's raw max is 938,579
  over all of levels 0–4 plus 600 deeper nodes, against 1,048,576. So a height is a 20-bit
  fraction of the header's `heightRange`, and the range is the only per-world scale.
- **Re-encoding is byte-exact (verified):** restart whenever the residual falls outside
  [−32768, 32766], and at the start. Re-encoding the decoded heights reproduces the game's token
  stream on 200/200 GRW and 45/45 GRB nodes, plus 120 + 120 more in `tools/tbf_read.py selftest`.
  (The zlib wrapper's own bytes differ from Python's `zlib` at levels 1/6/9; any valid stream
  should do, but that is untested in game.)

#### Is the 1500 m range hardcoded in GRB? (checked 2026-10-10, inconclusive but encouraging)
- A streamed scan of `GRB.exe` (536 MB) finds **no `1500/2^20` constant**. Its two raw byte matches
  (`00 80 BB 3A`) both sit inside instructions (`80 BB 3A …` = `cmp byte ptr [rbx+…]`). There is no
  `f32`/`f64` `2^20/1500` either. Plain `1500.0f` occurs 15 times and `3000.0f` 5 times, at unaligned
  code offsets, which is normal for unrelated immediates.
- The exe has no `FBT\0` literal. It names the files with the format string **`_terrainlin%d.tbf`**
  (beside `TerrainMaterialsStaging[%d]`), with the platform/world prefix (`PCtgt`, `PCgr`)
  formatted in front.
- **Inferred:** the engine takes the scale from each file's header, and a ported world would ship
  its own `PC<world>_terrainlin*.tbf` with `heightRange` 3000. That way Wildlands heights need no
  rescaling. This can only be confirmed in game.
- **Geometry, verified:** horizontal and vertical neighbours overlap by exactly 4 samples (shift
  128). A child's sample `2k` equals its parent's `1 + k` (100 % of 3,600 samples tested). So samples 2…129
  are the node's own 128, plus a 2-sample apron on each side.

### Run-length rasters (verified, both versions)
Several blocks are one 132×132 `u8` raster each, coded as literal bytes plus runs
`marker count value` (count 1–255). **The marker is fixed per block slot, not stored:**
`0xFF` for the material raster, `0xFE` for the "FE" raster, and `0x00` for the `00` rasters. Each block
decodes to exactly 17,424 bytes.

**Encoder rule (verified byte-exact on 1,400 GRW and 180 GRB rasters, plus the selftest's
840 + 480):** a run of 4 or more equal bytes (split at 255), or any byte equal to the marker,
becomes a `marker count value` token. Everything else is literal.

### The 40-byte trailer (verified in part)
`f32 a | f32 b | u8 materialMask[32]`.
- **Verified:** `materialMask` is a 256-bit set (bit `k` = byte `k/8`, bit `k%8`). It equals
  **exactly** the set of values in the node's material raster (300/300 GRW and 100/100 GRB nodes).
- `a ≤ b` always. Range 0.14–0.89 in GRW, 1e-21 to 0.96 in GRB, and larger at coarse levels.
  **Meaning unknown.**

## v14 (Wildlands) node layout — verified on 600/600 random nodes

| # | Block | Decoded | Meaning |
|---|---|---|---|
| 0 | frame + zlib | 132×132 `int32` | **heights** (above) |
| 1 | `u32 len \| u32 zlen[4] \| 4 × zlib` (`len = 16 + Σzlen`) | 33,808 / 8,452 / 8,452 / 33,808 B | four "image" layers A0–A3 (below) |
| 2 | `u32 len \| RLE(0xFF)` | 132×132 `u8` | **material ID raster** (`M`) |
| 3 | `u32 len \| u32 zlen \| 12 stale bytes \| zlib` | 33,808 B | image layer `Z` (below) |
| 4 | `u32 len \| RLE(0xFE)` | 132×132 `u8` | **FE raster** (mostly `0xFF`) |
| 5–9 | 5 × `u32 len \| RLE(0x00)` | 132×132 `u8` each | **`00` rasters** (weights / masks) |
| — | 40 B | | trailer |

- The first `u32` of the old "five `u32` size table" is the block length. The other four are the
  zlib sizes. Block 3's 12 bytes after `zlen` are **stale buffer contents**, a copy of bytes 8–19
  of the previous block (verified on several nodes). A writer can put anything there.
- **`M` raster:** few distinct values (7–30 per node). It renders as clean terrain regions (road
  and verges visible). Values are indices into a 256-entry material table (see the trailer mask).
- **`00` rasters (the `0x00`-marker slots), measured on 300 random GRW and 120 GRB nodes:**

  | | slot | non-zero in | values | correlations (mean per node) |
  |---|---|---|---|---|
  | GRW | 0 | 42 % of nodes | 0–255, smooth | height −0.38, slope −0.22, material R² 0.43 |
  | GRW | 1 | 76 % | binary 0/255 | none (≈ 0.06) |
  | GRW | 2 | 28 % | binary 0/253 | height −0.33, **material R² 0.71** |
  | GRW | 3 | 24 % | 0–255 | weak |
  | GRW | 4 | 90 % | 0–162 | none |
  | GRB | 0 | 33 % | enum: 0 (91 %), 2 (8 %), 1, 3, 255 | BC7 water alpha +0.23, otherwise weak |
  | GRB | 1 | 13 % | 0–255, 139 distinct | none |

  "Material R²" is the share of a slot's variance explained by the material ID under it.
  **No slot pairing could be established from file statistics alone.** By value domain only,
  GRB 1 (0–255 weight) resembles GRW 0 or 3, and GRB 0 (a small enum) has no GRW counterpart.
  Settling it needs the terrain material names or an in-game A/B test.
- **FE raster:** non-`0xFF` in 21 % of GRW nodes and 28 % of GRB nodes. GRW values look like IDs
  (20, 41, 33, 19, 38, 0 most common). GRB's are dominated by `0xFE` and 0, then 4, 13. About half
  of the distinct FE values per node also occur in the material raster, and the trailer mask never
  includes FE-only values. FE does not pair with any weight slot (P(slot ≠ 0 | FE set) ≤ 0.33).
  **Meaning unknown.**

### v14 "image" layers A0–A3 and Z (structure verified, predictor NOT decoded)
- Sizes are fixed: **33,808 = 1,040 + 2 × 128²** and **8,452 = 260 + 2 × 64²**. Each layer is a
  `u8` block (1,040 or 260 B) followed by a 128×128 (or 64×64) grid of `int16` residual tokens.
  1,040 = 132² − 128² and 260 = 66² − 64², so the `u8` block was first read as the apron ring.
  But its bytes don't line up with the decoded core in any tested ordering (it also isn't a
  ¼-scale thumbnail: 1,040 = 32² + 16 fits the size, but the correlation is ≈ 0). **Its layout is
  unknown.**
- **Verified on the tokens:** exactly four literal-sized tokens, at core positions (0,0), (0,1),
  (1,0) and (1,1); everything else is small. On a flat salt-flat node (L8 249,14), the literals
  are ≈ the `u8` block's values × 64 for A1/A2 (7,916–7,920 vs 124–128) and **× 128 for A0**
  (21,246–21,323 vs 162–173). So the cores are 14- or 15-bit versions of 8-bit quantities. On
  that node Z is the constant 32,000 (four literals, 16,380 zero tokens) and its `u8` block is
  all 255.
- **Predictor search (not solved):** first-order along rows 0–1 and columns 0–1 fits the flat
  node. For the interior, `(L + U) >> 1` gives clean but diagonally drifting images (the drift
  shows even on the flat node). Predictors using the up-right neighbour (`(L+U+UR)/3`,
  `(2L+U+UR)/4`) remove the diagonal drift but leave a vertical one. MED, gradient, plain `L`/`U`
  and spacing-2 (polyphase) variants are worse. **Some edge or rounding rule is still wrong;**
  the exe's decoder would settle it.
- A3 was all zero on every sample. A1/A2 sit near `0x80` (signed, normal- or derivative-like).
  Z is mask-like (lots of 0/255).
- **For the port this may not matter:** GRB wants a BC1 colour map, and Wildlands already ships
  world colour as raw BC1 in `gr.wmap` (2026-10-08). Resampling that per node is the likelier
  source than these layers.

## v16 (Breakpoint) node layout — verified on 150/150 random nodes

| # | Block | Decoded | Meaning |
|---|---|---|---|
| 0 | frame + zlib | 132×132 `int32` | **heights** (same codec) |
| 1 | `u32 len \| RLE(0xFF)` | 132×132 `u8` | **material ID raster** |
| 2 | `u32 len \| RLE(0xFE)` | 132×132 `u8` | **FE raster** |
| 3–4 | 2 × `u32 len \| RLE(0x00)` | 132×132 `u8` each | **`00` rasters** |
| 5 | `u32 len \| u32 8712 \| Oodle` | 8,712 B | **BC1 132×132 colour map** |
| 6 | `u32 len \| u32 17424 \| Oodle` | 17,424 B | **BC7 132×132 RGBA map** |
| — | 40 B | | trailer |

- The Oodle blocks are Mermaid (`8C 0A …`). The ones starting `CC 0A` are Oodle's
  stored/uncompressed form (data follows raw). Both decode with the game's `oo2core_7_win64.dll` via
  `tools/data_inspect.py`'s `Oodle` class.
- **Verified BC1:** decoded as `BC1_UNORM` 132×132, it is a clean albedo image (snow, grass,
  riverbed and trails), aligned with the height and material rasters.
- **Verified BC7:** a 16-byte block stride with 33 blocks per row; only BC7 modes 4–7 occur, and it
  decodes as `BC7_UNORM` into coherent channels. R and G are flat per material region, B is a
  smooth mask, and A lights up only on water (a river). **Inferred:** per-sample surface
  parameters (material-driven R/G, a blend or wetness term in B, water in A).
- GRB's `00` rasters and the FE raster are profiled in the v14 section's table above.

## Can a v14 node be rewritten as v16?

| v16 part | From v14 | Effort |
|---|---|---|
| frame, version 16 | rewrite | mechanical |
| heights | **same codec, same 20-bit normalisation**: copy unchanged into a Bolivia-own `.tbf` whose header says 3000.0 (if GRB reads the scale per file; see above). Into Auroa's 1500 m file, they would need rescaling plus an offset or clipping (GRW reaches ~2685 m, inferred) | mechanical (byte-exact re-encoder in `tools/tbf_read.py`) |
| min/max table entry | computed from the decoded heights (floor 0.015) | mechanical |
| material raster | same RLE. Unchanged if Bolivia keeps its own `TerrainMaterialBank` (route A below); remapped via `terrain-material-remap.tsv` if merged into Auroa (route B) | mechanical either way |
| FE raster | GRW's holds ID-like values in 21 % of nodes; copy and remap like the material IDs, or blank it to `0xFF` | unknown semantics, so test in game |
| two `00` rasters | pick from GRW's five, or zero them | needs the slot mapping (open; zeros are a safe first test) |
| BC1 colour | **synthesize** from `gr.wmap` (raw BC1 world colour), resampled per node, then BC1-encode + Oodle. The v14 image layers are a fallback once decoded | moderate |
| BC7 map | **synthesize**: R/G from the remapped materials, A from a water mask, B unknown, then BC7-encode + Oodle | moderate, semantics partly unknown |
| trailer | floats: copy or recompute (meaning unknown); mask: recomputed from the remapped raster | mechanical except the floats |
| placement | GRW level L → GRB level L + 1 at equal tile size. **Quadrant placement:** Bolivia = one GRB L1 node, every GRW node maps 1:1, and only GRB's root must be rebuilt. **Centred placement:** GRW (L, r, c) → GRB (L + 1, r + 2^(L−1), c + 2^(L−1)) for L ≥ 1. GRW's root has no GRB twin, so GRB L0 and L1 must be rebuilt by downsampling | mechanical, once a placement is chosen |

**Bottom line:** the geometry (heights, tree, bounds) ports mechanically. The surface (materials,
colour, the BC7 parameters) needs a material-ID remap and two synthesized textures. GRW's own
image layers would be the best source once their codec is fully pinned.

## Terrain materials: what the material raster's IDs mean (2026-10-10, later)

**Where the tables live (verified, read-only):**
- **GRW:** the root cell `Cell21844_DataBlock`, entry 116394053711 in `DataPC_GRN_WorldMap_patch_01.forge`
  (84 MB decompressed, 3,486 resources, complete walk).
- **GRB:** Bootstrap's root piece, `MFD_GridCellDataBlock_Cell87380_DataBlock(0x15CE78BD662)` in
  `DataPC_TGT_WorldMap_Bootstrap_Split.forge` (2,788 resources, complete walk). The base `_Split`
  forge is vanilla; Bootstrap's `_patch_01` does not override this piece. The other five regions'
  root pieces (~1.5 MB each) were not inspected.
- **Type names, confirmed as CRC32 of the name:** `TerrainMaterialBank` 1273578117,
  `TerrainMaterial` 24265096, `TerrainProceduralSetBank` 1707329488, `TerrainProceduralSet`
  793065790, `TerrainBakingSettings` 408039881.

**The chain (verified by resolving every 64-bit reference):** each world's `Terrain` entity
(`Terrain_001` in GRW, `Terrain_TGTWorldMap` in GRB) references its own `TerrainMaterialBank`
(`…_0X10EB8A262E` / `…_TGT`) and `TerrainProceduralSetBank`, plus `TerrainBakingSettings`, a
template material (`Terrain_template` / `TerrainMaterial`) and `TerrainSplattingNoise_Set`. GRW
also references `GrassPatternLibrary_WorldMap`; GRB references `TerrainGraphicSettings_TGT-Draft`.

**The Terrain entity also names the `.tbf` files and sets the height range (verified):**
```
GRW Terrain_001          … d8 94 89 98 | f32 3000.0 | u32 2 "gr\0"  | u32 10 "GR_Terrain\0" | 00 04 00 00 …
GRB Terrain_TGTWorldMap  … d8 94 89 98 | f32 1500.0 | u32 3 "tgt\0" |                        | 00 04 00 00 …
```
The float equals each world's `.tbf` `heightRange`, and the string is the `<prefix>` in
`PC<prefix>_terrainlin%d.tbf` (the exe's `_terrainlin%d.tbf`). GRB's version drops GRW's second
string. **Inferred:** a ported world's own Terrain entity, with `3000.0` and a prefix such as `gr`,
would make GRB load that world's own `.tbf` set at Wildlands' scale. Together with the per-file
header, this is the strongest file-side evidence yet that the 1500 m limit is per world, not
global. Still to be proven in game.

**`TerrainMaterialBank` layout (verified, both games parse to the last byte):**
```
u64 ClassID | u32 typeID | u8 1 | u32 nDetail | nDetail × ref | u32 nMaterials | nMaterials × ref | ref displacement
ref = u8 1 | u8 0 | u64 id
```
GRW: 5 detail sets (`TER-Cliff-…-Details_Set`), **169 materials**, then `Terrain-DisplacementsArray`.
GRB: 15 detail sets, **190 materials**, then a null ref (`03 00` + 0).
`TerrainProceduralSetBank` is `u64 | u32 | u8 | u32 n | n × ref`: GRW 157 `TPS-…` sets
(`TPS-Salar-Rough`, `TPS-Altiplano-Green` …), GRB 261.

**A raster material ID is the index into its world's material list (verified):**
- The highest ID in any trailer mask is 168 in GRW (1,841 nodes: all of levels 0–4 plus 1,500
  random leaves) and 189 in GRB (841 nodes), i.e. bank size − 1 in both.
- GRW's bank has 26 materials named `z-(Dont-Used)-…`. **None of them appears in any node**, and
  they are 26 of the 27 bank slots never seen.
- **Inferred:** the FE raster indexes the `TerrainProceduralSetBank` in the same way. Every FE
  value seen is below the bank size (max 126 of 157 in GRW, 133 of 261 in GRB, excluding
  `0xFE`/`0xFF`). But GRW's set 0 is `z-(Do-Not-Use)-TPS-Illegal` and FE = 0 does occur, so this
  is weaker.

**`TerrainMaterial` (GRW 245 B, GRB 356 B; same skeleton, verified on both):**
`u64 ClassID | u32 type | ref TextureSet | … | u32 4 | 4 × (u8 0, u64) TextureMaps
(Diffuse, Normal, Height, Mask1) | parameters | tint records (u8 index, …, 4 × f32 RGBA; GRW 4,
GRB 6) | …`. The **ground (physical) material ref** sits exactly 16 bytes before the end (190/190
GRB, 162/169 GRW; the other 7 are GRW crop-field materials with none).

**Ground types are shared between the games (verified, same IDs, same names):**
`GRN_Ground_Gravel/Dirt/Mud/Grass/Asphalt/Sand/Snow/Snow_Deep/TrainTrack` (`0x1B133A50xx`).
GRW-only: `GRN_Ground_Salt` (4 materials). GRB adds `Rock`, `Lava`, `Gravel_Flat`, `Dirt_Flat`,
`Sand_Flat`, `TGT_RAID_LavaField` and six IDs not found in GRB's non-resource forges. **Both
games have a `TER-HOLE` material with the same ground ID `0x1523930CA5`** (GRW index 102, GRB
index 65).

### What this means for the port
- **Route A, Bolivia as its own world (recommended):** a ported world brings its own root cell,
  Terrain entity and `TerrainMaterialBank`. Its 169 materials keep their order, so **the
  `.tbf` material rasters need no remap at all.** The work moves to converting each
  `TerrainMaterial` (245 → 356 B) and its textures: one TextureSet and four TextureMaps each, which
  `tools/grw2grb.py`'s texture rules already cover. A likely shortcut, mirroring the mesh-material
  transplant: clone a GRB `TerrainMaterial` with the same ground type and repoint its TextureSet
  and TextureMap refs. The ground refs carry over as-is, because the IDs are shared. Up to 256
  entries fit.
- **Route B, merging into Auroa's terrain:** the IDs must be remapped onto GRB's 190 materials.
  [`terrain-material-remap.tsv`](terrain-material-remap.tsv) has a suggested table for the 142 GRW
  IDs in use. It matches on the same ground type first, then name tokens. Confidence: 1 exact
  (`TER-HOLE`), 30 high, 101 medium, 10 low (3 salt with no GRB salt; 7 crop fields with no ground
  type). It is **lossy: 142 materials collapse onto 24**, and colour was not compared. Appending
  GRW materials to GRB's bank instead leaves room for only 66 (190 + 66 = 256).

## TerrainMaterial: field map and converter (2026-10-10, later still)

**No content twins exist.** No texture or TextureSet ID is shared between the two games' terrain
materials. Only `TER-HOLE` shares a name. **9 ClassIDs are shared under different names** (e.g.
GRW `TER-Snow-Flatten-Aa-WHI#E1` = GRB `TER-Grass-Dry-Aa1-CBS`): Ubisoft carried those database
objects over and repurposed them. They help align the structure but not the values.
Consequence for a port: **9 GRW terrain-material ClassIDs collide with different GRB objects.**

**ATK's AC schemas** (`ACOrigins`/`ACOdyssey`; ATK has none for GRW/GRB) name the fields
`CompiledData` (Handle), `Roughness`, `CollisionMaterial` (Reference), `Index` (U32), `Hole`,
`UVNoise`, `UVRotationAngle` and `DisableTesselation`. Ghost Recon's TerrainMaterial is much
larger, but these anchor the names below.

| Field | GRW offset (245 B) | GRB offset (356 B) | Status |
|---|---|---|---|
| ClassID, type id | 0, 8 | 0, 8 | verified |
| TextureSet ref (`01 00` + u64) | 12 / 14 | 12 / 14 | verified |
| 5-byte field (first byte 0/12/13) | 22 | 22 | same domain, meaning unknown |
| u64 handle, unresolved in either game (`CompiledData`, inferred) | 27 | 27 | — |
| `u32 4` + 4 × (u8 0, u64) TextureMaps: Diffuse, Normal, Height, Mask1 | 35, 39 | 35, 39 | verified |
| scale (1, 0.5, 2, 0.25 …) | f32 187 | f32 75 | inferred (same value domain) |
| UV tiling (200, 100, 20, 400 …) | f32 191 | f32 79 | inferred (same value domain) |
| tint records (28 B each, marker `ed 67 97 a7`) | 4 at 75 + 28i, pattern A B A B | 3 at 110 + 29i (+ u8 flag), then 3 at 197 + 28i | layout verified, semantics unknown |
| three small signed floats | 215, 219, 223 | 326, 330, 334 | inferred (same value domain) |
| `Hole` (u8, 1 only on TER-HOLE) | 212 | 323 | verified (1/169, 1/190) |
| `CollisionMaterial` = ground (`01 00` + u64) | 227 / 229 | 338 / 340 | verified |
| `Index` (u32 = bank slot) | 241 | 352 | verified (169/169, 190/190) |
| GRB-only params (f32 83 ≈ 0.04, 87, 91, 101 ∈ {10…40}, flags 105/109, 281–321, 348) | — | — | from the template |

GRW's tints have two colours in 154/169 materials; GRB's two groups are equal in 137/190. So
which GRW colour belongs in which GRB group is **unknown**. The converter writes A → group 1 and
B → group 2 (`--tints a` writes A to both).

**Converter: [`tools/terrain_material.py`](../tools/terrain_material.py).** It has `list`, `convert` and
`selftest`. `grw_to_grb()` clones a GRB template material and writes into it GRW's ClassID,
bytes 12–74 (TextureSet, handle, TextureMaps), scale, tiling, the three floats, `Hole`, ground,
tints and the new `Index`. All other bytes come from the template.
- **Template choice:** `TER-HOLE` → GRB `TER-HOLE`. Otherwise a GRB material with the same ground
  type (skipping `TER-TGT-*` raid/debug ones), ranked by name-token overlap. GRW's
  `GRN_Ground_Salt`, which GRB lacks, is aliased to `GRN_Ground_Sand`. Crop fields with no ground
  keep the template's.
- `convert` also writes a GRB-format `TerrainMaterialBank` in **GRW's order**, so the `.tbf`
  rasters need no remap. It ends in GRB's null ref instead of GRW's `Terrain-DisplacementsArray`.

**Selftest (both vanilla roots, verified):**
- Both banks rebuild byte-exact. 169 + 190 materials parse; Index = slot everywhere; `TER-HOLE` is
  the only hole in each.
- All 169 conversions re-parse as GRB. They use 24 distinct templates; only the 4 salt materials
  change ground type.
- **The TER-HOLE twin check:** the converted GRW `TER-HOLE` differs from GRB's own `TER-HOLE` in
  exactly ClassID, TextureSet, the 5-byte field's first byte, the handle, the four TextureMap IDs,
  the tint RGB values and `Index` (102 vs 65). The GRW-sourced scale, tiling, three floats, `Hole` and
  ground all equal GRB's. This is weak validation (one pair, mostly defaults), but nothing
  unexpected differs.

**Still needed before this runs in game:**
- the TextureSets/TextureMaps themselves, converted with `grw2grb.py`'s texture rules, including
  the 5 cliff detail sets the bank lists;
- a decision on the 9 colliding ClassIDs (`grw_to_grb(class_id=…)` takes a new one);
- a check that GRW's texture IDs don't collide with GRB's resources;
- packaging into the Bolivia root cell next to its Terrain entity.

## Tool

[`tools/tbf_read.py`](../tools/tbf_read.py) (2026-10-10) has `info`, `node` (with a `--png`
contact sheet that decodes GRB's BC1/BC7) and `selftest`. Its codecs are `decode_heights` /
`encode_heights` and `rle_decode` / `rle_encode`, both byte-exact. `selftest --n 120` on both
installs: Wildlands 120/120 nodes, 120/120 heights and 840/840 rasters re-encode exactly, 120/120
trailer masks match. Breakpoint: the same with 480/480 rasters, and 120/120 node maxima match the
min/max table.

## Open items
1. The v14 image-core predictor and the layout of each image layer's `u8` block (see that
   section for what was ruled out). Probably only needed if `gr.wmap` turns out not to be enough.
2. Which GRW `00` rasters map onto GRB's two, and what the FE raster means. File statistics don't
   decide it (see the table); material names or an in-game A/B test would.
3. The trailer floats `a ≤ b`.
4. GRW height scale: confirm `×3000/2^20` against a placed entity's height in a known cell.
5. ~~Terrain material tables in both games~~: found and decoded, and a converter written (sections
   above). Still open: the tint records' meaning (GRW 4, GRB 6), the GRB-only parameters, the
   offset-27 handle, and whether FE really indexes the procedural-set bank.
6. GRB lin2's header fields and why it holds one chain of nodes.
7. In game: does GRB honour a second Terrain entity's prefix and range (`gr`, 3000.0)?
