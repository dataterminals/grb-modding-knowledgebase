# Tier 1 Imports crowdfunds — the two systems, and the catalogue

> **Live panel:** <https://dataterminals.github.io/t1-crowdfunds/> — the same dataset, kept current, with the registry sortable and filterable. This file is the narrative and the citations; the panel is the living view.
>
> **Status:** First comprehensive pass, 2026-08-23. Compiled by reading *Tier 1 Imports* (guild `1302392670181916722`) directly through an authenticated Discord bridge as `@blkdnm`. Every claim below cites the message it came from. Provenance: [`../meta/research-log.md`](../meta/research-log.md).

## Why this is in a modding knowledgebase

A large fraction of the mod corpus catalogued in [`../examples/mod-catalog.md`](../examples/mod-catalog.md) is **crowdfund output**, and the folder names say so out loud:

| Corpus folder | Crowdfund it came from |
| --- | --- |
| `CFLIONNESS_JPCVest`, `CFLIONNESS_BangerJPC`, `CFLIONNESS_CondorTop`, `LIONNESS_Jeans`, `LIONNESS_RolledSlimShirt` | **Lioness** (`CF` = CrowdFund) |
| `Acosta - The Bison Belt - Ferro Concepts`, `acostabisonbattlebelt_*`, `bisonbelt_datapc` | **Tip of the Spear** (Acosta) |
| `AKM_KYPK` | **AKM w/ KPYK parts** |
| `Kalashnikova_SR1` | **Kalashnikov SR1** |
| `SA58` | **DS Arms SA 58 FAL** |
| `Vans Defcon - uormomchesthair`, various `Crye AVS` / `Crye JPC` variants | YourMomsChestHair crowdfunds |

So "where did this mod come from, and why can't I find it on Nexus?" is a **provenance question this file answers**. A mod that went to the supporter armoury instead of public release is not lost — it was a crowdfund that voted the other way. See §5.

This file documents the **funding and distribution system**, not the modding pipeline. Nothing here touches game files.

---

## 1. The short answer

Tier 1 Imports has run **at least 55 crowdfunds** since the server was founded on **2024-11-02**, under **two distinct systems**:

| | **System 1 — "buy-in"** | **System 2 — "Smiley's way"** |
| --- | --- | --- |
| **Ran** | 2024-11 → 2025-07 | 2025-07-29 → present |
| **Announced in** | `#crowdfund-projects-legacy`, `#crowdfund-votes`, sometimes `#on-topic` | `#crowdfund-projects` (`1399641218610233427`) |
| **How you opted in** | Vote in `#crowdfund-votes`, or DM the modder | React 👍 on the announcement post |
| **Price** | **Variable** — set per project by scope/asset cost ($5–$10+) | **Flat $10 minimum**, more accepted |
| **Access control** | Manual — a modder adds you to a channel | **Automated reaction-roles** via T1 Carl |
| **Channels per project** | One project channel (+ a confirmation channel by mid-2025) | **Two:** `#<name>` (unconfirmed) → `#<name>-confirmed` |
| **Roles per project** | None | **`<Name> unconfirmed` → `<Name>`**, both visible on your profile |
| **Reward tier** | "Tier 1 Armory", later "Tier 2" | **Supporter** (renamed from Tier 2, 2026-03-24) |
| **Named crowdfunds recoverable** | **23** (floor — see §6) | **32** (believed complete) |

The user's recollection is correct on every point: the second system is roles, unconfirmed→confirmed, and the paid-up role showing on your profile in the server.

---

## 2. System 1 — the "buy-in" era (2024-11 → 2025-07)

> **Verified:** The server was built *for* this. On its first full day, founder **McC00CHIEMAN** wrote: *"my idea for this server was to have this be a storefront of sorts for crowdfunding mod projects"* (`#on-topic`, msg `1302414873325604945`, 2024-11-02). The guild snowflake dates creation to the same day.

### The pricing model

Crowdfunds started as **split commissions**, not a flat fee. **YourMomsChestHair**, `#supporter-chat`, 2024-11-03:

> "i was thinking for pricing those for guns at 60$ with $5 buy ins minimum of 12 confirmations" (msg `1302780729121570906`)
> "full model imports as well like logans $100 for the full with $10 buy ins" (msg `1302781232068825260`)

So the buy-in was **a share of the modder's commission price**, and the project needed a **minimum number of participants** to go ahead. That is the single biggest structural difference from System 2, where $10 is a floor rather than a share.

> **Verified:** Amounts genuinely varied per project as late as May 2025 — *"its a dope mod and the min buy in is $5"* (msg `1371750407612665856`), against $10 elsewhere. **SexyCouchPotato** confirms the rule: *"There is a minimum buy in depending on the scope of the project or costs of the assets"* (msg `1384961275628490754`, 2025-06-18).

### The flow

1. A project is announced (`#announcements` `@everyone`, or `#on-topic`, pointing at `#crowdfund-projects-legacy`).
2. You **vote in `#crowdfund-votes`** (`1303906293219856477`) to opt in. *"if you want to 'buy-in' go vote in #crowdfund-votes"* (msg `1307805326631768124`).
3. You are **manually added** to the project channel, which carries the payment link.
4. You pay the modder directly — **PayPal** was standard (msgs `1369279409374232586`, `1437621881313431694`).
5. Once the modder confirms payment you are added to a **confirmation channel** (msg `1384961275628490754`).
6. At the end, **buyers vote** whether the mod goes public or stays private (msg `1312514949058400346`).

> **Verified:** The public/private release vote — the mechanic that still runs today — existed from the very first weeks. **wognog**, 2024-11-30: *"at the end of every crowd fund there's a vote held for the people who bought in for it to stay private or be released"* (msg `1312514949058400346`).

### The flake problem, and the leak

Non-payment was a problem from the start. **McC00CHIEMAN**, 2024-12-02 (msg `1313256555994681406`):

> "we've been having issues with people not following through with committing to the 'buy-ins' WITHOUT TELLING US THEY NO LONGER WISH TO 'BUY-IN'. If you continuously vote to 'buy-in' for a CROWDFUND and don't communicate that you no longer want to, you WILL be kicked from the server."

Then, in March 2025, someone leaked paid mods:

> "Basically an edgelord tried to leak buy in mods" — DA 𝕃𝕒𝕜𝕖𝕣_Man𝟚𝟛𝟚, `#on-topic`, msg `1352106850715308134`, 2025-03-19

YourMomsChestHair posted *"Im halting all buy ins atm"* the same day (msg `1351884110330859531`). SamiPuma, days later: *"we don't really know what the rules are yet, all of this is new, we're really jus trying to make sure the people from going into T1 wont be trying to leak stuff"* (msg `1353223879530647574`).

> **Inferred:** The March 2025 leak is a plausible driver of the move to per-project roles and auditable confirmed/unconfirmed state. **No message states this causally** — the two are adjacent in time and theme, nothing more. Treat as hypothesis.

---

## 3. System 2 — "Smiley's way" (2025-07-29 → present)

> **Verified:** The changeover is dateable to **2025-07-29**. `#crowdfund-projects` (`1399641218610233427`) is created, the old channel is renamed to `#crowdfund-projects-legacy`, and **SMilEY** posts the first announcement in the new format (msg `1399642502708858933`). SMilEY had taken over `@everyone` duty one day earlier (msg `1399335541346140210`, 2025-07-28).

> **Verified:** There was **no announcement of the change itself.** The entire `#announcements` channel was read end to end (94 messages, 2024-12-03 → 2026-08-19); it contains no "new crowdfund system" post. The system simply appeared as a new channel with a new post format.

### The flow, as the community explains it

The canonical description, **BlackWolf025** in `#on-topic`, 2025-08-26 (msg `1409849246219370558`):

> "react to the project that interests you, and you'll be added to an 'unconfirmed' channel which shows that you're interested in the mod and you intend to fund the project. Once funds are confirmed by the modder, you'll be added to the 'confirmed' channel for that mod and receive early/exclusive access to that project's mods."

And **Makiatto**, 2025-11-12 (msg `1438273489294459001`):

> "When you click the emoji you get the (CF name) unconfirmed role, once you pay and show proof of payment you get the actual role and access to the respective channel"

So, precisely:

| Step | What you get |
| --- | --- |
| React 👍 on the post | Role **`<Name> unconfirmed`** → access to the unconfirmed channel |
| Read the unconfirmed channel | The modder's PayPal link / preferred payment method |
| Pay + post proof | Modder swaps your role for **`<Name>`** → access to `#<name>-confirmed` |
| Automatically, with the first one | **Supporter** role — permanent, one crowdfund is enough |

> **Verified:** Roles come in **channel pairs created seconds apart**. Crowd Control's unconfirmed channel is `1436320079779201145` and its confirmed channel is `1436320209735778396` (msg `1436644451639361586`, which links both). The `-confirmed` suffix in the channel list is therefore the *paid* half of a pair.

> **Verified:** The reaction-role automation is **T1 Carl** (Carl-bot, account `235148962103951360`). It is the sole bot reactor on every crowdfund post — see §5.

### Why the roles are visible, and why that matters

The per-project roles are **public on your profile in the server**, and the community reads them. Examples:

- *"btw do you know that you have 4 unconfirmed crowdfund tags?"* — Ethan0403 (msg `1441914698940284990`)
- *"Seeing as you're unconfirmed for two projects, you're not off to a good start."* — BlackWolf025 (msg `1432329575764856934`)
- *"It just gets annoying with how many 'unconfirmed' roles that I come across for projects that have been released for months."* — BlackWolf025 (msg `1442081888226246750`)

> This is the system's real innovation. System 1 had a flake problem it could only address by threatening bans. System 2 makes flaking **permanently legible on the flake's own profile**, and enforcement becomes social rather than administrative. BlackWolf025 even proposed formalising it: *"if you go unconfirmed throughout a project and release … you should forfeit the access to that project altogether"* (msg `1442079358293508186`, 2025-11-23).

### The tier roles

| Role | How you get it | Notes |
| --- | --- | --- |
| **Supporter** | Support any one crowdfund, ever | Was **"Tier 2"**. Grants `#supporter-chat`, `#supporter-armory`, `#supporter-polls`. Permanent. |
| **Kingslayer** | Given, not earned or bought | Was **"Tier 1"**. Grants `#kingslayer–armory`, `#kingslayer-polls`. |

> **Verified:** T1 Carl's canned explainer (msg `1486172833552928954`): *"The supporter role is granted to users that have helped the Tier 1 team make mods via supporting crowdfunds… The Kingslayer role is for members who have been around a while, supported projects or just generally had a good influence on the community. This isn't a level up system, you don't 'earn' the roles, they're given as they're given."*

> **Verified:** "Tier 1" was renamed to **Kingslayer** on **2026-03-24** by community poll — 149 votes: Kingslayers 81, Vanguard 40, Pathfinders 26, The Bulwark 2 (`#kingslayer-polls`, msg `1485007498162475028`; result msg `1486094687105318985`; SMilEY's *"~~Tier 1~~ Kingslayer"* msg `1486095571730042960`).

> **⚠️ Naming trap for anyone reading old messages.** The tier labels **swapped meaning** during System 1. In March 2025 SamiPuma described the crowdfund reward as the *"Tier 1 Armory"* (msg `1347339972801466430`); by May 2025 the same reward was *"Tier 2"*, with Tier 1 as the earned role (msg `1375616498579800065`). Pre-mid-2025 references to "T1 Armory" usually mean **what is now the Supporter armoury**.

---

## 4. The catalogue

### System 1 (2024-11 → 2025-07) — 23 recovered, **not complete**

Entries marked ★ were announced only in chat and have **no `@everyone`**, which is why any count built from `#announcements` alone undercounts this era.

| # | Date | Crowdfund | Creator | Source |
| --- | --- | --- | --- | --- |
| 1 ★ | ≤2024-11 | **Night War Ghost** full outfit | YourMomsChestHair | First completed crowdfund; released public, Nexus mod 1090 (msg `1310097291587223553`) |
| 2 | 2024-11-17 | **Alex "Echo 3-1"** gear pack (CoD MW19) | YourMomsChestHair | msg `1307805326631768124` (`#on-topic`) |
| 3 ★ | 2024-11-23 | *(unnamed project by **SB-4**)* | SB-4 | msg `1309770589795520592` |
| 4 ★ | 2024-12-02 | **Shadow Company Heavy Outfit** | — | msg `1313256555994681406`; $10 buy-in |
| 5 ★ | ≤2024-12 | **Price Ghillie** | — | msgs `1318754880512327691`, `1350822574468370493` |
| 6 ★ | ≤2024-12 | **GZW assortment** | — | msgs `1318754880512327691`, `1322527000925307053`; stayed private over asset copyright (`1349505166176555060`) |
| 7 | 2024-12-11 | *(unnamed new weapon)* | YourMomsChestHair | msg `1316621603978874991` |
| 8 | 2024-12-16 | *(unnamed gear pack)* | FlawlyBoy | msg `1316829668674109511` |
| 9 | 2024-12-29 | **Daniel Defense DDM4V7** | `506427314301566976` | msg `1322878300007174144` |
| 10 | 2025-01-14 | **Shadow Rusher** outfit | YourMomsChestHair | msg `1328857878152613940` |
| 11 | 2025-01-21 | **Chimera Bridge** | `506427314301566976` | msg `1331300784599728188` |
| 12 ★ | ≤2025-03 | **SC Wolves / Wolves Overhaul** | — | msgs `1347339972801466430`, `1350547784788344943` |
| 13 | 2025-03-12 | **MCX Raptor** | `335527074079047680` | msg `1349440792007278703` |
| 14 | 2025-03-29 | **Australian SOF Vests** | `781897007043837952` | msg `1355682150719951068` |
| 15 | 2025-04-08 | **Ferro Concepts Slickster Plate Carrier** | YourMomsChestHair | msg `1359291748144119898` |
| 16 | 2025-04-13 | **Next Generation Ghost's Gear** | YourMomsChestHair | msg `1360895696894693396` |
| 17 | 2025-05-06 | **Konni Group Outfits** | `779221619892813854` | msg `1369345583709552750` |
| 18 | 2025-05-08 | **Kalashnikov SR1** | Agent/07 | msg `1370159031775268944` |
| 19 | 2025-05-15 | **"Warfare" movie outfits** | YourMomsChestHair | msg `1372703221805481984` |
| 20 | 2025-06-13 | **BREN 3** | `335527074079047680` | msg `1383200543043883179` |
| 21 | 2025-06-19 | **Haenel MK556** | Agent/07 | msg `1385507734392406037` |
| 22 | 2025-07-05 | **DS Arms SA 58 FAL** *(renewal)* | ᴇ Δ ᴡ ᴇ ʟ ʟ | msg `1391022434211069993` |
| 23 | 2025-07-08 | **Commando Diving Drysuit**, a.k.a. **"Frogman"** | YourMomsChestHair | msg `1392009113185030288`; "Frogman" per msgs `1398318235249672334`, `1399101991619399801` |

> **Inferred:** #12 may be the same project as #10 — SamiPuma linked channel `1328856903996018828` (created the same day as the Shadow Rusher announcement) while calling it *"the SC Wolves outfits"*. Both are Shadow Company content. Not resolvable without access to that channel; listed separately with the ambiguity flagged.

### System 2 (2025-07-29 → present) — 32, believed complete

Every entry has a dated `@everyone` in `#announcements`. Names in *(parentheses)* could not be recovered — see §6.

| # | Date | Crowdfund | Creator |
| --- | --- | --- | --- |
| 24 | 2025-07-29 | Vulcan/Malyuk 7.62 Assault Rifle | `779221619892813854` |
| 25 | 2025-08-14 | AKM w/ KPYK parts | Agent/07 |
| 26 | 2025-08-18 | White Moon | YourMomsChestHair |
| 27 | 2025-09-17 | **Snake Eater** | YourMomsChestHair |
| 28 | 2025-09-23 | **Steyr** | Agent/07 |
| 29 | 2025-10-13 | **Operation Mother's Chest Hair** | YourMomsChestHair |
| 30 | 2025-11-07 | **Crowd Control** *(Mercer's debut)* | MercerBlack™ |
| 31 | 2025-11-09 | **Enfield Tea Set** | — |
| 32 | 2025-11-19 | **Bad Boys** | YourMomsChestHair |
| 33 | 2025-11-21 | **Dual Sig** | — |
| 34 | 2025-12-15 / 20 | **Door Kicker** | — |
| 35 | 2025-12-17 | **Lioness** | YourMomsChestHair |
| 36 | 2025-12-15 / 20 | **Kill Confirmed** | ViruS |
| 37 | 2026-01-06 | **Ahead of Your Time** | SAMI TECH SUPUMA |
| 38 | 2026-01-18 | **Tip of the Spear** | Acosta. |
| 39 | 2026-01-30 | *(unnamed — Mercer, 🇿🇦)* | MercerBlack™ |
| 40 | 2026-02-11 | *(unnamed)* | — |
| 41 | 2026-02-17 | *(unnamed — "cold pasta")* | — |
| 42 | 2026-02-23 | *(unnamed)* | — |
| 43 | 2026-02-27 | **Crye Baby** | YourMomsChestHair |
| 44 | 2026-03-27 | **Spirited Away** | — |
| 45 | 2026-03-31 | **Wolf Pack** | — |
| 46 | 2026-04-07 | *(unnamed — Mercer, "FW" monogram)* | MercerBlack™ |
| 47 | 2026-04-12 | **CYBERSAMI** 🔴 *still posted* | SAMI TECH SUPUMA |
| 48 | 2026-05-11 | **Smokin Aces** | keem |
| 49 | 2026-05-15 | **Breach & Clear** | — |
| 50 | 2026-06-01 | **Heavy Metal** 🔴 *still posted* | MercerBlack™ |
| 51 | 2026-06-12 | **Pastaslov** | ᴇ Δ ᴡ ᴇ ʟ ʟ |
| 52 | 2026-06-13 | **Time 'n Tide** | 𝐵𝑂𝑁𝐹𝐼𝑅𝐸 ("Bon") |
| 53 | 2026-07-03 | **Rangers Lead The Way** | urmomschesthair |
| 54 | 2026-07-11 | **GWOT Classics** | ViruS |
| 55 | 2026-08-19 | **Dealer's Choice** 🔴 *open* | Avetis |

> Names for #43–#45, #48, #49 and #52 were recovered by **reading the announcement title-card graphics** posted in `#announcements` — the artwork spells the name out where the surviving text does not.

---

## 5. What the numbers show

### Sign-ups on the six posts still on the board

Read 2026-08-23 with a reactor expansion, so these are **exact reactor lists, not just counts**. T1 Carl seeds the 👍 on every post, so the human figure is the raw count minus one.

| Crowdfund | Raw 👍 | Humans | Min. committed @ $10 |
| --- | ---: | ---: | ---: |
| Rangers Lead The Way | 385 | **384** | $3,840 |
| GWOT Classics | 318 | **317** | $3,170 |
| CYBERSAMI | 198 | **197** | $1,970 |
| Heavy Metal | 173 | **172** | $1,720 |
| Pastaslov | 132 | **131** | $1,310 |
| Dealer's Choice *(4 days old)* | 118 | **117** | $1,170 |

### Backer overlap — the interesting part

Across those six posts: **812 distinct people, 1,318 sign-ups.**

| Signed up for | People | Share |
| --- | ---: | ---: |
| 6 of 6 | 14 | 1.7% |
| 5 of 6 | 30 | 3.7% |
| 4 of 6 | 20 | 2.5% |
| 3 of 6 | 59 | 7.3% |
| 2 of 6 | 138 | 17.0% |
| **1 of 6** | **551** | **67.9%** |

> **Verified:** The backer base is **wide and shallow — 68% one-and-done.** A crowdfund is not funded by a fixed subscriber core; each one recruits largely fresh. Dealer's Choice drew **37 of its 117 backers (32%) from people who appear on none of the other five**, four days in. Only **14 people of 812** are on all six.

### Release-vote turnout — a hard floor on paid supporters

The public/supporters vote runs inside the **confirmed** channel, so **only people who paid can see or cast it.** Turnout is therefore a floor on that project's paying membership. Readable for the 11 projects this account holds:

| Crowdfund | Turnout | Public | Supporters | Released to |
| --- | ---: | ---: | ---: | --- |
| Lioness | **275** | 132 | 143 | Supporters |
| Tip of the Spear | 149 | 84 | 65 | Public |
| Op Chesthair | 144 | 97 | 47 | Public |
| Ahead of Your Time | 103 | 43 | 60 | Supporters |
| Snake Eater | 99 | 59 | 35 (+5 private) | Public |
| Bad Boys | 72 | 32 | 40 | Supporters |
| Dual Sig | 61 | 22 | 39 | Supporters |
| Kill Confirmed | 58 | 27 | 31 | Supporters |
| Enfield Tea Set | 55 | 42 | 13 | Public |
| Crowd Control | 54 | 22 | 32 | Supporters |
| Door Kicker | 48 | 17 | 31 | Supporters |
| **Total** | **1,118** | | | **4 public / 7 supporters** |

Mean 102, median 72, range 48–275. All tallies finalized.

> **⚠️ Read the scope before reading the outcome.** The vote does not always cover the whole crowdfund. **Snake Eater's** poll asked *"Where to share the XOF Outfits?"* — one item — and SMilEY says so in-channel: *"MOST of the items in this crowdfund are supporter items, the XOF suit is what will be made public from this crowdfund"* (msg `1426355642410467368`). **Bad Boys'** was scoped to *"the Exfil Helmets, Police Vests and Belt"*. The other nine read as whole-project. So "4 public / 7 supporters" describes **the voted portion**, not the crowdfund.

### The four places content actually ends up

| Destination | Who can reach it | Notes |
| --- | --- | --- |
| **Public** | Anyone | `#mod-releases`, usually Nexus too. |
| **Supporter armoury** | Anyone who has backed *any* crowdfund | `#supporter-armory`. Called the **Tier 2 Armory** until March 2026 — and the **Tier 1 Armory** before that. |
| **Crowdfund exclusive** | Backers of that one crowdfund | Never leaves the crowdfund's own channel. *"Exclusives don't go public they are a treat from the modders to the people that contributed to the CF"* — Shadadi_, msg `1498457727851298858`. |
| **Private** | Nobody further | An option on Snake Eater's poll (5 votes). Has never won. |

> **Not a crowdfund destination:** the **Kingslayer armoury** (`#kingslayer–armory`). That is the *earned* role's own track — modders post there directly, threads titled *"Kingslayer Exclusive"* (e.g. *HK416D SMR | Final Edition | Kingslayer Exclusive*). Nothing arrives there by crowdfund vote. It is easy to confuse with the supporter armoury precisely because the latter used to be called "Tier 1 Armory".

### The vote is not the end of it

> **Verified:** every one of the 11 measurable crowdfunds kept delivering **after** its vote — **198 separate drops in total**, a median of **64 days** from first to last.

| Crowdfund | Drops | Window | Principal creator |
| --- | ---: | ---: | --- |
| Operation Mother's Chest Hair | 39 | 64 d | YourMomsChestHair |
| Ahead of Your Time | 36 | 141 d | SAMI TECH SUPUMA |
| Door Kicker | 18 | 57 d | MercerBlack™ |
| Lioness | 18 | 32 d | YourMomsChestHair |
| Snake Eater | 16 | 169 d | YourMomsChestHair |
| Crowd Control | 15 | 94 d | MercerBlack™ |
| Dual Sig | 13 | 189 d | 𝐵𝑂𝑁𝐹𝐼𝑅𝐸 |
| Kill Confirmed | 13 | 35 d | ViruS |
| Tip of the Spear | 13 | 70 d | Acosta. |
| Bad Boys | 11 | 25 d | YourMomsChestHair |
| Enfield Tea Set | 6 | 48 d | Gazza2764 |

**Each creator distributes differently**, which is why a single house format cannot be counted on: **MercerBlack** keeps one Google Drive folder and updates it in place (*"All mod files and updates will be in the Gdrive, as usual"*); **𝐵𝑂𝑁𝐹𝐼𝑅𝐸** ships versioned drops (MPX V1 → V1.1 → V2.0); **YourMomsChestHair**, **ViruS**, **SAMI TECH SUPUMA** and **Acosta** post discrete `MOD RELEASE` items.

> **Method caveat:** a "drop" is a post from the crowdfund's principal creator carrying a download link or a replacement statement. An earlier count keyed on the literal `MOD RELEASE` heading and scored Crowd Control, Enfield Tea Set, Dual Sig and Door Kicker as **zero** — all four had in fact delivered, in other formats. That was a measurement artefact and is corrected here.

### Cadence

| Period | Months | Crowdfunds | Rate |
| --- | ---: | ---: | ---: |
| System 1 | ~9 | 23+ | ≥2.6 / mo |
| System 2 | ~13 | 32 | 2.5 / mo |

**Creator concentration:** YourMomsChestHair leads ~14 of the 32 System 2 projects (~29% of all crowdfunds), including the largest on record (Rangers Lead The Way, 383).

---

## 6. Where Tier 1 Imports came from

Tier 1 Imports was created **2024-11-02**. It did not appear out of nothing: **The Bivouac** (guild `981599102523539466`), a Ghost Recon: Breakpoint modding community running since **mid-2022**, is where much of its early membership already was.

> **Verified — the two servers are directly linked in the record:**
>
> | Date | Event | Source |
> | --- | --- | --- |
> | 2024-11-02 | Tier 1 Imports created. Day one, its founder states the plan: *"my idea for this server was to have this be a storefront of sorts for crowdfunding mod projects."* | T1 msg `1302414873325604945` |
> | 2024-11-06 | The Bivouac's ownership transfers to **Sixthburrito**. The announcement names no outgoing owner and signals no conflict. | Bivouac msg `1303731106599796817` |
> | 2024-11-08 | **McC00CHIEMAN** posts into the Bivouac's `#grb-talk`: *"I'm the co-creator of Tier 1 Imports"*, with an invite link. He is not removed for it. | Bivouac msg `1304532626023120966` |
> | 2024-11-23 | **ViruS**, from inside the Bivouac, routes people to Tier 1 for crowdfunds: *"check nexusmods, put up a comission here, or make a request for a crowdfund mod … over at the tier1 server."* | Bivouac msg `1309919966497214525` |
> | 2026-05-11 | *"Just go to Tier 1 Imports server, this one is dead."* The Bivouac still exists but is largely inactive. | Bivouac msg `1503318552331948113` |

Several people who became Tier 1 regulars were active Bivouac members at the time — ViruS, DA 𝕃𝕒𝕜𝕖𝕣_Man𝟚𝟛𝟚, SamiPuma, Seven, ryan1662, wabbit, Ransu.

### The difference that actually matters

> **Verified:** The Bivouac's channel list still carries `#request-commission` and `#commission-guidelines`. It runs **commissions** — one person pays one modder for one job. Tier 1 was built, on its first day, to **split that cost across many people**. That is what a crowdfund is, and it is the structural reason the second server exists.

> **Inferred / unresolved:** whether Tier 1 was a deliberate *split* from The Bivouac. The founding, the ownership handover and the open recruitment all fall inside one week, which is suggestive — but **no message states a cause**, and the recruitment being public and tolerated argues against an acrimonious break. A long-standing member of either server could settle this in a sentence; the record cannot.

---

## 7. What could not be recovered, and why

> **⚠️ `#crowdfund-projects` does not keep its history.** The channel holds **six posts**, the oldest from 2026-04-12. Everything older is gone: `before=` paging and `around=` jumps both return nothing, and roughly 20 `@everyone` posts in `#announcements` still link to crowdfund posts that **no longer exist**.
>
> **Correction (2026-08-23):** an earlier draft of this file claimed CYBERSAMI and Heavy Metal were deleted between 2026-08-19 and 2026-08-23, and called that a direct observation. It was not — it was a `limit=4` query mistaken for the channel's full contents. Both posts are still on the board. **No deletion has actually been observed.** Whether posts are removed as projects close, or the channel was purged once in a cleanup, is **not established** — two of the six are months past their stated end date and still posted.

Consequences:

1. **👍 counts exist only for live crowdfunds.** For all 51 completed ones the commitment count is gone permanently. The figures in §5 are a four-project snapshot, not a history.
2. **Five System 2 crowdfunds cannot be named** (#39–#42, #46), plus three in System 1 (#3, #7, #8). Their date and often their creator are solid; the name died with the post. *(#28 was recovered on 2026-08-23 — see §7 — leaving eight unnamed in total.)*
3. **System 1 has no reliable count.** `#crowdfund-projects-legacy` and `#crowdfund-votes` (`1303906293219856477`) both return `forbidden` — as do individual System 1 project channels (`1370158615473946667` tested). The 23 in §4 are what could be reconstructed from public chat; **the true figure is higher.** Six of the 23 were found only because someone mentioned them in passing.
4. **Role membership is not readable.** Discord does not expose role-member counts to a member account, so "how many people hold the Lioness role" is bounded (≥275) but not known.

### Open questions

1. **How many System 1 crowdfunds were there really?** Answerable by anyone with access to `#crowdfund-projects-legacy` or `#crowdfund-votes`, or by a moderator with the audit log.
2. **The eight unnamed System 2 projects.** A member holding those roles would see the names immediately — the role name *is* the crowdfund name.
3. **Did the March 2025 leak cause the system change?** §2 flags this as inferred. A moderator could confirm or kill it in one sentence.
4. **Names from outside the server.** #28 was recovered by searching *The Bivouac*, not Tier 1 — a member there listing what was live on 2025-09-24: *"the Metal Gear Solid/XOF and the Steyr Crowdfund"* (msg `1420518885261836368`). Adjacent communities remember what a self-deleting channel does not; the remaining eight may be recoverable the same way.
5. **Full public/supporters split across all 55.** Only 11 are measurable from this account; a member with more roles could extend the table in §5 and turn the "two thirds stay private" estimate into a real figure.

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
