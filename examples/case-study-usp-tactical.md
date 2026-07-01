# Case study — "USP Tactical + Burris FF3" (a 3-forge weapon mod)

A real, complete weapon mod from the studied corpus that demonstrates the **three-forge model** ([`docs/05-three-forge-model.md`](../docs/05-three-forge-model.md)) cleanly. It replaces an in-game handgun (the **P12 / HDG** slot) with an **HK USP45** model and adds a **Burris FF3** optic, including the inventory icon.

> Source: `Extracted\GRBMods\USP Tactical + Burris FF3\` on a real install. All file IDs/sizes below are observed directly.

## What the mod ships (three repack folders)

```
USP Tactical + Burris FF3/
├── DataPC_extra_patch_01.forge/        ← gameplay (WG_) definitions
│     ├── 26_-_WG_HDG_P12.data                 (24 KB)
│     ├── 3950_-_WG_HDG_P12_Main.data          ( 2 KB)
│     └── 3952_-_WG_HDG_P12_Barrel.data        (722 B)
│
├── DataPC_patch_01.forge/              ← item / inventory (WI_) definitions
│     ├── 28580_-_WI_HDG_P12.data              ( 6 KB)
│     ├── 30091_-_WI_HDG_P12_Main.data         ( 2 KB)
│     └── 30093_-_WI_HDG_P12_Barrel.data       (605 B)
│
└── DataPC_Resources_patch_01.forge/   ← the heavy meshes + UI texture
      ├── 77777_-_WG_HK_USP45_Receiver_LOD0.data   (50.3 MB)
      ├── 77777_-_WG_HK_USP45_Magazine_LOD0.data   ( 9.6 MB)
      ├── 77777_-_WG_HK_USP45_Barrel_LOD0.data     ( 3.2 MB)
      ├── 77777_-_WG_HK_USP45_Muzzle_LOD0.data     (602 KB)
      ├── 77777_-_WI_HK_USP45_Receiver_LOD0.data   (50.3 MB)
      ├── 77777_-_WI_HK_USP45_Magazine_LOD0.data   ( 9.6 MB)
      ├── 77777_-_WI_HK_USP45_Barrel_LOD0.data     ( 3.2 MB)
      ├── 77777_-_WI_HK_USP45_Muzzle_LOD0.data     (602 KB)
      └── 79779_-_UI_HDG_P12_Map.data              (197 KB)
```

## How to read it

**1. The definition layers are tiny; the resource layer is huge.** The `WG_`/`WI_` `.data` files are KB-scale — they're definitions (which parts make up the weapon, how it's built). The mesh `.data` files in the resources forge are MB-scale (a 50 MB receiver mesh). This is the division of labor: definitions say *what*, resources supply the *bytes*.

**2. The same weapon appears in both a `WG_` and a `WI_` flavor.** `WG_HDG_P12` (gameplay) and `WI_HDG_P12` (item/inventory) are parallel definitions of the same P12 slot, living in different forges. The meshes likewise come in `WG_HK_USP45_*` and `WI_HK_USP45_*` sets — the **gameplay/world model** and the **inventory/preview model** of the same gun.

**3. Components are individual resources.** The USP is split into `Receiver`, `Barrel`, `Magazine`, `Muzzle` — each a separate mesh. The weapon's definition references these component IDs to assemble the whole gun. (Naming: [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md).)

**4. The replacement targets the P12 slot but supplies USP45 geometry.** The *definitions* keep the GRB slot name (`HDG_P12` — the handgun the game already has), while the *meshes* are named for what they actually are (`HK_USP45`). So in-game, selecting the P12 pistol now shows a USP45. The definition layer is the indirection that makes the swap appear under an existing weapon.

**5. Every new mesh is *labeled* `77777` — a filename tag, not a shared ID.** All eight mesh files are *named* `77777_-_…`, but they do **not** share a file ID: the leading number in an unpacked filename is a positional index / sort label, and each file's **real 64-bit ID is its embedded `ClassID`** (all distinct — verified on comparable mod files). The definition-layer numbers (`30091`, `28580`, `26`, `3950`, …) are likewise filename labels — for a *replacement* they're chosen to match the base entry the mod overrides. On repack ATK derives every entry's ID from its embedded `ClassID`, ignoring these numbers (see [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md)). The `77777` tag is simply a reliable tell that "these are injected new meshes."

**6. The UI icon is part of the mod.** `79779_-_UI_HDG_P12_Map` is the inventory thumbnail for the weapon — a mod that changes a weapon's look also updates how it appears in menus.

## What this implies for building a similar mod

To replace a weapon, you generally need to coordinate, with consistent IDs:
1. **Resources forge:** the new component meshes (`Receiver`/`Barrel`/`Magazine`/`Muzzle`, each LOD), in both `WG_` and `WI_` flavors, plus the UI icon.
2. **Item forge (`DataPC_patch_01`):** the `WI_` definitions pointing at the inventory meshes.
3. **Gameplay forge (`DataPC_extra_patch_01`):** the `WG_` definitions pointing at the world meshes.

Miss one layer (e.g. update the world model but not the inventory model) and the gun looks new in-hand but old in the menu — a classic symptom of an incomplete three-forge mod.

## Open threads from this example

- Only `LOD0` meshes are shipped here — does the game fall back to base LODs for distance, or does this mod simply not provide lower LODs (and is that visible at range)? (See [`docs/10-meshes-and-skeletons.md`](../docs/10-meshes-and-skeletons.md).)
- ~~The exact resolution of duplicate `77777` IDs at repack/install.~~ **Resolved:** `77777` is a filename label, not an ID; real IDs are the files' distinct embedded `ClassID`s, which ATK reads on repack. See [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md).
- Whether `WG_` vs `WI_` always means world-model vs inventory-model, or something subtler.
