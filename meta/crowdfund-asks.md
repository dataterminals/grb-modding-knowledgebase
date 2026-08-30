# Crowdfund research — what to ask, and who to ask

*Written 2026-08-30. Companion to [`../reference/crowdfund-history.md`](../reference/crowdfund-history.md)
and lane 3 of [`next-session.md`](next-session.md).*

A read-only role covering the paid channels was proposed to two staff members on 2026-08-25 and
**declined** — see next-session lead 4, and **do not re-pitch it**. What remains are *questions*
rather than permissions, and they split cleanly into two kinds:

- **A moderator can look at things nobody else can see** and say what is there. That is not access;
  it is a lookup. Section A.
- **A modder knows the answer about their own project** without looking anything up. Section B.

Both are bounded, and neither asks anyone to share a file, a channel, or a mod.

> **⚠️ Frame every ask as a fact, never as content.** *"Where did Konni Group end up — public or
> supporters?"* is a trivia question. *"Can you tell me about your crowdfund"* reads as *"can I have
> it"*, especially in a server built around paid access. The distinction is the whole reason these
> asks are viable when the access ask was not.

> **On names.** This file keeps the repo's Modder A–R pseudonyms, as the crowdfund prose does. The
> handle for each is on the [live panel](https://dataterminals.github.io/t1-crowdfunds/), matched by
> catalogue number. Activity is described coarsely and deliberately — who is around is a fair thing
> to weigh before asking someone a question, and not a thing this repo should publish a timeline of.

---

## Before either list — do not ask for what is already known

- **All 34 System 2 crowdfunds are named.** Only **#3** and **#7** are unnamed, both System 1.
- **11 crowdfunds have full vote + delivery data** — see §5. Do not re-ask those.
- **Destination is now known for 45 of the 57** (swept 2026-08-30 — §5, *Where the mods actually
  went*). **Do not ask where a crowdfund went unless it is one of the four with no answer: #3, #7,
  #10, #16.** What is still missing everywhere except the readable 11 is **turnout** — the vote
  tally — which is the harder thing to ask for and the less interesting answer.
- **Sign-up counts for closed crowdfunds are gone permanently.** No lookup recovers a deleted
  message. Do not ask; ask A8 instead.

---

## A. For a moderator — eyes-on lookups

Ordered by what they settle per second of someone's time. Each is a *look and tell me*, not a grant.

| # | Where to look | What to report back | What it settles | Effort |
| --- | --- | --- | --- | --- |
| **A1** | Server Settings → **Roles** | The list, pasted or screenshotted | Cross-checks all 34 System 2 names against the roles they were named after, exposes any crowdfund missing from the catalogue entirely, and confirms or refutes §3's claim that **System 1 had no per-project roles** | ~30 s |
| **A2** | **`#crowdfund-projects-legacy`** (`1302441788585279570`) | How many crowdfund posts it holds, and their **titles and dates** | ⭐ **The biggest open question in the file.** System 1 currently stands at 23 rows / 22 distinct projects and is *known to be a floor* — six of them were found only because someone mentioned them in passing. This is the only place the real number lives | ~5 min, screenshots fine |
| **A3** | **`#crowdfund-votes`** (`1303906293219856477`) | The list of vote posts — titles and dates | Same question from the other side, so it cross-checks A2 rather than duplicating it. Era-1 votes should also **name #3 and #7** | ~5 min |
| **A4** | Either of the above, targeted | Two specific answers: what was the project **by Modder D announced 2024-11-23** (`1309770589795520592`), and what was **Modder B's "new weapon" announced 2024-12-12** (`1316621603978874991`) | The last two unnamed crowdfunds in the catalogue | ~1 min if A2/A3 are already open |
| **A5** | The crowdfund **category** (`1310270708303138816`) | The `*-confirmed` channel names, and whether the `*-unconfirmed` channels sit in the **same** category or a different one | A second independent check on every System 2 name, plus a structural fact the write-up currently infers from 11 visible channels | ~1 min |
| **A6** | Their own memory | Did the **March 2025 leak** cause the move to the reaction-role system? | §2 flags this as **inferred** — the leak and the changeover are adjacent in time and theme and *no message states a cause*. One sentence from anyone who was staff then closes it either way | ~1 min |
| **A7** | Their own memory | Are crowdfund posts **deleted deliberately** when a project closes, or was there a one-off purge? | §7 calls the mechanism **unestablished**. Two of the posts on the board are months past their stated end date and still up, which argues against rolling removal but does not settle it | ~1 min |
| **A8** | — | Nothing to look at: a **request**. Sign-up counts die with the post, so if posts stay up — or if `tools/refresh.py` is simply left running on a schedule — the numbers stop being lost from here on | The one gap that closes itself. Costs nobody anything and grants nobody anything | — |
| **A9** | Each `*-confirmed` channel | The release-vote poll result — **two numbers** | Would extend §5's turnout table past 11. ⚠️ **~46 channels, so do not lead with this.** Only worth raising if someone volunteers, and then take the largest crowdfunds first | high |

---

## B. For the modders — one question about their own project

**Rewritten 2026-08-30.** The destination sweep answered *where it went* for 45 of 57 without
anyone being asked, so this list is no longer about that. What is left for a modder to answer is
**turnout** — *"roughly how many people voted on it, and which way?"* — plus the four crowdfunds
with no destination at all. Turnout is the harder ask and the duller answer, so treat this list as
lower priority than section A, and lead with the two rows marked ⭐.

| Modder | Crowdfunds with no turnout figure | Around? | Notes |
| --- | --- | --- | --- |
| **Modder B** | **#1, #7, #10, #15, #16, #19, #23, #26, #43** | active | ⭐ **By far the highest-value single conversation** — nine crowdfunds, a quarter of everything the server has run. Three separate things only this person can settle: the **name of #7**, and the **destination of #10 and #16**, the only two closed crowdfunds with no public trace at all |
| **Modder J** | #18, #21, #25, #28 | quiet since spring | Four, including **#28 Steyr**, whose name we only have via The Bivouac |
| **Modder E** | #2, #6, #8 | active | Also the one person who can confirm the **#6 ≡ #8** inference — that the GZW assortment and the "new gear pack" are one crowdfund counted twice. That is currently our strongest *inferred* claim in System 1 |
| **Modder A** | #9, #11 | quiet since spring | #38 is already measured, so this is a short conversation |
| **Modder G** | #13, #20 | around recently | — |
| **Modder I** | #17, #24 | occasionally | Both destinations known; turnout only |
| **Modder K** | #22, #41 | active | Both destinations known; turnout only |
| **Modder L** | #39, #46 | active | Both recent, both his own, both already named by his own posts |
| **Modder O** | #40, #45, #52 | active | Plus #56, live. **#45 Wolf Pack was attributed to them on 2026-08-30** (msg `1502850378373271692`), which makes five crowdfunds — level with Modder L |
| **Modder M + Modder R** | #42 | both active | The tag-team crowdfund; either could answer |
| **Modder N** | #48 | active | Plus #57, live |
| **Modder H** | #14 | long quiet | Lowest expected reply rate; one crowdfund |
| **Modder D** | **#3** | referenced in chat as recently as this week, but their account could not be resolved from this member account | ⭐ Holds a **name and a destination** — #3 has neither, and no public trace. The only person who can settle it short of A2/A4 |

### Six crowdfunds have no creator recorded at all

**#4, #5, #12** (System 1) and **#44, #49** (System 2) — five, since **#45 was attributed to
Modder O** on 2026-08-30. These need *attribution* before there is anyone to ask, so they belong
with A1/A2/A5 or with any long-standing member. #12 additionally carries the open question of
whether it is the same project as #10.

### Suggested wording

> Hey — I keep a public archive of every Tier 1 crowdfund (dates, who ran them, where the mods ended
> up). It's at <https://dataterminals.github.io/t1-crowdfunds/> and you're credited on it. I've got
> **\<name\>** in there but no idea how big the vote was — do you remember roughly how many people
> voted, and which way it went? Not after the files, just the numbers.

Short, one question, names what it is for, and makes clear it is not a request for content.

---

## Do not ask for

- **Read access to the `*-confirmed` channels, in any form.** Asked and declined 2026-08-25. A
  second, larger pitch would get a firmer no and would spend goodwill that sections A and B need.
- **Anything from the `*-unconfirmed` channels.** They are the payment channels and hold
  proof-of-payment screenshots — a moderator disabled images there on 2026-03-20 *"because users
  keep on posting personal info in their crowdfund payment posts"* (msg `1484600258473496628`).
  Nothing the archive needs is in them.
- **Mod files, exclusives, or armoury content.** The archive records *that* something exists and
  where it went. It has never needed the thing itself, and asking would recast every question above
  as an attempt to get paid content for free.
