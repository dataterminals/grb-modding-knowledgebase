# 06 — How GRB reassembles forges into one index at load

A question that shapes everything about modding GRB: **how does the game turn ~25 separate `.forge` files (plus your patch forges) into one coherent set of game data?** This doc lays out the working model. Parts are verified from the on-disk layout; parts are inferred from how the Anvil engine family is known to work and from the fact that the mod mechanism succeeds. Inferences are flagged.

## The working model

At startup (and during streaming) the engine **mounts every forge it's told to load and builds a single logical index keyed by 64-bit file ID.** When the same file ID exists in more than one mounted forge, a **load-order / priority rule** decides which wins — and **patch forges win over base forges.** The result is one virtual namespace of resources; the game and resources reference each other by ID and the engine resolves each ID to whichever mounted entry has priority.

```
   mount order (low → high priority)
   ┌────────────────────────┐
   │ DataPC.forge (base)    │  fileID 30091 → meshA
   ├────────────────────────┤
   │ DataPC_patch_01.forge  │  fileID 30091 → meshA'   ← overrides base
   │ (Ubisoft patch)        │
   ├────────────────────────┤
   │ DataPC_patch_01.forge  │  fileID 30091 → meshA''  ← your mod overrides again
   │ (your MOD, same name)  │
   └────────────────────────┘
            │  resolve by ID
            ▼
   effective index: fileID 30091 → meshA''
```

> **Why we believe this:** (1) the base/patch file pairing is real and universal on disk; (2) every studied mod works by placing entries into a `*_patch_01.forge`, never by editing the base; (3) **verified from ATK source** — a forge entry (`ForgeEntry`) is identified by its 64-bit `ID` alone, with no field tying it to a forge or to sibling entries (see [`02-forge-file-format.md`](02-forge-file-format.md)). A flat ID→data archive only "works" as game data if IDs resolve through a merged, cross-forge index. The exact priority algorithm (filename ordering? a manifest? newest mount wins?) is still **inferred**, not yet confirmed from engine internals.

> **Community corroboration:** SamiPuma (Tier 1 Imports) reports that the item/gameplay/resource split isn't required — putting everything into `DataPC_extra_patch_01.forge` "should still work." That is exactly what the flat-ID-archive model predicts: any **mounted** forge can host an entry, and the ID resolves regardless. The untested edge is whether an arbitrary *new* forge filename would be auto-mounted, or whether only the known `DataPC*` patch slots are. See open question 1.

## Evidence on disk

The base+patch pairing is consistent across the whole install (see [`reference/forge-inventory.md`](../reference/forge-inventory.md)):

- `DataPC.forge` + `DataPC_patch_01.forge`
- `DataPC_Resources.forge` + `DataPC_Resources_patch_01.forge`
- `DataPC_extra.forge` + `DataPC_extra_patch_01.forge`
- each `DataPC_TGT_WorldMap_*_Split.forge` + its `_Split_patch_01.forge`
- API-variant forges: `_dx11` and `_vulkan` siblings (DirectX 11 vs. Vulkan render backends)

The `_patch_01` suffix strongly implies a numbered patch chain (`_patch_02`, etc., are possible as the game updates). Mods reuse the **`_patch_01`** slot, which is exactly why mods can collide with each other and occasionally with official patches.

## Verified: real IDs are globally unique, and patches override by ID (empirical)

Parsing the **forge indexes directly** (the real `ForgeEntry.ID` for every entry — a uint64, *not* the positional number in unpacked filenames; see [`03-data-and-resources.md`](03-data-and-resources.md)) settles the ID model on real data:

- **IDs are unique within every forge.** `DataPC.forge` (48 707 entries), `DataPC_Resources.forge` (123 571), and every patch forge each had **zero duplicate IDs**.
- **IDs do not collide across forge families.** Real-ID overlap between unrelated forges is essentially just the two **reserved sidecar IDs** every forge carries — `16` (`GlobalMetaFile`) and `145` (`PrefetchingFileInfos`): `DataPC_Resources ∩ DataPC = 2`, `Resources ∩ extra = 2`, etc. The occasional extra cross-forge match (e.g. `WG_SMG_UZZI` present in both `DataPC_patch` and `extra_patch`) carries the **same ID *and* the same name** — the same logical resource intentionally shipped in two forges, not a collision. **There were no "same ID, different resource" cases across families.** So a 64-bit file ID effectively identifies one resource game-wide.
- **A patch overrides its base by ID.** Shared IDs between a base and its patch: `DataPC ∩ DataPC_patch = 2321`, `Resources ∩ Resources_patch = 1961`, `extra ∩ extra_patch = 268`. The large majority carry **matching names** (2316 / 1799 / 254) — the patch entry replaces the same resource. The rest are Ubisoft **repurposing an ID for new content** (e.g. `WI_DMR_MK14_Stock_Collapsed_LOD0` → `WI_DMR_JAEM1A_Stock_LOD0`; the `MSR` sniper parts → `JAE700` parts) or fixing a name typo (`TP_FaceHair…` → `TP_FacialHair…`, `FTP_Glove_Alicia` → `FTP_Gloves_Alicia`). Either way the patch entry with that ID wins.

> **This is the technical basis for replacement mods**, now confirmed rather than inferred: the merged index is keyed on the real 64-bit ID; put an entry with an existing ID into a mounted patch forge and it overrides. Ubisoft's own patches do exactly this, even repurposing IDs to swap content. (Tool: parse any forge's IDs/types or diff two forges for shared-ID conflicts with the Forge Inspector — see [`tools/`](../tools/README.md).)
>
> **Correction:** an earlier draft suspected IDs "aren't globally unique across forges" after seeing the number `34224` in two forges. That number was a **positional index in the unpacked filename**, not a file ID — the real IDs above show no such collision. See [`03-data-and-resources.md`](03-data-and-resources.md) and the research log.

> **⚠️ The forge shadow (2026-07-03) — same-ID duplication across two *base* forges.** The ID study above compared base-vs-patch and *unrelated* families, but **did not** compare the core `DataPC.forge` against the WorldMap `_Split` **base** forges. It later turned out that **44 of 56 `Cloth` resources carry the same 64-bit ID in *two base* forges** — `DataPC.forge` **and** a WorldMap region base (chiefly `DataPC_TGT_WorldMap_Bootstrap_Split.forge` for 41; also `_Darkwood_Split` for 3 and `_MaungaNui_Split` for 2). Same ID, same name, same resource — intentional duplication, not a collision — but it means **which base copy the runtime resolves for a shadowed ID is an open question** (the peer-forge priority rule below now clearly bites *base* forges, not just peer patches). It also breaks the clean "a patch overrides its base everywhere" picture for these resources: a patch override placed in only *one* of the two families' patch forges **hangs the load** (observed on a cloth), so a shadowed resource must be overridden in **both** patch forges — exactly how vanilla ships the one cloth it overrides (`TP_Top_Bodark_Trench_Cloth`, present in both `DataPC_patch_01` and `Bootstrap_Split_patch_01`). Whether the shadow extends beyond `Cloth` to meshes/definitions is **unmeasured** (a base-vs-base diff across all forges is a TODO). See [`../meta/research-log.md`](../meta/research-log.md) (2026-07-03).

## Consequences for modding (these are the practical rules)

1. **You override by ID, in a patch forge.** Put an entry with an existing file ID into `DataPC_*_patch_01.forge` and it replaces the base entry everywhere that ID is referenced. This is the entire basis of replacement mods. **⚠️ Exception — shadowed IDs:** if the same ID lives in *two* base forges (the forge shadow above — notably most cloths), overriding it in one family's patch is **necessary but not sufficient**: it can leave the other base copy live and (observed on cloth) **hang the load**. Shadowed resources must be patched in **both** relevant patch forges.
2. **You add new content by minting new IDs** (the embedded `ClassID` of each new resource) and referencing them from BuildTables/entities you also patch in. (New files are often *labeled* `77777` in the filename — a sort tag, not the ID; see [`08-naming-conventions.md`](08-naming-conventions.md).)
3. **Two mods that write the same patch forge collide.** Because everyone targets `*_patch_01.forge`, combining mods means **merging their `.data` entries into one patch forge**, not stacking files. If two mods change the *same* ID, only one can win — a true conflict.
4. **Keep cross-forge references consistent.** A patched BuildTable in the item forge must reference resource IDs that actually exist (with the right contents) in the resources forge. The merged index only "works" if the IDs line up.
5. **Render-backend variants exist.** `_dx11` vs `_vulkan` forges mean some data is duplicated per backend; a mod that touches such data may need to account for the backend the user runs. (Most cosmetic mods touch backend-agnostic resource forges and don't hit this.)

## What's still open

Tracked in [`meta/research-log.md`](../meta/research-log.md):

- **Partly resolved:** override *is* keyed on the real 64-bit ID, and a patch overrides its base (verified above). Still open is the **priority order when the same ID is in two *peer* forges** — e.g. two mods, or a mod vs. an official patch, both in `*_patch_01` slots. That's a game-runtime rule (mount order) not encoded in ATK; it needs an in-game A/B test.
- Whether GRB supports a patch chain beyond `_patch_01` and how numbering affects priority.
- The role of `GlobalMetaFile` / `PrefetchingFileInfos` in mount/streaming and whether a mod must update them for new content (vs. pure replacement).
- How the world-map `_Split` forges and `Bootstrap` forge participate (streaming regions vs. global data) — and, per the forge shadow above, **which copy wins when a `_Split` base and `DataPC.forge` hold the same ID** (44/56 cloths do). This is the highest-value shadow question.

Confirming the priority rule is the highest-value open question here: it determines mod load order, conflict resolution, and how a mod manager should merge patches.
