# 01 — Overview: Anvil, Scimitar, GRB, and the modding scene

## The engine

Ghost Recon: Breakpoint runs on Ubisoft's in-house **Anvil** engine (you will also see it called *AnvilNext*). Anvil's older internal codename is **"Scimitar,"** and that name is baked into the data files: every `.forge` archive begins with the literal ASCII bytes `scimitar`. The same engine family — and the same `.forge`/`.data` container format — powers a long line of Ubisoft titles, which is exactly why the **Anvil Toolkit (ATK)** is a *multi-game* tool.

Games in the Anvil/Scimitar lineage that ATK supports (from its README changelog) include:

- Assassin's Creed: AC1, AC2, Brotherhood, Revelations ("Ezio trilogy"), AC3 (+ Remastered), AC4: Black Flag, Rogue, Unity, Syndicate, Origins, Odyssey, Mirage
- Steep
- **Ghost Recon: Breakpoint** ← the focus of this repo

The practical upshot: GRB shares its data architecture with AC: Origins / Odyssey-era titles. Knowledge, hashes, and tooling often transfer between them.

## What "modding GRB" means today

There is **no official mod SDK** for GRB. The game ships as a set of `.forge` archives plus executables and a few loose data blobs. Modding is therefore **data modding**: you reach into the forges, replace or add resources (a weapon mesh, a face texture, a piece of gear), and let the game load your changes through its normal patch-loading mechanism.

Because of how the engine loads data (see [`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md)), you almost never edit the giant base forges directly. Instead you work in the smaller **patch forges** named `*_patch_01.forge` that the game layers on top of the base data, overriding specific entries by their file ID. In practice you point ATK at your own install and **repack these patch forges in place**, so your changes are live immediately — a modded install just accumulates changes in its forges over time. When mods are shared (e.g. on Nexus), it's usually the mod's **entries** (an unpacked folder), which you import into your own patch forges with ATK and repack — not whole forge files.

The overwhelming majority of GRB mods are **cosmetic asset replacements**: new outfits, gear, weapons, faces, hairstyles, camos, attachments, and UI. The corpus studied for this repo (150+ community mods — see [`examples/mod-catalog.md`](../examples/mod-catalog.md)) is almost entirely of this kind.

## The scene

GRB's modding community is small and concentrated. The relevant context for this repo:

- **Tier 1 Imports** — the primary active community where GRB mod development still happens. Most of the asset-replacement know-how lives in its Discord threads.
- **Anvil Toolkit (ATK)** — the toolkit that makes all of this possible, built and maintained by a few skilled community developers. Its support/updates Discord is `https://discord.gg/vsuGFEapdq`.
- Mods are also distributed via **Nexus Mods** (many folder names in the studied corpus carry Nexus-style IDs and timestamps, e.g. `Strix face V2-1550-V2-1757740151`).

This concentration is *why* this knowledgebase exists: the expertise is real but thinly spread and largely unwritten. Capturing it in a form both humans and AIs can read is the whole point.

## How the pieces fit together

```
        Blender (author mesh / texture)
                 │  export
                 ▼
       glTF / GLB  +  DDS / PNG
                 │  import via ATK
                 ▼
   ┌─────────────────────────────────────┐
   │  .forge archive  (magic: "scimitar") │
   │   ├─ .data entry (ID 1707208440119)  │
   │   │    └─ typed resource: Mesh       │
   │   ├─ .data entry (ID 1439949634142)  │
   │   │    └─ typed resource: TextureMap │
   │   └─ … index maps 64-bit ID → entry  │
   └─────────────────────────────────────┘
                 │  repack via ATK (in place, in your install)
                 ▼
        DataPC_*_patch_01.forge  (rewritten in the install)
                 ▼
   GRB loads base forges + patch forges,
   merges by file ID (patch overrides base)
```

## Where to go next

- The archive format itself: [`02-forge-file-format.md`](02-forge-file-format.md)
- What lives inside a forge: [`03-data-and-resources.md`](03-data-and-resources.md)
- The tool that does the work: [`04-anvil-toolkit.md`](04-anvil-toolkit.md)
- How a real mod is structured across forges: [`05-three-forge-model.md`](05-three-forge-model.md)
