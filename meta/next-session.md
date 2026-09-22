# Next session

*Rewritten 2026-08-09; lane 3 added 2026-08-24; refreshed 2026-09-09 to fold in the 2026-09-08
round trip; **refreshed again 2026-09-16** — lane 4 (the gameplay/AI database) written down, lane
2B's container blocker closed, and the claims a one-byte walker bug had propped up struck. The
2026-07-03 version described only the cloth-rebind investigation, which has been parked since
2026-07-09 while later sessions went somewhere else entirely. Every lane is written down now, so
none of them gets lost again.*

**Read [`project-goal.md`](project-goal.md) first** — Sami's north star, verbatim, and still the
reason this repo exists. Then the two 2026-08-09 entries in [`research-log.md`](research-log.md)
for the current state of lane 2 — and, for lane 3, the 2026-08-23 and 2026-08-24 entries.
**For where the tooling and lane 2B actually stand, read the last 2026-09-16 entry, *"The container
walker was one byte off"*.** It corrects entries from 2026-08-14, 2026-09-01, 2026-09-09 and earlier
the same day.

> **🖥️ Which machine are you on? (clarified 2026-09-10 — this is NOT path drift.)**
> This project is worked from **two** computers, and they disagree about drive letters:
>
> | | **SylG5** | **SylDesk** |
> | --- | --- | --- |
> | GRB install | `D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint` | `H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint` |
> | ATK | `D:\Anvil Toolkit` | `E:\Anvil Toolkit` |
> | Blender | `D:\SteamLibrary\steamapps\common\Blender` | `G:\SteamLibrary\steamapps\common\Blender` |
> | This repo | `D:\Github Repositories\grb-modding-knowledgebase` | `H:\Github Repositories\grb-modding-knowledgebase` |
>
> The 2026-08-31 banner this replaces said "everything is on `D:` now" — true, on SylG5. Older
> research-log entries naming `H:` are equally true, on SylDesk. **Do not "fix" either set of
> drive letters**; they are records of a real machine, not rot. Forge backups live on `D:` on
> both.
>
> ✅ **The tooling no longer cares** (2026-09-10). `atk_bridge.py` searches for ATK and for the
> GRB install rather than hardcoding `D:` — `--atk <dir>` or `$GRB_ATK` to override. It had been
> SylG5-only since it was written; `tools/blender/grbblend.py` always searched.

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
> 2026-09-09; `arm()` now handles it)*. **Three more are loud rather than silent, and all three
> are WPF** — `MeshFromGLTF` shows a modal dialog for a GLB with no colours/UVs; `ToXml` needs an
> **STA thread**; and `GameFileList` offers to *download* its file list unless
> `Lists/<Game>.gfl` resolves from the **working directory**. `import_gltf` and `export_xml`
> handle all three *(found 2026-09-09)*.
> ~~⚠️ **`Failed` is not a success signal** (ATK wants one byte past the payload)~~ **RESOLVED
> 2026-09-16 — that byte was our container slicer cutting off the payload's last byte; sliced
> correctly, `Failed` is False with no pad.** The bridge still deliberately never touches `DataFile`
> — its `Deserialize` writes to your install.
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
> - **🛠️ There is now a tool for this.** `python atk_bridge.py <donor.data> --import new.glb`
>   runs the import, applies all three corrections and tells you whether the file would get the
>   donor's exact format and stride; exit 2 when it would not. It also survives a **sixth gate**
>   the other tools never hit — `MeshFromGLTF` opens a **WPF modal dialog** for a GLB with no
>   vertex colours or UVs, which kills a headless import outright. **Run this before any
>   write-back.**
>
> **The rule to carry forward: take the target vertex format from the donor `.data`, never from
> the round trip.** ⚠️ Still unwritten and unloaded — the format agrees with the original as
> computed by ATK's own write path; no bytes were produced and nothing was tested in game.
>
> Incidental: `RemapBuffers` rebuilds the vertex list from face traversal, so vertices no face
> references are dropped (`Tsec_Madera_Coat_LOD0`: 12,502 → 12,498). A vertex-count check alone
> will flag that as a loss; it isn't one.

> **✅ New (2026-09-17): the lane-2B EDIT is proven on paper, and the donor rig has a shortlist.**
> Two things landed, both read-only, neither needing the game.
>
> 1. **ATK's XML round trip is byte-exact on BuildTables.** `XmlUtils.CompileXml(Stream) → byte[]`
>    is an in-memory XML→binary compiler with **no output path**, so the whole edit path runs
>    headless with nothing on disk to overwrite. **2,443 of 2,444** BuildTables in
>    `TEAMMATE_Template` export and recompile byte-identical — so row-component `Index` values do
>    survive, and the *"binary `BuildRow.Write` writes every Index as 0"* worry does not apply here.
>    A rig repoint changes only that handle's bytes; **adding** a `Skeleton` Handle costs exactly
>    **+25 B** — a component-count bump plus one 25-byte component, which confirms the row-component
>    layout from the *write* side — and the result reads back through ATK with `Failed=False`.
>    ⚠️ One table in 2,444 is lossy: a row component that **embeds an object** (`Type 0x150000`) is
>    exported as an empty `<BaseObjectPtr />` and loses its payload. `Skeleton`, `GraphicObject` and
>    `SoftBody` assignments are all `Handle` (`0x120000`) and unaffected. Round-trip an unfamiliar
>    table unmodified before editing it.
>    ⚠️ `Directory.SetCurrentDirectory` moves the **process** CWD — a relative `open(…, "w")` during
>    an `export_xml`/`prime_filelist` window writes into your **ATK install**.
>
> 2. **117 of 148 physics rigs really do drive a mesh** — [`tools/rig_census.py`](../tools/rig_census.py),
>    47 s over `TEAMMATE_Template` + `PLAYER_Template`. The 2026-09-16 evening conclusion rested on
>    five rigs checked by hand; all 148 have now been checked, and it **softens**: no vanilla flowing
>    *coat* moves on bones, but `Addon_body_samFisher` drives a **torso garment** with 22 constrained
>    bones and zero weight on parents. The shortlist is in lane 2B step 2 below.
>    ⚠️ It also generalises the trench trap: three more rigs are assigned to garments that carry
>    **no** weight on their driven bones. **Assignment ≠ motion; weight painting is the real
>    assignment.**
>
> ⚠️ Still arithmetic, not evidence: nothing was written, nothing was repacked, nothing was loaded.

> **🧶 New (2026-09-18): the cloth wrap is DECODED, and vanilla ships a rebind.** Lane 2A had been
> parked since July on two static blockers — the wrap record's "6-u16 weight encoding" and which render
> vertex each record belongs to. Both are closed, and without a game launch.
>
> - **A record is twelve quantized bytes:** `(u, v, h)` on a sim triangle for each of **position,
>   normal, tangent and binormal**, weights `(u, v, 1−u−v)`, height along the cage's vertex normals.
>   The table in front of the records is per render vertex (`0xFFFF` = skinned only), and records are
>   in render-vertex order.
> - **Proven against the game's own meshes:** it rebuilds the real render mesh from the cage to a
>   median of **0.45 mm** across **87 cloth LODs / 489,472 vertices**. Every structural rule holds on
>   **all 156** bodies, and 1,716/1,716 block↔body cross-checks pass. Tool:
>   [`tools/clothmap.py`](../tools/clothmap.py).
> - **ATK's "22 unmodelled sections" were this all along.** §4403–4410 are quantization headers plus
>   SIMD copies of the wrap's tangent/binormal bytes; §4374–4380/4386 hold one group **per mesh
>   mapping**, which answers why `MeshMappingsCount` exceeds the §4395 slots.
> - **⭐ Kropotkine's trench coat is Blake's cloth, rebound.** The cage is byte-identical, and the
>   mapping is regenerated for Kropotkine's mesh. Ubisoft did Sami's operation in shipped content.
>
> **Next, still no launch:** write the encoder (new mesh + donor cage → mapping block + body sections),
> then **validate it by re-encoding vanilla**: Walker, Blake and Bodark from their own meshes, compared
> with the shipped bytes and geometry. Only then spend the launch — STEP 1 below is still the gate on
> whether the game accepts a cloth we wrote.

> **🧩 New (2026-09-20): the Reflex3 physics record is fully decoded, and a rig has a recipe.**
> A self-delimiting parse of all 204 distinct blobs replaced the August scan, whose "204 of 205
> exact" test was vacuous. The physics record is `BoneInfo (5 matrices) | 5 gated limit slots
> (slide X/Y/Z in metres, two swing axes in radians) | 9 floats`; the floats read as mass\*,
> spring\*, slide damping\*, `p3`, gravity 9.8, gravity factor\*, wind factor\*, 0, 0 (\* inferred).
> The matrices are the bone's local bind (twice), the **parent's character-space frame** — a 90°
> turn plus 0.964 m over the male body rig, exact for five rigs — and the swing rest frame (twice).
> Bones can be referenced **by name string** (`Spine2`, `T_BackPack`); type 9's second byte is a
> count; types 8 and 11 were hiding in the old tails; the scarf and NVG straps use a different
> physics type (24). Hair strand, ponytail, kilt, backpack and trench recipes are tabulated in
> [`reference/reflex3-chain-templates.md`](../reference/reflex3-chain-templates.md) with an inferred
> poncho recipe. Still open: `p3`, the type-9 body, whether the runtime reads the baked matrices.
> **Nothing was written or launched.**

> **🧱 New (2026-09-20, second): the wall is one step wide.** A content-hash diff of the live forges
> against the install's pristine copies shows what the game already loads from other people's mods:
> 37 resource types added or modified — among them **124 backpack rigs overridden by vanilla ID with
> two bones moved and their 19–62 KB Reflex3 blobs intact** (*Sling Positions*), 65 weapon and
> holster rigs as edited copies under new IDs, the three holster rigs with the holster bone
> re-parented to `Hips`, twenty AI-database record types modified in place, and this repo's own
> eleven July test cloths still live in base `DataPC.forge` with the game booting on them. **Zero
> mods change a Reflex3 blob.** So for lane 2B everything is proven by proxy except one thing: a blob
> the game did not compile. The generator's first test should change one swing limit in one rig the
> install already overrides, and nothing else. Also: the GRB Mod Manager writes containers *without*
> ATK's trailer, so unsigned no longer means vanilla.
> [`reference/install-edit-classes.md`](../reference/install-edit-classes.md).

> **🧷 New (2026-09-20, third): the writer exists.** `tools/reflex3_write.py` re-emits every one of
> the install's 204 blobs byte-exact, edits swing/slide limits and the nine parameters by bone,
> generates a physics-only blob from a JSON spec (regenerating the kilt and Casper hair from their
> own fields reproduces every matrix to the float), and splices the result into the skeleton's
> `.data` with both container blocks rebuilt and verified. The game is never touched. The first
> write test — one swing limit in the Hill backpack rig the install already overrides — is one
> command in lane 2B step 2 below.

> **🔀 Reconciled (2026-09-22): the five callouts above come from two parallel lines.** SylDesk
> wrote the 2026-09-17 and 2026-09-18 ones, and SylG5 the three dated 2026-09-20. Both started from
> the 2026-09-16 state, and neither saw the other. Where they meet:
>
> - **The census holds on the new parser.** Re-run on the 2026-09-20 `reflex3.py`, it still finds
>   148 rigs, split 117 / 22 / 9, over 694 pairs. Eleven rigs' own counts moved, because the August
>   scan had invented two records and hidden the type-8/11 ones. See the 2026-09-22 research-log
>   entry.
> - **Compare the poncho recipe against `Addon_body_samFisher` before generating one from nothing.**
>   It is the census's vanilla garment body on bones (22 constrained bones, 0 weight on parents), and
>   the 2026-09-20 recipe was drafted without it.
> - **The 2026-09-17 "nothing was loaded" is superseded** by 2026-09-20 (second): edited skeletons
>   carrying physics blobs already load. What remains is a blob the game did not compile, and the
>   first write test in lane 2B step 2 isolates exactly that.

> **📍 Where this leaves us — read this one if you read nothing else (2026-09-09).**
>
> **What now works.** Export a real GRB garment to GLB, move weights in Blender, check the
> result against the rig's physics bones, import it back through ATK, and be told whether the
> file you would write is *structurally identical to the original* — all headless, all scripted,
> all read-only. Four garments have been through it end to end.
>
> **What that is NOT.** Nothing has been written into a `.data`. **No modified mesh and no
> modified skeleton has ever been confirmed to load in GRB** — that wall has not moved since
> July, and every tool built since assumes past it. "ATK's own arithmetic says the bytes would
> match" is a much weaker claim than "the game accepted it", and the gap between them is the
> whole remaining risk.
>
> **What to do next.** ~~Lane 2B step 1: get an ATK XML export of `PLAYER_Template`.~~
> **DONE 2026-09-09**, and the answer moved the target: a rig assignment is **not** an
> `EntityBuilder` field at all. `PLAYER_Template` reaches its rigs through a `BuildTable` named
> **`PLAYER_SkelAddons`** (ID `1898138514560`), which it **shares with `TEAMMATE_Template`**.
> ~~The new step 1 is: find where that BuildTable lives.~~ **FOUND, same day.** It is a
> `BuildTable` resource **inside the `TEAMMATE_Template.data` container** — verified in bytes at
> offset 94,195 of the patch copy. ~~**The new blocker is our own code:** `data_inspect.py`
> mis-parses that container, so the resource cannot yet be read or exported. See step 1c below.~~
> **CLOSED 2026-09-16.** The walker was one byte off: it never skipped the FileHeader byte between a
> resource's name and its payload. Fixed from ATK's source, `TEAMMATE_Template` walks to its last
> byte as 2,451 resources (3,963 live), and `PLAYER_SkelAddons` exports to XML headlessly
> (`atk_bridge.py … --xml out.xml --resource PLAYER_SkelAddons`).
>
> **And reading it moved the target again.** `PLAYER_SkelAddons` holds five **player-wide** rigs
> (FakeGun, ENVInfluence, Props, `Regular_Male_Reflex_SklAdd`, a default holster). **A garment's rig
> is assigned from the garment's own build table:** the kilt from `TP_PANT_Kilt` (Index 10), the
> scarf from eight mask/head tables, and Blake's flowing trench coat from
> `Tsec_IanBlake_Trench_Mcloth_MISSION` (Index 4). Two installed mods, Bison Belt and Tactical Human
> Set, already assign rigs per item this way, in files that byte-match the live container. The next
> step is lane 2B step 2 below, retargeted.

---

## Four lanes. Know which one you're in.

| Lane | State | What it is |
| --- | --- | --- |
| **1 — Community tutorial absorption** | idle since 2026-08-09; its open test **answered 2026-09-16** at ATK's repack layer | Working the *Tier 1 Imports* `#mod-tutorials` forum into the KB, thread by thread |
| **2A — Cloth→mesh rebind** | **⭐ UNBLOCKED on paper 2026-09-18** — was parked since 2026-07-09 | The wrap is **decoded** (`clothmap.py`) and vanilla ships a rebind (Kropotkine's trench coat on Blake's cage). Next: an encoder, validated against vanilla without the game. STEP 1 (does a modified cloth load?) still gates shipping. ⛔ The ATK-side route is `MotionCloth`, **not** `SoftBody` (2026-09-08) |
| **2B — Skeleton bone-physics (Reflex3)** | **⭐ LIVE — as of 2026-08-14**; read side complete 2026-09-16 | Same goal, different mechanism. Has a format, a corpus, vanilla exemplars, the exact record that assigns a rig, and mod precedents |
| **3 — Community record (crowdfunds)** | active 2026-08-23 → 2026-08-30 | The funding system behind a large slice of the mod corpus, plus a live panel in a second repo |
| **4 — Gameplay / AI database** | **active 2026-09-16** | How enemies see, hear, call for backup and cheat — `DBContainerEntry` records, binary-patched. Sylvia's own second track, not a detour from lane 2 |

Lane 1 is not a detour — it turns the only real primary documentation GRB modding has into
something durable, and it produced independent corroboration of the 64-bit ID model from a
direction (hex editing) that had nothing to do with ATK. Lane 3 is provenance, not engine work: it
explains where a large slice of the catalogued mods came from and why so many of them never reached
Nexus. Lane 4 is gameplay, not art: the AI database, with its own doc tree and its own reasons to
exist. But **lane 2 is the north star**, and none of the others may be allowed to quietly become
the whole project.

**2026-08-14 changed which sub-lane is live.** Chasing an unrelated community question about
ragdolls surfaced **Reflex3**, GRB's per-bone physics system: present in every skeleton, carrying
real data in 512 of them, fully typed in ATK's source, and already used by vanilla to drive a
**flowing trench coat** with bones instead of cloth. Because bones are re-bindable by
weight-painting and cloth is not, **2B is now the shortest path to Sami's goal**. See
[`reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

> ⚠️ **Corrected 2026-09-16 (evening): the trench coat is cloth, not bones.** Its build-table row
> assigns a cloth *beside* `Tsec_Trench_AddonSkeleton`, and no LOD of either trench coat mesh
> carries any vertex weight on any bone the rig's Reflex3 records drive. Vanilla's bone physics does
> visibly move hair, backpack straps and vest rigs (meshes weighted to the driven bones); every
> flowing garment checked — both trench coats, the kilt, the Golem cape — is cloth. Route 2B is
> still mechanically sound, and weight-painting is still why it matters, but ~~**there is no vanilla
> bone-only flowing garment to copy**: a poncho on bones would be a new, hand-weighted chain rig.~~
> See the 2026-09-16 (evening) research-log entry.
>
> ⚠️ **Softened 2026-09-17 by the census** (below): no *flowing coat*, still true — but vanilla does
> move a garment **body** with bones. `Addon_body_samFisher` drives `Tpri_Top_SamFisher_LOD0` with
> **22** constrained bones, 5,105 weight entries on record-head bones and **zero** on parents. The
> conclusion above rested on five rigs checked by hand; all 148 have now been checked.

---

## Lane 1 — keep working the forum

[`reference/community-tutorials.md`](../reference/community-tutorials.md) is the thread→page index
and the place to start. It records what's absorbed, what's known-but-not-absorbed, and the
five-step procedure for adding a thread. **Follow that procedure** — especially step 1 (fetch the
replies, not just the opening post; the corrections live there) and step 2 (read the attached
screenshots; several threads carry their key information only in images).

Three threads are absorbed. The forum has many more. The user intends to work through all of it.

### ~~The one test worth doing before more reading~~ — ANSWERED 2026-09-16, at ATK's repack

> **Yes, renumbering changes what reaches the game — through ATK, not the engine.** Both of ATK's
> repack paths (`DataFile.Serialize` for a container, `ForgeFile` for a forge) sort files by the
> number before `_-_` and **silently skip any file whose ClassID was already packed**. So when a
> vanilla copy and a mod copy of one resource share a folder, the **lower number wins** and the other
> is dropped without a message. Measured on this install: 259 ClassIDs with more than one file in
> the live `TEAMMATE_Template` unpack folder, and the container holds the lowest-numbered copy in
> **259 of 259**. Both field cases below fit it exactly — including *"the one that starts with 39 in
> patch01 … overwriting your edited ones"*. Source and measurement: the 2026-09-16 entry *"The
> container walker was one byte off"*; write-up in
> [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md). Re-running the vest case in
> game would confirm it, but no longer decides it.
>
> The original framing is kept below for provenance.

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
- ~~**ID byte offset in DB resources.** spncryn says "bytes 1-8"; our
  [`resource-type-ids.md`](../reference/resource-type-ids.md) layout says a payload begins with a
  `FileHeader` byte, putting the ClassID at offset 1. Either these types write no header byte or
  the phrasing is loose. Needs a hex check against a real `.DBToolSetting`.~~ **ANSWERED
  2026-09-16: both are right.** An ATK-unpacked resource file is `[FileHeader][payload]`; the
  header is one `00` byte for almost every resource, so the ClassID is at bytes 1–8. (In the
  container itself the header sits *between* the name and the counted payload.) Only resources
  carrying an object-block-allocator table — 17 `Animation`s in the DB container — have a longer
  header, putting the ClassID at 8 + 12N.
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

> ℹ️ **2026-09-20:** the eleven ghillie cloths modified on 2026-07-01 are *still live* in base
> `DataPC.forge` on SylG5 (`Backups\DataPC.forge.pre-clothtest-20260701` holds the originals), and
> the game has booted and run with them for eleven weeks. A lone modified cloth in `DataPC.forge`
> does not hang the game; whether that copy is ever read is the shadow question, unchanged.

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
coat's vertices; a poncho needs its binding recomputed. ~~Blocked on cracking the wrap/binding
encoding **and** on STEP 1.~~ **The encoding is cracked (2026-09-18)** — see the callout at the top and
`tools/clothmap.py`. STEP 1 is now the only blocker between a written mapping and the game, and an
encoder can be validated against vanilla before STEP 1 is run.

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
- **`Tsec_Trench_AddonSkeleton` carries 43,494 B of it** — ~~a vanilla flowing trench coat driven
  entirely by bones~~ an **addon** skeleton assigned beside the trench coat's **cloth**; the coat
  mesh is not weighted to any bone its Reflex3 records drive *(corrected 2026-09-16)*. Also
  `TP_HunterScarf_A_Skeleton` (9,991 B), hair rigs, backpack straps — which *are* skinned to their
  driven bones — and `Player_Kilt_Addon` (394 B, beside the kilt's cloth, likewise unweighted).

**The layer above is solved too** — *rewritten 2026-09-16; the 2026-08-14 version attributed the
references to whole containers and read the record from the wrong end.* A rig is assigned by a
**`BuildTable` row component**, verified from ATK's `BuildRow.Read` / `DynamicProperty` and from
ATK's own XML export:

```
i32 Index | u32 DataType (0x24AECB7C = Skeleton) | u32 Type (0x120000 = Handle) | u32 Unk00 | u8 (ignored) | u64 ClassID
```

`Index` is the `BuildColumn` the component fills; the table declares that column as an empty
`Skeleton` `Reference`. All 3,966 such Handles across `PLAYER_Template` and both
`TEAMMATE_Template` copies resolve to real skeletons. So **a rig assignment is a plain 64-bit ID**,
and `BuildTable` round-trips through ATK as XML:

```xml
<DynamicProperty Index="10">
  <Value Name="DataType" Type="UInt32" HashName="Skeleton">615435132</Value>
  <Value Name="Type" Type="UInt32">1179648</Value>
  <Value Name="Unk00" Type="UInt32">0</Value>
  <Handle>
    <Value Name="Value" Type="UInt64" Path="DataPC\Player_Kilt_Addon\Player_Kilt_Addon.Skeleton">1889064665537</Value>
  </Handle>
</DynamicProperty>
```

**Who assigns which rig:** the kilt's from **`TP_PANT_Kilt`** (Index 10, beside its mesh at 11); the
scarf's from eight mask/head tables; Blake's flowing trench coat's from
**`Tsec_IanBlake_Trench_Mcloth_MISSION`** and Kropotkine's from `MIS_Y2E4_Wassili_Kropotkine_Trench`
(both Index 4). `PLAYER_SkelAddons` carries only the five player-wide rigs. The trench rig is still
never assigned by a player template — but it is assigned by a *coat's* table, which is exactly the
shape a player garment would copy.

**Do next, in order:**

1. ~~**Get an ATK XML export of `PLAYER_Template`.**~~ **DONE 2026-09-09** —
   `python atk_bridge.py <PLAYER_Template.data> --xml out.xml`, 651 KB / 11,234 lines, headless.
   ⚠️ **It answered "which `EntityBuilder` field?" with "none".** The rigs are reached through a
   `BuildTable` named **`PLAYER_SkelAddons`** (`1898138514560`), referenced from
   `BuildRows → BuildRow → Components → DynamicProperty(Index 42, DataType=BuildTable)` and again
   from `SubTables`. **`PLAYER_Template` and `TEAMMATE_Template` share it.** It also **corrected**
   the 2026-08-14 claim that an EntityBuilder assigns skeletons: the EntityBuilder resource
   contains **zero** skeleton records — all 11 are elsewhere in the container.
1b. ~~**Find `PLAYER_SkelAddons.BuildTable`.**~~ **DONE 2026-09-09.** ATK's file list entry was
   the way in: `GameFileListEntry` is `{ForgeIndex, DataIndex, Name, Extension}` and its path is
   literally **forge / container / resource** — not an authoring path, which is how it was
   misread. `PLAYER_SkelAddons` is a `BuildTable` **inside the `TEAMMATE_Template.data`
   container** in `DataPC`. Verified in bytes: the record
   `int32 len(17) | "PLAYER_SkelAddons" | 0x00 | u64 1898138514560` sits at **offset 94,195** of
   the patch copy. *(The list holds 1,053,342 resources across 413,452 containers — a resource
   that is not its own container is the normal case, not an oddity.)*
1c. ~~**⭐ NEW step 1 — fix `data_inspect.py`'s container segmentation.**~~ **DONE 2026-09-16.**
   The walker never skipped the FileHeader byte between a resource's name and its payload, and
   stopped at unnamed resources. Fixed from ATK's source in `data_inspect.walk()`, which every tool
   now shares: `TEAMMATE_Template` walks to its last byte as 2,451 resources (3,963 live), confirmed
   against the container's own metadata index. `PLAYER_SkelAddons` reads and exports to XML:
   `python atk_bridge.py <TEAMMATE_Template.data> --xml out.xml --resource PLAYER_SkelAddons`.
2. **⭐ NOW step 1 — the goal-shaped experiment, retargeted to a garment's own build table.** Not
   the player template: a garment's rig comes from the garment's table (see above).
   - **Diff the two working precedents first.** `GRBMods\bisonbelt_mainfiles` moves
     `Player_Holster_NoSling_Addon` out of `PLAYER_SkelAddons` and into `TP_LEGHOLSTER_Platform`
     (Index 3); `GRBMods\Tactical Human Set` assigns it from `TP_TacticalHuman_Belt-Skeleton`. Both
     byte-match the live container, and both are rigid rigs, so they prove the assignment path
     but not bone physics. **Diffed 2026-09-20 (second): they prove more.** Each ships an *edited*
     skeleton — `Player_Holster_NoSling_Addon` with the holster bone re-parented from `RightUpLeg`
     to `Hips` — under a new ID, and *Sling Positions* overrides **124 vanilla backpack rigs by ID**
     with two bones moved and their 19–62 KB Reflex3 blobs intact. Modified skeletons carrying
     physics blobs load. The one untested step is a blob the game did not compile —
     [`reference/install-edit-classes.md`](../reference/install-edit-classes.md).
   - **⭐ The first write test, ready to run (2026-09-20, third).** One swing limit in one rig the
     install already overrides, nothing else:
     ```
     python tools\reflex3_write.py "<install>\Extracted\GRBMods\Sling Positions - 1 - Front Sling - 2 - Side Sling-803-1-1-1718027730\Alternate Holsters - 1FrontSling 2SideSling\Resources\45229_-_BP_wStraps_Hill_MEDIUMVEST.data" --set-swing 9650dc43 1 -30 30 --set-swing 9650dc43 2 -10 30 --out 1_-_BP_wStraps_Hill_MEDIUMVEST.data
     ```
     The pack body of the Hill backpack (mass 5, normally ±2°) gets ±30°. Drop the file as
     `1_-_…` into `Extracted\DataPC_Resources_patch_01.forge\`, **back up the live Resources
     patch forge** (36.9 GB, holds every texture mod), repack in ATK, launch, wear the Hill
     backpack with straps and sprint. **If the pack sways: a blob the game did not compile loads,
     and the poncho rig is a generate away.** If it hangs or the pack is rigid, the runtime
     rejects or ignores non-compiled blobs and route B needs ATK's Mirage-style source records
     instead. Either answer moves the wall.
   - **Then add one row component to a wearable garment's table**, pointing a `Skeleton` Handle at a
     physics-carrying rig and copying `TP_PANT_Kilt` (Index 10) or
     `Tsec_IanBlake_Trench_Mcloth_MISSION` (Index 4). Vanilla tables declare a same-typed column
     for every row Index, but both holster mods put a `Skeleton` Handle in a column declared
     `BuildTable` — so a matching column is *probably* not required, unverified either way. Edit
     through the XML round trip: ~~ATK's binary `BuildRow.Write` would write every Index as 0 *(read
     in source, untested)*.~~ **✅ TESTED 2026-09-17 — the XML route is byte-exact.** 2,443 of 2,444
     BuildTables in `TEAMMATE_Template` export and recompile byte-identical through
     `XmlUtils.CompileXml(Stream)`, Index values intact; a repoint changes only the handle's bytes,
     and adding a `Skeleton` Handle costs exactly **+25 B** (count bump + one 25-byte component) and
     reads back through ATK. The one exception is a row component that embeds an object
     (`Type 0x150000`) — not a shape any rig/mesh/cloth assignment uses. See the 2026-09-17 entry.
   - ⭐ **Pick the rig for what it moves, not its size** *(2026-09-16, evening; **the shortlist now
     exists**, 2026-09-17)*. Run [`tools/rig_census.py`](../tools/rig_census.py): of **148**
     physics-carrying rigs assigned by `TEAMMATE_Template`/`PLAYER_Template`, **117 drive a mesh**.
     Best candidates for a garment:

     | rig | driven bones | proven on | weights on driven |
     | --- | ---: | --- | ---: |
     | `Vest_Generic_Addon` | 9 | 197 meshes across **174 rows** | up to 41,944 |
     | `Addon_body_samFisher` | 22 | `Tpri_Top_SamFisher_LOD0` (a torso garment) | 5,105, **0 on parents** |
     | `addon_collar_samFisher` | 11 | same top | 8,786 |
     | `Addon_Collar_PunkJacket` | 5 | `TP_Top_Metal_PunkJacketB_D0_LOD0` | 5,376 |

     ⚠️ And the census found the trench trap is **not a one-off**: `Addon_Collar_PunkJacket` moves
     one jacket variant and has **0** weight on its driven bones in another, as does
     `Addon_Collar_ArmyJacket` and `BodarkPlates_Addon`. A rig assignment in a build table does not
     mean the mesh is painted for it. Check with `rebind_check.py` before any launch.
   - ⚠️ **Number the edited file below the vanilla copy** (`1_-_…`). Both of ATK's repack paths keep
     the lowest-numbered file per ClassID and silently drop the rest.
   - ⚠️ **Back up the live `DataPC_patch_01.forge` (1.63 GB, modded) first.** On SylG5 the only
     full copy found is the pristine 2023 one in `Backups\`; restoring that would wipe every
     installed mod.
   - First end-to-end test of route 2B, and the first edit of ours that would be confirmed in game.
3. ~~**Finish the constraint-blob decode.**~~ **DONE 2026-08-14.** The blob is readable —
   [`tools/reflex3.py`](../tools/reflex3.py) prints the driven bone, its parent, swing limits in
   degrees, mass, spring, damping and gravity. **2026-09-20:** every one of the 204 distinct blobs
   now reads to its last byte with a self-delimiting parse (the August "204 of 205" test was
   vacuous — the scan always consumed everything).
   ~~confirm the 8-byte header is a bone-name hash~~ **also DONE** — it is
   `u32 BoneID | u32 ParentBoneID`, both **CRC32 of the exact-case bone name**, resolving against
   each skeleton's real bone list at **≈99.7 %** vs a 0.000 % null control. ~~What's left inside the
   blob: the tails of type 9 and type 6, and the meanings of `param[0..3]` / `param[5..8]`.~~
   **DONE 2026-09-20.** The physics record is five gated limit slots (slide X/Y/Z in metres, two
   swing axes in radians) plus nine parameters — mass\*, spring\*, slide damping\*, `p3`, gravity
   9.8, gravity factor\*, wind factor\*, 0, 0 (\* inferred) — and its five matrices are identified,
   the third derivable from the body rig. The hinge grammar is read; types 8 and 11 were found
   hiding in the old "tails"; bones can be named by string. Still open: `p3` and the pose-driven
   type-9 body. Vanilla chain recipes: [`reference/reflex3-chain-templates.md`](../reference/reflex3-chain-templates.md).
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
   reached without touching `.cloth` at all. **The rig itself now has a recipe** (2026-09-20,
   inferred, untested): six four-link strands under `Spine2` with the hair strand's limits and
   mass taper, a generated blob carried into the skeleton through ATK's XML round trip (the blob
   is Base64 there) — [`reference/reflex3-chain-templates.md`](../reference/reflex3-chain-templates.md).

**The pipeline, as of 2026-09-09:**

```
   ATK export  ──►  Blender transfer  ──►  rebind_check  ──►  ATK import  ──►  repack
   AUTOMATED        AUTOMATED             AUTOMATED          CHECKED          manual
   (09-01)          (08-31)               (09-01)            (09-09)          by policy

   rig physics:  reflex3.py (read)  ──►  reflex3_write.py (edit / generate / splice)  ──►  repack
                 EXACT, all 204          BYTE-EXACT round trip, verified splice          manual
                 (09-20)                 (09-20)                                         by policy
```

Everything up to the write runs headlessly on real garment data, and the import end now **tells you
when it would produce a wrong file** — `atk_bridge.py <donor.data> --import new.glb`, exit 2 on a
mismatch. Write-back *fidelity* was the 2026-09-08 blocker and is closed: the format and stride the
file would receive match the donor exactly, for four garments.

⚠️ **"Would match" is arithmetic, not evidence.** No bytes have been produced and nothing has been
loaded. The final write into a `.data`/forge stays manual **by policy, not capability**.

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

## Lane 4 — the gameplay / AI database

**What it is.** How enemies see, hear, fight, call for backup and cheat lives in one forge entry,
`DBContainerEntry_0X104634F921.data` — **61,426** records in the base container, 61,446 in this
install's patch. Written up in [`docs/14-ai-and-npc-behaviour.md`](../docs/14-ai-and-npc-behaviour.md),
catalogued in [`reference/ai-db-records.md`](../reference/ai-db-records.md), read with
[`tools/db_inspect.py`](../tools/db_inspect.py). It exists because Sylvia plays with AI overhaul
mods installed (a forge-integrated Spartan port and Fear the Radio) and asked what else could be
changed. It is a second track in its own right, not a detour from lane 2.

**Verified so far (all 2026-09-16, read-only):**
- ATK has no `DB*` classes, so this layer is **binary patching**. It is tractable: 777 of the 1,012
  `DB*` types are fixed-size, and Ubisoft ships null variants (`_NoDetection`, `_NoCall`,
  `_NoCheat`) to diff against.
- **Fear the Radio** is `CallBodark`'s six-wave schedule transplanted onto `CallPMC`, with all six
  wave handles repointed at existing high-threat spawners.
- **Omniscience is a profile, not a flag:** `DBAICheatConfig_Miter_Omniscience` sets six grant
  flags, clears five honesty gates and raises three floats.
- A handle inside a record is its target's ClassID; index `payload[0:8]` over the container and
  every handle becomes a name.
- The patch container is a **full copy** of the database. DB mods still stack, because each ATK
  repack rebuilds it from the unpacked folder — but a mod that ships a whole
  `DBContainerEntry…data` wipes every other DB mod.
- ⚠️ The morning's "50,098 records" was a prefix — the walker stopped at the first unnamed record.
  Every per-type count in `docs/14` held up in the full walk; the container totals did not.
- **2026-09-20:** twenty `DB*` / `GR_*` record types are already modified in place by installed mods
  and the game runs — radio call, sound detection, sensor shapes, spawn descriptors, player health
  among them. The one-handle repoint sits squarely inside precedent
  ([`reference/install-edit-classes.md`](../reference/install-edit-classes.md)).

**Do next, in order:**
1. ~~**Map NPCs to cheat configs.**~~ **DONE 2026-09-16 (evening)** — and the lead was wrong:
   `DBNpcGeneralConfig` holds no handles. A spawn descriptor points at a **soldier config**
   (`SC_TGT_*`, 463 B) whose 10-byte slots hold the general config (@15), health (@25), **cheat
   config (@75)**, sound/visual detection (@155/@165) and **radio call (@355)**. Only 119 of 639
   descriptors cheat at all; regular Wolves, Bodark and Sentinel troops are `NoCheat`. Also resolved:
   Fear the Radio's four `TGT_*_Marks*` files make Heavy MK1–3 and Rusher MK1 descriptors identical
   to `TGT_Caller`. See `docs/14` §10.
2. **The first write test — now a one-handle repoint.** Change **one 8-byte handle** in one soldier
   config: e.g. `SC_TGT_Rifleman_Wolves_Default` @355 from `NoCall` to `CallBodark` (do Wolves
   riflemen start radioing?) or @75 from `NoCheat` to `Miter_Omniscience`. Visible, reversible, and
   no record changes size. ⚠️ Never edit the shared `DBAICheatConfig_NoCheat` (`0x1BC67BF6BD2`) — 320
   soldier configs use it. Back up the live `DataPC_patch_01.forge` first; number the edited record
   `1_-_` so ATK packs it rather than the vanilla copy; repack the container, then the forge.
3. **What the tier int scales.** MK1/2/3 is `DBNpcGeneralConfig` @25 *(inferred)*, chosen per
   soldier config; `DBNpcHealth` is identical across tiers, so whatever scales is keyed on the int.
4. **The 1,557 `[MVET] AI_*` / `[VECN] AI_*` records** the old walker never reached. Unexamined;
   the names match the `[VE] AI_…` voice events seen on 2026-08-14, so dialogue plumbing is more
   likely than behaviour.
5. Which installed mod is the Spartan port — no folder under `Extracted\GRBMods\` is named for it.

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
1b. ~~**⭐ NEW top candidate — the 22 sections ATK does not model.**~~ **DONE 2026-09-18 — 13 of the 22 are
   the render↔sim mesh mapping**, and the 4403–4410 "counters" are quantization headers. See the
   2026-09-18 research-log entry. Original framing kept below. The same sweep found GRB cloths
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
   **⚠️ Superseded 2026-09-16 (evening): vanilla *does* serve one cloth from two items.**
   `TP_WalkerCoat_Cloth` is assigned by the Walker vest's cloth sub-table
   (`TP_TACVEST_Walker_Coat_Cloth`) **and** by `TP_VestHeavy_RaidMedic` — the "Golem Cape | Field
   Medic" — each through a `SoftBody` Handle beside the same `TP_Tacvest_Walker_Coat` mesh, the cape
   with its own materials. So the repoint works in vanilla **when the mesh is the same**; a
   different mesh is still the rebind problem.
   **⭐ Upgraded 2026-09-18: the Bodark cloth IS a vanilla rebind.** Its cage is byte-identical to
   Blake's, but its mapping is **regenerated** for Kropotkine's own mesh (`TP_Top_Bodark_Trench_LOD0`,
   5,198 verts; §4386 names it; 0 of 2,243 records shared; rebuilds his mesh to 0.42 mm). Ubisoft
   did the project goal's exact operation — keep the cage, write a new mapping.
3. **Wrap-collapse validation on the kilt.** Once STEP 1 proves an override loads, run
   `clothwrap.py --diagnostic collapse/twist` on the kilt via the same both-patch pattern. If the
   visible mesh visibly scrambles, the wrap **is** the render driver → the route-A encoder is worth
   building. This is the gate; it was never validly tested (ghillies were pinned/invalid, Walker
   isn't player-viewable).
4. ~~**Decode the wrap weight encoding** (the 6×u16 per-record) + the record↔render-vertex
   correspondence — the remaining blocker for a reskin encoder (only after lead 3 is green).~~
   **DONE 2026-09-18, without lead 3.** Twelve quantized bytes = `(u, v, h)` × (position, normal,
   tangent, binormal); the table in front of the records is the render-vertex map. Verified to a
   median 0.45 mm on 87 cloth LODs against their own meshes.
4b. **⭐ Port ATK's `SoftBody` rebind maths** (new 2026-09-08). `ComputeBarycentric`,
   `ClosestPointOnTriangle`, `GetSimulationBones`, `ToMesh`/`ToMeshNext`/`ToMeshOld` and
   `SoftBodyVertexMapping` are a working cloth→mesh binding implementation sitting in ATK's
   source — for AC-family formats, readable by decompile. They cannot be *run* on GRB data (the
   gate is load-bearing, see above), but the algorithm is exactly what lead 4 would otherwise
   reinvent from nothing. **Read them before writing an encoder.**

**On the skeleton path (route B):**

5. ~~**Golem Cape** — still the interesting path-B exemplar: it visibly flows but has **no
   `Cloth`/`SoftBody` resource** (07-02).~~ **CLOSED 2026-09-16 (evening) — it is cloth.** Its item
   table, `TP_VestHeavy_RaidMedic`, assigns the Walker coat mesh and **`TP_WalkerCoat_Cloth`** with
   Raid Medic materials; there was never a cloth named for the cape to find. Not a route-B exemplar.
6. ~~**Ragdoll bone-collider list** in `TP_WalkerCoat_Cloth`'s editor data.~~ **CLOSED 2026-08-14.**
   Decoded: a 550-char *(536 as first recorded; re-measured 2026-09-16)* semicolon-separated list of **13 garment-owned capsule colliders**, every one
   prefixed `TP_WalkerCoat_`, covering **upper body only** (Head, Neck, L/R Arm, ForeArm, Hand,
   LeftShoulder ×4 — no spine, pelvis or legs). It is the coat cloth's collision proxy set, named
   after the bones it follows. **Not** a death-ragdoll rig, and not a binding mechanism.
   *(Refined by the 2026-09-16 census: the list names 13 of the 23 capsules of
   `TP_WalkerCoat_Ragdoll`, a whole-body `LiteRagdoll` in the same container that the cloth references
   by ClassID — the upper-body subset, `LeftShoulder` ×4 included. Still collision, still not a death
   rig.)*

**~~Do not re-chase~~ REOPENED 2026-09-16, RE-ANSWERED by the census that night — the community ragdoll question (2026-08-14):**

> ⚠️ **The absence argument below does not hold.** All three legs of the original answer counted
> **forge entries**, which name only a container's first resource, so none of them could see a nested
> resource of any type. The census confirms it exactly: first-position `LiteRagdoll`s number **0** and
> first-position `Animation`s exactly **1,564** — the two numbers the answer rested on.
>
> **Re-answered 2026-09-16 (night): the resources are there; the switch is not found.** The census
> walked all 415,024 containers in 27 forges: 3,935,343 resources, every walk ending on its last
> byte. It found:
>
> - **`GR_MaleAverage`, a `RagdollSkeleton`:** 19 `RagdollBoneData`, 18 `RagdollConstraintData`, 4
>   `RagdollMotorParameters` and 1 `RagdollBoneDriveParameters`, over the standard biped bones. It is
>   referenced by 51 human `Entity` resources: `CHR_NPC_BASEENTITY`, the
>   `CHR_NPC-REGULARSKEL-SOLDIER_TARGET` family, Walker, Miter, civilians, cinematic NPCs,
>   **`CHR_PLAYER_TGT`**. *Inferred:* the powered physics ragdoll the human entities share.
> - **88 distinct `LiteRagdoll`s** (637 nested copies). They are capsule sets, not jointed rigs:
>   whole-body `DamageTriggerRagdoll_{default, Heavy, ArmoredBodark, RocketLauncher, WALKER, Miter…}`
>   per archetype (20–28 capsules); garment cloth colliders; animals; drones; raid bosses.
> - **A death and hit-reaction bank,** all inside the container named `MIS_Y2E4_Katya_Maksimov`:
>   - 188 generic-soldier deaths, `mil_gen_m_ale_ros_{std,crh}_V0_N_death_{regular, heavy, explosion,
>     electric, …}_‹region›_‹direction›`
>   - 172 zonal `_hit_{regular,heavy}_` reactions
>   - 77 downstate clips, 24 stumbles and one get-up
>
>   No `Animation` is named `*ragdoll*`.
>
> All of it is vanilla: byte-identical to, or present by ClassID in, the `Backups\` forges, which
> include the Sept 2023 pristine patch.
>
> **The answer for Releptive, as it now stands:** GRB ships a physics-ragdoll definition that its
> human entities share *and* a directional canned-death bank. What decides a clip versus the ragdoll
> — and whether that decision is data at all — is **not located**, so "can normal deaths ragdoll
> instantly?" is open, not "no". *(Inferred, unchanged since 2026-08-14: the hostage-guard drop
> could be the ragdoll taking over when no clip fits. There is still no data either way.)*
>
> **Next, in order:**
> 1. Decode `GR_MaleAverage`'s 4 `RagdollMotorParameters` and 1 `RagdollBoneDriveParameters` against
>    the `RagdollBoneProperty_ActivationBlendTime` / `_ActivationDelayed` / `_StiffnessFactor` /
>    `_…DriveMode` strings in `GRB.exe`.
> 2. Export `PMC_HEAVY_RagDoll` — the only `BuildTable` named for a ragdoll; it points at
>    `DamageTriggerRagdoll_Heavy` — with `atk_bridge.py --xml --resource`.
> 3. Search the DB container for records that name ragdoll, death or hit behaviour.
>
> Detail and layouts: the 2026-09-16 (night) research-log entry.

*Original answer (2026-08-14), superseded — kept for provenance:*

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
10. **BuildTable side of binding:** ~~which property/node a BuildTable uses to reference a cloth~~
    **ANSWERED 2026-09-16 (evening):** a `SoftBody`-typed Handle row component pointing at the
    `.Cloth`, in the same row as the `GraphicObject` Handle for the mesh it simulates (Walker coat
    sub-table: SoftBody @7 + GraphicObject @8; trench coats: @5 + @1). Still open: whether the render
    mesh must carry `IsGeneratedFromCloth` + a matching `ClothEditorDataClothID`.

---

## Don't repeat

**On reading containers (added 2026-09-16):**

- **Don't quote a count from a walk that stopped early.** A container walk is complete only when it
  ends on the files block's last byte, and the metadata block's `u16` count is a free second check.
  The DB's "50,098 records, landing exactly on the end" was a 16.5 MB prefix of 56.8 MB, written up
  without that check being run.
- **Don't credit a byte-pattern hit to the nearest string or to the container's name.** Walk the
  container and name the resource that holds the bytes. "An `EntityBuilder` assigns skeletons" and
  "the precedents sit under `PLAYER_SkelAddons`" both came from that shortcut.
- **Don't treat a forge-entry sweep as a resource census.** A forge entry is a container named after
  its first resource. Nested resources are the normal case: 89.5 % of GRB's 3.9 M resources, and
  1,785 of its 1,852 resource types never come first (census, 2026-09-16). A sweep of entry names or
  extensions cannot see them. That is how "GRB ships no `LiteRagdoll`" and "no combat animations"
  got written. *(Per container the median is 1 resource and the mean 9.5; the "about 2.5" once
  quoted here does not hold install-wide.)*
- **Don't read an unsigned container as vanilla.** ATK's trailer marks what ATK wrote; the GRB Mod
  Manager writes containers without it, and most of this install's mods went in that way. In
  `DataPC_patch_01`, 2,140 of the 2,349 mod-changed resources sit in unsigned containers (2026-09-20).

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
