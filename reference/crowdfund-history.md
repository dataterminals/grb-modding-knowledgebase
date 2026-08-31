# Tier 1 Imports crowdfunds — the two systems, and the catalogue

> **Live panel:** <https://dataterminals.github.io/t1-crowdfunds/> — the same dataset, kept current, with the registry sortable and filterable. This file is the narrative and the citations; the panel is the living view.
>
> **On names:** modders appear as **Modder A–R**, assigned by first appearance and stable throughout this file. The labels are used rather than handles so the analysis stays checkable — that one modder ran nearly a third of all crowdfunds is visible without naming them. Everyone else is referred to by role. Message IDs are unchanged, so every claim remains verifiable against the source. Creator credits do appear under their real handles on the [live panel](https://dataterminals.github.io/t1-crowdfunds/), which is where attribution belongs.
>
> **Status:** First comprehensive pass, 2026-08-23; names swept again 2026-08-24; on **2026-08-30** a Tier 1 moderator supplied vote tallies and supporter counts for 40 crowdfunds, which validated 11/11 against the votes readable here and rewrote most of §5. Compiled by reading *Tier 1 Imports* (guild `1302392670181916722`) directly through an authenticated Discord bridge as `@blkdnm`. Every claim below cites the message it came from. Provenance: [`../meta/research-log.md`](../meta/research-log.md).

## Why this is in a modding knowledgebase

A large fraction of the mod corpus catalogued in [`../examples/mod-catalog.md`](../examples/mod-catalog.md) is **crowdfund output**, and the folder names say so out loud:

| Corpus folder | Crowdfund it came from |
| --- | --- |
| `CFLIONNESS_JPCVest`, `CFLIONNESS_BangerJPC`, `CFLIONNESS_CondorTop`, `LIONNESS_Jeans`, `LIONNESS_RolledSlimShirt` | **Lioness** (`CF` = CrowdFund) |
| the `*bisonbelt*` set (Ferro Concepts Bison Belt) | **Tip of the Spear** (Modder A) |
| `AKM_KYPK` | **AKM w/ KPYK parts** |
| `Kalashnikova_SR1` | **Kalashnikov SR1** |
| `SA58` | **DS Arms SA 58 FAL** |
| `Vans Defcon`, various `Crye AVS` / `Crye JPC` variants | Modder B crowdfunds |

So "where did this mod come from, and why can't I find it on Nexus?" is a **provenance question this file answers**. A mod that went to the supporter armoury instead of public release is not lost — it was a crowdfund that voted the other way. See §5.

This file documents the **funding and distribution system**, not the modding pipeline. Nothing here touches game files.

---

## 1. The short answer

Tier 1 Imports has run **at least 58 crowdfunds** since the server was founded on **2024-11-02**, under **two distinct systems**:

| | **System 1 — "buy-in"** | **System 2 — the reaction-role system** |
| --- | --- | --- |
| **Ran** | 2024-11 → 2025-07 | 2025-07-29 → present |
| **Announced in** | `#crowdfund-projects-legacy`, `#crowdfund-votes`, sometimes `#on-topic` | `#crowdfund-projects` (`1399641218610233427`) |
| **How you opted in** | Vote in `#crowdfund-votes`, or DM the modder | React 👍 on the announcement post |
| **Price** | **Variable** — set per project by scope/asset cost ($5–$10+) | **Flat $10 minimum**, more accepted |
| **Access control** | Manual — a modder adds you to a channel | **Automated reaction-roles** via T1 Carl |
| **Channels per project** | One project channel (+ a confirmation channel by mid-2025) | **Two:** `#<name>` (unconfirmed) → `#<name>-confirmed` |
| **Roles per project** | None | **`<Name> unconfirmed` → `<Name>`**, both visible on your profile |
| **Reward tier** | "Tier 1 Armory", later "Tier 2" | **Supporter** (renamed from Tier 2, 2026-03-24) |
| **Named crowdfunds recoverable** | 24 rows, **23 distinct projects**, 1 still unnamed — and a floor, not a count (§7) | **34 of 34** |

The user's recollection is correct on every point: the second system is roles, unconfirmed→confirmed, and the supporter's own role showing on your profile in the server.

---

## 2. System 1 — the "buy-in" era (2024-11 → 2025-07)

> **Verified:** The server was built *for* this. On its first full day, the founder wrote: *"my idea for this server was to have this be a storefront of sorts for crowdfunding mod projects"* (`#on-topic`, msg `1302414873325604945`, 2024-11-02). The guild snowflake dates creation to the same day.

### The pricing model

Crowdfunds started as **split commissions**, not a flat fee. Modder B, `#supporter-chat`, 2024-11-03:

> "i was thinking for pricing those for guns at 60$ with $5 buy ins minimum of 12 confirmations" (msg `1302780729121570906`)
> "full model imports as well like logans $100 for the full with $10 buy ins" (msg `1302781232068825260`)

So the buy-in was **a share of the modder's commission price**, and the project needed a **minimum number of participants** to go ahead. That is the single biggest structural difference from System 2, where $10 is a floor rather than a share.

> **Verified:** Amounts genuinely varied per project as late as May 2025 — *"its a dope mod and the min buy in is $5"* (msg `1371750407612665856`), against $10 elsewhere. A member confirms the rule: *"There is a minimum buy in depending on the scope of the project or costs of the assets"* (msg `1384961275628490754`, 2025-06-18).

### The flow

1. A project is announced (`#announcements` `@everyone`, or `#on-topic`, pointing at `#crowdfund-projects-legacy`).
2. You **vote in `#crowdfund-votes`** (`1303906293219856477`) to opt in. *"if you want to 'buy-in' go vote in #crowdfund-votes"* (msg `1307805326631768124`).
3. You are **manually added** to the project channel, which carries the payment link.
4. You pay the modder directly — **PayPal** was standard (msgs `1369279409374232586`, `1437621881313431694`).
5. Once the modder confirms payment you are added to a **confirmation channel** (msg `1384961275628490754`).
6. At the end, **buyers vote** whether the mod goes public or stays private (msg `1312514949058400346`).

> **Verified:** The public/private release vote — the mechanic that still runs today — existed from the very first weeks. A member, 2024-11-30: *"at the end of every crowd fund there's a vote held for the people who bought in for it to stay private or be released"* (msg `1312514949058400346`).

### The flake problem, and the leak

Non-payment was a problem from the start. The founder, 2024-12-02 (msg `1313256555994681406`):

> "we've been having issues with people not following through with committing to the 'buy-ins' WITHOUT TELLING US THEY NO LONGER WISH TO 'BUY-IN'. If you continuously vote to 'buy-in' for a CROWDFUND and don't communicate that you no longer want to, you WILL be kicked from the server."

Then, in March 2025, someone leaked crowdfund mods:

> "Basically an edgelord tried to leak buy in mods" — a moderator, `#on-topic`, msg `1352106850715308134`, 2025-03-19

Modder B posted *"Im halting all buy ins atm"* the same day (msg `1351884110330859531`). Modder C, days later: *"we don't really know what the rules are yet, all of this is new, we're really jus trying to make sure the people from going into T1 wont be trying to leak stuff"* (msg `1353223879530647574`).

> **Inferred:** The March 2025 leak is a plausible driver of the move to per-project roles and auditable confirmed/unconfirmed state. **No message states this causally** — the two are adjacent in time and theme, nothing more. Treat as hypothesis.

---

## 3. System 2 — the reaction-role system (2025-07-29 → present)

> **Verified:** The changeover is dateable to **2025-07-29**. `#crowdfund-projects` (`1399641218610233427`) is created, the old channel is renamed to `#crowdfund-projects-legacy`, and a moderator posts the first announcement in the new format (msg `1399642502708858933`). The same moderator had taken over `@everyone` duty one day earlier (msg `1399335541346140210`, 2025-07-28).

> **Verified:** There was **no announcement of the change itself.** The entire `#announcements` channel was read end to end (94 messages, 2024-12-03 → 2026-08-19); it contains no "new crowdfund system" post. The system simply appeared as a new channel with a new post format.

### The flow, as the community explains it

The canonical description, from a member in `#on-topic`, 2025-08-26 (msg `1409849246219370558`):

> "react to the project that interests you, and you'll be added to an 'unconfirmed' channel which shows that you're interested in the mod and you intend to fund the project. Once funds are confirmed by the modder, you'll be added to the 'confirmed' channel for that mod and receive early/exclusive access to that project's mods."

And a member, 2025-11-12 (msg `1438273489294459001`):

> "When you click the emoji you get the (CF name) unconfirmed role, once you pay and show proof of payment you get the actual role and access to the respective channel"

So, precisely:

| Step | What you get |
| --- | --- |
| React 👍 on the post | Role **`<Name> unconfirmed`** → access to the unconfirmed channel |
| Read the unconfirmed channel | The modder's PayPal link / preferred payment method |
| Pay + post proof | Modder swaps your role for **`<Name>`** → access to `#<name>-confirmed` |
| Automatically, with the first one | **Supporter** role — permanent, one crowdfund is enough |

> **Verified:** Roles come in **channel pairs created seconds apart**. Crowd Control's unconfirmed channel is `1436320079779201145` and its confirmed channel is `1436320209735778396` (msg `1436644451639361586`, which links both). The `-confirmed` suffix in the channel list is therefore the *supporter* half of a pair.

> **Verified:** The reaction-role automation is **T1 Carl** (Carl-bot, account `235148962103951360`). It is the sole bot reactor on every crowdfund post — see §5.

### Why the roles are visible, and why that matters

The per-project roles are **public on your profile in the server**, and the community reads them. Examples:

- *"btw do you know that you have 4 unconfirmed crowdfund tags?"* — a member (msg `1441914698940284990`)
- *"Seeing as you're unconfirmed for two projects, you're not off to a good start."* — a member (msg `1432329575764856934`)
- *"It just gets annoying with how many 'unconfirmed' roles that I come across for projects that have been released for months."* — a member (msg `1442081888226246750`)

> This is the system's real innovation. System 1 had a flake problem it could only address by threatening bans. System 2 makes flaking **permanently legible on the flake's own profile**, and enforcement becomes social rather than administrative. The member quoted above even proposed formalising it: *"if you go unconfirmed throughout a project and release … you should forfeit the access to that project altogether"* (msg `1442079358293508186`, 2025-11-23).

### The tier roles

| Role | How you get it | Notes |
| --- | --- | --- |
| **Supporter** | Support any one crowdfund, ever | Was **"Tier 2"**. Grants `#supporter-chat`, `#supporter-armory`, `#supporter-polls`. Permanent. |
| **Kingslayer** | Given, not earned or bought | Was **"Tier 1"**. Grants `#kingslayer–armory`, `#kingslayer-polls`. |

> **Verified:** T1 Carl's canned explainer (msg `1486172833552928954`): *"The supporter role is granted to users that have helped the Tier 1 team make mods via supporting crowdfunds… The Kingslayer role is for members who have been around a while, supported projects or just generally had a good influence on the community. This isn't a level up system, you don't 'earn' the roles, they're given as they're given."*

> **Verified:** "Tier 1" was renamed to **Kingslayer** on **2026-03-24** by community poll — 149 votes: Kingslayers 81, Vanguard 40, Pathfinders 26, The Bulwark 2 (`#kingslayer-polls`, msg `1485007498162475028`; result msg `1486094687105318985`; a moderator's *"~~Tier 1~~ Kingslayer"* msg `1486095571730042960`).

> **⚠️ Naming trap for anyone reading old messages.** The tier labels **swapped meaning** during System 1. In March 2025 Modder C described the crowdfund reward as the *"Tier 1 Armory"* (msg `1347339972801466430`); by May 2025 the same reward was *"Tier 2"*, with Tier 1 as the earned role (msg `1375616498579800065`). Pre-mid-2025 references to "T1 Armory" usually mean **what is now the Supporter armoury**.

---

## 4. The catalogue

### System 1 (2024-11 → 2025-07) — 24 rows, 23 distinct projects, **not complete**

Entries marked ★ were announced only in chat and have **no `@everyone`**, which is why any count built from `#announcements` alone undercounts this era.

| # | Date | Crowdfund | Creator | Source |
| --- | --- | --- | --- | --- |
| 1 ★ | ≤2024-11 | **Night War Ghost** full outfit | Modder B | First completed crowdfund; released public, Nexus mod 1090 (msg `1310097291587223553`). The moderator's list calls it **Crowdfund Project 1** and shows it was a vote on *which of three* to build — Ghost Nightwar 18, Gaz Road Warrior 13, Capt Price 3, from 34 buy-ins. The first two were made and went public |
| 2 | 2024-11-17 | **Alex "Echo 3-1"** gear pack (CoD MW19) | Modder E | msg `1307805326631768124` (`#on-topic`) names no modder; the release announcement does — *"The Alex Crowdfund by the legendary [Modder E] is now live on nexus"*, msg `1320181570610659340`, Nexus mod 1128 |
| 3 ★ | 2024-11-23 | **MCX Spear LT** | Modder D | msg `1309770589795520592`; named 2026-08-30 from a moderator's list — capped at 10 buy-ins, no confirmed channel, released public (Nexus 1125) |
| 4 ★ | 2024-12-02 | **Shadow Company Heavy Outfit** — the moderator's list calls it *"Shadow Company Heavies as Wolves"* | Modder B | msg `1313256555994681406`; $10 buy-in |
| 5 ★ | ≤2024-12 | **Price Ghillie** ⚠️ *may never have been made* | Modder B | msgs `1318754880512327691`, `1350822574468370493`. The moderator's list has the Price as one of three options inside **Crowdfund Project 1** — it took **3 votes of 34**, and *"I don't think Chest ended up making the Price"*. Its destination is downgraded to unknown; the Nexus *Price's Ghillied Up* the sweep matched on may be an unrelated mod |
| 6 ★ | 2024-12-12 | **GZW assortment** — *same project as #8* | Modder E | msgs `1318754880512327691`, `1322527000925307053`; stayed private over asset copyright (`1349505166176555060`) |
| 7 | 2024-12-11 | *(unnamed new weapon)* | Modder B | msg `1316621603978874991` |
| 8 | 2024-12-12 | **GZW (Gray Zone Warfare) gear pack** — *the announced half of #6* | Modder E | msg `1316829668674109511` |
| 9 | 2024-12-29 | **Daniel Defense DDM4V7** | Modder F | msg `1322878300007174144` |
| 10 | 2025-01-14 | **Shadow Rusher** outfit | Modder B | msg `1328857878152613940` |
| 11 | 2025-01-21 | **Chimera Bridge** | Modder F | msg `1331300784599728188` |
| 12 ★ | ≤2025-03 | **SC Wolves / Wolves Overhaul** | — | msgs `1347339972801466430`, `1350547784788344943` |
| 13 | 2025-03-12 | **MCX Raptor** | Modder G | msg `1349440792007278703` |
| 14 | 2025-03-29 | **Australian SOF Vests** | Modder H | msg `1355682150719951068` |
| 15 | 2025-04-08 | **Ferro Concepts Slickster Plate Carrier** | Modder B | msg `1359291748144119898` |
| 16 | 2025-04-13 | **Next Generation Ghost's Gear** | Modder B | msg `1360895696894693396` |
| 17 | 2025-05-06 | **Konni Group Outfits** | Modder I | msg `1369345583709552750` |
| 18 | 2025-05-08 | **Kalashnikov SR1** | Modder J | msg `1370159031775268944` |
| 19 | 2025-05-15 | **"Warfare" movie outfits** | Modder B | msg `1372703221805481984` |
| 20 | 2025-06-13 | **BREN 3** | Modder G | msg `1383200543043883179` |
| 21 | 2025-06-19 | **Haenel MK556** | Modder J | msg `1385507734392406037` |
| 22 | 2025-07-05 | **DS Arms SA 58 FAL** *(renewal)* | Modder K | msg `1391022434211069993` |
| 58 ★ | ≤2025 | **Salomon X4 Ultra Mid GTX** | Modder B | Recovered 2026-08-30 from a moderator's list; appears in no announcement readable here. 18 buy-ins, no confirmed channel, released public. **Numbered 58 because catalogue numbers are identifiers, not a chronological rank** — renumbering would break every citation in this file. It belongs in era 1 |
| 23 | 2025-07-08 | **Commando Diving Drysuit**, a.k.a. **"Frogman"** | Modder B | msg `1392009113185030288`; "Frogman" per msgs `1398318235249672334`, `1399101991619399801` |

> **Verified (2026-08-24) — #8 is the GZW gear pack.** The announcement calls it only *"a new gear pack by the one and only [Modder E]"*. Modder E names it himself ten days later: *"Ghost nightwar top and a mid sleeve top from **my gzw project**"* (msg `1320189637448433747`, 2024-12-22), having trailed it on 2024-11-09 — *"Gray Zone Warfare has some interesting looking vests that fit those two very well, that's all I'm saying for now"* (msg `1304937052088832092`).
>
> **Inferred (strong):** that makes **#6 and #8 the same crowdfund**, counted twice. On 2024-12-18 Modder B lists what is open — *"There are still three projects available for buy ins, price ghillie, shadow company heavy and **the latest** gzw assortment"* (msg `1318754880512327691`) — and "the latest" points back at the announcement six days earlier. Three open projects, no fourth: there was no separate Modder E gear pack running alongside a GZW one. #6 was reconstructed from chat and #8 from the announcement; they are one event seen from two directions. Both rows are kept so the citations survive, which is why this era now reads **23 rows, 22 distinct projects**.
>
> **Correction (2026-08-24) — #8's date.** It was listed as 2024-12-16; the announcement it cites is timestamped **2024-12-12T18:10Z**. Corrected.

> **From the moderator's list (2026-08-30).** It names **#3** (MCX Spear LT), gives **#4** a creator, adds **#58**, and calls #4 *"Shadow Company Heavies as Wolves"* — which is the language §4 records separately as **#12** (SC Wolves / Wolves Overhaul). #4 and #12 may therefore be one project rather than #10 and #12. Both ambiguities are now live and neither is settled; the list covers neither #10 nor #12 by name.
>
> ⚠️ **It also reopens #6 ≡ #8.** This file infers the GZW assortment and the "new gear pack" are one crowdfund counted twice. The moderator recalls **two** GZW crowdfunds — one Modder B's, one Modder E's — *"both never finished and kept private due to legal reasons"*, but hedges it explicitly as memory, with question marks, because both announcement posts are deleted. That is weak evidence against a strong inference: **the merge stands, and the doubt is recorded.** Modder E can settle it in a sentence.
>
> **Inferred:** #12 may be the same project as #10 — Modder C linked channel `1328856903996018828` (created the same day as the Shadow Rusher announcement) while calling it *"the SC Wolves outfits"*. Both are Shadow Company content. Not resolvable without access to that channel; listed separately with the ambiguity flagged.

### System 2 (2025-07-29 → present) — 34, believed complete, all 34 named

Every entry has a dated `@everyone` in `#announcements`. **Every one is now named** — the last five fell on 2026-08-24; the method and the citations are in §7.

| # | Date | Crowdfund | Creator |
| --- | --- | --- | --- |
| 24 | 2025-07-29 | Vulcan/Malyuk 7.62 Assault Rifle | Modder I |
| 25 | 2025-08-14 | AKM w/ KPYK parts | Modder J |
| 26 | 2025-08-18 | **To the Moon** | Modder B |
| 27 | 2025-09-17 | **Snake Eater** | Modder B |
| 28 | 2025-09-23 | **Steyr** | Modder J |
| 29 | 2025-10-13 | **Operation Mother's Chest Hair** | Modder B |
| 30 | 2025-11-07 | **Crowd Control** *(Mercer's debut)* | Modder L |
| 31 | 2025-11-09 | **Enfield Tea Set** | — |
| 32 | 2025-11-19 | **Bad Boys** | Modder B |
| 33 | 2025-11-21 | **Dual Sig** | Modder O |
| 34 | 2025-12-15 / 20 | **Door Kicker** | Modder L |
| 35 | 2025-12-17 | **Lioness** | Modder B |
| 36 | 2025-12-15 / 20 | **Kill Confirmed** | Modder M |
| 37 | 2026-01-06 | **Ahead of Your Time** | Modder C |
| 38 | 2026-01-18 | **Tip of the Spear** | Modder A |
| 39 | 2026-01-30 | **Recce** | Modder L |
| 40 | 2026-02-11 | **Blackbird** | Modder O |
| 41 | 2026-02-17 | **Cold Ops Carbonara** | Modder K |
| 42 | 2026-02-23 | **Step Brothers in Arms** | Modder M + Modder R |
| 43 | 2026-02-27 | **Crye Babies** | Modder B |
| 44 | 2026-03-27 | **Spirited Away** | — |
| 45 | 2026-03-31 | **Wolf Pack** | Modder O |
| 46 | 2026-04-07 | **Forgotten Weapons** | Modder L |
| 47 | 2026-04-12 | **CYBERSAMI** 🔴 *still posted* | Modder C |
| 48 | 2026-05-11 | **Smokin Aces** | Modder N |
| 49 | 2026-05-15 | **Breach & Clear** | Modder B |
| 50 | 2026-06-01 | **Heavy Metal** 🔴 *still posted* | Modder L |
| 51 | 2026-06-12 | **Pastaslov** | Modder K |
| 52 | 2026-06-13 | **Time 'n Tide** | Modder O ("Bon") |
| 53 | 2026-07-03 | **Rangers Lead The Way** | Modder B |
| 54 | 2026-07-11 | **GWOT Classics** | Modder M |
| 55 | 2026-08-19 | **Dealer's Choice** 🔴 *open* | Modder P |
| 56 | 2026-08-25 | **Flash Point** 🔴 *open* | Modder O |
| 57 | 2026-08-25 | **WMD** 🔴 *open* | Modder N |

> **#56 and #57 were caught live on 2026-08-25**, twelve hours apart, and both posts plus both `@everyone`s are still on the board — the first entries in this catalogue recorded from the board rather than reconstructed after the fact. **Flash Point** (post `1541701813349253190`, announcement `1541702858146320394`, *"Another Bonfire Masterclass"*): Spiritus Systems LV-119 and an FN Five-Seven MK3, Modder O's **third** after Dual Sig and Blackbird. **WMD** (post `1541884927086301296`, announcement `1541885741859078318`, *"Keem's got some WMDs for you"*): six weapons and handguards, Modder N's **second** after Smokin Aces.

> Names for #43–#45, #48, #49 and #52 were recovered by **reading the announcement title-card graphics** posted in `#announcements` — the artwork spells the name out where the surviving text does not.

> **#28** was named from *outside* the server, on 2026-08-23: a member of **The Bivouac** listing what was live on 2025-09-24 — *"the Metal Gear Solid/XOF and the Steyr Crowdfund"* (Bivouac msg `1420518885261836368`), which also confirms #27 by its subject matter.

#### Where the last five names came from (2026-08-24)

None of these five posts exists any more. Every name below is a **third party naming the crowdfund while it was live**, and where possible bound to that crowdfund's exact post id. Method in §7.

| # | Name | The binding |
| --- | --- | --- |
| **39** | **Recce** | A moderator lists what is open on 2026-03-22: *"Tip of the Spear, Recce (maybe?), Cold Ops Carbonara, Cryebabies, Step Brothers-in-Arms are all open crowdfunds"* (msg `1485209464712859778`). Modder L, the announced creator, says *"the link is in the pins of Recce"* (`1474000605449158917`) and *"Part of the Recce CF exclusives"* (`1484765469213851790`). Its **role `1466647776396836874` was created 23 minutes before the post** and Modder L credits exactly that role when releasing *"a series of South African Weaponry and Gear"* — Vektor R4/SS-77, SANDF beret, Beretta 92F (`1490767344023371957`), which is what the 🇿🇦 flag on the announcement was pointing at. |
| **40** | **Blackbird** | In `#on-topic`, 2026-03-18, a member says an optic is an *"Exclusive piece of Bon's latest crowdfund"* and another immediately posts **#40's own post link** in confirmation (`1483922818759528478`), adding *"if it's the project I sended then it's complete"*. Modder O — display name *Bonfire* — had posted *"BLACKBIRD EXCLUSIVE"* on 2026-02-19 (`1473890947162181723`). A member on 2026-03-16: *"i have the **blackbird role** now"* (`1483220369853648968`) — and a crowdfund's role carries the crowdfund's name. ⚠️ **Read "Blackbird" carefully in this server:** a member also goes by *BlackBird* and signs patch releases *"By BlackBird"* (e.g. `1425753643935727696`, October 2025). They are unrelated — the crowdfund is Modder O's, and it is *named* Blackbird rather than run by anyone of that name. |
| **41** | **Cold Ops Carbonara** | Named **the day it was announced**: *"I want to support the crowdfunding Cold Ops Carbonara, but I don't have PayPal"* (msg `1473362715845070901`, 2026-02-17), and *"just started a fresh install right as carbonara got announced"* (`1473389751875670037`, same day). Modder K posts **#41's post link** and the name seconds apart in the same thread (`1484990875707637831` / `1484990912017993778`), then publishes it: *"# Public release of Cold Ops Carbonara"* (`1507031310512685106`, `1507047540111966240`). That also settles the *"Time for some cold pasta"* announcement. |
| **42** | **Step Brothers in Arms** | One day after the announcement: *"the newest rn is step brother by my buddy [Modder M], tip of spear and ahead of time by [Modder C]"* (msg `1475996442270109739`, 2026-02-24). Modder R posts **#42's post link** in their own showcase thread (`1478232538240782428`). Modder M on release: *"# The first **tag-team** CF Project goes LIVE! … [Modder R] it was a blessing and an honor to work alongside you"* (`1502351245107789874`) — which is why the announcement led with a *"let's do this team"* GIF, and why this is the first crowdfund in the catalogue with two creators. |
| **46** | **Forgotten Weapons** | Five minutes after the announcement, in `#shit-talk`: *"Forgotten Weapons? Ian's mustache will be included?"* (msg `1490990928406773921`) — Ian McCollum presents the *Forgotten Weapons* channel, and the announcement's title card is an **FW** monogram. Next day Modder L posts *"Exclusive to Forgotten Weapons CF"* **followed by #46's exact post link** (`1491516204358176919`), and on release thanks *"all those that supported the Forgotten Weapons CF"* over five obscure guns (`1503565360715141321`). |

> **Correction (2026-08-24) — #26 is "To the Moon", not "White Moon".** The announcement reads *"Some beautiful White Moon assets being brought in by [Modder B]"* (msg `1407147347590250516`), and an earlier pass took "White Moon" for the project name. **White Moon Studio is the asset vendor** — a member describing a different project: *"The plan is to start the crowdfunding when I get a message from **White Moon Studio** with the first screenshots of the asset"* (msg `1327944649083584522`). The crowdfund itself is **To the Moon** everywhere else: a moderator answering a newcomer names both halves of the channel pair — *"**to-the-moon** base channel … and its sister channel the **to-the-moon-confirmed** channel"* (`1409115547068534904`) — and *"[Modder B] with his To the Moon Crowdfund"* links **#26's own post id** (`1409099156320161794`). Read the announcement as *assets from White Moon*, not *a crowdfund called White Moon*.

> **Correction (2026-08-24) — #43 is "Crye Babies", not "Crye Baby".** The singular came from the announcement's attachment filename, `CRYE_BABY.png`. Modder B's own release header is plural: *"CRYE BABIES SUPPORTER RELEASE"* (msg `1487141790770532525`, 2026-03-27), and the community is unanimous — *"Currently an exclusive for the **Crye Babies** CF"* (`1478840232487944213`), *"crye babies is closed"* (`1495819342686847036`).

> **Creators filled in (2026-08-24).** #33 **Dual Sig** → Modder O, named in a showcase thread: *"it was part of the crowdfund called 'Dual Sig' — you can ask [Modder O] for the SPC"* (msg `1472093680142778496`). #34 **Door Kicker** → Modder L, who runs its confirmed channel and its payments (`1459523762943824090`) and posts *"The **Door Kicker Crowdfund** has come to Tier 2"* (`1465710021294821556`). Both were already implied by the delivery table in §5; they are now cited.

---

## 5. What the numbers show

### Sign-ups on the eight posts still on the board

Read **2026-08-30T00:53Z** with a reactor expansion, so these are **exact reactor lists, not just counts**. T1 Carl seeds the 👍 on every post, so the human figure is the raw count minus one. This is a **snapshot of one moment**, not a history — see §7.

| Crowdfund | Raw 👍 | Humans | Min. committed @ $10 |
| --- | ---: | ---: | ---: |
| Rangers Lead The Way | 421 | **420** | $4,200 |
| GWOT Classics | 334 | **333** | $3,330 |
| CYBERSAMI | 207 | **206** | $2,060 |
| Heavy Metal | 181 | **180** | $1,800 |
| Dealer's Choice | 140 | **139** | $1,390 |
| Pastaslov | 138 | **137** | $1,370 |
| Flash Point *(5 days old)* | 108 | **107** | $1,070 |
| WMD *(5 days old)* | 107 | **106** | $1,060 |

### Backer overlap — the interesting part

Across those eight posts: **918 distinct people, 1,628 sign-ups.**

| Signed up for | People | Share |
| --- | ---: | ---: |
| 8 of 8 | 17 | 1.9% |
| 7 of 8 | 9 | 1.0% |
| 6 of 8 | 15 | 1.6% |
| 5 of 8 | 25 | 2.7% |
| 4 of 8 | 21 | 2.3% |
| 3 of 8 | 68 | 7.4% |
| 2 of 8 | 163 | 17.8% |
| **1 of 8** | **600** | **65.4%** |

> **Verified:** The backer base is **wide and shallow, and the shape holds across re-reads** — 67.9 % backed exactly one crowdfund across six posts on 2026-08-23, 67.9 % across seven on 2026-08-25, **65.4 %** across eight on 2026-08-30. Two new crowdfunds and 81 more people moved it by two and a half points. A crowdfund is not funded by a fixed subscriber core; each recruits largely fresh. **Fresh-backer share** — people appearing on none of the other seven: CYBERSAMI 109/206 (53 %), GWOT Classics 146/333 (44 %), Rangers Lead The Way 179/420 (43 %), Heavy Metal 61/180 (34 %), Dealer's Choice 39/139 (28 %), WMD 26/106 (25 %), Flash Point 20/107 (19 %), Pastaslov 20/137 (15 %).

> **The tail of the distribution is an artefact of when you read it.** On 2026-08-25 only **5 people** were on all seven posts; five days later **17** are on all eight. That reads like a surge and is not one. Flash Point was twenty minutes old at the first read, so the people who back everything simply had not reacted yet — the 12 who were then "6 of 7" are the 12 who make up the difference. **The same distortion, seen from the other end, sank the fresh-backer figure**: Flash Point's first 11 backers were 10/11 repeat backers (9 % fresh), and five days later it sits at 19 % fresh and climbing. The people watching the board when a post lands are the regulars; everyone else arrives over the following weeks. **Anything measured on a crowdfund's first day describes who was watching, not who funds it** — `tools/refresh.py` now refuses to compute a new-blood figure for a crowdfund less than a week old for exactly this reason.

### Release-vote turnout — 40 of 58, and the supporters behind each

> **Where these came from (2026-08-30).** A read-only role covering the confirmed channels was declined
> on 2026-08-25. A moderator was then asked, not for access, but for **the numbers** — and supplied
> them for every completed crowdfund, on the explicit basis that the objection had been to channel
> privacy rather than to the figures. That distinction is the whole thesis of
> [`../meta/crowdfund-asks.md`](../meta/crowdfund-asks.md), and it is what turned a refusal into the
> largest single data drop in this file.
>
> **It validates 11/11.** Every vote this account can read for itself appears in the moderator's
> file with **both numbers identical**. Nothing had to be reconciled, which is why the other 29 are
> carried at the same confidence rather than hedged as one person's recollection. Rows marked **°**
> are the ones read first-hand; the rest are the moderator's, corroborated by those eleven.
>
> ⚠️ **Every figure here is the crowdfund's own vote tally, never the summary sentence beside it.**
> He compiled it by going through the confirmed channels himself, counting members by hand where no
> count was shown, and copy-pasting one line per crowdfund with the numbers edited in. That workflow
> is exactly what leaves a **stale summary sentence next to correct numbers** — which is the file's
> one error, and why the rule is worth stating. Where tally and sentence disagree, the tally wins;
> see #40 below, where a screenshot of the poll settled it in the tally's favour.

**`Members` is new, and it retires a caveat.** It is the confirmed channel's membership — the people
who actually supported the project. Until now this file could only say turnout was a *floor* on how
many had supported it; the real figure is now known, and the gap is large. Lioness drew 275 votes
from **435 supporters**.

| # | Crowdfund | Creator | Members | Turnout | Public | Supporters | Private | Went to |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 35 | **Lioness** ° | Modder B | 435 | **275** | 132 | 143 |  | Supporters |
| 43 | **Crye Babies** | Modder B | 278 | **153** | 54 | 99 |  | Supporters |
| 38 | **Tip of the Spear** ° | Modder A | 244 | **149** | 84 | 65 |  | Public |
| 29 | **Operation Mother's Chest Hair** ° | Modder B | 244 | **144** | 97 | 47 |  | Public |
| 44 | **Spirited Away** | — | 237 | **140** | 78 | 62 |  | Public |
| 26 | **To the Moon** | Modder B | 253 | **129** | 36 | 93 | 0 | Supporters |
| 49 | **Breach & Clear** | Modder B | 203 | **120** | 90 | 30 |  | Public |
| 37 | **Ahead of Your Time** ° | Modder C | 197 | **103** | 43 | 60 |  | Supporters |
| 41 | **Cold Ops Carbonara** | Modder K | 165 | **103** | 74 | 29 |  | Public |
| 27 | **Snake Eater** ° | Modder B | 246 | **99** |  | 35 | 5 | Public |
| 48 | **Smokin Aces** | Modder N | 156 | **98** | 37 | 61 |  | Supporters |
| 45 | **Wolf Pack** | Modder O | 117 | **86** | 64 | 22 |  | Public |
| 28 | **Steyr** | Modder J | 119 | **84** | 64 |  | 20 | Public |
| 19 | **"Warfare" movie outfits** | Modder B | 205 | **80** | 53 | 22 | 5 | Public |
| 23 | **Commando Diving Drysuit** | Modder B | 117 | **74** | 36 | 38 | 0 | Supporters |
| 32 | **Bad Boys** ° | Modder B | 131 | **72** |  | 40 |  | Supporters |
| 52 | **Time 'n Tide** | Modder O | 109 | **72** | 48 | 24 |  | Public |
| 4 | **Shadow Company Heavy Outfit** | Modder B | 119 | **71** | 63 |  | 8 | Public |
| 25 | **AKM w/ KPYK parts** | Modder J | 87 | **64** | 50 |  | 14 | Public |
| 42 | **Step Brothers in Arms** | Modder M + R | 115 | **62** | 41 | 21 |  | Public |
| 21 | **Haenel MK556** | Modder J | 88 | **61** |  | 57 | 4 | Supporters |
| 33 | **Dual Sig** ° | Modder O | 84 | **61** | 22 | 39 |  | Supporters |
| 16 | **Next Generation Ghost's Gear** | Modder B | 96 | **60** | 55 |  | 5 | Public |
| 36 | **Kill Confirmed** ° | Modder M | 87 | **58** | 27 | 31 |  | Supporters |
| 31 | **Enfield Tea Set** ° | — | 75 | **55** | 42 | 13 |  | Public |
| 40 | **Blackbird** | Modder O | 83 | **55** | 40 | 15 |  | Public |
| 30 | **Crowd Control** ° | Modder L | 79 | **54** | 22 | 32 |  | Supporters |
| 34 | **Door Kicker** ° | Modder L | 56 | **48** | 17 | 31 |  | Supporters |
| 46 | **Forgotten Weapons** | Modder L | 75 | **47** | 37 | 10 |  | Public |
| 22 | **DS Arms SA 58 FAL** | Modder K | 52 | **45** | 25 | 20 | 0 | Public |
| 39 | **Recce** | Modder L | 57 | **40** | 33 | 7 |  | Public |
| 20 | **BREN 3** | — | 56 | **36** | 31 |  | 5 | Public |
| 15 | **Ferro Concepts Slickster Plate Carrier** | Modder B | 50 | **35** | 33 |  | 2 | Public |
| 24 | **Vulcan/Malyuk 7.62 Assault Rifle** | — | 57 | **34** | 26 | 6 | 2 | Public |
| 17 | **Konni Group Outfits** | — | 35 | **30** | 28 |  | 2 | Public |
| 18 | **Kalashnikov SR1** | Modder J | 28 | **25** | 23 |  | 2 | Public |
| 13 | **MCX Raptor** | — | 38 | **22** | 14 |  | 8 | Public |
| 14 | **Australian SOF Vests** | — | 25 | **22** | 17 |  | 5 | Public |
| 11 | **Chimera Bridge** | — | 24 | **15** | 9 |  | 6 | Public |
| 3 | **MCX Spear LT** | Modder D | 14 | **10** | 10 |  |  | Public |
| | **40 crowdfunds** | | **4,936** | **2,991** | | | | |

> **Verified:** **4,936 supporters and 2,991 votes across 40 crowdfunds.** Median
> participation is **63 %** — but it scales inversely with size. The twelve crowdfunds with 150+
> members vote at a median of **59 %**; the twelve under 60 members vote at **71 %**, topping out at
> 89 % (Kalashnikov SR1, 25 of 28). A small crowdfund is close to a plebiscite of everyone who supported it.
> A large one is decided by a little over half the room, and the largest — Warfare, 205 members —
> was settled by **39 %** of its backers.

> **Verified — the split, on votes rather than inference: 28 public / 12 supporters.** This is the
> same shape the public-record sweep found by a completely different route, and it settles the
> correction recorded there for good. **Two thirds of crowdfunded work reaches the public.**
> The era difference holds up too, and sharpens: **System 1 went 12 public / 2 supporters**;
> **System 2 goes 16 / 10.**

> **⚠️ Two disagreements, neither smoothed over.**
> - **#40 Blackbird — asked, and settled.** The file records **40 public against 15 supporter** and
>   then states the result as Supporter Armory. Asked directly, the compiler answered *"was released
>   according vote"* and sent **a screenshot of the closed poll**: *"Where to release."* — Public
>   **40 (73 %)**, Tier 2 **15 (27 %)**, 55 votes (msg `1543793745684603011`). Recorded **public**,
>   now on primary evidence rather than inference. He also explained why members called it public
>   yet could not find it: Bonfire released the items **individually, not under the Blackbird
>   name**.
> - **#28 Steyr flips to public.** The sweep had it as supporters on three members saying the Steyr
>   DMR sits in the armoury — but that ballot offered only **public or private** (64/20), with no
>   supporter option. The vote decides it. Both can be true: a Steyr in the supporter armoury need
>   not have arrived there by this vote.

> **⚠️ Read the scope before reading the outcome.** The vote does not always cover the whole crowdfund. **Snake Eater's** poll asked *"Where to share the XOF Outfits?"* — one item — and a moderator says so in-channel: *"MOST of the items in this crowdfund are supporter items, the XOF suit is what will be made public from this crowdfund"* (msg `1426355642410467368`). **Bad Boys'** was scoped to *"the Exfil Helmets, Police Vests and Belt"*. The other nine read as whole-project. So a "went to" cell describes **the voted portion**, not necessarily the whole crowdfund.

### Where the mods actually went — 47 of 58, and it reversed the earlier reading

Turnout answers this for the 40 above. For the rest, **where a crowdfund's output landed leaks** —
into public chat, `#mod-releases`, `#supporter-armory`, and the Nexus links creators post
themselves. Swept 2026-08-30, then largely superseded the same day by the moderator's vote figures.

| Destination | Count | Of the 47 |
| --- | ---: | ---: |
| **Public** | **33** | 70 % |
| **Supporters** | **12** | 26 % |
| **Private** | **2** | 4 % |
| *Still open (on the board)* | 8 | — |
| *Unknown* — #5, #7, #10 | 3 | — |

**Evidence grade, which the panel shows and this table must not blur:** **39** come from a release
vote (11 read here, 28 from the moderator), **7** from a creator or moderator stating an outcome
outright, and **1** from members only. A **solid** pill on the
[live panel](https://dataterminals.github.io/t1-crowdfunds/) is a vote; a **dashed** one is
reconstructed.

> **⚠️ Correction, now closed — "two thirds stay private" was backwards.** The 11 readable votes
> split 7 supporters / 4 public, and an earlier pass generalised that to *"roughly two thirds of
> crowdfunded work never reaches Nexus."* The public-record sweep suggested the reverse; the
> moderator's 40 votes then **settled it: 28 public / 12 supporters.** The 11 were not a random
> sample — they are the crowdfunds one account backed, clustered in 2025-09 → 2026-01, which is both
> a narrow window and the era that keeps the most behind the role. **Two thirds reaches the public.**

**The eras differ, and the vote data sharpens it.** System 1: **17 public / 2 supporters / 2
private**. System 2: **16 public / 10 supporters**. System 1 pushed almost everything to Nexus;
System 2 keeps roughly a third back. That follows from §3 — once supporting *any* crowdfund grants a
permanent role with a standing armoury attached, "supporters" stops meaning locked away and starts
meaning the reward that makes the role worth holding, so voting that way costs a backer less.

> **⚠️ Destination is not the same claim as turnout.** Almost every "public" crowdfund **still
> retained exclusives** — Forgotten Weapons kept a working RMR back; Snake Eater went public on the
> sneaking suit while *"a majority of the items … were exclusive to those that supported it"*
> (msg `1532274964785266778`). **Public does not mean all of it.** And where a vote was scoped to
> part of a project, destination and vote answer different questions — see the scope warning above.

> **The failure mode this sweep had to dodge**, kept because it will recur: a member writing *"I
> guess it was voted to not go public"* about Snake Eater (msg `1532273474637135975`) is flatly
> wrong, and only detectable because Snake Eater is one of the readable 11. Ordinary words make it
> worse — `Steyr`, `Recce`, `WMD` and `Warfare` are all common, and a search for `wolf pack` returns
> the unrelated *Hound Wolf Squad*. **#28 Steyr was in fact recorded wrong by this method** and the
> vote corrected it, which is the sweep's error rate made visible: one in forty-five.

### The four places content actually ends up

| Destination | Who can reach it | Notes |
| --- | --- | --- |
| **Public** | Anyone | `#mod-releases`, usually Nexus too. |
| **Supporter armoury** | Anyone who has backed *any* crowdfund | `#supporter-armory`. Called the **Tier 2 Armory** until March 2026 — and the **Tier 1 Armory** before that. |
| **Crowdfund exclusive** | Backers of that one crowdfund | Never leaves the crowdfund's own channel. *"Exclusives don't go public they are a treat from the modders to the people that contributed to the CF"* — a member, msg `1498457727851298858`. |
| **Private** | Nobody further | An option on Snake Eater's poll (5 votes). Has never won. |

> **Not a crowdfund destination:** the **Kingslayer armoury** (`#kingslayer–armory`). That is the *earned* role's own track — modders post there directly, threads titled *"Kingslayer Exclusive"* (e.g. *HK416D SMR | Final Edition | Kingslayer Exclusive*). Nothing arrives there by crowdfund vote. It is easy to confuse with the supporter armoury precisely because the latter used to be called "Tier 1 Armory".

### The vote is not the end of it

> **Verified:** every one of the 11 measurable crowdfunds kept delivering **after** its vote — **198 separate drops in total**, a median of **64 days** from first to last. **This is the one table the 2026-08-30 data drop did not move.** Votes went from 11 to 40 and destination to 47, but delivery is still **11 of 58** — a drop happens inside the channel, leaves no public trace, and nobody keeps a tally of them the way they keep the vote result. "Every one" means every one of the 11 that can be read.

| Crowdfund | Drops | Window | Principal creator |
| --- | ---: | ---: | --- |
| Operation Mother's Chest Hair | 39 | 64 d | Modder B |
| Ahead of Your Time | 36 | 141 d | Modder C |
| Door Kicker | 18 | 57 d | Modder L |
| Lioness | 18 | 32 d | Modder B |
| Snake Eater | 16 | 169 d | Modder B |
| Crowd Control | 15 | 94 d | Modder L |
| Dual Sig | 13 | 189 d | Modder O |
| Kill Confirmed | 13 | 35 d | Modder M |
| Tip of the Spear | 13 | 70 d | Modder A |
| Bad Boys | 11 | 25 d | Modder B |
| Enfield Tea Set | 6 | 48 d | Modder Q |

**Each creator distributes differently**, which is why a single house format cannot be counted on: Modder L keeps one Google Drive folder and updates it in place (*"All mod files and updates will be in the Gdrive, as usual"*); Modder O ships versioned drops (MPX V1 → V1.1 → V2.0); Modder B, Modder M, Modder C and Modder A post discrete `MOD RELEASE` items.

> **Method caveat:** a "drop" is a post from the crowdfund's principal creator carrying a download link or a replacement statement. An earlier count keyed on the literal `MOD RELEASE` heading and scored Crowd Control, Enfield Tea Set, Dual Sig and Door Kicker as **zero** — all four had in fact delivered, in other formats. That was a measurement artefact and is corrected here.

### Cadence

| Period | Months | Crowdfunds | Rate |
| --- | ---: | ---: | ---: |
| System 1 | ~9 (2024-11-02 → 2025-07-29) | 22 distinct, a floor | ≥2.5 / mo |
| System 2 | ~13 (2025-07-29 → 2026-08-30) | 34 | 2.6 / mo |

**The rate did not change when the system did** — which is worth noting, because everything else about the funding model did.

**Creator concentration:** Modder B has run **17 of the 58 — 29 %**, nearly a third of every crowdfund the server has held, and up from the 14 recorded before 2026-08-30 gave them #4, #49 and #58. Nine fall in era 1, so the share held steady across the changeover rather than being a legacy of the early days. Modder B also owns the largest sign-up on record (Rangers Lead The Way, **420** and still open). Next are Modder L and Modder O with 5 each.

---

## 6. Where Tier 1 Imports came from

Tier 1 Imports was created **2024-11-02**. It did not appear out of nothing: **The Bivouac** (guild `981599102523539466`), a Ghost Recon: Breakpoint modding community running since **mid-2022**, is where much of its early membership already was.

> **Verified — the two servers are directly linked in the record:**
>
> | Date | Event | Source |
> | --- | --- | --- |
> | 2024-11-02 | Tier 1 Imports created. Day one, its founder states the plan: *"my idea for this server was to have this be a storefront of sorts for crowdfunding mod projects."* | T1 msg `1302414873325604945` |
> | 2024-11-06 | The Bivouac's ownership transfers to a new owner. The announcement names no outgoing owner and signals no conflict. | Bivouac msg `1303731106599796817` |
> | 2024-11-08 | The founder posts into the Bivouac's `#grb-talk`: *"I'm the co-creator of Tier 1 Imports"*, with an invite link. He is not removed for it. | Bivouac msg `1304532626023120966` |
> | 2024-11-23 | Modder M, from inside the Bivouac, routes people to Tier 1 for crowdfunds: *"check nexusmods, put up a comission here, or make a request for a crowdfund mod … over at the tier1 server."* | Bivouac msg `1309919966497214525` |
> | 2026-05-11 | *"Just go to Tier 1 Imports server, this one is dead."* The Bivouac still exists but is largely inactive. | Bivouac msg `1503318552331948113` |

Several people who went on to become Tier 1 regulars — including the modders Modder M and Modder C — were active Bivouac members at the time.

### The difference that actually matters

> **Verified:** The Bivouac's channel list still carries `#request-commission` and `#commission-guidelines`. It runs **commissions** — one person pays one modder for one job. Tier 1 was built, on its first day, to **split that cost across many people**. That is what a crowdfund is, and it is the structural reason the second server exists.

> **Inferred / unresolved:** whether Tier 1 was a deliberate *split* from The Bivouac. The founding, the ownership handover and the open recruitment all fall inside one week, which is suggestive — but **no message states a cause**, and the recruitment being public and tolerated argues against an acrimonious break. A long-standing member of either server could settle this in a sentence; the record cannot.

---

## 7. What could not be recovered, and why

> **⚠️ `#crowdfund-projects` does not keep its history.** The channel holds **six posts**, the oldest from 2026-04-12. Everything older is gone: `before=` paging and `around=` jumps both return nothing, and roughly 20 `@everyone` posts in `#announcements` still link to crowdfund posts that **no longer exist**.
>
> **Confirmed with a real probe (2026-08-24):** resolving five of those dead links by URL — #39, #40, #41, #42, #46 — returns not the post but the channel's *oldest surviving* message (CYBERSAMI, `1493032233727033454`) in every case. That is a fetch failing over to the channel floor, so the posts are genuinely unfetchable rather than merely un-paged. Independently, they are absent from the search index: a guild search for `ANNOUNCING OUR NEXT CROWDFUND PROJECT` scoped to that channel returns the six live posts and nothing else.
>
> **Correction (2026-08-23):** an earlier draft of this file claimed CYBERSAMI and Heavy Metal were deleted between 2026-08-19 and 2026-08-23, and called that a direct observation. It was not — it was a `limit=4` query mistaken for the channel's full contents. Both posts are still on the board. **No deletion has actually been observed.** Whether posts are removed as projects close, or the channel was purged once in a cleanup, is **not established** — two of the six are months past their stated end date and still posted.

Consequences:

1. **👍 counts exist only for crowdfunds still on the board.** For the other **26** System 2 crowdfunds the commitment count went with the post — and System 1 never used this channel at all, so it has none. The figures in §5 are an eight-project snapshot taken at one moment, not a history, and they move: three reads between 2026-08-23 and 2026-08-30 are recorded above and none of them agree.
2. ~~**Five System 2 crowdfunds cannot be named**~~ — **closed 2026-08-24**, and **#3 closed 2026-08-30** from the moderator's list (MCX Spear LT). **Exactly one crowdfund in the catalogue is now unnamed: #7** (Modder B, *"a new weapon"*, msg `1316621603978874991`), which appears nowhere in that list either.
3. **System 1 has no reliable count.** `#crowdfund-projects-legacy` (`1302441788585279570`) and `#crowdfund-votes` (`1303906293219856477`) both return `forbidden`; individual System 1 project channels are either `forbidden` (`1370158615473946667`) or **deleted outright** — `1309056687801503805`, linked as a live crowdfund on 2024-11-21 (msg `1309130622513577984`), now 404s. The 24 rows in §4 are what could be reconstructed, and at least two of them are the same project (#6/#8); **the true figure is higher** all the same. Six were found only because someone mentioned them in passing, and **#58 was not found at all until a moderator listed it on 2026-08-30** — direct evidence that the era-1 count is still a floor.
4. ~~**Role membership is not readable.**~~ **Answered 2026-08-30 for 41 crowdfunds.** Discord still does not expose role-member counts to a member account, but a moderator can read the confirmed channel's membership and supplied it. "How many people hold the Lioness role" was bounded at ≥275; it is **435**. See §5.
5. ~~**The coverage caveat.**~~ **Retired for votes, kept for delivery, 2026-08-30.** §4 is the population — 58 crowdfunds. **§5's vote table covers 40** and destination **47**, after a moderator supplied the figures a role would have exposed. **The delivery table is still 11**, because a drop leaves no public trace and nobody tallies them the way they tally a vote. Quote the two with that difference in mind; they no longer have the same reach.

### How the last five names were recovered

The write-up's own prescription — *adjacent communities remember what a self-deleting channel does not* — is what named #28 in 2025. It named none of these five, and the reason is worth recording: **there is no adjacent community left to ask.** All 85 guilds readable from this account were checked by channel listing, and exactly **two** are GRB communities — Tier 1 Imports and The Bivouac. The Bivouac's GRB traffic thins through 2025 (*"Just go to Tier 1 Imports server, this one is dead"*, msg `1503318552331948113`) and it mentions no 2026 crowdfund at all. That avenue is exhausted, not untried.

What worked instead was **searching Tier 1 itself for people naming a crowdfund while it was running** — the same shape of evidence as the Bivouac quote, sourced from inside. Three query shapes did nearly all the work:

- **Author-scoped search.** `content=crowdfund` across the guild returns hundreds of Carl-bot autoresponses a month. Scoping the same query to the handful of members who answer *"what's live"* — moderators, and the modders themselves — cuts the noise to nothing and surfaces exactly the messages that enumerate open projects. One such message named three of the five at once.
- **Post-link search.** Searching for a crowdfund post's own URL finds every message that ever pointed at it. A deleted post keeps a stable id, so this bolts a name onto a *specific* crowdfund rather than onto a date — that is how #40 and #46 were pinned.
- **Tight windows around the announcement.** Reading `#shit-talk`, `#on-topic` and `#supporter-chat` in the hours after each `@everyone`. #41 and #46 were named within minutes by people reacting to the post.

Two indexing behaviours are worth knowing next time, both discovered here:

> **Discord's search index covers forwarded-message snapshots.** A forwarded crowdfund post carries the original's full text, and that text stays searchable in the forwarder's message **after the original is deleted** — while the bridge renders such a message as empty content, so it is invisible unless you search for words it does not appear to contain. Six of these exist in Tier 1. Pairing a fixed stem with a candidate word (`ANNOUNCING OUR NEXT CROWDFUND PROJECT` + `crye`) turns them into an **oracle**: each probe answers which forwards contain that word. All six resolved to crowdfunds that were already named (Op Chesthair, Lioness ×2, Crye Babies, Rangers Lead The Way), so the trick named nothing new — but it is the only known route to a deleted post's *verbatim* text, and it is worth re-running whenever new forwards appear.
>
> **Forum thread names are indexed too.** A message whose body is nothing but a URL matched a search for words that appear only in its thread's title. That is how #42's post link was found sitting inside a thread named for Step Brothers in Arms.

### Open questions

1. **How many System 1 crowdfunds were there really?** Answerable by anyone with access to `#crowdfund-projects-legacy` or `#crowdfund-votes`, or by a moderator with the audit log.
2. **#7 — the last unnamed crowdfund.** System 1, announced without a name, and named nowhere in public chat or in the moderator's list. (#3 was the other one and is now closed — it was the **MCX Spear LT**, which the 2026-08-24 pass had guessed at as one of three candidates in flight that month.) #7 is *"a new weapon done by none other [Modder B]"* (msg `1316621603978874991`) and is **absent from Modder B's own list of open buy-ins six days later** (*"There are still three projects available for buy ins, price ghillie, shadow company heavy and the latest gzw assortment"*, msg `1318754880512327691`), so it may have collapsed early — Modder B describes a crowdfund doing exactly that on 2024-12-19: *"the entire crowdfund for that has fallen short, had over 15 ppl vote yes and only a 4 ppl paid"* (msg `1319125305558040587`, said of the Shadow Company Heavy project). A member who was buying in that December could settle it in a sentence.
3. **Did the March 2025 leak cause the system change?** §2 flags this as inferred. A moderator could confirm or kill it in one sentence.
4. ~~**Full public/supporters split across all 57.**~~ **Closed 2026-08-30.** Destination is known for **47 of 58** and turnout for **40**, and the answer is roughly two thirds public. The route was not access — the role was declined on 08-25 — but **asking a moderator for the numbers rather than for the channels**, which is the distinction [`../meta/crowdfund-asks.md`](../meta/crowdfund-asks.md) was written around and is now the method's best evidence. What is still a sample of 11 is the **delivery** table.
5. **Is the role list readable another way?** The role name *is* the crowdfund name, so a single read of the guild's role list would have answered this whole session's question in one call — and would answer the System 1 question too, if those roles still exist. The Discord client caches **every** guild role, including ones the account does not hold; the bridge already reads that store to resolve role mentions but exposes no endpoint for the snapshot. One caution before anyone builds it: at least one crowdfund role has been deleted. #39's (`1466647776396836874`) renders unresolved in a message that mentions it, which is consistent with a moderator's *"when the CF ends we just delete the Unconfirmed role"* (msg `1459296798244868298`) going further than the unconfirmed half.

---

## Sources

All message IDs above are in guild `1302392670181916722`. Principal channels:

| Channel | ID | Role in this research |
| --- | --- | --- |
| `#announcements` | `1313278397484371968` | The only complete chronology; read end to end |
| `#crowdfund-projects` | `1399641218610233427` | Live posts + 👍 counts; self-deleting |
| `#on-topic` | `1302392670181916725` | Where the systems get explained to newcomers |
| `#supporter-chat` | `1302779485543727144` | Pricing model, leak fallout |
| `#kingslayer-polls` | `1467966546251878634` | The Tier 1 → Kingslayer rename poll |
| `*-confirmed` set | see [§5](#5-what-the-numbers-show) | Release votes |
