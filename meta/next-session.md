# Next session — reoriented around Sami's actual goal

*Rewritten 2026-07-03. **Read [`project-goal.md`](project-goal.md) first** (Sami's north star, verbatim), then the 2026-07-03 entry in [`research-log.md`](research-log.md) for the full state.*

---

## The goal (don't lose sight of it again)

**Put an existing in-game garment's cloth physics onto a NEW mesh.** Concretely: Sami wants a flowing **coat** replaced with an outside-source **poncho** that keeps the coat's cloth physics. This is a **REBIND** problem (bind vanilla `.cloth` to new geometry) — **NOT** parameter tuning. Parameter tuning (gravity/stiffness/wind/MaxDistance) is a **side quest**; stop chasing it as the main objective.

## Where we actually are (2026-07-03)

- Every cloth **parameter** edit (gravity §4398, stiffness §4360, wind §4397, MaxDistance paint) on the Tactical Kilt showed **zero in-game effect** — but this is **confounded by a newly-found FORGE SHADOW**: 44/56 cloths (incl. the kilt) are duplicated across `DataPC.forge` **and** a WorldMap base forge (`DataPC_TGT_WorldMap_Bootstrap_Split.forge`), and we'd only edited the `DataPC` copy. So "params are inert" is **NOT established** — the nulls may be shadowing. (This also downgrades last session's "gravity inert" DEFINITIVE.)
- **Patch-override attempts HANG the load.** A patch override in `DataPC_patch_01` only (both a wild edit and a gentle stable one) hangs partway into the post-title load. A stable edit hanging ⇒ it's the **override mechanism**, likely an **incomplete override** (the base copy is in 2 forges; we patched only 1).

## STEP 1 (if continuing in-game) — the prerequisite fork: can a modified cloth take effect *at all*?

A **complete** Bodark-pattern override is **staged on the desktop** (may need re-staging on the laptop): the gentle gravity-reversed kilt cloths (`90001`/`90002`) are in **both** `Extracted\DataPC_patch_01.forge\` **and** `Extracted\DataPC_TGT_WorldMap_Bootstrap_Split_patch_01.forge\`, with base `DataPC.forge` restored pristine.

**Do:** repack **both** patch forges → launch → watch the kilt.
- **Loads + hem lifts up** → a modified cloth CAN take effect → the **rebind path (A) is alive**; go do it.
- **Loads + no change** → mechanism works, gravity genuinely inert → try MaxDistance next (stable), else lean to (B).
- **Hangs even complete** → a lone cloth override isn't tolerated → cloth-resource edits can't ship → **(A) is likely dead → pivot to (B).**

> ⚠️ Safety: killing a hung GRB needs `taskkill /F /T`. Restore `DataPC_patch_01.forge` from its `.pre-coattest-backup` (or `D:\GRB_KnownGood_ForgeBackup_2026-07-02\`) to recover. Verify each patch `Extracted\` is in-sync with its live forge before repacking (both were, 2026-07-03).

## STEP 2 — the real work: pursue Sami's goal via (A) and/or (B)

**(A) Cloth→mesh REBIND** (the render↔sim remap). The hard, long-standing problem — see [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) render↔sim sections. The cloth is welded to the coat's vertices; a poncho needs its binding recomputed. Blocked on: cracking the exact wrap/binding encoding **and** (per STEP 1) whether a rebuilt cloth can even take effect in-game. Only pursue heavily if STEP 1 says modified cloths *can* load.

**(B) The `.skeleton` bone-cloth path — likely the more practical route.** Sami's key lead: GRB's `.skeleton` secondary-motion (rigid hanging items like thermoses) **transfers to new meshes via weight-paint** and **ATK CAN read GRB skeletons** (unlike cloth). Investigate: can a *flowing* garment be approximated with a chain of skeleton jiggle-bones the poncho weight-paints to? This sidesteps the `.cloth` rebind entirely. **Start here** — it's in tractable, ATK-supported territory. First moves: find an in-game item that uses `.skeleton` secondary motion on loose/flowing geometry (not just rigid), decompile ATK's `Skeleton`/bone-physics classes, and characterize how the jiggle is authored + whether it can be weight-transferred to a new mesh.

## Don't repeat
- Don't test parameter tuning as the goal. Don't conclude "params inert" without a shadow-free (confirmed-loaded) test. Don't edit only the `DataPC.forge` cloth copy and assume it's what loads — the WorldMap base copy may shadow it.
