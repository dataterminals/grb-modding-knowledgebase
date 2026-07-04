# CLAUDE.md — orientation for AI agents

You are an AI assistant working in the **GRB Modding Knowledgebase**. This file orients you so you can help with Ghost Recon: Breakpoint (GRB) modding accurately and safely. Read it fully before acting.

> **🎯 Read [`meta/project-goal.md`](meta/project-goal.md) FIRST.** It is the concrete modding objective (from SamiPuma) that all the cloth research serves: **put an existing in-game garment's cloth physics onto a NEW mesh** (replace a flowing coat with an outside poncho, keeping the coat's cloth physics) — a **rebind** problem, *not* parameter tuning. Then read [`meta/research-log.md`](meta/research-log.md) (latest entry = current state) and [`meta/next-session.md`](meta/next-session.md) (what to do next). As of 2026-07-03 the active leads are **(A)** rebinding `.cloth` to new geometry and **(B)** GRB's ATK-readable `.skeleton` bone-physics path.

## What this repo is

A structured knowledgebase about modding GRB via the Ubisoft *Anvil* engine, its `.forge` archives, and the **Anvil Toolkit (ATK)**. It is documentation-first. There is no build step and (currently) no code to run. Your job is usually to **read, reason, document, and guide** — not to mutate game files unless explicitly asked.

## The mental model (load this first)

- **`.forge`** = a Ubisoft Anvil archive. Magic string at byte 0 is `scimitar` (the engine's internal codename). It is essentially a virtual filesystem: an index mapping 64-bit **file IDs** to compressed data entries.
- **`.data`** = one entry inside a forge, *also* a container. It holds one or more **typed resources** (Mesh, TextureMap, Material, BuildTable, Skeleton, …). Unpacked names look like `<N>_-_<Name>.data`, where `<N>` is a **positional index, not the file ID** (the real 64-bit ID is embedded in the resource — see `docs/03-data-and-resources.md`).
- **ATK** = a `.NET`/WPF Windows app that behaves like a **file explorer for forges**: unpack → browse `.data` → view/export/replace resources → repack. It is the community's reference implementation of the forge format; when docs and ATK disagree, **ATK is authoritative.**
- A **mod** = new/replacement entries **repacked into the install's forges** (usually the `*_patch_01` set) that override base entries by ID. Modders point ATK at their real install and repack in place, so an install accumulates mods in its forges over time. Most cosmetic mods coordinate **three** forges: `DataPC_patch_01` (items), `DataPC_extra_patch_01` (gameplay), `DataPC_Resources_patch_01` (meshes + textures).
- The **authoring pipeline**: Blender → glTF/GLB (meshes) + DDS (textures) → import into the forge with ATK → repack in place in your install.

## Safety rules — non-negotiable

1. **Never modify, overwrite, or delete a `.forge` or `.data` file without a verified backup first.** Forges are huge (the resources forge is ~23 GB base + ~38 GB patch) and re-downloading is painful. ATK creates backups by default (`CreateBackups`, `CreateDataBackups`, `CreateFileBackups` all default `True`) — confirm the backup exists before any destructive step.
2. **Do not run ATK or repack forges on the user's behalf without explicit instruction.** Repacking mutates real game files.
3. **Game files live in the GRB install directory, not in this repo.** Do not copy multi-GB game assets into the repo. Document *about* them; reference paths instead.
4. **Distinguish verified from inferred.** This repo deliberately separates observed facts from hypotheses (see `meta/research-log.md`). Preserve that discipline in anything you write — do not silently promote a guess to a fact.
5. **Respect the working directory.** When invoked inside a GRB install, treat every `*.forge`, `*.tbf`, `*.wmap`, `GRB.exe`, etc. as precious original game data.

## Where to find authoritative facts

| Question | Look here |
| --- | --- |
| Forge / data binary format | `docs/02-forge-file-format.md`, `docs/03-data-and-resources.md` |
| What ATK can do, version history | `docs/04-anvil-toolkit.md` (sourced from ATK's own `README.txt`) |
| Which forge holds what | `docs/05-three-forge-model.md`, `reference/forge-inventory.md` |
| What a resource type is | `reference/resource-types.md` |
| Resource **type ids** (`Extension` = CRC32 of name) & `.data` compression | `reference/resource-type-ids.md`, `docs/02-forge-file-format.md` |
| Naming patterns (`FTP_`, `WG_`, `LOD0`, `Mip0`, `77777`) | `docs/08-naming-conventions.md` |
| **Cloth / `.cloth` / MotionCloth** (capes, coats, straps) | `docs/11-cloth-and-physics.md`, `reference/cloth-section-types.md` |
| A real worked mod | `examples/case-study-usp-tactical.md` |
| What's proven vs. guessed, open questions | `meta/research-log.md` |

**Ground truth = ATK's source.** `AnvilToolkit.dll` is a .NET assembly; decompile it (`ilspycmd -p -o <dir> AnvilToolkit.dll`, or `-t <Type>` for one class) and read the `Read`/`Write`/`Serialize`/`Deserialize` methods to resolve *any* binary-format question definitively. Much of this KB (the forge format, the entire cloth format) was derived this way. The community's active focus is **cloth** — prioritize accuracy there.

## House style for edits

- Keep the **verified / inferred** distinction explicit. Use callouts like `> **Verified:**` and `> **Inferred:**` where it matters.
- Cite *how* you know something (hex dump, ATK README, file listing, community report).
- Prefer relative links between docs so navigation works on GitHub and locally.
- When you learn something new, also append it to `meta/research-log.md` so provenance is never lost.
- This repo is public and may be read by other modders and their AIs. Write for a stranger picking it up cold on another machine.
