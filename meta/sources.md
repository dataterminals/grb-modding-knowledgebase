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

## What is NOT yet a source (gaps)
- **Engine-level documentation** of GRB's forge mount/load order — none consulted; the load model in [`docs/06-game-load-and-reassembly.md`](../docs/06-game-load-and-reassembly.md) is inferred (though the flat-ID-archive basis is now verified from ATK).
- **Empirical in-game tests** of conflict/override behavior and XML-tuned cloth — none run yet.
- **`DataFile` / file-type registry** (the per-`.data` compression descriptor and `Extension`-id→type map) — identified but not yet read.

## Citation style used in the docs
- `> **Verified:**` — observed directly this session (with the artifact noted).
- `> **Inferred:**` — deduced from patterns/structure/general knowledge; treat as hypothesis.
- ATK changelog facts are attributed inline (e.g. "changelog 1.2.9").
