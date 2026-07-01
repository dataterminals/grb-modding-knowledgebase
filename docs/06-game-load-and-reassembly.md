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

## Consequences for modding (these are the practical rules)

1. **You override by ID, in a patch forge.** Put an entry with an existing file ID into `DataPC_*_patch_01.forge` and it replaces the base entry everywhere that ID is referenced. This is the entire basis of replacement mods.
2. **You add new content by minting new IDs** (the embedded `ClassID` of each new resource) and referencing them from BuildTables/entities you also patch in. (New files are often *labeled* `77777` in the filename — a sort tag, not the ID; see [`08-naming-conventions.md`](08-naming-conventions.md).)
3. **Two mods that write the same patch forge collide.** Because everyone targets `*_patch_01.forge`, combining mods means **merging their `.data` entries into one patch forge**, not stacking files. If two mods change the *same* ID, only one can win — a true conflict.
4. **Keep cross-forge references consistent.** A patched BuildTable in the item forge must reference resource IDs that actually exist (with the right contents) in the resources forge. The merged index only "works" if the IDs line up.
5. **Render-backend variants exist.** `_dx11` vs `_vulkan` forges mean some data is duplicated per backend; a mod that touches such data may need to account for the backend the user runs. (Most cosmetic mods touch backend-agnostic resource forges and don't hit this.)

## What's still open

Tracked in [`meta/research-log.md`](../meta/research-log.md):

- The **exact priority rule** when an ID appears in multiple mounted forges (load order source of truth).
- Whether GRB supports a patch chain beyond `_patch_01` and how numbering affects priority.
- The role of `GlobalMetaFile` / `PrefetchingFileInfos` in mount/streaming and whether a mod must update them for new content (vs. pure replacement).
- How the world-map `_Split` forges and `Bootstrap` forge participate (streaming regions vs. global data).

Confirming the priority rule is the highest-value open question here: it determines mod load order, conflict resolution, and how a mod manager should merge patches.
