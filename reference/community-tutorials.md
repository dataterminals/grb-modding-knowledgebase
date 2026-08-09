# Reference — Community tutorial index

The *Tier 1 Imports* `#mod-tutorials` forum is the closest thing GRB modding has to primary documentation. This file is the **map from those threads to the pages in this KB that absorbed them**, so knowledge is traceable back to its source and we can tell at a glance what has and hasn't been captured yet.

> **Why this exists:** the KB's rule is that provenance is never lost ([`../meta/research-log.md`](../meta/research-log.md)). Discord threads move, get edited, and are invisible to search engines. When a thread is absorbed here, it gets a row below with its message ID so anyone can go back to the original.

**Server:** *Tier 1 Imports*, guild `1302392670181916722` · **Forum:** `#mod-tutorials`, channel `1302692674863763586`
For a forum post, the **thread ID equals its opening message ID** — the link form is `discord.com/channels/<guild>/<threadId>/<messageId>`.

## Absorbed

| Thread | Author | Date | Captured in |
| --- | --- | --- | --- |
| [Super short and simple way to move mods to another slot](https://discord.com/channels/1302392670181916722/1414435798090256437/1414435798090256437) | SAMIEVILPUMA | 2025-09-08 | [`buildtable-xml.md`](buildtable-xml.md) — BuildTable XML anatomy + the slot-move procedure |
| [Renaming ingame items (or basically any visible text you could think of)](https://discord.com/channels/1302392670181916722/1485672994138358001/1485672994138358001) | ViruS | 2026-03-23 | [`../docs/12-localization-and-text.md`](../docs/12-localization-and-text.md) |
| [How to swap out bandage slot for another item (and do hex item swaps in general)](https://discord.com/channels/1302392670181916722/1481311357134704753/1481311357134704753) | spncryn | 2026-03-11 | [`hex-item-swaps.md`](hex-item-swaps.md) |

Non-forum sources absorbed alongside these:

| Source | Author | Captured in |
| --- | --- | --- |
| Install-routing guide, `#on-topic` (posted ≥4×: `1525051213945503844`, `1525059603858194462`, `1525174023540179047`, `1525198009800065235`) | SAMIEVILPUMA | [`mod-anatomy.md`](mod-anatomy.md) — extension-routing table |
| "Renumber to 1" practice — ~151 messages server-wide; key: `1532105102658244873`, `1533008421249482883`, `1532445093724684360`, `1534303468192530723` | various | [`../docs/08-naming-conventions.md`](../docs/08-naming-conventions.md) |

## Known but not yet absorbed

| Thread / topic | Why it matters |
| --- | --- |
| **Spncryn's BuildTable tutorial** | Referenced by SamiPuma as the thorough, precise method for **cross-category** slot moves (e.g. scarf → face paint), where his quick copy-paste isn't safe. The deeper treatment of BuildTables; would extend [`buildtable-xml.md`](buildtable-xml.md). **Thread not yet located.** |
| **Various Tweaks** ([Nexus 537](https://www.nexusmods.com/ghostreconbreakpoint/mods/537)) | A large gameplay-mod package (item wheel, class tools, NPC triggers, camera). Its "Item wheel swap" component is the working context for [`hex-item-swaps.md`](hex-item-swaps.md). Worth a case study. |

## How to add a thread

1. Fetch the full opening post **and** its replies — the replies routinely contain the corrections and gotchas that make the tutorial usable, and are often more valuable than the steps.
2. Fetch attached screenshots and read them; several threads carry their key information only in images.
3. Write it into a topic page (new or existing), preserving the KB's **verified / inferred / field-reported** distinction. A tutorial author's claim is *field-reported* until byte-verified — say so.
4. Add a row above, and an entry in [`../meta/research-log.md`](../meta/research-log.md) with message IDs.
5. Record contradictions rather than smoothing them over. Where practitioners disagree, or a fix worked without a known mechanism, that *is* the finding.
