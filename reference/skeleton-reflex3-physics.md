# Reflex3 — GRB's skeleton bone-physics system

*Established 2026-08-14. This is the mechanism behind **route (B)** in
[`meta/next-session.md`](../meta/next-session.md): flowing/dangling geometry driven by
**bones**, not by a `.cloth`.*

> **Why this matters.** The project goal ([`meta/project-goal.md`](../meta/project-goal.md)) is
> putting an existing garment's physics onto a NEW mesh. The `.cloth` route is blocked because
> cloth is welded to one mesh's vertices. **Reflex3 is not** — it constrains *bones*, and a new
> mesh can be weight-painted to bones. This is the tractable route.

---

## What Reflex3 is

`Reflex3` is Anvil's **per-bone secondary-motion / constraint system** — swing, slide, look-at,
ball-joint, orientation and position constraints evaluated on skeleton bones. It is what makes
hair, ponytails, backpack straps, weapon slings, scarves and (crucially) the **Bodark trench
coat** move without any cloth simulation.

GRB skeleton resources whose names end in `_Reflex` (e.g. `Skeleton_Female_172_Reflex`,
`Regular_Male_Reflex_SklAdd`) are the physics layer for a character; the plain `_Body` skeleton
carries none.

---

## Verified facts

> **Verified (2026-08-14):** ATK v1.3.1 decompiled source (`ilspycmd -p`), plus a sweep of
> **all 2,469 Skeleton resources across all 27 forges** in the install, read index-only out of
> the `.forge` files and Oodle-decompressed. Nothing was written to the install.

### Every GRB skeleton carries a Reflex3 constraint slot

`Skeleton.Read()` (`AnvilToolkit.FileTypes.AnvilNext.Models.Skeleton`) — GRB is explicitly
handled:

```csharp
if ((uint)(version - 10) <= 1u || version == Game.GhostReconBreakpoint || version == Game.Mirage)
{
    Reflex3Constraints = new ObjectPtr(br, base.Version, 2386539642u);
}
```

and `Skeleton.SupportedGames` **includes `Game.GhostReconBreakpoint`**. ATK reads, writes and
XML-exports this field for GRB.

Empirically, **all 2,469 skeletons contain exactly one inline `Reflex3SkeletonConstraints`
object** (hash `2386539642`) — `ObjectPtr` tag 0/4 means the object is embedded, which is why no
forge entry is *typed* `Reflex3SkeletonConstraints`.

### 512 of 2,469 skeletons carry real constraint data

Immediately after the class hash comes an `int32` blob length
(`Reflex3SkeletonConstraints.Read()` = `BinaryData = br.ReadBytes(br.ReadInt32())`).

| Blob length | Meaning | Count |
| --- | --- | --- |
| **8 bytes** | header only → **no bone physics** | 1,957 |
| **> 8 bytes** | real per-bone constraints | **512** |

### The GRB blob header — a new constant

**All 512** non-empty blobs begin with the byte-identical 8-byte header:

```
34 12 34 12   a0 f5 2d 00
```

| Offset | Type | Value | Meaning |
| ---: | --- | --- | --- |
| `0x00` | `uint32` | `0x12341234` | magic |
| `0x04` | `uint32` | `3012000` (`0x002DF5A0`) | version |

> **This is why ATK cannot parse it.** ATK's `Reflex3SkeletonConstraint.Read()` validates
> `Reflex3SkeletonConstraintMagic = 19620929`, `Version = 2`, `ConstraintMagic = 5000004` — none
> of which appear anywhere in GRB's blobs. ATK's author gated the parser to `Game.Mirage`
> (`if (!ExportConstraints || base.Version != Game.Mirage) return;`), so **the GRB variant was
> never validated**. For GRB, ATK slurps the blob opaquely and round-trips it as Base64 in XML.

### Blob body — decoded

*Cracked 2026-08-14. Read it with [`tools/reflex3.py`](../tools/reflex3.py).*

```
blob   := u32 magic 0x12341234 | u32 version 3012000 | record*

record := u8  type
          [u8 0x01]                   type 9 only — one extra byte
          u32 BoneID                  CRC32 of the driven bone's name
          u32 ParentBoneID            CRC32 of its parent's name
          M(type) × 64-byte matrix    4×4 row-major affine: orthonormal 3×3,
                                      translation in column 3, bottom row (0,0,0,1).
                                      The first is Reflex3BoneInfo.InitTransform.
          tail                        type-specific
```

That head is exactly ATK's `Reflex3BoneInfo`:
`{ uint BoneID; uint ParentBoneID; Matrix4x4 InitTransform }`.

`H` and `M` are **constant per type**. Every blob's *first* record is unambiguous (it starts at
byte 8), giving 205 independent samples — and the vote was **unanimous for every type**:

| type | H | M | ATK's `Reflex3ConstraintTypeRegistry` | first-records |
| ---: | ---: | ---: | --- | ---: |
| 5 | 9 | 4 | — | 11 |
| 6 | 9 | 4 | **HingeVector** | 3 |
| 7 | 9 | 4 | **LookAt** | 4 |
| 9 | 10 | 4 | **Orientation** | 133 |
| 19 | 9 | 4 | — | 2 |
| 20 | 9 | 4 | — | 6 |
| **21** | **9** | **5** | — → **the physics record** | 38 |
| 23 | 5 | 1 | — | 4 |
| 24 | 9 | 4 | — | 4 |

> **Why this is convincing:** three of the nine type bytes — 6, 7 and 9 — land exactly on
> `HingeVector`, `LookAt` and `Orientation` in ATK's registry. That the byte is the constraint
> **type** is not a guess. The other six are types GRB uses that ATK never modelled — the same
> species of blind spot as the 22 unmodeled MotionCloth sections.

**Acid test:** walking every blob with this model consumes **204 of 205 exactly**, landing on the
final byte with nothing left over.

### Bone names are `CRC32(exact-case name)` — and the record head is two of them

> **Verified 2026-08-14.** ATK's `Bone.Name` is a `uint32`, i.e. a hash. GRB bakes that hash into
> its collider names — `TP_WalkerCoat_Ragdoll_LeftForeArm_**2310617728**` — so the names are their
> own Rosetta stone. **CRC32 matched 9 of 9** (`Head`, `Neck`, `LeftArm`, `LeftForeArm`, `LeftHand`,
> `LeftShoulder`, `RightArm`, `RightForeArm`, `RightHand`), while crc32-lower, crc32-upper,
> CRC-32/BZIP2 and no-final-xor each matched **0 of 9**.

Every `Skeleton` payload declares its bones before the constraint blob; `Bone.Name` sits **4 bytes
after** the `Bone` class hash (`2507411529`). Checking each record's `BoneID` against its own
skeleton's real bone list:

| type | records | BoneID resolves | ParentBoneID resolves |
| ---: | ---: | ---: | ---: |
| 5 | 185 | 96.2 % | 96.2 % |
| 6 | 472 | 99.8 % | 99.8 % |
| 7 | 265 | **100.0 %** | **100.0 %** |
| **9** | 1,402 | **100.0 %** | 99.9 % *(at header offset +1 — the extra `0x01` byte)* |
| 19 | 115 | **100.0 %** | 93.0 % |
| 20 | 48 | **100.0 %** | 70.8 % |
| 21 | 1,354 | **100.0 %** | 99.9 % |
| 24 | 19 | **100.0 %** | **100.0 %** |

**≈99.7 % overall**, against a **0.000 %** null control (random `uint32` values never hit the
1,274-hash bone-name set). Type 9 initially scored 0 % because its bone IDs sit one byte later; that
single extra `0x01` byte is what makes its header 10 rather than 9.

### Turning the hashes back into names

ATK ships the reverse lookup: `AnvilToolkit.Resources.hashes.hl`, an embedded
**Fast-LZMA2-compressed plain-text list**, one name per line. `HashedData.CheckStrings()`
decompresses it via `Libs/fast-lzma2.dll` and keys it by `CRC32` of each line plus its lower- and
upper-case forms. Extract it from your own install with
[`tools/atk_hashes.py`](../tools/atk_hashes.py):

```
1,294,015 B compressed  ->  6,610,946 B  =  276,087 names
```

> **The dictionary is ATK's data and is not redistributed here** — run the extractor against your
> own copy.

**Coverage is partial, and the shape of the gap is the useful part.** The list is built for ATK's
primary games (the Assassin's Creed line), so it resolves the **standard biped bones** GRB shares
with them and not GRB's bespoke dangle bones:

| | resolved |
| --- | --- |
| GRB skeleton-declared bone hashes | **51 / 1,274 (4 %)** |
| Reflex3 constraint bones (the dangle bones themselves) | 0 |

That sounds bleak until you look at *which* ones resolve — they are exactly the **attachment
points**:

| Rig | Constraint parent |
| --- | --- |
| `Tsec_Trench_AddonSkeleton` | **`Spine2`** |
| `TP_HunterScarf_A_Skeleton` (5 records) | **`Spine2`** |
| `Watch_Skeleton` | **`LeftForeArm`** |

A coat and a scarf hang off the spine; a watch hangs off the left forearm. Anatomically correct,
and an end-to-end check on the whole decode chain — forge → skeleton → constraint record → bone
hash → name. The unresolved hashes are the rig's *own* invented bones (coat panels, hair strands),
which only a GRB-specific name source would cover.

### GRB's own bone names — recovered from the hashes

ATK's dictionary covers the Assassin's Creed lineage, not GRB's bespoke rigs. Those names were
recovered separately and are shipped as
[`reference/grb-bone-names.tsv`](grb-bone-names.tsv) — **126 names, 43 of them physics bones.**

**Method, and its limits.** Two sources: *harvesting* literal strings (GRB.exe — 536 MB, ~892,000
strings — plus all 370,259 forge entry names and every string in a skeleton payload) and CRC32
matching them; then *generating* candidates from the naming grammar the harvest revealed.

> ⚠️ **Brute force against a 2,491-hash target set produces collisions.** A **null run** — the same
> generator pointed at 2,491 *random* hashes — scored **20 spurious hits per 18.7 M candidates**.
> Generated hits therefore mean nothing on their own, and **93 isolated ones were discarded.**

Every shipped name carries one of three independent kinds of evidence:

| Evidence | Count | What it means |
| --- | ---: | --- |
| `literal` | 70 | The name was **read verbatim** from GRB.exe, a forge entry name, or a skeleton payload. It was not guessed. |
| `family` | 51 | Part of a numbered run of ≥3 sharing a stem — `T_Zipper01`…`T_Zipper07`. For one stem we test ~24 variants at P≈1.4 × 10⁻⁵ each; a six-long run cannot be chance. |
| `context` | 16 | The name's distinctive token matches a skeleton that **actually uses that hash** — evidence independent of the hash itself. |

The `context` hits are the most satisfying:

| Name | Found in |
| --- | --- |
| `RFX_Watch`, `T_Watch` | `Watch_Skeleton` |
| `T_Scarf` | `TPri_CIN_Hawkins_Scarf` |
| `RFX_BackPack`, `T_BackPack` | backpack rigs |
| `DRN_UGV_Goliath-Rig-{FL,FR,BL,BR}` | `DRN_UGV_Goliath` |

**The naming grammar.** GRB bones fall into families, and the prefixes are the useful discovery:

| Prefix | Role | Examples |
| --- | --- | --- |
| **`RFX_`** | **Reflex — the physics bones themselves** | `RFX_LeftShoulderRoll`, `RFX_Watch`, `RFX_BackPack` |
| `T_` | targets / attachment points | `T_Strap01`…`06`, `T_Zipper01`…`07`, `T_Scarf`, `T_BackPack` |
| `L_` | link / no-roll helpers | `L_LeftArmNoRoll`, `L_NeckNoRoll` |
| `Prop_` | prop attach points | `Prop_LeftHand2`, `Prop_Head` |
| `Reflex_…_Sphere` | collision primitives | `Reflex_Spine1_Sphere` |
| (none) | standard biped | `Hips`, `Spine2`, `LeftForeArm`, `RightHandRing2` |

**Coverage is 126 / 2,491 (5 %)** — 43 of 649 physics bones. The bulk of each rig's own dangle
bones (coat panels, hair strands) are still bare numbers, and no source found so far contains them.

### It reads like authored animation data

`Tsec_Herzog_Hair_Skeleton`, first four records — each record's parent **is the previous record's
bone**, i.e. a hair strand:

| # | bone | ← parent | swing limits | damping |
| ---: | ---: | ---: | --- | ---: |
| 0 | 877775753 | 2908265011 | ±10° / 0…+25° | 0.4 |
| 1 | 1129773855 | **877775753** | ±15° / −1…+30° | 0.3 |
| 2 | 3711069884 | **1129773855** | ±20° / −3…+35° | 0.2 |
| 3 | 79239470 | **3711069884** | ±25° / −5…+40° | 0.1 |
| 4 | 3135163498 | 601333200 | ±10° / 0…+25° | 0.4 ← a new strand begins |

The limits **widen** down the chain while damping **falls** — stiff at the root, floppy at the tip.
That is how an animator authors hair, and it is strong evidence the decode is reading real fields
rather than coincidental bytes.

### The physics record (type 21) — field by field

> **Verified** against **all 1,354 type-21 records in the game.**

```
tail := u8 × 3                          flags
        { u8 gate ; if gate==1: f32 lo, f32 hi }*   angular limits, RADIANS
        f32 × 9                         parameter block
```

| Evidence | Result |
| --- | --- |
| `param[4]` | **9.8 in 1,344 / 1,354 records (99.3 %)** — this is `Reflex3Physics.Gravity`, whose ATK default is `9.8f` |
| `param[5]`, `param[6]` | `1.0` in 1,344 / 1,338 |
| `param[7]`, `param[8]` | `0.0` in 1,353 / 1,349 |
| `param[0]` | `0.2` in 1,096 (then 5.0, 0.8, 0.5, 0.4) — damping-shaped |
| `param[1]` | `0.0` in 1,231, else 25.0 / 20.0 / 100.0 — stiffness-shaped |
| `param[2]` | `0.0` in 1,306, else 1.0 / **0.95** / **0.98** — classic damping coefficients |
| gate count | **2 pairs in 1,262 records**, 1 pair in 72, 0 in 20 |
| limit values | exactly `−1.5708` (−π/2), `3.1416` (π), `−0.4363` (−25°), `0.6109` (35°); range `[−π, +π]`; **median \|limit\| = 15.00°** |

The limits are **unmistakably radians** — the constants are π and π/2 to four decimals, and the
median is a round 15°. 44 % of pairs are symmetric (`lo == −hi`).

> **Still inferred:** the meanings of `param[0..3]` and `param[5..8]` are shape-guesses from their
> value distributions, not confirmed — though `param[0]`/`param[3]` behave like damping in the hair
> chain above. Tails for types other than 21 and 23 are large and variable and remain undecoded;
> their record boundaries come from the forward-scan heuristic, which yields exact total consumption
> but is not independently verified per boundary. Type 23's header is only 5 bytes, so it holds one
> `uint32`, not a bone/parent pair.

### What it reads like

```
$ python reflex3.py Player_Kilt_Addon.data
  1 constraint record(s); 394/394 bytes accounted for
  by type: 21=1 (Physics (swing/gravity))
       #  swing limits (degrees)              gravity  damping/stiffness
       0  [  -15.0,   +15.0]  [   -5.0,    +5.0]    9.800  0.2, 0, 0, 0

$ python reflex3.py Tsec_Trench_AddonSkeleton.data
  48 constraint record(s); 43,494/43,494 bytes accounted for
  by type: 6=36 (HingeVector), 9=2 (Orientation), 21=10 (Physics (swing/gravity))
       0  [  -20.0,    +0.0]                    9.800  0.2, 0, 0, 0
       3  [   +0.0,   +20.0]                    9.800  0.2, 0, 0, 0
```

The kilt is one bone swinging ±15° and ±5°. The coat is **36 hinges plus 10 swinging bones**,
half limited −20°→0° and half 0°→+20° — panels hinging fore and aft.

---

## The constraint types (from ATK source — fully typed)

`Reflex3ConstraintTypeRegistry` maps a constraint's type id to its class:

| Type id | Class | What it does |
| ---: | --- | --- |
| `0` | `Reflex3Attachment` | attach a bone to a target |
| `1` | `Reflex3BallJoint` | ball-joint (also `Reflex3DoubleBallJoint`) |
| `3` | `Reflex3BoundingVolume` | collision volume / convex hull |
| `6` | `Reflex3HingeVector` | hinge |
| `7` | `Reflex3LookAt` | aim a bone at a target |
| `9` | `Reflex3Orientation` | orientation constraint |
| **`10`** | **`Reflex3Physics`** | **the jiggle/swing/slide solver — see below** |
| `11` | `Reflex3Position` | position constraint |

Ids `2`, `4`, `5`, `8` are **unmapped by ATK** — the same kind of blind spot as the 22 unmodeled
MotionCloth sections (see [`cloth-section-types.md`](cloth-section-types.md)).

> **⚠️ These ids are NOT the type byte you will find in a GRB blob.** (Noted 2026-09-01.) The table
> above is **ATK's registry**; the blob carries its **own** type byte, and the two spaces only
> partly coincide. Most importantly:
>
> | | ATK registry id | GRB blob type byte |
> | --- | ---: | ---: |
> | `Reflex3Physics` | **10** | **21** |
> | `Reflex3HingeVector` | 6 | 6 |
> | `Reflex3LookAt` | 7 | 7 |
> | `Reflex3Orientation` | 9 | 9 |
>
> Because 6/7/9 agree, it is easy to assume 10 will too — it does not. GRB blobs use type bytes
> `5, 6, 7, 9, 19, 20, 21, 23, 24`; **there is no type-10 record in any of the 205 blobs surveyed.**
> Byte 21 was identified as the physics record *empirically*, not by number: `param[4] == 9.8` in
> 1,344 of 1,354 records, matching `Reflex3Physics.Gravity`'s ATK default (2026-08-14, third entry).
> [`tools/reflex3.py`](../tools/reflex3.py) speaks the **blob** space (`PHYSICS_TYPE = 21`); prose
> quoting ATK's source speaks the **registry** space. Say which one you mean.

### `Reflex3Physics` — the tunable fields

Decompiled from `Reflex3Physics.ReadData(BinaryReader)`, in wire order:

| Field | Type | Note |
| --- | --- | --- |
| `Common` | `Reflex3ConstraintCommon` | |
| `ConstrainedObject` | `Reflex3BoneInfo` | **which bone this drives** |
| `ConstrainedObjectParentBoneHandle` | `uint32` | |
| `UseSlide`, `SlideX`, `SlideY`, `SlideZ` | `bool` ×4 | |
| `SlideMax`, `SlideMin` | `Vector4` ×2 | translation limits |
| `UseSwing` | `bool` (+3 pad) | |
| **`Gravity`** | `float` | default `9.8` |
| `UseGravityNode` | `bool` (+3 pad) | |
| `GravityNode` | `Reflex3BoneInfo` | gravity can follow a bone |
| `IsGravityLocal`, `UseCollisionInfo` | `bool` ×2 (+2 pad) | |
| `UNUSED_WindNoise` | `float` | |
| **`WindFactor`** | `float` | |
| `SlideInfoOptimized` | `Reflex3SlidePhysicsInfo` | |
| `SwingInfoOptimized` | `Reflex3SwingPhysicsInfo` | |
| `EvaluationVersion` | `uint32` | only if `ConstraintVersion > 1` |
| `SwingAxis` | `Vector4` | only if `ConstraintVersion > 2`; default `(1,0,0,0)` |

That is a complete jiggle-bone description: **which bone, swing axis, slide limits, gravity, wind,
collision toggle.**

---

## Where the physics actually lives (the corpus)

512 skeletons carry constraints. The garment-relevant ones:

| Skeleton | Blob | Why it matters |
| --- | ---: | --- |
| `Skeleton_Female_172_Reflex`, `Regular_Male_Reflex_SklAdd`, `Eclipse_Reflex_SklAdd`, … | 99–114 KB | the character-wide physics layer |
| `BP_TacTailor_RemOp_*`, `BP_wStraps_Hill_*`, `BP_Nomad_AMP24_*` | 48–62 KB | backpacks + swinging straps |
| **`Tsec_Trench_AddonSkeleton`** | **43,494 B** | **a trench COAT driven by bone physics — the route-B exemplar** |
| `Hair_R6_Ash_Skel`, `Tsec_Herzog_Hair_Skeleton`, `Tpri_Hair_Addon_Rosa` | 10–12 KB | hair jiggle |
| **`TP_HunterScarf_A_Skeleton`** | **9,991 B** | a wearable scarf |
| `TPri_CIN_Hawkins_Scarf` | 4,920 B | |
| `Male_Heavy_feedBelt` | 2,892 B | ammo belt |
| `NVG_Straps_addon_Sam`, `Tter_ponytail_layla` | 1,552–1,980 B | |
| **`Player_Kilt_Addon`** | **394 B** | the kilt has bone physics **as well as** a `.cloth` |
| `WI_ASR_AK47`, `WI_SKEL_AK47` | 386 B | weapon slings |

Full table: regenerate with the sweep described below.

> **`Tsec_Trench_AddonSkeleton` is the headline.** A flowing coat, on an **addon** skeleton,
> physics carried entirely in bones. That is precisely the shape of the thing the project wants to
> put on a new mesh — and unlike `.cloth`, bones are re-bindable by weight-painting.

---

## The layer above: how an `EntityBuilder` names a skeleton

*Answered 2026-08-14, empirically.* The physics is **not inherited** — it is embedded in the
skeleton resource itself. What gets assigned is the **skeleton**, and the thing that assigns it is
an **`EntityBuilder`**, not a standalone BuildTable.

### How it was found

Rather than guess, every resource in `DataPC.forge`, `DataPC_extra.forge` and both patches
(**66,899 resources**) was decompressed and searched for the raw little-endian `uint64` ClassID of
four skeletons. Anvil stores cross-resource references as bare 64-bit IDs, so whatever points at a
skeleton contains its ID verbatim. **37 references found, and 32 of 35 non-`Entity` hits are
`EntityBuilder`s** — no other resource type assigns a skeleton.

| Skeleton | Referenced by |
| --- | --- |
| `Regular_Male_Reflex_SklAdd` | `PLAYER_Template`, `TEAMMATE_Template`, and ~20 character builders |
| `Player_Kilt_Addon` | `TEAMMATE_Template` |
| `TP_HunterScarf_A_Skeleton` | `TEAMMATE_Template`, `MIS_Rosebud`, several NPCs |
| **`Tsec_Trench_AddonSkeleton`** | **`TSec_MIS_Blake(184)`, `TSec_CIN_Blake(184)`, `MIS_Y2E4_Wassili_Kropotkine`** — character builders only, **never** a player template |

### The reference record

> **Verified.** Hand-aligned on four samples, then validated by extracting **every**
> `Skeleton`-typed record from two EntityBuilders: **16 records, 16 IDs, 100 % resolving to real
> skeletons** in the independent 2,469-skeleton sweep. Zero false positives.

```
u32  TypeHash     0x24AECB7C  == CRC32("Skeleton")   (0xEC6AC357 = GraphicObject, etc.)
u16  0x0000
u8   0x12                                            record tag
6 x  0x00
u64  ClassID      the resource being referenced
u32  Slot         attachment slot index
```

**A skeleton assignment is a plain 64-bit ID at a fixed offset in a fixed-shape record.** That is
the same shape as the community's documented hex item swaps
([`buildtable-xml.md`](buildtable-xml.md)) — and it does not have to be done in hex:
`EntityBuilder.SupportedGames` **includes `Game.GhostReconBreakpoint`** and its
`FileActionType` is **`Xml`**, so ATK exports the whole builder to XML and re-imports it.

### What a build sheet actually looks like

Extracting all `Skeleton` records from two builders reads like a parts list — and shows exactly
where the physics enters:

**`TSec_MIS_Blake(184)`**

| Slot | Skeleton | Physics |
| ---: | --- | ---: |
| 4 | `Regular_Male_Body_Skl` | none — the plain rig |
| 1 | `Regular_Male_Reflex_SklAdd` | **107,350 B** |
| 4 | `Skeleton_IanBlake_Head` | none |
| 2816 | `Player_Props_Addon` | none |
| **5** | **`Tsec_Trench_AddonSkeleton`** | **43,494 B** — sits beside `Tsec_IanBlake_Trench_Mcloth_MISSION` |

**`PLAYER_Template`**

| Slot | Skeleton | Physics |
| ---: | --- | ---: |
| 4 | `Regular_Male_Body_Skl` | none |
| 1 | `Regular_Male_Reflex_SklAdd` | **107,350 B** |
| 12 | `BodyUp_Skeleton` | **10,443 B** |
| 11 | `Watch_Skeleton` | **5,556 B** |
| 1792 | `Tpri_Schultz_Beard_Addon` | **2,710 B** |
| 3328 | `Tpri_Schultz_gloves_addon` | **1,166 B** |
| 10 | `Hat_Skeleton` | none |
| 5 / 3 | `Skeleton_Schultz_Head`, `TPri_CIN_Hawkins_Head` | none |
| 4864 | `WeaponsAttachment_NoBackPack_Addon` | none |

A character is a **plain base rig plus a stack of add-on rigs**, each carrying its own physics.
Blake's coat is one entry in that stack.

### The full chain

```
EntityBuilder  (PLAYER_Template / TEAMMATE_Template / a named character)
   └── typed reference record  (Skeleton, <64-bit ClassID>, slot)
          └── add-on Skeleton resource
                 └── inline Reflex3SkeletonConstraints   <- the physics lives HERE
```

> ⚠️ **One caveat that shapes the plan.** `Tsec_Trench_AddonSkeleton` is referenced **only by
> character builders (Blake, Kropotkine)** — never by `PLAYER_Template` or `TEAMMATE_Template`. The
> flowing-coat rig is wired into specific NPCs, not into a wearable gear slot. The
> player-wearable precedents are `Player_Kilt_Addon` and `TP_HunterScarf_A_Skeleton`, which **are**
> in `TEAMMATE_Template`. So the goal-shaped experiment is: **add a skeleton record to the player
> template pointing at a physics-carrying add-on rig**, using the kilt/scarf entries as the
> template to copy.

---

## Related class hashes (new to this KB)

| Hash (dec) | Class | Present in GRB? |
| ---: | --- | --- |
| `2386539642` | **`Reflex3SkeletonConstraints`** | ✅ inline in every skeleton |
| `3558325132` | `ReflexSystem` | field read for GRB, but never inline in the 7 sampled skeletons |
| `2507411529` | `Bone` | ✅ |
| `2299544533` | `LiteRagdoll` | ❌ **never** — and `SupportedGames` excludes GRB |
| `2371068428` / `572675924` / `333476854` / `2408076648` | `LiteRagdollCapsule` / `Shape` / `CapsuleGroupFlags` / `ExternalCapsule` | ❌ never |
| `3371740159` / `547156082` / `119336528` | `SkeletonPoseGroup` / `SkeletonPose` / `SkeletonPoseBone` | ❌ not inline in sampled skeletons |
| `4226984470`, `2137463166`, `2236439251`, `1849557783`, `3730792035`, `3946334986`, `868651492`, `575748634`, `3465920383`, `4030027666` | `ReflexBallJoint`, `ReflexFastPoseHull`, `ReflexPoseSet`, `ReflexPackedPoseBone`, `ReflexBoneInfo_BallJoint`, `ReflexBoneInfo_Connector`, `ReflexBoneTarget`, `ReflexMeasurement`, `ReflexConnector`, `ReflexConnectorElement` | ❌ never (the older Reflex, not Reflex3) |

---

## How to reproduce the sweep

Read-only; touches nothing in the install.

1. Parse each `.forge` index for entries with `Extension == 615435132` (`Skeleton`) — the layout is
   in [`../docs/02-forge-file-format.md`](../docs/02-forge-file-format.md); `tools/forge_inspect.py`
   already implements it.
2. Read `Len` bytes at `Offset` — those bytes **are** the `.data` file.
3. Decompress the two `CompressedFileData` blocks with `tools/data_inspect.py`'s `read_cfd()`
   (needs the install's `oo2core_7_win64.dll`).
4. `find` the little-endian `uint32` `2386539642`; the `int32` at `+4` is the blob length; the blob
   starts at `+8`.

---

## Open questions

1. ~~**Finish the blob decode.**~~ **Done 2026-08-14** — see "Blob body — decoded" above. What
   remains inside it: the 8-byte header remainder (bone hash?), the meanings of `param[0..3]` /
   `param[5..8]`, and the tails of types 5, 6, 7, 9, 19, 20, 24.
2. **Is `Tsec_Trench_AddonSkeleton` re-targetable?** Can a new mesh be weight-painted to its bones
   and shipped, keeping the coat's motion? This is the project-goal experiment.
3. **Constraint type ids 2, 4, 5, 8** — unmapped by ATK; check whether GRB uses them.
4. **Does a modified skeleton load at all?** The cloth work's hard lesson — shadow copies across
   `DataPC.forge` **and** a WorldMap `_Split` base, and hang-on-load for edits GRB won't tolerate —
   applies here too. Skeletons are shadowed the same way (e.g. `Player_Kilt_Addon` appears in both
   `DataPC.forge` and `DataPC_TGT_WorldMap_Bootstrap_Split.forge`). **Override both.**

---

## What Reflex3 is *not*

It is **not** a death ragdoll. `Reflex3Physics` is a driven-bone solver (swing/slide about a rest
pose, with gravity and wind) — not a rigid-body ragdoll with joint limits and impulses. GRB ships
**no `LiteRagdoll` resource at all**, and no death/hit-reaction animations exist as forge
resources. See the 2026-08-14 research-log entry.
