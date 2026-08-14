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

### Blob body — partially decoded

> **Verified:** past the 8-byte header sits a **constant 9-byte record preamble**, then a run of
> `4×4` little-endian `float32` matrices. Two independent specimens:
>
> | Skeleton | preamble bytes at `0x08` |
> | --- | --- |
> | `Player_Kilt_Addon` (394 B) | `15 25 b5 9c b9 b9 1b 94 92` |
> | `TP_HunterScarf_A_Skeleton` (9,991 B) | `05 6f e3 82 aa 1f b7 69 7d` |
>
> The matrices are orthonormal with a `(0,0,0,1)` final row — i.e. **bone transforms**. In the
> kilt the first two matrices are byte-identical (plausibly a rest/current pair).

> **Inferred, not confirmed:** the 9 bytes read most naturally as `uint64` (high-entropy, bone- or
> object-name-hash shaped) + one tag/type byte. **Do not build on this until it is checked against
> a bone-name hash from the same skeleton.**

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

1. **Finish the blob decode.** Identify the 9-byte preamble (bone hash?), then the per-constraint
   record framing, then map it onto `Reflex3ConstraintTypeRegistry` so `Reflex3Physics` fields
   become readable. ATK has every reader already written — it is a **port**, not a reverse.
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
