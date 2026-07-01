# 05 — The three-forge model (base vs. patch, and how a mod is split)

GRB's data is spread across ~25 forge files, but a modder interacts with a small, predictable subset. This doc explains the **base vs. patch** distinction and the **three-forge structure** that most cosmetic mods follow.

## Base forges vs. patch forges

For most data forges there are **two physical files**:

- `DataPC_<name>.forge` — the **base** archive shipped with the game.
- `DataPC_<name>_patch_01.forge` — the **patch** archive shipped by Ubisoft's updates.

> **Verified** on a real install: `DataPC.forge` (1.0 GB) **and** `DataPC_patch_01.forge` (1.45 GB); `DataPC_Resources.forge` (23.6 GB) **and** `DataPC_Resources_patch_01.forge` (38 GB); `DataPC_extra.forge` and `DataPC_extra_patch_01.forge`; world-map splits each with their own `_patch_01`.

At load time the game layers the patch over the base. **A mod is just another patch layer** — you put your changes into a `*_patch_01.forge` and the game treats your entries the same way it treats Ubisoft's patch entries: same-ID entries override. (How that merge works is detailed in [`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md).)

This is why you almost never repack the giant base forges. You build small patch forges instead — faster, safer, and that's the mechanism the engine already expects.

## The three forges a cosmetic mod touches

> **⚠️ Important nuance — the split is a *convention*, not a hard requirement.** Community feedback from **SamiPuma (Tier 1 Imports)**, a very active cosmetic mod creator: *"I don't think that forge split is even necessary — if someone just puts all those in `extras patch 01`, it should still work."* This is consistent with the verified forge format: a forge entry is identified by its **file ID alone**, with no field binding it to a particular forge (see [`02-forge-file-format.md`](02-forge-file-format.md)). The engine merges **all mounted forges** into one ID-keyed index, so an entry resolves by ID regardless of *which* mounted forge holds it. The practical caveats: (a) the forge you use must be one the game **already mounts** (the `DataPC*_patch_01` set qualifies), and (b) the heavy mesh/texture resources still want to live in a *Resources* forge for streaming/size reasons. So treat the three-forge layout below as the **organizing convention the community follows** (mirroring how Ubisoft ships the data), not a law the engine enforces. Confirming the exact limits of this is an open question in [`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md).

A complete asset-replacement mod usually coordinates **three** patch forges. Observed directly in the `USP Tactical + Burris FF3` mod, which ships exactly these three folders to repack:

```
USP Tactical + Burris FF3/
├── DataPC_patch_01.forge/           ← item / inventory definitions  (WI_…)
│     ├── 28580_-_WI_HDG_P12.data
│     ├── 30091_-_WI_HDG_P12_Main.data
│     └── 30093_-_WI_HDG_P12_Barrel.data
├── DataPC_extra_patch_01.forge/     ← gameplay definitions          (WG_…)
│     ├── 26_-_WG_HDG_P12.data
│     ├── 3950_-_WG_HDG_P12_Main.data
│     └── 3952_-_WG_HDG_P12_Barrel.data
└── DataPC_Resources_patch_01.forge/ ← the heavy resources (meshes + textures)
      ├── 77777_-_WG_HK_USP45_Receiver_LOD0.data   (~50 MB)
      ├── 77777_-_WG_HK_USP45_Magazine_LOD0.data   (~9.5 MB)
      ├── 77777_-_WG_HK_USP45_Barrel_LOD0.data
      ├── 77777_-_WG_HK_USP45_Muzzle_LOD0.data
      ├── (matching WI_… mesh set)
      └── 79779_-_UI_HDG_P12_Map.data              (UI icon)
```

### The division of labor

| Forge | Role | Typical contents | Size feel |
| --- | --- | --- | --- |
| **`DataPC_patch_01`** | *Item* layer | `WI_…` (Weapon Item / inventory entries), **BuildTables**, entity defs | small (KB) |
| **`DataPC_extra_patch_01`** | *Gameplay* layer | `WG_…` (Weapon Gameplay entries) | small (KB) |
| **`DataPC_Resources_patch_01`** | *Resource* layer | the actual **meshes** (`…_LOD0–3`) and **textures** (`…_Mip0–N`), UI maps | large (MB–GB) |

The small definition forges say *"this item/weapon exists and is built from these parts"*; the resources forge supplies the *bytes* (geometry + pixels). A mod that changes only a texture might touch just the resources forge; a mod that adds a whole new weapon variant touches all three. (`WI_`/`WG_`/prefix meanings are in [`08-naming-conventions.md`](08-naming-conventions.md).)

### Not every mod is three forges

The split depends on what's being changed:

- **Texture-only retexture** (e.g. a camo) → often just `DataPC_Resources_patch_01`.
- **BuildTable-only tweak** (e.g. re-pointing a head to existing parts, like `Sheva_buildtables` which ships a single `295_-_Head_Hisp_Kunal.BuildTable`) → just the item/definition forge.
- **Full new outfit/weapon** → all three, in lockstep, with IDs matched up.

The studied corpus shows both patterns plainly: many mod folders are named `*_buildtables` (definition-layer only) or `*_resources` (resource-layer only), and others ship the full set.

## Why the layers must agree

The forges are coupled by **file IDs and references**. A BuildTable in the item forge references mesh/material/texture resources *by ID* in the resources forge. If the resource forge has the new mesh but the BuildTable still points at the old ID (or vice-versa), the asset won't appear correctly. Keeping IDs consistent across the three forges is the central correctness concern when assembling a mod — and the most common source of "why isn't my mod showing up" problems.

## Installation shape

You normally mod **in place**: ATK is pointed at your GRB install and repacks the forge directly, so the mod is live with no separate "install" step (see [`docs/07-modding-workflow.md`](../docs/07-modding-workflow.md)). Whole forge files aren't usually passed around — they're multi-GB and hold your machine's accumulated state. **Sharing a mod** means sharing its `.data` entries (often an unpacked mod folder), which the recipient imports into their own forges and repacks. Because everyone's entries end up merged into the same patch forge, **combining mods means their entries must coexist in one forge** — and two mods that touch the same file ID truly conflict (only one wins; diff them with the Forge Inspector, [`tools/`](../tools/README.md)). (This merge/conflict problem is an open area; see [`meta/research-log.md`](../meta/research-log.md).)
