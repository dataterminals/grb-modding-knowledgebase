# Next session — first moves (GRB cloth)

*Written 2026-07-02 at the end of a long in-game session. Read the three **2026-07-02** entries in [`research-log.md`](research-log.md) for full context, retractions, and the tooling state.*

---

## ⚠️ THE BIG LEAD — do this first: we may have edited the WRONG gravity all day

Today we concluded *"GRB ignores cloth gravity"* after reversing **and** zeroing gravity on a loose Tactical Kilt with **zero** visible change. **But that edit went into the gravity field inside section `4357` (`ClothProperties`).** Spotted at session's end (from [`reference/cloth-section-types.md`](../reference/cloth-section-types.md)): there is **also a dedicated `ClothPropertiesGravity` section, type `4398`** — a 12-byte `Vector3` holding the **same** gravity value — and **we never touched it.** Verified present (with the same value as 4357) in `Cloth_HunterCoat`, `Cloth_FTP_Kilt`, and `Cloth_ArcturusWarrior_Ghillie_JacketBody2`.

The runtime very likely reads **4398**, making 4357's gravity a dead default/authoring copy. **So gravity is NOT confirmed dead — we tested the wrong copy.**

**STEP 1 (decisive):** On the **Tactical Kilt** (`Cloth_FTP_Kilt` *and* `Cloth_0X193A6210EB9` — do both, they cover the FTP/TP variants), reverse or zero the gravity in **section 4398** (12-byte payload = 3 floats at offsets **0 / 4 / 8**; leave 4357 alone). Run the proven pipeline (below), launch, wear the kilt.
- **Hem flips / goes limp** → 🎯 gravity **IS** a live lever, in section **4398** → retract today's "gravity ignored" headline; we finally have a working cloth edit.
- **4398 also does nothing** → gravity is genuinely global-only; move to the other levers.

## The generalization (why this matters for every param)

Section `4357` (`ClothProperties`) carries struct fields (gravity @ off 2, damping ≈ off 14, friction ≈ off 26), **but there are dedicated sibling sections that likely hold the live values**: `4398` Gravity, `4397` Wind, `4360` `ClothPropertiesConstraintsStiffness`, etc. (full map in `reference/cloth-section-types.md`). **Edit the dedicated sections, not the 4357 struct fields.** Our whole day's gravity work hit 4357 — probably why *everything* was inert. This likely also explains the ghillie/kilt nulls without needing "gravity is ignored."

## Then: the damping / stiffness levers

Once 4398 settles "is any dedicated section live," test **stiffness (`4360`)** and **damping** (find its dedicated section, or 4357 off ≈14 as a fallback) on the kilt — floppy-vs-stiff is unmissable. If a dedicated section drives the cloth → real modding levers exist → build a **"GRB Cloth Editor" `.exe`** (GUI + build workflow, same pattern as the inspectors).

## The proven pipeline (verified today)

1. **`Extracted\DataPC.forge\` must be byte-faithful to the LIVE forge.** It's a *persistent* working source (extract once, edit incrementally) — but `DataPC.forge` specifically had **drifted** from live (its Extracted was stale; live had unlock+clothing mods added by another path). Repacking a stale Extracted **reverts the user's mods**. Verify thoroughly (all entry sizes + byte-compare BuildTable/unlock records); if diverged, **re-extract that one forge once** to resync.
2. **Edit the target cloth `.data` COMPRESSED in place.** `tools/clothwrap.py` now writes Oodle-compressed loadable `.data` (raw/uncompressed crashes GRB at load — that was the day's core blocker). For a section-4398 edit, reuse the scratchpad approach: `motioncloth` to reach the sections → overwrite the 4398/4360 bytes → `clothwrap`'s compressed writer.
3. **ATK repack `DataPC.forge` → launch → observe.** Mods preserved.

## Subject + safety

- **Subject: the Tactical Kilt** — loose free-hanging hem, confirmed edit-reaches-it (edit read back live in the repacked forge, not patch-shadowed), player-equippable. (Ghillies are pinned; the "Golem/Field-Medic raid cape" is *skinned*, not cloth — don't retry those.)
- **Backups:** hash-verified known-good modded forges at **`D:\GRB_KnownGood_ForgeBackup_2026-07-02\`** — restore from there if anything breaks.
- Scratchpad pipeline scripts from today are session-temporary; rebuild from this spec + the `clothwrap` compressed writer.
