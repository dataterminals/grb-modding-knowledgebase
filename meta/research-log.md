# Research log

The provenance and verification ledger for this knowledgebase. **This is the most important file for anyone (human or AI) continuing the work**: it records what was actually observed vs. inferred, the environment it came from, and the open questions worth chasing next. Append, don't rewrite history.

---

## Entry — 2026-06-30 — Initial establishment

### Environment snapshot
- **Machine:** Windows 11 Pro researcher workstation (user `sylvi`, GitHub `dataterminals`).
- **Game:** GRB install at `H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint` (Steam). Forges patched to current as of this date (`DataPC_Resources_patch_01.forge` dated 2026-01-15).
- **ATK:** `AnvilToolkit_Release_v1.3.1` from `C:\Users\user\Downloads\AnvilToolkit_Release_v1.3.1-16-1-3-1-1753733025.zip` (only copy on machine; not installed/extracted elsewhere). Extracted to a scratchpad for inspection.
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
- Decompiled `AnvilToolkit.dll` v1.3.1 with **`ilspycmd`** (`ilspycmd -p -o <dir> AnvilToolkit.dll`; .NET 8 SDK, ilspycmd already installed at `C:\Users\user\.dotnet\tools`). 1119 classes; full project source dumped to scratchpad.
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

## Entry — 2026-06-30 — Cloth binding: why a `.cloth` "refuses to take on" a new mesh

### Prompt
SamiPuma: *"we can reference [a `.cloth`] in buildtables, but it refuses to take on."* Test case: **Walker's coat** — new weight-painted mesh + vanilla cloth reference, no simulation.

### What I did
Located the real Walker coat resources on disk and read the cloth binding classes (`ClothAdditionalVerticesBarycentricCoordinatesData`, `ClothUserData`, `ClothPropertiesMeshMappings`, `ClothEditorDataClothID`), `Mesh.cs`, and `SoftBody.ClothGenerationSettings`.

### VERIFIED (new)
- **Walker coat = 3 coupled resources in `DataPC.forge`** (cloth lives in DataPC, *not* Resources): `34223 TP_Tacvest_Walker_Coat` (~0.5 KB def), `34224 TP_WalkerCoat_Cloth` (MotionCloth, **72** sections), `35720 Cloth_WalkerCoat` (MotionCloth, **102** sections). Confirmed by counting 0xECD7 section magics in the raw `.data`.
- **Cloth is welded to a specific mesh's vertices**: `ClothAdditionalVerticesBarycentricCoordinatesData` (4565) maps render verts→sim triangles by barycentric coords baked for the vanilla mesh; plus `ClothUserData.UserVerticesCount`, vertex positions, constraints, per-vertex data — all index-addressed to the vanilla topology.
- **`Mesh.IsGeneratedFromCloth`** flag exists — render mesh and cloth sim mesh are produced together.
- **Cloth "weight" = `VertexMaxDistance`** (0=pinned, higher=free), exported by ATK into **GLB vertex color `Color1`**. It is *not* a skin weight.
- **ATK cloth generation is NOT wired for GRB:** `SoftBody.ClothGenerationSettings`'s host `SoftBody.SupportedGames` = AC2…Syndicate only. So ATK can read/export/edit/repack GRB cloth but **cannot regenerate** sim+mapping for new geometry. This is why GRB cloth "can't be used right now."

### Answer for Sami (the why + the what-works)
The BuildTable reference only *names* the cloth; the binding lives inside the cloth, baked to the vanilla coat's vertices. A new mesh has different vertices → mapping invalid → cloth dropped. Achievable today: (1) **tune** vanilla cloth via XML, (2) **reshape vanilla mesh keeping vertex count/order**, (3) **repaint `MaxDistance` (Color1)**. Brand-new topology needs a regeneration/remap step ATK lacks for GRB. Written up in [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) → "The binding problem".

### New top open question
Build/define the **render↔sim remap** (recompute barycentric 4565 + per-vertex data for a new mesh) — this is the single highest-value cloth task; it would unblock new-garment cloth on GRB.

---

## Entry — 2026-06-30 — Diffed the two Walker cloth resources

### What I did
Wrote an approximate MotionCloth parser ([`tools/cloth_inspect.py`](../tools/cloth_inspect.py)) and diffed `34224 TP_WalkerCoat_Cloth` vs `35720 Cloth_WalkerCoat` by decoding body names + a section-type histogram from the raw uncompressed `.data`.

### VERIFIED (new)
- **The two cloths are different-purpose, not redundant.** Body names decode cleanly:
  - `34224 TP_WalkerCoat_Cloth` → 1 body `Sim_TP_Tacvest_Walker_Coat_LOD1` = **gameplay/wearable** coat cloth. Carries full constraint buffers (ClothConstraints/Sizes, StretchingConstraints, MeshConstraintsSizes, Presets) + a **ragdoll bone-collider list** (`Ragdoll_Head…;LeftArm…Fore…Hand…Shoulder…Neck…Right…`).
  - `35720 Cloth_WalkerCoat` → 2 bodies `Sim_TPri_CIN__LOD0` + `Sim_TPri_CIN_Walker_Coat_LOD1` = **cinematic** (CIN) cloth; adds ClothPropWind×4, ClothEngineLoop, BodyTransform/Color, ClothAABox; ships LOD0+LOD1.
- **Cloth body name = `Sim_<TargetMeshName>_LOD<n>`** — the human-readable trace of the per-mesh-per-LOD binding. So modding the wearable coat means targeting `TP_WalkerCoat_Cloth`, not the cinematic one.
- **MotionCloth section header nuance:** header is small (type u16 + magic 0xECD7 + a size field); buffer sections (constraints, vertex data) are sized from **earlier counter sections** (per `MotionSectionFactory`), not a self-contained length — so a naive size-field or magic-scan walk is only approximate. Exact parsing needs the counter→buffer dependency logic.

### New open questions
- Build a **fully accurate MotionCloth parser** (counter→buffer sizing) for exact `ClothProperties` value diffs.
- Decode the **ragdoll bone-collider list** structure in the wearable cloth's editor data.

### Deliverables
`tools/cloth_inspect.py` (approximate inspector/differ, with documented limits); `docs/11` → "Diffing the two Walker cloths".

---

## Entry — 2026-06-30 — Closed two format gaps: `.data` compression descriptor + resource-type-id table

### What I did
Re-decompiled `AnvilToolkit.dll` v1.3.1 (`ilspycmd`, .NET 8) on a **new machine** (game now at `D:\SteamLibrary\...`, was `H:\`). Read `DataFile`, `CompressedFileData`, `DataBlock`, `CompressionInfo`, `Manager`, `HashedData`, `CRC32`, `ScimitarClassRegistry`, and the `Cloth`/`SoftBody`/`MotionSoftBody` classes. **Then verified empirically** by writing a from-scratch `.data` parser and Oodle-decompressing real files with the game's `oo2core_7_win64.dll` via ctypes.

### VERIFIED (new — resolves doc-02 open Qs 3 & 4)
- **Per-`.data` compression descriptor.** A `.data` payload = two `CompressedFileData` blocks (metadata/index, then file payloads). Each block: `uint64 Magic=1154322941026740787`, 7-byte `CompressionInfo` (int16 ver, byte algo, uint16, uint16), `int32 blockCount`, `blockCount×(int32 uncomp,int32 comp)` block-info, then blocks of `[uint32 adler32][comp bytes]`; block stored raw iff uncomp==comp. **GRB = Version 3, Algorithm 3, 32 768-byte blocks.** `Manager.GetCompressionAlgorithm` for GRB: 0=LZO1X,1=LZO1X999,2=LZO2A,**3=Oodle Mermaid SuperFast (default)**,4=Oodle Mermaid Optimal3. → confirms & refines the old "Oodle" inference (it's Oodle **Mermaid**, at the `.data` layer, 32 KB chunks, per-block adler32). Verified against `1687_-_TP_Top_Bodark_Trench_Cloth.data`. Doc: [`02`](../docs/02-forge-file-format.md).
- **Resource-type id = `CRC32(typeName)`** (standard zlib CRC-32, ASCII). Verified: `CRC32("BuildTable")=585940579`, `CRC32("Mesh")=1096652136` match ids embedded in real resources. Authoritative id→class map = `ScimitarClassRegistry` (dumped). Name resolution = `HashedData.GetHashedString` (embedded `hashes.hl` CRC-32 list + `AnvilExtensions` fallback). Typed-resource on-disk layout: `[FileHeader][uint64 ClassID][uint32 Extension=TypeId][…]`. New table: [`reference/resource-type-ids.md`](../reference/resource-type-ids.md).
- **GRB garment cloth is typed `Cloth`** (id `3811591354`), **not** `ClothPackage`. Full hierarchy: `Cloth → MotionClothState (1629082830) → MotionClothLOD (693470191) → ClothPackage (nested, no id) → MotionBody → MotionSection`. `SoftBody` (1263847064) / `MotionSoftBody` (2559966986) are sibling non-garment physics types. Verified: `TP_Top_Bodark_Trench_Cloth` embedded `Extension=3811591354`. Docs [`11`](../docs/11-cloth-and-physics.md) corrected (it previously called the top-level a "ClothPackage").

### Questions ANSWERED
- ✅ doc-02 Q3 (per-`.data` compression descriptor) and Q4 (`Extension` id→type table, incl. "which id = cloth").
- ✅ doc-11 Q6 (ClothPackage's `Extension` id) — reframed: the resource is `Cloth`; ClothPackage is nested.

### Deliverables
- `reference/resource-type-ids.md` (CRC-32 mechanism, on-disk layout, curated id table incl. full cloth/physics family).
- `tools/data_inspect.py` — lists typed resources + resolved types inside any GRB `.data`, Oodle-decompressing via the game DLL (auto-located). Tested on cloth/texture/mesh.
- Doc updates: [`02`](../docs/02-forge-file-format.md), [`03`](../docs/03-data-and-resources.md), [`11`](../docs/11-cloth-and-physics.md).

### Still open
- Per-`.data` **GlobalMetaFile**/**PrefetchingFileInfos** schemas (doc-02 Q5).
- Forge **mount/priority** rule; note observed: the same decimal entry id (e.g. `34224`) appears in *different* forges for unrelated resources, so ids are **not globally unique across all forges** — refine the load/override model in [`06`](../docs/06-game-load-and-reassembly.md) accordingly. **⚠️ RETRACTED — see the 2026-06-30 "leading number is not the file ID" entry below: `34224` was a positional *index*, not a file ID, so this observation is invalid.**
- Cloth **render↔sim remap** (the highest-value cloth task) — unchanged.

---

## Entry — 2026-06-30 — The leading number is NOT the file ID (corrects a foundational error + answers the `77777` question)

### What I did
While investigating "forge mount/priority + ID uniqueness," I compared entry names across the unpacked forges and noticed `DataPC_Resources.forge` was numbered `0..123568` with **zero gaps** — a dead giveaway for a positional index, not sparse 64-bit IDs. Read `FileSet.cs` / `DataFile.cs` / `ForgeFile.cs` / `DataFile.CreateForgeEntry`, then verified against real files with `tools/data_inspect.py` (Oodle).

### VERIFIED (new — and it CORRECTS earlier docs)
- **The leading number in `<N>_-_<name>.ext` is a positional index / sort label, NOT the file ID.** Forge unpack writes `SetIndex*5000 + i` (`FileSet.cs`); `.data` unpack writes a counter `k` (`DataFile.cs`); mod folders use a modder label. It's used only to **sort** on repack (`ForgeFile` `OrderBy(GetUntilOrEmptyInt("_-_"))`).
- **The real 64-bit file ID is each resource's embedded `ClassID`** (right after the file header), mirrored in the forge index as `ForgeEntry.ID`. On repack ATK reads it from the bytes (`CreateForgeEntry → ReadClassID`), ignoring the filename number. Verified: `3476_-_TP_Tacvest_Walker_Coat_LOD1.data` → embedded ClassID `1707208440119` (≠ 3476); `100000_-_UI_Emblem_Placeholder_Map.data` → `1822825930679`.
- **`77777` is a filename label, not a shared ID (answers a long-standing open question).** Two real `77777_-_…_LVAW_40R_LOD0.data` files have *different* embedded ClassIDs (`77444146123331`, `183219380011`). So there is no "77777 → real ID" reassignment mechanism: modders label new files `77777`; ATK uses the embedded ClassID at repack.

### Questions ANSWERED
- ✅ "How does `77777` resolve to real IDs at repack/load?" — it doesn't need to; IDs come from the embedded `ClassID`. (Was open in doc-08 / USP case study.)

### RETRACTED
- ❌ The prior entry's note that "the same decimal entry id (`34224`) appears in different forges ⇒ ids not globally unique." That compared **positional indices**, not IDs. The claim is withdrawn. **True ID uniqueness/override across forges is still unmeasured** — it must be studied via embedded ClassIDs (or forge-index `ForgeEntry.ID`), not filenames.

### Docs corrected
[`02`](../docs/02-forge-file-format.md), [`03`](../docs/03-data-and-resources.md), [`08`](../docs/08-naming-conventions.md) (leading-number + `77777` sections), [`reference/glossary.md`](../reference/glossary.md), [`examples/case-study-usp-tactical.md`](../examples/case-study-usp-tactical.md). Also fixed a `tools/data_inspect.py` console-encoding crash on resources whose names contain non-cp1252 bytes.

### Still open
- The **mount/priority** rule and real cross-forge **ID uniqueness/override** — now correctly framed around embedded `ClassID` / `ForgeEntry.ID`, needing a forge-index or ClassID scan to measure.

---

## Entry — 2026-06-30 — Forge ID study: real IDs are globally unique; patches override by ID

### What I did
Built a forge-**index** parser (reads `ForgeEntry.ID`/`Extension`/`Name` for every entry without decompressing payloads — layout from `ForgeFile.Deserialize27` + `FileSet` + `ForgeEntry`) and ran a cross-forge ID study on the real install. Packaged it as the **Forge Inspector** tool.

### VERIFIED (new)
- **IDs are unique within every forge** (0 duplicates): `DataPC.forge` 48 707, `DataPC_Resources.forge` 123 571, all patches — no dup IDs.
- **Real IDs don't collide across forge families.** Cross-family overlap is only the reserved sidecar IDs **16** (`GlobalMetaFile`) and **145** (`PrefetchingFileInfos`): `Resources ∩ DataPC = 2`, `Resources ∩ extra = 2`, etc. The rare extra match carries the *same ID and name* (same logical resource shipped in two forges). **No "same ID, different resource" across families** → a 64-bit ID identifies one resource game-wide.
- **Patches override their base by ID.** Base∩patch shared IDs: `DataPC` 2321, `Resources` 1961, `extra` 268 — mostly matching names (same resource updated). The name-differ cases are Ubisoft **repurposing an ID for new content** (`WI_DMR_MK14_Stock_Collapsed_LOD0`→`WI_DMR_JAEM1A_Stock_LOD0`; `MSR`→`JAE700` sniper parts) or typo-fix renames (`TP_FaceHair…`→`TP_FacialHair…`). Confirms the replacement-mod mechanism from real data.

### Questions ANSWERED / advanced
- ✅ Cross-forge **ID uniqueness** — real IDs are effectively globally unique (definitively kills the retracted "34224 collision" note, which was a positional index).
- ◑ **Override rule** — confirmed keyed on the real 64-bit ID; a patch overrides its base. **Still open:** priority *order* when the same ID sits in two *peer* forges (two mods, or mod vs. official patch) — a game-runtime mount-order question needing an in-game A/B test. Also still open: whether a novel (non-`DataPC*`) forge filename auto-mounts.

### Deliverables
- `tools/forge_inspect.py` (+ GUI, 2 launchers, `build-forge-inspector.yml`) — **Forge Inspector**: summarize a forge's types by real ID, or **diff two forges by ID to find mod conflicts/overrides**. Index-only, so fast on the 23 GB forge; no Oodle needed.
- Doc: [`06`](../docs/06-game-load-and-reassembly.md) "Verified: real IDs are globally unique, and patches override by ID".

---

## Entry — 2026-07-01 — Cloth render↔sim remap: characterized the binding, found ATK already has the algorithm

### What I did
Read the MotionCloth binding classes + `MotionSectionFactory` (exact section sizing) and the `Cloth` generation path. Extracted and scanned **all 56 `Cloth`-typed resources in `DataPC.forge`** directly (forge index → offset/len → Oodle-decompress → section scan) to characterize the binding across the real cloth population.

### VERIFIED (new)
- **Two render↔sim binding schemes.** Most GRB garment cloths are **direct** (no `ClothAdditionalVertices*` 4561–4565; sim verts == render verts). A subset use the **barycentric** scheme (4561–4565): a low-res sim mesh drives extra render vertices via per-vertex *triangle + barycentric*. `TP_WalkerCoat_Cloth` (wearable) is barycentric (170 sim / 288 tri); `IanBlake_TrenchCoat_Cloth` is direct (186/305). List includes `Cloth_HunterCoat`, `Tsec_Madera_Coat_Cloth`, `Cloth_Hunter_Hood`.
- **Exact binding layout + sizing** (from `MotionSectionFactory`): sim mesh = `ClothUserData.UserVerticesCount`(4354) + `ClothVerticesCurrentPosition`(4363, `Vector4[(V+15)&~15]`) + `ClothMeshIndexBufferSize`(4370)/`ClothMeshIndexBuffer`(4371). Barycentric binding sized off `ClothAdditionalVerticesCounters`(4561 = `{BufferSize N, SIMDSize}`): 4562 `byte[N]`, 4563 `ushort[N]` (index into sim index buffer), 4564 `SIMDF8` dequant params, 4565 `ushort[SIMDSize]` weights.
- **ATK already contains the remap algorithm** — `Cloth.FromMeshSet` → `GenerateVisualMapping` → `FindNearestTriangleWithIndices` + `computeTriBarycentricCoords` (per render vertex: nearest sim triangle + barycentric coords). It is **GRB-gated** (`SoftBody.SupportedGames` = AC2…Syndicate, checked in `FileHandler`) and emits the `SoftBodyVertexMapping` form, whereas GRB writes the packed `ClothAdditionalVertices*` sections. Two gaps: the gate, and a mapping→packed-section encoder.

### Design produced
The remap recipe (keep vanilla sim mesh; for each new render vertex compute nearest-triangle + barycentric with ATK's math; re-encode 4561–4565) is written up in [`docs/11`](../docs/11-cloth-and-physics.md) → "The render↔sim remap". The geometry is solved; remaining is an accurate section writer + encoder + **in-game validation**.

### Questions answered / advanced
- ◑ Q1 render↔sim remap — **characterized** (algorithm known = ATK's; encoding target known; two schemes identified). Build (accurate writer + encoder + in-game test) pending.
- ◑ Q3 accurate MotionCloth parser — sizing rules transcribed from `MotionSectionFactory` ([`reference/cloth-section-types.md`](../reference/cloth-section-types.md)); now a transcription job.

### Notes for next session
Build the accurate MotionCloth section reader/writer (parse ClothPackage via the ScimitarClass graph to reach sections cleanly), then the mapping encoder; validate on `TP_WalkerCoat_Cloth`. Consider surfacing "direct vs barycentric" + sim/render counts in the cloth tooling (and give `cloth_inspect.py` Oodle support, which it currently lacks).

---

## Entry — 2026-07-01 — Built the accurate MotionCloth reader/writer (`motioncloth.py`); upgraded Cloth Inspector

### What I did
Built `tools/motioncloth.py` — the exact ClothPackage reader/writer that the remap encoder needs — and rewired the Cloth Inspector to use it (accurate + plain-language + `.data`/Oodle support).

### VERIFIED (new)
- **Exact parse + byte-for-byte round-trip.** `motioncloth.py` locates every ClothPackage in a resource (one per LOD), walks each MotionBody's sections by their self-declared size (validating the `0xECD7` marker), decodes them, and re-serializes **byte-identical** to the input. Verified on: `IanBlake_TrenchCoat_Cloth` (direct, 2 LODs 186/305 + 138/227), `TP_WalkerCoat_Cloth` (barycentric, 2 LODs 170/288 + 66/100), and `1687_-_TP_Top_Bodark_Trench_Cloth.data` (Oodle path). Coverage checked: all `0xECD7` section markers fall inside located packages (bar one chance byte in Walker's bone-weight data).
- **Multi-ClothPackage resources confirmed.** A cloth resource holds one ClothPackage per LOD, with MotionClothLOD/state/skinning data (and the ScimitarClass wrapper) between/around them; `splice()` preserves all of that when editing one package.
- Incidental: `1687_-_TP_Top_Bodark_Trench_Cloth` reuses the **`Sim_Tsec_IanBlake_Trench`** sim mesh (same 186/305) — Bodark trench and IanBlake trench share the coat model.

### How it reads (for reuse)
Accepts a decompressed `*.Cloth` resource (what ATK writes when you unpack a cloth `.data`) or a cloth `.data` (auto-Oodle via the game DLL). Locate = find a `0xECD7` section, treat preceding 8 bytes as ClothPackage `count`+`body0len`, validate by parsing `count` bodies that consume exactly — robust against chance markers.

### Deliverables
- `tools/motioncloth.py` — accurate reader/writer engine (locate/parse/round-trip/splice + decoders).
- Upgraded `tools/cloth_inspect.py` (+ GUI text/filters) to delegate to it: exact counts, `.data`/`.Cloth` input, and a plain-language **DIRECT vs BARYCENTRIC** attachment call-out so modders know their reskin route. Rebuilt `ClothInspector.exe`.
- Docs: [`11`](../docs/11-cloth-and-physics.md) (remap "Progress"; open Q3 = built), [`tools/README`](../tools/README.md), main README.

### Still open (next)
The **write/encode** side: compute new barycentric bindings for a new render mesh (ATK's `computeTriBarycentricCoords` math) and encode them into the `ClothAdditionalVertices*` sections via `motioncloth`'s writer — then **in-game validation** on the Walker coat.

---

## Entry — 2026-07-01 — Encoder dig: the cloth binding model needs correcting (encoder paused)

### What I did
Started the render↔sim encoder. First step was to crack the barycentric quantization by decoding it and checking it reconstructs a known ground truth. Read the full LOD binary structure (`MotionSoftBodyLOD.Read` + `MotionClothLOD.Read`), `SIMDF8`, `Triangle`, `Handle`, `MeshBone`, `ScimitarClass`/`ScimitarClassReader`, and empirically walked real cloths (`TP_WalkerCoat_Cloth`, `IanBlake_TrenchCoat_Cloth`) extracted from `DataPC.forge`.

### VERIFIED (new)
- **Full GRB cloth-LOD layout.** Each MotionClothLOD (one per LOD) contains, in order: `Settings`; six per-**sim**-vertex `byte[]` paint arrays — **`VertexMaxDistance`**, `VertexBackStopDistance`, `VertexGravityScale`, `VertexDamping`, `VertexSkinWidthScale`, `VertexFriction`; the **ClothPackage** (length-prefixed blob; blob length int32 immediately precedes it — verified == parsed end); `TriQuadIndex`; **`VertexPos`** (sim, count == `ClothUserData.UserVerticesCount`); `VertexNormals`; `Indices` (sim tris×3); then visual/other fields; then (MotionClothLOD) `BoneIndices`/`BoneWeights`, `VisualVertexPos`, `VisualBoneIndices`/`VisualBoneWeights`, `MeshBones`/`VisualMeshBones`.
- **Sim mesh is skinned to the skeleton** (`BoneIndices`/`BoneWeights` + `MeshBones`; `MeshBone` = bind `Matrix4x4` + hashed bone name). ATK's `ToMesh` exports **only the sim mesh** (MaxDistance→`Color1`, per-vertex data→`Color2/3`), flagged `IsGeneratedFromCloth`.
- **`VisualVertexMappings` (SoftBodyVertexMapping list) = 0** in real GRB cloths (Walker + IanBlake). ATK's generator (`FromMeshSet`/`GenerateVisualMapping`) produces *this* form — so it does not match GRB's on-disk representation.
- **`SIMDF8` = 3 floats** {Scale, Offset, MagicValue}. Nested ScimitarClass header (GRB) = `ClassID`(u64,8) + `Hash`(u32,4).
- **`ClothAdditionalVertices*` (4561–4565) count == sim *triangle* count** for Walker LOD0 (288 == 288). Strongly suggests these are **per-triangle "additional collision vertices"**, not the per-render-vertex binding.

### CORRECTION (supersedes earlier)
The earlier claim (doc-11) that **`ClothAdditionalVerticesBarycentricCoordinatesData` (4565) is the render↔sim binding** is now **doubtful**. Evidence: `VisualVertexMappings` empty, 4561==triangle-count, sim/visual are separate skeleton-skinned meshes. doc-11's remap section now carries an ⚠️ "under revision" note. Not yet replaced with a confirmed model — flagged, not asserted.

### OPEN (the crux, blocks the encoder)
**How does a GRB MotionCloth drive its render mesh, given `VisualVertexMappings` is empty?** Candidates: (a) the separate render `Mesh` resource carries its own cloth-skinning to sim vertices; (b) `VisualVertexPos`+`VisualBoneIndices/Weights` at the LOD level; (c) 4561–4565 after all. Must resolve before the encoder.
- Secondary: my per-LOD walk **desyncs right after `Indices`** — a `BaseObject[]` array (read via `ClassReader.Read`) doesn't parse with the ClassID+Hash+data size I derived (Hash reads as 0, which ATK would reject). There's a nested-serialization subtlety (the exact `ClassReader` path / possible null handling) I haven't cracked. Needed to reach `VisualVertexPos`/`VisualBoneIndices` and to build a full LOD reader/writer.

### Deliverables / state
- No encoder yet (correctly — the model was wrong). `tools/motioncloth.py` (ClothPackage reader/writer, byte-exact round-trip) is solid and unaffected.
- Docs: doc-11 remap section flagged under revision.

### Next
Resolve the nested-`BaseObject`/`ClassReader` serialization to finish the LOD walk (get `VisualVertexPos`/`VisualBoneIndices` counts) and settle the render→sim mechanism — likely via reading `ClassReader.Read` exactly, or by having ATK export a Walker cloth to GLB and inspecting. Then re-scope the encoder around the confirmed mechanism.

---

## Entry — 2026-07-01 — Cracked the LOD-walk desync: ATK has NO GRB cloth reader; the binding IS 4561–4565 (with quantization decoded)

### What I did
Re-decompiled `AnvilToolkit.dll` v1.3.1 and read the **whole** cloth class family to settle "how does a GRB MotionCloth drive its render mesh" (the blocker from the prior encoder-dig). Traced the reader dispatch (`ScimitarClassReader.Read` → `ScimitarClass.Deserialize` → `ReadClassID`/`ReadClassHash`), the LOD classes (`SoftBodyLOD`/`ClothLOD` "old" family; `MotionSoftBodyLOD`/`MotionClothLOD` "next" family), their `SupportedGames` guards, `SoftBody`/`Cloth` (the resource class), and `FileHandler`. Then **verified empirically** by extracting the real Walker (`TP_WalkerCoat_Cloth`) and IanBlake (`IanBlake_TrenchCoat_Cloth`) cloths from `DataPC.forge` (index→offset/len→Oodle) and parsing them with `tools/motioncloth.py`.

### VERIFIED (new — this is a correction)
- **ATK v1.3.1 has no game-enabled structured reader for GRB cloth — it cannot parse a GRB `Cloth` at all.** `Cloth : SoftBody` (id `3811591354`, registry-confirmed → `typeof(Cloth)`) uses `SoftBody.Read`, whose first line throws unless the game is in `SoftBody.SupportedGames` = {AC2, Brotherhood, Revelations, AC3, AC3Remastered, BlackFlag, Rogue, Unity, Syndicate} — **`GhostReconBreakpoint` is not in it**. The exception is caught and `Failed = true` is set, so states/LODs/ClothPackage are never read. `FileHandler`'s cloth Mesh-Viewer (case 0, line 286) and XML-export (case 1, `if (Data.Failed) return ""`) both bail for GRB. So ATK's *structured* cloth features (viewer, XML/GLB export, generation) are all off for GRB; it only round-trips the cloth as **opaque container bytes** on repack. (Corrects the earlier "ATK can read/export/edit GRB cloth" and "ClothProperties round-trip to XML for GRB" claims — those hold for the games ATK supports, not GRB.)
- **This is why the prior per-LOD walk desynced right after `Indices`.** That walk reconstructed the *wrong game family's* schema (`MotionSoftBodyLOD`/`MotionClothLOD`, gated to {Unity, Syndicate}) onto GRB bytes. GRB's on-disk cloth is the engine's native MotionCloth serialization, which ATK models for other games but not GRB; the field lists diverge past `Indices`, so the "`VisualVertexMappings` empty" reading is meaningless (that field belongs to a class that never runs for GRB). The nested `BaseObject` header assumption was fine: for GRB, `ReadClassID` = **u64 (8 bytes)**, `ReadClassHash` = **u32 (4 bytes)** that must equal the expected hash — so the desync was upstream, not in the header.
- **The render↔sim binding IS the `ClothAdditionalVertices*` family (4561–4565), inside the ClothPackage.** Reverses the prior "doubtful/under revision" note. Verified byte-exact on real cloths:
  - **DIRECT** (IanBlake, 186 sim/305 tri both LODs): no 4561–4565 → render mesh == sim mesh.
  - **BARYCENTRIC** (Walker LOD0: 170 sim verts, 288 sim tris): render mesh = sim mesh **+ A extra ("additional") vertices**, each barycentric-bound to a sim triangle.
    - `4561 Counters {AdditionalVerticesBufferSize N, AdditionalVerticesSIMDSize M}`: **N == sim-triangle count (288)**, M = 64.
    - `4562 TriangleVerticesCount byte[N]` + `4563 TriangleFirstVertexIndex ushort[N]` = **per-sim-triangle CSR adjacency** (how many additional verts sit on triangle *t*, and the first index into the additional-vertex list). `A = sum(4562) = 62`, and `4563[last] + 4562[last] = 62` (exactly consistent). *(Corrects doc-11's earlier "byte[N] = sim verts per binding (typically 3)" / "start index into the sim index buffer" — the arrays are indexed per sim triangle, not per render vertex.)*
    - `4565 BarycentricCoordinatesData ushort[M]` = **one quantized-barycentric ushort per additional vertex**, with **M = A padded up to a multiple of 8** (SIMD width; 62→64, 114→120). Tail padding = `0xFFFF`.
  - So the "4561–4565 count == triangle count" the prior session flagged is just the CSR adjacency (4562/4563), **not** evidence against the binding.
- **Quantization decoded (unblocks the encoder).** `4564 BarycentricCoordinatesParameters` = `SIMDF8` = 3 floats {Scale, Offset, Magic}; for Walker LOD0 = {0.0020564, ≈0, 0.52335}. Each 4565 ushort splits into two bytes; **coord = byte × Scale + Offset** gives the two smaller barycentric weights (each ≤ Magic ≈ Scale·255 ≈ 0.523; the dominant weight = `1 − u − v`). This decode yields **62/62 valid barycentrics** (all coords in [0,1]). The additional vertex → triangle → 3 sim verts chain resolves via the CSR arrays + the sim index buffer (4371, `ushort[3·tri]`).

### Questions answered
- ✅ "How does a GRB MotionCloth drive its render mesh, given the ATK LOD walk desyncs / `VisualVertexMappings` is empty?" — The premise was an artifact of reading the wrong game family. GRB drives its render mesh via the **direct** scheme (render == sim) or the **barycentric** `ClothAdditionalVertices*` sections (render = sim + additional verts bound to sim triangles). The encoder is **re-scoped and now fully specified** (below).
- ✅ The nested-`BaseObject`/`ClassReader.Read` serialization (header = u64 ID + u32 hash for GRB).

### Encoder — now fully specified (build pending)
For a barycentric reskin, keep the vanilla sim mesh + triangles; the new render mesh = **sim verts (same order) + additional verts**. Per additional render vertex: find its sim triangle + barycentric (ATK's `computeTriBarycentricCoords`), take the two smaller weights, `byte = round((w − Offset)/Scale)` clamped [0,255], pack hi/lo → one ushort. Rebuild CSR (4562/4563) grouping additional verts by sim triangle, set 4561 `N = tri count`, `M = A padded to ×8` (pad 4565 with `0xFFFF`), and write 4564 `Scale = maxWeight/255, Offset ≈ 0`. Remaining unknowns before a **byte-exact** writer: the exact vertex-order convention (which of the 3 tri verts each byte maps to; u↔v order) and confirming the "two smaller weights, drop the max" rule — both settle by cross-decoding 4565 against the real render `Mesh` (`TP_Tacvest_Walker_Coat_LOD0.Mesh`, predicted **232** verts = 170 sim + 62 additional). `tools/motioncloth.py` (byte-exact ClothPackage reader/writer) is unaffected and is the substrate for the encoder.

### Deliverables / state
- No repo tool changes yet; findings only. doc-11's remap section updated (the "under revision" doubt is resolved; CSR semantics + quantization corrected). Scratchpad verification scripts (`verify_binding.py`, `probe_quant.py`) are session-temporary.

### Next
Confirm the vertex-slot convention against the render `Mesh` (positions of `TP_Tacvest_Walker_Coat_LOD*.Mesh`), then build the mapping→section encoder in `motioncloth.py` and validate in-game on the Walker coat. Note: GRB `Mesh` *is* game-enabled in ATK (`Mesh.SupportedGames` includes GRB, unlike cloth), so a render-mesh parser is feasible — but it's a real sub-project (Mesh→CompiledMesh→MeshData vertex streams).

### Refinement (same session, corrects the quantization detail above)
Characterized 4565 statistically on Walker (both LODs) without the render mesh. Corrections to the "two smaller weights" wording above:
- **`Scale` is a per-LOD normalization** (`Scale = maxStoredWeight/255`, so `Magic = Scale·255` = that max), **not** a fixed ½ bound. Walker LOD0 `Magic` = 0.524, **LOD1 `Magic` = 0.751** — a stored weight can exceed ½, so the two stored are **not** "the two smaller."
- Verified instead: **every stored weight ≤ `Magic`** (0/62 and 0/114 exceed), the **tail is all `0xFFFF`**, and **all** reconstructed additional-vertex rest positions (from sim positions 4363 + index buffer 4371 + decoded barycentric) fall **inside the sim-mesh bbox**.
- The derived third (`1−u−v`) is **not** consistently the largest weight (LOD0: 40 max / 14 mid / 8 min of 62) → the encoding stores two weights at **fixed per-triangle vertex slots** (index-buffer order), not magnitude-sorted. The remaining unknown is just that slot permutation (~6 candidates), which needs render-mesh positions or an in-game trial — everything else about the encoding is pinned.

---

## Entry — 2026-07-01 — GRB Mesh parser DISPROVES the "4561–4565 is the render binding" model

### What I did
Built a minimal GRB render-`Mesh` position reader to pin the cloth binding's slot convention (the one open detail from the previous entry). It ended up **disproving the binding model** instead. Read the GRB mesh path in ATK (`Mesh.ReadFromFile` → `CompiledMesh.ReadFromFile` → `ClusteredMeshData`/`MeshData`, `MeshPrimitive`, `VertexFormatsMap`) — note `Mesh.SupportedGames` **includes** GRB, so meshes (unlike cloth) are game-enabled. Then extracted `TP_Tacvest_Walker_Coat_LOD0/LOD1.Mesh` from `DataPC_Resources.forge` and parsed vertex positions + skinning.

### VERIFIED (new)
- **GRB render mesh format.** `Mesh` (wrapper: flags, SubMeshes, Bones, extents) → `CompiledMesh` → **`ClusteredMeshData`** (GRB uses clustered; `MeshData`'s own buffers are empty). Layout reached by scanning the `ClusteredMeshData` class hash (3276926531): `DataVersion, formatByte, VertexStride(int32), ClusterCount, Center(v3), HalfExtend(v3), DrawPrimsCount, ClusterCountPerDrawPrim[], VertexOffsetPerDrawPrim[], IsFixedClusterSize, <u32>, VertexBufferData, IndexBufferData, PrimitiveDescData`. Vertex format = `Pos3s_Norm4ub_Col4ub_Tex2s_Tex2s_Color4ub_Joint`, **stride 36**: position = 3×int16 at offset 0, `world = int16 × QuantizationFactor` (≈6.10e-5 here, ≈ mesh extent / int16 range; no center offset). Last 4 bytes = **two-bone skinning** `[idx0, w0, idx1, w1]`, `w0+w1 = 255`.
- **Walker LOD0 render mesh = 1816 verts / 3263 tris** (verified 3 ways: `vlen 65376 / stride 36`, `max index = 1815`, `MeshPrimitive.NumVertices = 1816`). LOD1 = 956 / 1631.
- **The render mesh is an ordinary skeleton-skinned mesh.** Two-bone weights sum to 255 for **all 1816** verts; bone indices span only **0..23** — a skeleton, not the 170 sim vertices. So the render mesh carries **no per-vertex binding to the sim mesh**.

### CORRECTION (supersedes the two prior 2026-07-01 entries' conclusion)
- **`render ≠ sim + additional`.** 1816 render verts ≠ 170 sim + 62 additional (=232). The `ClothAdditionalVertices*` (4561–4565) sections describe only **62** (LOD0) / 114 (LOD1) points — a small per-triangle set — **not** the render mesh. So **"4561–4565 is the render↔sim binding" is WRONG.** (The byte-exact section *format/decode* from the prior entry still stands as facts about those sections; only the interpretation is wrong.)
- The 62 additional points reconstruct (barycentric on sim triangles) onto the **sim surface** but do **not** coincide with render vertices (nearest render vert ≈ 2% of mesh scale away, same offset as the sim verts). Consistent with ATK's literal class name *"additional **collision** vertices."* Role unconfirmed.
- Prior claims withdrawn: "render mesh = sim verts + A additional verts (sim first)"; "the encoder is fully specified / un-blocked"; the "direct vs barycentric render↔sim binding" framing.

### OPEN (the real blocker, reopened)
**How does a GRB MotionCloth drive its 1816-vertex render mesh?** The render mesh is skeleton-skinned with no sim binding; the cloth stores only the sim mesh + 62 additional points. So the sim→render map is either (a) **runtime-computed by proximity** (render vert → nearest sim triangle, nothing authored — which would make 4561–4565 genuinely just collision points), or (b) **stored somewhere not yet located** (a wrap/skin section, or in the mesh's SubMesh/Bone data I skipped). Settle this before any reskin encoder. Next probes: decode the render mesh's `Bones`/`MeshBones` names (skeleton vs cloth), and look for a per-render-vertex sim-wrap in the mesh or a cloth section not yet mapped.

### Deliverables / state
Docs corrected (doc-11 render↔sim section carries a prominent correction note; `reference/cloth-section-types.md` reframed; open-question #1 reopened). No repo tool yet from the mesh parser (scratchpad `mesh_parse.py`/`subset_test.py`, session-temporary). `tools/motioncloth.py` unaffected.

---

## Entry — 2026-07-01 — Hunt the wrap: the render↔sim binding IS STORED in the cloth

### What I did
Followed up the mesh-parser correction by hunting for how the cloth actually drives its render mesh. Examined the cloth's per-LOD bytes **after** the sim `ClothPackage` (the region `motioncloth.py` treats as opaque, and where the old hand-walk desynced), using the render mesh facts (1816 verts, sim 170) as anchors.

### VERIFIED (new — answers the reopened blocker)
- **The render↔sim wrap is STORED in the cloth, not runtime-computed.** Each cloth LOD carries a large per-LOD block after its sim `ClothPackage` (Walker LOD0: ~35 KB between package0@[2945–40358] and package1@[83290–105475]). Layout after the sim package parses cleanly: `TriQuadIndex(288)`, sim `VertexPos(170)`, sim `VertexNormals(170)`, sim `Indices(864)`, an **empty list (count 0)** — *this is the "VisualVertexMappings empty" the earlier entry saw* — then a **count = 1816 (render vertex count)** followed by per-render-vertex data.
- **That per-render-vertex data binds each render vert to ~3 nearby sim vertices.** The region holds **~5833 sim-valued u16 indices ≈ 1816 × 3**. Parsing at a **20-byte stride**, 1361/1816 records carry 3 valid sim indices that (a) **track render order** (render200→sim(0,2,3), render1000→(92,114,113), render1400→(163,164,150)) and (b) form **tight local triangles**: median 3-vertex spread **0.131 ≈ 1.5 sim-edge-lengths** (sim edge 0.085), vs. mesh-scale 0.56 for random triples. Random data cannot produce spatially-local, order-correlated sim triples, so this is a genuine stored wrap (render vert → local sim triangle + weights). The `4561–4565` "additional vertices" are a separate small (62) collision set, consistent with ATK's class name.
- **GRB render `Mesh` decode** (built this session, reused here): `Mesh`→`CompiledMesh`→`ClusteredMeshData`; vertex `Pos3s_Norm4ub_…` stride 36; position = int16 × QuantizationFactor (≈6.10e-5); two-bone **skeleton** skinning (bone idx 0..23) — i.e. the mesh's own skinning is to the skeleton; its cloth-following comes from the stored wrap in the cloth.

### INFERRED / still to decode
- Exact wrap record layout: the ~20-byte record appears to be `[flag/count][6× u16 weight data][3× u16 sim index]`; weight encoding not yet cracked (a first float-weight reconstruction failed). ~25% of records don't parse at the fixed 20-byte stride → the buffer may be **variable-length** (0xFFFF-delimited runs seen elsewhere in the block), not a flat array.
- A **render-vertex-order remap** between the cloth's ordering and the render `Mesh`'s vertex-buffer order: index-matched position reconstruction was poor (median 0.39) even though per-record sim triples are local — i.e. the binding is real but cloth-render-vert *i* ≠ mesh-vert *i*.

### Why it matters (modding)
The reskin path is now correctly scoped: to put a new render mesh on a cloth garment, **regenerate this wrap** (for each new render vert: nearest sim triangle + barycentric weights — exactly ATK's `computeTriBarycentricCoords`), keep the sim mesh, and write the records. So the mechanism is both **understood and regenerable in principle** — the remaining work is cracking the record encoding + the vertex-order remap, then an encoder + in-game test.

### Deliverables / state
Docs updated (doc-11 "Net" note now says the wrap is stored + located; open-question #1 reframed to "mechanism found, format to decode"). Scratchpad probes (`wrap_test.py`, `wrap_test2.py`) session-temporary. `tools/motioncloth.py` unaffected (this wrap lives in the LOD bytes *outside* the ClothPackage it parses).

---

## Entry — 2026-07-01 — Wrap record structure cracked (20-byte format); weight encoding hits a correspondence wall

### What I did
Pushed to fully decode the stored render↔sim wrap for an encoder. Pinned the record layout by histogramming the gaps between "local sim-triple" positions in the LOD0 visual block, then tried to crack the weight encoding by reconstructing render positions and regressing stored fields against true barycentric.

### VERIFIED (new)
- **Wrap record = 20 bytes, fixed stride.** Gap histogram between local sim-index triples is dominated by **20** (1144×) → fixed 20-byte records. Layout: **`[u16 flag][6× u16][3× u16 sim vertex index]`** (indices in the last 6 bytes, verified by a consistent phase). The 3 sim indices per record are valid (`< V`) local triangles.
- **The binding reconstructs to render vertices.** Using the 3 sim indices + any reasonable weights, `Σ wₖ·simP[idxₖ]` lands **≈0.013 from a render vertex** (= the sim↔render frame offset) for essentially all clean records. Confirms render vert → 3 sim verts is the real mechanism.
- **~75% of render verts are cloth-bound.** At the correct 20-byte phase, **1361 / 1816** records carry valid sim indices; the rest are likely null/rigid (skeleton-only) verts — physically sensible for a coat (upper rigid, lower swinging).

### WALL (offline analysis can't finish this alone)
- The **6 middle u16 don't decode as plain barycentric weights**: `stored/65535` sums to ~1.2–1.5 (too big for an in-plane barycentric), and regressing all 6 stored fields against the nearest-render-vert barycentric gives **~0 correlation** (|r|<0.18). Two non-exclusive reasons: (a) the encoding isn't a simple normalized-u16 barycentric (maybe weights+normal-offset, a different scale, or skin-style weights renormalized at runtime); (b) the exact **record ↔ render-vertex correspondence is unknown** — records carry no render index, so they must be in the cloth's own render-vertex order, which differs from the render `Mesh` buffer order, and the sim triangles are too small (~6 render verts each) to disambiguate geometrically. Can't crack the weights without the correspondence, can't pin the correspondence without the weights.

### Paths to finish (next)
1. Decode the **render-vertex-order remap** buffer — elsewhere in the same block there's an ascending-render-index + `0xFFFF`-delimited structure (seen ~offset 48814) that likely maps cloth render-order ↔ mesh order (or groups render verts per sim vert). Cracking it gives the correspondence, which unlocks the weight regression.
2. Or an **in-game round-trip**: write records with straightforward computed barycentric weights (nearest sim triangle) and see whether the cloth drapes correctly — the fastest way to validate the encoding empirically (the maintainer's in-game testing).

### Deliverables / state
Record structure documented (doc-11). Scratchpad probes (`crack_weights.py` and the gap/regression scripts) session-temporary. No encoder yet — correctly, pending the weight encoding. `tools/motioncloth.py` unaffected (wrap is outside the ClothPackage).

---

## Entry — 2026-07-01 — Wrap block sub-structure mapped; correspondence still needs in-game

### What I did
Attacked the record↔render-vertex correspondence (the wall from the previous entry) by decoding the rest of the LOD0 visual block — the goal being to unlock the weight encoding. Mapped the block into its sub-buffers.

### VERIFIED (new — block layout)
After the LOD0 sim `ClothPackage` + sim mesh fields, the visual block is: `[u16 flag / small header ~46766][reindex-grouping table 46894–50524][1268 wrap records 50524+]`.
- **Wrap records:** exactly **1268 contiguous 20-byte records** at offset 50524, **all 1268 with valid sim indices** — i.e. one record per *bound* render vertex (not per render vertex; the render mesh has 1816, ~70% are cloth-bound).
- **Reindex/grouping table (46894–50524):** a `0xFFFF`-delimited list whose values are a **clean permutation of 0..1267** (globally ascending → literally 0,1,2,…), partitioned into **547 buckets** (282 non-empty). So it groups the 1268 record indices into buckets. The buckets loosely relate to sim vertices — 169 non-empty buckets have all their records sharing a common sim vertex — but it is **not** a clean 1:1 (only 72 distinct shared verts across 282 buckets), so the exact bucket key isn't pinned.

### STILL OPEN (unchanged blocker)
- **Record ↔ render-mesh-vertex correspondence.** Records appear ordered by a sim-vertex-ish grouping (via the reindex table), which is why identity-to-mesh-order fails. Recovering the exact per-record mesh vertex would need either fully decoding the grouping-table semantics (a deep nested structure) or a bijection solve against render positions (ambiguous given the ~0.012 sim↔render surface offset ≈ 10% of a sim triangle).
- **6-u16 weight encoding** — still entangled with the above.

### Recommendation (revised next step)
Offline decode of this nested structure has hit steeply diminishing returns. The efficient path to a working reskin encoder is now an **in-game round-trip**: build a best-effort encoder (per new render vert → nearest sim triangle + barycentric weights, written in the confirmed `[flag][weights][3 sim idx]` record form, weights as normalized u16 since the game likely renormalizes) and validate by loading the modified cloth in GRB. That empirically settles the weight scale and whether the game rebuilds the grouping table itself. The maintainer runs in-game tests, so this fits the workflow.

### Deliverables / state
Block layout documented (doc-11 already carries the "still to decode" caveat). Scratchpad probes session-temporary. No encoder yet.

---

## Entry — 2026-07-01 — Built `clothwrap.py` (wrap locator + in-game diagnostic); designed the confirmation test

### What I did
Built a first tool on the wrap findings and designed the in-game test that settles the remaining unknowns (weight scale, whether the game rebuilds the grouping table).

### Deliverable: `tools/clothwrap.py` (experimental / research-tier)
- **Robust wrap locator** — forward-parses the sim fields after each LOD's `ClothPackage` (TriQuadIndex, VertexPos, VertexNormals, Indices, empty list, render-count), then detects the 20-byte record run (longest stretch whose last 3 u16 are valid sim indices). No hardcoded offsets. Verified it finds Walker **LOD0: 1268 records @50524** and **LOD1: 956 records @109921** (LOD1 is 100% bound; LOD0 ~70%).
- **`inspect`** — plain-language summary (sim cage size, visible mesh size, % bound).
- **Diagnostic generators** (`--diagnostic twist|collapse`) — deliberately mis-point every record's 3 sim indices (twist = shift by 40 mod V; collapse = all → cage vertex 0). Edits are **same-size, in-place**: verified byte-identical to vanilla except exactly the sim-index low-bytes (0 unintended changes across 133 336 bytes). Input/output a decompressed `.Cloth` (or `.data` via `--oodle`).

### The in-game confirmation test (why it's decisive)
Editing only the **sim indices** uses the one part of the record we're 100% sure of, so it's a clean test of the *mechanism* (independent of the still-unknown weight encoding). If a twisted/collapsed Walker coat visibly distorts in-game → the wrap **is** what drives the visible mesh (confirms the whole render↔sim finding live). If it looks normal → we're wrong and must reconsider. This gates any weight-encoder work.

### Apply pipeline (for the tester)
Back up the forge → unpack `TP_WalkerCoat_Cloth` in ATK → run `clothwrap.py … --diagnostic twist` → re-import the modified `.Cloth` and repack (ideally into a patch forge on a backed-up install) → load GRB and view the Walker coat. Open question for the tester: easiest way to see the Walker coat in-game (player outfit vs. NPC/cutscene); if awkward, retarget an easily-equippable garment (the locator is generic, though only verified on Walker).

### Next
Run the in-game diagnostic. If confirmed, extend `clothwrap.py` with the weight-writing encoder (new render mesh → nearest sim triangle + barycentric) and iterate the weight scale in-game.

---

## Entry — 2026-07-01 — IN-GAME TEST: editing the wrap records had NO visible effect (wrap-as-driver NOT confirmed)

### What I did
Ran the first live in-game test of the render↔sim "wrap" hypothesis. Used `tools/clothwrap.py` + a raw-block `.data` repacker to produce modified ghillie cloths (which have wraps on player-equippable gear), staged them into `DataPC.forge`, and had the maintainer repack and observe on female Nomad. Two edits tested: **twist** (shift every record's 3 sim indices by +40) and **collapse** (all indices → sim vertex 0). Verified the modified cloth was actually present in the live forge each time (e.g. `Cloth_Shoulder_Sniper_GhillieThreads1` record0 idx = (0,0,0) after collapse), and confirmed no patch forge overrides these cloth IDs.

### RESULT (verified in-game)
- **Editing the 20-byte wrap records produced NO visible change** — not in the loadout/bivouac menus, and not in live gameplay with full movement (sprint/roll/jump), across all equippable ghillie items. Even a full **collapse** of a **100%-LOD0-bound** wrap (`Cloth_Shoulder_Sniper_GhillieThreads1`, 2996/2996) left the shoulder tufts looking completely normal.

### What this means (honest downgrade)
- **The "20-byte wrap records drive the visible mesh at runtime" conclusion is NOT confirmed and is now doubtful.** The static evidence that these records are *geometrically* a render→sim binding still stands (per-render-vertex → 3 local sim verts, reconstructs onto render vertices), but a binding that the runtime renderer actually uses would visibly break when collapsed. It didn't. So the records are more likely **editor/build/derived data** (an authoring-side or precompute representation the runtime doesn't consult) than the live render driver — OR the runtime uses a *baked* form not affected by editing this source.
- **Caveat (why this isn't a clean disproof for coats):** only **ghillie** cloths were tested (they were the equippable, viewable option). Ghillie strands may be **skeleton-skinned** rather than cloth-render-driven, which would make any ghillie cloth edit invisible regardless. So this disproves "wrap drives the ghillie render mesh" but leaves the **coat** case (the original Walker/Sami question) formally untested in-game.
- **Methodological lesson:** the extensive static analysis produced a self-consistent geometric story that a single in-game test overturned. Weight this: static "it looks like a render→sim binding" ≠ "the runtime renders from it."

### Deliverables / state
Forge reverted to the pre-test backup (`Backups/DataPC.forge.pre-clothtest-20260701`), install clean. `tools/clothwrap.py` still valid as a wrap *locator/inspector*; its framing as "the render↔sim binding" is downgraded pending a coat test. doc-11 flagged.

### Next (candidates, no more speculative offline decoding)
1. One clean **coat** test: collapse an equippable, viewable *coat* cloth with a wrapped LOD0 (e.g. `Cloth_HunterCoat` if equippable) — coats are more likely genuinely cloth-render-driven than ghillie strands. This is the real disambiguator.
2. If coats also show nothing → the runtime render→sim path is elsewhere (a baked/compiled buffer, possibly in the render `Mesh` or a compiled cloth form); the 20-byte records are authoring data. Re-open "how does a GRB cloth drive its render mesh" accordingly.

---

## Entry — 2026-07-01 — Ghillie strands are SKINNED, not simulated → the ghillie tests were an invalid subject (wrap model UNTESTED, not disproven)

### What I did
Ran a control test to check whether the ghillie cloth is even physics-simulated at render time: set `ClothProperties.Gravity` (section 4357) from the default `(0,0,-15)` to **`(120,0,150)`** (reversed + ~10× magnitude) on all 11 equippable ghillie cloths, staged into `DataPC.forge`. Verified the flipped gravity was present in the *running* forge (`Cloth_Shoulder_Sniper_GhillieThreads1` 4357 gravity = (120,0,150) live).

### RESULT (verified in-game)
- **Reversing + amplifying gravity 10× produced NO visible change** on the ghillie strands in gameplay. Gravity is the most fundamental simulation input, so no response means the visible ghillie strands are **not driven by live cloth simulation** — they are **skinned** (or `VertexMaxDistance`-pinned so tightly they never deviate from the skinned pose). Either way, **a ghillie's visible strands don't move via cloth sim.**

### CORRECTION (supersedes the prior "IN-GAME TEST … wrap NOT confirmed" entry's implication)
- The ghillie was an **invalid test subject.** Since ghillie strands aren't cloth-simulated, *no* cloth edit (wrap twist, wrap collapse, gravity flip) could ever show — which fully explains the earlier null results **without bearing on the wrap hypothesis at all.**
- So the earlier downgrade ("wrap-as-driver is doubtful") is itself corrected: the ghillie negatives are **uninformative**, not disconfirming. The wrap model (static: the 20-byte records are geometrically a render→sim binding) is **neither confirmed nor disproven — it remains IN-GAME UNTESTED**, because no *equippable + viewable + genuinely cloth-simulated* garment was available this session (ghillies skinned; Walker/named-character coats not player-viewable; female Nomad has no other cloth garment).
- **New verified fact (useful in its own right):** GRB **ghillie suits render their strands via skinning, not live cloth**, at the LODs/poses the player sees. Good to know for modders — reskinning a ghillie is a mesh/skin-weight job, not a cloth job.
- **Meta:** two layers of misread here (static self-consistency ≠ runtime; and a null in-game result can mean "invalid subject," not "hypothesis false"). Both worth remembering.

### Next (for a future session — no more ghillie tests)
1. Find/obtain a **player-equippable, close-up-viewable, genuinely cloth-simulated** garment (a coat/cape whose strands visibly sway in gameplay), then re-run the wrap collapse on it — the only clean in-game validator.
2. Or accept in-game is blocked and pursue the runtime path in data: check whether the render `Mesh`/`CompiledMesh` carries a baked cloth-skinning buffer (the actual runtime render→sim link) that the 20-byte records feed at build time.

### Deliverables / state
`tools/clothwrap.py` + the scratchpad raw-`.data` repacker + a `ClothProperties.Gravity` editor all work (verified end-to-end: edits reach the running game). Forge revert pending (GRB was still holding the file open) — restore `Backups/DataPC.forge.pre-clothtest-20260701` once the game is closed.

---

## Entry — 2026-07-01 — RETRACTION: ghillie strands ARE simulated; the null tests only covered 11 of 33 ghillie cloths (inconclusive)

### Correction (retracts the previous "ghillie strands are SKINNED" entry)
The tester (who plays the game) reports the ghillie strands **visibly respond to character movement and environmental wind** — i.e. they **are** live cloth-simulated. So the prior conclusion "ghillie strands are skinned/pinned" is **WRONG and retracted.**

### Why the tests still showed nothing (the actual gap)
- The in-game edits (wrap twist/collapse, gravity flip) were applied to only **11 of the ~33 base ghillie cloths** — the subset that had *wraps*. The gravity test reused that same 11.
- No patch/mod overrides the base ghillie cloths (checked all three patch forges: 0 Cloth-typed ghillie overrides), so the base files *are* what loads — but the tester's specific ghillie item very plausibly uses one of the **other 22 ghillie cloths that were never edited.** That produces a "no change" that is **wrong-file, not wrong-hypothesis.**
- So all the ghillie null results are **INCONCLUSIVE**, not disconfirming — for *both* the wrap and the gravity. The wrap model is still **untested**, and the one thing we can say is confirmed is that GRB ghillie strands **are** cloth-simulated (contrary to the retracted entry).

### Fix for next time (makes it a clean test)
1. Edit **all ~33 ghillie cloths** (or, better, have the tester name the exact ghillie item so we target its cloth) — for both the gravity control and the wrap collapse. Then any equipped ghillie is guaranteed affected, and a single look is decisive.
2. Gravity control first (does flipping gravity on the *right* cloth billow the strands? → confirms we're editing the live sim), then the wrap collapse (→ tests whether the 20-byte records are the render path).

### Meta
Third correction in this thread. Compounding lesson: a null in-game result can mean (a) hypothesis false, (b) invalid subject, or (c) **wrong file/subset edited** — rule out (c) by ensuring the edit demonstrably covers what's on screen (e.g. a gravity control that *must* move a working cloth).

---

## Entry — 2026-07-02 — In-game cloth-gravity tests; forge *append*-edits are NOT launch-safe (ATK repack required); real-mod corpus survey begun

### Environment
- Same researcher workstation as 2026-06-30 (H:\ Steam install, user `sylvi`, GitHub `dataterminals`). Disk was critically low (~4.5 GB free); freed to ~14 GB before forge work. Repo pulled up-to-date (was 21 commits behind — the cloth-wrap research had advanced on another machine).

### What we did
- Resumed the project and ran the **first substantial in-game cloth tests**, driving edits through a custom *append-repoint* forge writer (scratchpad `forge_stage.py`) + `clothwrap.py` gravity edits — then, on the tester's advice, **pivoted to the standard ATK repack workflow**.

### VERIFIED (new)
- **Cloth resources live only in `DataPC.forge`.** All **56** `Cloth`-typed entries are there; the sole patch-forge copy is `TP_Top_Bodark_Trench_Cloth` (overridden in **both** `DataPC_patch_01.forge` and `DataPC_TGT_WorldMap_Bootstrap_Split_patch_01.forge`). So a cloth edit targets `DataPC.forge` — the exception to the usual "cosmetic mods don't touch DataPC" rule (meshes/textures live in Resources; DataPC holds BuildTables + logic + cloth).
- **`ClothProperties` gravity (section 4357) is freely editable and round-trips**; negating/scaling the vector reads back live through Oodle decompression. (Editable ≠ visibly effective — the render effect is the open question below.)
- **⚠️ KEY FINDING — *append-repoint* forge editing is NOT launch-safe for GRB.** *(⚠️ **RETRACTED same day** — see the later 2026-07-02 entry: the real cause was **RAW vs Oodle-compressed `.data` blocks**, not the packing method; a clean ATK repack fails identically when fed raw-block cloths.)* A writer that appends modified entries to the end of a `.forge` and re-points the index yields a forge that *parses* correctly (Forge Inspector reads it; the game even booted one such edit once) but the game then **repeatedly fails to launch — dying at the pre-app, borderless-logo splash, before the engine window opens.** That pre-engine timing implicates a **startup data-integrity/structure check** that a clean rebuild passes and an append+dead-space+raw-block forge fails (seemingly intermittently). **A proper ATK repack of the unpacked forge folder is the correct, launch-safe way to edit GRB forges** (the community's standard method). ⇒ do NOT ship a naive forge-*writer* tool; document ATK repack as required. (Caveat: the tester reports GRB/Ubisoft-Connect launches are semi-flaky *independent* of edits — retry the splash a couple times before concluding.)
- **The Golem Cape ("Golem Cape | Field Medic", a vest-slot skin) is genuinely cloth-simulated** — video-confirmed: the long coat flares/swings/lags with movement in gameplay and hangs straight down at rest. It's an **equippable, close-up-viewable, truly-simulated** control subject — exactly what every prior in-game cloth test lacked (ghillies were skinned/inconclusive).
- **Mid-write hazard confirmed:** editing forge files while the game is launching/running corrupts what it reads (crash). Always edit with the game fully closed (added a `GRB.exe`-running guard to the staging scripts).

### Method note — the effective gravity value
- First tests used `(120,0,150)` — gravity **reversed and ~12× over-cranked** (magnitude ~192 vs default 10–15). We initially blamed this for a crash ("sim blow-up"), but the crash is at the *pre-engine* splash, so that theory is **wrong** (cloth isn't loaded yet). Switched to **per-cloth vector negation** (same magnitude, reversed direction) as the stable, clean control value regardless.

### OPEN / in progress
- **THE control test (in progress):** does editing a cloth's gravity visibly move a genuinely-simulated garment? Reversed-gravity now delivered the right way — edited the 56 cloth `.data` files **in the tester's `Extracted\DataPC.forge\` working folder** (originals backed up), for a normal **ATK repack**. Awaiting the in-game result on the Golem Cape (menu-standing pose is the clearest tell: hem hangs **down** vs. lifts **up**). Outcome decides whether cloth edits reach the render at all, and retroactively makes the ghillie null meaningful or not.
- Ghillie gravity flip showed **no visible change** — but ghillies appear skinned/pinned (invalid subject); inconclusive pending the coat/cape control.

### Deliverables / state
- Scratchpad only (NOT for the repo as-is): `forge_stage.py` append-repoint writer **(launch-unsafe — see above)**, `prep_*`/`stage_*` batch cloth-gravity pipelines, an ffmpeg-based video→contact-sheet frame extractor for reviewing in-game clips. The **working** delivery path = reverse gravity on the cloth `.data` in the Extracted working dir → ATK repack (the tool's designed path; raw/uncompressed `.data` blocks are ATK- and game-readable).

### Side thread (started) — real-mod corpus
- Began surveying the tester's **207-mod** corpus (`Downloads` + `Extracted\GRBMods`) to write a **"GRB mod anatomy"** reference note (working-folder → forge-family mapping, BuildTable+resources split, the `23_-_TEAMMATE_Template` item-def container, install-by-ATK-repack). Confirmed on two samples: `CFLIONNESS_JPCVest` = BuildTable (DataPC) + mesh/UI (`DataPC_Resources_patch_01`); `APC9 RepScorpionCQC` = `dbcontainer/ extra/ resources/` split. Cataloging workflow running; note to be added under `reference/` when it lands.

---

## Entry — 2026-07-02 (later) — DEFINITIVE: GRB cloth runtime IGNORES `ClothProperties.Gravity`; the real load-blocker was RAW vs Oodle-compressed `.data` (append-repoint theory RETRACTED)

A full day of in-game testing produced two definitive results and two retractions.

### Headline
1. **The load-blocker was the `.data` BLOCK FORMAT, not the forge-packing method.** A cloth `.data` written with **RAW/uncompressed** blocks (what `clothwrap.write_data` produces) makes GRB **crash or hang at load**. The *same* edit written as **Oodle-compressed** loads fine. Both a custom append-repoint writer **and** a clean ATK repack fail with raw-block cloths and both succeed with compressed ones — so the packing method was never the cause.
2. **GRB's cloth runtime completely IGNORES the per-cloth `ClothProperties.Gravity` (section 4357).** Proven on a genuinely *loose* garment (Tactical Kilt, `Cloth_FTP_Kilt`): reversing gravity (direction) → **0 visible change**; setting gravity to **(0,0,0)** (magnitude) → **0 visible change**. The edit was confirmed **live in the repacked forge (Z read back +10, then 0) and NOT patch-shadowed**. So GRB applies a global/scene gravity to cloth; that field is inert authoring metadata at runtime.

### VERIFIED (new)
- **Game-loadable compressed cloth `.data` spec** (the writer GRB needs): keep the 1st `CompressedFileData` (metadata) verbatim; rebuild the 2nd CFD as `u64 magic 1154322941026740787` + `CompressionInfo{i16 ver=3, u8 algo=3, u16, u16 blk=32768}` + `i32 blockCount` + `blockCount×(i32 uncomp, i32 comp)` + per block `[u32 checksum][comp bytes]`, where **checksum = `adler32(compressed_bytes, seed=0)`** (zlib's default seed is 1 — GRB seeds 0), each 32 KB chunk compressed with **Oodle Mermaid (codec 9)** via the game's `oo2core_7_win64.dll::OodleLZ_Compress`; store a block raw iff comp≥uncomp. Verified: a no-op compressed round-trip decompresses byte-identical through the game DLL, and single/edited compressed cloths **launch**. ⇒ **`tools/clothwrap.py` must be changed to compress — its current raw-block writer produces unloadable cloths.**
- **Edit pipeline + the community workflow (corrected by the maintainer).** Modders extract a forge to `Extracted\<forge>\` **once**, then edit/add/remove there **incrementally over time and repack from it** — you do NOT re-unpack per edit (ATK skips the unpack if the folder exists, and only re-backs-up the forge on a *fresh* extract, i.e. after you delete the folder). So `Extracted\` is the **persistent source of truth**, not something you regenerate each session. **The pitfall we hit** wasn't "didn't re-extract" — it was a forge whose *live* copy had **DIVERGED** from its Extracted folder: `DataPC.forge`, which this user "doesn't normally touch," so its Extracted was the original first-unpack while the live forge had gained unlock+clothing mods **via another path**. Repacking that stale Extracted silently **reverted those mods** (re-locked items, broke buildtable↔resource links → crash-on-mouseover). **Rule:** before repacking a forge you haven't been maintaining in `Extracted`, **verify `Extracted`==live thoroughly** (all entry sizes + byte-compare the BuildTable/unlock records — a 16-sample check falsely passed the stale folder); if diverged, **re-extract that one forge once** to resync (ATK re-backs-up on the fresh extract), then edit incrementally. Once in sync: edit the cloth `.data` **compressed** in place → **ATK repack** → launch; mods preserved.
- **Cloth↔garment identification:** every `Cloth` carries an internal **`Sim_<TargetMesh>_LOD<n>`** body name = the authoritative garment map (dumped for all 56). Two garments people assume are cloth are not: the **"Golem Cape / Field Medic" raid vest cape has NO `Cloth`/`SoftBody` resource** (there are **zero** `SoftBody`/`MotionSoftBody` entries in `DataPC.forge`) → skinned/bone secondary-motion; **ghillie strands are pinned** (`VertexMaxDistance`≈0 — move from motion, not gravity). Neither was a fair gravity subject; the Kilt (loose hem) was.

### RETRACTED
- ❌ Earlier-today's "**append-repoint forge editing is NOT launch-safe; ATK repack is the launch-safe way**" (the ⚠️ KEY FINDING in the earlier 2026-07-02 entry). Both methods behave identically: raw cloth → fails, compressed cloth → loads. The forge structure was never the issue.
- ◑ "`ClothProperties` (incl. gravity) is tunable for GRB" — as implied by [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) and [[grb-forge-and-atk-facts]]. True for ATK's *supported* games; **for GRB at runtime, gravity is not read.** (Other fields untested — see open.)

### OPEN / next (the actually-useful levers)
- Whether **other** `ClothProperties` fields (**stiffness, damping, friction, wind**) or the per-vertex **`VertexMaxDistance`** paint ARE runtime-effective. Gravity being ignored does not imply all cloth params are; these are what a modder would tune to change drape/stiffness, and they're **untested**. Same pipeline; a floppy-vs-stiff kilt is the tell.
- Fold the compressed-`.data` writer into `tools/clothwrap.py`.

### Deliverables / state
- Scratchpad: game-format compressed cloth `.data` writer (Oodle compress + `adler32` seed-0), the re-edit/verify pipeline, an ffmpeg video→contact-sheet reviewer. User's forge restored to the pristine modded backup; a **hash-verified tangible backup** at `D:\GRB_KnownGood_ForgeBackup_2026-07-02\`.
- New KB draft: [`reference/mod-anatomy.md`](../reference/mod-anatomy.md) (18-mod survey; `23_-_TEAMMATE_Template` = player **and** teammate customization, not teammate-only).

---

## Entry — 2026-07-02 (end) — CORRECTION: the gravity we edited was section 4357's copy; a dedicated `ClothPropertiesGravity` (4398) was never touched

Caught at session's end, before starting fresh next time. Gravity exists in **two** places per cloth: the `ClothProperties` (**4357**) struct field we edited all day (offset 2, `Vector3`), **AND a dedicated `ClothPropertiesGravity` section, type 4398** — a 12-byte `Vector3` carrying the *same* value — which **we never edited.** Verified both present with identical values in `Cloth_HunterCoat`, `Cloth_FTP_Kilt`, `Cloth_ArcturusWarrior_Ghillie_JacketBody2` (all default `(0,0,-10)` / `(0,0,-15)`).

⇒ **The "GRB ignores cloth gravity" headline (the DEFINITIVE entry above) is DOWNGRADED.** Confirmed: 4357's gravity field is inert. **Untested:** section **4398**, which is the *likely* runtime field. The kilt null is fully consistent with "we edited the wrong copy," not "gravity is ignored." Same pattern almost certainly applies to the other params — dedicated sibling sections (**4397** Wind, **4360** `ClothPropertiesConstraintsStiffness`, …) probably hold the live values, not the 4357 struct fields (see [`reference/cloth-section-types.md`](../reference/cloth-section-types.md)). **This likely explains ALL the day's nulls: every gravity edit hit 4357.**

**Next session, step 1 (see [`meta/next-session.md`](next-session.md)):** reverse/zero gravity in **section 4398** (12-byte Vector3, floats @ 0/4/8) on the Tactical Kilt, leave 4357 alone, run the proven pipeline. If the hem moves → gravity is a live lever after all and the "ignored" conclusion is retracted.

---

## Entry — 2026-07-03 — Params all null on the kilt; discovered a FORGE SHADOW; patch-override HANGS; Sami's real goal reframes the effort

### Environment
Same desktop workstation (H:\ Steam install). Resumed the 2026-07-02 "STEP 1" plan (re-test gravity in the dedicated section **4398**).

### VERIFIED (in-game this session)
Ran a full battery of cloth-parameter edits on the **Tactical Kilt** — a **confirmed genuinely-simulated** garment (the maintainer verified the hem sways/lags like normal Ubisoft cloth). Each edit was derived from pristine bytes, byte-verified (only the target section changed), Oodle-compressed, and **confirmed read back live from the *repacked* `DataPC.forge`**:
- **Gravity §4398** (dedicated `ClothPropertiesGravity`) reversed `(0,0,+10)` → **no visible change.**
- **Stiffness §4360 → `(0,0,0)` + Wind §4397 `WindVelocity → (100,0,0)`** (combined screen) → **no visible change.**
- **MaxDistance (per-vertex paint) → fully free (255)** → **no visible change.**

So: edits reach the game, the subject genuinely simulates, yet nothing moves. Provisional read was "runtime uses a compiled cloth, ignores the editable resource" — **but a confound overturns that:**

### 🚨 THE FORGE SHADOW (overturns prior "inert" conclusions)
- **44 of 56 `Cloth` resources are DUPLICATED across two *base* forges:** `DataPC.forge` **and** a WorldMap region forge — `DataPC_TGT_WorldMap_Bootstrap_Split.forge` (41, incl. the kilt / both Walker coats / HunterCoat), `_Darkwood_Split` (3), `_MaungaNui_Split` (2). Same 64-bit ID + name in both. Only **9** cloths are DataPC-only (all NPC/civilian — IanBlake trench, FTciv dress, kids). `TP_Top_Bodark_Trench_Cloth` is the lone cloth in **4** forges (both bases + both patches).
- **We had only ever edited the `DataPC.forge` copy.** If the game loads the WorldMap-base copy (or it mounts with priority), every null — this session's **and last session's "4357 gravity inert DEFINITIVE"** — is **SHADOWING, not runtime-inertness.** Last session's "confirmed live, not patch-shadowed" only proved the edit was *in* DataPC.forge, not that the game *loads* that copy, and it checked only *patch* forges, missing the WorldMap *base* duplication.
- **⇒ DOWNGRADE: "GRB cloth gravity/params are runtime-inert" is no longer supported.** Confounded by the shadow; unresolved. (doc-11's gravity claims reconciled accordingly.)

### Patch-override (the proper mod path) → HANGS
Per the maintainer (practitioner): normal cloth-mod path = a **patch-forge override** (overrides base by ID → sidesteps which-base-wins). Template: Bodark cloth ships as an override in **both** `DataPC_patch_01` and `Bootstrap_Split_patch_01`.
- Override of the 2 kilt cloths into `DataPC_patch_01` only (combined: reversed gravity + free MaxDistance) → **game HANGS ~34% into the post-title load** (1.98 GB, CPU spinning, Responding-but-stalled; no crash report ⇒ hang, not crash). Recovered.
- Retried a **gentle STABLE** override (reversed gravity only, pinning intact — verified stable) in `DataPC_patch_01` only → **hangs identically.** A stable edit hanging **rules out sim-instability** → the hang is the **override mechanism** itself, most likely an **incomplete override** (base copy in 2 forges, patched in only 1 → conflicting versions).
- **STAGED, NOT YET RUN:** the *complete* Bodark-pattern override — gentle gravity in **both** patch forges, base `DataPC.forge` restored pristine (confound removed). This is the decisive **"can a modified cloth take effect at all?"** test. Files staged in both patch `Extracted\` folders on the desktop; awaiting a 2-patch repack + launch.

### 🎯 SAMI'S REAL GOAL — reframes everything (verbatim in [`project-goal.md`](project-goal.md))
The north star is **NOT parameter tuning.** SamiPuma wants to **replace a flowing coat with an outside-source poncho and give the poncho the coat's cloth physics** — i.e. **REBIND vanilla cloth to NEW geometry.** His method (weight-paint transfer + point the item at the coat's `.cloth`) fails because the `.cloth` is **welded to the coat's exact vertices**. **KEY LEAD:** GRB's separate **`.skeleton`** bone-physics (rigid hanging items — thermoses) **DOES** transfer to new meshes via weight-paint, and **ATK can read GRB skeletons** (unlike cloth). ⇒ Real levers: **(A) cloth→mesh rebind** (render↔sim remap; hard) and **(B) the `.skeleton` bone-cloth path** (maybe more practical). Parameter tuning is orthogonal — but the param/shadow/override tests remain a **prerequisite**: can a *modified* cloth take effect in-game *at all*? (= the staged both-patches test.) If never → (A) is dead, pivot to (B).

### Technical facts nailed
- **GRB per-vertex cloth paint layout:** the 6 per-sim-vertex byte arrays (`VertexMaxDistance`, BackStop, GravityScale, Damping, SkinWidth, Friction — MaxDistance first, order from ATK `MotionSoftBodyLOD`) are stored **BARE `byte[V]` contiguous in GRB** — NOT length-prefixed as ATK's supported-game reader expects — as `6×V` bytes ending exactly at the ClothPackage's `int32 blobLen`. Verified both kilt cloths/LODs. (Spatial correlation to §4363 positions was weak → paint uses a different vertex order than the position buffer.)
- From ATK source: `§4360 ClothPropertiesConstraintsStiffness` = `float[3]` (default 1.5s; kilt 0.5/0.6/0.5); `§4397 ClothPropertiesWind` = `bool WindIsEnabled` + `Vec3 WindVelocity` + 2 densities + 3 rotation vecs (57 B); `ClothDefinition.UseWind` = byte 8 (kilt: true, WindVelocity=0).

### Deliverables / state
- New [`meta/project-goal.md`](project-goal.md); doc-11 gravity claims downgraded (shadow confound); this entry.
- Scratchpad (desktop, temporary): staging/edit/verify scripts, extracted ATK dll + decompiles, staged variants under `Extracted\_kilt_cloth_tests\`, the both-patches override in the patch `Extracted\` folders. Base `DataPC.forge` + `DataPC_patch_01` restored clean this session. Backups: `D:\GRB_KnownGood_ForgeBackup_2026-07-02\`.

### Next session (reoriented — see [`next-session.md`](next-session.md))
1. (If in-game) run the staged **both-patches** override → does a modified cloth take effect / even load? Fork to (A) or (B).
2. **Pivot to Sami's goal:** (A) cloth→poncho rebind and/or (B) the ATK-readable `.skeleton` bone-cloth path. **Stop parameter-tuning.**

---

## Entry — 2026-07-09 — Session resume: repo re-verified, staged both-patch test confirmed NOT run, KB reconciled to the 2026-07-03 shadow findings

### What I did
Resumed on the same H:\ workstation. Confirmed the local clone is current with GitHub (`main` @ `d6b1ee0`; the `docs/cloth-2026-07-02-corrections` branch is now **merged** — its "4357 gravity inert" claim was properly downgraded by the later shadow-confound commit `7a7e7f7`, so the old "don't merge yet" hold is resolved). Ran a full re-read of the KB + an on-disk state check, then reconciled every passage that still asserted the downgraded param claims or the one-base-copy-per-ID model.

### VERIFIED (new — on-disk state)
- **The decisive both-patch-forge kilt test has NOT been run.** SHA256 of all three live forges (`DataPC.forge`, `DataPC_patch_01.forge`, `DataPC_TGT_WorldMap_Bootstrap_Split_patch_01.forge`) is **byte-identical** to the `D:\GRB_KnownGood_ForgeBackup_2026-07-02\` known-good set. The staged `90001`/`90002` override is NOT live; the forges are in the clean restored state (the 2026-07-03 03:12 mtimes are from that restore, not a landed edit).
- **The staged override is intact and ready.** `90001_-_Cloth_FTP_Kilt.data` (304,860 B) + `90002_-_Cloth_0X193A6210EB9.data` (318,759 B), byte-identical pairs, sit in BOTH `Extracted\DataPC_patch_01.forge\` and `Extracted\DataPC_TGT_WorldMap_Bootstrap_Split_patch_01.forge\` (sizes +1/+3 B vs pristine — single-field edit).
- **Backups intact:** D:\ set hash-verifies; plus `.pre-coattest-backup` / `.pre-ghillietest-backup` files and `_kilt_4398_test_ORIGINALS`. Rollback fully covered.
- **`Extracted\` root =** `H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint\Extracted\`. `_kilt_cloth_tests\` holds **8** variant folders (README documents 6; `6_paint_PIN_all0` + `7_paint_FREE_all255` were added 07-03 01:48).
- ~~⚠️ **The AnvilToolkit executable was not found on disk** (only the `AnvilToolkit_Release_v1.3.1-…` zip in Downloads) — likely needs re-extracting before the next repack.~~ **WRONG — corrected 2026-08-09:** ATK is installed and in active use at **`E:\Anvil Toolkit\AnvilToolkit.exe`** (v1.3.1). The 07-09 search simply never covered `E:\`. No re-extraction is needed before a repack.

### Reconciliation (docs corrected this session)
Rewrote every passage still asserting "gravity §4357 verified inert" or framing §4398 as "the untested live-candidate" — all now read: nulls **confounded by the forge shadow, unresolved**. Files: `docs/11` (runtime caveat, render↔sim update, open-question 7), `meta/sources.md`, `tools/clothwrap.py` (docstrings + prints), `tools/README.md`. Added the **forge-shadow caveat** to the one-base-copy-per-ID model in `docs/06` (new callout + consequence-rule-1 exception + open-question), `docs/07`, `reference/forge-inventory.md`, `reference/mod-anatomy.md`, `reference/glossary.md` (+ a new **"Forge shadow"** glossary term), and `examples/case-study-usp-tactical.md`. Documented GRB's **BARE `6×byte[V]`** per-vertex paint layout in `docs/11` and `reference/cloth-section-types.md`, and an ATK-vs-GRB divergence caveat in `AGENTS.md`. Added `4359`/`4360`/`4398` to `tools/motioncloth.py` `SECTION_NAMES`. Folded **10 parked leads** into `meta/next-session.md`.

### Questions answered / opened
- **Answered:** Is the staged test run? **No** (hashes prove it). Are backups safe? **Yes.**
- **Open (unchanged):** the decisive both-patch-forge test still needs an in-game run; re-extract the ATK exe first; and after the repack, **hash-verify the patch forges actually changed** — ATK dropping never-before-seen IDs (90001/90002) is an unverified risk (fallback = overwrite the existing kilt IDs 34800/34793 rather than mint new ones).

---

## Entry — 2026-08-09 — BuildTable XML structure; the "renumber to 1" practice, disambiguated

### What I did
Followed up a *Tier 1 Imports* screenshot the user asked about ("renumber mod files to 1"), then read the source material via the Discord bridge. Primary sources, all **Tier 1 Imports** (guild `1302392670181916722`):

- **`#mod-tutorials`** thread *"Super short and simple way to move mods to another slot"* — msg/thread `1414435798090256437`, by **SAMIEVILPUMA**, 2025-09-08, 38 👍. Full 10-step procedure + **two screenshots of a real ATK BuildTable XML export** (`Screenshot_2025-06-17_211627.png`, `…211641.png` — `0_-_TP_Pants_511Apex.xml`, `tool="AnvilToolkit" toolVersion="1.2.10"`). Both images read directly.
- **`#on-topic`** install guide, posted ≥4× — msgs `1525051213945503844`, `1525059603858194462`, `1525174023540179047`, `1525198009800065235`. The "Small advice" renumbering block is the tail of *this* guide, not of the slot-move thread.
- Renumbering field reports: `1532105102658244873` (SamiPuma states the mechanism), `1533008421249482883` (adrian), `1533475170650685440` / `1533475558418157600` (Jen Jen), `1532445093724684360` (DeckardX, ATK renumbers on drag-drop), `1534303468192530723` (Lucklens release note). A guild search for "renumber" returns **151** hits — this is high-traffic practice, not a fringe habit.

### VERIFIED (new)
- **BuildTable XML has two distinct ID spaces.** The root `<BuildTable ID="1778867967382">` and every `Handle`/`FileReference` value are **real 64-bit resource IDs** (embedded `ClassID`s). But `ID=` on `BuildColumn` / `PropertyPath` / `RowSelector` / `BuildTags` is a **file-local serialization handle**, allocated as a sequential counter from **`0xF8000000`**: observed `4160749568/69/70/71/72` = `0xF8000000`–`0xF8000004` and `4160749580/81` = `0xF800000C`/`0xF800000D`. This is exactly why the slot-move procedure works — you swap the body, keep the root ID, and the game still resolves the destination slot.
- **`CRC32(typeName)` type ids appear inside BuildTable XML**, in `DynamicProperty` → `<Value Name="DataType" … HashName="…">`. Confirmed `zlib.crc32(b"GraphicObject") = 3966419799` matching `HashName="GraphicObject"`, and `BuildTable = 585940579` (already known). Added **`GraphicObject` / `3966419799` / `0xEC6AC357`** to [`reference/resource-type-ids.md`](../reference/resource-type-ids.md).
- **ATK prints unresolved *field-name* hashes as `x<HEX>`** — `x73B5D0A0` (`1941295264`), `x67660D91` (`1734741393`) in the same export. Distinct from a resolved `HashName`.
- **`TEAMMATE_Template` confirmed from live data, not folder names.** A *pants* BuildTable resolves its own handle to `Path="DataPC\TEAMMATE_Template\TP_Pants_511Apex.BuildTable"`. Also visible: gender variants as `tag_MAL` / `tag_FEM` BuildTable handles (IDs `516281366872` / `…871`).
- **ATK's XML round-trip is: double-click `.buildtable` → save → sibling `.xml`; right-click `.xml` → Compile → BuildTable.**
- **Nested containers repack inside-out** — `TEAMMATE_Template` / `Dbcontainer` first, wait, *then* `DataPC_patch_01.forge`. Explicit in the install guide; was absent from our workflow docs.
- **ATK assigns its own leading numbers on drag-and-drop into the Game Explorer**, so an in-ATK import and a plain file-copy into `Extracted\` do not behave the same way.

### INFERRED (new)
- The `Type` UInt32 on `DynamicProperty` (`0x1C0000`, `0x120000` — both `<byte> << 16`) is a slot/usage code. Unknown.
- `BuildColumn`/`DynamicProperty` `Index` values are sparse (`1, 2, 10`; `13, 18`) → meaningful slot numbers, not positions.
- `ForceBuiltTableTOCOrder` (empty in this sample) implies an explicit TOC-ordering override for built tables.

### Questions answered / opened
- **Corrected an over-strong claim made earlier this session.** I initially judged *"renumber to 1 so mod files won't overtake vanilla files"* simply **false**, reasoning that override is `ClassID`-keyed and the leading number is only a sort label. The engine-level reasoning is right, but it answers the wrong claim: SamiPuma means **filesystem overwrite in the unpacked working folder** — *"if you renumber/rename you won't ever overwrite vanilla files"* (`1532105102658244873`). Copying a mod file whose exact `<N>_-_<Name>.<ext>` filename already exists in `Extracted\` silently replaces that entry. Renaming genuinely prevents that. Both layers are now written up in [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md).
- **Still an overstatement in the other direction:** mods shipped as *"renumbered to 1 to avoid replacing vanilla files"* (`1534303468192530723`) will still override vanilla if their resources carry vanilla `ClassID`s. Renaming protects the file on disk; only the embedded `ClassID` decides what the game replaces.
- **Open — does renumbering ever change in-game outcome?** Field reports conflict (a vest that showed UI-only until renumbered, vs. mods that work either way, vs. mods that fail even after). The disk-collision mechanism explains the positive report without engine involvement. The only plausible engine path is two entries sharing a real ID inside one forge, where write order (which the leading number controls) decides — but vanilla forges have zero duplicate IDs, and peer priority is still open. **Test:** reproduce the vest case, use `data_inspect.py` to check for a filename collision before renumbering.
- **Open (BuildTable):** the `Type` code; whether `ForceBuiltTableTOCOrder` is ever populated; resolve `x73B5D0A0`/`x67660D91`; whether the copy boundaries hold for non-gear BuildTables (weapons via `dbcontainer`, solid-colour mods). Only one export (pants, ATK 1.2.10) has been seen — a second category would confirm which elements are universal.
- **Beards fan out like hair** across headgear-compatibility variants — every relevant BuildTable must be edited. Recorded in [`reference/mod-anatomy.md`](../reference/mod-anatomy.md); no sample in the 18-mod corpus.
- **Bridge limitation noted:** Discord message bodies truncated at ~1500 chars until the user updated VCB mid-session; the full procedure came through afterwards.

### Docs written this session
New: [`reference/buildtable-xml.md`](../reference/buildtable-xml.md). Updated: `docs/03` (cross-link), `docs/07` (nested repack order, collision warning, BuildTable XML pointer), `docs/08` (new "Renumber your mod files to 1" section), `reference/resource-type-ids.md` (`GraphicObject` + BuildTable-XML usage), `reference/mod-anatomy.md` (TEAMMATE_Template confirmation, beards row, extension-routing table + inside-out repack), `README.md` (reference index).

---

## Entry — 2026-08-09 (second) — Localization/renaming and hex item swaps; two new technique classes

### What I did
Continued absorbing *Tier 1 Imports* `#mod-tutorials` threads (guild `1302392670181916722`, forum `1302692674863763586`). The user intends to work through the whole forum, so this session also established [`reference/community-tutorials.md`](../reference/community-tutorials.md) as the thread→page index. Sources:

- **"Renaming ingame items (or basically any visible text you could think of)"** — thread/msg `1485672994138358001`, **ViruS**, 2026-03-23, 14 👍. Full post + 25 replies. Attachment `image.png` on msg `1517910027392909473` read directly (a live `DataPC_patch_01.forge\Extracted` listing).
- **"How to swap out bandage slot for another item (and do hex item swaps in general)"** — thread/msg `1481311357134704753`, **spncryn**, 2026-03-11, requested by *steven*. Full post + 25 replies, including Tenebrae's clarification.

### VERIFIED (new)
- **The 64-bit ID model holds in DB records, and the encoding is little-endian.** spncryn's three worked IDs decode as LE uint64: `53 D0 C7 E7 64 01 00 00` → `1532896989267`; `51 77 EB 97 43 01 00 00` → `1389823227729`; `5B B4 BE B4 89 01 00 00` → `1690954544219`. Same magnitude band as ClassIDs verified from other angles (`1707208440119`, `1778867967382`, `1661865036083`). **Independent corroboration of the ID model from hex editing rather than ATK.** Characteristic shape: trailing `01 00 00` / `00 00`, so IDs are visually obvious in a dump.
- **`0_-_Game Bootstrap Settings.data` has a known purpose now.** It holds `DBToolSetting` slot/tool records (e.g. `DBItemSetting_HealingItemEssence_Bandages.DBToolSetting`); the item objects themselves (`*.HealingItemEssence`) live in `DBContainer`. The entry was previously only a name in `docs/03`.
- **Live `DataPC_patch_01.forge\Extracted` listing** (13 items, ATK **1.3.4**): `0_-_Game Bootstrap Settings.data`, `1_-_DBContainerEntry_0X104634F921.data`, `23_-_TEAMMATE_Template.data`, `24_-_MIS_Y2E4_Katya_Maksimov.data`, `26_-_TP_BackPacks_Bivouac.data`, `28627_-_WI_ASR_Mk17_CQC.data`, and the seven `LocalizationPackage_English(US)*` containers at `29523 / 44689 / 45089 / 45346 / 45470 / 47002 / 47602`. Independently confirms `23_-_TEAMMATE_Template` and the `Extracted\<forge>.forge\Extracted\` working layout.
- **English (US) localization is split across seven containers** with stable suffixes `(none) / _E015 / _1L2 / _1E2 / _1E3 / _1L3 / _2E4`. Items are scattered across them and **may appear in more than one** — a partial edit silently fails.
- **`&` in a localization string corrupts the file** (raw ampersand is invalid XML); the fix is `&amp;`, not avoidance. Cost one modder their work.
- **ATK renders unresolved *name* hashes as `0X<HEX>`** (`DBContainerEntry_0X104634F921`) — the same convention as `x<HEX>` for field names in BuildTable XML.

### INFERRED (new)
- The localization suffixes (`_E015`, `_1L2`, `_2E4`, …) look like content/expansion partitions — episode and title-update batches. Unconfirmed.
- Item swaps succeed between objects sharing an **activation model** and fail otherwise (stealth camo is called out as not swappable). Informal, from practitioner experience.

### Questions answered / opened
- **Answered — a major usability trap:** a hex item swap changes an item's **function but not its item-wheel icon**. *"it looks like a duck, but it quacks like a lion"* (Tenebrae). The tutorial's requester lost days to this, concluded a working swap had failed, and broke his install trying to fix it. **Test by using the item, not by looking at it.**
- **Second field case on the renumbering question** (see the first 2026-08-09 entry). Localization edits compiled and repacked correctly but didn't appear; the fix was consolidating the XMLs into one container **renumbered to `1_-_`**, and it worked. Still confounded — the fix bundles consolidation with renumbering — but it's now two independent reports where the leading number coincided with an in-game behaviour change. Recorded in `docs/08` and `docs/12`. **This raises the priority of the controlled test.**
- **Open — ID byte offset in DB resources.** spncryn says "bytes 1-8"; our `resource-type-ids.md` layout says a payload begins with a `FileHeader` byte, putting the ClassID at offset 1. Either these types write no header byte, or the phrasing is loose. Needs a hex check against a real `.DBToolSetting`.
- **Open — ATK 1.3.4 is in the wild**; this KB's format facts were decompiled from **1.3.1**. Worth confirming nothing relevant changed before treating 1.3.1 behaviour as current.
- **Open — Spncryn's BuildTable tutorial** is referenced as the thorough method for cross-category slot moves but has not been located. Tracked in `community-tutorials.md`.
- **Open — can the item-wheel icon be re-pointed** by the same hex technique, closing the "looks like a duck" gap?

### Docs written this session
New: [`docs/12-localization-and-text.md`](../docs/12-localization-and-text.md), [`reference/hex-item-swaps.md`](../reference/hex-item-swaps.md), [`reference/community-tutorials.md`](../reference/community-tutorials.md). Updated: `docs/08` (second field case), `reference/resource-types.md` (new "Gameplay database records" section), `README.md`.

---

## Entry — 2026-08-09 (third) — §4395 and §4658 decoded and BOTH ruled out as the rebind lever; found ATK's 22-section blind spot

### What I did
Took parked lead #1 ("`§4395 ClothPropertiesMeshMappings` + `§4658 ClothEditorDataClothID` are undecoded… plausibly the exact rebind lever"). Answered it two ways: decompiled the two classes out of `AnvilToolkit.dll`, and swept the whole on-disk cloth corpus to see what vanilla actually stores. Corpus = every `*Cloth*.data` under `…\Ghost Recon Breakpoint\Extracted\`: **205 files seen, 81 containing real `ClothPackage`s, 156 `MotionBody`s**.

### VERIFIED (new)
- **§4395 `ClothPropertiesMeshMappings` is `bool[64]`** — ATK's reader is `for (i=0;i<64;i++) MeshMappingsEnabled[i]=br.ReadBoolean();`. Payload is **64 bytes in all 156 bodies**. It is an **enable bitmap, not a mapping table** — it contains no binding data whatsoever. Vanilla uses only two values: slot `0` alone (129 bodies) or slots `0`+`1` (27 bodies). Slots `2–63` are never used → the engine supports up to **64** mesh mappings per body while shipped content uses 1–2.
- **§4356 `ClothDefinition` carries `sbyte MeshMappingsCount` at offset 24**, 40-byte payload in all 156 bodies, values ∈ {1 (6 bodies), 2 (123), 3 (27)}. Correlation with §4395 is deterministic: `MMC=1`→slot{0}, `MMC=2`→slot{0}, `MMC=3`→slots{0,1}. `UseMeshMappingTangentSpace` is **true in all 156**.
- **§4658 `ClothEditorDataClothID` is a null-terminated STRING, and it is EMPTY in all 156 vanilla bodies** (payload = a single `0x00`). It is not a numeric ID, not a `ClassID`, and references nothing. The old table entry "the cloth's editor ID (attachment)" implied a binding role it does not have.
- **Both sections occur TWICE per `MotionBody`** (paired with the two §4357 `ClothProperties` blocks), and both copies are byte-identical in every body. A tool editing only the first copy yields an inconsistent resource.
- **ATK's section map is complete for ATK but NOT for GRB.** `MotionSectionFactory.ReadSection` has **64** `case` entries; the corpus uses **86** distinct section types. **22 types are populated in real GRB cloths with no ATK class at all** — they fall through to `UnknownSection`. Because this KB's cloth-section knowledge was transcribed *from ATK*, these 22 have never been examined. Full list + size profile now in [`reference/cloth-section-types.md`](../reference/cloth-section-types.md).
- **The 4403–4410 block is the leading unexamined structure.** Four `12-byte counter → variable buffer` pairs, exactly once per body in all 156. `size(4404)==size(4408)`, `size(4406)==size(4410)`, and `size(4404)==2×size(4406)` — two parallel index+payload arrays, echoing the 1–2 enabled §4395 slots.
- **ATK on this machine is v1.3.1** (`E:\Anvil Toolkit\`, README changelog ends at 1.3.1) — the same build every format fact here was decompiled from. **Corrects the 2026-07-09 entry's "AnvilToolkit executable was not found on disk"**, which was wrong: that search never covered `E:\`.
- **Bodark-trench precedent, refined.** `1687/42/47351_-_TP_Top_Bodark_Trench_Cloth` all carry `Sim_Tsec_IanBlake_Trench_LOD0` at **186 verts / 305 tris** — geometrically identical to `30291_-_IanBlake_TrenchCoat_Cloth` LOD0, confirming the parked lead #2 claim. But the sim-mesh name suffixes **differ** (`0x1DE8F05F3C9` vs `0x15FE3444A17`), so it is a **copy, not a shared reference**; and Bodark declares `MeshMappingsCount=1` with only LOD0, vs IanBlake's `3` with LOD0+LOD1.

### INFERRED (new)
- The 4403–4410 buffers are **render-scale, not sim-scale**, and are the most plausible home for the render↔sim mapping. **Not confirmed — the one decisive check available came out negative:** `TP_WalkerCoat` LOD0 has **1816** render verts (per the KB) but only **636** elements in `4404`, so this is *not* a one-entry-per-render-vertex table. Its meaning is unknown.
- Why `MeshMappingsCount` exceeds the enabled-slot count for `MMC∈{2,3}` is unresolved; possibly the final declared slot is implicit/reserved.

### Questions answered / opened
- **Answered — parked lead #1 is CLOSED, negatively.** Neither §4395 nor §4658 is the rebind lever. §4658 has nothing to repoint; §4395 is a gate, not a binding. This removes a lead that had been flagged "top cloth priority" since 2026-06-30 and twice deferred.
- **Answered — ATK version in use is 1.3.1**, so 1.3.1-derived facts are current *for this machine*. The separate open question ("1.3.4 is in the wild") is unchanged: a 1.3.4 build has still not been examined.
- **Opened — what are the 22 unmodeled sections?** No ATK reader exists to crib from, so decoding means working from bytes directly. Suggested start: the 12-byte counters (`4403`/`4405`/`4407`/`4409`, presumably 3×`int32`) and whether their fields predict the buffer lengths.
- **Unchanged:** lane 2 STEP 1 (the both-patch kilt repack) is still un-run, and remains the gate on whether *any* cloth-resource edit can ship. Today's work narrows *where* to look; it does not change that dependency.

### Docs written this session
Updated: [`reference/cloth-section-types.md`](../reference/cloth-section-types.md) (completeness caveat; §4395 and §4658 decoded write-ups; §4356 `MeshMappingsCount`; new "Sections GRB uses that ATK does not model" section with the 22-type size profile and the 4403–4410 analysis), [`tools/motioncloth.py`](../tools/motioncloth.py) (`SECTION_NAMES` synced to all 64 ATK classes — was missing 37 — plus a new `UNMODELED_BY_ATK` set; round-trip re-verified byte-exact), [`meta/next-session.md`](next-session.md).

---

## Entry — 2026-08-14 — Chasing a ragdoll question, found route B's mechanism: **Reflex3 skeleton bone-physics**

### What I did
Started from a community question, not from the KB's own backlog. In *Tier 1 Imports* `#shit-talk`
(2026-08-14, ~15:11 ET) **Releptive** observed that Bodarks standing over hostages "legit js DROP…
full on ragdoll drop" when shot, and asked why normal deaths can't do that; **96kamisama** noted
Ready or Not achieves it "not really altering the animation, but it makes the animation transition
faster into ragdolling." The user asked whether it's possible.

Two questions fell out, and both got answered: **(a)** is there any *data surface* in GRB for
death-ragdoll behaviour, and **(b)** what physics systems does GRB actually expose on skeletons.
Method: an index-only sweep of **all 27 forges / 415,177 entries**, a full `ilspycmd -p` decompile
of `AnvilToolkit.dll` v1.3.1, then targeted extraction and Oodle-decompression of real skeleton and
cloth resources straight out of the `.forge` files. **Read-only throughout — nothing in the install
was modified.**

### VERIFIED (new)

**On the ragdoll question — the answer is negative, and cleanly so:**
- **GRB ships no ragdoll resource.** ATK registers `LiteRagdoll` (`2299544533`) plus
  `LiteRagdollCapsule` / `Shape` / `CapsuleGroupFlags` / `ExternalCapsule`, but
  `LiteRagdoll.SupportedGames` lists twelve Assassin's Creed titles and **excludes
  `Game.GhostReconBreakpoint`**. Zero forge entries carry any of those type ids, and none appear
  inside any sampled skeleton payload.
- **No combat animations exist as forge resources.** All **1,564** `Animation` entries
  (`262342271`) are ambient NPC "acting" clips — prefixes `milM`/`CivM`/`civM`/`homM`/`homF`/`outM`/
  `kidM` plus a few creature idles (`Ogre`, `SkyCherubim`, `AirDroidMed`). **0 of 1,564** fall
  outside that set. Keyword sweeps over all 415,177 entry names return **zero** hits for `ragdoll`,
  `hitreact`, `flinch`, `stagger`, `getup`, `takedown`, `rappel`, `aimdown`; `death` matches only
  `[VE] AI_…` **voice** events and DB records. The player/enemy locomotion-death-reaction bank is
  not in the forges.
- **Parked lead #6 is CLOSED.** The `Ragdoll_…` string in `TP_WalkerCoat_Cloth` is a
  semicolon-separated list of **garment-owned collider names**:
  `Ragdoll_Head_130111906;TP_WalkerCoat_Ragdoll_Head_…;…_LeftArm_…;_LeftForeArm_…;_LeftHand_…;
  _LeftShoulder_…(×4);_Neck_…;_RightArm_…;_RightForeArm_…;_RightHand_…` (536 chars, 13 entries).
  Every collider is prefixed **`TP_WalkerCoat_`** and the set is **upper-body only** — no spine,
  pelvis or legs. These are capsule colliders the *coat's cloth* collides against, named after the
  bones they follow. Ubisoft's naming, not a death-ragdoll rig.

**On skeletons — a whole system this KB had never seen:**
- **Every GRB `Skeleton` carries an inline `Reflex3SkeletonConstraints` object** (hash
  `2386539642`). `Skeleton.SupportedGames` includes GRB, and `Skeleton.Read()` reads the field
  under an explicit `version == Game.GhostReconBreakpoint` branch. Confirmed in **all 2,469**
  skeletons across all forges.
- **512 of 2,469 skeletons carry real constraint data** (blob > 8 B); the other 1,957 hold the
  8-byte header only.
- **The GRB blob header is a new constant**: all 512 begin byte-identically with
  `34 12 34 12 a0 f5 2d 00` = `uint32` magic **`0x12341234`** + `uint32` version **`3012000`**.
- **This is exactly why ATK can't read it.** ATK validates
  `Reflex3SkeletonConstraintMagic = 19620929`, `Version = 2`, `ConstraintMagic = 5000004` — none of
  which occur anywhere in GRB's blobs — and gates the parse behind
  `base.Version != Game.Mirage`, so the GRB variant was never validated. ATK still **reads,
  round-trips and Base64-exports** the blob for GRB; it just doesn't interpret it.
- **The constraint model is fully typed in ATK.** `Reflex3ConstraintTypeRegistry`:
  `0` Attachment, `1` BallJoint, `3` BoundingVolume, `6` HingeVector, `7` LookAt, `9` Orientation,
  **`10` Physics**, `11` Position (ids `2`,`4`,`5`,`8` unmapped). `Reflex3Physics` carries
  `ConstrainedObject` (the bone), `UseSwing`, `SwingAxis`, `UseSlide` + `SlideMin`/`SlideMax`,
  **`Gravity`** (default `9.8`), `UseGravityNode`/`GravityNode`/`IsGravityLocal`,
  `UseCollisionInfo`, **`WindFactor`**, and optimized slide/swing info blocks. A complete
  jiggle-bone description.
- **Blob body, partially decoded:** an 8-byte header, then a **constant 9-byte record preamble**,
  then `4×4` `float32` matrices, orthonormal with a `(0,0,0,1)` final row — bone transforms.
  Preamble differs per skeleton (`Player_Kilt_Addon`: `15 25 b5 9c b9 b9 1b 94 92`;
  `TP_HunterScarf_A_Skeleton`: `05 6f e3 82 aa 1f b7 69 7d`).
- **The corpus points straight at the project goal.** `Tsec_Trench_AddonSkeleton` carries
  **43,494 B** of bone constraints — **a flowing trench coat driven entirely by bones, on an
  *addon* skeleton.** Also: `TP_HunterScarf_A_Skeleton` 9,991 B, hair rigs 10–12 KB, backpacks with
  straps 48–62 KB, character `*_Reflex` layers 99–114 KB, and **`Player_Kilt_Addon` 394 B — the
  kilt has bone physics *as well as* its `.cloth`.**
- **Skeletons are forge-shadowed exactly like cloths** — `Player_Kilt_Addon` (id
  `1889064665537`) appears in both `DataPC.forge` and
  `DataPC_TGT_WorldMap_Bootstrap_Split.forge`, byte-identical. Any skeleton override must patch
  both families.

### INFERRED (new)
- The 9-byte preamble reads most naturally as a `uint64` (high-entropy, bone-name-hash shaped) plus
  one tag/type byte. **Unconfirmed** — needs checking against a real bone-name hash from the same
  skeleton.
- In `Player_Kilt_Addon` the first two 4×4 matrices are byte-identical; plausibly a rest/current
  pair, but that is a guess from one specimen.
- Why the hostage-guard kill ragdolls while a normal death plays a canned animation is still
  unexplained by anything on disk. The likeliest reading — a scripted pose with no matching death
  animation falling through to physics — remains **speculation**; no data was found either way.

### Questions answered / opened
- **Answered — ragdoll-on-death is not moddable with today's data surface.** Not "hard": the
  resources aren't there. No `LiteRagdoll`, no death animations, no hit-reaction data in any forge.
  It would need the animation state machine, which isn't shipped as a forge resource. This closes
  the community question honestly rather than leaving it as a maybe.
- **Answered — parked lead #6** (`Ragdoll_…` bone-collider string): decoded, it's garment cloth
  collision, not a ragdoll rig. Remove from the parked list.
- **Opened — ⭐ the strongest route-B lead this project has had.** `Reflex3` is a *bone*-driven
  physics system, and bones are re-bindable by weight-painting — the exact thing `.cloth` cannot
  do. `Tsec_Trench_AddonSkeleton` is a vanilla flowing coat implemented this way. The decode is a
  **port of readers ATK already has**, not a reverse from nothing.
- **Opened — finish the blob decode**: identify the 9-byte preamble, then the per-constraint record
  framing, then map onto `Reflex3ConstraintTypeRegistry` so `Reflex3Physics` fields become
  readable/writable.
- **Opened — constraint type ids 2, 4, 5, 8** are unmapped by ATK. Same species of blind spot as
  the 22 unmodeled MotionCloth sections.
- **Unchanged:** lane 2 STEP 1 (the both-patch kilt repack) is still un-run. Whether a modified
  *skeleton* loads is a separate, equally untested question — and it inherits the same
  shadow-copy and hang-on-load hazards.

### Docs written this session
New: [`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md) (the whole
Reflex3 write-up — GRB blob header, constraint type table, `Reflex3Physics` field list, the
512-skeleton corpus, class-hash table, reproduction steps). Updated:
[`reference/resource-type-ids.md`](../reference/resource-type-ids.md) (Reflex3/ragdoll/skeleton
hashes), [`meta/next-session.md`](next-session.md).

---

## Entry — 2026-08-14 (second) — The layer above the skeleton: `EntityBuilder` names it by 64-bit ID

### What I did
Raven asked in `#shit-talk` (17:18 ET) — of the earlier Reflex3 finding — "yes but it must inherit
those physics from something," and Sylvia asked what the next step up the hierarchy is. Answered it
**empirically instead of by inference**: since Anvil stores cross-resource references as bare
little-endian `uint64` ClassIDs, whatever assigns a skeleton must contain that skeleton's ID
verbatim. Decompressed **every resource in `DataPC.forge`, `DataPC_extra.forge` and both patches —
66,899 resources, 8 unreadable** — and searched for the IDs of four skeletons. Then decoded the
record the ID sits in, and validated the decode. **Read-only throughout.**

### VERIFIED (new)
- **The physics is not inherited. It is embedded in the skeleton resource itself** (established in
  the previous entry: `Reflex3SkeletonConstraints` is an *inline* object, `ObjectPtr` tag 0/4).
  What gets assigned is the **skeleton**.
- **`EntityBuilder` is the assigning layer — nothing else assigns a skeleton.** 37 references
  found; **32 of the 35 non-`Entity` hits are `EntityBuilder`s** (the rest: 3 `Entity`, 2
  `#1767772698` cinematic configs). No standalone `BuildTable` references any of the four.
- **The typed reference record, decoded:**
  ```
  u32  TypeHash   0x24AECB7C == CRC32("Skeleton")   (0xEC6AC357 = GraphicObject, …)
  u16  0x0000
  u8   0x12                                          record tag
  6×   0x00
  u64  ClassID                                       the referenced resource
  u32  Slot                                          attachment slot index
  ```
  **Validated, not assumed:** extracting *every* `Skeleton`-typed record from two builders gave
  **16 records → 16 ClassIDs → 16/16 resolving to real skeletons** in the independent
  2,469-skeleton sweep. **Zero false positives.**
- **A character is a base rig plus a stack of physics-carrying add-on rigs.** `TSec_MIS_Blake(184)`
  assigns 5 skeletons: `Regular_Male_Body_Skl` (no physics), `Regular_Male_Reflex_SklAdd`
  (107,350 B), `Skeleton_IanBlake_Head`, `Player_Props_Addon`, and **`Tsec_Trench_AddonSkeleton`
  (43,494 B) at slot 5, sitting beside `Tsec_IanBlake_Trench_Mcloth_MISSION`**. `PLAYER_Template`
  assigns 11, of which 5 carry physics — including `Watch_Skeleton` (5,556 B),
  `Tpri_Schultz_Beard_Addon` (2,710 B) and `Tpri_Schultz_gloves_addon` (1,166 B).
- **`TEAMMATE_Template` contains a node literally named `PLAYER_SkelAddons`** (at payload offset
  `0x00f35f`), with `Regular_Male_Reflex_SklAdd`'s reference 602 bytes later. Item-level skeleton
  references sit inside the item's own node — the kilt's 803 B after the string `TP_PANT_Kilt`,
  the scarf's after `TP_FullMask_Flycatcher`.
- **`EntityBuilder` is editable through supported tooling.** `EntityBuilder.SupportedGames`
  includes `Game.GhostReconBreakpoint` and its `FileActionType` is **`Xml`** — ATK exports the
  builder to XML and re-imports it. The class is BuildTable-shaped (`BuildColumns`/`BuildRows`)
  **plus** `Template`, `ReplicaTemplate`, `TemplateOverrides`, `Tables`, `Dependencies`, so
  [`buildtable-xml.md`](../reference/buildtable-xml.md) largely applies.
- **⚠️ The trench rig is NPC-only.** `Tsec_Trench_AddonSkeleton` is referenced by exactly three
  builders — `TSec_MIS_Blake(184)`, `TSec_CIN_Blake(184)`, `MIS_Y2E4_Wassili_Kropotkine` — and
  **never** by `PLAYER_Template` or `TEAMMATE_Template`. It is wired into characters, not into a
  wearable gear slot. The player-wearable precedents are `Player_Kilt_Addon` and
  `TP_HunterScarf_A_Skeleton`, both of which **are** in `TEAMMATE_Template`.

### INFERRED (new)
- Which `EntityBuilder` field the records live in is not pinned down — `Dependencies`
  (`List<ulong>`) and the `BuildRows` object graph are both candidates. The record shape is
  verified; its *owning field* is not. Getting an ATK XML export of `PLAYER_Template` would settle
  it immediately and is the cheapest next check.
- `Slot` values are mostly small (1–12) but some are large and byte-aligned (2816, 3328, 4864,
  1792 = multiples of 256). Plausibly a packed slot+flags word rather than a plain index.
  Unconfirmed.

### Questions answered / opened
- **Answered — the hierarchy question.** Full chain:
  `EntityBuilder → (Skeleton, 64-bit ClassID, slot) record → add-on Skeleton → inline Reflex3
  constraints`. Raven's instinct was half right: something *does* assign it, but the physics data
  itself is not inherited from anywhere.
- **Answered — is it re-pointable?** Yes in principle: it is a plain 64-bit ID at a fixed offset in
  a fixed-shape record — the same shape as the community's documented hex item swaps — and ATK
  supports XML round-trip on EntityBuilders for GRB, so it need not be done in hex.
- **Answered — parked lead #10** (which property a BuildTable uses to reference a resource) is
  substantially resolved for skeletons: typed reference records inside the `EntityBuilder`. The
  cloth half is still open, but `TP_TACVEST_Walker_Coat_Cloth` and
  `Tsec_IanBlake_Trench_Mcloth_MISSION` both appear as named nodes in the same builders, so the
  same method will find it.
- **Opened — the goal-shaped experiment.** Add (or re-point) a skeleton record in the **player**
  template aiming at a physics-carrying add-on rig, copying the kilt/scarf entries as the pattern.
  That is the first end-to-end test of route 2B.
- **Opened — `data_inspect.py` mis-parses large EntityBuilder containers.** On
  `TEAMMATE_Template.data` (5.65 MB payload, 173 file blocks) its resource-record walker desyncs
  after the first resource and reports a garbage name and an impossible ClassID
  (`11812857376716750848`). Harmless here — it did surface the `PLAYER_SkelAddons` string — but the
  walker needs a bounds/sanity check.
- **Unchanged:** whether a modified skeleton or builder actually loads is still untested, and
  inherits the shadow-copy and hang-on-load hazards from the cloth work.

### Docs written this session
Updated: [`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md) (new
"The layer above" section — how the reference was found, the record format, the validation, two
build sheets, the full chain, and the NPC-only caveat on the trench rig),
[`meta/next-session.md`](next-session.md), [`tools/README.md`](../tools/README.md). New:
[`tools/entity_skeletons.py`](../tools/entity_skeletons.py) — prints a character's or item's
skeleton build sheet with physics sizes.

---

## Entry — 2026-08-14 (third) — The Reflex3 constraint blob is DECODED

### What I did
Took the open lead from this morning's entry ("finish the blob decode"). Rather than eyeball hex,
used structural detectors: a 4×4-affine validator (orthonormal 3×3 + `(0,0,0,1)` bottom row), a
type-byte survey across every blob, and an exact-consumption walk as the acid test. Corpus = **205
unique non-empty blobs** (the earlier "512" counted shadow duplicates across forges; 205 is the
distinct count). **Read-only throughout.**

### VERIFIED (new)
- **Blob grammar:**
  `blob := u32 magic 0x12341234 | u32 version 3012000 | record*`, and
  `record := u8 type | u8×(H−1) header | M × 64-byte 4×4 affine | tail`.
- **`H` and `M` are constant per type.** Every blob's first record is unambiguous (starts at byte
  8), giving 205 independent samples — **the vote was unanimous for all nine types**:
  H = 9 for types 5/6/7/19/20/21/24, **10** for type 9, **5** for type 23; M = 4 for most,
  **5** for type 21, **1** for type 23.
- **The type byte is genuinely the constraint type.** Three of the nine observed values land
  exactly on ATK's `Reflex3ConstraintTypeRegistry`: **6 = HingeVector, 7 = LookAt, 9 = Orientation**.
  The other six (5, 19, 20, 21, 23, 24) are types GRB uses that ATK never modelled.
- **Acid test: the walk consumes 204 of 205 blobs EXACTLY** — landing on the final byte with
  nothing left over.
- **The matrices are 4×4 row-major affines** — orthonormal 3×3, translation in column 3, bottom row
  `(0,0,0,1)`. The first probe missed most of them because it wrongly demanded zero translation.
- **Type 21 is the physics record, decoded field by field and validated over all 1,354 in the
  game:** `tail := u8×3 flags | { u8 gate ; if gate: f32 lo, f32 hi }* | f32×9 params`.
  - **`param[4]` == 9.8 in 1,344/1,354 (99.3 %)** → `Reflex3Physics.Gravity`, whose ATK default is
    `9.8f`. `param[5]`/`param[6]` == 1.0 in 1,344/1,338; `param[7]`/`param[8]` == 0.0 in
    1,353/1,349; `param[0]` == 0.2 in 1,096; `param[2]` takes 0.95/0.98 — damping-shaped.
  - **The limits are radians.** Values include exactly `−1.5708` (−π/2) and `3.1416` (π), the range
    is `[−π, +π]`, and the **median |limit| is 15.00°**. 44 % of pairs are symmetric.
  - Gate counts: **2 pairs in 1,262 records**, 1 in 72, 0 in 20 — matching the bool-gated model.
- **Real readings.** `Player_Kilt_Addon` = one bone swinging **±15° and ±5°**, gravity 9.8, damping
  0.2, 394/394 bytes accounted. `Tsec_Trench_AddonSkeleton` = **48 records — 36 HingeVector, 2
  Orientation, 10 Physics** — the physics bones limited −20°→0° and 0°→+20° (panels hinging fore and
  aft), 43,494/43,494 bytes accounted.
- **Correction to this morning's entry:** the "constant 9-byte record preamble" is really
  `u8 type + 8 more header bytes`, and it is **not** constant — type 9 uses 10 and type 23 uses 5.
  The earlier claim came from sampling only types whose H happens to be 9.

### INFERRED (new)
- The 8 bytes after the type byte are high-entropy and read most naturally as a **bone-name hash**.
  **Not checked** against a real bone hash from the same skeleton — that is the next cheap test.
- `param[0]` ≈ damping, `param[1]` ≈ stiffness, `param[2]` ≈ a damping coefficient (0.95/0.98 are
  the classic values). Shape-guesses from value distributions, not confirmed.
- Record boundaries for types other than 21/23 come from a forward-scan heuristic. It yields exact
  *total* consumption, which is good evidence, but individual boundaries are not independently
  verified, and those types' tails (hundreds to thousands of bytes) are undecoded.

### Questions answered / opened
- **Answered — the blob is readable.** GRB's per-bone physics can now be inspected in engineering
  units: which constraint type, how many bones, what angular limits in degrees, what gravity.
- **Opened — the write side.** Reading is done; nothing here has been *written* back yet, and the
  hang-on-load and forge-shadow hazards from the cloth work all still apply to skeletons.
- **Opened — confirm the bone hash**, then constraint records can be tied to named bones, which is
  what a rebind ultimately needs.
- **Opened — decode the non-21 tails**, especially type 9 (Orientation, 1,400 records — the most
  common in the game) and type 6 (HingeVector, 472 — 36 of them in the trench coat alone).

### Docs written this session
New: [`tools/reflex3.py`](../tools/reflex3.py) — decodes a skeleton's constraints and prints swing
limits in degrees, gravity and damping. Updated:
[`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md) (full grammar,
the type/H/M table, the type-21 field table with per-field evidence counts, sample output),
[`tools/README.md`](../tools/README.md), [`meta/next-session.md`](next-session.md).

---

## Entry — 2026-08-14 (fourth) — CONFIRMED: the record head is `BoneID | ParentBoneID`, and bone names are CRC32

### What I did
Closed the one item the previous entry left marked *inferred*. Four independent lines of evidence,
then a fix to the one type that didn't fit. **Read-only throughout.**

### VERIFIED (new)
- **ATK settles the shape.** `Reflex3BoneInfo` is
  `{ uint BoneID; uint ParentBoneID; Matrix4x4 InitTransform }` and `Bone.Name` is a `uint32` —
  exactly the "8 bytes then a 64-byte matrix" observed in the blob. The first matrix in every record
  is `InitTransform`.
- **Bone names are `CRC32(exact-case name)` — 9 of 9.** GRB bakes the hash into its collider names
  (`TP_WalkerCoat_Ragdoll_LeftForeArm_2310617728`), so they are self-verifying. All nine
  (`Head`, `Neck`, `LeftArm`, `LeftForeArm`, `LeftHand`, `LeftShoulder`, `RightArm`, `RightForeArm`,
  `RightHand`) matched plain CRC32. **crc32-lower, crc32-upper, CRC-32/BZIP2 and no-final-xor each
  matched 0 of 9.**
- **`Bone.Name` sits 4 bytes after the `Bone` class hash (`2507411529`)** in a Skeleton payload —
  found by scanning candidate offsets and taking the one that resolves the constraint IDs.
  `Player_Kilt_Addon`: **1/1** BoneID and **1/1** ParentBoneID. `Tsec_Herzog_Hair_Skeleton`:
  **28/28 and 28/28**.
- **Game-wide, by record type:** BoneID resolves **100.0 %** for types 7, 9, 19, 20, 21, 24;
  **99.8 %** for type 6; **96.2 %** for type 5. **≈99.7 % overall (3,850-ish of 3,860)** against a
  **0.000 %** null control — random `uint32`s never hit the 1,274-hash bone-name set.
- **Type 9 explained.** It initially scored **0 %** — because its bone IDs sit at header offset **+1**,
  behind one extra constant `0x01` byte. At +1 it scores **100.0 % / 99.9 %**. That single byte is
  precisely why type 9's header is 10 bytes while every other type's is 9. The anomaly and the fix
  are the same fact.
- **The decode produces authored-looking data.** `Tsec_Herzog_Hair_Skeleton`'s records form
  **bone chains** — each record's `ParentBoneID` is the previous record's `BoneID` — and down each
  4-bone strand the swing limits **widen** (±10° → ±15° → ±20° → ±25°) while damping **falls**
  (0.4 → 0.3 → 0.2 → 0.1), then reset when a new strand starts. Stiff at the root, floppy at the
  tip: that is how an animator authors hair, and it is much stronger evidence than byte statistics.
- Across all types, 364/3,655 consecutive record pairs chain (10 %) — high within hair/strand rigs,
  low in rigs whose bones hang in parallel.

### INFERRED (new)
- The earlier "body-skeleton" explanation for the missing 36 % was **wrong** — only 1 of 1,403
  misses resolved in a body/reflex rig. The real cause was the type-9 offset, now fixed.
- `param[0]` and `param[3]` behave like damping terms (they vary smoothly down a hair strand), but
  the naming is still a shape-guess.
- `RBTYPE_LEFTFOREARM` exists as a string inside `AnvilToolkit.dll` — a rigid-body type enum,
  presumably the ragdoll capsule taxonomy. Not pursued; noted because it is the only ragdoll-shaped
  identifier found in the toolkit.

### Questions answered / opened
- **Answered — the record head is `BoneID | ParentBoneID`, both CRC32 of the bone name.** Constraints
  can now be tied to named bones, which is what a rebind needs.
- **Opened — a bone-name dictionary.** ATK embeds `AnvilToolkit.Resources.hashes.hl` (a hash→string
  table) and exposes `Name.GetHashedString()`. Extracting it would turn every hash in the tooling
  into a readable bone name. Not attempted — it is an embedded .NET resource, not a loose file.
- **Unchanged:** tails for types other than 21/23 are undecoded, and nothing is written back yet.

### Docs written this session
Updated: [`tools/reflex3.py`](../tools/reflex3.py) (extracts BoneID/ParentBoneID incl. the type-9
offset, reads the skeleton's real bone list, flags which constraints resolve),
[`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md) (record head in
the grammar, the CRC32 proof, the per-type resolution table, the hair-strand walkthrough),
[`tools/README.md`](../tools/README.md), [`meta/next-session.md`](next-session.md).

---

## Entry — 2026-08-14 (fifth) — Extracted ATK's hash→name dictionary; bone names resolve

### What I did
Took the "cheap win" flagged in the previous entry: get `AnvilToolkit.Resources.hashes.hl` out of
ATK and use it to turn Reflex3 bone hashes into names. **Read-only on the toolkit.**

### VERIFIED (new)
- **Format, from ATK's `HashedData.CheckStrings()`:** `hashes.hl` is an embedded, **Fast-LZMA2**
  compressed **plain-text list, one name per line**. ATK decompresses it by P/Invoking
  `Libs/fast-lzma2.dll` (`FL2_findDecompressedSize` + `FL2_decompressMt`) and keys it by `CRC32`
  of each line **plus its lower- and upper-case forms** — which is why a name can resolve under
  three different hashes.
- **Extracted: 1,294,015 B compressed → 6,610,946 B → 276,087 names.** Two independent routes agree
  **byte-for-byte**: a C# `System.Reflection.Metadata` reader (exact, via the ManifestResource
  table) and a pure-Python scan of the PE's Resources data directory. The Python one is what ships.
- **Coverage against GRB is partial and its shape is informative.** The list targets ATK's primary
  games (the Assassin's Creed line): **51 of 1,274** GRB skeleton-declared bone hashes resolve
  (4 %), and **none** of the Reflex3 constraint bones themselves. But the ones that resolve are
  exactly the **attachment points**:
  - `Tsec_Trench_AddonSkeleton` → parent **`Spine2`**
  - `TP_HunterScarf_A_Skeleton` (5 records) → parent **`Spine2`**
  - `Watch_Skeleton` → parent **`LeftForeArm`**

  A coat and a scarf hanging off the spine, a watch off the left forearm. Anatomically correct, and
  an **end-to-end check on the whole chain** — forge → skeleton → constraint record → bone hash →
  name.
- The unresolved hashes are each rig's *own* invented bones (coat panels, hair strands). Only a
  GRB-specific name source would cover those; ATK's dictionary never will.

### INFERRED (new)
- Nothing material. The one judgement call: the extractor identifies the dictionary by
  *decompressing candidates and checking the output is a newline-separated ASCII list*, because no
  ranking heuristic survived a 14 MB resource directory — random bytes in the metadata tables make
  `FL2_findDecompressedSize` report plausible sizes, and the real blob ranked 69th by size. The
  exhaustive check is slower (~108 s) but deterministic.

### Questions answered / opened
- **Answered — the hash dictionary is obtainable**, and bone names resolve for the standard biped.
- **Opened — a GRB-specific name list.** Every dangle bone in the game is currently a bare number.
  Anything that yields real GRB bone-name strings (an ATK GLB skeleton export, a modder's Blender
  file, an animation-side resource) would fill the gap; the CRC32 is trivial to invert once the
  candidate string exists.
- **Unchanged:** tails for types other than 21/23 are undecoded, and nothing is written back.

### Docs written this session
New: [`tools/atk_hashes.py`](../tools/atk_hashes.py) — extracts and decompresses the dictionary from
a local ATK install. The dictionary itself is **not committed** (it is ATK's data). Updated:
[`tools/reflex3.py`](../tools/reflex3.py) (`--names` flag), [`tools/README.md`](../tools/README.md),
[`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md),
[`meta/next-session.md`](next-session.md).

---

## Entry — 2026-08-14 (sixth) — GRB-specific bone names recovered from their hashes

### What I did
ATK's dictionary only covers its Assassin's Creed lineage (4 % of GRB's bone hashes), so I went
looking for a GRB source. Two approaches: **harvest** literal strings and CRC32-match them, then
**generate** candidates from the grammar the harvest revealed. Crucially, I also ran a **null
experiment** to measure how many "hits" brute force produces by chance. **Read-only throughout.**

### VERIFIED (new)
- **Targets:** 2,491 distinct bone hashes across all 205 physics-carrying skeletons — 2,484
  declared in bone lists, 649 referenced by Reflex3 constraints.
- **Harvest sources:** `GRB.exe` (536 MB → ~892,000 strings), all **370,259** forge entry names, and
  every string inside a skeleton payload (32,305). Matching those literally resolved **63** hashes
  and, more importantly, exposed the naming grammar.
- **⚠️ Measured false-positive rate.** Replaying the generator against **2,491 random hashes**
  produced **20 spurious "hits" per 18.7 M candidates**. Generated matches are therefore worthless
  on their own — a fact that changed how the whole result is reported.
- **Three independent evidence types**, and only names carrying at least one are shipped:
  - **`literal` (70)** — read verbatim from GRB.exe / a forge entry name / a skeleton payload.
  - **`family` (51)** — member of a numbered run of ≥3 (`T_Zipper01`…`T_Zipper07`,
    `T_Strap01`…`06`). Per stem we test ~24 variants at P≈1.4 × 10⁻⁵; a six-long run is not chance.
  - **`context` (16)** — the name's distinctive token matches a skeleton that *uses* that hash:
    `RFX_Watch` and `T_Watch` in **`Watch_Skeleton`**, `T_Scarf` in **`TPri_CIN_Hawkins_Scarf`**,
    `RFX_BackPack`/`T_BackPack` in backpack rigs, `DRN_UGV_Goliath-Rig-{FL,FR,BL,BR}` in
    **`DRN_UGV_Goliath`**. This evidence is independent of the hash entirely.
- **93 isolated generated hits were discarded** as probable collisions — consistent with the
  measured null rate.
- **Result: 126 names, 43 of them Reflex3 physics bones** →
  [`reference/grb-bone-names.tsv`](../reference/grb-bone-names.tsv), with the evidence tier recorded
  per row.
- **The naming grammar, which is the more reusable finding:**
  - **`RFX_`** = **Reflex — the physics bones** (`RFX_LeftShoulderRoll`, `RFX_Watch`, `RFX_BackPack`)
  - `T_` = targets/attachment points (`T_Strap01…06`, `T_Zipper01…07`, `T_Scarf`)
  - `L_` = link/no-roll helpers (`L_LeftArmNoRoll`, `L_NeckNoRoll`)
  - `Prop_` = prop attach points; `Reflex_<bone>_Sphere` = collision primitives
  - unprefixed = standard biped (`Hips`, `Spine2`, `LeftForeArm`, `RightHandRing2`)
- `RBTYPE_LEFTFOREARM` in `AnvilToolkit.dll` (noted last entry) fits this scheme as a rigid-body
  type enum, not a bone.

### INFERRED (new)
- The `T_` prefix reads as "target" and `RFX_` as "Reflex", from context rather than documentation.
- `rfx_l_topwristctrl_1…7` and `SIM_TORCH02_*` survive on family coherence and are probably real,
  but their exact casing is a guess — the generator tests exact/lower/upper and the lower-case form
  is what hit.

### Questions answered / opened
- **Answered — a GRB bone-name source exists**: GRB.exe's own string table plus the forge entry
  names, and they are enough to recover the grammar even where they don't contain a given name.
- **Opened — the long tail.** 2,365 of 2,491 hashes are still numbers, including most per-garment
  dangle bones (coat panels, hair strands). Nothing searched so far contains them. Remaining ideas:
  an ATK **GLB skeleton export** (ATK names GLB nodes via `GetHashedString`, so an export would only
  echo hashes it already knows — probably a dead end), a modder's original Blender/FBX rig, or an
  animation-side resource that stores track names as strings.
- **Methodological note worth keeping:** any future hash-cracking in this KB should run the null
  experiment first. Without it, this session's 214 raw "hits" would have been reported as fact when
  ~40 % were noise.

### Docs written this session
New: [`reference/grb-bone-names.tsv`](../reference/grb-bone-names.tsv) (126 names with per-row
evidence). Updated: [`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md)
(method, the null-run caveat, the evidence table, the naming grammar),
[`tools/reflex3.py`](../tools/reflex3.py) (`--names` now also accepts the TSV),
[`tools/README.md`](../tools/README.md), [`meta/next-session.md`](next-session.md).

## Entry — 2026-08-23 — Tier 1 Imports crowdfund history; the two funding systems

### What I did
Not a game-file session. Documented the **funding and distribution system** behind a large slice of
the mod corpus, because folder names in [`examples/mod-catalog.md`](../examples/mod-catalog.md)
(`CFLIONNESS_*`, `acostabisonbattlebelt_*`, `AKM_KYPK`, `Kalashnikova_SR1`, `SA58`) are crowdfund
output and nothing here explained what that meant. Read *Tier 1 Imports* (guild `1302392670181916722`)
through the Discord bridge as `@blkdnm`: `#announcements` end to end (94 messages, 2024-12-03 →
2026-08-19), `#crowdfund-projects`, the 11 readable `*-confirmed` channels, `#kingslayer-polls`, and
guild search on "buy-in" / "crowdfund project" / "unconfirmed". New doc:
[`reference/crowdfund-history.md`](../reference/crowdfund-history.md).

### VERIFIED (new)
- **Two systems, changeover dateable to 2025-07-29.** System 1 ("buy-in", 2024-11 → 2025-07):
  variable price set per project as a *share of the modder's commission* ($60 gun / 12 people / $5
  each — msg `1302780729121570906`), opt in by voting in `#crowdfund-votes`, manual channel adds.
  System 2 ("the reaction-role system's way", 2025-07-29 →): flat $10 minimum, 👍 reaction grants a
  `<Name> unconfirmed` role, supporting the project swaps it for `<Name>` plus the `-confirmed` channel and the
  permanent **Supporter** role.
- **The changeover was never announced.** `#announcements` was read in full and contains no post
  describing it; the new channel and post format simply appeared.
- **Reaction-role automation is T1 Carl** (`235148962103951360`), the sole bot reactor on every
  crowdfund post — which also means every raw 👍 count is inflated by exactly one.
- **Per-project roles are public on the profile**, and the community polices "unconfirmed" tags
  socially (msgs `1441914698940284990`, `1432329575764856934`, `1442081888226246750`). This replaced
  System 1's only lever, which was threatening bans (msg `1313256555994681406`).
- **Tier naming changed twice.** The crowdfund reward was "Tier 1 Armory" (Mar 2025) → "Tier 2"
  (May 2025) → **Supporter**; the earned role became **Kingslayer** by poll on 2026-03-24, 149 votes
  (msg `1485007498162475028`). Pre-mid-2025 "T1 Armory" references mean today's supporter armoury.
- **`#crowdfund-projects` does not keep its history** — it holds six posts, oldest 2026-04-12;
  `before=`/`around=` return nothing past that, and ~20 `@everyone` links into it are dead.
  **Corrected later the same day:** I first wrote that CYBERSAMI and Heavy Metal were *deleted*
  between 08-19 and 08-23 and called it observed. It was not — a `limit=4` query mistaken for the
  channel's contents. Both are still posted. No deletion has been observed; the mechanism (rolling
  removal vs. a one-off purge) is **unestablished**, and two of the six are months past their end
  date and still up. Caught only because `tools/refresh.py` re-read the board with a real limit —
  a reminder that a query bound is not a measurement.
- **Release votes are readable and are a hard floor on paid membership** (only payers can see the
  channel). 11 measured: 1,118 votes total, range 48–275. **7 of 11 voted to stay supporter-only** —
  i.e. roughly two thirds of crowdfunded work never reaches Nexus, which is the answer to "why can't
  I find this mod publicly".
  **⚠️ Superseded 2026-08-30 — the generalisation was backwards.** The 11 measurements stand; the
  inference from them does not. A destination sweep across 45 of 57 found **two thirds reaching the
  public**, not two thirds staying private. The 11 are the crowdfunds this one account backed, all
  from a five-month window in the era that keeps the most behind the supporter role. See that day's
  entry.
- **Backer base is wide and shallow.** Exact reactor lists for all six posted crowdfunds: **812
  distinct humans, 1,318 sign-ups, 67.9% backed only one**, and just 14 people are on all six.

### INFERRED (new)
- The **March 2025 leak** ("an edgelord tried to leak buy in mods", msg `1352106850715308134`; buy-ins
  halted same day, msg `1351884110330859531`) plausibly drove the move to auditable per-project roles.
  Adjacent in time and theme; **no message states the causal link.** Flagged as hypothesis in the doc.
- System 1 item #12 (SC Wolves / Wolves Overhaul) may be the same project as #10 (Shadow Rusher) —
  Modder C linked the Shadow Rusher channel while naming it "SC Wolves".

### Questions answered / opened
- ✅ What the two systems were, and exactly how each worked.
- ✅ Provenance for the `CF*`-prefixed corpus folders.
- ❌ **How many System 1 crowdfunds existed** — 23 recovered, true count higher.
  `#crowdfund-projects-legacy` and `#crowdfund-votes` (`1303906293219856477`) both return `forbidden`.
- ❌ **Eight System 2 crowdfunds cannot be named** — post deleted, channel invisible. Anyone holding
  those roles could name them instantly, since the role name *is* the crowdfund name.
- ❌ Release split across all 55 — only 11 measurable from this account.

### Follow-up (same day) — The Bivouac, and a name recovered from outside
- **Tier 1 grew out of The Bivouac** (guild `981599102523539466`), a GRB modding community running
  since mid-2022. **Verified:** T1 founded 2024-11-02; the Bivouac's ownership transfers to
  a new owner 2024-11-06 (msg `1303731106599796817`); T1's co-creator posts an invite into the
  Bivouac's own chat 2024-11-08 (msg `1304532626023120966`) and is not removed for it; Modder M routes
  Bivouac members to T1 for crowdfunds 2024-11-23 (msg `1309919966497214525`). The Bivouac is now
  largely inactive (msg `1503318552331948113`).
- **The structural difference is the funding model, and it is still visible in the channel lists.**
  The Bivouac runs commissions — `#request-commission`, `#commission-guidelines` — one person paying
  one modder. T1 was built on day one to split that cost across many. **Inferred / unresolved:**
  whether T1 was a deliberate *split*. Founding, handover and recruitment fall inside one week, but
  no message states a cause and the recruitment was public and tolerated.
- **Method worth reusing: adjacent communities remember what a self-deleting channel does not.**
  Crowdfund #28, unnamed since its post was lost, was recovered by searching *The Bivouac* — a member
  there listing what was live on 2025-09-24: *"the Metal Gear Solid/XOF and the Steyr Crowdfund"*
  (msg `1420518885261836368`). Eight crowdfunds remain unnamed; the same trick may reach some of them.

### Docs written this session
New: [`reference/crowdfund-history.md`](../reference/crowdfund-history.md). Updated:
[`README.md`](../README.md) (link).

Also published the live panel — **[dataterminals/t1-crowdfunds](https://github.com/dataterminals/t1-crowdfunds)**
→ <https://dataterminals.github.io/t1-crowdfunds/> — which renders this dataset and carries
`tools/refresh.py` to re-pull sign-ups and backer overlap from the bridge. The narrative stays here;
the panel is the living view of it.

## Entry — 2026-08-24 — Naming the lost crowdfunds; how a deleted channel still talks

### What I did
Follow-up to the 2026-08-23 crowdfund work. Eight catalogue entries had `"name": null` because the
crowdfund post was deleted and `#crowdfund-projects` is invisible from a member account. **Five of
the eight are now named**, plus a sixth in System 1, plus two name corrections to entries that were
never flagged as doubtful. Everything below is from *Tier 1 Imports* (`1302392670181916722`) and
*The Bivouac* (`981599102523539466`) through the bridge as `@blkdnm`. Updated:
[`reference/crowdfund-history.md`](../reference/crowdfund-history.md).

### VERIFIED (new)
- **The five unnamed System 2 crowdfunds.** #39 **Recce** (Modder L), #40 **Blackbird** (Modder O),
  #41 **Cold Ops Carbonara** (Modder K), #42 **Step Brothers in Arms** (Modder M **+ Modder R** —
  the first two-creator crowdfund on record), #46 **Forgotten Weapons** (Modder L). Each is a third
  party naming the project while it ran; #40, #41, #42 and #46 are additionally bound to their own
  post id by someone posting that link beside the name. Full citations in §4 of the write-up.
- **#8 is the GZW (Gray Zone Warfare) gear pack.** Modder E calls it *"my gzw project"*
  (msg `1320189637448433747`). **Inferred (strong):** #6 and #8 are therefore the same crowdfund
  counted twice — Modder B lists exactly three open buy-ins on 2024-12-18 including *"the latest gzw
  assortment"* (msg `1318754880512327691`), six days after #8's announcement, with no fourth project
  running. Era 1 is now **23 rows, 22 distinct**.
- **#26 is "To the Moon", not "White Moon".** The announcement says *"Some beautiful White Moon
  assets"* (msg `1407147347590250516`) and an earlier pass read the vendor as the project name.
  **White Moon Studio is an asset seller** (msg `1327944649083584522`). The channel pair, the role
  and every member reference say *To the Moon* — including one that links #26's own post id
  (msg `1409099156320161794`). A caution for this whole file: an announcement's phrasing is not
  always the crowdfund's name.
- **#43 is "Crye Babies", not "Crye Baby"** — the singular came from the attachment filename
  `CRYE_BABY.png`; Modder B's own release header is *"CRYE BABIES SUPPORTER RELEASE"*
  (msg `1487141790770532525`).
- **#2's creator is Modder E, not Modder B.** The announcement names no modder; the release
  announcement does — *"The Alex Crowdfund by the legendary [Modder E] is now live on nexus"*
  (msg `1320181570610659340`). #33's creator is Modder O and #34's is Modder L, both now cited.
- **The deletions are real, and this time actually probed.** Resolving the five dead post links by
  URL returns the channel's *oldest surviving* message every time — a fetch falling through to the
  channel floor, not a paging limit. They are absent from the search index too. This is the check
  the 2026-08-23 `limit=4` mistake should have had.
- **Only two GRB communities are readable from this account.** All 85 guilds were enumerated by
  channel listing: Tier 1 Imports and The Bivouac, and the Bivouac mentions no 2026 crowdfund. The
  "ask an adjacent community" method that named #28 is **exhausted, not untried** — worth stating so
  nobody re-runs it hoping.

### Method (new, reusable)
- **Author-scoped search beats keyword search in a bot-heavy guild.** `content=crowdfund` returns
  hundreds of Carl-bot autoresponses a month; the same query scoped to the five or six people who
  answer *"what's live"* returns almost nothing but the enumerations. One such message named three
  crowdfunds at once.
- **Search a post's own URL** to find every message that ever pointed at it. A deleted post keeps a
  stable id, so this attaches a name to a *specific* crowdfund instead of to a date.
- **Discord's search index covers forwarded-message snapshots.** A forward carries the original's
  full text and stays searchable after the original is deleted — while the bridge renders it as
  empty content, so it is invisible unless you search for words it does not appear to contain.
  Pairing a fixed stem with a candidate word turns the six forwards in Tier 1 into an oracle. All
  six resolved to already-named crowdfunds, so it named nothing new, but it is the only known route
  to a deleted post's verbatim text.
- **Forum thread names are indexed as well** — a URL-only message matched words that appear only in
  its thread's title.
- **Announcement GIFs and title cards are the puzzle, not decoration.** "Time for some cold pasta" →
  Cold Ops Carbonara; a *let's do this team* GIF → a two-modder crowdfund; an **FW** monogram →
  Forgotten Weapons. Useful for generating a hypothesis, never sufficient to confirm one — each was
  only accepted once a member had written the name down.

### Questions answered / opened
- ✅ All 32 System 2 crowdfunds are now named.
- ❌ **#3 and #7 remain unnamed** (System 1, both announced without a name and never named in public
  chat). #7 is missing from Modder B's own open-buy-ins list six days after its announcement, so it
  may have collapsed early — one crowdfund is described doing exactly that that month.
- ❌ How many System 1 crowdfunds existed. Unchanged: the legacy channels are `forbidden` and at
  least one project channel is deleted outright (`1309056687801503805` now 404s).
- 🆕 **The cheapest possible fix for all of this is a guild role-list read.** The role name *is* the
  crowdfund name, and the Discord client caches every guild role including ones the account does not
  hold — the bridge already reads that store for mention resolution but exposes no endpoint for the
  snapshot. Caveat: at least one crowdfund role has since been deleted (#39's, `1466647776396836874`,
  renders unresolved), so it would not be a complete answer for closed projects.

### Docs written this session
Updated: [`reference/crowdfund-history.md`](../reference/crowdfund-history.md) (§1 counts, §4 both
tables plus a naming-provenance block, §5 and §7 coverage caveat, §7 rewritten),
[`meta/next-session.md`](next-session.md). The panel repo
**[dataterminals/t1-crowdfunds](https://github.com/dataterminals/t1-crowdfunds)** was left untouched
and now lags this file by six names and two corrections — see next-session.

## Entry — 2026-08-25 — Crowdfund #56 caught live, and what a first-hour sample actually measures

### What I did
Short session. A new crowdfund went up while we were working on the previous entry, so it is in the
catalogue from the day it was posted rather than reconstructed later — the first one that has been.
Also fixed a statistic that the seventh post quietly broke.

### VERIFIED (new)
- **#56 — Flash Point**, Modder O, posted **2026-08-25T06:52Z** (post `1541701813349253190`,
  `@everyone` msg `1541702858146320394`, *"Another Bonfire Masterclass"*). Spiritus Systems LV-119
  and an FN Five-Seven MK3. Modder O's **third** crowdfund after Dual Sig (#33) and Blackbird (#40).
- **Board snapshot 2026-08-25T07:12Z, seven live posts:** Rangers Lead The Way 399, GWOT Classics
  321, CYBERSAMI 200, Heavy Metal 176, Pastaslov 134, Dealer's Choice 126, Flash Point 11.
  **837 distinct people, 1,367 sign-ups.**
- **The wide-and-shallow finding is stable, not a fluke of one read.** 67.9 % backed exactly one
  crowdfund across six posts on 08-23, and **67.9 %** across seven posts on 08-25 — a seventh
  crowdfund and 25 more people, same figure to a decimal. Only 5 people of 837 are on all seven.
- **Creator concentration, recomputed.** Modder B has run **14 of the 56** — a quarter of every
  crowdfund the server has held — and it is **7 in each era**, so the share survived the changeover
  rather than being a legacy of the early days. ⚠️ The previous text said *"~14 of the 32 System 2
  projects (~29 %)"*, which put the all-era numerator against the era-2 denominator. Corrected.
- **Cadence is unchanged across the system change:** System 1 ≥2.5/mo (22 distinct over ~9 months),
  System 2 2.6/mo (33 over ~13 months). Everything about the funding model changed; the rate did not.

### INFERRED (new) — and the measurement trap it exposed
- **A crowdfund's first hour recruits nobody.** Flash Point was 20 minutes old when read, and
  **10 of its first 11 backers already back at least one other live crowdfund** — the exact inverse
  of the 46–55 % fresh-backer share the mature crowdfunds show. Reading that as "this crowdfund
  isn't recruiting" would be wrong: it is a **sampling-order artefact**. The people watching the
  board when a post lands are the regulars; fresh backers arrive over the following weeks.
- This was not hypothetical — `tools/refresh.py` picks the *newest* crowdfund for the panel's
  new-blood figure, so it selected Flash Point and would have rendered **"0 of Flash Point's 9
  backers appear on none of the other 6 — each crowdfund recruits largely fresh"**, a sentence that
  states the opposite of its own evidence. Fixed at the source: the script now **skips any crowdfund
  less than seven days old** and logs which it skipped and why. It picked GWOT Classics (45 days,
  149 of 321 fresh). Same family of error as the `limit=4` mistake — a number that is technically
  correct and answers a different question than the prose around it.

### Questions answered / opened
- ✅ #56 named and dated at source.
- 🆕 **Hidden channel names may be reachable.** A ShowHiddenChannels-type plugin was enabled mid-
  session so locked channels appear in the client's sidebar. It does **not** reach the bridge:
  `GuildChannelStore.getChannels` still returns the same 50 accessible channels, and reads on hidden
  channels still fail the client-side permission gate. But **the client demonstrably holds their
  names** — `#heavy-metal` and `#pastaslov` render as names inside crowdfund posts and neither is
  accessible from this account. Two routes remain: `current_view` is **ungated** and returns the
  full channel object for whatever is on screen (one channel per click), or a few sidebar
  screenshots. Worth pursuing: an era-1 project channel's *name* is a crowdfund name, which is the
  standing open question for #3 and #7.

### Follow-up (same day) — the access ask was declined, and what replaces it
- **Read-only access to the paid channels is closed.** The minimal role — zero guild-level
  permissions, `View Channel` + `Read Message History`, `*-confirmed` channels only, explicitly not
  the confirmation channels, read-once sufficient, export offered as an alternative — was put to **two
  staff members and turned down**. Recorded in [`next-session.md`](next-session.md) as
  **do not re-pitch**. The **turnout** column is therefore fixed at 11 of 56 permanently.
- **Destination is a different question, and it is reachable.** Where a crowdfund's output *landed*
  leaks into public chat, `#supporter-armory` (readable) and Nexus. Probed the same day and it
  returns outcomes for crowdfunds well outside the 11, including **System 1**, where there is no
  vote data at all: To the Moon → supporters (msg `1422746736690200616`), Commando Diving Drysuit →
  supporters (`1413651144026099755`), Vulcan/Malyuk → public (`1478138630139543864`), Cold Ops
  Carbonara → public (`1507031310512685106`). Validated against a known answer: Tip of the Spear →
  public (`1498457981350842450`) matches the vote we can read.
- ⚠️ **Keep destination and turnout in separate columns.** Destination is broader and weaker, it is
  not always what the vote said (the vote is sometimes scoped to part of a project), and **the
  source has to be weighted** — a member's *"I guess it was voted to not go public"* about Snake
  Eater (`1532273474637135975`) is flatly wrong, and only detectable as wrong because that vote
  happens to be readable. On an unreadable crowdfund it would have been recorded as fact.
- **Asking one modder about their own crowdfund is not the ask that was declined.** Different
  question, different people, no permissions involved.

### Docs written this session
Updated: [`reference/crowdfund-history.md`](../reference/crowdfund-history.md) (§1, §4 catalogue,
§5 sign-ups / overlap / cadence / creator concentration, §7 counts and open question 4),
[`meta/next-session.md`](next-session.md), and in the panel repo `data/crowdfunds.json` plus
`tools/refresh.py`.

## Entry — 2026-08-30 — The destination sweep, and a headline claim that was backwards

### What I did
Ran the destination sweep proposed after the access refusal: for each of the 57 crowdfunds, harvest
every message naming it from channels this account already reads — public chat, `#mod-releases`,
`#supporter-armory`, and Nexus links posted by the creators — and work out **where its output
landed**. Machine-tagged the evidence, judged every row by hand. New doc:
[`meta/crowdfund-asks.md`](crowdfund-asks.md) was written the same day (the two ask-lists).

### VERIFIED (new)
- **Destination is now known for 45 of 57**, up from 11. **30 public, 13 supporters, 2 private**;
  8 still open on the board; 4 unknown (#3, #7, #10, #16). Every row is a named person saying where
  a named crowdfund went, cited by message id in `data/crowdfunds.json`.
- **⚠️ The "two thirds stay private" claim was backwards.** The 2026-08-23 entry generalised
  *7 of 11 voted supporter-only* into *"roughly two thirds of crowdfunded work never reaches
  Nexus"*. Across 45 it is close to the reverse: **two thirds reaches the public.** The 11
  measurements were never wrong — the inference from them was. Annotated in place at that entry
  rather than edited away.
- **Why the 11 misled, which is the reusable part.** They are the crowdfunds *this one account
  backed*, all from 2025-09 → 2026-01. That is a narrow window **and** the wrong era. This is the
  first time the 11-of-57 caveat has actually caught something, which is a good argument for having
  stated it twice.
- **The two eras behave differently, and that is the real finding.** System 1: **79 % public**
  (15/2/2 of 19 decided). System 2: **58 % public** (15/11 of 26). System 2 keeps roughly twice as
  much behind the supporter role. Coherent with §3: once supporting *any* crowdfund grants a
  permanent role with a standing armoury attached, "supporters" stops meaning locked away and starts
  meaning the reward that makes the role worth holding, so voting that way costs a backer less.
- **#45 Wolf Pack's creator is Modder O** — three Nexus mods posted in a row with *"thank everyone
  in wolfpack!"* (msg `1502850378373271692`). The catalogue had no creator for it. That makes five
  crowdfunds for Modder O, level with Modder L.
- **#6/#8 GZW stayed private for a stated reason:** *"GZW stuff … was kept private due to legal
  reason"* (msg `1541641511165370488`) — which matches §4's copyright note from 2025.

### INFERRED / method
- **Destination is a weaker and different claim than turnout, and the data says which.** New field
  `destination {where, confidence, src, note}`, deliberately **separate** from `release`.
  `confidence` is `vote` (11, read in the channel), `strong` (24, creator or moderator said so) or
  `moderate` (10, members only). The panel renders a **solid** pill for a read vote and a **dashed**
  one for a reconstruction — they must not look alike.
  - ⚠️ Caught while wiring that up: two entries (#1, #6) carried a `release` value reconstructed
    from chat *before* this field existed, so keying the solid pill on `release` would have claimed
    a vote nobody ever read. It keys on `vote` now.
- **Public rarely means all of it.** Almost every public crowdfund retained exclusives — Forgotten
  Weapons kept a working RMR back; Snake Eater went public on the sneaking suit while *"a majority
  of the items … were exclusive to those that supported it"* (msg `1532274964785266778`).
- **Search keys, not catalogue names.** Discord ANDs the tokens in `content`, so a full name like
  *"Shadow Rusher outfit"* matches almost nothing. The first sweep returned zero hits for several
  crowdfunds purely because of that; each needs a short distinctive key.
- **The failure mode this had to dodge**, recorded because it will recur: a member writing *"I guess
  it was voted to not go public"* about Snake Eater (msg `1532273474637135975`) is flatly wrong, and
  the only reason that is detectable is that Snake Eater is one of the readable 11. On any of the
  other 46 it would have gone in as fact. Ordinary words make it worse — `Steyr`, `Recce`, `WMD`,
  `Warfare` are all common, and a search for `wolf pack` returns the unrelated *Hound Wolf Squad*.

### Questions answered / opened
- ✅ Destination across the catalogue — §7 open question 4, now largely closed.
- ❌ **Turnout stays at 11 and always will**; a tally exists only inside the channel that held the
  vote, and access was declined on 2026-08-25.
- ❌ **#10 Shadow Rusher and #16 Next Generation Ghost's Gear have no destination** and no public
  trace at all. #16 nearly got one in error: a creator's Nexus release post crediting a crowdfund
  role looked like it, but the role's snowflake dates to 2025-05-16 — one day after the **Warfare**
  announcement, not #16's. Both belong on the modder-ask list.

### Docs written this session
New: [`meta/crowdfund-asks.md`](crowdfund-asks.md). Updated:
[`reference/crowdfund-history.md`](../reference/crowdfund-history.md) (§5 gains *Where the mods
actually went*; §7 open question 4 closed), and in the panel repo `data/crowdfunds.json` (the
`destination` field on 45 entries) plus `index.html` (the two-grade pill).

## Entry — 2026-08-30 (second) — A moderator supplied the numbers the declined role would have shown

### What I did
Five days after the read-only role was refused, the user asked a moderator for **the figures**
rather than for **the channels** — explicitly noting that the staff objection had been to channel
privacy, not to the data. He agreed on the spot, said he would *"collect them all manually"*, and 1 h 39 m later
sent a 7 KB text file covering every completed crowdfund. Largest single data drop in the strand.

> **⚠️ Correction, 2026-08-31 — I claimed this file showed signs of being machine-generated. It
> does not, and the reasoning was bad.** The compiler was asked outright and said: *"no I manually
> looked through all the channels and in some cases counted the individual members in the channels
> … then just copied and pasted everything and changed numbers to fit the CF"*, adding that he chose
> *"the harder and non lazy way"* over using AI (msgs `1543794401896038420`, `1543794505105412216`).
> Both of my "tells" have innocent explanations, and I had already seen one of them:
> - `Agent\/07` is **that modder's actual Discord display name**, backslash included — verified against
>   the user record, and printed in this very session hours earlier while resolving creator IDs.
>   It was never JSON escaping.
> - A UTF-8 BOM is what Windows Notepad writes by default. Evidence of nothing.
>
> **The user floated the possibility and I over-confirmed it** rather than testing it — I went
> looking for support and stopped when I found some, which is the same failure as the `limit=4`
> read, in a different costume.
>
> **What survives, and is now better explained.** *Take the tally, never the summary sentence.* His
> actual method — copy-paste a line per crowdfund and edit the numbers into it — is a **better**
> account of the one error than an agent skimming would be: the numbers get edited, the trailing
> sentence gets missed. That is exactly the Blackbird failure, and it means the rule holds for
> human-compiled data too, not just machine-compiled.

### VERIFIED (new)
- **11 of 11 exact.** Every release vote this account can read first-hand appears in the file with
  **both numbers identical** — Lioness 132/143, Snake Eater 59/35/5, Op Chesthair 97/47, and the
  other eight. Nothing needed reconciling, which is why the remaining 29 are carried at the same
  confidence instead of being hedged as one person's recollection. **A free accuracy test on a
  whole batch, from the overlap alone.**
- **Turnout goes from 11 crowdfunds to 40; 1,118 votes to 2,991.**
- **`members` is an entirely new metric — the confirmed channel's membership, i.e. who actually
  paid.** 41 crowdfunds, **4,936 paid memberships**. This retires a standing caveat: turnout was
  only ever a *floor* on paid membership, and §7 recorded Lioness as "bounded (≥275) but not
  known". It is **435**.
- **Participation scales inversely with size.** Median **63 %**; crowdfunds with 150+ members vote
  at a median of 59 %, those under 60 members at 71 %, topping out at 89 % (Kalashnikov SR1, 25 of
  28). The largest, Warfare at 205 members, was decided by **39 %** of its backers.
- **The release split, settled on votes: 28 public / 12 supporters.** Same shape the public-record
  sweep reached by a different route, so the "two thirds stay private" correction is now closed
  from both directions. Era 1 **12 public / 2 supporters**, era 2 **16 / 10**.
- **#3 is named — SB-4's MCX Spear LT** (10 buy-ins cap, no confirmed channel, public, Nexus 1125).
  The 2026-08-24 pass had listed the Spear LT as one of three candidates in flight that month
  without being able to choose. **#7 is now the only unnamed crowdfund in the catalogue.**
- **A crowdfund nobody here had ever seen: #58, Modder B's Salomon X4 Ultra Mid GTX**, 18 buy-ins,
  released public. It appears in no announcement readable from this account. Direct proof the era-1
  count is still a floor. Numbered 58 because catalogue numbers are identifiers, not a
  chronological rank — renumbering would break every citation in the file.
- **Creators filled:** #4 and #49 → Modder B. Modder B is now **17 of 58 (29 %)**, up from 14.
- **#1 is really a three-way build vote.** "Crowdfund Project 1" pooled 34 buy-ins and voted on
  *which* to make: Ghost Nightwar 18, Gaz Road Warrior 13, Capt Price 3.

### Corrections and conflicts (all recorded, none smoothed)
- **#28 Steyr flips supporters → public.** The destination sweep had it as supporters from three
  members saying a Steyr DMR sits in the armoury; the ballot in fact offered only **public or
  private** (64/20). The vote decides it, and both can be true — an item in the armoury need not
  have arrived by that vote. **This is the sweep's error rate made visible: one in forty-five.**
- **#40 Blackbird is the file's single internal contradiction** — it records 40 public against 15
  supporter and then states the result as Supporter Armory. The tally agrees with the independent
  public-record evidence, so the result line is read as a slip and Blackbird stays **public**,
  flagged in the data with the disagreement written out. **Settled 2026-08-31 with a screenshot of
  the poll itself** — *"Where to release."*, Public **40 (73 %)**, Tier 2 **15 (27 %)**, 55 votes,
  closed (msg `1543793745684603011`). The tally was right and the sentence beside it was stale. He
  also supplied the reason members called it public but could not find it: Bonfire released the
  items **individually rather than under the Blackbird name**.
- **#5 Price Ghillie downgraded to unknown.** The sweep called it public off a Nexus *Price's
  Ghillied Up*; the file has the Price taking 3 votes of 34 inside Crowdfund Project 1, with *"I
  don't think Chest ended up making the Price"*. The Nexus mod may be unrelated.
- **#6 ≡ #8 is reopened but not overturned.** The moderator recalls **two** GZW crowdfunds, one per
  modder, *"both never finished and kept private due to legal reasons"* — but hedges it as memory,
  with question marks, because both posts are deleted. Weak evidence against a strong inference:
  the merge stands and the doubt is written down.
- **#4 may be #12, not #10.** The file calls #4 *"Shadow Company Heavies as Wolves"*, which is the
  language this catalogue records separately as #12. Both ambiguities are now live.

### The method finding, which is the transferable part
**Asking for a fact is not asking for access, and the difference decided this.** The same people who
refused a role — one with no guild permissions, view-and-read-history on the confirmed channels
only, explicitly not the confirmation channels, read-once accepted — handed over the contents of those
channels' votes when asked for the numbers instead. That distinction was written up in
[`crowdfund-asks.md`](crowdfund-asks.md) the same week as a hypothesis about how to work around the
refusal; it is now the strand's best-evidenced technique. What did **not** transfer: the delivery
table is still 11 of 58, because a drop leaves no trace and nobody keeps a tally of them the way
they keep a vote result.

### Questions answered / opened
- ✅ Turnout, membership, and the release split across the catalogue.
- ✅ #3 named. ❌ **#7 remains the only unnamed crowdfund**, absent from the moderator's list too.
- ❌ #10 Shadow Rusher still has no destination; #5 now has none either.
- 🆕 **Era 1's true count is still open and now demonstrably a floor** — #58 was invisible from here.
  `#crowdfund-projects-legacy` and `#crowdfund-votes` remain the only places the real number lives.

### Docs written this session
Updated: [`reference/crowdfund-history.md`](../reference/crowdfund-history.md) (§1, §4 catalogue and
notes, §5 turnout rewritten around 40 votes plus membership and participation, destination section
reconciled against the votes, §7 consequences and open questions),
[`meta/crowdfund-asks.md`](crowdfund-asks.md), [`meta/next-session.md`](next-session.md), and in the
panel repo `data/crowdfunds.json` (vote blocks, `members`, #58) plus `index.html` (membership beside
turnout, a paid-memberships KPI, and the retired "hard floor" line).

---

---

> **Template for future entries:**
> ```
> ## Entry — YYYY-MM-DD — <topic>
> ### What I did
> ### VERIFIED (new)
> ### INFERRED (new)
> ### Questions answered / opened
> ```

---

## Entry — 2026-08-31 — Blender is scriptable from here; built the bridge and proved it end to end

### Environment change (record it before anything else)
**The install and the repo moved off `H:` onto `D:`.** Every path in the 2026-06-30 snapshot is
stale. Current, verified by listing this session:

| Thing | Now at |
| --- | --- |
| GRB install | `D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint` |
| ATK | `D:\Anvil Toolkit` (has run — a crash log dated 2025-10-23 sits beside it) |
| This repo | `D:\Github Repositories\grb-modding-knowledgebase` |
| Blender | `D:\SteamLibrary\steamapps\common\Blender` (Steam listing; `5.0` and `5.2` resource dirs, `blender.exe` is **5.2.1 LTS**) |
| Host Python | 3.12.10, on PATH |

Forges are all present and the six main ones are already unpacked under `Extracted\`.

### What I did
The user asked what we actually have for authoring mods with Blender, and whether a "Blender
connector" already exists. Answered both by checking rather than recalling, then built the piece
that was genuinely missing and tested it.

### VERIFIED (new)
- **Blender runs headless on this machine and is fully scriptable.** `blender.exe --background
  --python <script>` works; bundled interpreter is **Python 3.13.13**; `io_scene_gltf2` is present
  and enabled. This is the whole basis for driving Blender from a terminal — or from an assistant.
- **There is no GRB-specific Blender add-on to find, and none is needed.** The connector *is*
  glTF: ATK exports/imports GLB (via SharpGLTF, per [`docs/10`](../docs/10-meshes-and-skeletons.md)),
  and Blender reads/writes GLB natively. Both ends already speak the same format; what was missing
  was tooling around the seam, not a plugin.
- **Blender is Python-only — there is no Lua in it.** (The user's Garry's Mod modelling background
  is where the Lua association comes from.)
- **ATK still has no command-line interface.** Re-checked its `README.txt`: every "batch" reference
  is multi-select *inside the GUI*. So the two ends of the pipeline — export the donor GLB, import
  the finished one — stay manual clicks. Everything between them is now scriptable. This is
  consistent with the 2026-06-30 finding that `EnableCommands` is an experimental off-by-default
  console toggle, not an automation API.
- **The local mod corpus contains no 3-D source files at all.** 205 mod folders, 4,424 files,
  **zero** `.glb` / `.gltf` / `.fbx` / `.blend` / `.obj` / `.dae` / `.ma` / `.max`. Mods ship as
  repacked forge data only; nobody's working rig survives in what we hold.
  **This closes one of the leads listed on 2026-08-14 and again in
  [`next-session.md`](next-session.md) for recovering GRB's own bone names** — "a modder's original
  Blender/FBX rig" is not available *from this corpus*. It would have to come from a modder
  directly.

### Built: `tools/blender/` — a two-part Blender bridge
`grbblend.py` runs on the host and finds Blender (explicit `--blender`, then `GRB_BLENDER`, then a
sweep of Steam and Program Files locations on every drive letter). `_inside.py` runs inside Blender
and prints a JSON report between sentinels so the host can find it among Blender's console output.
Four commands: `doctor`, `selftest`, `inspect`, `transfer-weights`, plus a `run` escape hatch for
arbitrary Python with the helpers in scope.

Two deliberate design choices worth keeping:
- **Operator keywords are filtered against what the installed Blender actually accepts**
  (`op.get_rna_type().properties.keys()`). glTF export options get renamed between Blender
  releases; asking beats assuming. This is the "compatibility layer" the user floated, at the
  layer where it earns its keep.
- **`inspect` checks the failure modes [`docs/10`](../docs/10-meshes-and-skeletons.md) names by
  hand** — missing UVs, >5 UV sets, missing vertex colours, >4 influences per vertex, unweighted
  vertices, multiple materials. The doc listed them as prose; they are now assertions.

### VERIFIED — the selftest passes end to end
`selftest` touches no game files. It builds a rigged, weight-painted, vertex-coloured cylinder
("coat") and a differently-shaped, differently-tessellated cone with no rig ("poncho"), writes both
to GLB, runs the real `transfer-weights` code, re-exports, reloads, and checks the result. All seven
checks pass: weights land (3 of 3 groups), **100 % weight coverage** on the new mesh, vertex colours
come across, the armature survives, and the GLB round trip preserves both the groups and the
complete coverage.

Two things the test caught that are worth writing down:
- **A weight transfer copies weights and nothing else.** The donor's vertex colours stay behind
  unless asked for — and a GRB mesh arriving without the vertex colours its slot expects is exactly
  the "corrupted shading / colours read as UVs" failure `docs/10` describes. Hence `--with-colors`
  and `--with-uvs`, each a separate `data_transfer` pass. Note the domain split: vertex groups are
  point data and take `vert_mapping`; UVs and corner colours are loop data and take `loop_mapping`.
- **The number that matters is unweighted-vertex count, not group count.** Groups can transfer while
  large parts of the new mesh get nothing, and those vertices simply will not deform in game. The
  report leads with coverage percent for that reason.

### NOT verified — say so plainly
- **No real GRB mesh has been through this yet.** The selftest proves the *machinery*; it does not
  prove the *pipeline*. A garment exported from ATK, transferred, re-imported, and seen in game is
  the open experiment, and per `docs/10` the vertex-format choice on ATK import is the step most
  likely to bite.
- **This does not touch the `.cloth` rebind** (lane 2A) and does not claim to. Cloth is welded to
  one mesh's exact vertices and ATK's GRB cloth reader is gated off. Where weight transfer *does*
  serve the north star is **lane 2B, the bone-physics route** — Reflex3 secondary motion is
  transferable precisely because it is weight-painted rather than vertex-welded
  ([`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md)). A scripted,
  reproducible, checkable weight transfer is the Blender-side half of that route.

### Open questions this raises
1. **What does a real GRB garment GLB look like through `inspect`?** UV set count, vertex-colour
   naming scheme, influences per vertex, bones per primitive. Cheap to answer — one ATK export.
2. **Does a `transfer-weights` result import into ATK without complaint, and which vertex format
   does the donor slot want?** The first genuine pipeline test.
3. **Does a Reflex3-driven garment's bone set survive the ATK → Blender → ATK trip intact?** ATK
   "removes unused bones" on GRB import; a dangle-bone chain that the new mesh weights to only
   partially could lose bones silently.
4. **Can `inspect` on a real skinned garment recover GRB bone *names* that `grb-bone-names.tsv`
   does not have?** ATK's GLB export writes bone names as strings. That is a third route to the
   name-recovery problem, and unlike the mod corpus it is available right now.

---

## Entry — 2026-08-31 (second) — ATK's format engine loads headlessly from Python; the GUI is a shell over a callable library

### What I did
The user asked whether a compatibility layer between an assistant and ATK is worth building.
Rather than answer from the standing assumption — *"ATK is GUI-only, therefore the ends of the
pipeline are manual"* — I tested it. That assumption is **true of the application and false of the
library**, and the difference is large.

### VERIFIED (new) — the assembly loads and its format types are reachable
Loaded `D:\Anvil Toolkit\AnvilToolkit.dll` into **CPython 3.12 via pythonnet**, using
`clr_loader.get_coreclr(runtime_config="AnvilToolkit.runtimeconfig.json")` to bring up the same
.NET 9 runtime ATK itself targets.

- **The assembly loads.** `Assembly.LoadFrom` → `AnvilToolkit 1.3.1.0`.
- **1,235 types enumerate.** `GetTypes()` throws `ReflectionTypeLoadException` — expected, since
  some types reference WPF assemblies that don't resolve outside the app — but the exception
  **carries the successfully-loaded types**, and the format code is among them. The UI types are
  the ones that fail; `FileTypes.*` is a separate namespace tree and survives.
- **Everything needed is already on this machine, unplanned:** `.NET 9.0.10` +
  `Microsoft.WindowsDesktop.App 9.0.10` runtimes, `ilspycmd`, and **pythonnet already installed**.
  Zero new dependencies to test this.

### VERIFIED (new) — the API surface is exactly the pipeline
Reflected over the public methods of three types:

| Type | Public methods (abridged) |
| --- | --- |
| `…Models.AnvilGLTF` | `CreateGLTF`, `FromGLTF`, `MeshFromGLTF`, `BonesFromGLTF`, `ShapeFromGLTF`, `AnimationsFromGLTF`, `CreateBones`, `RecomputeTangents`, `RecomputeDuplicateVertices`, `RemapBuffers`, `GetVertexColor`, `GetMeshCenter` |
| `…Models.Mesh` | `Read`, `ReadFromFile`, `Write`, `WriteToFile`, `ReadVertexData`, `WriteVertexData`, `ReadIndexData`, `WriteIndexData`, `ReadXml`, `WriteXml`, `MergeMeshes`, `GetBoneByID`, `ConvertToTriangleMesh`, `GenerateShadowPrimitives` |
| `…Containers.ForgeFile` | `Deserialize`, `DeserializeAsync`, `Serialize`, `SerializeAsync` |

`Mesh` constructors take `(ScimitarClass)`, `(BinaryReader, ScimitarClass)`, or
`(XmlReader, ScimitarClass)`.

**`AnvilGLTF` is the Blender bridge, and it is a plain callable class.** The glTF conversion,
tangent recomputation and vertex-format handling that `docs/10` describes as "what ATK does on
import" are library calls, not GUI behaviour. So is forge serialisation.

### What this changes
The KB has said since 2026-06-30 that ATK is GUI-driven and `EnableCommands` is an experimental
off-by-default console toggle, "not a public CLI/automation API". **That remains exactly true and
is not retracted** — but it was being used to support a stronger conclusion than it licenses.
*ATK has no CLI* does not entail *ATK's capabilities are unautomatable*. The application is a WPF
shell; the engine underneath is an ordinary .NET library that a Python process can load and call.

This reframes the pipeline diagram in [`tools/blender/README.md`](../tools/blender/README.md),
which currently says the ATK export and import clicks "stay manual, and that's not going away
soon." That sentence is now **provisional** — see the honest limit below before rewriting it.

### NOT verified — and the gap is the whole question
- **No call has been made.** Types and method signatures were reflected over; **nothing was
  invoked.** Whether `Mesh.ReadFromFile` or `AnvilGLTF.CreateGLTF` actually succeed outside the
  application depends on state the GUI may set up first — `ScimitarClass` construction, the game
  registry (`ScimitarClassRegistry`), the loaded `Games.gsb`, `Lists\GhostReconBreakpoint.gfl`,
  settings from `AnvilToolkit.dll.config`. **Reflection proving a method exists is not the same as
  that method working.** This is precisely the error pattern the 2026-08-30 correction names —
  finding support and stopping — so it is written down as untested on purpose.
- **The first real test is read-only and cheap:** load one known `.data`, call the mesh read path,
  and compare the result against what this repo's own independent Python parsers already say about
  the same file. Two independent readers agreeing is a real check; one reader running is not.

### ⚠️ Safety — the write path is live
`ForgeFile.Serialize` and `Mesh.WriteToFile` are **in this surface**. A pythonnet layer therefore
has, in principle, the ability to rewrite forges **without ATK's GUI safeguards** — and ATK's
backup defaults (`CreateBackups`, `CreateDataBackups`, `CreateFileBackups`, all `True`) are
*application settings*, not library behaviour. There is no reason to assume they apply to a direct
library call.

**Rule for any work down this path: read-only until proven otherwise, and never a write to a real
forge without a verified backup and an explicit instruction** — CLAUDE.md safety rules 1 and 2,
which this does not weaken but makes considerably easier to violate by accident.

### Open questions
1. **Does `Mesh.ReadFromFile` work on a real GRB `.data` outside the app?** The cheap decisive test.
2. **What does `ScimitarClass` need to be constructed?** Probably the gate on everything else.
3. **Does `AnvilGLTF.CreateGLTF` produce a GLB byte-identical to the GUI's export?** If yes, the
   export click is genuinely automatable and the pipeline diagram changes.
4. **What does `EnableCommands` actually expose?** Still unexamined; now lower priority, because
   direct library calls would be a better interface than a console anyway.
5. **Is `Reflex3SkeletonConstraints` readable this way?** ATK's Reflex3 parser is gated behind
   `Version != Game.Mirage` for Breakpoint (see
   [`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md)), so this
   would likely reproduce the gate rather than bypass it — `reflex3.py` stays the tool for GRB.

---

## Entry — 2026-09-01 — ATK's mesh reader RUNS headlessly, and it corrects a "verified" fact about GRB skinning

### What I did
Ran the cheap decisive test the 2026-08-31 (second) entry specified and left open:
*load one known `.data`, call the mesh read path, and compare the result against this repo's own
Python parsers on the same file.* That entry was careful to record that **nothing had been invoked**
— only reflected over. It has now been invoked, on `TP_Tacvest_Walker_Coat_LOD0` and `LOD1`.

### VERIFIED (new) — ATK's `Mesh` reader works outside the application, and agrees
Two independent readers, same files, same numbers:

| | LOD0 (this repo, 2026-07-01) | LOD0 (ATK, headless) | LOD1 (repo) | LOD1 (ATK) |
| --- | --- | --- | --- | --- |
| Vertices | 1816 | **1816** | 956 | **956** |
| Triangles | 3263 | **3263** | 1631 | **1631** |
| Vertex stride | 36 | **36** | 36 | **36** |
| Max index | 1815 | **1815** | — | **955** |

Container-layer facts agree too: file-header length (1 B), `ClassID` `1707208439117`, class hash
`1096652136`. ATK's own `DataFile.ReadFileHeader` computes the header length by exactly the rule
[`resource-type-ids.md`](../reference/resource-type-ids.md) states (`12·n + 8` when the lead byte is
`1`, else 1) — an independent confirmation of a format note this KB derived separately.

**So `AnvilGLTF`/`Mesh`/`ForgeFile` are not merely reflectable, they are callable.** The reframing
in the 2026-08-31 entry survives contact with a real call.

### VERIFIED (new) — three things gate it, and each is silent when wrong
The 2026-08-31 entry guessed the gate would be `ScimitarClass` construction or the game registry.
It is neither. It is:

1. **`<ATK>\Libs` is not on .NET's probe path.** Without an `AssemblyResolve` handler pointing
   there, `GetTypes()` throws `ReflectionTypeLoadException`. The prior session read that as
   "expected, the WPF types fail" and moved on with 1235 types. **With the handler, 1245 types load
   and there are zero loader exceptions** — so the exception was a missing-dependency artifact, not
   an inherent WPF limit. Ten types were being lost silently.
2. **`DataStorage.GlobalScimitarClassReader` is a public static that only the GUI populates.**
   `ScimitarClass.ClassReader` is a *field initializer* reading it, so every instance built while it
   is null carries a null reader. `Mesh.ReadFromFile` then dies on its first `ClassReader.Read(...)`
   — at byte 24, immediately after reading the bone count. It is a plain parameterless class;
   constructing one and assigning the static is the whole fix, but it must happen **before** any
   `ScimitarClass` is constructed.
3. **`Mesh.Read` catches its own exceptions**, prints to `Console` and sets `Failed = true`. A
   failed read therefore returns a *half-built object that looks plausible* — the first attempt
   reported a real `VertexFormat` and a real `UVScale` off a mesh that had parsed 11 bytes. Capture
   `Console.Out` or you get no message at all.

### ⚠️ `Failed` is not a success signal for GRB meshes in ATK 1.3.1
Even on a fully correct read, ATK wants **exactly one byte more** than the resource payload holds:
it ends at `88089/88089` with *"Unable to read beyond the end of the stream"* and `Failed = True`.
Append a single zero byte and `Failed` is `False` with byte-identical geometry. Confirmed on both
LODs. **Whether that byte is an ATK over-read or a container subtlety is UNRESOLVED** — flagging it
rather than picking the flattering explanation.

Also noted: `Mesh.ReadIndexData()` **appends** to `Faces` instead of clearing, and on the successful
path `ReadFromFile` already calls it — so calling it again silently doubles the triangle count
(3263 → 6526). Caught only because 6526 = 2×3263 was too tidy to be geometry.

### ⚠️ CORRECTION — GRB garment meshes are FOUR-influence, not two-bone
This supersedes a claim carried as **VERIFIED** since 2026-07-01 and repeated in
[`docs/11`](../docs/11-cloth-and-physics.md) three times.

**The old claim:** *"Last 4 bytes = two-bone skinning `[idx0, w0, idx1, w1]`, `w0+w1 = 255` … for
all 1816 verts; bone indices span only 0..23."*

**What is actually there.** ATK reports the format as
`Pos3s_Col1s_Norm3ub_Col1ub_Tan4ub_Binorm4ub_Tex2s_Joint4_Col4ub`, which accounts for all 36 bytes:

```
0      6       8         11       12       16          20      24       32      36
| Pos3s | Col1s | Norm3ub | Col1ub | Tan4ub | Binorm4ub | Tex2s | Joint4 | Col4ub |
                                                                 ^^^^^^   ^^^^^^
                                                    4 idx + 4 weights     read as
                                                                          skinning
```

Skinning lives at **bytes 24–31** — four bone indices then four weights — and bytes 32–35 are a
colour channel. The 2026-07-01 parse read the colour channel.

- **Influences per vertex, LOD0:** `{1: 490, 2: 53, 3: 238, 4: 1035}`. The majority of vertices use
  **four** bones. LOD1: `{1: 204, 2: 32, 3: 133, 4: 587}`.
- Weights at 24–31 sum to 255 for **all** 1816 vertices; indices span **1..25** against a 30-entry
  `Bones` list (LOD1: 0..24 against 25).
- **The clincher:** ATK exposes bytes 32–35 as vertex `Color2`. On vertex 0 it reads
  `(0.02745, 0.02353, 0.02353, 0.97647)` — ×255 = `(7, 6, 6, 249)` = the raw bytes `07 06 06 f9`,
  exactly. Meanwhile ATK reads that same vertex as rigidly bound to bone 9 at weight 255, from
  `09 00 00 00 | ff 00 00 00` at 24–31.

**Why the old check passed, which is the part worth keeping.** The test used was *"do the two
weights sum to 255?"* — and they do, 1816/1816. But so do the real weights at 24–31, and the
complementary pair inside a normalized colour channel satisfies it too. Both hypotheses score
1816/1816; both keep their "bone indices" inside the bone count (0..23 and 0..22 against a 30-bone
list), so even a range check does not separate them. **A test that a wrong model also passes is not
evidence.** What separated them was byte-budget accounting (under the old model, bytes 24–31 —
14,528 bytes on LOD0 — were entirely unexplained) and reading the same bytes through the reference
implementation. This is the identical failure mode the 2026-08-14 bone-name work guarded against
with its null control, arrived at from a different direction.

Practical consequences: the render mesh is still *skeleton-skinned with no per-vertex sim binding*,
so **the conclusion that disproved "4561–4565 is the render↔sim binding" is unaffected** — it
rested on 1816 ≠ 170 + 62, which still holds. What changes is anything downstream of influence
count. For **lane 2B** that is direct: a weight transfer onto a GRB garment must carry up to four
influences per vertex, and `tools/blender/`'s `inspect` warns above four — the right threshold,
confirmed rather than assumed. `PackedJoints.MaxCount` is 8, so ATK itself can carry more.

### Built: [`tools/atk_bridge.py`](../tools/atk_bridge.py)
The loader recipe, packaged, so this is reproducible by a stranger. `start()` / `arm()` /
`resources()` / `read_mesh()` / `summarize()`, plus a CLI. The container layer stays **ours**
(`data_inspect.py` decompresses and slices the payload) and only the payload goes to ATK — that is
what keeps the two readers independent.

⚠️ It never calls `DataFile`. `DataFile.Deserialize` calls `CreateBackup` and unpacks to an
`Extracted\` folder — it **writes to the install**, which is not what "read-only test" means. The
docstring says so, at length, because the write path (`ForgeFile.Serialize`, `Mesh.WriteToFile`)
sits in the same object graph with none of ATK's application-level backup settings applying.

### Open questions
1. **The one-byte tail.** ATK over-read, or is the resource payload one byte longer than the record
   length says? Check a non-Mesh type through the same path — if `Skeleton` also wants +1, it is the
   container; if only `Mesh` does, it is the reader.
2. **`SubMeshes` is 0 on both LODs** while `Bones` is 30/25. Expected, or another silent gate?
3. **Does `AnvilGLTF.CreateGLTF` run headlessly too?** That is the one that matters — it would make
   the ATK export click automatable and change the pipeline diagram in
   [`tools/blender/README.md`](../tools/blender/README.md), which currently calls it manual. Same
   three gates presumably apply; the GLB it writes can be diffed against a GUI export.
4. **Re-check the other numbers 2026-07-01 derived from that hand parse** — `QuantizationFactor`,
   the position decode, the LOD1 figures. Two of its claims about the same vertex layout were wrong;
   the rest were verified three ways and stand, but they came from the same scratch parser.

### Addendum (same session) — `AnvilGLTF.CreateGLTF` gets all the way in, and a FOURTH silent gate

Pushed one step further than the mesh read, because any design built on top of this needs to know
whether the *export* half is automatable. Short answer: **yes, apparently** — the remaining failure
is a missing input, not a missing environment.

**Gate 4 — `HashedData.CheckStrings()` is a startup race.** Every hash→name lookup routes through
it, and it kicks its load off inside a `Task.Run` and **returns immediately**:

```csharp
public static void CheckStrings() {
    if (HashedStrings != null) return;
    Task.Run(delegate { HashedStrings = new Dictionary<uint, string>(); ... });
}
```

So the first caller dereferences a still-null dictionary → `NullReferenceException`. The GUI wins
the race by loading early; a headless caller loses it. This is the same failure that made
`ScimitarClass.ClassName` throw during the mesh test — recorded there as "cosmetic", which was
wrong: it is the same gate, and it blocks glTF export outright. `atk_bridge.prime_hashes()` starts
the load and waits for the count to settle.

> **⚠️ Inferred, not verified:** the settle-detection is a plateau check (two equal readings 0.3 s
> apart). ATK exposes no completion flag. A slower machine could plateau early and under-load.

**VERIFIED — `CreateGLTF` runs.** With hashes primed, the call reaches
`AnvilGLTF.ToGLTFS4(Mesh, Bones, ModelRoot, Scene)` and fails with
`Missing skeleton! Bone "LeftArm" not found.` — i.e. it got through argument marshalling, into the
real converter, and stopped because **I passed an empty skeleton list** for a skinned mesh. That is
correct behaviour on bad input, not an environment failure. **The remaining work to automate the
ATK export click is "locate and pass the garment's `Skeleton` resource", not "make the library
work."** ⚠️ Still unproven end to end: no GLB has been written yet, and nothing has been diffed
against a GUI export.

**VERIFIED — ATK's embedded dictionary is 820,037 names, ~3× what we extract by hand.**
[`atk_hashes.py`](../tools/atk_hashes.py) pulls **276,087** names out of `hashes.hl`; ATK's own
loader on the same install produces **820,037**. Our extractor is getting well under half of it.
Worth re-checking whether the missing ~544 k changes the 4 % GRB bone-hash resolution rate quoted
on 2026-08-14 — though the result below suggests not.

**The bone-name question, answered against the full dictionary.** `MeshBone` carries `Name` (a
CRC32) and `NameString` (resolved). On `TP_Tacvest_Walker_Coat_LOD0`, **8 of 30 resolve**:

```
LeftArm, RightArm, LeftShoulder, RightShoulder, Neck, Spine1, Spine, Hips
```

All eight are standard biped — consistent with the naming grammar in
[`grb-bone-names.tsv`](../reference/grb-bone-names.tsv) (unprefixed = biped). The other **22 stay
bare numbers**, and they are the ones that matter: bones 0–4 (the resolved arm/shoulder/neck set)
have `IsUsedBySubMeshes = False`, while nearly every *used* bone is unresolved.

This **hardens a lead rather than opening one**. The 2026-08-31 entry closed off "a modder's
original rig" as a source (no 3-D files in the local corpus). This closes off the richer dictionary
too: even ATK's complete 820 k table does not contain GRB's garment bone names, so the shortfall
was never our extractor. An animation resource storing track names as strings remains the best
untried bet.

**Practical upshot for tooling:** `atk_bridge.py` gained `prime_hashes()` and `hashed_string()`, and
`summarize()` now reports resolved bone names — which makes it, incidentally, a bone-name recovery
tool for any GRB mesh, not just a cross-check harness.

### Addendum 2 (same session) — built the pre-flight rebind validator

With the ATK bridge working, the first thing built on it is
[`tools/rebind_check.py`](../tools/rebind_check.py): given a physics-carrying
skeleton and a candidate GLB, does the new mesh's weight painting reach the bones
Reflex3 actually drives? Chosen over automating ATK's export/import clicks because
clicks cost minutes and a silent rigging failure costs a game launch — and a hung
GRB needs `taskkill /F /T`.

**It is the first thing in this project that needs both halves at once.** ATK reads
GRB meshes and skeletons but cannot parse Reflex3 (gated behind `Version !=
Game.Mirage`); `reflex3.py` parses Reflex3 but knows nothing about meshes. The check
is the intersection, which is why it could not have been written before today.

**VERIFIED — the name-matching trick that makes it work.** Reflex3 addresses bones by
CRC32 of the exact-case name, and GRB's dangle bones are absent from ATK's dictionary
— so `HashedData.GetHashedString` falls back to `id.ToString()` and ATK writes those
glTF nodes with **the number as the name**. A numeric node name therefore *is* the
bone hash, which sidesteps the unresolved-names problem entirely for this purpose.
Non-numeric names are CRC32-ed exact/lower/upper (ATK's own map convention), Blender's
`.001` suffixes stripped, and anything still unmatched is reported as a warning — the
tool degrades to "cannot check", never to a silent pass.

**Checks:** influences ≤ 4 (the `Joint4` limit corrected earlier today — a `JOINTS_1`
set is caught as up-to-8), weight coverage, UV sets (>5 rejected), vertex colours, and
the physics cross-reference. The physics result distinguishes two failures that need
different fixes: a driven bone **present in the skin but carrying no weight** (chain
will not move, *and* it is the bone most at risk from ATK's "removes unused bones" on
import) versus one **absent from the skin entirely** (wrong rig transferred).

**Tested** against `TP_HunterScarf_A_Skeleton` (6 driven bones, constraint types 5, 6,
24 — note **none** of type 21, so a Reflex3 rig need not contain a single
`Reflex3Physics` record) on five inputs: a synthetic clean case (PASS), a synthetic
case with 75 % coverage plus one unweighted and one missing driven bone (all three
caught), a two-`JOINTS`-set case (caught), the real Blender weight-transfer output
`_selftest_result.glb` (correctly FAILs — its synthetic `Coat_Root` names match no GRB
bone, and the warning says exactly that), and the unrigged poncho (correctly FAILs on
no skin). The GLB reader is stdlib-only and parses real `io_scene_gltf2` output.

> **⚠️ Not verified:** no *real* GRB garment has been through the full loop yet, because
> that still needs an ATK GLB export — which is the next thing the bridge could
> automate. The validator's own logic is tested; the pipeline it guards is not.

**Documentation gap found while wiring this up — two numbering spaces, one word.**
`Reflex3Physics` is **id 10** in ATK's `Reflex3ConstraintTypeRegistry` but the physics
record's **type byte in a GRB blob is 21** (`PHYSICS_TYPE` in
[`reflex3.py`](../tools/reflex3.py)). Both numbers are correct and the KB already holds
both — the 2026-08-14 (third) entry identified byte 21 as physics *empirically*
(`param[4] == 9.8` in 1,344/1,354 records, matching `Reflex3Physics.Gravity`'s ATK
default), not by matching ATK's registry. But
[`skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md) prints ATK's
registry table without saying it is a *different space* from the blob's type byte, so a
reader who greps a real blob for "type 10" finds nothing and a reader who sees "21" in
tool output cannot find it in the table. Ids 6/7/9 coincide across both spaces, which
makes the trap worse, not better. Noted in the reference doc.

---

## Entry — 2026-09-01 (second) — The ATK export click is automated, and a real garment went through the validator

### What I did
Finished the thread the previous entry left at *"the remaining work is to locate and pass the
garment's `Skeleton` resource, not to make the library work."* It was exactly that.

### VERIFIED — a real GRB garment exported to GLB with no ATK GUI
`AnvilGLTF.CreateGLTF` now returns cleanly and writes a valid file.
`TP_Tacvest_Walker_Coat_LOD0` → **351,640 B GLB**, generator `SharpGLTF 1.0.11`, containing:

| | |
| --- | --- |
| Geometry | **1816 verts / 3263 tris** — matches the raw read, and the 2026-07-01 parse |
| Skin joints | 271 — **51 named biped bones, 220 bare numbers** |
| UV sets | **5** (`TEXCOORD_0..4`) — exactly at the limit `docs/10` documents |
| Colour sets | **5** (`COLOR_0` + `_COLOR_1.._COLOR_4`) |
| Skinning | one `JOINTS_0`/`WEIGHTS_0` set |

**The 220 bare numbers are the point.** They are the dictionary fallback predicted in the previous
entry, arriving intact through a real export — which is what `rebind_check.py`'s whole
name-matching strategy rests on. That assumption is now observed rather than inferred.

**A garment needs TWO rigs, not one.** `CreateGLTF` refuses a skinned mesh whose bones it cannot
find, and the coat's 30 bones are split: 24 come from a character skeleton and the other **6** from
`Vest_Generic_Addon` (28 bones). No single skeleton in the install covers a garment. This is why
the first attempt failed with `Missing skeleton! Bone "LeftArm" not found` — an empty list.

### VERIFIED — the four-influence correction, confirmed a second way
The GLB's `JOINTS_0`/`WEIGHTS_0` accessors give the influence histogram
`{1: 490, 2: 53, 3: 238, 4: 1035}` — **identical** to the histogram read straight out of the raw
vertex buffer at bytes 24–31. Two entirely different paths (glTF accessors written by SharpGLTF vs
our own byte offsets) agreeing on the same numbers. The morning's correction is now doubly attested.

### The validator met real data, and real data found two bugs
Running `rebind_check.py` on the exported coat did what testing on synthetic GLBs could not.

1. **Colour sets were undercounted 5 → 1.** ATK/SharpGLTF writes the 2nd–5th colour set as the
   *custom* attributes `_COLOR_1.._COLOR_4` (glTF only standardises `COLOR_n`, so extras take an
   underscore prefix). The check counted `COLOR_`-prefixed keys only. A real garment would have been
   told it had one colour set when it had five — and since a missing colour set is exactly the
   "corrupted shading" failure `docs/10` names, that is a check that would have lied in the
   dangerous direction.
2. **⚠️ The physics check was scoped wrong, and this is the important one.** It compared the mesh
   against *every* bone the skeleton drives. Run against a real character rig, the vanilla coat —
   which is by definition correct — was reported as **FAIL: 61 driven bones carry no weight**,
   because `Skeleton_Harmony_Reflex` drives 74 bones including hair, straps and other garments'.
   A coat is never meant to weight them all.

   The honest reference set is **the driven bones the donor garment actually weights**, so
   `--donor` now scopes the check. Re-run: *"8 of the 8 bones the donor uses carry weight"*, 66
   correctly ignored, **PASS**. Without `--donor` the findings drop from FAIL to WARN and say so,
   because the tool genuinely cannot tell "you lost the coat's physics" from "the rig also drives
   somebody's hair".

   This was a **false FAIL on known-good input** — the failure mode that trains you to ignore the
   tool. Caught only by running it on something whose answer was already known.

3. Added a guard for the vacuous case: if a skeleton drives **none** of the donor's bones, the
   scoped set is empty and the old logic would have reported a cheerful PASS. It now hard-stops
   with "wrong skeleton for this garment".

### Tooling
- `atk_bridge.py`: `read_typed()` / `read_skeleton()`, `find_skeletons_for()` (greedy cover over
  every candidate rig), `export_gltf()`, and `--export out.glb` on the CLI. Auto-discovery works
  end to end: it located both rigs itself and exported.
  > ⚠️ It picks by **bone coverage alone** and several character rigs share biped bone names, so
  > ties break arbitrarily — it chose `Skeleton_Female_Cinematic_162_Reflex` where I had picked
  > `Harmony_Reflex`. Names and hierarchy are right, **rest pose may not be**. Pass `--skeleton`
  > explicitly if you care how it looks in Blender.
- **Fixed a genuine bug in both tools:** `read_typed` raised `SystemExit` on a missing resource.
  `SystemExit` derives from `BaseException`, so a sweep wrapped in `except Exception` was killed
  outright by the first container holding something else — which is precisely what happened while
  scanning 110 skeletons. Now `ResourceNotFound(LookupError)`.

### Where this leaves the pipeline
```
   ATK export  ──►  Blender transfer  ──►  rebind_check  ──►  ATK import  ──►  repack
   AUTOMATED        automated             automated          still manual     still manual
   (this entry)     (2026-08-31)          (this session)     FromGLTF untested
```
The front half runs headlessly end to end. **`FromGLTF`/`MeshFromGLTF` — the return trip — has not
been touched**, and the repack is deliberately still manual.

> **⚠️ Unchanged and still the wall:** nobody has confirmed a modified skeleton loads in game. Every
> bit of this assumes it. See [`next-session.md`](next-session.md).

---

## Entry — 2026-09-08 — Live Blender bridge installed; ATK's glTF *importer* called for the first time; the cloth gate is load-bearing

### Environment snapshot
- **Blender:** 5.2.1 LTS, `D:\SteamLibrary\steamapps\common\Blender` (Steam), bundled Python 3.13.13. Both 5.0 and 5.2 are installed; 5.2 is the one in use.
- **NEW — live control.** The official **Blender Lab MCP** add-on is now installed (`bl_ext.lab_blender_org.mcp`, from the `https://lab.blender.org/` extension repository), alongside this repo's own `grb_blender_addon`. The connector's Claude-side server was already running; only the Blender-side add-on was missing, which is why `localhost:9876` was closed. An assistant can now inspect and drive a *running* Blender session, not just the headless CLI. `grb_blender_addon` registers 4 operators (`analyze`, `transfer_weights`, `select_unweighted`, `export_glb`) and 3 panels.
- **ATK:** 1.3.1 at `D:\Anvil Toolkit`. `ilspycmd` available at `C:\Users\sylvi\.dotnet\tools\ilspycmd`.
- `grbblend.py doctor` and `selftest` both pass on this machine (7/7).

### Experiment 1 — the headless GLB round trip

**Method.** `atk_bridge.export_gltf` on `87874_-_TP_Tacvest_Walker_Coat_LOD0.data` → GLB in a scratch dir → back through **`AnvilGLTF.FromGLTF`**, which had never been invoked before this session → diffed against `read_mesh` of the same `.data`. Nothing was written outside the scratch directory; the install was read-only throughout.

> **Verified:** `AnvilGLTF.FromGLTF(string)` returns `(List<Mesh> meshes, List<ConvexVerticesShape> shapes)` and performs the **entire** import internally — it calls `LoadBoneNodes` and `MeshFromGLTF` itself. One call is the whole import side. Skeletons auto-resolved to `29770_-_Skeleton_Female_Cinematic_162_Reflex.data` and `29792_-_Vest_Generic_Addon.data`.

| field | original `.data` | round-tripped | |
| --- | --- | --- | --- |
| Vertices | 1816 | 1816 | PASS |
| Faces | 3263 | 3263 | PASS |
| SubMeshes | 0 | 0 | PASS |
| **Bones** | **30** | **25** | **DIFF** |
| VertexFormat | `…_Tex2s_Joint4_Col4ub` | `…_Tex2s_Joint4` | `Col4ub` dropped |
| VertexStride | 36 | 0 | buffer not yet built |
| VertexBuffer | 65,376 B | 0 B | buffer not yet built |
| IsUsingClusteredData | True | False | |

> **Verified — the export is faithful; nothing is lost on the way out.** Direct parse of the GLB's JSON chunk: 1 mesh, 15 attributes — `POSITION`, `NORMAL`, `TANGENT`, `TEXCOORD_0..4` (**5 UV sets**), `COLOR_0` + `_COLOR_1..4` (**5 colour sets**), `JOINTS_0`, `WEIGHTS_0`; no glTF extensions; 262 nodes, 1 skin, 0 unreachable nodes. Blender agrees independently: 5 UV sets, 5 colour layers, max 4 influences/vertex, **0 unweighted vertices**.

What actually changes is on **re-import**:

- **Bones 30 → 25.** The importer keeps only bones that carry weights (Blender: "260 vertex groups, **25 actually used**"). The 5 lost bones were weightless entries in the original mesh's bone table.
- **`VertexStride`/`VertexBuffer` are 0** because the buffer is not serialized until it is written. **`RemapBuffers` does *not* rebuild it** — verified from decompiled source, it only reorders `Vertices` into face-traversal order and rewrites face indices. The format/buffer step is elsewhere.
- **The `Col4ub` drop is the importer's own format guess**, and is exactly the vertex-format choice [`docs/10-meshes-and-skeletons.md`](../docs/10-meshes-and-skeletons.md) warns is the step most likely to bite on import.

> **Inferred, NOT verified:** whether the 5 dropped bones or the format guess actually break a garment in game. Untested. The point of the round trip is that both are now **measurable before anything ships**, instead of surfacing as a corrupted garment with no way to localise the cause.

> **Note on the pipeline claim.** [`tools/blender/README.md`](../tools/blender/README.md) says "the two ends stay manual, and that's not going away soon." Since 2026-09-01 the export end is scripted; as of today the import end is **demonstrably callable too**. Only the final write-back into a `.data`/forge remains manual — and that one stays manual by policy, not capability.

### A false positive in this repo's own inspector — the phantom `Icosphere`

`grbblend.py inspect` reported a **second** mesh, `Icosphere` (42 verts, 80 tris), and warned that it had no vertex colours. It is not in the GLB — the JSON chunk has `meshes=1`, no extensions, and no unreachable nodes.

> **Verified by control experiment:** importing `_selftest/_selftest_coat.glb` (**rigged**) into a genuinely empty scene produces an `Icosphere`; importing `_selftest/_selftest_poncho.glb` (**not rigged**) does not. **Blender's own glTF importer synthesises it for skinned GLBs** as a bone-display shape. It is unparented, at the origin, with no materials, no vertex groups, and no custom properties.

**Consequence:** `inspect` raises a spurious *"no vertex colors — GRB uses them"* warning on **every rigged GRB garment**, i.e. on exactly the files it is meant to validate. The fix is to filter the importer's bone-shape object out of the report. (Also checked: `_inside.py`'s `reset_scene()` *is* called by `cmd_inspect` — the scene is clean; the Icosphere is genuinely the importer's doing.)

### Experiment 2 — the cloth gate is LOAD-BEARING, and `SoftBody` is the wrong door

**Method.** `34800_-_Cloth_FTP_Kilt.data` — one `Cloth` resource, **type id 3811591354**, 436,220 B. Built the `ScimitarClass` base through the same path `read_typed` uses, then constructed `SoftBody` over it, before and after appending GRB to the gate list. **In memory only — `AnvilToolkit.dll` on disk was never modified.**

> **Verified:** ATK's own hash dictionary resolves this resource's class name to **`'Cloth'`** (hash 3811591354), and `SoftBody.FileActionType` is `MeshViewerCloth`. `SoftBody` *is* ATK's cloth class — so this is the right door to try, and the gate is what closes it.

> **Verified from source** (`ilspycmd -t …Physics.SoftBody`) — the gate is **inside `Read`**, and the throw is **swallowed** into `Failed = true`. In outline: `Read` begins with `if (!SupportedGames.Contains(base.Version)) throw new Exception("This file format is unsupported for this game");` and the whole body is wrapped in a `try`/`catch` that does `Console.WriteLine(ex.Message); Failed = true;`. Another silent-when-wrong path of exactly the kind [`atk_bridge.py`](../tools/atk_bridge.py)'s docstring already catalogues.

`SoftBody.SupportedGames` = `[AC2, Brotherhood, Revelations, AC3, AC3Remastered, BlackFlag, Rogue, Unity, Syndicate]` — **GRB absent**. It is a `public static List<Game>` with `IsInitOnly=False`, so it *can* be appended at runtime. A sweep of every type in a `*.Physics*` namespace found **zero** that admit `GhostReconBreakpoint`. And `AnvilGLTF.CreateGLTF`'s 4th parameter is `List<SoftBody> clothObjects` — so GRB cloth **structurally cannot reach the glTF exporter** either; `export_gltf` passing an empty list is a consequence, not an oversight.

| | `Failed` | `SoftBodyStates` | ATK console |
| --- | --- | --- | --- |
| **A.** as shipped | True | 0 | `This file format is unsupported for this game` |
| **B.** GRB appended in memory | True | **257** | same message *(from a nested type's gate)*, then `Unable to read beyond the end of the stream.` |

> **Verified conclusion: the gate is load-bearing, not merely conservative.** Ground truth for this file, from this repo's own `cloth_inspect`, is **2 cloth LODs** with simulation cages of 262 pt/482 tri and 120 pt/210 tri. With the gate open, `SoftBody.Read` interprets the leading `int32` as a state count and gets **257**, then runs off the end of a 436 KB stream. The two formats are unrelated: AC-era `SoftBody` is a list of `ObjectPtr` states, whereas GRB cloth is a `ClothPackage` of `MotionBody` **section streams** — each section `uint16 TypeID | uint16 0xECD7 | int32 SizeIncludingHeader` (see [`reference/cloth-section-types.md`](../reference/cloth-section-types.md)). The residual "unsupported for this game" in run **B** comes from *nested* gates: `SoftBodyState`, `SoftBodyLOD`, `SoftBodyConstraint` and `SoftBodyVertexMapping` are gated to `AC2..Rogue` only, so opening the top gate merely exposes a chain of them.

**What this kills.** The hope that ATK's GRB cloth support is one static-list edit away. It is not. Appending GRB to `SupportedGames` — at runtime, or by patching the assembly — produces garbage, and would produce the same garbage in the GUI. **Do not spend time on it.**

**What this leaves standing.** The **72** `Physics.MotionCloth.*` section types carry **no `SupportedGames` field at all** — they are ungated and fully modelled, just not reachable through `SoftBody`. The route to ATK-side GRB cloth is wiring *those* up, which [`tools/motioncloth.py`](../tools/motioncloth.py) already does independently. And the **22 sections GRB uses that ATK does not model at all** (2026-08-09 sweep) remain the most plausible home of the render↔sim binding.

**A reference implementation worth porting.** `SoftBody` exposes `ComputeBarycentric`, `ClosestPointOnTriangle`, `GetSimulationBones` and `ToMesh`/`ToMeshNext`/`ToMeshOld`, and there is a `SoftBodyVertexMapping` type. That is a complete cloth→mesh rebind implementation — for AC-family formats. It is something to **port**, not a switch to flip. This sharpens, rather than replaces, the 2026-07-01 finding that "ATK already has the algorithm".

### Open questions raised here
- Where does the importer actually decide `VertexFormat`? Grepping the decompiled `AnvilGLTF` for `VertexFormat` returns **nothing** — it is set elsewhere (in `Mesh`, or by the GUI's format picker). Worth pinning down before any write-back, since it is the documented failure point.
- Do the 5 weightless dropped bones matter in game? GRB may index a mesh's bone table positionally.
- Are the 22 unmodelled GRB sections where the binding lives? (Carried forward from 2026-08-09; unchanged by today's work, but now the *only* live route on the ATK side.)

---

## Entry — 2026-09-08 (second) — Where `VertexFormat` is decided; corrects the "importer's format guess" claim from this morning

Answers the first open question left by the entry above, and **corrects that entry**: it
described the round trip's `Col4ub` loss as "the importer's own format guess". That is wrong.
Nothing guesses. The format is derived deterministically from a table lookup, and the loss is
caused by something else entirely. Per house style the earlier entry is left standing; this is
the correction.

### The chain, verified from decompiled source

**1. `Mesh.VertexFormat` is not stored on the mesh.** It is a facade over `CompiledMesh`:

- **getter** — returns `((CompiledMesh)CompiledMesh).VertexFormat`, or, when `CompiledMesh` is
  null, a **hardcoded** `Pos3s_Col1s_Norm3ub_Col1ub_Tan4ub_Binorm4ub_Tex2s_Joint4`.
- **setter** — `if (CompiledMesh != null) { … }` and **nothing otherwise**. A silent no-op.

**2. It is assigned at *write* time, from vertex zero alone.** In `Mesh.WriteToFile`:

```
VertexFormat = Vertices[0].Format;
int gsvf = VertexFormatsMap.GetGameSpecificVertexFormat(base.Version, VertexFormat);
VertexStride = (byte)VertexFormatSizes.GetVertexFormatSize(base.Version, gsvf);
```

The same three lines appear in `WriteToFileAC1` and `WriteToFileRPG`. There is no format
picker in `AnvilGLTF` at all — grepping the decompiled `AnvilGLTF` for `VertexFormat` returns
nothing, which is why the first search missed it.

**3. `WriteToFile` mutates vertex zero per game first, and GRB has its own case:**

```
case Game.GhostReconBreakpoint:  Vertices[0].Version = 3; UVScale = 16f;  break;
…
case Game.GhostReconBreakpoint:  Vertices[0].Color3    = null;
                                 Vertices[0].Color4    = null;
                                 Vertices[0].TEXCOORD_4 = null;  break;
```

**4. `Vertex.Format` is a dictionary lookup.** `AnvilToolkit.Common.Vertex` computes a
descriptor and hands it to `VertexFormats.GetVertexFormat`:

```
_Format => (Position != null, Normals != null, Tangents != null, Binormals != null,
            Color: ColorCount, UV: UVCount, Skinning: JointCount, Version: Version)
```

`ColorCount` and `UVCount` are plain counts of non-null `COL_0..COL_4` / `TEXCOORD_0..TEXCOORD_4`.
`VertexFormats.Types` holds **62** entries; a descriptor not among them returns
`VertexFormat.Null`.

### What that means for the Walker coat — measured

> **Verified 2026-09-08** by reading the real mesh and the re-imported mesh and evaluating the
> descriptor at each stage (in-memory; nothing written):

| stage | descriptor `(P,N,T,B,Color,UV,Skin,Ver)` | resulting format |
| --- | --- | --- |
| original, as read from the forge | `(T,T,T,T,3,1,4,`**`0`**`)` | `Null` — **not in the table** |
| original, after the GRB write prep | `(T,T,T,T,3,1,4,`**`3`**`)` | `…_Tex2s_Joint4_Col4ub` ✅ correct |
| round-tripped, as `FromGLTF` returns it | `(T,T,T,T,`**`2`**`,1,4,0)` | `…_Tex2s_Joint4` |
| round-tripped, after the GRB write prep | `(T,T,T,T,`**`2`**`,1,4,3)` | `…_Tex2s_Joint4` — still wrong |

**The write path is self-consistent.** Setting `Vertices[0].Version = 3` is precisely what
lifts the vanilla descriptor into the table, and it resolves to the coat's true original
format. A vanilla GRB mesh would write its format back correctly. GRB's nulling of `Color3`,
`Color4` and `TEXCOORD_4` is a **no-op on this mesh** — those slots are already empty.

> **The defect is upstream, in `AnvilGLTF.MeshFromGLTF`:** it rebuilds a vertex with
> `ColorCount` **2** where the original had **3**. That single unreconstructed colour channel
> is the entire cause of the `Col4ub` loss, and it survives the write because the descriptor
> is what selects the format. **The fix target is the importer's colour reconstruction, not a
> format picker** — which is what the earlier entry got wrong.

### Two silent-failure paths worth naming

1. **`VertexFormat.Null` is returned, not thrown.** `GetVertexFormat` falls back to `Null` for
   any unmapped descriptor, and `WriteToFile` assigns it without checking — then computes
   `VertexStride` from it. No exception, no log line.
2. **The `VertexFormat` setter no-ops when `CompiledMesh` is null**, so
   `VertexFormat = Vertices[0].Format` can quietly not happen while the getter keeps returning
   the hardcoded default. (Not what happened in the round trip — the re-imported mesh *does*
   have a `CompiledMesh` — but it is live in this code path.)

### The UV/colour counts in `inspect` are an upper bound, not a measurement

> **Verified:** `AnvilGLTF.CreateGLTF` writes vertex data through `Vertex.GetUVs()` and
> `Vertex.GetColors()`, which return `new PackedUV()` / `PackedRGBA(1,1,1,1)` for **null**
> slots. So the writer emits **all five** UV and **all five** colour channels unconditionally,
> padding the absent ones.

That resolves an apparent contradiction in the entry above: Blender reported 5 UV sets and 5
colour layers on a mesh whose `VertexFormat` names a single `Tex2s`. Both are true — the GLB
carries five, the vertex buffer holds **`UVCount = 1` and `ColorCount = 3`**, on both sides of
the round trip. The earlier entry's "the GLB carries everything: 5 UV sets, 5 colour sets"
is therefore right about the *file* and misleading about the *mesh*.
[`tools/blender/README.md`](../tools/blender/README.md) now says so at both places a reader
would meet those numbers.

### Still open
- **Why does `MeshFromGLTF` reconstruct only 2 colour channels?** The importer reads all five
  (`GetVertexColor(0)` … `GetVertexColor(4)`); something downstream of that assigns fewer.
  This is now the single concrete blocker on a faithful mesh write-back.
- Do the 5 weightless dropped bones matter in game? (unchanged)
- `VertexFormatsMap.GetGameSpecificVertexFormat` and `VertexFormatSizes.GetVertexFormatSize`
  were not read this session — they map the format to a per-game id and a stride, and they sit
  directly on the write path.

---

## Entry — 2026-09-09 — The dropped colour channel is an unset global, and the importer does not reconstruct a vertex format at all

Answers the blocker the 2026-09-08 (second) entry left as *"Why does `MeshFromGLTF`
reconstruct only 2 colour channels?"* — and **corrects that entry twice over**. It named
"the importer's colour reconstruction" as the fix target. The reconstruction is fine; it
writes all five channels unconditionally. And the deeper answer is that the importer does
not reconstruct the format in *any* sense — it normalises every skinned GRB mesh to the
same descriptor. Per house style the earlier entry is left standing; this is the correction.

### What I did
Decompiled `AnvilGLTF`, `AnvilToolkit.Common.Vertex`, `Mesh`, `DataStorage` and the `Game`
enum from `AnvilToolkit.dll` 1.3.1, then measured the round trip through
[`tools/atk_bridge.py`](../tools/atk_bridge.py) on four real garments. Everything was
in-memory or into a scratch directory; the install was read-only throughout.

### VERIFIED — the colour is dropped by a *game branch*, not by the reconstruction

`MeshFromGLTF`'s per-vertex loop assigns **all five** colour and **all five** UV slots
unconditionally, substituting a default when the GLB has no such accessor:

```
vertex.Color0 = (list6 != null) ? new PackedRGBA(...) : new PackedRGBA(1,1,1,1);
vertex.Color1 = (list7 != null) ? new PackedRGBA(...) : new PackedRGBA(1,1,1,1);
vertex.Color2 = (list8 != null) ? new PackedRGBA(...) : new PackedRGBA(0,0,0,0);
…  and the same shape for TEXCOORD_0..4
```

Nothing is lost there. The loss happens afterwards, in a `switch (DataStorage.ActiveGame)`
that nulls slots on **`Vertices[0]` only** — the vertex whose descriptor selects the
format:

| branch | nulls on vertex zero |
| --- | --- |
| `GhostReconBreakpoint` | `Color3`, `Color4`, `TEXCOORD_4` |
| `BlackFlag`/`Rogue`/`AC2`/`Brotherhood`/`AC3`/`AC3Remastered` | `TEXCOORD_1..4`, `Color3`, `Color4`, **and `Color2` when `Joints.Count != 0`** |

> **Verified:** the Walker coat is skinned, so under the Black Flag branch that last clause
> fires and takes `Color2` with it. `ColorCount` **3 → 2**. That one clause is the whole of
> the "importer drops a colour channel" defect.

### VERIFIED — why the Black Flag branch ran at all: a global nobody set

```
public static Game ActiveGame;          // AnvilToolkit.Utils.DataStorage
public enum Game { Null = -1, BlackFlag, Rogue, AC2, … }
```

No initialiser, and the sentinel `Game.Null` is **-1** — so an unset field reads as
`(Game)0`, which is **`BlackFlag`**: a real game with real, wrong code paths. Nothing
throws. It is assigned in exactly **two** places, `MainWindow.cs:325` and
`GameSelector.cs:182` — i.e. only when a human picks a game in ATK's GUI — and **68 files
read it**, including `Schema`, `XmlUtils`, `Reference`, `Object`, the compression manager
and `AnvilGLTF`.

The bridge's read helpers were never affected, because they pass `game()` explicitly to
each constructor. Anything that consults the global was.

> **⚠️ A fifth silent gate, of the same family as the four already catalogued in
> [`atk_bridge.py`](../tools/atk_bridge.py)'s docstring.** Wrong value, valid enum, plausible
> output, no error. **Fixed** — `arm()` now sets `DataStorage.ActiveGame` alongside
> `GlobalScimitarClassReader`, which is exactly its job: make ATK's GUI-only statics look
> like a game is open.

### VERIFIED — and the bigger finding: the importer NORMALISES, it does not reconstruct

With the global set, the coat comes back with `ColorCount = 3`, matching the original. That
is **coincidence, not fidelity.** The GRB branch always leaves exactly `Color0..2` and
`TEXCOORD_0..3` standing, so *every* skinned GRB mesh returns from `FromGLTF` as
**`ColorCount 3, UVCount 4`** whatever went in. Measured on four garments:

| mesh | original (col/uv) | round-tripped | |
| --- | --- | --- | --- |
| `TP_Tacvest_Walker_Coat_LOD0` | 3 / **1** | 3 / **4** | DIFFERS |
| `TP_Tacvest_Walker_Coat_LOD1` | 3 / **1** | 3 / **4** | DIFFERS |
| `Tsec_Madera_Coat_LOD0` | 3 / 4 | 3 / 4 | matches — it was already at the constant |
| `TP_Pants_Tactical_Kilt_LOD0` | 3 / 4 | 3 / 4 | matches — it was already at the constant |

**That is how this stays invisible.** Most GRB garments already sit at (3, 4), so the round
trip looks lossless; the Walker coat, at (3, 1), is what exposed it.

The cause is symmetric with the export. `CreateGLTF` writes all five UV and all five colour
channels unconditionally through `GetUVs()`/`GetColors()`, padding absent ones (2026-09-08),
so the GLB cannot distinguish a real channel from a pad — and the importer, reading it back,
has nothing to distinguish them by either. **The target format must come from the donor
`.data`, not be inferred from the round trip.**

### VERIFIED — a second wrong-game trap, on the write path

`MeshFromGLTF` builds its result with `ScimitarClassReader.New(Game.BlackFlag, 1096652136u)`
and **never assigns `mesh.Version`**. `Mesh.WriteToFile` switches on `base.Version` — not on
`ActiveGame` — in ten places, including `GetGameSpecificVertexFormat(base.Version, …)` and
`GetVertexFormatSize(base.Version, …)`. So a re-imported mesh claims to be a Black Flag mesh
no matter what the active game is. Measured: `mesh.Version = BlackFlag` with `ActiveGame`
unset **and** with it set to GRB. The property is settable, so a caller can correct it.

### VERIFIED — three corrections reproduce the original exactly

Evaluating `WriteToFile`'s own three lines (`VertexFormat = Vertices[0].Format` →
`GetGameSpecificVertexFormat` → `GetVertexFormatSize`) without writing anything:

| stage | col | uv | format | game id | stride |
| --- | --- | --- | --- | --- | --- |
| original on disk | 3 | 1 | `…_Tex2s_Joint4_Col4ub` | 1 | **36** |
| round trip as the bridge ran it | 2 | 1 | `…_Tex2s_Joint4` | 0 | 32 |
| `+ ActiveGame = GRB`, `+ mesh.Version = GRB` | 3 | 4 | `…_Tex2s_Tex2s_Tex2s_Joint4_Col4ub_Tex2s` | 5 | 48 |
| `+ padded TEXCOORD_1..4 cleared on vertex zero` | 3 | 1 | `…_Tex2s_Joint4_Col4ub` | **1** | **36** ✅ |

The third row is worth staring at: fixing the game **widens** the stride from 32 to 48,
further from the truth than the bug was, because the padded UV channels are now believed.
Only trimming them to the donor's real count lands on 36.

### NOT verified
- **Whether any of this matters in game.** No mesh has been written back. The stride and
  format now agree with the original *as computed by ATK's own write path*; no bytes were
  produced and nothing was loaded.
- **Whether trimming by donor UV count is right in general.** It is right when the donor's
  count is known. Nothing here recovers a *new* mesh's intended channel count.

### Incidental — `RemapBuffers` drops orphan vertices
`Tsec_Madera_Coat_LOD0` came back **12,498** vertices against the original's **12,502**.
`RemapBuffers` rebuilds the list from face traversal, so any vertex no face references is
gone. Four in that mesh. Not a defect, but it means vertex counts can legitimately shrink
across a round trip, and a count check alone will flag it.

### Addendum (same session) — built the write-back checker, and found a sixth gate that is *loud*

Built [`import_gltf()`](../tools/atk_bridge.py) — the import-side counterpart to
`export_gltf`, and the thing the entry above left in its open questions. It runs a GLB
through `AnvilGLTF.FromGLTF`, applies the three corrections, and reports **what vertex
format the file would actually get**, without writing anything. `python atk_bridge.py
<donor.data> --import new.glb`; exit status 2 when it does not match the donor.

Supporting pieces: `_write_prep()` replicates `Mesh.WriteToFile`'s prologue without a
stream, `write_preview()` evaluates its three format lines, and `_glb_summary()` reads a
GLB's JSON chunk directly for the two things ATK will not report — the vertex count as the
*file* has it, and whether any colour/UV channels exist at all.

> **Verified — trimming vertex zero alone is correct, and not a shortcut.**
> `Mesh.WriteVertexData` writes *every* vertex as
> `vertex.WriteToFile(bw, VertexFormat, …)` — one mesh-level format, taken from vertex zero.
> Slots trimmed there are simply not written; slots missing on other vertices are padded by
> `GetUVs()`/`GetColors()`. The buffer is uniform by construction, which is what makes a
> single `VertexStride` meaningful.

### ⚠️ A SIXTH gate — and unlike the other five it is not silent, it is fatal

`MeshFromGLTF` calls **`WpfMessageBox.Show`** when the GLB carries no vertex colours, and
again when it carries no UVs. Headless there is no WPF dispatcher, so `WpfMessageBox..ctor()`
throws and the entire import dies — on exactly the fresh-from-Blender mesh a modder is most
likely to bring. Reproduced on `_selftest/_selftest_poncho.glb`.

> **Verified:** its own guard flag is useless here. `FromGLTF` begins with
> `VertexColorMessageShown = false;`, so pre-setting the static is undone on entry.
> (`TexCoordMessageShown` is *not* reset — an inconsistency in ATK, not in us.) The only
> lever that works for both is
> `AnvilToolkit.Properties.Settings.Default.SuppressMeshViewerImportErrorMessages`.

`import_gltf` borrows that setting for the call and restores the previous value in a
`finally`, then reports the same two conditions itself from the GLB. **`Settings.Save()` is
never called** — an in-memory property set does not touch ATK's user config, and calling
Save would.

### ⚠️ VERIFIED — `RemapBuffers` moves the prepped vertex, so vertex zero is not reliable

`MeshFromGLTF` normalises `Vertices[0]` and *then* calls `RemapBuffers`, which rebuilds the
list in face-traversal order. The prepped vertex goes wherever that puts it. Counting the
per-vertex `(ColorCount, UVCount)` distribution across a whole mesh shows exactly one
outlier:

| GLB | distribution | prepped vertex ends up at |
| --- | --- | --- |
| Walker coat | 1815 × (5,5), 1 × (3,4) | index **0** |
| selftest poncho | 623 × (5,5), 1 × (3,4) | index **67** |

**Writing is unaffected** — `WriteToFile` re-preps whatever is at index 0 by then, which is
why this has never broken anything. **Inspection is fooled**, and that is worth knowing: it
retro-explains why the 2026-09-08 round-trip table was legible at all (the coat's prepped
vertex happened to stay at index 0; a mesh like the poncho would have reported a raw
`(5, 5)` and told a different story). `import_gltf`'s report labels those numbers
`at index 0 … (raw)` rather than "as imported".

### Tested on five inputs, including a negative

| input | donor | result |
| --- | --- | --- |
| Walker coat LOD0 round trip | itself | **MATCH** — `…_Tex2s_Joint4_Col4ub`, stride 36 |
| Walker coat LOD1 round trip | itself | **MATCH** — same format, stride 36 |
| `Tsec_Madera_Coat_LOD0` round trip | itself | **MATCH** — 4-UV format, stride 48 |
| `TP_Pants_Tactical_Kilt_LOD0` round trip | itself | **MATCH** — stride 48 |
| unrigged selftest poncho | Walker coat | **MISMATCH**, exit 2 — and the warnings say why: no vertex colours, no bones, `stride 24 vs 36` |
| Walker coat round trip | *none* | runs, and says loudly that stride **48** is the normalised constant, not a measurement |

The negative case is the one that matters: an unrigged mesh against a skinned donor is the
most likely real-world mistake, and it now fails with three specific reasons instead of a
plausible-looking `Mesh` object.

### Still not done
- **Nothing is written.** `import_gltf` hands back a live in-memory `Mesh`. Getting it into
  a `.data` and repacking a forge stays manual, backed-up, and deliberate — CLAUDE.md rules
  1 and 2. No mesh has been through the game.
- The donor supplies channel *counts*, not channel *meaning*. Nothing here recovers what a
  genuinely new mesh's channels ought to be.

### Open questions
- Does GRB index a mesh's bone table positionally? (unchanged — bears on the 5 weightless
  bones the importer drops)
- The **22 unmodelled GRB cloth sections** remain the live ATK-side cloth route (unchanged).
- ~~Should `import_gltf()` exist in the bridge?~~ **BUILT, same session** — see the addendum
  above. What it cannot do is decide what a genuinely new mesh's channels *should* be; it
  only carries the donor's counts across.

---

## Entry — 2026-09-09 (third) — Lane 2B step 1 is done: `PLAYER_Template` exports to XML, and it does **not** assign skeletons

Step 1 of lane 2B, un-run since 2026-08-14: *"Get an ATK XML export of `PLAYER_Template`.
Cheapest possible check — it settles which `EntityBuilder` field the reference records live
in, and gives an editable round-trip path."* Done. The answer is **none of them**, and the
route to a rig assignment is one level further out than this KB has been assuming.

### VERIFIED — the XML export runs headlessly, and it took two more gates

| | base `28359_-_PLAYER_Template.data` | patch `22_-_PLAYER_Template.data` |
| --- | --- | --- |
| EntityBuilder payload | 63,625 B | 63,625 B |
| `Failed` | False | False |
| XML | 651,239 chars / 11,234 lines | 652,906 chars / 11,262 lines |

> **⚠️ Gate 6 — `WriteXml` needs an STA thread.** `ScimitarClass.ToXml` recurses into
> `Handle.ToXml` → `XmlUtils.WriteToXMLRef` → `GameFileList.GetFileReference`, which reaches
> `WpfMessageBox`; WPF refuses to initialise outside a single-threaded apartment, and
> pythonnet's CLR thread is MTA. It dies with *"The calling thread must be STA"* before
> writing a byte. Fix: run the call on a `Thread` with `SetApartmentState(STA)`.

> **⚠️ Gate 7 — `GameFileList` looks for its list at a RELATIVE path, and asks to download it
> when it cannot find one.** `GameFileList.CheckStrings()` opens
> `"Lists/" + DataStorage.ActiveGame + ".gfl"` — relative to the **process working
> directory** — and on a miss calls `WebUtils.CheckWebsite` and then
> `WpfMessageBox.Show("Game File List", "…do you want to download it now?")`. On an STA
> thread that dialog now *constructs*, and dies on a missing XAML resource instead. ATK ships
> the file at `D:\Anvil Toolkit\Lists\GhostReconBreakpoint.gfl` (6.8 MB, dated Oct 2025), so
> the fix is to point the working directory at the ATK folder for the call. Then it loads —
> **1,053,342 entries** — and no dialog is ever built.

**That second one is worth more than a workaround.** With the list primed, every 64-bit
reference in the XML renders as a real path. Without it they are bare decimal numbers:
technically correct, unreadable, and useless for the editing this step exists to enable.
Note it is also loaded in a `Task.Run` and must be waited for, exactly like
`HashedData.CheckStrings` (2026-09-01).

### VERIFIED — where a rig assignment actually lives

`PLAYER_Template`'s `EntityBuilder`, by field:

| field | base | patch |
| --- | --- | --- |
| `BuildColumns` | 6 | 6 |
| `BuildRows` | 3 | 3 |
| `SubTables` | **2,885** | **2,893** |
| `Template` | 1536663478066 | 1536663478066 |
| `TemplateOverrides` / `Tables` / `Dependencies` / `ForceBuilTableTOCOrder` | 0 | 0 |

The rigs are reached through a **`BuildTable` named `PLAYER_SkelAddons`**, ID
**1898138514560**, which appears **four times** — three inside `BuildRows`, once in
`SubTables`:

```xml
<DynamicProperty Index="42">
  <Value Name="DataType" Type="UInt32" HashName="BuildTable">585940579</Value>
  <Value Name="Type" Type="UInt32">1835008</Value>
  <Value Name="Unk00" Type="UInt32">0</Value>
  <Reference>
    <FileReference Name="Value" IsGlobal="0"
        Path="DataPC\TEAMMATE_Template\PLAYER_SkelAddons.BuildTable">1898138514560</FileReference>
  </Reference>
</DynamicProperty>
```

So the chain is `EntityBuilder → BuildRows → BuildRow → Components → DynamicProperty(Index 42,
DataType `BuildTable`) → Reference → FileReference`. **`PLAYER_SkelAddons` is the editable
surface**, not `PLAYER_Template` itself.

> **Two side-effects of reading this.** (1) `Type` here is **1835008 = `0x1C0000`** — the same
> unexplained `Type` UInt32 that [`buildtable-xml.md`](../reference/buildtable-xml.md) lists as
> open from the lane-1 pants export. A second sighting, in a different category, with a
> `DataType` of `BuildTable`. (2) The path string says `DataPC\TEAMMATE_Template\…` while the
> *player* template references it, so **`PLAYER_Template` and `TEAMMATE_Template` share one
> skeleton-addon table.** That softens the 2026-08-14 framing of "player-wearable precedents"
> as a property of `TEAMMATE_Template`: they are the same list.

### ⚠️ CORRECTION — an `EntityBuilder` does not contain the skeleton records

The 2026-08-14 entry says: *"An **`EntityBuilder`** assigns skeletons — nothing else does."*
Measured today, that is not right about the **resource**:

> **Verified:** the `EntityBuilder` payload — all **63,625 B** of it, parsed cleanly by ATK's
> own reader with `Failed = False` — contains **zero** occurrences of the 19-byte skeleton
> reference prefix. The whole decompressed container is **188,342 B** and
> [`entity_skeletons.py`](../tools/entity_skeletons.py) finds **11** in it.

So the records are real, and they are in the container, but **outside the typed
`EntityBuilder` resource**. `data_inspect` reports the container as holding exactly one typed
resource, so ~125 KB of it is not accounted for as a typed resource at all. The 2026-08-14
sweep decompressed whole resources and matched a byte pattern — which finds the records
correctly and attributes them to the wrong owner. **What holds them is now open.**

### The 11 rigs, and which ones move

Unchanged between base and patch:

| slot | skeleton | Reflex3 blob |
| --- | --- | --- |
| 1 | `Regular_Male_Reflex_SklAdd` | **107,350 B** |
| 12 | `BodyUp_Skeleton` | 10,443 B |
| 11 | `Watch_Skeleton` | 5,556 B |
| 1792 | `Tpri_Schultz_Beard_Addon` | 2,710 B |
| 3328 | `Tpri_Schultz_gloves_addon` | 1,166 B |
| 5 / 4 / 2816 / 3 / 10 / 4864 | head, body, props, costume head, hat, weapon-attach rigs | — |

**`Regular_Male_Reflex_SklAdd` carries 107,350 B of bone physics and is referenced by the
PLAYER.** That is **2.5×** the `Tsec_Trench_AddonSkeleton` blob (43,494 B) which 2026-08-14
called the vanilla flowing-coat exemplar *and* flagged as NPC-only. The largest bone-physics
rig found so far is on the player already.

### ⚠️ `PLAYER_Template` is forge-shadowed too

Base 188,206 B vs patch 188,342 B, and `SubTables` **2,885 → 2,893**. The patch copy is the
live one. Same hazard as cloths and skeletons: an edit must target the patch, or both.

### NOT verified / open
- **Where `PLAYER_SkelAddons.BuildTable` (1898138514560) actually lives.** It is **not** a
  top-level entry in `DataPC`, `DataPC_patch_01`, `DataPC_extra_patch_01` or
  `DataPC_Resources` — all four indexes were dumped and searched. ATK's file list knows a path
  for it, so it exists; it is presumably a resource inside another container. Finding it is
  the next concrete step, because it is what a rig-assignment edit would target.
- **Which part of the container holds the 11 skeleton records** (see the correction above).
- `TEAMMATE_Template`'s container holds a second resource of unknown type `#444870144`,
  **15,973,783 B**, which `data_inspect` mis-slices (its name field reads as binary). Not
  chased.

### Tooling
[`atk_bridge.py`](../tools/atk_bridge.py) gains `prime_filelist()` (gate 7, with the
plateau-wait), `_on_sta()` (gate 6) and `export_xml()`, plus `--xml out.xml` on the CLI and an
`ATK_XML_TYPES` map of the resource types that declare `FileActionType.Xml`. **Read-only
against the install; it writes only the XML path you name.**

### Addendum (same session) — found it: an ATK file-list path is `forge / container / resource`

The entry above left "where does `PLAYER_SkelAddons.BuildTable` live?" open, having searched
four forge indexes for its ID and found nothing. The search was wrong, not the question: it is
not a top-level forge entry, and **the path ATK printed was already the answer** — I read it as
an authoring path.

> **Verified from source and confirmed with controls.** `GameFileListEntry` holds
> `{int ForgeIndex, int DataIndex, string Name, uint Extension}` and
> `GetPath(ForgeFiles, DataFiles)` is
> `Path.Combine(ForgeFiles[ForgeIndex], DataFiles[DataIndex], Name) + "." + Extension.GetHashedString()`.
> So every path in the list decomposes as **forge / container / resource-name . type**.

Reading the fields back by reflection for three IDs:

| ID | forge | container | name |
| --- | --- | --- | --- |
| 1898138514560 | `DataPC` | **`TEAMMATE_Template`** | `PLAYER_SkelAddons` |
| 1536663434687 *(control)* | `DataPC` | `PLAYER_Template` | `PLAYER_Template` |
| 1707208439117 *(control)* | `DataPC_Resources` | `TP_Tacvest_Walker_Coat_LOD0` | `TP_Tacvest_Walker_Coat_LOD0` |

The two controls are resources that *are* their own container, which is the common case and
exactly why the distinction was easy to miss. `PLAYER_SkelAddons` is not: **it is a
`BuildTable` resource inside the `TEAMMATE_Template.data` container.**

The list holds **1,053,342 resources across 413,452 containers and 27 forges** — about 2.5
resources per container, so this is not a rare shape.

### VERIFIED in bytes

Searching the decompressed container for the exact 30-byte record
`int32 len(17) | "PLAYER_SkelAddons" | 0x00 | u64 1898138514560`:

| copy | payload our slicer yields | exact record |
| --- | --- | --- |
| base `DataPC.forge\28398_-_TEAMMATE_Template.data` | 236,119 B | **0** |
| patch `DataPC_patch_01.forge\23_-_TEAMMATE_Template.data` | 8,342,705 B | **1**, at offset 94,195 |

The little-endian ID `80 34 df f1 b9 01 00 00` follows the name directly, so the record is
name-then-ClassID — the same shape as the `EntityBuilder` skeleton records from 2026-08-14.

> **Inferred, NOT verified:** that the base copy lacks it. Our slicer is demonstrably wrong on
> this container (below), so 236,119 B is not a trustworthy reading of what the base holds.
> What is verified is that the record **is** in the patch copy — which is the live one anyway.

### ⚠️ Our own container slicer mis-parses `TEAMMATE_Template.data`

`data_inspect.py` reports this container as **2** typed resources: an `EntityBuilder`, and a
second whose name field decodes as binary garbage and whose "type id" differs between the two
copies (`#3971900160` base, `#444870144` patch) at 173,858 B and 8,340,098 B. Those are not
two readings of the same thing; the segmentation is lost after the first resource.

For scale on what is being missed: the `BuildTable` type id **585940579 appears 34,636 times**
in the patch payload. This container is a large bundle of build tables — the player/teammate
customization set — and we currently see one resource of it.

**This is now the blocker.** `PLAYER_SkelAddons` is located, but it cannot be cleanly *read* —
let alone exported to XML through `export_xml()` — until the container layer can address a
resource inside a multi-resource container by name or ID. That is a `data_inspect.py` fix, in
our own code, not an ATK gate.

---

## Entry — 2026-09-10 — `atk_bridge.py` finds ATK instead of hardcoding it; and the `D:`/`H:` split was never drift

Two machines, not one, and the KB had been treating the difference as rot.

### VERIFIED — the drive letters are per-machine, and both sets of docs are right

Confirmed by Sylvia: this project is worked from **two** computers.

| Machine | Layout |
| --- | --- |
| **SylG5** | everything under `D:` — GRB install, ATK, this repo |
| **SylDesk** | repo + GRB on `H:`, ATK on `E:`, Blender on `G:` |

So [`next-session.md`](next-session.md)'s 2026-08-31 banner (*"everything is on `D:` now"*) is
**correct for SylG5**, and the older research-log entries naming `H:` are **correct for
SylDesk**. Neither is stale. What they lack is a machine name — a future session should add
one rather than "fixing" the drive letters, which would just break them for the other machine.

> **This corrects a claim made earlier today**, before Sylvia clarified: that the D: paths were
> drift to be cleaned up. They are not.

### VERIFIED — but the tooling *was* genuinely broken on one machine

`atk_bridge.py` hardcoded `D:` in two places — `ATK_DIR` (via `GRB_ATK`, defaulted to
`D:\Anvil Toolkit`) and `DEFAULT_SEARCH` (two `D:` forge `Extracted\` paths). On SylDesk that
is not a wrong default, it is a **non-functional tool**: every entry point starts with
`start()`, which resolved a path that does not exist. Everything the 2026-09-01 → 09-09
sessions built on top of it — `export_gltf`, `import_gltf`, `export_xml`, `rebind_check`'s ATK
half — was therefore SylG5-only, silently.

`tools/blender/grbblend.py` already had this right: it *searches* for Blender across every
drive rather than naming one. The fix ports that approach.

### Fixed — the bridge searches, the way the Blender bridge already did

- **`candidate_atk_dirs()` / `find_atk(explicit=None)`.** `$GRB_ATK` → cache → search: every
  drive root plus `Program Files`, `Program Files (x86)`, `Games`, `Modding`, `Tools`, and
  `~/Desktop`, `~/Downloads`, `~/Documents`, for any folder whose name contains *anvil* and
  which holds `AnvilToolkit.dll`. The **directory** is the unit, not the exe — `Libs\` (gate 1)
  and `Lists\` (gate 7) resolve relative to it. Resolved once and cached in `_state`.
- **`candidate_grb_installs()` / `default_search_dirs()`.** Finds the game by `GRB.exe` across
  the Steam/Ubisoft layouts, then offers each install's `Extracted\DataPC.forge` and
  `…\DataPC_Resources.forge` to `find_skeletons_for`. Checking for `GRB.exe` — not for the
  directory — is what makes it correct: this machine has an empty
  `F:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint\` stub holding one orphaned DLL, and
  the search rejects it.
- **`--atk <dir>`** on the CLI, which seeds the same cache, so every downstream call sees it.
- A failure now names **everywhere it looked**. That is deliberate: a 2026-07-09 session
  searched three directories, concluded ATK *"was not found on disk"*, and wrote that into this
  log as a blocker on the staged in-game cloth test, where it sat for a month.

### Measured on SylDesk

| | |
| --- | --- |
| ATK found | `E:\Anvil Toolkit` (the only candidate) |
| GRB found | `H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint` (F: stub correctly rejected) |
| search cost | **0.01 s** for both searches |
| `atk_bridge.py <coat>.data` | runs — 1816 verts / 3263 faces, stride 36, format `…_Tex2s_Joint4_Col4ub`, influences `{1: 490, 2: 53, 3: 238, 4: 1035}` |

Those numbers are **identical to the ones recorded on SylG5** on 2026-09-01 and 2026-09-08, so
this is the first confirmation that the ATK bridge reproduces across machines rather than
across sessions on one machine.

> **Verified, not inferred:** the bridge was run end to end on SylDesk against the real install.
> Still read-only — nothing was written, and the write-back remains untested in game.

### Tooling

[`tools/atk_bridge.py`](../tools/atk_bridge.py): `_drive_roots()`, `candidate_atk_dirs()`,
`find_atk()`, `candidate_grb_installs()`, `default_search_dirs()`, the `--atk` flag, and a
`__main__` that prints an `EnvironmentError` as a message instead of a stack trace.
`ATK_DIR` and `DEFAULT_SEARCH` are gone; nothing outside the module referenced either.

---

## Entry — 2026-09-16 — Found GRB's gameplay/AI database: 50,098 records in one forge entry, and decoded what "Fear the Radio" does

**Trigger:** Sylvia asked what else could be done to NPC behaviour, given two AI mods already
installed (a forge-integrated Spartan port, and "Fear the Radio"). This knowledgebase had
**nothing** on gameplay logic — 13 docs, all about art. It does now.

### VERIFIED — the gameplay DB is one nested forge entry, and it was hiding in plain sight

`DataPC.forge / 5_-_DBContainerEntry_0X104634F921.data` (13.9 MB, decompressing to ~57 MB)
holds **50,098 named records**: 23,617 `DB*`-named across **1,008 types** over 825 type ids,
plus 26,481 others (`TGT_*_Marks*` spawn descriptors, 198 `WaveSetting_Hunt_*`, 225
`*_SpawnEntityDescriptor`, quest/dialogue). `DataPC_patch_01.forge` carries the same entry —
that is the override target, and it is where the installed AI mods write.

It stayed invisible because `data_inspect.py` correctly reports **one** typed resource here and
stops: the records are nested one level deeper, in their own stream, framed as

```
[uint32 typeId][int32 payloadLen][int32 nameLen][name bytes][0x00][payload]
```

The `0x00` after the name is **not counted by `nameLen`**. Without it the walk desyncs on record
0; with it, it consumes all 50,098 records and lands exactly on the end of the block. Record 0
is the container's own header.

`typeId` is the schema, the name is the instance. **76 type ids are shared by more than one name
prefix** (`DBSimpleFightingBehaviour` / `DBDefensiveStrafeBehaviour` both `0x131086dd`), so the
id gives layout and the name gives meaning.

### VERIFIED — ATK has no schema for any of it

`AnvilToolkit.dll` exposes 1,245 types; **zero** are `DB*`. Of the 350 classes declaring
`WriteXml()`, none is a DB record. So the BuildTable XML round-trip
(`reference/buildtable-xml.md`) **does not extend to gameplay records** — ATK unpacks and
repacks the container fine, but the bodies are opaque to it. AI modding here is binary patching.

### VERIFIED — why that is still tractable

**775 of the 1,008 DB types have a single fixed record size**, so instances of one type are
field-aligned and diff cleanly. And Ubisoft ships **null variants** (`_NoCall`, `_NoDetection`,
`_NoConfidence`, `_NoGrenade`, `_NoRevive`, `_NoChase`, ...) — diffing a live config against its
own "off" twin exposes the whole tunable surface.

`DBSoldierSoundDetectionConfig_Default` vs `_NoDetection` (303 B each, 125 differing bytes,
49 float-plausible fields) comes out as clean human-scale numbers in **runs of seven**:
50/135/150, then 10 x8, 25 x7, 100 x7, then 10/15/15/15/15/25/50/150/75/25.
*Inferred:* hearing radii in metres, banded by alert state or sound class. The shape is
verified; the meaning of the seven is not.

### VERIFIED — what "Fear the Radio" actually is (byte-level)

The installed mod ships 5 records. Vanilla has three radio configs: `_NoCall` (20 B), `_CallPMC`
(54 B, **one** call entry, floats 20/180), `_CallBodark` (224 B, **six** entries). The mod's
`CallPMC` is 225 B — strip ATK's leading byte and it is 224 B, differing from vanilla
`CallBodark` in **31 of 224 bytes**: one byte keeping CallPMC's own ClassID, plus **six** 64-bit
handles, one per wave, all repointed. *(Corrected before publication — see the last entry of
the day: a first draft said five handles, aimed at the `TGT_*_Marks*` descriptors the mod
ships. Both were wrong.)*

So the mod is **vanilla Bodark's escalation schedule transplanted onto the regular army**, aimed
at harder spawners. Its float pairs are (15,45) (10,55) x4 (20,45) against vanilla's single
(20,180). *Inferred:* delay and cooldown in seconds. The counts and values are verified; the
units are not.

That generalises into a technique worth naming: **find a record that already does what you want
on somebody else, copy its body, preserve the target's ClassID, repoint the handles.** It is the
gameplay-layer twin of the community's "move a mod to another slot" XML copy-paste — done in hex
because ATK gives no XML here.

### VERIFIED — two negative results that save wasted effort

- **NPC tier scaling is NOT in `DBNpcHealth`.** `_Rifleman_MK1` vs `_Rifleman_MK3` differ by
  **2 bytes**, both inside the ClassID. The MK1/2/3 health records are otherwise identical.
  Tier is resolved elsewhere — the `TGT_*_Marks1/2/3` spawn descriptors are the obvious
  candidate, and Fear the Radio ships edits to exactly those, but that is unverified.
- **Some named variants are byte-identical.** `DBSoldierVisualDetectionConfig_Wolves` vs
  `_Vantage` differ by **5 bytes**, all ClassID — the Wolves and the snipers share one sight
  config. Where that type does differ for real (`_Fighter` vs `_Wolves`, 33 bytes) the
  differences are **handles, not floats**: it is a bundle of references, so you retarget it
  rather than tune it. `DBSoldierSoundDetectionConfig` is the opposite — raw numbers. Check
  which kind a record is before planning an edit.

### Corrected

`examples/mod-catalog.md` listed **`UE Update`** as an *"engine/update package containing forge
data"*. It is **"UE 2.0" = Unlock Everything** — 235 `DBUnlockableGroup` records. Fixed, and the
gameplay/AI mods (`FearTheRadio`, `4HealthBarsAllClasses` -> `DBPlayerHealth`,
`behemoth_42kcredits` -> `DBLootableCurrency`) are now their own catalogue section instead of
being filed under "UI / quality-of-life".

No mod folder named for **Spartan** exists in this install's `Extracted/GRBMods/`; whatever the
forge-integrated Spartan port was installed as, it is under another name. Unresolved.

### UNTESTED — the write path

Everything above is **read-only**: nothing was repacked and nothing was launched. The write path
is inferred from the shape of the installed mods. The first in-game test should be a single-field
change to one fixed-size record so a failure is unambiguous. Repack rules are unchanged: inner
`DBContainerEntry` first, then `DataPC_patch_01.forge`; keep edited `.data` compressed.

### Open

- Where MK1/2/3 tier scaling actually lives (`TGT_*_Marks*` is the lead).
- What the seven bands in `DBSoldierSoundDetectionConfig` are.
- What `DBAICheatConfig` grants — 44 records x 162 B, one named **`_Miter_Omniscience`**.
  Diffing that against a mundane instance is the obvious next move.
- **Is the patch `DBContainerEntry` a full copy or a delta?** Fear the Radio puts 5 records in
  it. If the patch container must carry all 50,098, then two AI mods that both touch it will
  clobber each other — which would explain a good deal of community conflict reports. This one
  matters most: it decides whether AI mods can stack at all.

### Tooling

New: [`tools/db_inspect.py`](../tools/db_inspect.py) — walks the nested record stream (reusing
`data_inspect.read_cfd`, so the container format and the Oodle search stay in one place),
summarises types, extracts records by regex to a directory, and `--diff`s two same-size records
into an offset map. Read-only on the game; only ever writes the `--out` directory named.
New docs: [`docs/14-ai-and-npc-behaviour.md`](../docs/14-ai-and-npc-behaviour.md) and the
217-type catalogue [`reference/ai-db-records.md`](../reference/ai-db-records.md) (2,674
instances), generated by that tool.

---

## Entry — 2026-09-16 — The patch DBContainer is a FULL COPY; DB mods still stack; ATK's repack silently drops Oodle compression

**Trigger:** the open question left by this morning's entry — whether the patch
`DBContainerEntry` carries the whole database or only overrides. It decides whether two AI mods
can coexist. Answered, plus two findings that were not being looked for.

### VERIFIED — full copy, not a delta, and that is Ubisoft's own shape

| Container | Records | Entry size | Blocks |
| --- | ---: | ---: | --- |
| base `DataPC.forge` | 50,098 | 13,908,748 B | all Oodle-compressed (0.24) |
| **pristine** `DataPC_patch_01.forge` (`Backups/`, Sept 2023, pre-modding) | **50,121** | 13,911,655 B | all Oodle-compressed (0.27) |
| **live modded** `DataPC_patch_01.forge` | **50,434** | 57,688,741 B | **all raw** (1.00) |

Record-by-record, the live patch container reproduces **49,265 of the base's records
byte-for-byte**, changes 160, adds 597, drops 264. The untouched 2023 Ubisoft container is the
same shape. There is **no record-level override mechanism** — the whole entry wins by ID like
any forge entry.

The pristine copy matters: it rules out "a mod inflated it into a full copy". Ubisoft ships it
this way.

### VERIFIED — mods nevertheless stack, and the real conflict risk is a different one

Both installed DB mods are live in that single container at once:

- `DBAIRadioCallConfig_CallPMC` is **224 B** in the patch (vanilla 54 B) -> Fear the Radio.
- `DBUnlockEverything (1..235)` records present -> UE 2.0.

They coexist because each ATK repack rewrites the container **from its current on-disk state**,
so records dropped into an already-modded container accumulate. Same model as the rest of GRB
modding.

So the risk is not "two AI mods clobber each other". It is: **a mod that ships a pre-built whole
`DBContainerEntry_0X104634F921.data` instead of a folder of individual records replaces the
entire database and silently wipes every other DB mod.** Both mods examined ship individual
records. That is the pattern to insist on, and the thing to check before installing a third.

### VERIFIED — ATK's repack drops the container from compressed to raw

Pristine: 27 meta + 1,734 file blocks, all Oodle-Mermaid. Live: the same block counts, every
one with `uncompressed == compressed`. The entry inflated 4.1x (13.9 MB -> 57.7 MB) and
`DataPC_patch_01.forge` went 831 MB -> 1.63 GB. Nothing but ATK touched it.

### This NARROWS the 2026-07-02 compression rule

That entry concluded a `.data` with **raw/uncompressed** blocks makes GRB crash/hang at load,
and `reference/mod-anatomy.md` §5 repeats it as a general rule. It was established on **cloth**.
A 57.7 MB fully-raw DB container is sitting in an install that is played with these mods, so the
rule is **not universal** — it holds for cloth and does not hold here.

> *Verified:* the block flags and sizes, read out of the live forge index and the 2023 backup.
> *Resting on the modder's report, not on a launch I observed:* that this install runs.
> Where the boundary actually lies is unestablished and should not be guessed at. `mod-anatomy.md`
> §5 and `docs/14` §8 now both carry the narrowing rather than the blanket claim.

### Method note

The 2023 `Backups/DataPC_patch_01.forge` was the load-bearing artifact — without a pristine
copy, "full copy" and "a mod inflated it" are indistinguishable. Worth remembering that this
install keeps ATK backups going back to first use.

### Tooling

`tools/db_inspect.py` gained `--oodle DLL`: the auto-search walks up from the `.data`'s own
path, which fails the moment you extract an entry out of the forge to somewhere neutral —
exactly what reading the pristine backup required.

---

## Entry — 2026-09-16 — `DBAICheatConfig` field-mapped: omniscience is a profile, not a flag

**Trigger:** the open question from this morning — *"what does `DBAICheatConfig` actually grant,
and is 'enemies always know where you are' one byte?"* Answer: **no, it is a coordinated
profile** — six flags set, five cleared, three numbers raised.

### VERIFIED — the shape

44 records, all exactly **162 B**, so field-aligned, and the game ships a null variant
(`_NoCheat`). Across all 44 only **46 of 162 bytes ever vary**, and ignoring the 8-byte ClassID
the 44 collapse to **22 distinct profiles**. **18 share one identical body** — `_NoCheat`,
`_SC_TGT_Grenadier`, `_BlackGate`, the Goliath/Ogre arms, the autonomous turrets and mortar,
`_Suicide`, the Cherubims. That is the honest default.

Two flag groups move in **opposite directions** between `_NoCheat` and `_Miter_Omniscience`:

| | 13 | 18 | 19 | 35 | 36 | 37 | 51–55 | @14 | @20 | @28 |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | ---: | ---: | ---: |
| `_NoCheat` (+17) | 0 | 0 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 2 | 0 | 100 |
| `_Walker` | 1 | 0 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 2 | 0 | 75 |
| `_Teammate` | 1 | 0 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 2 | 0 | 100 |
| `_DC_TGT_Dragonfly_Ambush` | 1 | 1 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 5 | 30 | 800 |
| `_FactionWarfare` | 1 | 0 | 0 | 0 | 0 | 0 | `1 0 0 0 0` | 2 | 0 | 100 |
| `_Miter_Omniscience` | 1 | 1 | 1 | 1 | 1 | 1 | `0 0 0 0 0` | 10 | 22 | 250 |

Invariant in all 44: bytes 8–12 (typeId echo + a constant) and **38–49** — the handle marker
plus a 64-bit handle, i.e. every cheat config references the same target.

### Inferred, but strongly patterned

Group A (13/18/19/35/36/37) reads as **cheat grants**, off by default; group B (51–55) as
**honesty gates** that omniscience clears. Byte 13 looks like a master "this unit cheats at all"
switch — set on the Omniscience family, the scripted boss `_Walker`, the Behemoths, **and on
`_Teammate`**, which fits: your AI squad has to spot things for you.

`@28` behaves like a **distance in metres** and scales the way a cheat radius would: `_Walker`
75, Goliath 80, turrets 120, `_RAID_BlackGates` 200, omniscient Miter 250, ambushing Dragonfly
800, and **0** for plain `_DC_TGT_Ogre_base` / `_Dragonfly_base`. None of the floats' units are
verified.

### Two claims corrected during the pass

A first draft of the layout table asserted bytes 59–161 are zero in every record and that
38–50 is invariant. Both were wrong and are fixed in `docs/14` §9: **59–161 is zero in 40 of 44**
— `_Children`, `_LE2_Low_Stim`, `_FactionWarfare` and `_Suicide` use a sparse further flag bank
out there (62, 63, 73, 78, 81, 83, 88, 108, 115, 123, 129, 143, 148, 160, 161) — and the
invariant handle region is **38–49**, not 38–50, because byte 50 is a group-B flag that
`_FactionWarfare` clears. There is also a fourth float at offset **24**, used by exactly one
record (`_Miter_Omniscient_InFight` = 10).

### Practical

Granting omniscience is a **one-record transplant**: copy `_Miter_Omniscience`'s 154-byte body
onto a target cheat config, keeping the target's own 8-byte ClassID — the §5 technique. The
reverse (paste `_NoCheat` over `_Walker` or a Behemoth) strips a scripted boss's advantage.

**Still missing:** `DBAICheatConfig` has no `_Wolves` or `_Rifleman` instance, so which config a
regular soldier uses is decided by a handle in `DBNpcGeneralConfig` (61 records x 38 B).
Resolving it is what stands between this and "make the Wolves omniscient" — and as the next entry
shows, handles resolve by a plain ClassID lookup, so that is a lookup nobody has run yet rather
than an open research problem.

---

## Entry — 2026-09-16 — Handles resolve by ClassID lookup; Fear the Radio's real targets (a correction)

**Caught before publication.** Earlier entries today said Fear the Radio repointed *five* handles
at the `TGT_*_Marks*` descriptors it ships. That was an unchecked inference. Six distinct handles
cannot map onto four records, and none matched their ClassIDs.

### VERIFIED — how to resolve a handle

A 64-bit handle inside a record is the **ClassID of its target**, and every record's payload
begins with its own ClassID. Index `payload[0:8]` across base + patch (50,436 ClassIDs) and every
handle becomes a name. All 13 radio-call handles resolved to exactly one record each.

### VERIFIED — what the radio configs actually summon

Wave entry: `f8 00 00 00 00` marker, 4 constant bytes, int32 count, two floats, `01 00`, then the
handle at marker + 23. Vanilla `CallPMC`: one wave -> `WaveSetting_TGT_CallerBackup`. Vanilla
`CallBodark`: six waves -> `WaveSetting_TGT_CallerBodark_Wave1..6`.

Fear the Radio keeps Bodark's timings and counts **exactly** and repoints all six waves at:
`WaveSpawner_TGT_Y1E3MM08_Ambush_FatBoy`, `PvEE_WaveSpawner_Basic`,
`WaveSetting_Hunt_TGT_GQ250_AmbushMaoriFort`, `WaveSetting_Hunt_TGT_OnFootBackup_MQ190_3HNTR-RFLM`,
`PvEE_WaveSpawner_Warfare_Wolf`, `WaveSpawner_WildHunt_VHC`. Bodark's schedule, aimed at the
nastiest spawners the game already has. The shipped `TGT_*_Marks*` descriptors are a separate,
still-unlinked edit.

Corrected in place: `docs/14` §4/§5/§7/§9, `examples/mod-catalog.md`, and this day's earlier
entries. Consequence: the `DBNpcGeneralConfig` -> cheat-config mapping is a lookup nobody has run
yet, not an open research problem.
