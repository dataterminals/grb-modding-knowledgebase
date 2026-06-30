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

Distributing the mod = giving the user the repacked patch forge(s) to place in their GRB install directory (next to the base forges), replacing/adding the corresponding `*_patch_01.forge`. Because mods and official patches share the same patch filename, **mod managers / manual installs must reconcile multiple mods that all want to write `DataPC_Resources_patch_01.forge`** — combining mods means merging their entries into one patch forge. (This merge problem is an open area; see [`meta/research-log.md`](../meta/research-log.md).)
