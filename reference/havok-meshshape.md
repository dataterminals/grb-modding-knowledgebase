# Havok MeshShape blobs: Wildlands (2016.1) vs Breakpoint (2018.2)

An Anvil `MeshShape` resource is a collision mesh. Its triangles live in the resource itself (`Vertices`,
`Indices`, per-triangle materials; the full layout is in [`../meta/notes-entities.md`](../meta/notes-entities.md#physics-shapes-and-collision-materials)).
Its `PhysicsSDKDataPack.SerializedRawData` is a **Havok binary tagfile** that holds only the
bounding-volume tree over those triangles. This page describes that blob in both games and how
[`../tools/havok_tag.py`](../tools/havok_tag.py) converts one to the other.

> **Verified (2026-10-10):** everything below was measured on random samples of `_RT` entries from
> both installs (60 and then 300 per game), plus the Ghost Room twin `TPL_Ground_64m`, which exists
> in both games. Nothing here has been tested in game yet.

## Tagfile containers

Each section has a header: a big-endian `u32` holding `flag << 30 | size` (the size includes the
8-byte header), then a 4-character tag. Flag `1` marks a leaf section and `0` a container.

```text
GRW  TAG0 { SDKV "20160100", DATA, TYPE { TPTR TSTR TNAM FSTR TBOD THSH TPAD }, INDX { ITEM PTCH } }
GRB  TAG0 { SDKV "20180200", DATA, TCRF,                                       INDX { ITEM PTCH } }
```

- **GRW's tagfiles describe their own types.** Each one carries the full Havok reflection data for
  the classes it uses (57 types for one MeshShape).
- **GRB's tagfiles carry no types.** `TCRF` names a type compendium instead: the 8-byte ID
  `1bb87a285a374916` plus 16 zero bytes, the same on every sample. GRB's types are referred to by
  compendium index.
- The compendium itself was not found. It is not a `TCM0` section in `GRB.exe`, where the `TCM0` and
  `TCID` hits are only the tagfile reader's string constants. No forge entry has a name that looks
  like a compendium either.

## Items

Both games write the same object graph: four items, the first one null.

| Item | Class (GRW name) | GRB compendium type | Count | Offset in DATA |
| --- | --- | --- | --- | --- |
| 1 | `hknpExternMeshShapeData` | 80 | 1 | 0 (128 bytes) |
| 2 | `hkcdStaticTree::Codec3Axis6` | 44 | N tree nodes, 6 bytes each | 128 |
| 3 | `hkcdSimdTree::Node` | 52 | 2 | 128 + 6N, rounded up to 16 |

`ITEM` entries are `u32 (flags << 24 | type)`, `u32 offset`, `u32 count`. The root has flags `0x10`
and the arrays `0x20`. `PTCH` lists pointer fix-ups as `u32 type`, `u32 count`, then `count`
offsets.

**The SIMD tree is always empty.** All 2 nodes, in every sample from both games, hold the same
sentinel. The AABB lanes are `0x7F7FFFEE` / `0xFF7FFFEE` (just under ±FLT_MAX) and the data is
zero. So the real content is only the static tree's domain and its nodes.

One GRB sample (`ENV-ANX-RAID-Arena_SawSmall_A3_Ext_RT`) has no tree at all: an empty domain and 3
items. `havok_tag.convert` refuses that shape rather than guessing.

## What changed between the SDKs

| | GRW 2016.1 | GRB 2018.2 |
| --- | --- | --- |
| root `aabbTree` | @32: nodes array (item 2), domain `hkAabb` @48 | unchanged |
| root `simdTree` | @80: vtable (8 bytes), nodes array @88 | @80: nodes array, then `u8 = 1` @96 on every sample |
| `hkcdSimdTree::Node` | 112 bytes: `hkcdFourAabb` (96) + `u32[4]` | 128 bytes: 16 more bytes, zero on every sample |
| PTCH | arrays @32, @88 | arrays @32, @80 |
| DATA end | after the last SIMD node | after the last SIMD node |

> **Inferred:** the GRB byte at root+96 is probably `hkcdSimdTree::m_isCompact`. The 2018 class lost
> its vtable, and that field name fits its size. No compendium was available to confirm it.

The Ghost Room twin is the exception on DATA length: both its copies carry 8 extra trailing bytes.
None of the 600 sampled `_RT` blobs do.

## The tree codec is unchanged

A `Codec3Axis6` node is `u8 xyz[3]`, `u8 hiData`, `u16 loData`.

- **Bounds.** For each axis, the high nibble `h` and the low nibble `l` shrink the parent box:
  `min = parent.min + h² · extent / 226` and `max = parent.max − l² · extent / 226`.
- **Internal nodes.** `hiData` bit 7 set marks an internal node. Then
  `(hiData & 0x7F) << 16 | loData` is the number of leaves in its left subtree. The left child is the
  next node, and the right child is `this + 2 × that`.
- **Leaves.** For a leaf, the same value is its triangle index. Bigger meshes have fewer leaves than
  triangles in both games, probably because quads are paired.

> **Verified:** under this one rule, every leaf box holds its triangle in 300 of 300 GRW and 299 of
> 299 GRB samples. On the twin, the boxes are tight, with about 0.3 m of slack per side in both
> games.

Ubisoft rebuilt the trees for GRB. The twin's two trees differ node for node, yet both are valid
over the same 32 triangles. A converted blob is therefore GRB's format wrapped around GRW's tree,
not GRB's exact bytes.

## Conversion

`havok_tag.convert(grw_blob)` does the following:
1. Checks that the blob is 2016.1 and that its root is `hknpExternMeshShapeData` with an empty SIMD
   tree.
2. Takes the domain and the tree nodes.
3. Writes a 2018.2 `TCRF` tagfile around them.

> **Verified:** `grb_blob()` re-wraps GRB's own trees byte-identically in 299 of 300 samples (the
> 300th is the tree-less shape). Every converted GRW blob parses back.

[`../tools/grw_cell.py`](../tools/grw_cell.py) `--collision` uses this to ship a transplanted cell's
MeshShapes. Each one becomes its own entry, the way GRB stores 9,409 `_RT` entries.

## Collision materials: GRB kept GRW's library

The GRB ClassID census (every ID in every entry, inner resources included) shows that GRB has GRW's
GRN collision materials **under the same IDs**. GRB embeds copies next to the shapes that use them:

| Material | ID | GRB entries holding it |
| --- | --- | --- |
| `GRN_Wood_Solid` | `0x11f1a6a63a` | 13,521 |
| `GRN_Concrete` | `0x11f1a6a5ff` | 10,020 |
| `GRN_Wood_Weak` | `0x1b133a5165` | 4,121 |
| `GRN_Metal_Fence` | `0x152393009a` | 2,867 |
| `GRN_Rock` | `0x11f1a6a643` | 2,069 (with `Physics_GRN_Rock` `0x2bf3c9c4f7`, 2,069) |
| `GRN_Dirt` | `0x11f1a6a5ad` | 823 |
| `GRN_Metal_Pipe` | `0x1523930099` | 2 |
| unnamed hard surface | `0x1523930094` | 4, in `DBContainerEntry_0X104634F921` (global) |

GRB `_RT` entries come in two styles:
- **Embedded:** `[MeshShape, CollisionMaterial, PhysicsCollisionMaterial]`. In 40 samples, 22 of 50
  material references were embedded like this.
- **Referenced:** the shape points at a material in the global DB container instead. Both games'
  `_RT` entries reference `0x1523930094` that way.

Every `_RT` entry has the empty 145 record `00000000`. A GRB cell's own 145 record lists each `_RT`
entry its bodies use with tail `01 00 00`; Cell45147 lists all 16 it references.

The GRW `TPL_Default` (`0x738d22e44`) is not in GRB, which uses `0x103976b93b` instead.
