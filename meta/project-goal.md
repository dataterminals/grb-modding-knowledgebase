# The big-picture goal (from SamiPuma, verbatim)

This is the **north star** for the GRB cloth research. Everything else — the format reversing, the parameter tests, the forge-shadow investigation — is in service of this concrete modding goal. Recorded verbatim (2026-07-03) so it is never lost or paraphrased away.

> "I am attempting to make a ghost recon breakpoint mod in which I want to replace a flowing coat in game with a flowing poncho that I got from an outside source. I wish to integrate cloth physics to it that the in game flowing coat has, I've been having issues with the cloth physics not being applied to the flowing poncho that I got from an outside source. Usually what I would do is transfer weightpainting in blender from the flowing coat to the flowing poncho and reference the cloth file in the in-game item's pointers. The issue is that cloth file has an extension called .cloth, and at this current moment, .cloth files are not able to be opened/edited or used unless it's pointing to the original flowing coat that's already in game. In the past I've been able to implement physics by-way of another file type called .skeleton. These are usually used for hanging rigid items such as thermoses hanging off a belt. I was able to take weightpaint reference from something in game that uses that .skeleton onto an outside source model, and it would successfully take on those physics when I implement it to the game. Unfortunately this method does not work with .cloth references."

## What this actually asks for

The goal is **not** to *tune* cloth parameters (gravity/stiffness/wind/damping). It is to **make a NEW mesh (an outside-source poncho) take on the cloth physics of an existing in-game garment (a flowing coat)** — i.e. **rebind vanilla cloth to new geometry.** This is the long-standing **render↔sim binding / reskin** problem (see [`../docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md), "The binding problem").

### Sami's workflow and where it breaks
- **His method:** in Blender, transfer the weight-painting (the cloth's per-vertex `MaxDistance` "what's pinned vs. free") from the coat to the poncho, then point the in-game item's BuildTable pointers at the coat's existing `.cloth`.
- **The break:** the `.cloth` is **welded to the original coat's exact vertices**. Pointed at a poncho (different vertices), the cloth **won't take on** — it only works when the item still references the original coat mesh. And ATK can't open/edit GRB `.cloth` to fix the binding (its GRB cloth reader is gated off — see [`../docs/11`](../docs/11-cloth-and-physics.md)).

### The `.skeleton` contrast — a key lead
Sami reports a **separate** GRB physics path that DOES transfer to new meshes: **`.skeleton`-based secondary motion** (used for **rigid hanging items** — thermoses on a belt, etc.). He can take weight-paint reference from an in-game `.skeleton`-physics item onto an outside model, and the new model **takes on that physics in-game.** This works because it's **bone-driven** (weight-paint to the same bones), unlike `.cloth` which is welded to specific mesh vertices. **This does NOT work for `.cloth` references.**

## Implications for the research direction
1. **The core blocker is the cloth→mesh REBIND**, not parameter tuning. The productive levers are:
   - **(A) Rebind the `.cloth` to the poncho's vertices** — recompute the cloth's vertex binding/wrap for new geometry. Hard; ATK can't do it for GRB; partially reverse-engineered (see doc-11's render↔sim sections). Its viability also depends on **(prerequisite)** whether a *modified* cloth resource can take effect in-game at all — the open question the 2026-07-03 forge-shadow/patch-override tests were probing.
   - **(B) The `.skeleton` bone-based path** — investigate whether GRB's skeleton secondary-motion (proven transferable to new meshes) can approximate a *flowing* garment (bone-chain "cloth"), sidestepping `.cloth` entirely. Since Sami has this working for rigid items, this may be the more practical route for a poncho.
2. **Parameter tuning (gravity/stiffness/wind/MaxDistance) is orthogonal to Sami's need** — but the tests weren't wasted: they probe whether the runtime reads the *editable cloth resource* at all, which is the prerequisite for shipping ANY rebind (A). If cloth-resource edits can never take effect in-game, (A) is dead and (B) is the only hope.

**Next-session note:** when resuming, re-read this file first, then [`../docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) and the research log. Orient work around **(A) rebind** and **(B) skeleton**, not parameter tuning.
