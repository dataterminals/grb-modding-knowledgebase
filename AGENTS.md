# AGENTS.md

This repository's primary agent-orientation file is [`CLAUDE.md`](CLAUDE.md). It applies to **any** AI coding agent, not just Claude — read it first.

Quick summary of the non-negotiables (full detail in `CLAUDE.md`):

- This is a **documentation-first knowledgebase** for Ghost Recon: Breakpoint modding. Default to reading, reasoning, and writing docs — not mutating game files.
- **Never modify a `.forge` or `.data` file without a verified backup.** Forges are multi-gigabyte original game data.
- **ATK (the Anvil Toolkit) is the authoritative reference implementation** of the forge format. When this repo and ATK disagree, ATK wins — and the doc should be corrected.
- Keep the **verified vs. inferred** distinction explicit in everything you write, and log new findings in [`meta/research-log.md`](meta/research-log.md).
