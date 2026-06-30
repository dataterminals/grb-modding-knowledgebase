# Research log

The provenance and verification ledger for this knowledgebase. **This is the most important file for anyone (human or AI) continuing the work**: it records what was actually observed vs. inferred, the environment it came from, and the open questions worth chasing next. Append, don't rewrite history.

---

## Entry — 2026-06-30 — Initial establishment

### Environment snapshot
- **Machine:** Windows 11 Pro researcher workstation (user `sylvi`, GitHub `dataterminals`).
- **Game:** GRB install at `H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint` (Steam). Forges patched to current as of this date (`DataPC_Resources_patch_01.forge` dated 2026-01-15).
- **ATK:** `AnvilToolkit_Release_v1.3.1` from `C:\Users\sylvi\Downloads\AnvilToolkit_Release_v1.3.1-16-1-3-1-1753733025.zip` (only copy on machine; not installed/extracted elsewhere). Extracted to a scratchpad for inspection.
- **Mod corpus:** `…\Ghost Recon Breakpoint\Extracted\GRBMods\` — 150+ community mod working folders.
- **Tooling:** `gh` 2.89.0 (authed `dataterminals`, `repo` scope), git 2.53.0. Repo created at `H:\Github Repositories\grb-modding-knowledgebase`.

### How this knowledge was gathered (methodology)
1. Directory listings of the GRB install and `Extracted\` tree (sizes, names, structure).
2. Read ATK's bundled `README.txt` (full changelog 1.0.0 → 1.3.1) — primary source for capabilities and GRB-specific behaviors.
3. Read ATK's `AnvilToolkit.dll.config` (default settings) and `Libs/` listing (dependency/codec stack).
4. Hex-dumped real files: `DataPC_patch_01.forge` header; a `.BuildTable` resource.
5. Inspected representative mod folders: `Sheva_resources`, `Sheva_buildtables`, `USP Tactical + Burris FF3`.

### VERIFIED facts (directly observed this session)
- Forge magic string = ASCII **`scimitar`** at offset 0; version field = **27** (`0x1B`), little-endian, 64-bit offsets.
- Forges come in **base + `_patch_01` pairs** across the whole install (verified file list + sizes — see [`reference/forge-inventory.md`](../reference/forge-inventory.md)).
- Unpacked forge entries are named **`<decimalFileID>_-_<Name>.data`**.
- A **`.data` is a nested container**: observed `23_-_TEAMMATE_Template.data\295_-_Head_Hisp_Kunal.BuildTable`.
- **BuildTable** is a binary object graph with recurring 8-byte (64-bit) file references.
- The **three-forge mod structure** is real: `USP Tactical + Burris FF3` ships `DataPC_patch_01` (WI defs), `DataPC_extra_patch_01` (WG defs), `DataPC_Resources_patch_01` (meshes + UI), with exact IDs/sizes recorded in the [case study](../examples/case-study-usp-tactical.md).
- **`77777`** is used as a shared placeholder file ID for all new mesh resources in that mod.
- **LOD0–3** (mesh) and **Mip0–N** (texture) suffixes; hair **`For…` headgear variants** each with full LOD sets; face sub-meshes (`eyebrow`/`eyeShadow`/`eyelashes`); weapon component split (`Receiver`/`Barrel`/`Magazine`/`Muzzle`).
- ATK capabilities & GRB support (from its own README): glTF/GLB mesh import-export, DDS texture replace, XML export/import for BuildTables/EntityBuilder/Materials/TextureSet/LocalizationPackage/PrefetchingFileInfos, Oodle + LZMA/LZ4/Zstd/LZO codecs, DirectXTex DDS, HelixToolkit 3D viewer, LibGit2Sharp.
- ATK is **GUI-driven** (.NET 9 / WPF); `EnableCommands` is an experimental, off-by-default console feature, **not** a public CLI/automation API.
- GRB data files historically serialized **uncompressed**; compression later became a toggle (`EnableCompression` ships `True`).
- PC GRB textures are **not swizzled** (`UnswizzleTextures = False`).
- `oo2core_7_win64.dll` + `compressed_oodle_compression_state.bin` present in install → **Oodle** is the resource codec.

### INFERRED / hypothesized (reasonable, NOT yet confirmed)
- Prefix expansions: `TP_`=Third-Person, `FTP_`=Face/Female-Third-Person, `WG_`=Weapon-Gameplay, `WI_`=Weapon-Item, `UI_`=User-Interface, `HDG`=Handgun, `ENV-`=Environment. *(Patterns verified; the letter expansions are educated guesses.)*
- Game load model: forges mount into a **single ID-keyed index**; **patches override base by ID**. Strongly implied by the mod mechanism, but the **exact priority rule** is unconfirmed.
- Base GRB resource entries are **Oodle-compressed** (indirect evidence only).
- `WG_` = world model vs `WI_` = inventory/preview model (consistent with the USP mod, not proven general).

### OPEN QUESTIONS (highest-value first)
1. **Forge index/priority rule** — when a file ID exists in multiple mounted forges, what determines the winner? (Filename order? a manifest? newest mount?) This governs mod load order and conflict resolution. *(Best path: read ATK's forge mount/reader code, or test empirically with two patches.)*
2. **Full forge binary layout** past offset `0x0D` — table offsets, counts, index-record field layout, per-entry compression descriptor. *(Best path: ATK's `AnvilToolkit.dll` forge reader; or QuickBMS/community Anvil forge specs.)*
3. **The `77777` resolution mechanism** — how duplicate placeholder IDs become real references at repack/load. Does ATK reassign? Does the BuildTable resolve by name? Does the game tolerate dupes in patch context?
4. **Combining mods** — the correct procedure to merge multiple mods that each write `DataPC_Resources_patch_01.forge` (entry-level merge; conflict detection on shared IDs). Is there a community tool/mod manager?
5. **New content vs. replacement** — exact steps + ID minting (Hash Converter) to add a genuinely new item rather than hijack an existing slot.
6. **GlobalMetaFile / PrefetchingFileInfos** — schemas, and whether a mod must update them for new content (vs. pure replacement).
7. **LOD fallback** — does the engine fall back to base LODs when a patch supplies only `LOD0` (as the USP mod does)? Visible at distance?
8. **Patch chain** — does GRB support `_patch_02+`, and how does numbering affect priority?
9. **Audio modding** — `sounddata\`, `.tbf` sound blobs: completely uncharacterized here.
10. **World-map `_Split` / `Bootstrap` forges** — role in streaming; are they ever mod targets?

### Suggested next steps for a future session
- Decompile / inspect `AnvilToolkit.dll` (it's .NET — ILSpy/dnSpy/`monodis`) to extract the **exact forge + mesh + texture binary schemas** and the mount/priority logic. This single step would convert most "inferred" items to "verified."
- Add a worked **texture-only** case study and a **BuildTable-only** case study to complement the USP weapon one.
- Capture screenshots / a walkthrough of an actual ATK session (Game Explorer, Mesh Viewer, Texture Viewer) into `assets/`.
- Confirm prefix expansions with the Tier 1 Imports community and update [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md).

---

## Entry — 2026-06-30 — Decompiled ATK; forge format verified; `.cloth` cracked; Sami's feedback

### What I did
- Decompiled `AnvilToolkit.dll` v1.3.1 with **`ilspycmd`** (`ilspycmd -p -o <dir> AnvilToolkit.dll`; .NET 8 SDK, ilspycmd already installed at `C:\Users\sylvi\.dotnet\tools`). 1119 classes; full project source dumped to scratchpad.
- Read the forge container code (`ForgeFile`, `ForgeEntry`, `DataFile`) and the entire `MotionCloth` namespace.
- Incorporated community feedback from **SamiPuma (Tier 1 Imports)** relayed via the user, plus reception from Ms. Deni.

### VERIFIED (new — promoted from inferred)
- **Forge header (v27) layout** confirmed from `ForgeFile.Serialize27/Deserialize27`: `scimitar\0`, uint32 version (GRB=27; Origins/Odyssey=28; Mirage/Valhalla=29; Ezio/AC1=25), int64 HeaderSize=1050, constants, EntriesCount, FileSetCount, FirstFileSetOffset=1094. Entries split into **FileSets of ≤5000**. Details in [`docs/02-forge-file-format.md`](../docs/02-forge-file-format.md).
- **`ForgeEntry` record:** `{Offset int64, ID uint64, LengthOnDisk int32}` (192-byte record, 188 for old games) + a metadata table (`UMACHash`, `EngineVersion`, **`Extension`=resource-type id**, `Parent`, `TimeStamp`, `Name` padded to 127, `MetaFileKey`, `IsHidden`). **An entry is identified by ID alone — nothing binds it to a forge.** This settles the "split" question below.
- **GRB cloth = MotionCloth.** `ClothPackage` (int count + length-prefixed `MotionBody` blobs) → `MotionBody` (sections to end-of-stream) → **TLV sections**: `uint16 TypeID` + `uint16 0xECD7(60631)` + `int32 sizeInclHeader` + payload. Unknown sections preserved verbatim. Full section map: [`reference/cloth-section-types.md`](../reference/cloth-section-types.md); format: [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md).
- **Cloth tunables** (`ClothProperties`, section 4357): Gravity (def 0,0,−10), Damping (0.05), Friction (0.01), MaxSpeed (1000), tearing, stiffness, wind, clustering, strips-untwisting, etc., all round-tripping to **XML**. Fields **truncate per game** (Unity/Syndicate write fewer). `ClothDefinition` (4356) = feature-flag bank that must agree with present sections.

### Questions ANSWERED
- ✅ Forge header & entry binary layout (was open Q2 / doc-02 Qs 1–2).
- ✅ "Is the three-forge split required?" — **No.** Convention, not requirement; the engine merges mounted forges by ID. (Sami was right.) Docs [`05`](../docs/05-three-forge-model.md) and [`06`](../docs/06-game-load-and-reassembly.md) updated.
- ✅ `.cloth` overall structure and tunable parameters (was the user's headline goal).

### Questions OPENED / still open
- Cloth **mesh/skeleton binding** (`ClothPropertiesMeshMappings` 4395 + `ClothEditorDataClothID` 4658) — how a cloth body attaches to a garment + bones. **Top cloth priority next.**
- Reliable **new-cloth authoring** path (SoftBody `ClothGenerationSettings` vs. transplanting an existing cloth).
- The **`Extension` (resource-type id) → type** table, incl. which id = ClothPackage. (`DataFile` + a file-type registry is the next read.)
- Per-`.data` **compression descriptor** layout (read `DataFile`).
- Still open from before: exact forge **mount priority** rule; whether a *new* (non-`DataPC*`) forge filename auto-mounts; patch chain beyond `_patch_01`.
- Empirically validate XML-tuned `ClothProperties` in-game.

### Reception (community)
Repo was shared in Tier 1 Imports. Ms. Deni highlighted the USP "perfect mod" case study and the "three-forge model"; SamiPuma flagged the split-not-required nuance (now incorporated) and asked specifically about `.cloth` files — which became this session's focus.

---

> **Template for future entries:**
> ```
> ## Entry — YYYY-MM-DD — <topic>
> ### What I did
> ### VERIFIED (new)
> ### INFERRED (new)
> ### Questions answered / opened
> ```
