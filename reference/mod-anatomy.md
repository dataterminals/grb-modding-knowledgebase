# GRB mod anatomy: how real mods are structured & installed

> **Status:** Survey-derived reference — 2026-07-02. Synthesized from an automated structured survey of **18 real mod working folders** in a modder's `Extracted/GRBMods/` (weapons, gear, faces, hair, camo, UI, patches, config-only, and one loose-file utility). It cross-checks cleanly against this repo's already-verified facts (the three-forge model, the `77777` placeholder, the forge container magic). Specific numeric IDs cited are from those particular sample mods. Anything tagged *(inferred)* is not yet byte-verified. Provenance: [`../meta/research-log.md`](../meta/research-log.md) (2026-07-02 entry). Complements [`resource-type-ids.md`](resource-type-ids.md), [`forge-inventory.md`](forge-inventory.md), and [`../examples/case-study-usp-tactical.md`](../examples/case-study-usp-tactical.md).

A working reference for reading, authoring, and installing Ghost Recon: Breakpoint (GRB) mods, grounded in real unpacked mod folders. It explains the on-disk layout of a mod, how folders map to the game's **forge families**, the item-definition vs. resource split, override mechanics, and the repack-based install workflow.

---

## 1. The unpacked working-folder layout & the three-forge model

Almost every GRB mod you download is **not** a drop-in file. It is an **unpacked / decompiled working tree** — a folder of loose records and payloads that must be **repacked into the game's `.forge` archives** before it will load. The folder and file names are the load-bearing metadata: they tell a forge tool (Anvil Toolkit / "ATK") *which forge each piece belongs in* and *what index/ID it takes*.

GRB stores game data across a small number of **forge families**. Mods split their contents into sibling subfolders that mirror those families:

| Forge family | Holds | Typical mod subfolder name(s) | Content |
|---|---|---|---|
| **`DataPC.forge`** | Item / gear **definitions** | `dbcontainer/`, `Main/`, `23_-_TEAMMATE_Template[.data]/` | `.BuildTable`, `.GR_WeaponDBEntry`, `DB*` records |
| **`DataPC_extra[_patch_01].forge`** | Weapon-group / assembly **gameplay data** | `extra/`, `DataPC_extra_patch_01.forge/` | `WG_` weapon-group `.data` |
| **`DataPC_Resources[_patch_01].forge`** | **Meshes, textures, UI icons** | `resources/`, `resource/`, `DataPC_Resources_patch_01[.forge]/` | `.data` mesh/texture blobs, `UI_*` maps |

Key points:

- **Folder name = forge routing hint.** A subfolder literally named `DataPC_Resources_patch_01.forge/` or `Main/` tells the packer which archive to repack the contents into. Some mods use descriptive names (`resources/`, `extra/`, `dbcontainer/`); others use the exact forge filename. Both conventions appear.
- **`.data` is the universal container extension** for a single unpacked forge entry (mesh, texture, UI map, weapon-group, or an extracted BuildTable container). The GRB per-entry forge datafile header magic is **`33 AA FB 57`** (the low 4 bytes of the 8-byte container magic; seen on resource meshes, textures, and patch entries).
- **Numeric `N_-_` prefixes are ordering / slot indices, not asset names.** `0_-_`, `1_-_`, `23_-_` are the toolkit's export/import order (or template family) markers. They are **not** part of the asset's real name and **not** item IDs. (The item ID, when present, is a *different* number — see §4.)
- The three-forge split for a single weapon is shown cleanly by **`USP Tactical + Burris FF3`**, which ships all three: `DataPC_extra_patch_01.forge/` (WG_ defs), `DataPC_patch_01.forge/` (WI_ defs), `DataPC_Resources_patch_01.forge/` (meshes + UI). **`APC9 RepScorpionCQC`** and **`Gazza_MP5A2`** show the same split with `dbcontainer/` + `extra/` + `resources/`.

### Resource naming prefixes (memorize these)

| Prefix | Meaning |
|---|---|
| `WG_` | **W**eapon **G**eometry — visible/in-world weapon mesh |
| `WI_` | **W**eapon **I**nventory — paired inventory / first-person / info variant |
| `TP_` | **T**hird-**P**erson worn mesh (or a teammate-slot item def) |
| `FTP_` | **F**emale / alternate third-person mesh variant |
| `UI_*_Map` | Inventory icon / portrait texture |
| `CP_` | **C**haracter **P**art (e.g. `CP_Wrinkles`, `CP_Patch_*`) |
| `_LOD0` | Highest mesh detail level |
| `_Mip0` | Highest-resolution top texture mip (streamed separately from the base map) |

Meshes very often ship as a **`WG_`/`WI_` pair** (weapons) or a **`TP_`/`FTP_` pair** (worn gear, covering gender/viewmodel variants). Textures often ship as a **base map + `_Mip0` pair** (GRB splits a texture's streaming body from its top mip; the two carry *different* resource IDs — e.g. `Deckard_ATACSWeaponPaintReplacement`'s ArcticTundra base `63552` / Mip0 `65655`).

---

## 2. The BuildTable + resources split, and the `23_-_TEAMMATE_Template` pattern

A gear/clothing/hair mod is conceptually two layers:

1. **Item-definition layer** — a **`.BuildTable`** (binary DB record) that defines the inventory item: its slot, config, and the resource IDs it points at. These go into **`DataPC.forge`**.
2. **Resource layer** — the actual `.data` meshes, textures, and `UI_*` maps. These go into **`DataPC_Resources[_patch_01].forge`**.

`.BuildTable` files are **opaque binary** — they encode references as packed 64-bit forge file IDs and 4-byte record indices, usually with **no readable ASCII asset names** (`FemalePants_buildtables`, `SC_Revamp_PMC_sniper`). So a BuildTable's *target* is often only inferable from its **filename** and its **containing folder's index**, not from bytes inside it.

### The `23_-_TEAMMATE_Template` container

The folder name **`23_-_TEAMMATE_Template`** (sometimes `23_-_TEAMMATE_Template.data`) is a recurring, important marker — a container (template family **#23**) inside `DataPC.forge`. **Despite the "TEAMMATE" name it is NOT teammate-only** (practitioner correction, 2026-07-02): it is the shared **character-customization template** that worn-gear item definitions route through, and it drives **the player's own character model as well as AI teammates**. Modders drop a gear `.BuildTable` here and it applies to the player, not just squadmates — the folder name is misleading. Treat it as "the customization item-def container," not "the teammate mod folder."

Examples routed through `23_-_TEAMMATE_Template`:
- **`CFLIONNESS_JPCVest`** — one `TP_VestMedium_CryeJPC.BuildTable` + gender-paired TP/FTP meshes + UI map.
- **`CFLIONNESS_SkinnyJeansX1`** — `TP_PANT_Metal_Punk.BuildTable` (reskins the vanilla "Metal Punk" pants slot).
- **`Ponytail`** — **11** `.BuildTable` records (`Bun`, `BunForBeanie`, `BunForNVG`, `BunForHelmetGoggles`, …), one per **headgear-compatibility variant**, so the hair clips/hides correctly under each headgear class — plus 3 mesh variants + 1 UI map in `DataPC_Resources_patch_01/`.
- **`FemalePants_buildtables`** — the *minimal* case: a single `1_-_TP_PANT_Fixit.BuildTable`, no resources at all.
- **`SC_Revamp_PMC_sniper`** — 11 BuildTables named by slot + tier (`HeadGears/UpperBody/Tops/Vest/Visuals` × `Mark1–3`), showing teammate templates support **tiered "mark" gear variants**.

A weapon's item-def equivalent is the **`.GR_WeaponDBEntry`**, which appears on disk as an **empty named directory** (e.g. `18133_-_SMG_SCPN-EVO3_CQC.GR_WeaponDBEntry/`) — the marker for a `DataPC.forge` weapon item definition (`APC9 RepScorpionCQC`, `Gazza_MP5A2`).

---

## 3. Mod categories observed & what each touches

| Category | Touches | Example mods | Notes |
|---|---|---|---|
| **Weapon (reskin over vanilla slot)** | All three forges (DataPC item def + DataPC_extra WG + DataPC_Resources meshes/UI) | `APC9 RepScorpionCQC`, `Gazza_MP5A2_VanillaMP5Replacer`, `USP Tactical + Burris FF3` | `GR_WeaponDBEntry` + `WG_`/`WI_` mesh pairs + `UI_` map. Modular sub-parts (Barrel/Magazine/Muzzle/Receiver) mirror GRB's attachment system. |
| **Vest / torso gear** | DataPC item def (often via `23_-_TEAMMATE_Template`) + DataPC_Resources | `CFLIONNESS_JPCVest`, `Crye AVS`, `acostabisonbattlebelt` | `TP_`/`FTP_` worn meshes (often 60–200 MB). Handled as static/rigged mesh — **no `.cloth`/MotionCloth** seen in these vests. |
| **Pants** | DataPC item def + DataPC_Resources | `CFLIONNESS_SkinnyJeansX1`, `FemalePants_buildtables` (def-only), `FemalePants_resources` (mesh-only) | Ships both `TP_`+`FTP_` even for "female" items. |
| **Hair** | DataPC item defs (×N headgear variants) + DataPC_Resources | `Ponytail` | Headgear-compatibility fan-out is the signature. |
| **Face** | DataPC_Resources only | `Better Faces` (`CP_Wrinkles` normal maps) | Pure texture; **zero item-def work**. |
| **Camo / texture** | DataPC_Resources only | `Desert Night Camo` (A-TACS LE), `Deckard_ATACSWeaponPaintReplacement` | Base `DiffuseMap` + `_Mip0` pairs; reuses real vanilla resource IDs. |
| **UI / portrait** | DataPC_Resources only | `Sheva ui` (`UI_FTP_Head_Kunal_Map`) | Single texture swap; `.bak` shows edit-in-place. |
| **Patch / emblem** | DataPC_Resources_patch_01 only | `Devil Gal Dark` (`CP_Patch_Panther`) | 5 entries: Diffuse/Normal/Map + Mip0s. |
| **BuildTable-only (config-layer)** | DataPC.forge only | `Individual Buildtables - Vests`, `SC_Revamp_PMC_sniper` | No art assets; a **dependency-style / config** mod relying on vanilla (or a companion resource mod) to supply meshes. |
| **Resource-only** | DataPC_Resources only | `FemalePants_resources`, `acostabisonbattlebelt` (meshes half of a two-part mod) | The paired item-def forge lives in a companion mod. |
| **Utility (loose-file, NON-forge)** | *No forge at all* | `GRB No-Intro Fix` | See §5 edge cases. |

---

## 4. Override mechanics

GRB mods almost never "add a brand-new inventory slot" cleanly; they **hijack an existing vanilla item/resource** by making the repacked entry carry an ID or name the game already uses. Three override mechanics recur:

**(a) Reuse of real vanilla IDs (in-place override).** The filename is prefixed with a *real existing vanilla resource/item ID*, so repacking overwrites that stock entry.
- `Better Faces`: files prefixed `797/811/812/5587` = the real `CP_Wrinkles` normal-map IDs → direct in-place replacement.
- `Deckard_ATACSWeaponPaintReplacement`: reuses vanilla A-TACS DiffuseMap IDs (`63552–63566`, etc.).
- `Desert Night Camo`: reuses `1547 / 73497 / 73625` (A-TACS LE Diffuse / Mip0 / UI).
- `Crye AVS`: reuses 3-digit vanilla item IDs `805 / 863` (Raid Panther medium vest) + UI map `111664`.
- `APC9 RepScorpionCQC`: reuses ScorpionEVO3 IDs (`18133` DB entry, `33192/33194/…`) to swap an imported APC9/ADP9 mesh onto the vanilla ScorpionEVO3 CQC slot.

**(b) Named replacement (override-by-name).** The `.BuildTable` / resource is *named after* the vanilla item (`TP_VestMedium_CryeJPC`, `TP_PANT_Metal_Punk`, `CP_Patch_Panther`, `SMG_MP5`), so it reuses that item's identity even though the actual mesh has a custom name (e.g. BuildTable `Metal_Punk` but mesh `Lioness_Jean_X1Kneepad`). A name/mesh mismatch is a reliable tell that it's a **reskin**, not an addition.

**(c) Placeholder IDs (new-asset injection, resolved at repack).** Round-number placeholder IDs mark *freshly imported* assets that don't correspond to any vanilla resource; the forge tool assigns real IDs at repack:
- **`77777`** — new mesh/texture resources (`USP Tactical + Burris FF3`: the new HK USP45 + FF3 optic geometry).
- **`99999`** — new attachments/meshes (`APC9`'s `AT_APC9ngal`; `Crye AVS`'s new TP/FTP Tacvest meshes).
- **`9999`** — new config BuildTables (`Crye AVS` CFG; and the whole `Individual Buildtables - Vests` set prefixes every per-vest CFG with `9999_-_`).
- **`1_-_` round-number IDs** — occasionally used for a bulk imported mesh library (`APC9`'s ADP9 set). *(inferred: exact placeholder-ID → real-ID resolution rules are toolkit-specific and not documented in these folders.)*

A single mod frequently **mixes conventions**: reused vanilla IDs on the records that hijack an existing item, plus `77777/99999` placeholders on the new geometry it injects (`USP Tactical + Burris FF3`, `Crye AVS`, `APC9`).

> **Reading `.bak` files:** several resource mods (`Desert Night Camo`, `Sheva ui`) keep `.bak` copies of the original vanilla payload beside the edited one. These are the modder's own **edit-in-place restore points** and confirm a direct-resource-edit workflow.

---

## 5. Install workflow (edit → **REPACK** → deploy)

For every forge-based mod above, install is the same **manual repack** pattern — **none** of these ship a `.fomod`, and most ship no readme at all:

1. Work inside an **unpacked / `Extracted/` working directory** (the mod folder as downloaded *is* that working tree).
2. Edit the loose `.data` / `.BuildTable` / `GR_WeaponDBEntry` records as desired (the mod has already done this; you can further edit).
3. **Repack each subfolder back into its matching forge** with a GRB forge tool (**Anvil Toolkit / ATK**), using the folder→family routing from §1:
   - `dbcontainer/`, `Main/`, `23_-_TEAMMATE_Template/` → **`DataPC.forge`** (or `DataPC_patch_01.forge`)
   - `extra/` → **`DataPC_extra[_patch_01].forge`**
   - `resources/` / `resource/` / `DataPC_Resources_patch_01.forge/` → **`DataPC_Resources[_patch_01].forge`**
4. Drop the repacked forge(s) into the game's Data folder, overriding the base/patch forge.

> ### CRITICAL: append-style / binary forge edits are NOT launch-safe
> You **cannot** simply splice, append, or hex-patch bytes into a packed `.forge` and expect the game to boot. **GRB runs a pre-engine integrity check that fails** on a forge whose structure doesn't match a clean pack (the game dies at the borderless-logo splash, *before* the engine window opens). A modified forge **must be produced by a clean ATK repack** — the tool rebuilds the archive's tables/offsets so the integrity check passes. Hand-appended or naively binary-edited forges will be rejected before the engine even starts. *(This is why the "edit the working folder and repack" loop is mandatory, not optional — verified the hard way, 2026-07-02.)*

Because the target forge is encoded in folder names (not in a manifest), a mod that only names its folder `Main/` or `resources/` **assumes you know** which packed forge those IDs live in; that knowledge comes from the tool's index, not the mod (`Deckard_ATACSWeaponPaintReplacement` explicitly notes this).

---

## 6. Variations & edge cases

- **Packaged / pre-named `.forge` working folders.** Some mods ship folders *named* like the forge itself (`acostabisonbattlebelt_DataPC_Resources_patch_01.forge/` wrapping an inner `DataPC_Resources_patch_01.forge/` of loose `.data`). This is still an **unpacked working directory**, not a ready archive — the inner folder holds the loose members to repack. Watch for **double-nested same-name folders** (`Devil Gal Dark`, `Sheva ui`, `CFLIONNESS_SkinnyJeansX1`) — a packaging quirk to document in install paths.

- **BuildTable-only vs. resource-only *paired* mods.** A complete gear item = one item-def half + one resource half, and these are sometimes **shipped as two separate mods** meant to be installed together: `FemalePants_buildtables` (def only, into `DataPC.forge`) + `FemalePants_resources` (mesh only, into `DataPC_Resources_patch_01`). `acostabisonbattlebelt` is the **resources half only** — it explicitly needs a companion item-def forge to appear in-game. `SC_Revamp_PMC_sniper` is a **config-layer** mod that ships *no* art and depends on vanilla or other resource mods for the meshes.

- **Multi-piece outfit / modular sets.** One "item" can fan out into many records: `Ponytail`'s **11 headgear-compat BuildTables**; `Individual Buildtables - Vests`' **75** files (1 master `48_-_VestsCFG` category config + 74 per-vest CFGs) as a pick-and-choose menu; `acostabisonbattlebelt`'s belt + 5 modular attachment meshes (DumpPouch, FastRopeGloves, Glowstick, Holster, Lanyard) plus a 2 KB `Player_Holster_*_Addon` **config stub** (not geometry).

- **Category-config master records.** BuildTable sets sometimes include a **category master** with a low index ID (`48_-_VestsCFG.BuildTable`, category #48) alongside the individual `9999_-_` item CFGs. *(inferred: the master enables/registers the category the individual CFGs slot into.)*

- **Loose-file (NON-forge) utility mods.** Not everything is a forge. `GRB No-Intro Fix` touches **no forge at all**: GRB ships its intro/logo/warning videos as **loose `.bk2` files** under `…/Ghost Recon Breakpoint/videos/` (with `TRC/<language>/` legal-screen and `TU200–TU410/` title-update subfolders). The mod overwrites them with byte-identical 468-byte black stubs. Its install is a plain **"unpack and overwrite the existing files"** drag-and-drop — no repack, no ATK, and trivially reversible via Steam file verification. This is the canonical example of the **loose-file override class**, distinct from every forge-based mod above.

- **`.cloth` / MotionCloth.** *Not present* in any of these 18 mods — the vests/pants here are handled as static/rigged `TP_`/`FTP_` meshes, not physics cloth. Physics-cloth gear is a separate resource family that lives in `DataPC.forge` (see [`../docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md)); reskinning it is a distinct, harder job than a normal mesh swap.

---

### Quick-reference fingerprints

- **Weapon mod** → `GR_WeaponDBEntry` (empty named dir) + `WG_`/`WI_` mesh pairs + one `UI_*_Map`, split across dbcontainer/extra/resources.
- **Gear/clothing/hair mod** → `.BuildTable` in `23_-_TEAMMATE_Template` (item def) + `TP_`/`FTP_` meshes + `UI_*_Map` in `DataPC_Resources_patch_01`.
- **Texture/camo/face/patch/UI mod** → resource-only, base map + `_Mip0` pairs, real vanilla IDs as filename prefixes, no BuildTable.
- **Config-only mod** → all `.BuildTable`, no `.data` meshes; often `9999_-_`-prefixed; depends on existing art.
- **Utility mod** → loose files (e.g. `.bk2`) overwriting non-forge game files; drag-and-drop install.
