# What a modded install already loads — the edit classes GRB has accepted

*Written 2026-09-20 from a content-hash diff of the live forges on SylG5 against the pristine copies
the install keeps, plus a bone-by-bone comparison of every mod-touched skeleton with its vanilla
namesake. Read-only; nothing was written or launched. Method and caveats are at the end.*

> **Why this page exists.** No edit of *ours* has been confirmed to load in game since July. But
> this install runs with about two hundred community mods repacked into its forges, and every one of
> them is an edit the game has already accepted. Listing which resource types they touch turns "will
> a modified X load?" into a lookup. For skeletons the answer was better than hoped.

## The short version

| Lane | What the install already proves | What it does not prove |
| --- | --- | --- |
| **2B — bone physics** | **Modified skeletons load, physics blobs and all.** The *Sling Positions* mod overrides **124** vanilla backpack rigs **by their vanilla IDs** with two bones moved and a 37–62 KB Reflex3 blob carried byte-for-byte. 65 weapon and holster rigs ship edited copies under new IDs. The three holster mods re-parent the holster bone from `RightUpLeg` to `Hips`. | **No mod has ever changed a Reflex3 blob.** Whether the runtime accepts a blob it did not compile itself is the one untested step, and it is exactly the step an authored rig needs. |
| **2A — cloth** | Eleven modified `Cloth` resources have sat in the live base `DataPC.forge` since the 2026-07-01 test, and the game has booted and run with them for eleven weeks. | Whether that copy is ever read: all eleven are shadowed by copies in the WorldMap forges. No mod on this install ships a cloth. |
| **4 — AI database** | Twenty `DB*` / `GR_*` record types are modified in place by installed mods, among them the radio-call config, a sound-detection record, spawn descriptors and the sensor shapes. | Anything about records that change size: every precedent keeps its record the same length. |

## Install-wide: resource types found added or modified

Each live forge against its pristine copy, by resource type. *Added* = a ClassID no backup holds;
*modified* = the ClassID exists but the bytes differ from every backup copy. Counts are resources,
not containers.

| Type | Added | Modified | Where, and which mods |
| --- | ---: | ---: | --- |
| `TextureMap` | 5,446 | 0 | Resources patch; every reskin |
| `Material` | 2,374 | 10 | Resources patch |
| `TextureSet` | 2,089 | 0 | Resources patch |
| `BuildTable` | 1,819 | 239 | `DataPC_patch_01` (1,552 added, 203 modified — the item tables in `TEAMMATE_Template`), `extra_patch` (weapon tables), Resources patch (242 weapon tables) |
| `DBUnlockable` | 0 | 1,734 | base `DataPC.forge` — the *UE Update* unlock-everything mod, which is why the base forge is not pristine |
| `Mesh` | 1,205 | 5 | Resources patch, plus 37 meshes in `DataPC_patch_01` |
| **`Skeleton`** | **278** | 0 | see the next section: 124 of them are vanilla IDs overridden with moved bones |
| `DBUnlockableGroup` | 0 | 176 | `DataPC_patch_01` |
| `CompiledMip` | 158 | 0 | |
| `ScopeAttachmentDBEntry` | 0 | 79 | |
| `LODSelector` | 57 | 0 | |
| `Animation` | 38 | 22 | 22 idle and gunsmith clips modified in place (`crouchanimations`, weapon mods) |
| `EntityBuilder` | 32 | 7 | weapon mods; 7 vanilla builders modified in `extra_patch` |
| `DBUnlockableUIConfig`, `GR_WeaponDBEntry` | 0 | 22 each | |
| `TextureMapArray` | 22 | 0 | |
| `DBQuartzUnlockable` (id 2447912088) | 0 | 16 | |
| `DBSensorShapeCustom` | 0 | 14 | AI sensor shapes, modified in place |
| **`Cloth`** | 0 | **11** | base `DataPC.forge` — this repo's own July test cloths, never restored |
| `DIA_*` (id 3275129368) | 0 | 7 | dialogue records |
| `DBSensorShapeVehicle` | 0 | 6 | |
| `Entity`, `KinoGraphData`, `KinoExternalResourceHolder` | 4 each | 0 | |
| `GR_SpawnNpcDescriptor` | 0 | 4 | *Fear the Radio* |
| `DBWeaponSmith_AttachmentPerWeaponSetting`, `DBLootableUnlockable` | 0 | 3 each | |
| `TextureMapSpec` | 2 | 0 | |
| `DBAIRadioCallConfig`, `DBPlayerHealth`, `GR_BulletDBEntry`, `GR_DBExplosionParams`, `XCurve`, `ProjectileGeneratorDBEntry`, `DBAISoundDetection_MovingSounds`, `DBLootableCurrency`, `RegionLayout` | 0 | 1 each | *Fear the Radio*, *4HealthBars*, *Honey Badger*, *behemoth_42kcredits*, …; the `RegionLayout` is `RoadEvents_MainIsland` in the Bootstrap patch, source unknown |

Types **never** touched by any installed mod include `Cloth` (added), `SoftBody`, `MotionCloth`,
`LiteRagdoll`, `RagdollSkeleton`, and every world-map resource except that one layout.

## Skeletons, bone by bone

277 `Skeleton` resources in the three live patch forges match no backup copy. Compared with the
vanilla skeleton of the same name (indexed from the base forges):

| Verdict | Count | Physics blob | ClassID | What it is |
| --- | ---: | --- | --- | --- |
| **bones differ, blob identical** | **124** | 19–62 KB | **vanilla** | the *Sling Positions* mod's backpack rigs: it re-ships every `BP_*` rig into the Resources patch with the two sling-attach bones moved, overriding the base copy by ID |
| bones differ, blob identical | 37 | none (8 B header) | vanilla | weapon rigs overridden with re-positioned parts |
| bones differ, blob identical | 62 | none | new | weapon rigs and the three holster rigs, copied under new IDs |
| bones differ, blob identical | 1 | 386 B | new | `WI_ASR_AK47` from *AKM_KYPK*: twelve bones moved 2–3 cm, **including `f46825bf`, the bone its physics record drives** — the blob, with that bone's baked local matrices, is vanilla. The game runs with a physics record whose matrices disagree with the skeleton by 3 cm |
| no vanilla namesake | 50 | none | new | new weapon parts |
| same bones and blob, other bytes differ | 3 | one with | mixed | re-serialised copies |

So: **zero mods change a Reflex3 blob; 125 carry one unchanged through an edited skeleton**, 124 of
them as overrides by vanilla ID. The runtime reads the blob out of a mod-written container, applies
the mod's bone positions, and the straps still swing.

**The holster mods** (*Acosta – The Bison Belt*, *Tactical Human Set*, *Eva Modern Outfit*) each ship
a copy of `Player_Holster_NoSling_Addon` (1,560 B, 12 bones, no physics) under a new ID —
`999930102020999`, `8538993526999`, `888830102028888` — with one change: the holster bone
`a33f821d` re-parented from `RightUpLeg` to `Hips` and moved to the belt. Their build tables assign
the new rig at Index 3. `Delta_Holster_Addon` is therefore **mod content**, not vanilla; the
2026-09-16 rig-assignment table listed it as if it were.

> **Verified:** every count and comparison above. **Inferred:** that "the game loads it" follows
> from "the mod is enabled, the game boots, and the user plays with it". A rig's visible effect —
> the sling on the front, the holster on the belt — is one look in game away and has not been taken
> for this page.

## What this does to the lane-2B plan

The wall from July — *nothing we have written has been confirmed to load* — still stands for our
own files, but the install has already walked most of the way past it:

1. A `Skeleton` resource rewritten by a modder's tool, with bones re-parented and moved, loads. ✔
2. A skeleton that carries a Reflex3 blob loads with it, from a mod-written container. ✔
3. A rig assigned from an item's build table by a `Skeleton` Handle loads. ✔ (the holster mods)
4. Overriding a vanilla skeleton by ID from the Resources patch works. ✔ (124 times)
5. **A blob the game did not compile** — an authored chain — has never been tried. ✘

The generator can therefore skip straight to step 5. The cheapest first test is the one that
isolates it: take a vanilla rig the install already overrides (`BP_AVS_CASPER_ADDON_MEDIUMVEST`),
change one number in one physics record — a swing limit — and nothing else, and see whether the
strap still swings.

## Where mods write, and how to tell

| Forge | Containers | ATK-signed | Changed resources in signed / unsigned containers |
| --- | ---: | ---: | --- |
| `DataPC.forge` (base) | 48,705 | 4,172 | 1,775 / 11 — the eleven are the July cloths, written by this repo's own tool |
| `DataPC_patch_01` | 2,440 | 34 | 209 / 2,140 |
| `DataPC_extra_patch_01` | 304 | 24 | 89 / 44 |
| `DataPC_Resources_patch_01` | 2,894 | 1,313 | 9,848 / 1,804 |
| `WorldMap_Bootstrap_Split_patch_01` | 112 | 0 | 0 / 1 |

⚠️ **An unsigned container is not a vanilla container.** ATK's per-container trailer marks what ATK
wrote; the *GRB Mod Manager* rewrites containers without it, and most of this install's mods went in
through the manager. The 2026-09-16 census used the trailer only to say which containers ATK had
written, which still holds; do not read its absence as pristine.

## Method and caveats

- **Tool:** a scratch script that reads every forge entry by index offset, Oodle-decompresses it,
  walks the container with `tools/data_inspect.walk`, and records `sha1(header + payload)` per
  resource and `sha1(entry)` per container. About 42 GB in three minutes with four workers.
- **Pristine copies:** `Backups\DataPC.forge` (Oct 2025, unsigned, same size as ATK's own
  `_backupdatafiles` copy); `Backups\DataPC_patch_01.forge` (**Sept 2023**); `Backups\DataPC_extra_patch_01.forge`
  and `…Bootstrap_Split_patch_01.forge` (Oct 2025); `DataPC_Resources_patch_01.forge` from both
  `Backups\` (Sept 2023) and ATK's `_backupdatafiles` (Oct 2025), unioned. The 2023 patch copy
  predates this install, so some of `DataPC_patch_01`'s 524 "modified" resources could be official
  differences rather than mods; the base-forge diff (Oct 2025 copy) has no such gap. The 23.6 GB base
  `DataPC_Resources.forge` was not hashed; it is byte-for-byte the same size as its backup.
- **Skeleton comparison:** vanilla namesakes indexed by name from `Backups\DataPC.forge`,
  `DataPC_Resources.forge`, the Bootstrap base and the two 2023 patch backups; bones parsed with the
  GRB `Bone` layout (name hash, parent link, local position and rotation).
- **The GRB Mod Manager keeps its own originals** under `_GRBbackups\originals\` — 113 replaced
  entries of `DataPC_patch_01`, 106 of them build tables inside `TEAMMATE_Template`, plus a handful
  of weapon entries — a per-file record of what the manager overwrote.
- Read-only throughout. Nothing was written, repacked or launched.
