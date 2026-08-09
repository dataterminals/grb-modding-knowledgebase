# 12 — Localization: renaming items, weapons, and any in-game text

Every piece of displayed text in GRB — item names, weapon names, descriptions, UI strings — lives in **`LocalizationPackage`** resources, one set per language. Renaming things is therefore a **text edit**, not an asset edit: no Blender, no mesh, no texture. It's one of the most approachable mods in the game.

> **Source:** *Tier 1 Imports* `#mod-tutorials` thread **"Renaming ingame items (or basically any visible text you could think of)"** by **ViruS** (message `1485672994138358001`, 2026-03-23, 14 👍), plus the troubleshooting exchange in-thread (ViruS, spncryn, Darmflora, Maliketh, ryan1662). Screenshot evidence read directly. Provenance: [`../meta/research-log.md`](../meta/research-log.md).

`LocalizationPackage` is a known resource type (id `1849465967` / `0x6E3C9C6F` — see [`../reference/resource-type-ids.md`](../reference/resource-type-ids.md)) and one of the types ATK round-trips through **XML**.

## Where the text lives

Localization resources sit in **`DataPC.forge`**. Find them with ATK's search bar using a wildcard on the language:

```
local*us          ← English (US); substitute your language
```

English (US) is spread across **seven** containers. Verified from a live `DataPC_patch_01.forge\Extracted` folder (ATK 1.3.4), with the leading numbers that install happened to have:

```
29523_-_LocalizationPackage_English(US).data
44689_-_LocalizationPackage_English(US)_E015.data
45089_-_LocalizationPackage_English(US)_1L2.data
45346_-_LocalizationPackage_English(US)_1E2.data
45470_-_LocalizationPackage_English(US)_1E3.data
47002_-_LocalizationPackage_English(US)_1L3.data
47602_-_LocalizationPackage_English(US)_2E4.data
```

> Leading numbers are positional labels and will differ on your install — see [`08-naming-conventions.md`](08-naming-conventions.md). The **suffixes** (`_E015`, `_1L2`, `_1E2`, `_1E3`, `_1L3`, `_2E4`) are the stable part. *(inferred: they look like content/expansion partitions — episode and title-update batches — but this is unconfirmed.)*

## The procedure

1. Unpack `DataPC.forge` in ATK; search `local*<lang>`.
2. Unpack all seven containers for your language (list above).
3. **Copy those folders into `DataPC_patch_01.forge\Extracted`** — you override in the patch forge, never in the base ([`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md)).
4. In ATK, save the XML of the `.LOCALIZATIONPACKAGE` file in each folder.
5. Open the XMLs in any text editor (Notepad, Notepad++, …).
6. `Ctrl+F` the text you want to change — e.g. `Crye AVS`.
7. You're in the right place when you land inside a `<String ID="XXXXXX">` element.
8. Edit **only the text**, never the ID:
   ```xml
   <String ID="249162">Crye AVS</String>
   <String ID="249162">CryeBaby Precision AVS</String>
   ```
9. Save, then **compile** the XML in ATK (right-click → Compile).
10. ⚠️ Repack the folder whose XML you changed.
11. ⚠️ Repack `DataPC_patch_01.forge`.

Same inside-out order as everywhere else: inner container first, then the forge ([`07-modding-workflow.md`](07-modding-workflow.md)).

## Gotchas

**Strings are scattered, and duplicated.** Items are spread across *all* of a language's localization files. The vast majority sit in the first two (`(US)` and `(US)_E015`), but not all — the SIG516 Survival, for instance, is in `_1L2`. Worse, **one item can appear in several files**; if you change only one, the name may not update in-game. Change every occurrence.

**Never edit the `ID` attribute.** The numeric `String ID` is the handle the game resolves. Only the element's text content is yours to change.

**`&` will corrupt the file.** A raw ampersand is invalid XML — it's markup, not text. One modder lost their work to it:

> "Do not put the `&` in the weapon name. in my case it likes corrupts the entire file and i had to start over, and renaming any other weapon wont work anymore." — Maliketh

The fix is standard XML escaping, not avoidance:

> "You can use `&`, just replace it with `&amp;`" — spncryn

The same applies to the other XML metacharacters (`<` → `&lt;`, `>` → `&gt;`).

**Your in-game language must match the files you edited.** Editing `English(US)` does nothing if the game is running in another locale.

**Pro tip — make your renames findable.** Prefix renamed weapons with `*`; sorting by name then floats them to the top of the list. Genuinely useful on installs with hundreds of guns (Darmflora).

## Troubleshooting: edits compiled but nothing changed in-game

A worked case from the thread (ryan1662, resolved). Symptom: the rename compiled and repacked cleanly, but the weapon kept its stock name. The checklist ViruS ran:

1. Did you save **and compile** the XML?
2. Did you repack the localization folder you edited?
3. Did you repack `DataPC_patch_01`?
4. Did you check whether the item is named in the **other** files too?
5. Does your in-game language match the files you edited?

When all five passed, the diagnosis was a **competing localization entry already present in the patch forge**:

> "bc you still got the one that starts with 39 in patch01 which is overwriting your edited ones … look at the numbers" — ViruS

The fix that worked: **pull the XMLs out of all the folders, put them into a single folder, rename that folder so its index is `1`, and repack.**

> **⚠️ Field-reported, mechanism unconfirmed.** This resolved the user's problem, but the fix bundles two changes — consolidating several containers into one, *and* renumbering to `1_-_`. Which of the two did the work was never isolated. It is a genuine data point for the open question in [`08-naming-conventions.md`](08-naming-conventions.md) about whether entry ordering ever reaches the engine, but it does not settle it. Note also that the screenshot of the same user's folder shows the localization containers numbered `29523`…`47602`, not `39` — so the specific number in that quote should not be taken literally.

## What else this unlocks

The tutorial's own framing: *"basically any visible text you could think of."* Item and weapon names are the common case, but the same `<String ID>` machinery carries descriptions, menu labels, and UI copy. Nothing about the procedure is weapon-specific.

Related: [`../reference/hex-item-swaps.md`](../reference/hex-item-swaps.md) changes what an item *does* while leaving its name and icon alone — the natural complement to changing what an item is *called* while leaving its function alone.
