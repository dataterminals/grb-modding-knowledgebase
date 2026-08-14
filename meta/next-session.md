# Next session

*Rewritten 2026-08-09. The previous version (2026-07-03) described only the cloth-rebind
investigation, which has been parked since 2026-07-09 while two sessions went somewhere else
entirely. Both lanes are now written down, so neither gets lost again.*

**Read [`project-goal.md`](project-goal.md) first** — Sami's north star, verbatim, and still the
reason this repo exists. Then the two 2026-08-09 entries in [`research-log.md`](research-log.md)
for the current state.

---

## Two lanes. Know which one you're in.

| Lane | State | What it is |
| --- | --- | --- |
| **1 — Community tutorial absorption** | idle since 2026-08-09 | Working the *Tier 1 Imports* `#mod-tutorials` forum into the KB, thread by thread |
| **2A — Cloth→mesh rebind** | **PARKED** since 2026-07-09 | Blocked on an in-game test that is staged but never run |
| **2B — Skeleton bone-physics (Reflex3)** | **⭐ LIVE — as of 2026-08-14** | Same goal, different mechanism. Now has a format, a corpus, and a vanilla flowing-coat exemplar |

Lane 1 is not a detour — it turns the only real primary documentation GRB modding has into
something durable, and it produced independent corroboration of the 64-bit ID model from a
direction (hex editing) that had nothing to do with ATK. But **lane 2 is the north star**, and
lane 1 must not be allowed to quietly become the whole project.

**2026-08-14 changed which sub-lane is live.** Chasing an unrelated community question about
ragdolls surfaced **Reflex3**, GRB's per-bone physics system: present in every skeleton, carrying
real data in 512 of them, fully typed in ATK's source, and already used by vanilla to drive a
**flowing trench coat** with bones instead of cloth. Because bones are re-bindable by
weight-painting and cloth is not, **2B is now the shortest path to Sami's goal**. See
[`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

---

## Lane 1 — keep working the forum

[`reference/community-tutorials.md`](../reference/community-tutorials.md) is the thread→page index
and the place to start. It records what's absorbed, what's known-but-not-absorbed, and the
five-step procedure for adding a thread. **Follow that procedure** — especially step 1 (fetch the
replies, not just the opening post; the corrections live there) and step 2 (read the attached
screenshots; several threads carry their key information only in images).

Three threads are absorbed. The forum has many more. The user intends to work through all of it.

### The one test worth doing before more reading

**Does renumbering a mod file to `1_-_` ever change in-game outcome?** There are now **two
independent field cases** where renumbering coincided with a behaviour change, and both are
confounded:

- The vest that showed UI-only until renumbered.
- The localization edits that compiled and repacked correctly but didn't appear, fixed by
  consolidating the XMLs into one container **renumbered to `1_-_`** — which bundles
  *consolidation* with *renumbering*, so it isolates neither.

The disk-collision mechanism explains both without any engine involvement: copying a mod file whose
exact `<N>_-_<Name>.<ext>` filename already exists in `Extracted\` silently replaces that entry.
The only plausible engine path is two entries sharing a real ID inside one forge, where write order
decides — but vanilla forges have zero duplicate IDs, and peer priority is still open.

**Test:** reproduce the vest case and use `data_inspect.py` to check for a filename collision
*before* renumbering. If there is one, the mystery is closed at the filesystem layer. To resolve
the localization case, separate the two variables — renumber without consolidating, and vice versa.

This matters beyond curiosity: mods ship advertised as *"renumbered to 1 to avoid replacing vanilla
files"*, and that claim is **wrong at the engine layer** — renaming protects the file on disk, but
only the embedded `ClassID` decides what the game replaces.

### Other open threads from 2026-08-09

- **Locate spncryn's BuildTable tutorial.** Referenced by SamiPuma as the thorough method for
  **cross-category** slot moves (scarf → face paint), where his quick copy-paste isn't safe. Would
  extend [`buildtable-xml.md`](../reference/buildtable-xml.md). Thread not yet found.
- **ID byte offset in DB resources.** spncryn says "bytes 1-8"; our
  [`resource-type-ids.md`](../reference/resource-type-ids.md) layout says a payload begins with a
  `FileHeader` byte, putting the ClassID at offset 1. Either these types write no header byte or
  the phrasing is loose. Needs a hex check against a real `.DBToolSetting`.
- **ATK 1.3.4 is in the wild**; this KB's format facts were decompiled from **1.3.1**. Confirm
  nothing relevant changed before treating 1.3.1 behaviour as current. *(Partly settled 2026-08-09:
  the build installed on this machine — `E:\Anvil Toolkit\` — **is 1.3.1**, so KB facts match the
  tool actually in use. A 1.3.4 build still hasn't been examined.)*
- **BuildTable unknowns:** the `Type` UInt32 slot/usage code (`0x1C0000`, `0x120000`); whether
  `ForceBuiltTableTOCOrder` is ever populated; resolve field-name hashes `x73B5D0A0` /
  `x67660D91`. Only **one** export has been seen (pants, ATK 1.2.10) — a second category (weapons
  via `dbcontainer`, or a solid-colour mod) would confirm which elements are universal.
- **Can the item-wheel icon be re-pointed** by the same hex technique? This closes the
  "looks like a duck, quacks like a lion" gap that cost the swap tutorial's requester days.

---

## Lane 2 — the cloth rebind (Sami's north star)

**The goal:** put an existing in-game garment's cloth physics onto a NEW mesh — a flowing coat
replaced with an outside-source poncho that keeps the coat's cloth physics. This is a **REBIND**
problem (bind vanilla `.cloth` to new geometry), **not** parameter tuning. Parameter tuning is a
side quest; don't let it become the objective again.

### STEP 1 — the prerequisite fork, still un-run

Can a modified cloth take effect *at all*? Everything in route (A) depends on the answer, and it
has never been validly tested.

> **You are on the desktop now — which is where this is staged.** A **complete** Bodark-pattern
> override sits in `Extracted\DataPC_patch_01.forge\` **and**
> `Extracted\DataPC_TGT_WorldMap_Bootstrap_Split_patch_01.forge\` (the gentle gravity-reversed kilt
> cloths `90001`/`90002`), with base `DataPC.forge` restored pristine. Earlier attempts patched
> only **one** of the two forges holding the cloth, which is the suspected reason they hung.

**Do:** repack **both** patch forges → launch → watch the kilt.

- **Loads + hem lifts** → a modified cloth CAN take effect → **route (A) is alive**; go do it.
- **Loads + no change** → mechanism works, gravity genuinely inert → try MaxDistance next
  (stable), else lean to (B).
- **Hangs even when complete** → a lone cloth override isn't tolerated → cloth-resource edits
  can't ship → **(A) is likely dead → pivot to (B).**

> ⚠️ Killing a hung GRB needs `taskkill /F /T`. Restore `DataPC_patch_01.forge` from its
> `.pre-coattest-backup` (or `D:\GRB_KnownGood_ForgeBackup_2026-07-02\`) to recover. Verify each
> patch `Extracted\` is in-sync with its live forge before repacking (both were, 2026-07-03).

### STEP 2 — the real work, via (A) and/or (B)

**(A) Cloth→mesh REBIND** (the render↔sim remap). The hard, long-standing problem — see
[`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md). The cloth is welded to the
coat's vertices; a poncho needs its binding recomputed. Blocked on cracking the wrap/binding
encoding **and** on STEP 1. Only pursue heavily if STEP 1 says modified cloths can load.

**(B) The `.skeleton` bone-physics path — ⭐ START HERE. As of 2026-08-14 this has a name, a
format, and a vanilla exemplar.** Sami's key lead: GRB's `.skeleton` secondary-motion **transfers
to new meshes via weight-paint**, and **ATK can read GRB skeletons** (unlike cloth). That system is
called **Reflex3**, and it is now characterized —
see [`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

What changed:

- **Every** GRB skeleton carries an inline `Reflex3SkeletonConstraints` (hash `2386539642`);
  **512 of 2,469** hold real per-bone constraint data.
- The GRB blob header is `magic 0x12341234` + `version 3012000`, identical across all 512 — and it
  does **not** match ATK's Mirage constants, which is exactly why ATK stores it as an opaque
  Base64 blob instead of parsing it.
- `Reflex3Physics` (constraint type `10`) is fully typed in ATK source: constrained bone, swing
  axis, slide limits, **`Gravity`**, gravity node, **`WindFactor`**, collision toggle. Decoding the
  GRB blob is a **port of readers ATK already has**, not a reverse from nothing.
- **`Tsec_Trench_AddonSkeleton` carries 43,494 B of it** — a vanilla flowing trench coat driven
  entirely by bones, on an **addon** skeleton. Also `TP_HunterScarf_A_Skeleton` (9,991 B), hair
  rigs, backpack straps, and `Player_Kilt_Addon` (394 B — the kilt has bone physics *as well as*
  its cloth).

**The layer above is solved too** (2026-08-14, second session). An **`EntityBuilder`** assigns
skeletons — nothing else does; confirmed by decompressing all 66,899 resources in `DataPC`/`extra`
+ patches and finding every reference. The record is:

```
u32 TypeHash(0x24AECB7C = Skeleton) | u16 0000 | u8 0x12 | 6x 00 | u64 ClassID | u32 Slot
```

validated 16/16 against the skeleton sweep. So **a rig assignment is a plain 64-bit ID** — the same
shape as the community's hex item swaps — and `EntityBuilder` is `FileActionType.Xml` with GRB in
`SupportedGames`, so ATK can round-trip it as XML instead.

⚠️ **But the trench rig is NPC-only.** `Tsec_Trench_AddonSkeleton` is referenced by
`TSec_MIS_Blake(184)`, `TSec_CIN_Blake(184)` and `MIS_Y2E4_Wassili_Kropotkine` — **never** by
`PLAYER_Template` or `TEAMMATE_Template`. The player-wearable precedents are `Player_Kilt_Addon`
and `TP_HunterScarf_A_Skeleton`, which *are* in `TEAMMATE_Template` (under a node named
`PLAYER_SkelAddons`).

**Do next, in order:**

1. **Get an ATK XML export of `PLAYER_Template`.** Cheapest possible check — it settles which
   `EntityBuilder` field the reference records live in, and gives an editable round-trip path. Use
   [`tools/entity_skeletons.py`](../tools/entity_skeletons.py) first to see the build sheet.
2. **The goal-shaped experiment:** add or re-point a skeleton record in the **player** template
   aiming at a physics-carrying add-on rig, copying the kilt/scarf entries as the pattern. First
   end-to-end test of route 2B.
3. ~~**Finish the constraint-blob decode.**~~ **DONE 2026-08-14.** The blob is readable —
   [`tools/reflex3.py`](../tools/reflex3.py) prints the driven bone, its parent, swing limits in
   degrees, gravity and damping; the walk accounts for every byte in 204 of 205 skeletons.
   ~~confirm the 8-byte header is a bone-name hash~~ **also DONE** — it is
   `u32 BoneID | u32 ParentBoneID`, both **CRC32 of the exact-case bone name**, resolving against
   each skeleton's real bone list at **≈99.7 %** vs a 0.000 % null control. What's left inside the
   blob: the tails of type 9 (Orientation, 1,402 records) and type 6 (HingeVector, 472 — 36 of them
   in the trench coat), and the meanings of `param[0..3]` / `param[5..8]`.
   - ~~**Cheap win available:** extract ATK's `hashes.hl` name table.~~ **DONE 2026-08-14** —
     [`tools/atk_hashes.py`](../tools/atk_hashes.py) pulls 276,087 names out of a local ATK install
     (Fast-LZMA2 text, one name per line), and `reflex3.py --names` uses it. ⚠️ It only covers ATK's
     Assassin's Creed lineage, so it resolves **4 %** of GRB's bone hashes — but those are the
     **attachment points**: the trench coat and the scarf hang off `Spine2`, the watch off
     `LeftForeArm`. GRB's own dangle-bone names are still bare numbers.
     - **Open:** find a GRB-specific bone-name source (an ATK GLB skeleton export, a modder's
       Blender rig, an animation-side resource). CRC32 is trivial to check once you have candidate
       strings.
4. Then: a new mesh weight-painted to a physics-carrying rig. That step **is** the project goal,
   reached without touching `.cloth` at all.

> **Reading is done; writing is not.** Nothing has been written back to a skeleton yet, and any
> skeleton edit inherits the forge-shadow and hang-on-load hazards from the cloth work.

⚠️ Skeletons are **forge-shadowed** exactly like cloths (`Player_Kilt_Addon` sits in both
`DataPC.forge` and `DataPC_TGT_WorldMap_Bootstrap_Split.forge`). Any override must patch **both**
families, and "does a modified skeleton even load?" is as untested as STEP 1 is for cloth.

---

## Parked leads (don't lose these)

Open threads that aren't captured above but stay relevant to the north star. Roughly ordered by
payoff.

**Directly on the rebind goal (route A):**

1. ~~**`§4395` + `§4658` are undecoded… plausibly the exact rebind lever.**~~ **CLOSED 2026-08-09 —
   negatively. Do not re-open.** Both decoded from ATK source + a 156-body corpus sweep: §4395 is a
   `bool[64]` **enable bitmap** (a gate, no binding data), §4658 is a **null-terminated string that
   is empty in every vanilla body**. Neither is the rebind lever. Full write-ups in
   [`cloth-section-types.md`](../reference/cloth-section-types.md).
1b. **⭐ NEW top candidate — the 22 sections ATK does not model.** The same sweep found GRB cloths
   use **86** section types while ATK's `MotionSectionFactory` handles **64**; the other **22** hit
   `UnknownSection`. Since this KB's section knowledge was transcribed *from ATK*, they have never
   been looked at. Best sub-target: the **4403–4410 block** — four `12-byte counter → variable
   buffer` pairs, once per body in all 156, with `size(4404)==2×size(4406)` (paired index+payload
   arrays). ⚠️ **Render-scale but NOT one-per-render-vertex** — Walker LOD0 has 1816 render verts
   vs 636 elements in `4404`, so the obvious reading is already disproven. No ATK reader exists;
   decode from bytes, starting with the 12-byte counters (presumably 3×`int32`).
2. **Vanilla rebind precedent — the cheapest route-A experiment.**
   `1687_-_TP_Top_Bodark_Trench_Cloth` carries `Sim_Tsec_IanBlake_Trench_LOD0` at the identical
   **186-vert / 305-tri** geometry as `30291_-_IanBlake_TrenchCoat_Cloth` — confirmed 2026-08-09.
   ⚠️ **Refinement:** the sim-mesh name suffixes differ (`0x1DE8F05F3C9` vs `0x15FE3444A17`), so
   it is a **copy, not a shared reference** — vanilla does *not* demonstrate one cloth serving two
   items. Bodark also declares `MeshMappingsCount=1` and ships LOD0 only, vs IanBlake's `3` with
   two LODs. Still the cheapest experiment: try a **repoint** (make a second item reference an
   existing cloth whose sim mesh matches) before attempting to re-encode a wrap.
3. **Wrap-collapse validation on the kilt.** Once STEP 1 proves an override loads, run
   `clothwrap.py --diagnostic collapse/twist` on the kilt via the same both-patch pattern. If the
   visible mesh visibly scrambles, the wrap **is** the render driver → the route-A encoder is worth
   building. This is the gate; it was never validly tested (ghillies were pinned/invalid, Walker
   isn't player-viewable).
4. **Decode the wrap weight encoding** (the 6×u16 per-record) + the record↔render-vertex
   correspondence — the remaining blocker for a reskin encoder (only after lead 3 is green).

**On the skeleton path (route B):**

5. **Golem Cape** — still the interesting path-B exemplar: it visibly flows but has **no
   `Cloth`/`SoftBody` resource** (07-02). ⚠️ The 2026-08-14 all-skeleton sweep found **no skeleton
   entry named `*Cape*`/`*Golem*` anywhere**, so the cape's rig is named something else. Find its
   actual skeleton (via its BuildTable / mesh), then check its Reflex3 blob with the method in
   [`skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md). *(ATK's
   `Skeleton`/`Reflex3` classes are now decompiled and written up — that half of the lead is done.)*
6. ~~**Ragdoll bone-collider list** in `TP_WalkerCoat_Cloth`'s editor data.~~ **CLOSED 2026-08-14.**
   Decoded: a 536-char semicolon-separated list of **13 garment-owned capsule colliders**, every one
   prefixed `TP_WalkerCoat_`, covering **upper body only** (Head, Neck, L/R Arm, ForeArm, Hand,
   LeftShoulder ×4 — no spine, pelvis or legs). It is the coat cloth's collision proxy set, named
   after the bones it follows. **Not** a death-ragdoll rig, and not a binding mechanism.

**Do not re-chase — the community ragdoll question (2026-08-14):**

Releptive asked in `#shit-talk` whether GRB deaths could ragdoll instantly the way hostage-guard
kills do. **Answer: not with today's data surface, and the reason is absence, not difficulty.**
GRB ships **no `LiteRagdoll` resource** (ATK's `SupportedGames` excludes GRB; zero entries anywhere),
and **no combat animations at all** — all 1,564 `Animation` resources are ambient NPC acting clips,
and sweeps of all 415,177 forge entry names return zero hits for `ragdoll`, `hitreact`, `flinch`,
`stagger`, `getup`. Death-anim selection and ragdoll blend-out live in an animation state machine
that is not a forge resource. Full detail in the 2026-08-14 research-log entry.

**Prerequisite / infrastructure:**

7. **Full shadow-surface map.** Re-run `forge_inspect.py` base-vs-base across ALL forges (incl. the
   WorldMap `_Split` bases the 06-30 ID study skipped) to learn whether the shadow extends beyond
   `Cloth` to meshes/definitions. Cheap; de-risks every future override.
8. **§4356 `ClothDefinition` flag↔section agreement** is an untested failure mode — a flag that
   disagrees with the sections present likely breaks load; load-bearing for any rebind that
   adds/removes sections.
9. **Reconcile the raw-block contradiction:** on 2026-07-01 raw-block `.data` staged into
   `DataPC.forge` and the game *booted*, yet 07-02 proved raw blocks hang. Either the 07-01 edit
   never loaded (shadowed) or raw tolerance is contextual — bears on trusting any "edit confirmed
   in forge" check.
10. **BuildTable side of binding:** which property/node a BuildTable uses to reference a cloth, and
    whether the render mesh must carry `IsGeneratedFromCloth` + a matching `ClothEditorDataClothID`.
    [`buildtable-xml.md`](../reference/buildtable-xml.md) now documents the file's anatomy, so this
    lead is cheaper than it was — **lane 1 fed lane 2 here.**

---

## Don't repeat

**On the cloth work:**

- Don't test parameter tuning as the goal.
- Don't conclude "params inert" without a shadow-free (confirmed-loaded) test. 44/56 cloths are
  duplicated across `DataPC.forge` **and** a WorldMap base forge — editing only the `DataPC` copy
  proves nothing.
- After any repack, **hash-verify the live patch forges actually changed.** ATK may silently drop
  never-before-seen IDs (`90001`/`90002` aren't in the original file table). If a forge's hash is
  unchanged, the override didn't land; fallback = overwrite the existing kilt entry IDs
  (`34800`/`34793`) instead of minting new ones.

**On the tutorial work:**

- Don't judge a practitioner's claim false on engine reasoning alone. The "renumber to 1" call was
  initially marked simply false; the engine reasoning was right but answered the wrong claim —
  SamiPuma meant filesystem overwrite in the unpacked working folder, not resource override.
  **Find out which layer someone is talking about before grading them.**
- Don't smooth over contradictions between practitioners. Where they disagree, or a fix worked
  without a known mechanism, that *is* the finding.
- Don't test a hex item swap by looking at it. A swap changes an item's **function but not its
  item-wheel icon** — test by *using* the item.
- Don't edit one localization container and assume you're done. English (US) is split across
  **seven**, items may appear in more than one, and a partial edit silently fails. And `&` must be
  `&amp;` — a raw ampersand corrupts the file.
