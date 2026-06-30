# GRB Modding Knowledgebase

A human- **and** AI-readable knowledgebase for modding **Tom Clancy's Ghost Recon: Breakpoint** (GRB) — the Ubisoft *Anvil* engine, its `.forge` archives, the **Anvil Toolkit (ATK)**, and the asset-replacement pipeline the modding community uses.

> **Status:** Living research project. First established 2026-06-30. Maintained primarily through the *Tier 1 Imports* modding community. Expect rapid expansion — see [`meta/research-log.md`](meta/research-log.md) for what is **verified** vs. **inferred**, and the current open questions.

---

## Why this repo exists

GRB's official modding tools are effectively gone; the scene survives through a handful of skilled people who built **ATK** and a body of hard-won, mostly-undocumented tribal knowledge living in Discord threads. The goal here is to **capture that knowledge in a structured form** so that:

1. **Humans** new to GRB modding have a real reference instead of scattered chat logs.
2. **AI coding agents** (Claude Code and others) can load this repo as context and meaningfully *assist* with — or eventually *automate* — GRB modding tasks.

We do not have one single end goal. The near-term mission is breadth and accuracy: build a trustworthy map of *how GRB's data works and how we change it*, then expand into tooling, automation, and worked examples.

## What modding GRB actually is (the 60-second version)

GRB stores nearly all of its game data inside large **`.forge`** archive files. A `.forge` is a Ubisoft *Anvil* engine container (engine codename **"Scimitar"** — it's literally the magic string at the top of every forge). Inside a forge are many **`.data`** entries; each `.data` is itself a small container holding one or more **typed resources** — meshes, textures, materials, build tables, skeletons, and so on.

**ATK** (the Anvil Toolkit) is a Windows `.NET`/WPF application that acts as a **specialized file explorer for forges**: it unpacks a `.forge` into a browsable folder of `.data` files, lets you view/replace textures and meshes, exports resources to standard formats (**DDS**, **glTF/GLB**, **XML**), re-imports edited versions, and **repacks** everything back into a forge the game will load.

A finished asset-replacement mod is, in practice, a small set of **patch forges** (`*_patch_01.forge`) that the game loads *on top of* its base forges, overriding specific entries by ID. Most cosmetic mods touch three forges together:

| Forge | Holds |
| --- | --- |
| `DataPC_patch_01.forge` | Item / inventory definitions (`WI_…`), BuildTables, entity data |
| `DataPC_extra_patch_01.forge` | Gameplay definitions (`WG_…`) |
| `DataPC_Resources_patch_01.forge` | The heavy resources: meshes (`…_LOD0–3`) and textures (`…_Mip0–N`) |

The authoring loop is: **model/texture in Blender → export to glTF/DDS → "digest" (import) into the forge with ATK → repack → drop the patch forges into the game directory.** See [`docs/07-modding-workflow.md`](docs/07-modding-workflow.md).

## How to use this repo

### If you are a human
Start with [`docs/01-overview.md`](docs/01-overview.md), then read the docs in order. Use [`reference/glossary.md`](reference/glossary.md) when a term is unfamiliar. The [`examples/`](examples/) folder walks through real mods end-to-end.

### If you are an AI agent
Read [`CLAUDE.md`](CLAUDE.md) first — it is the orientation file written for you. It tells you the safety rules (e.g. **never touch a forge without a backup**), the mental model, and where to find authoritative facts. `AGENTS.md` points here too.

## Repo map

```
docs/        Conceptual documentation, numbered in reading order
reference/   Lookup tables: forge inventory, resource types, glossary
examples/    Worked case studies of real mods, plus the studied mod corpus
meta/        Research provenance, verification status, sources, open questions
assets/      Diagrams and supporting images
```

| Doc | Topic |
| --- | --- |
| [`docs/01-overview.md`](docs/01-overview.md) | Anvil/Scimitar engine, GRB, the modding scene |
| [`docs/02-forge-file-format.md`](docs/02-forge-file-format.md) | The `.forge` archive format (binary layout, what's verified) |
| [`docs/03-data-and-resources.md`](docs/03-data-and-resources.md) | `.data` containers, typed resources, file IDs, nesting |
| [`docs/04-anvil-toolkit.md`](docs/04-anvil-toolkit.md) | ATK deep dive: tech stack, features, the file-explorer model |
| [`docs/05-three-forge-model.md`](docs/05-three-forge-model.md) | base vs. patch forges; the three-forge mod structure |
| [`docs/06-game-load-and-reassembly.md`](docs/06-game-load-and-reassembly.md) | How GRB merges many forges into one index at load |
| [`docs/07-modding-workflow.md`](docs/07-modding-workflow.md) | End-to-end: Blender → glTF/DDS → digest → repack → install |
| [`docs/08-naming-conventions.md`](docs/08-naming-conventions.md) | Prefixes, LOD/Mip suffixes, the `77777` convention, ID formats |
| [`docs/09-textures.md`](docs/09-textures.md) | DDS, pixel formats, swizzling, mips, gamma |
| [`docs/10-meshes-and-skeletons.md`](docs/10-meshes-and-skeletons.md) | Vertex formats, LODs, the glTF pipeline, skeletons |
| [`docs/11-cloth-and-physics.md`](docs/11-cloth-and-physics.md) | The `.cloth` / MotionCloth format, reverse-engineered from ATK source — sections, tunable properties, how to mod cloth |

Lookup tables of note: [`reference/forge-inventory.md`](reference/forge-inventory.md) · [`reference/resource-types.md`](reference/resource-types.md) · [`reference/cloth-section-types.md`](reference/cloth-section-types.md) · [`reference/glossary.md`](reference/glossary.md)

## Community

- **Tier 1 Imports** — the primary active GRB modding community.
- **Anvil Toolkit Discord** — `https://discord.gg/vsuGFEapdq` (from ATK's README; tool support & updates).

## A note on accuracy

This knowledgebase is assembled by inspecting a real GRB install, the ATK distribution, and a large corpus of community mods on one researcher's machine. Wherever a claim is **observed and verified**, we say so. Wherever it is **inferred** from naming, structure, or general Anvil-engine knowledge, we flag it as such. If you can confirm or correct something, update [`meta/research-log.md`](meta/research-log.md) and the relevant doc. Treat unverified claims as hypotheses, not gospel.
