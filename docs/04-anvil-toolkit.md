# 04 — The Anvil Toolkit (ATK)

**ATK is the single most important tool in the GRB modding pipeline.** It is the community's reverse-engineered reader/writer for the Anvil/Scimitar `.forge` and `.data` formats, wrapped in a GUI that behaves like a file explorer purpose-built for game archives. Almost every mod in the wild was made with it.

> **Reference version for this doc:** `AnvilToolkit_Release_v1.3.1` (distributed as a zip; the studied copy is `AnvilToolkit_Release_v1.3.1-16-1-3-1-1753733025.zip`). Facts here come from ATK's bundled `README.txt`, its `AnvilToolkit.dll.config`, and its `Libs/` dependency set.

## What it is, technically

ATK is a **Windows desktop application** built on **.NET 9** (WPF GUI). It ships as a folder you run in place — there is no installer:

```
AnvilToolkit.exe                 launcher (~248 KB)
AnvilToolkit.dll                 the application (~16 MB — all the real logic)
AnvilToolkit.deps.json           .NET dependency manifest
AnvilToolkit.dll.config          default settings (userSettings)
AnvilToolkit.runtimeconfig.json  .NET runtime config
Libs/                            native + managed dependencies
README.txt                       documentation + full changelog
```

It creates `Settings.xml` and `Games.gsd` at runtime (and regenerates them if corrupted). Those hold your per-game paths and preferences, so they're not in the distributed zip.

### The dependency stack (what it tells us)

The `Libs/` folder is a precise map of ATK's capabilities:

| Dependency | Capability it provides |
| --- | --- |
| `Oodle` handling (game's `oo2core_7_win64.dll`) | Decompress/compress forge data |
| `EasyCompressor`, `fast-lzma2`, `K4os.Compression.LZ4`, `libzstd`, `lzo`, `SevenZip` | The full Anvil codec stack (LZMA, LZ4, Zstd, LZO, 7-zip) |
| `DirectXTexNet` / `DirectXTexNetImpl`, `DDSUnswizzle` | DDS texture read/write, format conversion, console **un-swizzling** |
| `SharpGLTF.Core` / `SharpGLTF.Toolkit` | **glTF/GLB import & export** — the Blender bridge |
| `HelixToolkit` / `HelixToolkit.Wpf.SharpDX`, `SharpDX.*` | The in-app **3D Mesh Viewer** (DirectX-rendered) |
| `Newtonsoft.Json` | JSON / settings / hash data |
| `LibGit2Sharp` + `git2-*.dll` | Git integration (versioning support) |
| `discord-rpc` | Discord Rich Presence ("Developing mods") |
| `Cyotek.Drawing.BitmapFont`, `Microsoft.Xaml.Behaviors` | UI |

The takeaway for an AI assistant: **ATK already contains correct, battle-tested code for every hard part of the format** (compression, DDS, vertex formats, hashes). It is the ground truth — prefer matching its behavior over re-deriving formats from scratch.

## The file-explorer model

The defining design idea of ATK is the **Game Explorer**: it presents an unpacked (or unpackable) forge as a **navigable folder tree**, exactly like Windows Explorer, but understanding game resources. From its README and changelog, the Game Explorer supports:

- Double-click a `.forge`/`.data` to **unpack**; right-click for **unpack/repack/export/replace** actions; an action panel on the right mirrors the context menu.
- **Cut / Copy / Paste / Delete / Rename** (F2) of entries, **create new folders**, **drag-and-drop** to move (hold Ctrl to copy) or to **replace a texture/mesh** by dropping a file onto it.
- **Backspace** = up a folder; **F5** = refresh.
- Wildcard search with history; tooltips; automatic scaling to screen size; resizable window.
- A **console/log** pane (timestamped) for operation feedback.

So when a modder says "open the file in ATK and replace it," they mean: navigate the forge as a folder tree, find the resource by name/ID, and use replace/import.

## Core capabilities relevant to GRB

### Unpack / repack
The fundamental loop. Unpack a forge to a working folder, change resources, repack to a new forge. Notes specific to GRB:
- ATK won't unpack if the destination unpacked folder already exists (avoids clobbering work).
- GRB data files: uncompressed-by-default historically; compression is now a setting (`EnableCompression = True` by default in the shipped config). See [`07-modding-workflow.md`](07-modding-workflow.md).
- Background-threaded and multithreaded unpacking for speed.

### Texture Viewer
Double-click a texture (TextureMap) to open it. You can **export** to DDS / PNG / TGA / JPG and **replace** with a new image (any image format accepted; **DDS recommended** for full control). Supports gamma settings (auto-updated on import), mip generation on import, cube maps, and a drop-preview UI. GRB TextureMap and TextureSet support are explicitly listed.

### Mesh Viewer
A real-time 3D viewer (HelixToolkit/SharpDX). Load Mesh, Skeleton, Cloth/SoftBody resources; inspect bones; **export to glTF/GLB and import edited meshes back**. Rich GRB-specific handling: all GRB vertex formats, skinned meshes, up to 5 UV sets, vertex colors (with Blender-friendly naming), tangent/binormal recalculation on glTF import, automatic rescale, bone-limit checks. It can also generate **BuildTables** directly from a scene/mesh/skeleton.

### XML export/import (schema-based)
Many resource types export to **XML** for editing and recompile back. For GRB specifically the changelog lists: **BuildTables, EntityBuilder, Materials, TextureSet, LocalizationPackage, PrefetchingFileInfos**, and (as of 1.3.0) a **schema-based exporter** for AC1–Syndicate that can be forced with Shift+double-click / Shift+context-menu.

### Hash Converter utility
Converts between names and hashes / file IDs (including generating a "64-bit File ID"). Because GRB references everything by ID/hash, this utility is how you find or mint the right identifiers.

## Settings worth knowing (from the shipped config)

The default `AnvilToolkit.dll.config` reveals behaviors a modder/AI should expect:

| Setting | Default | Why it matters |
| --- | --- | --- |
| `EnableCompression` | `True` | Repacked data may be compressed; relevant to GRB compatibility. |
| `CreateBackups` / `CreateDataBackups` / `CreateFileBackups` | `True` | ATK auto-creates `.bak`/Backups folders — your safety net. |
| `OverwriteFileBackups` | `True` | Existing backups can be overwritten — don't rely on it for long-term archival. |
| `AddDateToBackups` | `False` | Backups overwrite rather than version by date unless you change this. |
| `IgnoredExtensions` | `dependency;bak;dds;obj;glb;xml;ignored` | Hides your working/export files from the Game Explorer. |
| `UnswizzleTextures` | `False` | PC textures aren't swizzled; this is for console formats. Per-game override exists. |
| `GenerateMipsWhenImporting` | `True` | New textures get a mip chain automatically. |
| `ForceConvert32BitIDsTo64Bit`, `ForceBigEndianReader` | `False` | Cross-game/console compatibility levers. |

ATK also auto-detects installed games from the registry and Steam library (1.3.0), so it can usually find a GRB install on its own.

## How an AI should treat ATK

- **It is authoritative for the format.** If you need the exact binary truth of a forge/mesh/texture, the answer is "what ATK does."
- **It is GUI-driven, not a CLI.** There is no documented command-line/automation interface in this version (`EnableCommands` defaults `False` and is an experimental console feature, not a public scripting API). Do not assume you can script ATK headlessly without confirming.
- **Its README changelog is a dense knowledge source** — it names supported types, fixed quirks, and GRB-specific behaviors. A condensed version of the GRB-relevant entries is captured in [`reference/resource-types.md`](../reference/resource-types.md) and [`meta/sources.md`](../meta/sources.md).
