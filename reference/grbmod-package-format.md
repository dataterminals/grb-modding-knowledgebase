# `grbmod` packages — anatomy of *SCUBA CoD* (Nexus 2164)

A **new** packaging format for GRB mods, read from one real package: **SCUBA CoD 1.0.0** by
fox77x ([Nexus 2164](https://www.nexusmods.com/ghostreconbreakpoint/mods/2164), file built
2026-10-03). The package adds nine new appearance items without replacing any vanilla item. It does not ship
replaced copies of the big shared containers (`TEAMMATE_Template`, the CharacterSmith database,
Game Bootstrap Settings). It ships **ops**: "insert these references after this one in that list".
A manager applies them to whatever the install already holds, so two packages can add to the same
table without overwriting each other.

> **Scope.** Everything below was read from the package's bytes and checked against a live install
> (pre-2026-09-29-update build, `D:\SteamLibrary\…\Ghost Recon Breakpoint`) on 2026-10-07. It was
> **not installed, repacked or run.** The Nexus page could not be read: the in-app browser stopped
> at a Cloudflare check and plain fetches got HTTP 403. So the author's description and stated
> requirements are **not known**. The format is read by **GRB Mod Manager 1.15.7** (Nexus 1602,
> built 2026-10-06), whose `package.json` names its author as **Fox77x**, the same author as this package.
> Its code was read, not run: [below](#how-grb-mod-manager-1157-applies-it). The 1.0.6 manager
> installed here has no code for the format. Provenance:
> [`../meta/research-log.md`](../meta/research-log.md), entries 2026-10-07.

## Package layout

```
grbmod.json                                   manifest
forge/<Forge>.forge/<ID>_-_<Name>.data        whole new forge entries, one folder per forge
forge/DataPC_patch_01.forge/Extracted/
    23_-_TEAMMATE_Template.data/<N>_-_<Name>.BuildTable          new resources to append
    1_-_DBContainerEntry_0X104634F921.data/<N>_-_<Name>.<Type>    into those containers
records/records.json                          the ops
records/bin/{rows,dicts,groups,prefetch}/*.bin   binary payloads the ops point at
```

Unlike ATK's unpacked folders, the number before `_-_` in the `forge/` folders **is** the real
64-bit entry ID, written in decimal. Under `Extracted/` it is a placeholder (`90001…`), and the real
ID is the resource's own ClassID.

`grbmod.json` (verbatim keys): `formatVersion` 1, `id` `fox77x.scuba`, `name`, `version`,
`author`, `description`, `records` → `records/records.json`.

## The ops (`records/records.json`)

`formatVersion` 1, `owner` = the package id, then **290 ops**. Every op names the user-facing
`item` it belongs to (`"SCUBA CoD (Helmet)"`), a `forge`, and usually an `entry` + `record`
(both 64-bit IDs in hex) and a `list`. Ordered inserts carry `at: {after: <ID or tag>}`.

| op / list | target (resolved against the live install) | count | what it adds |
| --- | --- | ---: | --- |
| `list_add` `subtables` | BuildTables in `TEAMMATE_Template` (`Pants`, `Shoes`, `VestsCFG`, `PLAYER_headCFG`, 28 `Hats_for…` tables, …) and the `TEAMMATE_Template` EntityBuilder itself | 59 | references to the new BuildTables |
| `list_add` `buildrows` | the same slot tables | 40 | `BuildRow` objects (`records/bin/rows/<table>_<tag>.bin`) |
| `list_add` `possibletags` | `PLAYER_Custo`, `PLAYER_UppBodyCFG`, `PLAYER_LowBodyCFG`, `PLAYER_headCFG`, the EntityBuilder | 12 | the new BuildTags, per named row (`rows: [...]`) |
| `list_add` `root_refs` | `DBContainerEntry_0X104634F921` (the CharacterSmith database) | 9 | the new `CharacterSmithEntry` + `DBCharactersmithDataUIConfig` records |
| `list_add` `menu_entries` / `menu_stubs` | the `CharacterSmithEntryContainer` categories `TOPS`, `PANTS`, `VESTS`, `SHOES`, `GLASSES`, `FACE MASKS`, `HEAD PROTECTION` | 9 + 9 | the items' places in the customization menu |
| `list_add` `boot_dicts` / `boot_groups` | **`TagDictionnaries`** (record `0xBD6`, Ubisoft's spelling) in **Game Bootstrap Settings** (entry `0x800`) | 9 + 6 | new `TagDictionnary` objects and tag groups |
| `list_add` `boot_dict_tags` / `boot_group_tags` | existing vanilla `TagDictionnary` objects / tag groups there | 40 + 43 | the new tags, registered in the dictionaries that already exist |
| `string_add` | `LocalizationPackage_English(US)` (`0xA67D037EDA`) | 9 | display names, keys `0x70000021…`, e.g. `SCUBA CoD (Top)` |
| `prefetch_add` | each forge's **PrefetchingFileInfos** (ID 145) | 45 | one prefetch record per new entry — see [below](#prefetch-records) |

> **Verified** — all 51 targeted records exist in Ubisoft's own 2023 `DataPC_patch_01`
> (`Backups\`), as do all 38 tag dictionaries and all 20 `after:` anchors. The package
> depends on no other mod. All 53 resources under `Extracted/` are reachable: 35 directly from an
> op, the other 18 (`TP_Helmet_ScubaHelmet_*_CFG`, `TP_Vest_ScubaVest_CFG`) from the build rows
> the ops insert (one helmet config per headgear context: balaclava, goggles, each gas mask, …).
> Type names: `TagDictionnaries` `0xFFC5A970`, `TagDictionnary` `0x0196529F`,
> `TagDescriptor` `0xA31AA51D`, `BuildRow` `0x348B28D6`, `BuildTag` `0xB332698E`,
> `BuildTags` `0x11BD5345`, `CharacterSmithEntryContainer` `0x4CD967BE`, `DBContainerEntry`
> `0x5768183B`, `TextureMapSpec` `0x989DC6B2` (the UI `…_MapDesc`), `LODDescriptor`
> `0xA360319A`. All of these are CRC32s, resolved through ATK's name dictionary.
>
> **Not resolved:** the 57 new tag hashes are not CRC32s of the obvious names (`TopsScubaTop`,
> `tag_TopsScubaTop`, `ScubaTop`, …).

**Why some items are `.bin` files.** An op's JSON can carry a reference inline (an ID, a tag
hash). A new *object* ships as the bytes the game's serializer writes, which the manager can
splice in without a schema for each class:

| folder | holds (classes resolved by CRC32) |
| --- | --- |
| `rows/<table>_<row tag>.bin` | one `BuildRow` tree: `BuildRow` → `BuildTag` → `BuildTags` → n × `BuildTag` |
| `dicts/<ID>.bin` | a `TagDescriptor` for a new `TagDictionnary` |
| `groups/<tag>.bin` | `TagGroupDescriptor` → `BuildTags` → `BuildTag` |
| `prefetch/<forge>_<owner>.bin` | one prefetch record ([below](#prefetch-records)) |

⚠️ **Each object carries a container-local number** (the `0xF800xxxx` IDs: `0x3F0`–`0x3F9` in
the `Pants` row). 39 of the 40 row files use numbers above every one their target table already
has. **The `GlassGOGGLES` row does not.** It uses `0x51`–`0x56`, and vanilla `GlassGOGGLES`
already has `0x51` (a `RowSelector`) and `0x52` (a `BuildTags`), in both the 2023 pristine patch
and this install. **The manager renumbers:** 1.15.7's `records_tmpl.add` re-sequences a table's
object numbers (`_reseq`) after inserting rows, so the file's numbers are placeholders. It refuses
a table whose numbering is not already in sequence ("refusing to renumber them").

⚠️ **Entry IDs can drift in a modded install, and the manager does not follow them.** The ops
address `TEAMMATE_Template` as entry `0x165C84D83A1` in `DataPC_patch_01`. That is where
Ubisoft's 2023 patch keeps it. In *this* install, `DataPC_patch_01` has no entry with that ID.
`TEAMMATE_Template` sits in an 8.4 MB container keyed `0x19D30A1CAEC`, whose first resource is
`OUT_RIFLEMAN`, with the EntityBuilder `0x165C84D83A1` inside it. 1.15.7 looks an op's `entry` up
strictly by forge-entry ID: `Entries.get` raises "has no entry" when the ID is not in the forge's
index, with no fallback (disassembled). On this install the package would be refused before
anything is written. The manager's message blames the game version: "DataPC_patch_01.forge
doesn't have a game record this mod adds to (made for another game version?)". The real cause is
the drifted ID.

## What installing it leaves on disk

The ops are a recipe; the game only reads forges. So the end state is ordinary forge bytes. For
this package (sizes from this install):

| forge | new entries | existing entries rewritten |
| --- | --- | --- |
| `DataPC_patch_01` | 10 (9 LODSelectors, the rig) | `TEAMMATE_Template` (8.4 MB: +35 resources, 42 tables grow), `DBContainerEntry_0X104634F921` (57.7 MB: +18 resources, 8 records grow), Game Bootstrap Settings (33.3 MB: `TagDictionnaries` grows), `LocalizationPackage_English(US)` (0.4 MB: +9 strings), PrefetchingFileInfos (+9) |
| `DataPC_Resources_patch_01` | 18 (9 mesh containers, ~191 MB; 9 UI icons) | PrefetchingFileInfos (+18) |
| `DataPC_extra_patch_01` | 9 (UI `TextureMapSpec`s) | PrefetchingFileInfos (+9) |
| `DataPC_TGT_WorldMap_Bootstrap_Split_patch_01` | 9 (the same LODSelectors) | PrefetchingFileInfos (+9) |

- **Nothing vanilla is overridden by ID.** All 46 new entries use new IDs. The donor items,
  including the hydration-pack rig whose blob was edited, are untouched; the edit lives in a copy.
- **The shared containers are rewritten whole.** A container is one compressed entry, so
  adding one row means re-serializing and recompressing all of it. The ops say only lists grow.
  That every existing record keeps its bytes is what the ops promise, not something checked
  here.
- **The rig gets no prefetch record** (45 records for 46 new entries). Vanilla forges already boot
  with entries that have none (2026-10-04 entry).
- **It stays until something rewrites those four forges.** Possible causes:
  - a manager remove or disable, which takes the ops out from the per-mod journal (below);
  - a game update or Steam file verification, which restores vanilla and drops every mod;
  - an **ATK repack.** ATK rebuilds the whole forge from `Extracted\`, and each unpacked container
    from its nested folder, without reading the forge (2026-10-04 entry;
    [`../tools/db_patch.py`](../tools/db_patch.py), step 1). 1.15.7 writes record edits **only
    into the forge, never into `Extracted\`**. So the next ATK repack of that forge silently
    drops them: rows, menu entries, tags, strings and prefetch records. The page and whole-entry
    files the manager placed in `Extracted\` survive. What the game then does with menu entries
    whose rows are gone is untested.

  **Mixed with ATK repacks or the 1.0.6 workflow:**
  - Through 1.15.7 alone, order is handled. After any repack of a forge it re-applies every other
    enabled package's ops on it (`records_apply --reapply`). So a whole-table mod (this install has
    *Individual Buildtables – Helmets* shipping `Hats_forREGULAR` and `Hats_forGOGGLES`, and
    *– Vests* shipping `VestsCFG`) no longer wipes a package's rows when the manager installs it.
  - Outside it, nothing re-applies. An ATK repack drops the edits as above. 1.0.6's uninstall,
    which restores a file's "ownership-aware" original, also predates them.
  - 1.15.7 notices afterwards. It keeps each forge's SHA-1 and size after every write. A forge that
    changed outside it makes every later write or restore stop with "Your game files changed since
    the manager last touched them … remove them from the list and add them again". The exception
    is an install into a forge no other managed mod uses, which it takes as a new start.

  ATK's `Backups\` hold 2023 vanilla copies, not a pre-install snapshot (2026-09-23 entry).
- **Unknown:** what a save that has a character wearing one of these items does if the mod is
  later removed.

## What a brand-new appearance item needs (the recipe this package implies)

> **Inferred from one package**, which shipped all of these. Whether each layer is
> *required* has not been tested by leaving one out. Every layer matches a vanilla pattern that
> exists in the install.

| layer | forge | this package ships |
| --- | --- | --- |
| Mesh + its textures + material, one container | `DataPC_Resources_patch_01` | `<Item>_LOD0.data`: `Mesh`, `DiffuseMap` / `NormalMap` / `Mask1Map` `TextureMap`s, `TextureSet`, `Material` |
| UI icon | `DataPC_Resources_patch_01` | `UI_<SLOT>_<Item>_Map` `TextureMap` |
| UI icon descriptor | `DataPC_extra_patch_01` | `UI_<SLOT>_<Item>_MapDesc` (`TextureMapSpec`) |
| LOD selector | `DataPC_patch_01` **and** `DataPC_TGT_WorldMap_Bootstrap_Split_patch_01` | the same bytes in both (the [forge shadow](../docs/06-game-load-and-reassembly.md): the vanilla donors live in `DataPC` *and* the Bootstrap base) |
| Optional rig | `DataPC_patch_01` | `BP_Scuba_TubeRig_P3` `Skeleton` (see [below](#the-rig-a-vanilla-hose-with-two-edited-physics-values)) |
| Item BuildTables | `TEAMMATE_Template` | `TP_<Slot>_<Item>` + `tag_<Slot><Item>` (+ per-context `_CFG` tables for helmets/vests) |
| Hook into slot tables | `TEAMMATE_Template` | `subtables` + `buildrows` + `possibletags` |
| Customization-menu entry | `DBContainerEntry_0X104634F921` | `CharacterSmithEntry` + `DBCharactersmithDataUIConfig`, `root_refs`, `menu_entries` / `menu_stubs` |
| Tag registration | Game Bootstrap Settings → `TagDictionnaries` | new dictionaries/groups + tags added to existing ones |
| Display name | `LocalizationPackage_English(US)` | one string per item |
| Prefetch records | PFI of every forge that gained an entry | one per new entry |

The package was built by cloning existing items: every new entry starts as a vanilla donor.

| new item | LOD1–LOD4 borrowed from (vanilla, unmodified IDs) | other donor |
| --- | --- | --- |
| Top | `TP_Top_ScubaDiver` | |
| Pants | `TP_Pants_ScubaDiver` | |
| Hood, Hood + Net | `TP_Balaclava_511-Nomad` | |
| Helmet | `TP_Helmet_OpsCoreFastXP` | |
| Goggles | `TP_Goggles_Scuba_Diving` / `…_Mask_LOD4` | |
| Vest | `TP_Tacvest_511_PlateCarrier` | rig: `BP_TacTailor_HydrAdvPack_MEDIUMVEST` |
| Boots, Fins | `TP_Shoes_RangerBoots` (LOD1–3) | |

**Verified:** each of the nine `LODSelector`s is its donor's vanilla `LODSelector` (from
`DataPC.forge`) **byte for byte except two IDs**: its own (payload offset 0) and the main-mesh
pointer at offset 308, now the new `…_LOD0` (own ID `+1`). The LOD slots, and so the donor's
LOD1–4 meshes and switch distances, are untouched. Each mod LOD0 container bundles its textures
inline as resources: 22,369,772 B per map on the top. That fits 4096² at one byte per pixel with a full mip
chain *(inferred)*. Vanilla ships separate `…_Mip0` / `…_Mip1` entries instead.

**ID namespaces** chosen by the author: `0x1F01C1B02x0` LODSelectors with `…x1` meshes (one
`0x10` step per item); `0xC0DE…` textures, materials and the rig; `0x0FEEDBEEF…` UI, BuildTables,
DB records, tag dictionaries. None of the package's 140 new IDs collides with any of the 385,408
IDs in this install.

## The rig: a vanilla hose with two edited physics values

`BP_Scuba_TubeRig_P3` (`0xC0DE5370001`), assigned in `TP_Vest_ScubaVest`'s BuildTable, is
**vanilla `BP_TacTailor_HydrAdvPack_MEDIUMVEST` byte for byte except 8 bytes in three places**
(diffed against the pristine `Backups\DataPC.forge`):

1. the skeleton's own ID (payload offset 0);
2. and 3. **two floats inside the 48,525-byte Reflex3 blob**, at blob offsets 46,574 and 46,960.

Decoded with [`../tools/reflex3.py`](../tools/reflex3.py), the change is **`p3` 0 → 0.5 on
physics records 0 and 1**: the two-bone chain `276e5795 → 3678b950` under `7dcd5e11`. It is the rig's
one unpaired chain. The other two chains sit mirror-image at ±z, so this one is the likeliest
drinking hose *(inferred; bone names do not resolve)*. Swing limits, mass, gravity and the matrices are untouched.

`p3` is the physics parameter [`skeleton-reflex3-physics.md`](skeleton-reflex3-physics.md) lists
as **unresolved** ("swing damping or centre of mass"). **0.5 is not among its vanilla values**
(0, 1.0, 0.6, 0.8, 0.95, 0.98), so it was set by hand or by a tool, not copied. This is the first
published mod seen to **change a Reflex3 blob**. The installed mods carry blobs through unchanged.
Whether it loads in game, and what 0.5 does to the hose, is **community territory, not verified
here**.

## Prefetch records

Each `prefetch_add` ships one record in the PrefetchingFileInfos record layout, decoded
2026-10-07 ([`../tools/prefetch_inspect.py`](../tools/prefetch_inspect.py)):

```
record := u16 0 | u16 k | k x { u64 ID | 3 bytes (01 00 00 on every gear record) }
```

Of the 45: **27 are byte-identical to the donor's vanilla record**. The LODSelector's record
lists the donor's LOD1–4 and the LOD0 mesh's record lists the donor's textures (e.g. the new top
mesh prefetches `TP_Top_ScubaDiver`'s three maps plus `CHR_Bandages` and two `LIB_Cloth_Bandages`
maps). **9 are empty** (the UI icons, as in vanilla). **9 are new**, each MapDesc → its own new
icon, in the vanilla pattern (`UI_TP_Top_ScubaDiver_MapDesc` → `UI_TP_Top_ScubaDiver_Map`). The
mod's own textures are never listed: they sit inside the mesh's container. The new records carry
the donor's stale lists, which cost extra preloading but load nothing missing *(inferred)*.

## How GRB Mod Manager 1.15.7 applies it

Read from the release zip (`GRB Mod Manager 1.15.7 1602 1.15.7 2026-10-06T02-30Z`), **not run**.
The JavaScript (`resources/app.asar`: `main.js`, `records.js`, `grbpkg.js`) is plain source. The
Python tools ship only as CPython **3.14** `.pyc` under `app.asar.unpacked/tools/repack/`, with
docstrings stripped. They were read through a small marshal reader and an opcode table rebuilt
from the bundled `_opcode_metadata.pyc` (method in the research log).

- **It repacks by itself.** A bundled embeddable Python runs `forge_unpack`, `container_pack`,
  `forge_pack`, `manager_repack` and `records_apply` (plus `records_{tmpl,db,boot,strings,prefetch,spec}`).
  Auto-repack is on by default ("no AnvilToolkit step is needed"). Only `*_patch_*` forges are ever
  rewritten, never a base forge.
- **Containers are rebuilt from the forge, not the folder.** A container a mod adds pages to is
  "rebuilt from its packed bytes with only these pages changed". That is the opposite of ATK.
- **Record edits.**
  1. `records_apply` checks every op against the current forge first, a dry run with no write.
  2. It writes the changed entries plus a **journal** (the entries' bytes from before) to
     `%APPDATA%\…\records\<mod>\<forge>\`.
  3. It packs them into the forge, verifies the result, and swaps it in atomically.
  4. Remove or disable replays the journal. The ops come out while the mod's pages are still in.

  Duplicates are refused ("already in the table (another mod?)", "a row already lists tag",
  "the game's English text already has key", "another mod already gave a prefetch entry"). After
  any forge rebuild, every other enabled package's ops on that forge are re-applied.
- **Backups:** `<game>\_GRBbackups\forges\` holds a permanent `<forge>.pristine.bak` (the forge as it
  was before the manager first wrote it, which on a modded install is not vanilla) plus the 2
  newest rolling copies, all SHA-1-verified. Before writing, it refuses unless the disk has, per
  forge, 2× its size the first time (1× after) plus what the rebuild adds, plus the largest
  forge once more, plus 256 MiB. For an operation that first touches the 36.9 GB
  `Resources_patch_01`, that is about 111 GB (this package's four forges: about 115 GB). The
  steady state is three copies of that forge, about 111 GB.
- **The format is wider than this package uses** (`grbpkg.js`): DLL/ASI `plugins` loaded through
  the manager's own `dinput8.dll` loader, `.ini` `config`, `requires` / `conflicts` between mod
  IDs, `options/` folders, a `dataFolder` under `grb_mods`, `keepOnUpdate`, and `overlayHost`.
  Plugins run native code in the game process.
- First start copies a legacy data folder (`GRB-Mod-Manager`, `GRB Mod Manager`, …) into its own,
  so a 1.0.6 mod list carries over.

## Verified / inferred / open

- **Verified:** the layout, ops, targets, donors, the rig diff, the prefetch layout, ID ranges
  above. Read from the package and the install with the repo's tools plus throwaway scripts. The
  1.15.7 behaviour above is read from its code; none of it was run.
- **Inferred:** that each layer of the recipe is needed; that the format exists so packages can be
  re-applied after a game update replaces the `_patch_01` forges (the 2026-09-29 update did
  exactly that); that the edited chain is the hose.
- **Open:** what the 3-byte tail of a prefetch item and the 57 tag names mean; what `p3` does;
  how common a drifted `TEAMMATE_Template` entry ID is in modded installs, and what re-keyed it here.
