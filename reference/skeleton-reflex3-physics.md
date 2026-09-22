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
forge entry is *typed* `Reflex3SkeletonConstraints`. *(Those 2,469 are forge-entry skeletons; 60 of
the 285 that only occur nested carry none — see the census note below.)*

### 512 of 2,469 skeletons carry real constraint data

Immediately after the class hash comes an `int32` blob length
(`Reflex3SkeletonConstraints.Read()` = `BinaryData = br.ReadBytes(br.ReadInt32())`).

| Blob length | Meaning | Count |
| --- | --- | --- |
| **8 bytes** | header only → **no bone physics** | 1,957 |
| **> 8 bytes** | real per-bone constraints | **512** |

> ⚠️ **The 2,469 were forge entries, not all skeletons** *(2026-09-16, census of nested resources)*.
> The sweep picked skeletons by forge-entry `Extension`, which sees only a container's *first*
> resource. Walking every container finds **9,649 `Skeleton` resources**, 7,192 of them nested.
> **285 distinct skeletons never occur first**, so the sweep above could not see them:
>
> | Nested-only skeletons | Count |
> | --- | ---: |
> | Reflex3 blob > 8 B — `Addon_collar_midas` 15,234 B, `DRN_CIV-Farmer-Crane` 7,138 B, `Addon_Accessories_Midas` 780 B, `Addon_hair_midas` 394 B | **4** |
> | header-only (8 B) | 221 |
> | **no `Reflex3SkeletonConstraints` hash in the payload at all** — mostly `*_RTA` / `*RTAONLY` drone and boss rigs (`DRN_CERBERUS_*_RTA`, `DRN_BAAL_*_RTA`) in world cells and cinematic configs | **60** |
>
> So "every skeleton carries an inline Reflex3 object" holds for the 2,469, not for all GRB
> skeletons. *Inferred:* the 60 hold a null pointer; this was not checked field by field. Method: the
> 2026-09-16 (night) research-log entry.

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

*Cracked 2026-08-14; **rewritten 2026-09-20** after a self-delimiting parse of all 204 distinct
blobs in the install. Read it with [`tools/reflex3.py`](../tools/reflex3.py).*

```
blob     := u32 magic 0x12341234 | u32 version 3012000 | record*

record   := u8 type | head | body

head     := BoneInfo                       types 5 6 7 8 19 20 21 24
          | u8 count | BoneInfo            types 9 11   — count = constrained bones, 1…12
          | u32 v | 64-byte matrix         type 23      — v is 2 or 3; a 69-byte marker

BoneInfo := u32 BoneID                     CRC32 of the bone's name, or 0xFFFFFFFF
            u32 ParentBoneID               CRC32 of its parent's name (0xFFFFFFFF = none)
            [u8 len | name]                only when BoneID is 0xFFFFFFFF: the bone is named
            4 × 64-byte matrix             5 for the physics record (type 21)
```

Every matrix is a 4×4 row-major affine — orthonormal 3×3, translation in column 3, bottom row
`(0,0,0,1)` — except that the swing rest frame of seven physics records carries a scale.

**What changed since August.** The 2026-08-14 model was `u8 type | 8 header bytes | M matrices |
tail`, with type 9 carrying "one extra constant `0x01`", and its acid test — "the walk consumes 204
of 205 blobs exactly" — was vacuous: the walk found the next record by scanning, so the last record
always ran to the end of the blob whatever the boundaries in between were. Parsing each record from
its own fields instead gives:

| | 2026-08-14 | 2026-09-20 |
| --- | --- | --- |
| type-9 second byte | constant `0x01` | a **count**: 1 (790 records), 5 (476), 12 (114), 4, 2 — the number of constrained bones that follow, each with its own BoneInfo |
| a bone in a record | `BoneID \| ParentBoneID \| 1 matrix` | `BoneID \| ParentBoneID \| [name] \| 4 matrices` — 264 bytes |
| bones in a record | one | the constrained bone(s) **plus the targets**, each a full BoneInfo |
| record types | 5 6 7 9 19 20 21 23 24 | **also 8 and 11** — hidden inside what the scan called "tails": 218 type-11 records, one type 8 |
| strings | none | **bone names and pose names as plain text**: `Spine2`, `LeftShoulder`, `T_BackPack`, `T_SpineTrenchCoat`, `L_LeftArmNoRoll`; `Default`, `left`, `back`, `right`, `down`, `up` |
| boundaries | scan heuristic | physics, hinge and types 5, 19, 24 delimit themselves; the rest are scanned |

**By-name bones.** A `BoneID` of `0xFFFFFFFF` followed by a length-prefixed string is a bone the
add-on rig does not own — a body bone, referenced by name and resolved at runtime. `ParentBoneID`
still carries a hash: `LeftForeArm`'s is `LeftArm`, `LeftShoulder`'s and `T_BackPack`'s are
`Spine2` (all CRC32-confirmed). This is how a hair or backpack rig says where on the body it hangs.

**Result of the parse:** all **204 blobs read to their last byte** — 4,505 records — and each
record's `BoneID` resolves to a bone its own skeleton declares in 4,081 of 4,088: 100 % for every
type but 5 (168 of 174) and one hinge. Scanning is now confined to types 7, 8, 9, 11, 20 and 23,
and it is exact for whatever follows a self-delimiting record.

| type | records | delimits itself | what it is |
| ---: | ---: | --- | --- |
| **21** | **1,362** | yes: 1,353 land on the next type byte, the other nine on a type-8 or type-11 record | **the physics record** — [below](#the-physics-record-type-21--field-by-field) |
| 6 | 472 | yes, 470 | **hinge**: `u8 n \| n × { BoneInfo target ; f32 weight }` then `u8 u8 \| unit quaternion \| u8 \| u32`. Weights are percentages: 50 + 50, 30 + 70, 100 |
| 9 | 1,413 | scanned | **pose-driven orientation** (`Reflex3_RotationExpression`-shaped): `count` constrained bones, two target bones, `i32 k \| vec4 \| k × 87-byte entries`, then **named poses** (`Default`, `left`, `back`, `right`, `down`, `up`, `Pose_6`), each a vec4, a name and two matrices |
| 23 | 379 real | scanned | a 69-byte **marker**: `u32 2` (or 3) and an identity matrix, almost always right before a type-9 record; four weapon rigs open with one |
| 11 | 218 | scanned | `Position` in ATK's registry; a count byte like type 9 and six matrices on the constrained bone |
| 19 | 115 | yes | attachment-like: `u8 n \| n × { BoneInfo ; f32 weight (0.5) ; matrix }` then a matrix, `u8`, `u32`. Follows the physics record on every backpack |
| 7 | 266 | scanned | `LookAt`: one target, then an up-node BoneInfo, axes and a quaternion, as in ATK's Mirage class |
| 5 | 174 | yes, 167 | two weighted targets (50 + 50) and a 22-byte trailer; the character rigs |
| 24 | 19 | yes, 15 | a **ball-joint physics** record — the **scarf** (five) and the **NVG straps** use it instead of type 21: one target, one limited angle pair, three unlimited `±π` pairs, a quaternion, a matrix; 677 bytes |
| 20 | 48 | scanned | a bone pair and vectors; unread |
| 8 | 1 | — | `BodyUp_Skeleton` only; head like type 6 |

> **Verified:** the grammar above, the counts, and every field named in the physics and hinge rows.
> **Inferred:** what types 9, 19, 24 and 11 *do* — their shapes are read; the names are ATK's
> registry (`9` Orientation, `11` Position) or the exe's list. `GRB.exe` carries thirteen
> `Reflex3_*_Constraint` names, four of which ATK does not model: `RotationExpression`,
> `Double_BallJoint`, `Measurement`, `Engine`.

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

| # | bone | ← parent | swing limits | mass\* |
| ---: | ---: | ---: | --- | ---: |
| 0 | 877775753 | 2908265011 | ±10° / 0…+25° | 0.4 |
| 1 | 1129773855 | **877775753** | ±15° / −1…+30° | 0.3 |
| 2 | 3711069884 | **1129773855** | ±20° / −3…+35° | 0.2 |
| 3 | 79239470 | **3711069884** | ±25° / −5…+40° | 0.1 |
| 4 | 3135163498 | 601333200 | ±10° / 0…+25° | 0.4 ← a new strand begins |

The limits **widen** down the chain while mass **falls** (0.4 → 0.1; the 2026-08-14 entry read this
field as damping) — stiff and heavy at the root, light and loose at the tip.
That is how an animator authors hair, and it is strong evidence the decode is reading real fields
rather than coincidental bytes.

### The physics record (type 21) — field by field

> **Verified** against **all 1,362 type-21 records in the game** (2026-09-20). With this layout
> 1,353 records end exactly on the next record's type byte; the other nine end on a type-8 or
> type-11 record. The 2026-08-14 "three flag bytes then gated pairs" was the same bytes misread:
> the three "flags" are the first three of five gates.

```
head := u8 21 | u32 BoneID | u32 ParentBoneID | 5 × matrix
             m0 = m1 = the bone's LOCAL bind transform, from the skeleton's own Bone record
                       (1,314 of 1,362; the rest differ from it by a rotation only)
             m2      = the PARENT bone's transform in character space — see below
             m3 = m4 = the swing rest frame: == m0 in 1,194, a pure rotation away from it in 146,
                       and scaled in 7

body := 5 × { u8 gate ; if gate == 1: f32 min, f32 max }
             slots 1–3: slide X, Y, Z — translation limits in METRES (|v| ≤ 0.0025 in vanilla)
             slots 4–5: swing axis 1, swing axis 2 — angular limits in RADIANS
        f32 × 9
        [64-byte matrix]   in 5 of 1,362 (four knife/rifle rigs, one hair rig); nothing in the
                           record announces it — a reader has to test for it
```

| slot pattern | records | what |
| --- | ---: | --- |
| `- - - S S` | 1,272 | two swing axes — hair, straps, garments |
| `- - - - S` | 68 | one swing axis — the trench coat's ten, among others |
| `X Y - - -` | 15 | slide only — light-machine-gun parts |
| `X Y Z S -` | 5 | slide and one swing |

| # | value in vanilla | name | evidence |
| ---: | --- | --- | --- |
| 0 | `0.2` (1,118); `0.4 → 0.3 → 0.2 → 0.1` down a hair strand; **`5.0` on every backpack body** (47); `0.8` on gun parts | **mass** *(inferred)* | a whole backpack is 5, a zipper pull 0.2, a hair tip 0.1 — the shape of a mass, not of a damping term |
| 1 | `0` (1,239); **`25`** on backpacks (100); **`20`** on every slide record; `100` twice | **spring constant** *(inferred)* | ATK's `SpringConstant`; every record with slide on has 20 |
| 2 | `0` (1,314); `0.95` / `0.98` exactly when slide is on; `1.0` on 27 backpack records | **slide damping** *(inferred)* | ATK's `DampingConstant`; only non-zero with slide or spring |
| 3 | `0` (900); `1.0` (342, backpacks); `0.6` (54, hair strands); `0.8` ponytail; `0.95` / `0.98` with slide | *unresolved* | swing damping or centre of mass — both fit the distribution |
| 4 | **`9.8`** (1,352) | **gravity** | ATK's `Gravity` default `9.8f` |
| 5 | `1.0` (1,352) | gravity factor *(inferred)* | ATK's `GravityFactor` |
| 6 | `1.0` (1,348); **`0` on seven knife and rifle rigs** and one backpack | wind factor *(inferred)* | wind switched off on small hard items |
| 7, 8 | `0` | — | `1.0` once and five times; unknown |

The limits are radians: `−1.5708`, `3.1416` and `−0.4363` (−25°) occur verbatim, the median swing
limit is a round 20°, and slide limits never exceed 2.5 mm. 44 % of swing pairs are symmetric;
hair and the trench coat use one-sided pairs (`0 … +25°`, `−20° … 0`) as the only thing keeping a
bone out of the body — **no physics record carries a collision shape.**

**The character-space matrix is derivable.** `m2` is the parent bone's bind transform in a frame
with the ground at the origin and the character turned 90° from the body rig's axes:

```
m2 = W · G_body(attach bone) · G_addon(parent bone)

W  = [ 0  1  0  0 ]      a 90° turn about the vertical axis
     [-1  0  0  0 ]
     [ 0  0  1  h ]      h = 0.964 m for the regular male body — kilt, Casper hair, Rosa hair,
     [ 0  0  0  1 ]          the trench coat, the Hill backpack: every record, within 2 cm
```

`G_body` is the attach bone's global transform in `Regular_Male_Body_Skl` (`Hips` at the origin,
`Head` at z 0.708) and `G_addon` the parent's global transform in the add-on skeleton, relative to
its own root. Two hair rigs (Herzog, Layla) fit the same `W` with `h` 0.758 and 0.845 — compiled
against a different character. So an authored rig can compute `m2`; whether the runtime *reads* it
or recomputes it from the skeleton is untested.

### What it reads like

```
$ python reflex3.py Player_Kilt_Addon.data
  1 constraint record(s); 1 delimited exactly, 0 located by scan
  by type: 21=1 (Physics (swing/slide/gravity))
      #        bone  <- parent  swing 1     swing 2     slide  mass* spring* damp*   p3  grav  height
      0*   b99cb525   92941bb9  [-15,+15]   [-5,+5]     -        0.2       0     0    0   9.8    0.96

$ python reflex3.py Tsec_Herzog_Hair_Skeleton.data --raw
  28 constraint record(s); 28 delimited exactly, 0 located by scan
      0*   3451cb89   ad589a33  [-10,+10]   [+0,+25]    -        0.4       0     0  0.6   9.8    1.62
      1*+  4356fb1f   3451cb89  [-15,+15]   [-1,+30]    -        0.3       0     0  0.6   9.8    1.58
      2*+  dd326ebc   4356fb1f  [-20,+20]   [-3,+35]    -        0.2       0     0  0.6   9.8    1.54
      3*+  04b9192e   dd326ebc  [-25,+25]   [-5,+40]    -        0.1       0     0  0.6   9.8    1.49

$ python reflex3.py Tsec_Trench_AddonSkeleton.data --raw
  48 constraint record(s); 46 delimited exactly, 2 located by scan
  by type: 6=36 (HingeVector), 9=2 (Orientation (pose-driven)), 21=10 (Physics (swing/slide/gravity))
  body bones referenced by name: T_SpineTrenchCoat
```

The kilt is one bone at hip height swinging ±15° and ±5°. A hair strand is four links (`+` = the
parent is the previous record's bone): limits widening by 5° a link, mass falling from 0.4 to 0.1,
the fore-aft swing one-sided at the root. The `height` column is `m2`'s vertical translation — hair
at 1.5–1.6 m, kilt at 0.96, backpacks at 1.3–1.4 — which is what identified that matrix. The
recipes, rig by rig: [`reflex3-chain-templates.md`](reflex3-chain-templates.md).

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
| **`Tsec_Trench_AddonSkeleton`** | **43,494 B** | assigned beside the trench coat's **cloth**; the coat mesh is **not** weighted to its driven bones *(corrected 2026-09-16 — see below)* |
| `Hair_R6_Ash_Skel`, `Tsec_Herzog_Hair_Skeleton`, `Tpri_Hair_Addon_Rosa` | 10–12 KB | hair jiggle |
| **`TP_HunterScarf_A_Skeleton`** | **9,991 B** | a wearable scarf |
| `TPri_CIN_Hawkins_Scarf` | 4,920 B | |
| `Male_Heavy_feedBelt` | 2,892 B | ammo belt |
| `NVG_Straps_addon_Sam`, `Tter_ponytail_layla` | 1,552–1,980 B | |
| **`Player_Kilt_Addon`** | **394 B** | the kilt has bone physics **as well as** a `.cloth` |
| `WI_ASR_AK47`, `WI_SKEL_AK47` | 386 B | weapon slings |

Full table: regenerate with the sweep described below.

> ~~**`Tsec_Trench_AddonSkeleton` is the headline.** A flowing coat, on an **addon** skeleton,
> physics carried entirely in bones.~~
>
> ⚠️ **Corrected 2026-09-16 (evening).** The trench coat's build-table row assigns a **cloth** next
> to this rig, and no LOD of either trench coat mesh (Blake's, Kropotkine's) carries any vertex
> weight on a bone the rig's Reflex3 records drive. What those 48 constrained bones move is open.
> Where Reflex3 demonstrably moves geometry, meshes *are* weighted to the driven bones:
>
> | Mesh | Rig | Weight entries on driven bones |
> | --- | --- | ---: |
> | `FTP_Hair_PonytailBforGoogles_LOD0` | `FTP_Casper_Hair_Skeleton` | 1,137 |
> | `TP_Backpack_wStraps_Hill_LOD0` | `BP_Hill_MEDIUMVEST` | 1,885 |
> | `TP_Tacvest_Walker_LOD0` | `Vest_Generic_Addon` | 11,635 |
> | kilt meshes / trench coat meshes (all LODs) | `Player_Kilt_Addon` / `Tsec_Trench_AddonSkeleton` | **0** |
>
> So bone physics swings danglers — hair, straps, vest pieces — and every flowing garment checked is
> cloth. Bones are still re-bindable by weight-painting, which is why route B matters, but there is
> no vanilla bone-only flowing garment to copy. Method and evidence: the 2026-09-16 (evening)
> research-log entry.

---

## The layer above: how a build table assigns a skeleton

*First answered 2026-08-14; **rewritten 2026-09-16.** The 2026-08-14 version searched decompressed
forge entries for skeleton IDs and credited each hit to its container, named after the container's
first resource (an `EntityBuilder`), and to the nearest string. It also read the record from the
wrong end. Walked resource by resource with the fixed `data_inspect.walk()`, the picture below is
what holds. The ClassIDs were always right.*

The physics is **not inherited** — it is embedded in the skeleton resource itself. What gets
assigned is the **skeleton**, and the thing that assigns it is a **`BuildTable` row component**.

### The assignment record

> **Verified from source and from bytes.** ATK 1.3.1's `BuildRow.Read`, `DynamicProperty` and
> `PropertyRegistry` give the layout; ATK's own XML export of the tables confirms it field by field.
> Across `PLAYER_Template` and both `TEAMMATE_Template` copies, **3,966 of 3,966** `Skeleton` Handles
> resolve to real skeletons.

A `BuildTable` declares typed **columns** and fills them from **rows**:

```
BuildColumn component:  u32 (ATK writes 0x2CECF817)
                        DynamicProperty: Skeleton, Type 0x1C0000 (Reference), ID 0   <- an empty typed column

BuildRow component:     i32  Index        which column this component fills
                        u32  DataType     0x24AECB7C == CRC32("Skeleton")   (0xEC6AC357 = GraphicObject, …)
                        u32  Type         0x00120000 = Handle
                        u32  Unk00        0
                        u8   (ignored)    ATK discards it, writes 0
                        u64  ClassID      the skeleton assigned
```

In ATK's XML it is:

```xml
<DynamicProperty Index="10">
  <Value Name="DataType" Type="UInt32" HashName="Skeleton">615435132</Value>
  <Value Name="Type" Type="UInt32">1179648</Value>
  <Value Name="Unk00" Type="UInt32">0</Value>
  <Handle>
    <Value Name="Value" Type="UInt64" Path="DataPC\Player_Kilt_Addon\Player_Kilt_Addon.Skeleton">1889064665537</Value>
  </Handle>
</DynamicProperty>
```

**A skeleton assignment is a plain 64-bit ID in a fixed-shape record,** and `BuildTable` round-trips
through ATK as XML, so it does not have to be done in hex. Export one table from inside its container
with `python tools/atk_bridge.py <container.data> --xml out.xml --resource <TableName>`.

> ⚠️ **The 2026-08-14 `u32 Slot` does not exist.** It was read from the four bytes *after* the
> ClassID, which are the **next** component's `Index` — or, after a row's last component, the start
> of whatever follows. That is where the large "slots" (1792, 2816, 3328, 4864) came from:
> `PLAYER_SkelAddons`' `3328` is `00 0d 00 00`, the table's `u8 Shuffle` byte followed by the low
> bytes of its `RowSelector`'s local ID.

### Who assigns which rig

| Skeleton | Assigned by (resource, Index) |
| --- | --- |
| `Player_FakeGun_Addon`, `ENVInfluence_Addon`, `Player_Props_Addon`, `Regular_Male_Reflex_SklAdd`, `Player_Holster_NoSling_Addon` | **`PLAYER_SkelAddons`** (inside `TEAMMATE_Template.data`) — 1, 5, 2, 4, 3; shared by `PLAYER_Template` and `TEAMMATE_Template` |
| `Player_Kilt_Addon` | **`TP_PANT_Kilt`** — Index 10, beside its `GraphicObject` at 11 |
| `TP_HunterScarf_A_Skeleton` | eight mask/head tables: `TP_FullMask_Flycatcher`, `_Rosebud`, `_RaidSniper`, `_RaidMedic`, `TP_Mask_RaidIngineer`, `TP_FullMaskBodark_E`, `Head_Fyodor_Archinov_Icon`, `Head_Katya_Maksimov_Icon` |
| **`Tsec_Trench_AddonSkeleton`** | **`Tsec_IanBlake_Trench_Mcloth_MISSION`** (inside `TSec_MIS_Blake(184)`) and `MIS_Y2E4_Wassili_Kropotkine_Trench` — both Index 4. Never by a player template |
| `Delta_Holster_Addon` | `TP_PANT_Bodark_A`, `TP_VestLight_AliceChestRig` — Index 3. ⚠️ **Not vanilla** (found 2026-09-20): this rig exists only in the live `DataPC_Resources_patch_01.forge`, under the mod-minted ID `888830102028888`, shipped by the *Eva Modern Outfit* mod — a copy of `Player_Holster_NoSling_Addon` with its holster bone re-parented from `RightUpLeg` to `Hips`. The two tables that assign it are that mod's, not the game's |

**The rule that falls out: a garment's rig is assigned from the garment's own table.** The shared
`PLAYER_SkelAddons` carries only player-wide rigs. *Inferred:* Index 3 is a holster column —
vanilla assigns holster rigs at 3 from item tables, and the shared table's default holster is at 3.

### Which rigs actually MOVE something — the donor shortlist

> **Verified 2026-09-17** with [`tools/rig_census.py`](../tools/rig_census.py), joining every
> `Skeleton`-assigning `BuildTable` row in `TEAMMATE_Template` + `PLAYER_Template` to that rig's
> Reflex3 record-head bones and to the per-bone weights of the meshes in the same row. **148**
> physics-carrying rigs are assigned; **117 drive a mesh**, 22 drive none of the meshes in their own
> rows, and 9 have no mesh reachable from the row (*which is not evidence either way*). 694 rig↔mesh
> pairs; 0 partial Reflex3 parses.

**Assignment is not motion.** A build-table row only makes a rig *available*; whether anything moves
is decided by **weight painting**. Vanilla itself ships rows where the rig is assigned and the mesh
carries no weight on a single bone it drives:

| rig | mesh | weights on **driven** bones | on parents |
| --- | --- | ---: | ---: |
| `Addon_Collar_PunkJacket` | `TP_Top_Metal_PunkJacketB_D0_LOD0` | 5,376 | 498 |
| `Addon_Collar_PunkJacket` | `TP_Top_PunkJacketB_D7_LOD0` | **0** | 1,104 |
| `Addon_Collar_ArmyJacket` | `TP_Top_ArmyJacket_D7_LOD0` | **0** | 1,966 |
| `BodarkPlates_Addon` | `TP_Tacvest_Sniper_ForFleeingMan_LOD0` | 2,238 | 2,839 |
| `BodarkPlates_Addon` | `TP_Top_VKBO_heavyNPC_LOD0` | **0** | 1,407 |
| `Tsec_Trench_AddonSkeleton` | every LOD of both trench coats | **0** | 0 |
| `Player_Kilt_Addon` | all four meshes in the kilt's row | **0** | 0 |

Weight on a record's **parent** does not count: that is the chain's anchor, and a mesh hanging off it
stays put.

**The rigs worth copying,** highest measured weight on driven bones per rig:

| rig | physics | driven bones | proven on | weights on driven |
| --- | ---: | ---: | --- | ---: |
| `Vest_Generic_Addon` / `Female_Vests_generic_Addon` | 40,403 B | 9 | 197 meshes across **174 rows** | up to **41,944**, 0 on parents |
| `Nomad_Vest_511_PlateCarrier_Addon` | 41,699 B | 9 | `TP_NOMAD_LoadOut_LOD0` | 25,860, 0 on parents |
| `addon_collar_samFisher` | 7,540 B | 11 | `Tpri_Top_SamFisher_LOD0` | 8,786 |
| `Addon_Collar_PunkJacket` | 4,428 B | 5 | `TP_Top_Metal_PunkJacketB_D0_LOD0` | 5,376 |
| **`Addon_body_samFisher`** | 21,381 B | **22** | `Tpri_Top_SamFisher_LOD0` — a **torso garment** | 5,105, **0 on parents** |
| `ShoulderPads_Addon` | 7,387 B | 4 | `TP_Shoulder_OutcastC_B_LOD0` and 46 more | 3,627 |
| `BP_Fixit_AllHazardsPrime_*` | 55,851 B | 33 | `TP_Backpack_Fixit_LOD0` | 30,213 |
| `Hair_R6_Ash_Skel` | 12,113 B | 10 | `FTP_Hair_R6_Ash_LOD0` | 15,555 |

> **`Addon_body_samFisher` is the closest vanilla has to a soft outer garment on bones** — 22
> constrained bones painted into a torso mesh with nothing merely anchored. It is **not** a flowing
> coat: every flowing garment in GRB checked so far (both trench coats, the kilt, the Golem cape) is
> cloth. But it does retire the flat claim that Reflex3 only swings danglers.
>
> `Vest_Generic_Addon` is the best-trodden path rather than the most dramatic one: 9 driven bones,
> exercised from 174 rows across 197 meshes, 0 weight on parents anywhere.

### What a build sheet actually looks like

`python tools/entity_skeletons.py <container.data> --install <GRB folder>` lists every assignment
in a container with its holder, Index and physics:

**`TSec_MIS_Blake(184)`** — 7 resources

| Held by | Index | Skeleton | Physics |
| --- | ---: | --- | ---: |
| `TP_Blake_Skeleton` | 1 | `Regular_Male_Body_Skl` | none — the plain rig |
| `TP_Blake_Skeleton` | 2 | `Regular_Male_Reflex_SklAdd` | **107,350 B** |
| `TP_Blake_Skeleton` | 4 | `Player_Props_Addon` | none |
| `TSec_CIN_Blake_Head` | 2 | `Skeleton_IanBlake_Head` | none |
| **`Tsec_IanBlake_Trench_Mcloth_MISSION`** | **4** | **`Tsec_Trench_AddonSkeleton`** | **43,494 B** |

**`PLAYER_Template`** — 44 resources; all 11 assignments come from costume tables inside it

| Held by | Index | Skeleton | Physics |
| --- | ---: | --- | ---: |
| `TPri_Schultz_Skeleton` | 1 / 2 / 4 | `Regular_Male_Body_Skl` / `Regular_Male_Reflex_SklAdd` / `Player_Props_Addon` | none / **107,350 B** / none |
| `TPri_Schultz_UpperBody` | 9 / 10 / 11 / 12 | `Hat_Skeleton` / `Watch_Skeleton` / `BodyUp_Skeleton` / `WeaponsAttachment_NoBackPack_Addon` | none / **5,556 B** / **10,443 B** / none |
| `TPri_Schultz_Beard` | 2 | `Tpri_Schultz_Beard_Addon` | **2,710 B** |
| `TPri_Schultz_LowerBody` | 5 | `Tpri_Schultz_gloves_addon` | **1,166 B** |
| `TPri_Schultz_Head`, `TPri_CIN_Hawkins_Head_Costume` | 2 | `Skeleton_Schultz_Head`, `TPri_CIN_Hawkins_Head` | none |

A character is a **plain base rig plus a stack of add-on rigs**, each carrying its own physics.
Blake's coat rig is one entry in that stack — and it enters through the **coat's** table, beside the
coat's cloth (which, not the rig, is what the coat mesh follows; see the correction above).

### The full chain

```
item / character BuildTable  (TP_PANT_Kilt, Tsec_IanBlake_Trench_Mcloth_MISSION, PLAYER_SkelAddons, …)
   └── BuildRow component  (Index, Skeleton Handle -> 64-bit ClassID)
          └── add-on Skeleton resource
                 └── inline Reflex3SkeletonConstraints   <- the physics lives HERE
```

> **What this means for the plan.** `Tsec_Trench_AddonSkeleton` is assigned only by coat tables worn
> by NPCs (Blake, Kropotkine), never by a player template — but it is assigned *from a coat's
> table*, which is exactly the shape a player garment's table can copy. The goal-shaped experiment
> is therefore: **add a `Skeleton` Handle row component to a wearable garment's own BuildTable,
> pointing at a physics-carrying add-on rig**, with `TP_PANT_Kilt` and
> `Tsec_IanBlake_Trench_Mcloth_MISSION` as patterns. Two installed mods (Bison Belt, Tactical Human
> Set) already assign rigid holster rigs per item this way; see the 2026-09-16 research-log entry.
>
> ⚠️ **But choose the rig for what it moves** *(2026-09-16, evening)*. Those two patterns assign a
> rig next to a **cloth**, and neither garment's mesh is weighted to the bones its rig drives. A
> mesh follows a rig only through weights on the driven bones — true of hair, backpack straps and
> vest rigs (table at the top of this section), not of the trench coat or the kilt.

---

## Related class hashes (new to this KB)

| Hash (dec) | Class | Present in GRB? |
| ---: | --- | --- |
| `2386539642` | **`Reflex3SkeletonConstraints`** | ✅ inline in every forge-entry skeleton (all 2,469); absent from 60 of the 285 skeletons that only occur nested *(2026-09-16)* |
| `3558325132` | `ReflexSystem` | field read for GRB, but never inline in the 7 sampled skeletons |
| `2507411529` | `Bone` | ✅ |
| `2299544533` | `LiteRagdoll` | ✅ **637 nested resources, 88 distinct, all vanilla, never a container's first resource** — hence the old sweep's zero *(census 2026-09-16, night)*. A list of bone-attached capsules. Families: per-archetype `DamageTriggerRagdoll_*` on human entities; garment collider sets referenced by `Cloth` resources (e.g. `TP_WalkerCoat_Ragdoll`, 3,573 B, whose 13 upper-body capsules are the coat cloth's collider list); animals; drones and robots; raid-boss `*_ColContainer*`; a one-capsule set each for player and teammate. ATK's `SupportedGames` excludes GRB and its capsule layouts do not fit; the GRB layout is in the research-log entry |
| `333476854` | `LiteRagdollCapsuleGroupFlags` | ✅ embedded in every GRB capsule (`u64 localID`, hash, 16 × bool); never a resource |
| `2371068428` / `572675924` / `2408076648` | `LiteRagdollCapsule` / `LiteRagdollShape` / `LiteRagdollExternalCapsule` | ❌ **not used** — GRB capsules use four other classes, names unknown: `286154434` (`0x110E5EC2`), `3736378044` (`0xDEB49ABC`), `3405269372` (`0xCAF8497C`) — *inferred* sphere / capsule / box from 1 / 2 / 3 size floats — and `716768756` (`0x2AB905F4`), which points at a `MeshShape` / `ConvexVerticesShape` / `BoxShape` / `CylinderShape` resource by ClassID |
| `1273385935` | `RagdollSkeleton` *(CRC32 match in ATK's name dictionary; no ATK class)* | ✅ one: **`GR_MaleAverage`**, 6,070 B, nested in `MIS_Y2E4_Katya_Maksimov`. Referenced by 51 human `Entity` resources (25 names), `CHR_PLAYER_TGT` and `CHR_TEAMMATE_TGT` included. Vanilla |
| `1401269008` / `854659681` / `4236257670` / `2032007014` | `RagdollBoneData` / `RagdollConstraintData` / `RagdollMotorParameters` / `RagdollBoneDriveParameters` *(dictionary matches)* | ✅ embedded in `GR_MaleAverage`: 19 / 18 / 4 / 1, over 19 standard biped bones. Fields undecoded |
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

> ⚠️ **Step 1 finds only skeletons that come first in their container** *(2026-09-16)*. To include the
> 285 distinct skeletons that only occur nested, read **every** entry, `walk()` its files block, and
> keep the resources with `type_id == 615435132`. Then search each resource's payload, not the whole
> files block.

---

## Open questions

> **2026-09-20:** the physics record is fully laid out — five limit slots, nine parameters, five
> matrices with the third derivable — the hinge grammar is read, and the blob's record set is
> 5 6 7 8 9 11 19 20 21 23 24. Still open: the meaning of `p3` and of parameters 7–8; what the
> pose-driven type-9 body's 87-byte entries encode; whether the runtime reads or recomputes the
> baked matrices; whether a generated blob loads at all.
>
> **2026-09-20 (second):** modified skeletons carrying *unchanged* blobs are proven to load by the
> install's own mods — 124 backpack rigs overridden by vanilla ID with moved bones
> ([`install-edit-classes.md`](install-edit-classes.md)). One of them, `WI_ASR_AK47` from *AKM_KYPK*,
> moves the very bone its physics record drives by 3 cm while the blob's baked matrices stay
> vanilla, and the game runs. What is untested is a blob the game did not compile.
>
> **Writer (2026-09-20, third):** [`tools/reflex3_write.py`](../tools/reflex3_write.py) re-emits all
> 204 blobs byte-exact, edits physics fields, generates physics-only blobs from a spec, and splices
> them into a skeleton container that re-reads identically. Regenerating the kilt and the Casper
> hair rig from their own decoded fields reproduces every matrix to the float — the matrix rules
> above are complete for those rigs. Nothing generated has been loaded in game.

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
pose, with gravity and wind) — not a rigid-body ragdoll with joint limits and impulses.

> ⚠️ **Corrected 2026-09-16, and settled by a census of nested resources the same night.** This
> section used to add that GRB ships no `LiteRagdoll` resource and no death/hit-reaction animations.
> **Both are wrong.** Every container in every forge was walked:
>
> - **637 `LiteRagdoll`s, 88 distinct, all vanilla.** They are bone-attached capsule sets, and their
>   format holds no joints (*inferred:* collision and hit volumes). Per-archetype `DamageTriggerRagdoll_*` sets (20–28 capsules
>   over the whole body) hang off the human `Entity`s. The Walker coat cloth's
>   `TP_WalkerCoat_Ragdoll_*` collider list above names 13 of the 23 capsules of
>   `TP_WalkerCoat_Ragdoll`, which the cloth references by ClassID.
> - **A rigid-body ragdoll candidate, separate from Reflex3:** the `RagdollSkeleton`
>   **`GR_MaleAverage`** — 19 `RagdollBoneData`, 18 `RagdollConstraintData`, 4
>   `RagdollMotorParameters` and 1 `RagdollBoneDriveParameters` over the standard biped bones. The
>   human `Entity`s reference it, `CHR_PLAYER_TGT` included. *Inferred:* a powered ragdoll. Its
>   fields are undecoded.
> - **A nested death and hit-reaction bank:** 188 directional generic-soldier deaths
>   (`mil_gen_m_ale_ros_std_V0_N_death_regular_chest_front_01`, …), 172 zonal hit reactions and one
>   get-up clip.
>
> **What decides between a canned death and the ragdoll is not located.** See the 2026-09-16
> (night) research-log entry.
