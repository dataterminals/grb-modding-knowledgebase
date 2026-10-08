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

> **Community corroboration:** SamiPuma (Tier 1 Imports) reports that the item/gameplay/resource split isn't required — putting everything into `DataPC_extra_patch_01.forge` "should still work." That is exactly what the flat-ID-archive model predicts: any **mounted** forge can host an entry, and the ID resolves regardless. Which filenames get mounted was the untested edge. It is now answered from the executable: an arbitrary new name is not mounted, but any `Data<base>_patch_<N>.forge` is. See [How GRB.exe finds forges](#how-grbexe-finds-forges-verified-from-the-executable-2026-10-04) below.

## Evidence on disk

The base+patch pairing is consistent across the whole install (see [`reference/forge-inventory.md`](../reference/forge-inventory.md)):

- `DataPC.forge` + `DataPC_patch_01.forge`
- `DataPC_Resources.forge` + `DataPC_Resources_patch_01.forge`
- `DataPC_extra.forge` + `DataPC_extra_patch_01.forge`
- each `DataPC_TGT_WorldMap_*_Split.forge` + its `_Split_patch_01.forge`
- API-variant forges: `_dx11` and `_vulkan` siblings (DirectX 11 vs. Vulkan render backends)

The `_patch_01` suffix is a number the engine reads, not a fixed name: GRB.exe finds patch forges with a wildcard and ranks them by that number (see the next section). Ubisoft never shipped a `_patch_02` for GRB. Mods reuse the **`_patch_01`** slot, which is exactly why mods can collide with each other and occasionally with official patches.

## How GRB.exe finds forges (verified from the executable, 2026-10-04)

> **How this is known:** static analysis of `GRB.exe` (build `ChangeList:7793716`, linked 2023-09-11). The work used string extraction, code cross-references, and disassembly of the forge manager with capstone. A second agent re-derived every load-bearing step independently. The exe is wrapped by a commercial protector, but its real code section is plain x64 with a valid exception table, so the trace reaches real code. `GRB_vulkan.exe` carries the same strings and the same patch-scan function. **Nothing was run.** The *mechanism* below is verified from code. What the game then *does* with a given file stays **inferred** until an in-game test. Addresses are RVAs in that build. A game update that ships a new exe moves them.

### Base forges: assembled from parts, checked by exact name

- **There is no list of forge filenames in the exe.** `DataPC`, `GRN_GhostRoom` and `TGT_WorldMap` never appear as literals. Names are composed with `"%sData%s.%sforge"` (fn `0x19ffd0`). The name is the platform string `PC` plus a suffix: none, `_Resources`, `_extra`, `_extra_chr`, a world name taken from game data, or a graphics suffix `_dx11`/`_vulkan`.
- A base forge is opened only if that exact name exists (`GetFileAttributesW`).
- **⇒ A forge with a brand-new name in the game folder (`MyMod.forge`, `DataPC_Mods.forge`) is never opened.** There is no `*.forge` scan of the game folder.

### Patch forges: found by a wildcard, ranked by their number

For every base it opens, the forge manager's `OpenForge` (fn `0x1b4960`, vtable slot `+0xb8`) scans the folder (fn `0x197b50`):

```
FindFirstFileW("*<name>_patch_*.forge")        e.g. "*PC_patch_*.forge" for DataPC.forge
for each hit:  skip "Data", find "_patch_" (any case), read the digits after it as N
               priority = base priority (0) + 1 + N
```

Every opened forge goes into **one manager-wide list**. After each `OpenForge` the whole list is stable-sorted by priority, highest first. The global ID resolver (fn `0x1b29c0`, slot `+0x198`) returns the first forge in that list whose index holds the ID.

| File | Priority |
| --- | ---: |
| `DataPC.forge`, any base | 0 |
| `DataPC_patch_01.forge`, any shipped patch | 2 |
| `DataPC_patch_02.forge` | 3 |
| `DataPC_patch_10.forge` | 11 |

- **The patch chain is open-ended by design.** `_patch_02`, `_patch_2` and `_patch_57` are all found. A higher number outranks a lower one **across all forge sets**, because there is one list. A `_patch_02` of any family outranks every shipped `_patch_01`.
- **Ties are deterministic.** Each newly opened forge is inserted at the front of the list, and the sort is stable. So among equal priorities, **the most recently opened forge wins**. Equal priorities include all shipped `_patch_01`s (2), and `DataPC.forge` together with the WorldMap split bases (0). The order in which the sets are opened was not traced, so which tied forge wins is still unknown.
- **⚠️ The global resolver is not the only lookup.** A set-scoped lookup (fn `0x19f280`, slot `+0xf8`) tests one forge, then its attached patches and split siblings, and ignores priority. An index-scoped read (fn `0x1a2020`, slot `+0x160`) also exists. So "a higher patch wins everywhere" is **inferred**. These scoped lookups are a candidate explanation for the [forge-shadow](#verified-real-ids-are-globally-unique-and-patches-override-by-id-empirical) hang.

### Filename rules for a patch forge (read from the parser)

- **Start with exactly `Data`** (case-sensitive). Whenever `Data` appears anywhere in the name, the parser skips the first four characters. So `datapc_patch_02.forge` or `MyDataPC_patch_02.forge` opens the wrong name and fails.
- **Spell it `_patch_` with both underscores.** The wildcard needs them. `DataPC_Resources_Patch02.forge` is not matched.
- **Text after the number parses** (inferred from the digit loop, which stops at the first non-digit). `DataPC_Resources_patch_05_MyPoncho.forge` reads as N = 5.
- **No `(` anywhere.** The opener cuts the name at the first `(`. `DataPC_patch_01 (2).forge` is found by the scan, but opening it fails. That is one more reason the community's "(2)" unpack trick says to delete that copy before playing.
- **⚠️ Stray copies get mounted.** `DataPC_patch_01 - Copy.forge` or `DataPC_patch_01_backup.forge` left in the game folder matches the wildcard. It is mounted as a live patch at priority 2. Keep backups in a subfolder. Directories are skipped, and `Backups\` is never scanned.

### Other routes, and why they don't help

- **World split forges** are found by `"%s%s%s_*_Split.forge"` filtered by the regex `<name>_[a-zA-Z]+_Split` (fn `0x189350`). This happens only when no exact `Data<name>.forge` exists. A new letters-only `DataPC_TGT_WorldMap_<Letters>_Split.forge` would join the world set as another base (inferred).
- **DLC folders.** Every `dlc_*` folder under the install is enumerated. Inside, `*.forge` files whose stem starts with `PC` and ends in `_dlc` are passed to `OpenForge`. This is the only route by which a forge with a new name could load. Its gating (ownership, the "Downloadable content %ls corrupted" check) is **untraced**. The install has no `dlc_*` folder.
- **Livepatch.** The game probes `%LOCALAPPDATA%\My Games\Ghost Recon Breakpoint\livepatch\Data<name>_livepatch.forge` by exact name. That folder is governed by a hidden manifest, `livePatch.bin` (version 2, changelist 7793716). At startup the game deletes every `*_livepatch.forge` there that a valid manifest does not name. **Not a mod slot.**
- **`workingdir`** is a registered command-line switch. It sets the folder every forge path resolves against, which defaults to the exe's folder. How it is spelled on the command line, and whether the launchers pass it through, were not checked.

### What the forge file must carry

- **Nothing in a forge names itself or marks it as a patch.** The first 1050 bytes are identical in all 27 live forges and 6 backup originals. Base and patch headers differ only in counts and offsets. "Patch-ness" exists only in the filename.
- **Producing the file is solved.** ATK's repack builds every byte from the folder and never reads the original forge. Create Folder `Extracted\<Name>.forge` followed by Repack writes a new `<Name>.forge` (from ATK 1.3.1 source). It writes with `FileMode.Create` and makes no backup, so it overwrites any file of that name.
- **GlobalMetaFile (ID 16)** holds a build tag (`tgt-data/Y2E4.1.0/` in base forges, `Y2E4.5.0/` in patches), build numbers, a GUID, class-type tables, and a family "kind" byte. The kinds are 0 DataPC, 1 Resources, 2 extra, 3 Bootstrap, 4 world regions, 5 GhostRoom, and 6 dx11/vulkan. A patch has its base's kind. `DataPC` and `DataPC_Resources` share one GUID. ATK never creates this sidecar. It copies a `.MetaFile` that is already in the folder. **Community-reported** (Kamzik123, ATK's author, Tier 1 Imports, 2026-03-06): a `_patch_02` "only" needs a different MetaFile, namely its CodeCL/DataCL/SoundCL version values. A renamed copy of a patch folder with an unedited MetaFile hung in an infinite load (ViruS, same day).
- **PrefetchingFileInfos (ID 145)** has one record per entry in the forge, listing the IDs that entry needs prefetched. Its layout is decoded (2026-10-07): an LZO1X-compressed table of `{ID, size, offset}` followed by records of `u16 0 | u16 k | k × {u64 ID, 3 bytes}`. Read any forge's table with [`tools/prefetch_inspect.py`](../tools/prefetch_inspect.py). The first published mod seen shipping its own records copies its donors' vanilla records ([`reference/grbmod-package-format.md`](../reference/grbmod-package-format.md#prefetch-records)). ATK 1.3.1 never regenerates it. The live ATK-repacked patch forges carry hundreds of entries with no record and still boot. Kamzik reports ATK 1.3.5 (2026-07-13) "fully" supports it. In his `_patch_02` test, textures worked but files that needed prefetching crashed.

> **Community-reported runtime evidence:** Kamzik123 reported a resources `_patch_02` working in-game (2025-07-06). He later said you can make a custom resources `_patch_02` to *add* content (2025-09-14). He also said new resources in a `_patch_02` can be driven by BuildTables left in `_patch_01` (2026-03-06). Nobody has published files or logs. Nobody has tested a non-Resources `_patch_02`, a patch for a base that ships without one (`DataPC_dx11`, `GhostRoom`, WorldMap `_dx11`/`_vulkan`), or `_patch_01` against `_patch_02` on the same ID.
>
> **Engine-family precedent:** Ubisoft's depot manifests show official `_patch_02` and higher in Steep, AC Unity, AC Origins, AC Shadows and Skull and Bones. AC Odyssey and AC Mirage mods ship as a standalone `DataPC_patch_02.forge`. No Anvil game is known to load a forge with an arbitrary new name.

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
6. **You can ship your own patch layer (mechanism verified, runtime inferred).** A `Data<base>_patch_<N>.forge` with N ≥ 2 is found by the engine's own scan and outranks every shipped `_patch_01`. It installs by dropping it in, uninstalls by deleting it, and survives an update that replaces Ubisoft's patch forges. Four things it does **not** change:
   - **Entries still override whole.** If a mod's `_patch_02` carries a container that `_patch_01` also has, it replaces the whole container. The DB container is a full copy, so two DB mods still have to be merged into one container ([docs/14](14-ai-and-npc-behaviour.md)).
   - **Shadowed IDs still need every family.** A cloth shadowed in `DataPC` and `Bootstrap_Split` still wants a patch in both families.
   - **The MetaFile ties the forge to a game version** (community-reported). Expect to re-sync it after every official update.
   - **A frozen copy goes stale.** If an update changes a resource the mod overrides, the mod still serves its old copy.

## What's still open

Tracked in [`meta/research-log.md`](../meta/research-log.md):

- **Mechanism decoded, runtime unconfirmed:** peer priority. Override is keyed on the real 64-bit ID (verified above). From the exe, priority is 1 + the patch number, and ties go to the most recently opened forge ([above](#how-grbexe-finds-forges-verified-from-the-executable-2026-10-04)). Still open: the order the sets are opened in, which decides ties between the shipped `_patch_01`s, and whether the set-scoped lookups bypass priority. Needs an in-game A/B test.
- **Supported by design, untested in game:** a patch chain beyond `_patch_01`. The engine scans for any number. The first test is a tiny `DataPC_Resources_patch_02.forge` with one visible texture override, the slot the community reports working.
- **Partly known:** `GlobalMetaFile` and `PrefetchingFileInfos`. Their contents are described above. Still open: which MetaFile fields the engine checks (the CodeCL/DataCL/SoundCL report is from memory, unverified), and what a `PrefetchingFileInfos` must hold so that prefetch-dependent assets load from a new forge.
- **Untraced:** the `dlc_*` route, the only way a forge with a new name could load.
- How the world-map `_Split` forges and `Bootstrap` forge participate (streaming regions vs. global data) — and, per the forge shadow above, **which copy wins when a `_Split` base and `DataPC.forge` hold the same ID** (44/56 cloths do). Both are priority 0, so the exe says the more recently opened one wins in the global resolver. The set open order is untraced, and the set-scoped lookups may answer differently. This is the highest-value shadow question.

Confirming the runtime behaviour of the priority rule is the highest-value open question here: it determines mod load order, conflict resolution, and how a mod manager should lay out patches.
