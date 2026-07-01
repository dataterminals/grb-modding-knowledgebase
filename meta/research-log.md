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
Confirm the vertex-order/drop-max convention against the render `Mesh` (parse `TP_Tacvest_Walker_Coat_LOD*.Mesh` vertex count + positions; expect 232/180), then build the mapping→section encoder in `motioncloth.py` and validate in-game on the Walker coat.

---

> **Template for future entries:**
> ```
> ## Entry — YYYY-MM-DD — <topic>
> ### What I did
> ### VERIFIED (new)
> ### INFERRED (new)
> ### Questions answered / opened
> ```
