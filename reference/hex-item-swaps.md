# Reference — Hex item swaps (re-pointing 64-bit object references)

A whole class of GRB gameplay mods needs **no ATK export, no XML, and no art**: you open a record in a hex editor and overwrite an 8-byte object reference with a different object's ID. That's it. Swapping the bandage slot for a syringe, the thrown bullet casing for a strike designator, bullet drop for syringes — all the same edit.

> **Source:** *Tier 1 Imports* `#mod-tutorials` thread **"How to swap out bandage slot for another item (and do hex item swaps in general)"** by **spncryn** (message `1481311357134704753`, 2026-03-11), requested by *steven*; with a critical clarification from **Tenebrae** in-thread. Byte values quoted below are spncryn's, read directly from the post. Provenance: [`../meta/research-log.md`](../meta/research-log.md).

## Why this works (and what it confirms)

[`../docs/03-data-and-resources.md`](../docs/03-data-and-resources.md) establishes that GRB data is a graph of **64-bit file IDs**, and that a BuildTable is "essentially a node graph of references." DB records are the same idea: a container record holds the IDs of the objects it points at. **Change the ID, change what it points at.**

spncryn states the principle plainly:

> "bytes 1-8 … are the ID of the object. *This information is very important for nearly all hex-based editing.*"

The three IDs used in the worked example decode as **little-endian uint64**, and land squarely in the same magnitude range as `ClassID`s verified elsewhere in this KB:

| Object | Bytes | LE uint64 |
| --- | --- | ---: |
| `DBItemSetting_HealingItemEssence_Bandages.DBToolSetting` | `53 D0 C7 E7 64 01 00 00` | `1532896989267` |
| `HealingItemEssence_HealingSyringes.HealingItemEssence` (Mk. 1) | `51 77 EB 97 43 01 00 00` | `1389823227729` |
| `HealingItemEssence_HealingSyringesUpgraded.HealingItemEssence` (Mk. 2) | `5B B4 BE B4 89 01 00 00` | `1690954544219` |

Compare verified ClassIDs from elsewhere in the KB: `1707208440119`, `1778867967382`, `1661865036083`. Same space, same encoding, same order of magnitude — **independent corroboration of the ID model from a completely different direction.** Note the shape: the high bytes are `00 00`, so every ID is ~10¹²–10¹³ and the last two bytes of the 8 are always zero. That's what makes them easy to spot by eye in a hex dump.

> **✅ Offset — resolved 2026-09-16: spncryn is exactly right.** An ATK-unpacked resource file is `[FileHeader][payload]`, and the FileHeader is one `0x00` byte for almost every resource, so the ClassID occupies **bytes 1–8** (counting from 0). Verified from ATK's source and on real files: ATK's unpacked `1_-_PLAYER_SkelAddons.BuildTable` is a `00` byte followed byte-for-byte by the resource's payload. The one exception is a resource whose header starts `0x01` (it carries an object-block-allocator table — seen on 17 `Animation` records); there the header is `8 + 12N` bytes and the ClassID follows it. Layout: [`resource-type-ids.md`](resource-type-ids.md).

## Where item objects live

Two locations, and knowing which is which is most of the battle:

| Container | Holds | Example |
| --- | --- | --- |
| **`Game Bootstrap Settings`** (`0_-_Game Bootstrap Settings.data`) | The **slot/tool settings** — the wrapper that says "this wheel slot is a healing item" | `DBItemSetting_HealingItemEssence_Bandages.DBToolSetting` |
| **`DBContainer`** (e.g. `1_-_DBContainerEntry_0X104634F921.data`) | The **item objects themselves** — "nearly all of these can be found in DBContainer" | `HealingItemEssence_HealingSyringes.HealingItemEssence` |

Both sit inside `DataPC_patch_01.forge\Extracted`. `0_-_Game Bootstrap Settings.data` is the same entry documented in [`../docs/03-data-and-resources.md`](../docs/03-data-and-resources.md); this is the first place in the KB it's had a *purpose* attached.

Observed resource extensions, new to the KB: **`.DBToolSetting`**, **`.HealingItemEssence`**. Note also `DBContainerEntry_0X104634F921` — ATK printing an **unresolved name hash** as `0X<HEX>` ([`resource-type-ids.md`](resource-type-ids.md)).

## The procedure

Worked example: make the bandage slot dispense the **Syringe Mk. 2**. (In the original the slot has already been swapped to the Mk. 1 by the *Various Tweaks* mod's "Item wheel swap" component; the files are near-identical without it.) The only tool needed is a hex editor — **HxD** in the original.

1. **Find the container record** — the thing whose reference you're going to re-point. Here: `DBItemSetting_HealingItemEssence_Bandages.DBToolSetting`, in *Game Bootstrap Settings*. Open it in HxD.
2. **Find the object currently in the slot** — what you're swapping *out*. Here the Mk. 1 syringe, `HealingItemEssence_HealingSyringes.HealingItemEssence`, in *DBContainer*. Open it and **copy its first 8 bytes** (`51 77 EB 97 43 01 00 00`).
3. **Find the object you want instead** — what you're swapping *in*. Here `HealingItemEssence_HealingSyringesUpgraded.HealingItemEssence`. Note its first 8 bytes (`5B B4 BE B4 89 01 00 00`).
4. **Back in the container record, search for the step-2 bytes.** `Ctrl+F`, datatype **Hex-values**, direction **All**.
5. **Replace every hit with the step-3 bytes.** HxD shows altered bytes in red; they return to black once saved.
6. Save.
7. ⚠️ Repack the folders back into `.data` as usual — inner container first, then the forge ([`../docs/07-modding-workflow.md`](../docs/07-modding-workflow.md)).

That's the entire technique. Everything else is knowing which two files to open.

## ⚠️ The gotcha that costs people days

**The item wheel icon does not change. The function does.**

This is not in the original steps and it derailed the requester for several days — he swapped correctly, saw the Mk. 1 icon still sitting there, concluded it had failed, and started hex-editing at random trying to fix a mod that was already working. Tenebrae's diagnosis:

> "The guide probably should have clarified that the appearance on the item wheel won't change, but the function will. Think of it this way — it looks like a duck, but it quacks like a lion. … I'd recommend actually using the item and see if the functionality has changed."

Confirmed by the requester once he actually used it: *"i actually tested it and it worked!!!!"*

**Test by using the item, not by looking at it.** If you want the icon and name to match, that's a separate job — see [`../docs/12-localization-and-text.md`](../docs/12-localization-and-text.md) for text and the UI-map resources for icons.

## What can and can't be swapped

| Swap | Status |
| --- | --- |
| Bandages → syringe (Mk. 1 / Mk. 2) | ✅ the worked example |
| Bullet drop ↔ syringes | ✅ "exact same method" (spncryn) |
| Bandages → ration; bullet casing → strike designator | ✅ offered as practice exercises |
| Blowtorch ↔ rations | ✅ possible per Tenebrae, though a user attempting it got greyed-out unusable rations — i.e. **easy to get wrong** |
| **Stealth camo** → anything | ❌ "Highly unlikely, as its activation mechanics are very different from the other objects" (spncryn) |

The pattern: objects that share an **activation model** swap cleanly; ones with bespoke activation don't.

> **Learn it on the documented case first.** From the thread, to a user who jumped straight to their own swap and got broken items: *"Can you follow the guide as written for the items it talks about? If the answer is no, then trying on something else is probably never going to work because the fundamentals aren't there."* (Tenebrae)

## Open questions

- The exact byte offset of the ID within these DB resource types (see the caveat above).
- Why the swap works from the `DBToolSetting` side in *Game Bootstrap Settings* while the parallel `DBItemSetting_HealingItemEssence_HealingSyringes.DBToolSetting` in *DBContainer* is left untouched — spncryn poses this as an exercise rather than answering it.
- Whether the icon can be re-pointed by the same technique (a UI-map reference elsewhere in the record), which would close the "looks like a duck" gap.
- What determines swap compatibility, beyond the informal "similar activation mechanics."
