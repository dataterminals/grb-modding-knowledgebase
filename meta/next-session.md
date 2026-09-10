# Next session

*Rewritten 2026-08-09; lane 3 added 2026-08-24; **refreshed 2026-09-09** to fold in the 2026-09-08
round trip and to strike two claims that had gone stale. The 2026-07-03 version described only the
cloth-rebind investigation, which has been parked since 2026-07-09 while later sessions went
somewhere else entirely. Every lane is written down now, so none of them gets lost again.*

**Read [`project-goal.md`](project-goal.md) first** — Sami's north star, verbatim, and still the
reason this repo exists. Then the two 2026-08-09 entries in [`research-log.md`](research-log.md)
for the current state of lane 2 — and, for lane 3, the 2026-08-23 and 2026-08-24 entries.
**For where the tooling actually stands, the 2026-09-09 entry is the current one.**

> **⚠️ Paths moved (2026-08-31). Everything is on `D:` now, not `H:`.** GRB install
> `D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint`, ATK `D:\Anvil Toolkit`, this repo
> `D:\Github Repositories\grb-modding-knowledgebase`. Older research-log entries name `H:` and are
> left alone on purpose — they record where things were at the time.

> **🧊 New (2026-08-31): Blender is scriptable from the command line, and there is now a bridge
> for it** — [`tools/blender/`](../tools/blender/README.md). `doctor`, `selftest`, `inspect`,
> `transfer-weights`, `run`. Blender 5.2.1 LTS lives at
> `D:\SteamLibrary\steamapps\common\Blender`. **This is lane-2B tooling**: a scripted, checkable
> weight transfer is the Blender-side half of the bone-physics route. ~~The selftest passes on
> synthetic data; **no real GRB mesh has been through it yet** — that is the next cheap
> experiment.~~ **SUPERSEDED 2026-09-08** — the Walker coat has since been through the whole
> bridge, twice; see the 2026-09-08 callout below. The selftest still passes, 7/7.

> **⚙️ New (2026-09-01): ATK's format engine is CALLABLE from Python** —
> [`tools/atk_bridge.py`](../tools/atk_bridge.py). The 2026-08-31 finding said the types were
> *reflectable* and honestly flagged that nothing had been invoked. Now they have: ATK's own mesh
> reader runs headless and **agrees with this repo's independent parser** on the Walker coat
> (1816/3263 and 956/1631). Four gates, all silent when wrong — `Libs\` needs an `AssemblyResolve`
> handler, `DataStorage.GlobalScimitarClassReader` must be populated before anything is constructed,
> `Mesh.Read` swallows its own exceptions into a plausible-looking half-built object, and
> `DataStorage.ActiveGame` silently reads as `BlackFlag` until something sets it *(4th found
> 2026-09-09; `arm()` now handles it)*.
> ⚠️ **`Failed` is not a success signal** (ATK wants one byte past the payload), and the bridge
> deliberately never touches `DataFile` — its `Deserialize` writes to your install.
> ⚠️ **It also corrected a fact this KB carried as VERIFIED since 2026-07-01:** GRB garment meshes
> are **four-influence**, not two-bone. That matters directly to lane 2B's weight transfer.

> **🧵 New (2026-09-01): the lane-2B pre-flight check exists** —
> [`tools/rebind_check.py`](../tools/rebind_check.py). Point it at a physics-carrying skeleton and
> your candidate GLB and it answers *does the new mesh's weight painting reach the bones Reflex3
> actually drives?*, plus influences/coverage/UVs/vertex-colours. **It is the first thing here that
> needs ATK and this repo's own decoders at once** — ATK reads meshes but is gated out of Reflex3;
> `reflex3.py` reads Reflex3 but knows nothing about meshes.
> **Do this before any in-game test**, then spend the launch. ~~Tested on five inputs including
> the real Blender transfer output; **no real GRB garment has been through it**, because that
> still needs an ATK GLB export.~~ **SUPERSEDED the same day** — the ATK export got automated
> and a real garment went through it, which found two bugs, one of them a **false FAIL on
> known-good input**. ⚠️ **Scope it with `--donor`.** Unscoped, it checks your mesh against *every*
> bone the rig drives — hair, straps, other garments' bones — and fails a garment that is
> correct.

> **🔁 New (2026-09-08): the round trip RUNS, and ATK's cloth gate is dead as a route.** Three
> things landed, and one of them closes a lead rather than opening one.
>
> 1. **`AnvilGLTF.FromGLTF` was called for the first time.** One call is the whole import side — it
>    runs `LoadBoneNodes` and `MeshFromGLTF` itself. The Walker coat went out to GLB, came back in,
>    and was diffed against the original: **verts and faces round-trip exactly** (1816/3263). Three
>    deltas — bones **30 → 25** (the importer keeps only bones that carry weight), `VertexStride`
>    and `VertexBuffer` still `0` (the buffer isn't built until write, and `RemapBuffers` does
>    **not** rebuild it), and **`Col4ub` dropped** from the vertex format.
> 2. **⛔ `SoftBody` is the wrong door, and the gate is LOAD-BEARING.** `SoftBody` *is* ATK's cloth
>    class, and GRB is absent from its `SupportedGames` — but appending GRB at runtime does not
>    open it, it produces **garbage**: `Read` takes the leading `int32` as a state count, gets
>    **257**, and runs off the end of a 436 KB file. AC-era `SoftBody` is a list of `ObjectPtr`
>    states; GRB cloth is a `ClothPackage` of section streams. **Don't spend time patching that
>    list**, at runtime or in the assembly. What survives is the **72 ungated
>    `Physics.MotionCloth.*` types**, which [`tools/motioncloth.py`](../tools/motioncloth.py)
>    already reads independently.
> 3. **The mesh write-back loses a colour channel.** ~~`AnvilGLTF.MeshFromGLTF` rebuilds a
>    vertex with `ColorCount` **2** where the original had **3**; find why, and the write-back is
>    faithful.~~ **ANSWERED 2026-09-09, and it is worse than a colour channel — see the callout
>    below.**
>
> ⚠️ **Two numbers `inspect` reports are upper bounds, not measurements.** ATK's writer emits all
> five UV and all five colour channels unconditionally, padding the absent ones. The Walker coat's
> GLB carries five of each; the **mesh** holds `UVCount = 1`, `ColorCount = 3`. Both are true.
>
> ⚠️ **The phantom `Icosphere` is Blender's doing**, not the file's — its glTF importer
> synthesises a bone-display mesh for every skinned GLB. `inspect` filters it as of 2026-09-08;
> before that it raised a spurious *"no vertex colors"* warning on **every rigged GRB garment**,
> i.e. on exactly the files it exists to validate.
>
> 🖥️ **Blender is drivable live now**, not just headless: the official Blender Lab MCP add-on
> (`bl_ext.lab_blender_org.mcp`) is installed alongside this repo's `grb_blender_addon`. The
> Claude-side server was always running — the Blender-side add-on was the missing half, which is
> why `localhost:9876` was closed.

> **🎯 New (2026-09-09): the write-back does not reconstruct a vertex format — it NORMALISES
> one.** This answers yesterday's blocker and replaces it with a sharper rule.
>
> - **The dropped colour was an unset global.** `DataStorage.ActiveGame` is a `public static Game`
>   with **no initialiser**, and the sentinel `Game.Null` is **-1** — so unset it reads as
>   `(Game)0` = **`BlackFlag`**. Only ATK's GUI ever assigns it (`MainWindow`, `GameSelector`);
>   **68 files read it**. `MeshFromGLTF` is one, and its Black Flag branch carries
>   `if (Joints.Count != 0) Vertices[0].Color2 = null;` — which fires on every skinned GRB
>   garment. **Fixed:** [`atk_bridge.py`](../tools/atk_bridge.py)'s `arm()` now sets it. Treat this
>   as a **fifth silent gate** alongside the four already in that module's docstring.
> - **⚠️ But do NOT read the round trip as a reconstruction.** With the game set, *every* skinned
>   GRB mesh comes back as **`ColorCount 3, UVCount 4`** regardless of what went in — measured on
>   four garments. Most GRB garments already sit at (3, 4), so the round trip *looks* lossless;
>   the Walker coat, at (3, **1**), is the one that exposed it. Symmetric with the export, which
>   pads all five channels unconditionally: **nothing in the GLB distinguishes a real channel from
>   a pad.**
> - **⚠️ A second wrong-game trap sits on the write path.** `MeshFromGLTF` builds its Mesh with
>   `ScimitarClassReader.New(Game.BlackFlag, …)` and **never assigns `mesh.Version`**, while
>   `Mesh.WriteToFile` switches on `base.Version` in ten places. A re-imported mesh claims to be a
>   Black Flag mesh whatever the active game is. It is settable; set it.
> - **✅ Three corrections reproduce the Walker coat exactly** — `ActiveGame = GRB`,
>   `mesh.Version = GRB`, and clear the padded `TEXCOORD_1..4` on vertex zero: format
>   `…_Tex2s_Joint4_Col4ub`, game id 1, **stride 36**, identical to what is stored on disk.
>   Note the middle step *widens* the stride to 48 before the trim brings it back — fixing the
>   game alone lands **further** from the truth than the bug did.
>
> **The rule to carry forward: take the target vertex format from the donor `.data`, never from
> the round trip.** ⚠️ Still unwritten and unloaded — the format agrees with the original as
> computed by ATK's own write path; no bytes were produced and nothing was tested in game.
>
> Incidental: `RemapBuffers` rebuilds the vertex list from face traversal, so vertices no face
> references are dropped (`Tsec_Madera_Coat_LOD0`: 12,502 → 12,498). A vertex-count check alone
> will flag that as a loss; it isn't one.

---

## Three lanes. Know which one you're in.

| Lane | State | What it is |
| --- | --- | --- |
| **1 — Community tutorial absorption** | idle since 2026-08-09 | Working the *Tier 1 Imports* `#mod-tutorials` forum into the KB, thread by thread |
| **2A — Cloth→mesh rebind** | **PARKED** since 2026-07-09 | Blocked on an in-game test that is staged but never run. ⛔ Narrowed 2026-09-08: the ATK-side route is `MotionCloth`, **not** `SoftBody` |
| **2B — Skeleton bone-physics (Reflex3)** | **⭐ LIVE — as of 2026-08-14** | Same goal, different mechanism. Now has a format, a corpus, and a vanilla flowing-coat exemplar |
| **3 — Community record (crowdfunds)** | active 2026-08-23 → 2026-08-24 | The funding system behind a large slice of the mod corpus, plus a live panel in a second repo. **Panel is out of sync — fix that first.** |

Lane 1 is not a detour — it turns the only real primary documentation GRB modding has into
something durable, and it produced independent corroboration of the 64-bit ID model from a
direction (hex editing) that had nothing to do with ATK. Lane 3 is provenance, not engine work: it
explains where a large slice of the catalogued mods came from and why so many of them never reached
Nexus. But **lane 2 is the north star**, and neither of the others may be allowed to quietly become
the whole project.

**2026-08-14 changed which sub-lane is live.** Chasing an unrelated community question about
ragdolls surfaced **Reflex3**, GRB's per-bone physics system: present in every skeleton, carrying
real data in 512 of them, fully typed in ATK's source, and already used by vanilla to drive a
**flowing trench coat** with bones instead of cloth. Because bones are re-bindable by
weight-painting and cloth is not, **2B is now the shortest path to Sami's goal**. See
[`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

---

## Lane 1 — keep working the forum

[`reference/community-tutorials.md`](../reference/community-tutorials.md) is the thread→page index
and the place to start. It records what's absorbed, what's known-but-not-absorbed, and the
five-step procedure for adding a thread. **Follow that procedure** — especially step 1 (fetch the
replies, not just the opening post; the corrections live there) and step 2 (read the attached
screenshots; several threads carry their key information only in images).

Three threads are absorbed. The forum has many more. The user intends to work through all of it.

### The one test worth doing before more reading

**Does renumbering a mod file to `1_-_` ever change in-game outcome?** There are now **two
independent field cases** where renumbering coincided with a behaviour change, and both are
confounded:

- The vest that showed UI-only until renumbered.
- The localization edits that compiled and repacked correctly but didn't appear, fixed by
  consolidating the XMLs into one container **renumbered to `1_-_`** — which bundles
  *consolidation* with *renumbering*, so it isolates neither.

The disk-collision mechanism explains both without any engine involvement: copying a mod file whose
exact `<N>_-_<Name>.<ext>` filename already exists in `Extracted\` silently replaces that entry.
The only plausible engine path is two entries sharing a real ID inside one forge, where write order
decides — but vanilla forges have zero duplicate IDs, and peer priority is still open.

**Test:** reproduce the vest case and use `data_inspect.py` to check for a filename collision
*before* renumbering. If there is one, the mystery is closed at the filesystem layer. To resolve
the localization case, separate the two variables — renumber without consolidating, and vice versa.

This matters beyond curiosity: mods ship advertised as *"renumbered to 1 to avoid replacing vanilla
files"*, and that claim is **wrong at the engine layer** — renaming protects the file on disk, but
only the embedded `ClassID` decides what the game replaces.

### Other open threads from 2026-08-09

- **Locate spncryn's BuildTable tutorial.** Referenced by SamiPuma as the thorough method for
  **cross-category** slot moves (scarf → face paint), where his quick copy-paste isn't safe. Would
  extend [`buildtable-xml.md`](../reference/buildtable-xml.md). Thread not yet found.
- **ID byte offset in DB resources.** spncryn says "bytes 1-8"; our
  [`resource-type-ids.md`](../reference/resource-type-ids.md) layout says a payload begins with a
  `FileHeader` byte, putting the ClassID at offset 1. Either these types write no header byte or
  the phrasing is loose. Needs a hex check against a real `.DBToolSetting`.
- **ATK 1.3.4 is in the wild**; this KB's format facts were decompiled from **1.3.1**. Confirm
  nothing relevant changed before treating 1.3.1 behaviour as current. *(Partly settled 2026-08-09:
  the build installed on this machine — `E:\Anvil Toolkit\` — **is 1.3.1**, so KB facts match the
  tool actually in use. A 1.3.4 build still hasn't been examined.)*
- **BuildTable unknowns:** the `Type` UInt32 slot/usage code (`0x1C0000`, `0x120000`); whether
  `ForceBuiltTableTOCOrder` is ever populated; resolve field-name hashes `x73B5D0A0` /
  `x67660D91`. Only **one** export has been seen (pants, ATK 1.2.10) — a second category (weapons
  via `dbcontainer`, or a solid-colour mod) would confirm which elements are universal.
- **Can the item-wheel icon be re-pointed** by the same hex technique? This closes the
  "looks like a duck, quacks like a lion" gap that cost the swap tutorial's requester days.

---

## Lane 2 — the cloth rebind (Sami's north star)

**The goal:** put an existing in-game garment's cloth physics onto a NEW mesh — a flowing coat
replaced with an outside-source poncho that keeps the coat's cloth physics. This is a **REBIND**
problem (bind vanilla `.cloth` to new geometry), **not** parameter tuning. Parameter tuning is a
side quest; don't let it become the objective again.

### STEP 1 — the prerequisite fork, still un-run

Can a modified cloth take effect *at all*? Everything in route (A) depends on the answer, and it
has never been validly tested.

> **You are on the desktop now — which is where this is staged.** A **complete** Bodark-pattern
> override sits in `Extracted\DataPC_patch_01.forge\` **and**
> `Extracted\DataPC_TGT_WorldMap_Bootstrap_Split_patch_01.forge\` (the gentle gravity-reversed kilt
> cloths `90001`/`90002`), with base `DataPC.forge` restored pristine. Earlier attempts patched
> only **one** of the two forges holding the cloth, which is the suspected reason they hung.

**Do:** repack **both** patch forges → launch → watch the kilt.

- **Loads + hem lifts** → a modified cloth CAN take effect → **route (A) is alive**; go do it.
- **Loads + no change** → mechanism works, gravity genuinely inert → try MaxDistance next
  (stable), else lean to (B).
- **Hangs even when complete** → a lone cloth override isn't tolerated → cloth-resource edits
  can't ship → **(A) is likely dead → pivot to (B).**

> ⚠️ Killing a hung GRB needs `taskkill /F /T`. Restore `DataPC_patch_01.forge` from its
> `.pre-coattest-backup` (or `D:\GRB_KnownGood_ForgeBackup_2026-07-02\`) to recover. Verify each
> patch `Extracted\` is in-sync with its live forge before repacking (both were, 2026-07-03).

### STEP 2 — the real work, via (A) and/or (B)

**(A) Cloth→mesh REBIND** (the render↔sim remap). The hard, long-standing problem — see
[`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md). The cloth is welded to the
coat's vertices; a poncho needs its binding recomputed. Blocked on cracking the wrap/binding
encoding **and** on STEP 1. Only pursue heavily if STEP 1 says modified cloths can load.

> ⛔ **2026-09-08 — one hoped-for shortcut is closed.** ATK cannot be talked into reading GRB
> cloth by appending GRB to `SoftBody.SupportedGames`. The formats are unrelated and the gate is
> load-bearing; opening it yields garbage, and merely exposes a chain of nested gates on
> `SoftBodyState`, `SoftBodyLOD`, `SoftBodyConstraint` and `SoftBodyVertexMapping`.
> **What that leaves standing is worth more than what it cost:** `SoftBody` also carries
> `ComputeBarycentric`, `ClosestPointOnTriangle`, `GetSimulationBones`, `ToMesh` and a
> `SoftBodyVertexMapping` type — a complete cloth→mesh rebind implementation, for AC-family
> formats. Something to **port**, not a switch to flip. It sharpens rather than replaces the
> 2026-07-01 finding that "ATK already has the algorithm".

**(B) The `.skeleton` bone-physics path — ⭐ START HERE. As of 2026-08-14 this has a name, a
format, and a vanilla exemplar.** Sami's key lead: GRB's `.skeleton` secondary-motion **transfers
to new meshes via weight-paint**, and **ATK can read GRB skeletons** (unlike cloth). That system is
called **Reflex3**, and it is now characterized —
see [`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

What changed:

- **Every** GRB skeleton carries an inline `Reflex3SkeletonConstraints` (hash `2386539642`);
  **512 of 2,469** hold real per-bone constraint data.
- The GRB blob header is `magic 0x12341234` + `version 3012000`, identical across all 512 — and it
  does **not** match ATK's Mirage constants, which is exactly why ATK stores it as an opaque
  Base64 blob instead of parsing it.
- `Reflex3Physics` (constraint type `10`) is fully typed in ATK source: constrained bone, swing
  axis, slide limits, **`Gravity`**, gravity node, **`WindFactor`**, collision toggle. Decoding the
  GRB blob is a **port of readers ATK already has**, not a reverse from nothing.
- **`Tsec_Trench_AddonSkeleton` carries 43,494 B of it** — a vanilla flowing trench coat driven
  entirely by bones, on an **addon** skeleton. Also `TP_HunterScarf_A_Skeleton` (9,991 B), hair
  rigs, backpack straps, and `Player_Kilt_Addon` (394 B — the kilt has bone physics *as well as*
  its cloth).

**The layer above is solved too** (2026-08-14, second session). An **`EntityBuilder`** assigns
skeletons — nothing else does; confirmed by decompressing all 66,899 resources in `DataPC`/`extra`
+ patches and finding every reference. The record is:

```
u32 TypeHash(0x24AECB7C = Skeleton) | u16 0000 | u8 0x12 | 6x 00 | u64 ClassID | u32 Slot
```

validated 16/16 against the skeleton sweep. So **a rig assignment is a plain 64-bit ID** — the same
shape as the community's hex item swaps — and `EntityBuilder` is `FileActionType.Xml` with GRB in
`SupportedGames`, so ATK can round-trip it as XML instead.

⚠️ **But the trench rig is NPC-only.** `Tsec_Trench_AddonSkeleton` is referenced by
`TSec_MIS_Blake(184)`, `TSec_CIN_Blake(184)` and `MIS_Y2E4_Wassili_Kropotkine` — **never** by
`PLAYER_Template` or `TEAMMATE_Template`. The player-wearable precedents are `Player_Kilt_Addon`
and `TP_HunterScarf_A_Skeleton`, which *are* in `TEAMMATE_Template` (under a node named
`PLAYER_SkelAddons`).

**Do next, in order:**

1. **Get an ATK XML export of `PLAYER_Template`.** Cheapest possible check — it settles which
   `EntityBuilder` field the reference records live in, and gives an editable round-trip path. Use
   [`tools/entity_skeletons.py`](../tools/entity_skeletons.py) first to see the build sheet.
2. **The goal-shaped experiment:** add or re-point a skeleton record in the **player** template
   aiming at a physics-carrying add-on rig, copying the kilt/scarf entries as the pattern. First
   end-to-end test of route 2B.
3. ~~**Finish the constraint-blob decode.**~~ **DONE 2026-08-14.** The blob is readable —
   [`tools/reflex3.py`](../tools/reflex3.py) prints the driven bone, its parent, swing limits in
   degrees, gravity and damping; the walk accounts for every byte in 204 of 205 skeletons.
   ~~confirm the 8-byte header is a bone-name hash~~ **also DONE** — it is
   `u32 BoneID | u32 ParentBoneID`, both **CRC32 of the exact-case bone name**, resolving against
   each skeleton's real bone list at **≈99.7 %** vs a 0.000 % null control. What's left inside the
   blob: the tails of type 9 (Orientation, 1,402 records) and type 6 (HingeVector, 472 — 36 of them
   in the trench coat), and the meanings of `param[0..3]` / `param[5..8]`.
   - ~~**Cheap win available:** extract ATK's `hashes.hl` name table.~~ **DONE 2026-08-14** —
     [`tools/atk_hashes.py`](../tools/atk_hashes.py) pulls 276,087 names out of a local ATK install
     (Fast-LZMA2 text, one name per line), and `reflex3.py --names` uses it. ⚠️ It only covers ATK's
     Assassin's Creed lineage, so it resolves **4 %** of GRB's bone hashes — but those are the
     **attachment points**: the trench coat and the scarf hang off `Spine2`, the watch off
     `LeftForeArm`. GRB's own dangle-bone names are still bare numbers.
     - ~~**Open:** find a GRB-specific bone-name source.~~ **PARTLY DONE 2026-08-14** — GRB.exe's
       own string table + the 370,259 forge entry names yielded
       [`reference/grb-bone-names.tsv`](../reference/grb-bone-names.tsv): **126 names, 43 of them
       physics bones**, each tagged with its evidence. More useful than the names is the **grammar**:
       `RFX_` = the Reflex physics bones, `T_` = targets/attachment points, `L_` = no-roll helpers,
       `Prop_` = prop attach points, unprefixed = standard biped.
     - ⚠️ **If you extend this, run a null experiment first.** Brute-forcing candidates against
       2,491 target hashes scores ~20 chance hits per 18.7 M tries; 93 of this session's raw hits
       were discarded as collisions. Only ship names backed by a literal string, a numbered family
       of ≥3, or a contextual match to the skeleton that uses them.
     - **Still open — the long tail:** 2,365 hashes remain bare numbers, including most per-garment
       dangle bones. An ATK GLB export is probably a dead end (ATK names GLB nodes from the same
       dictionary). A modder's original Blender/FBX rig, or an animation resource storing track
       names as strings, are the better bets.
4. Then: a new mesh weight-painted to a physics-carrying rig. That step **is** the project goal,
   reached without touching `.cloth` at all.

**The pipeline, as of 2026-09-08:**

```
   ATK export  ──►  Blender transfer  ──►  rebind_check  ──►  ATK import  ──►  repack
   AUTOMATED        AUTOMATED             AUTOMATED          CALLABLE         manual
   (09-01)          (08-31)               (09-01)            (09-08)          by policy
```

The front half runs headlessly, end to end, on real garment data. `FromGLTF` works; what is **not**
solved is write-back *fidelity* — see the `MeshFromGLTF` colour-channel blocker in the 2026-09-08
callout at the top. The final write into a `.data`/forge stays manual **by policy, not capability**.

> **Reading is done; writing is not.** Nothing has been written back to a skeleton yet, and any
> skeleton edit inherits the forge-shadow and hang-on-load hazards from the cloth work.

⚠️ Skeletons are **forge-shadowed** exactly like cloths (`Player_Kilt_Addon` sits in both
`DataPC.forge` and `DataPC_TGT_WorldMap_Bootstrap_Split.forge`). Any override must patch **both**
families, and "does a modified skeleton even load?" is as untested as STEP 1 is for cloth.

---

## Lane 3 — the community record (crowdfunds)

**What it is.** [`reference/crowdfund-history.md`](../reference/crowdfund-history.md) — the funding
and distribution system behind a large slice of the mod corpus, with a Discord message id behind
every claim. It is in this repo because it answers a provenance question the corpus keeps raising:
*where did `CFLIONNESS_*` come from, and why can't I find it on Nexus?* The companion live panel is
a **separate repo**, `dataterminals/t1-crowdfunds` →
<https://dataterminals.github.io/t1-crowdfunds/>, which renders `data/crowdfunds.json`.

**⭐ The access refusal was worked around on 2026-08-30, and how is the reusable part.** A
moderator was asked for **the numbers** instead of **the channels** — and supplied vote tallies and
supporter counts for **40 crowdfunds**, the contents of exactly the channels the declined role
would have opened. It validated **11/11** against the votes readable here. Turnout went 11 → 40,
membership went from unmeasurable to 41 crowdfunds, #3 got its name, and a crowdfund nobody knew
existed (#58) turned up. **If a request for access is refused, the fact behind it may not be.**

**The two ask-lists live in [`crowdfund-asks.md`](crowdfund-asks.md)** — what a moderator can
*look at* and report back (the archive channels, the role list, the two unnamed projects), and which
modder to ask about which of their own crowdfunds. Neither list asks anyone to grant access or share
a file, which is why they survive the refusal in lead 4. Read it before opening any conversation
about this in the server.

**Panel and repo are in sync as of 2026-08-30 (second pass).** Both carry the 2026-08-24 naming pass,
crowdfunds #56–#58, and the moderator's vote and membership figures. Names go on the panel under real handles; this repo keeps the Modder A–R pseudonyms.
**Modder R** is SexyCouchPotato, co-creator of Step Brothers in Arms with Modder M — the first
crowdfund with two creators. When they diverge again, the panel's `tools/refresh.py` re-pulls
sign-ups and the cohort block but **deliberately never touches the catalogue**, so names, creators,
dates and outcomes are always a hand edit in both places.

### What is actually left

1. **⭐ Hidden channel names — live lead as of 2026-08-25.** A ShowHiddenChannels-type plugin is now
   enabled, so locked channels appear in the client's sidebar. **It does not reach the bridge:**
   `GuildChannelStore.getChannels` still returns the same 50 accessible channels, and reads on hidden
   channels still fail the client-side permission gate. But **the client demonstrably holds their
   names** — `#heavy-metal` and `#pastaslov` render as names inside crowdfund posts and neither is
   accessible from this account. Why it matters: **an era-1 project channel's name is a crowdfund
   name**, which is the standing open question below. Two routes, neither yet tried in bulk:
   - **`current_view` is ungated** and returns the full channel object for whatever is on screen, so
     clicking a hidden channel names it. One click per channel — fine for a handful, not for 45.
   - **Sidebar screenshots.** Expand the crowdfund categories and read the names off the image.
     Cheapest by far, and covers the whole list in two or three shots.
   - If someone does patch the bridge for this, the store to read is the same one `parentChannel`
     already uses — the client receives *every* guild channel in `GUILD_CREATE`, permissions or not.
2. **#3 and #7 are the last two unnamed**, both System 1, both announced without a name. See
   §7 open question 2 for what is known about each and why they resisted. Low expected yield from
   more text searching — the productive moves are lead 1 above, or asking a member who was buying in
   during December 2024.
3. **⭐ The cheapest unexplored lever: read the guild role list.** A crowdfund's role carries the
   crowdfund's *name*, and the Discord client caches **every** guild role — including ones the
   account does not hold. The VesktopClaudeBridge plugin already reads that store
   (`GuildRoleStore.getRolesSnapshot`, in `plugin/discord.ts`, used only to resolve `@role` mentions)
   but exposes no RPC method or HTTP route for the snapshot itself. One small addition would have
   answered the whole naming strand in a single call, and might reach System 1's roles too.
   ⚠️ Not a complete answer: at least one crowdfund role has been deleted (#39's,
   `1466647776396836874`, renders unresolved), so closed projects may be gone from the store.
   ⚠️ Also a different repo and a plugin change — it needs an Equicord rebuild and a Discord reload.
   Ask before starting it. **A moderator can also just paste it** from Server Settings → Roles,
   which costs them thirty seconds and grants nothing.
4. **~~Ask the moderators for read-only access.~~ DECLINED 2026-08-25 — do not re-pitch.** The ask
   was put to two staff members and turned down. It was the minimal version — one role, zero
   guild-level permissions, `View Channel` + `Read Message History` only, on the `*-confirmed`
   channels plus `#crowdfund-projects-legacy` (`1302441788585279570`) and `#crowdfund-votes`
   (`1303906293219856477`), explicitly **not** the `*-unconfirmed` channels because those are the
   confirmation channels and hold proof-of-support screenshots (a moderator disabled images there on
   2026-03-20 *"because users keep on posting personal info in their crowdfund payment posts"*,
   msg `1484600258473496628`). A read-once was offered as sufficient, and an export as an
   alternative to any grant. All of it was declined, so **treat confirmed-channel access as closed** and
   spend the effort on leads 1, 5 and 6 instead. Two things worth remembering rather than repeating:
   asking *staff* for access to *everyone's* channels is a different question from asking *one
   modder* about *their own* crowdfund (see lead 6), and the answer being no does not make the
   sample dishonest — it made the coverage caveat load-bearing. *(Superseded 2026-08-30: a moderator
   supplied the vote figures anyway. The caveat now applies only to the delivery table.)*
5. **⭐ Widen the *destination* column from public channels — the best remaining lead, and it needs
   nothing from anybody.** Turnout is locked at 11 forever, but **where a crowdfund's output landed**
   leaks constantly into channels this account already reads, and into two it holds by right:
   `#supporter-armory` (`1310257013430681600`, readable now) and `#mod-releases`, plus Nexus. Probed
   2026-08-25 and it is real — outcomes for crowdfunds well outside the readable 11:
   - **#26 To the Moon → supporters.** *"The people who crowdfunded that voted for it to be released
     only to T2 armory"* — Modder C, msg `1422746736690200616`.
   - **#23 Commando Diving Drysuit → supporters.** *"the scuba you can still obtain, it was voted to
     be released in Tier 2 armory"* — msg `1413651144026099755`. That one is **System 1**, where we
     have no vote data at all.
   - **#24 Vulcan/Malyuk → public.** *"crowdfunded and voted to go public last year"* — a moderator,
     msg `1478138630139543864`.
   - **#41 Cold Ops Carbonara → public**, its creator posting the Nexus links (`1507031310512685106`).
   - **#38 Tip of the Spear → public** (`1498457981350842450`), which agrees with the vote we can
     read — the method validating against a known answer.

   ⚠️ **Three disciplines, or this turns into the thing §5 already had to correct.**
   *(a)* This measures **destination, not turnout** — a different, weaker, broader column. Keep it
   in its own field; never merge it into the vote table or quote it as a tally.
   *(b)* Destination is not the same claim as "what the vote said" when the vote was scoped to part
   of a project — see the Snake Eater and Bad Boys note in §5.
   *(c)* **Weight the source.** The creator or a moderator stating an outcome is evidence; a member
   guessing is not. A real example of the failure mode: *"I guess it was voted to not go public"*
   about Snake Eater (msg `1532273474637135975`) is flatly wrong — we can read that vote, and the
   XOF suit went public. Had it been an unreadable crowdfund, that guess would have been recorded
   as fact.
6. **Ask the modders, not the staff.** A modder describing the outcome of **their own** crowdfund is
   answering a trivia question, not granting access to anyone's private channel — a completely
   different ask from the one that was declined, aimed at different people, and it is how several
   facts already in this file were obtained. Modders L, C and K are all active in public channels
   and all credited on the panel. Per-crowdfund, incremental, no permissions involved.
7. **Sign-up counts are only recoverable while a post is live.** The 👍 count for the 26 System 2
   crowdfunds whose post is gone cannot be recovered by any permission — the messages are deleted.
   But it stops getting worse the moment `tools/refresh.py` runs on a schedule — nobody's permission
   required, and it is the one gap that closes itself if the script is simply left running.
8. **Re-run the forward oracle when new forwards appear.** Discord's search index covers forwarded
   message snapshots, so a deleted post's verbatim text survives in whoever forwarded it. Method and
   the six known forwards are in §7. It named nothing new this time; it is the only route to a
   deleted post's exact wording if one is ever needed.

### Don't repeat

- **A query bound is not a measurement.** This cost the 2026-08-23 pass a false "the posts were
  deleted this week" claim built on a `limit=4` read. Before calling an absence observed, probe it —
  resolve the URL, search the channel, page with a real bound. The 2026-08-24 §7 note shows what an
  actual absence proof looks like.
- **An announcement's phrasing is not the crowdfund's name.** #26 was catalogued as "White Moon"
  because the announcement said *"White Moon assets"*; White Moon is the asset **vendor** and the
  crowdfund is **To the Moon**. #43 was catalogued as "Crye Baby" from an attachment *filename*;
  it is **Crye Babies**. Confirm a name against how members and the modder write it, not against
  the announcement alone.
- **Don't count a chat-only entry and an announcement entry as two projects without checking.**
  #6 and #8 are the same GZW crowdfund reached from two directions. #10/#12 may be another pair.
- **Searching a bot-heavy guild by keyword mostly returns the bot.** Scope by author.
- **The adjacent-community trick is exhausted.** All 85 readable guilds were enumerated; only Tier 1
  Imports and The Bivouac are GRB, and the Bivouac has nothing from 2026. Don't re-run it hoping.

---

## Parked leads (don't lose these)

Open threads that aren't captured above but stay relevant to the north star. Roughly ordered by
payoff.

**Directly on the rebind goal (route A):**

1. ~~**`§4395` + `§4658` are undecoded… plausibly the exact rebind lever.**~~ **CLOSED 2026-08-09 —
   negatively. Do not re-open.** Both decoded from ATK source + a 156-body corpus sweep: §4395 is a
   `bool[64]` **enable bitmap** (a gate, no binding data), §4658 is a **null-terminated string that
   is empty in every vanilla body**. Neither is the rebind lever. Full write-ups in
   [`cloth-section-types.md`](../reference/cloth-section-types.md).
1b. **⭐ NEW top candidate — the 22 sections ATK does not model.** The same sweep found GRB cloths
   use **86** section types while ATK's `MotionSectionFactory` handles **64**; the other **22** hit
   `UnknownSection`. Since this KB's section knowledge was transcribed *from ATK*, they have never
   been looked at. Best sub-target: the **4403–4410 block** — four `12-byte counter → variable
   buffer` pairs, once per body in all 156, with `size(4404)==2×size(4406)` (paired index+payload
   arrays). ⚠️ **Render-scale but NOT one-per-render-vertex** — Walker LOD0 has 1816 render verts
   vs 636 elements in `4404`, so the obvious reading is already disproven. No ATK reader exists;
   decode from bytes, starting with the 12-byte counters (presumably 3×`int32`).
2. **Vanilla rebind precedent — the cheapest route-A experiment.**
   `1687_-_TP_Top_Bodark_Trench_Cloth` carries `Sim_Tsec_IanBlake_Trench_LOD0` at the identical
   **186-vert / 305-tri** geometry as `30291_-_IanBlake_TrenchCoat_Cloth` — confirmed 2026-08-09.
   ⚠️ **Refinement:** the sim-mesh name suffixes differ (`0x1DE8F05F3C9` vs `0x15FE3444A17`), so
   it is a **copy, not a shared reference** — vanilla does *not* demonstrate one cloth serving two
   items. Bodark also declares `MeshMappingsCount=1` and ships LOD0 only, vs IanBlake's `3` with
   two LODs. Still the cheapest experiment: try a **repoint** (make a second item reference an
   existing cloth whose sim mesh matches) before attempting to re-encode a wrap.
3. **Wrap-collapse validation on the kilt.** Once STEP 1 proves an override loads, run
   `clothwrap.py --diagnostic collapse/twist` on the kilt via the same both-patch pattern. If the
   visible mesh visibly scrambles, the wrap **is** the render driver → the route-A encoder is worth
   building. This is the gate; it was never validly tested (ghillies were pinned/invalid, Walker
   isn't player-viewable).
4. **Decode the wrap weight encoding** (the 6×u16 per-record) + the record↔render-vertex
   correspondence — the remaining blocker for a reskin encoder (only after lead 3 is green).
4b. **⭐ Port ATK's `SoftBody` rebind maths** (new 2026-09-08). `ComputeBarycentric`,
   `ClosestPointOnTriangle`, `GetSimulationBones`, `ToMesh`/`ToMeshNext`/`ToMeshOld` and
   `SoftBodyVertexMapping` are a working cloth→mesh binding implementation sitting in ATK's
   source — for AC-family formats, readable by decompile. They cannot be *run* on GRB data (the
   gate is load-bearing, see above), but the algorithm is exactly what lead 4 would otherwise
   reinvent from nothing. **Read them before writing an encoder.**

**On the skeleton path (route B):**

5. **Golem Cape** — still the interesting path-B exemplar: it visibly flows but has **no
   `Cloth`/`SoftBody` resource** (07-02). ⚠️ The 2026-08-14 all-skeleton sweep found **no skeleton
   entry named `*Cape*`/`*Golem*` anywhere**, so the cape's rig is named something else. Find its
   actual skeleton (via its BuildTable / mesh), then check its Reflex3 blob with the method in
   [`skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md). *(ATK's
   `Skeleton`/`Reflex3` classes are now decompiled and written up — that half of the lead is done.)*
6. ~~**Ragdoll bone-collider list** in `TP_WalkerCoat_Cloth`'s editor data.~~ **CLOSED 2026-08-14.**
   Decoded: a 536-char semicolon-separated list of **13 garment-owned capsule colliders**, every one
   prefixed `TP_WalkerCoat_`, covering **upper body only** (Head, Neck, L/R Arm, ForeArm, Hand,
   LeftShoulder ×4 — no spine, pelvis or legs). It is the coat cloth's collision proxy set, named
   after the bones it follows. **Not** a death-ragdoll rig, and not a binding mechanism.

**Do not re-chase — the community ragdoll question (2026-08-14):**

Releptive asked in `#shit-talk` whether GRB deaths could ragdoll instantly the way hostage-guard
kills do. **Answer: not with today's data surface, and the reason is absence, not difficulty.**
GRB ships **no `LiteRagdoll` resource** (ATK's `SupportedGames` excludes GRB; zero entries anywhere),
and **no combat animations at all** — all 1,564 `Animation` resources are ambient NPC acting clips,
and sweeps of all 415,177 forge entry names return zero hits for `ragdoll`, `hitreact`, `flinch`,
`stagger`, `getup`. Death-anim selection and ragdoll blend-out live in an animation state machine
that is not a forge resource. Full detail in the 2026-08-14 research-log entry.

**Prerequisite / infrastructure:**

7. **Full shadow-surface map.** Re-run `forge_inspect.py` base-vs-base across ALL forges (incl. the
   WorldMap `_Split` bases the 06-30 ID study skipped) to learn whether the shadow extends beyond
   `Cloth` to meshes/definitions. Cheap; de-risks every future override.
8. **§4356 `ClothDefinition` flag↔section agreement** is an untested failure mode — a flag that
   disagrees with the sections present likely breaks load; load-bearing for any rebind that
   adds/removes sections.
9. **Reconcile the raw-block contradiction:** on 2026-07-01 raw-block `.data` staged into
   `DataPC.forge` and the game *booted*, yet 07-02 proved raw blocks hang. Either the 07-01 edit
   never loaded (shadowed) or raw tolerance is contextual — bears on trusting any "edit confirmed
   in forge" check.
10. **BuildTable side of binding:** which property/node a BuildTable uses to reference a cloth, and
    whether the render mesh must carry `IsGeneratedFromCloth` + a matching `ClothEditorDataClothID`.
    [`buildtable-xml.md`](../reference/buildtable-xml.md) now documents the file's anatomy, so this
    lead is cheaper than it was — **lane 1 fed lane 2 here.**

---

## Don't repeat

**On the cloth work:**

- Don't test parameter tuning as the goal.
- ⛔ **Don't try to open ATK's cloth gate** by appending GRB to `SoftBody.SupportedGames`, at
  runtime or by patching the assembly. Tried 2026-09-08: it yields garbage, not cloth, and would
  do the same in the GUI. The gate is load-bearing because the two formats are unrelated.
- Don't conclude "params inert" without a shadow-free (confirmed-loaded) test. 44/56 cloths are
  duplicated across `DataPC.forge` **and** a WorldMap base forge — editing only the `DataPC` copy
  proves nothing.
- After any repack, **hash-verify the live patch forges actually changed.** ATK may silently drop
  never-before-seen IDs (`90001`/`90002` aren't in the original file table). If a forge's hash is
  unchanged, the override didn't land; fallback = overwrite the existing kilt entry IDs
  (`34800`/`34793`) instead of minting new ones.

**On the tutorial work:**

- Don't judge a practitioner's claim false on engine reasoning alone. The "renumber to 1" call was
  initially marked simply false; the engine reasoning was right but answered the wrong claim —
  SamiPuma meant filesystem overwrite in the unpacked working folder, not resource override.
  **Find out which layer someone is talking about before grading them.**
- Don't smooth over contradictions between practitioners. Where they disagree, or a fix worked
  without a known mechanism, that *is* the finding.
- Don't test a hex item swap by looking at it. A swap changes an item's **function but not its
  item-wheel icon** — test by *using* the item.
- Don't edit one localization container and assume you're done. English (US) is split across
  **seven**, items may appear in more than one, and a partial edit silently fails. And `&` must be
  `&amp;` — a raw ampersand corrupts the file.
