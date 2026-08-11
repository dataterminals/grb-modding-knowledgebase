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
| **1 — Community tutorial absorption** | **LIVE** — the last two sessions | Working the *Tier 1 Imports* `#mod-tutorials` forum into the KB, thread by thread |
| **2 — Cloth→mesh rebind** | **PARKED** since 2026-07-09 | Sami's actual goal. Blocked on an in-game test that is staged but never run |

Lane 1 is not a detour. It is turning the only real primary documentation GRB modding has into
something durable, and it has already produced independent corroboration of the 64-bit ID model
from a direction (hex editing) that had nothing to do with ATK. But **lane 2 is the north star**,
and lane 1 must not be allowed to quietly become the whole project.

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

**(B) The `.skeleton` bone-cloth path — likely the more practical route.** Sami's key lead: GRB's
`.skeleton` secondary-motion (rigid hanging items like thermoses) **transfers to new meshes via
weight-paint**, and **ATK can read GRB skeletons** (unlike cloth). Can a *flowing* garment be
approximated with a chain of jiggle-bones the poncho weight-paints to? This sidesteps the `.cloth`
rebind entirely. **Start here** — it's in tractable, ATK-supported territory.

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

5. **Golem Cape is the ready path-B exemplar.** It visibly flows but has **no `Cloth`/`SoftBody`
   resource** (07-02) → it's skeleton secondary-motion on flowing geometry. Decompile ATK's
   `Skeleton`/bone-physics classes against it.
6. **Ragdoll bone-collider list** in `TP_WalkerCoat_Cloth`'s editor data (`Ragdoll_Head…;LeftArm…`
   string, flagged 06-30, never decoded) — names the skeleton bones the cloth collides against;
   relevant to binding a cloth to a character in either route.

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
