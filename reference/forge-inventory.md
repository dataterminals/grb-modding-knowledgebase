# Reference — Forge inventory (GRB install)

The `.forge` files present in a real, up-to-date GRB install (Steam), with sizes and inferred roles. Sizes are from a live install on 2026-06-30 and will vary slightly by patch level. **Roles marked (inferred)** are deduced from filenames + observed contents, not from engine documentation.

## Core data forges

| Forge | Size | Role (inferred) |
| --- | ---: | --- |
| `DataPC.forge` | 1.02 GB | Base game data: entities, missions, AI, animations, item/weapon definitions. |
| `DataPC_patch_01.forge` | 1.45 GB | Patch layer over `DataPC.forge`. **Primary mod target for item/inventory (`WI_`) defs + BuildTables.** |
| `DataPC_Resources.forge` | 23.6 GB | Base **resources**: meshes + textures for everything. The big one. |
| `DataPC_Resources_patch_01.forge` | 38.0 GB | Patch layer of resources. **Primary mod target for meshes/textures.** |
| `DataPC_extra.forge` | 70.3 MB | Base "extra" data (gameplay `WG_` defs, etc.). |
| `DataPC_extra_patch_01.forge` | 36.9 MB | Patch layer. **Mod target for gameplay (`WG_`) defs.** |

## Render-backend variants

These mirror data per graphics API (DirectX 11 vs. Vulkan). Most cosmetic mods don't touch them.

| Forge | Size | Role (inferred) |
| --- | ---: | --- |
| `DataPC_dx11.forge` | 30.6 MB | DirectX 11 backend data. |
| `DataPC_vulkan.forge` | 116.9 MB | Vulkan backend data. |
| `DataPC_TGT_WorldMap_dx11.forge` | 5.5 MB | World-map data, DX11. |
| `DataPC_TGT_WorldMap_vulkan.forge` | 24.1 MB | World-map data, Vulkan. |

## World-map / streaming "Split" forges

Region/streaming data. Each has a base `_Split.forge` and a `_Split_patch_01.forge`.

| Forge (base + patch) | Base size | Note |
| --- | ---: | --- |
| `DataPC_TGT_WorldMap_MaungaNui_Split.forge` | 10.95 GB | Main island region — largest world forge. |
| `DataPC_TGT_WorldMap_Darkwood_Split.forge` | 1.29 GB | Region. |
| `DataPC_TGT_WorldMap_Golem_Split.forge` | 1.07 GB | Region. |
| `DataPC_TGT_WorldMap_Windy_Split.forge` | 554 MB | Region. |
| `DataPC_TGT_WorldMap_OrphanCells_Split.forge` | 530 MB | Streaming "orphan" cells. |
| `DataPC_TGT_WorldMap_Egg_Split.forge` | 146.8 MB | Region. |
| `DataPC_TGT_WorldMap_Bootstrap_Split.forge` | 136.8 MB | World bootstrap/init data. |

## GhostRoom / misc forges

| Forge | Size | Note |
| --- | ---: | --- |
| `DataPC_GRN_GhostRoom.forge` | 229 KB | "Ghost Room" (loadout/social hub) data. |
| `DataPC_GRN_GhostRoom_dx11.forge` | 393 KB | DX11 variant. |
| `DataPC_GRN_GhostRoom_vulkan.forge` | 1.6 MB | Vulkan variant. |

## Non-forge data blobs (for completeness)

These sit beside the forges in the install and are **not** forge archives:

| File | Size | Note |
| --- | ---: | --- |
| `PCtgt_terrainlin1.tbf` | 5.97 GB | Terrain data (`.tbf`). |
| `tgt.wmap` | 892 MB | World map data. |
| `tgt.wmp2` | 254 MB | World map data (v2). |
| `PCtgt_terrainlin0.tbf` / `…lin2.tbf` | 33.8 MB / 6.5 MB | Terrain. |
| `compressed_oodle_compression_state.bin` | 1.04 MB | Oodle compression state (codec support). |
| `oo2core_7_win64.dll` | 1.03 MB | **Oodle** codec — confirms forge resource compression. |
| `GRB.exe` / `GRB_vulkan.exe` | 536 MB / 519 MB | Game executables (DX11 / Vulkan). |

## Backup folders observed in the install

The install carries backup copies of forges (created by ATK and/or by modders), confirming the "always back up before repacking" discipline:

- `Backups\` — contains `DataPC.forge`, `DataPC_patch_01.forge`, `DataPC_Resources.forge`, `DataPC_Resources_patch_01.forge`, `DataPC_extra*.forge`, world-map patch forges.
- `_GRBbackups\` — additional backup set.
- `Extracted\` — ATK's unpacked working folders (per forge), plus `Extracted\GRBMods\` holding 150+ mod working folders.

> The **three primary mod targets** are highlighted above: `DataPC_patch_01.forge` (items), `DataPC_extra_patch_01.forge` (gameplay), `DataPC_Resources_patch_01.forge` (meshes/textures). See [`docs/05-three-forge-model.md`](../docs/05-three-forge-model.md).
