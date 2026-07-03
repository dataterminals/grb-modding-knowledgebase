# Sources

Where the facts in this knowledgebase come from, so claims can be re-checked and the next researcher knows what's authoritative.

## Primary sources (on the research machine, 2026-06-30)

| Source | What it gave us | Reliability |
| --- | --- | --- |
| **ATK `README.txt`** (in `AnvilToolkit_Release_v1.3.1`) | Full changelog 1.0.0→1.3.1; explicit GRB feature support; the unpack→edit→repack workflow; format/codec mentions; GRB-specific behaviors (uncompressed serialization, compression toggle, etc.). | **High** — the tool authors' own words. The backbone of [`docs/04-anvil-toolkit.md`](../docs/04-anvil-toolkit.md). |
| **ATK `AnvilToolkit.dll.config`** | Default settings (compression, backups, ignored extensions, swizzle, mips, gamma, IDs). | High — shipped defaults. |
| **ATK `Libs/` listing** | Dependency/codec stack → ATK's real capabilities (Oodle, LZMA/LZ4/Zstd/LZO, DirectXTex, SharpGLTF, HelixToolkit, LibGit2Sharp). | High. |
| **GRB install directory listing** | The forge inventory, sizes, base/patch pairing, non-forge blobs, backup folders, presence of Oodle DLL. | High — direct observation. [`reference/forge-inventory.md`](../reference/forge-inventory.md). |
| **Hex dumps** of `DataPC_patch_01.forge` and a `.BuildTable` | Forge magic/version; BuildTable structure (64-bit references). | High for the bytes shown; interpretation beyond the header is flagged inferred. |
| **Mod folders** (`Sheva_resources`, `Sheva_buildtables`, `USP Tactical + Burris FF3`, + 150-folder `GRBMods` corpus) | The three-forge model, layer split, naming conventions, `77777`, LOD/Mip/variant patterns. | High for the observed mods; generalizations flagged. [`examples/`](../examples/). |
| **Decompiled `AnvilToolkit.dll`** (v1.3.1, via `ilspycmd`) | The **exact** forge format (`ForgeFile`/`ForgeEntry`), the `.cloth`/MotionCloth format (`MotionCloth.*`), cloth tunables, the `Game` enum / version-27 family. | **Highest** — it is the reference implementation's actual source. Backbone of [`docs/11`](../docs/11-cloth-and-physics.md) and the verified parts of [`docs/02`](../docs/02-forge-file-format.md). |

## Secondary / community sources (referenced, not yet independently verified here)

| Source | Notes |
| --- | --- |
| **Anvil Toolkit Discord** — `https://discord.gg/vsuGFEapdq` | Tool support, updates, and format discussion (from ATK README). |
| **Tier 1 Imports** community | The primary active GRB modding space; much tribal knowledge lives here. Confirm naming/workflow claims against it. |
| **Nexus Mods** | Distribution platform; mod folder naming (`<name>-<id>-<ver>-<timestamp>`) originates here. |
| General **Anvil/Scimitar forge** reverse-engineering (QuickBMS scripts, AC modding wikis, "Gibbed"-style tools) | The broader community has documented older Anvil forges; useful for cross-checking the binary layout. Not yet cited specifically — a TODO to gather concrete references. |

## How to reproduce the decompilation
ATK is a .NET assembly. With the .NET SDK installed: `dotnet tool install -g ilspycmd`, then `ilspycmd -p -o <outdir> AnvilToolkit.dll` dumps a full C# project; or `ilspycmd -t <FullTypeName> AnvilToolkit.dll` for one class. (Note: ilspycmd's project output is UTF-8; PowerShell `>` redirection writes UTF-16 — read accordingly.) The `Read`/`Write`/`Serialize`/`Deserialize` methods are the format.

## In-game testing (now a source, as of 2026-07-02)
Empirical in-game testing on a real modded GRB install is **now a load-bearing source** (it was a gap on 2026-06-30). It established, among other things, that a **raw/uncompressed cloth `.data` crashes/hangs GRB at load** while an Oodle-Mermaid-compressed one loads, and that the per-cloth **`ClothProperties` gravity field (section 4357) is ignored at GRB runtime** (with the dedicated `ClothPropertiesGravity` section 4398 as the untested live-candidate). These results are recorded in [`meta/research-log.md`](research-log.md) (2026-07-02 entries) and drive [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md). **Reliability:** direct observation on one researcher's machine — high for what was seen, but single-install.

## What is NOT yet a source (gaps)
- **Engine-level documentation** of GRB's forge mount/load order — none consulted; the load model in [`docs/06-game-load-and-reassembly.md`](../docs/06-game-load-and-reassembly.md) is inferred (though the flat-ID-archive basis is now verified from ATK). In particular, the **priority order when the same ID sits in two *peer* forges** (mod vs mod, or mod vs official patch) is still untested in-game.
- **XML-tuned cloth is not a GRB workflow.** ATK cannot XML-export GRB cloth at all (`SoftBody.SupportedGames` gate), so there is no "XML-tune the cloth" path to test for GRB — cloth edits go through raw-section tools + a compressed `.data` repack. (This corrects an earlier gap-note that listed "XML-tuned cloth" as a pending test.)

## Citation style used in the docs
- `> **Verified:**` — observed directly this session (with the artifact noted).
- `> **Inferred:**` — deduced from patterns/structure/general knowledge; treat as hypothesis.
- ATK changelog facts are attributed inline (e.g. "changelog 1.2.9").
