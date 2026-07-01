# Reference — Glossary

Short definitions of the terms used throughout this knowledgebase. Cross-references in **bold**.

| Term | Definition |
| --- | --- |
| **Anvil** (AnvilNext) | Ubisoft's in-house engine powering GRB and the Assassin's Creed line. Older codename **Scimitar**. |
| **Scimitar** | The engine's internal codename; the literal magic string `scimitar` at the start of every **forge**. |
| **`.forge`** | Top-level Anvil archive file. A virtual filesystem mapping 64-bit **file IDs** to compressed **data** entries. See [`docs/02-forge-file-format.md`](../docs/02-forge-file-format.md). |
| **`.data`** | One entry inside a forge — itself a container holding one or more **typed resources**. Unpacked as `<ID>_-_<Name>.data`. |
| **File ID** | A stable 64-bit handle identifying a resource — its embedded `ClassID`, mirrored in the forge index (`ForgeEntry.ID`). The *real* identity; override/reference is keyed on it. **Not** the number shown in an unpacked filename (that's a positional index / sort label — see **Leading number**). |
| **Leading number** | The `<N>` in an unpacked `<N>_-_<name>.ext`. A **positional index** (`SetIndex*5000+i` for forge entries; a counter inside a `.data`) or a modder label — used only for sort order, **not** the file ID. |
| **Typed resource** | The actual engine asset inside a `.data`: **Mesh**, **TextureMap**, **Material**, **BuildTable**, **Skeleton**, etc. |
| **ATK** / **Anvil Toolkit** | The community .NET/WPF tool that reads/writes forges and resources. The reference implementation of the format. See [`docs/04-anvil-toolkit.md`](../docs/04-anvil-toolkit.md). |
| **Game Explorer** | ATK's file-explorer-style view of a forge as a navigable folder tree. |
| **Mesh Viewer** | ATK's 3D viewer for meshes/skeletons; the glTF import/export workspace. |
| **Texture Viewer** | ATK's texture editor; DDS/PNG/TGA/JPG export and replace. |
| **BuildTable** | A data-driven "recipe" that assembles an entity/item from parts/meshes/materials by referencing other resources by ID. |
| **TextureMap** | A single texture (with mips). | 
| **TextureSet** | Named bundle mapping material slots (DiffuseMap, NormalMap…) to TextureMaps. |
| **Material** | Shader parameters + texture references. |
| **Skeleton** | Bone hierarchy for skinned meshes. |
| **LOD** (Level of Detail) | A mesh detail tier. `LOD0` = highest/closest, `LOD3` = lowest/distant. |
| **Mip / Mipmap** | A precomputed half-resolution texture level. `Mip0` = full res. |
| **Digest** | Community term for importing an authored asset (glTF/DDS) into the game's data via ATK — converting + embedding it into a forge. |
| **Repack** | Writing an unpacked working folder back into a `.forge` (or `.data`). |
| **Patch forge** | A `*_patch_01.forge` the game loads on top of base forges, overriding by ID. Mods ship these. See [`docs/05-three-forge-model.md`](../docs/05-three-forge-model.md). |
| **Base forge** | The original `DataPC_<name>.forge` shipped with the game (no `_patch` suffix). |
| **The three forges** | The trio most cosmetic mods touch: `DataPC_patch_01` (items/`WI_`), `DataPC_extra_patch_01` (gameplay/`WG_`), `DataPC_Resources_patch_01` (meshes/textures). |
| **`WI_` / `WG_`** | Inferred prefixes: **W**eapon **I**tem (inventory) / **W**eapon **G**ameplay definitions. |
| **`TP_` / `FTP_`** | Inferred prefixes: **T**hird-**P**erson model / Face-or-Female Third-Person (on heads). |
| **`HDG`** | Inferred: **H**an**d**gun weapon class (e.g. the P12 pistol). |
| **`77777`** | A modder **filename label** (not a file ID) put on new, non-replacement resources during authoring; the real IDs are the files' distinct embedded ClassIDs. See [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md). |
| **Oodle** | The primary compression codec for GRB forge resources (`oo2core_7_win64.dll`). |
| **Swizzle / Unswizzle** | Console GPU texture byte reordering. Off for PC GRB (`UnswizzleTextures = False`). |
| **GlobalMetaFile** | Forge-wide metadata sidecar (`.MetaFile`). |
| **PrefetchingFileInfos** | Streaming/prefetch hint sidecar (`.PrefetchInfo`). |
| **`.tbf` / `.wmap` / `.wmp2`** | Non-forge GRB data blobs (terrain / world map) sitting beside the forges. |
| **Tier 1 Imports** | The primary active GRB modding community. |
