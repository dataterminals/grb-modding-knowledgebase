# 🧵 GRB Cloth Inspector

A little tool that reads a **Ghost Recon: Breakpoint cloth file** and tells you, in
plain language, **what that cloth is** — how many cloth pieces (LODs) it has, the exact
**mesh + LOD** each is bound to (via its `Sim_<Mesh>_LOD<n>` name), and the size of the
simulated "cage" mesh.

It's aimed at modders — **you do not need to know any coding to use it.**

> **⚠️ Reskin reality check:** the *visible* garment is a **separate**, larger,
> skeleton-skinned mesh that follows the low-res simulation **cage** via a stored wrap.
> That wrap is decoded on paper but **not yet validated in-game**, so rebinding a
> brand-new visible mesh is **unsolved for GRB** today. What works: reshape the vanilla
> garment while keeping the cage's vertex **count and order** (constraints are addressed
> by cage-vertex index).
> *(An earlier version labeled cloths "DIRECT/BARYCENTRIC" as a "reskin route" — that
> rested on a since-disproven binding model; see [`../docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md).)*

> Why this helps: GRB cloth is baked to one specific mesh at one specific LOD. This
> tool shows you that binding at a glance (e.g. a body named
> `Sim_TP_Tacvest_Walker_Coat_LOD1` is the *wearable* Walker coat cloth at LOD1),
> so you can tell which `.cloth` goes with which garment before you start. Full
> background: [`../docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md).

---

## What you need first

1. **A cloth file to look at.** Cloth resources are the entries whose names contain
   **`Cloth`** — e.g. `TP_WalkerCoat_Cloth` or `Cloth_WalkerCoat` — living in
   `DataPC.forge`. Unpack that `.forge` with **ATK** and look in its `Extracted` folder.
   You can point this tool at either the cloth **`.data`** entry *or* (best) the
   decompressed **`.Cloth`** file you get by unpacking that `.data` one level further.
2. **A way to run the tool** — pick one:
   - **Easiest (no setup):** download **`ClothInspector.exe`** from this repo's
     [Releases](https://github.com/dataterminals/grb-modding-knowledgebase/releases)
     (if a release is available) and just double-click it. Nothing else to install.
   - **Or install Python once** (free, ~2 min): get it from
     <https://www.python.org/downloads/> and **tick “Add python.exe to PATH”** during
     setup. Then use the `.bat` launchers below.

---

## How to use it (three ways, easiest first)

### 1. The window (recommended)
Double-click **`Cloth Inspector (GUI).bat`** (or `ClothInspector.exe`). A window opens:

- Click **“Open a cloth file…”** and pick a cloth `.data` → it prints the report.
- Click **“Compare two cloth files…”** to see two cloths side by side.
- **“Save report…”** writes the text to a file you can paste into Discord.

### 2. Drag-and-drop
Drag **one or two** cloth `.data` files onto **`Cloth Inspector (drag files here).bat`**.
One file = inspect it; two files = compare them. A console window shows the result.

### 3. Command line (for the comfortable)
```
python cloth_inspect.py  yourcloth.data
python cloth_inspect.py  clothA.data  clothB.data
```

---

## What the report tells you

```
FILE: TP_WalkerCoat_Cloth.Cloth
  2 cloth LOD(s), 2 simulated piece(s).

  A piece named  Sim_<TargetMesh>_LOD<n>  is bound to that exact mesh + LOD -
  match your mod to it (e.g. Sim_TP_... is the wearable one, not a cutscene).

  - LOD0: Sim_TP_Tacvest_Walker_Coat_LOD0   [gameplay / wearable cloth]
      simulation cage: 170 points, 288 triangles
```

- **Cloth pieces (LODs)** = the separate simulated pieces in the file.
- **Piece name** `Sim_<Mesh>_LOD<n>` = **the mesh and LOD this cloth drives.** If it says
  `..._CIN_...`/`TPri_...` it's a **cinematic** (cutscene) cloth; `Sim_TP_<gear>` is the
  **wearable** one you want for player gear. **Identifying this cloth↔garment binding is
  the practical takeaway.**
- **simulation cage** size = the low-res physics mesh (not the visible garment — see the
  reskin reality check up top).

## Good to know

- The tool is **read-only** — it never changes your files. Safe to point at anything.
- Counts are **exact now** — it uses the precise MotionCloth reader (`motioncloth.py`),
  which walks each data section by its real size (the old version magic-scanned and could
  miscount).
- It reads both a decompressed **`*.Cloth`** file (what ATK writes when you unpack a cloth
  `.data`) **and** a cloth **`.data`** directly — for a `.data` it auto-decompresses with
  the game's `oo2core_7_win64.dll` (found next to your GRB install). `*.Cloth` needs no DLL.

## Build the standalone .exe yourself (optional)

If you'd rather hand people a single `.exe` (no Python needed), build it with
[PyInstaller](https://pyinstaller.org/):

```
pip install pyinstaller
pyinstaller --onefile --windowed --name ClothInspector cloth_inspect_gui.py
```

The result is `dist/ClothInspector.exe`. This repo also has a GitHub Actions workflow
([`../.github/workflows/build-cloth-inspector.yml`](../.github/workflows/build-cloth-inspector.yml))
that builds it for you in the cloud — run it from the repo's **Actions** tab and
download the `ClothInspector.exe` artifact.

---

*Files here:* `motioncloth.py` (the exact MotionCloth reader/writer engine — locates every
ClothPackage, walks sections by their real sizes, round-trips byte-for-byte),
`cloth_inspect.py` (the plain-language report on top of it), `cloth_inspect_gui.py` (the
window), and the two `.bat` launchers — these are **read-only**. Also here:
`clothwrap.py` — an **experimental / research** tool that *writes* modified cloths (locates
the render↔sim wrap; can set the dedicated gravity section `4398` for in-game tests;
rebuilds a game-loadable **Oodle-compressed** `.data`). Because it edits cloth internals,
**always work on a backed-up copy** — and note most cloths are *shadowed* (same ID in
`DataPC.forge` **and** a WorldMap base forge), so an override must be repacked into **both**
families' patch forges to take effect (a single-patch override hangs the load; see
[`../docs/06-game-load-and-reassembly.md`](../docs/06-game-load-and-reassembly.md)). All documented.

---

## 🔎 GRB Data Inspector — what's inside any `.data`?

Opens **any** GRB `.data` container and lists the typed resources inside it — each
resource's **name**, **type** (Mesh, TextureMap, BuildTable, Cloth, …), 64-bit
**ClassID**, and size. Like the Cloth Inspector, **you don't need to know any coding.**

### How to use it (three ways, easiest first)

**1. The window (recommended).** Double-click **`Data Inspector (GUI).bat`** (or
`DataInspector.exe`). Click **“Open .data file(s)…”**, pick one or more `.data`, and
read the report. **“Save report…”** writes it to a file you can paste into Discord.

**2. Drag-and-drop.** Drag one or more `.data` files onto
**`Data Inspector (drag files here).bat`**.

**3. Command line.**
```
python data_inspect.py  30091_-_WI_HDG_P12_Main.data
python data_inspect.py  *.data                       # several at once
python data_inspect.py  23_-_TEAMMATE_Template.data --all   # every resource, not the first 40
python data_inspect.py  foo.data --oodle "D:\...\Ghost Recon Breakpoint\oo2core_7_win64.dll"
```

**Containers are often bigger than their name.** `TP_WalkerCoat_Cloth.data` holds a Cloth, its
SoftBodySettings *and* a LiteRagdoll; `TEAMMATE_Template.data` holds 2,451 resources. Above 40
resources the report prints a count per type and the first 40; `--all` lists every one. The walk
must end on the last byte of the container — if it doesn't, the report says
**INCOMPLETE** rather than presenting a partial list.

> ⚠️ **Fixed 2026-09-16.** Earlier versions read every resource after the first one byte early
> (they missed the header byte between a resource's name and its payload), so any container with
> more than one resource showed up as one resource plus garbage. Other tools now share this
> walker (`data_inspect.walk()`), so the fix reaches all of them. See
> [`../meta/research-log.md`](../meta/research-log.md).

### Oodle note (important)
GRB `.data` payloads are Oodle-compressed (Mermaid, 32 KB blocks), so the tool needs
the game's **`oo2core_7_win64.dll`** to read them. It **auto-finds** the DLL by
searching up from the file you open (the DLL lives in your GRB folder, and `.data`
files sit under it in `Extracted\`). If it can't, use **“Set Oodle DLL…”** in the
window, or pass `--oodle` on the command line. The DLL is **not** bundled with the
`.exe` (it's Ubisoft's). The tool is **read-only**.

### Get / build the `.exe`
- **Download:** grab **`DataInspector.exe`** from
  [Releases](https://github.com/dataterminals/grb-modding-knowledgebase/releases)
  (if a build has been published), or from the **Actions** tab
  ([`build-data-inspector.yml`](../.github/workflows/build-data-inspector.yml)) →
  the `DataInspector-exe` artifact.
- **Build it yourself:** `pip install pyinstaller` then, in `tools/`,
  `pyinstaller --onefile --windowed --name DataInspector data_inspect_gui.py`
  → `dist/DataInspector.exe`.

Background: [`../reference/resource-type-ids.md`](../reference/resource-type-ids.md),
[`../docs/02-forge-file-format.md`](../docs/02-forge-file-format.md).

---

## 🗂️ GRB Forge Inspector — what's in a `.forge`, and do two mods conflict?

Reads a whole `.forge` by its **index only** (no unpacking, no Oodle), so even the
23 GB resources forge opens in a moment. Two jobs:

- **Inspect one forge** → version, entry count, and a **resource-type histogram**
  (how many Meshes / TextureMaps / BuildTables / Animations / … it holds), keyed on
  the **real 64-bit file IDs**.
- **Compare two forges** → a **diff by file ID**. Shared IDs mean: **overrides** (if
  one is a patch of the other), **conflicts** (if they're two mods — only one can
  win), or a **forge shadow** (if they're two *base* forges — the same resource
  intentionally duplicated, e.g. cloth in `DataPC.forge` and a WorldMap `_Split` base;
  see [`../docs/06-game-load-and-reassembly.md`](../docs/06-game-load-and-reassembly.md)).
  This is the mod-conflict / merge / shadow checker.

### How to use it (three ways, easiest first)
1. **Window (recommended):** double-click **`Forge Inspector (GUI).bat`** (or
   `ForgeInspector.exe`) → “Open a forge…”, “Compare two forges…”, or “Save entries
   as CSV…”.
2. **Drag-and-drop:** drop one `.forge` (summary) or two `.forge` files (diff) onto
   **`Forge Inspector (drag files here).bat`**.
3. **Command line:**
   ```
   python forge_inspect.py  DataPC_patch_01.forge
   python forge_inspect.py  DataPC_patch_01.forge  DataPC.forge      # diff by ID
   python forge_inspect.py  DataPC_Resources.forge --csv out.csv     # dump every entry
   ```

### Get / build the `.exe`
- **Download** `ForgeInspector.exe` from
  [Releases](https://github.com/dataterminals/grb-modding-knowledgebase/releases)
  or the **Actions** tab
  ([`build-forge-inspector.yml`](../.github/workflows/build-forge-inspector.yml)) →
  `ForgeInspector-exe` artifact.
- **Build:** `pip install pyinstaller` then, in `tools/`,
  `pyinstaller --onefile --windowed --name ForgeInspector forge_inspect_gui.py`.

Background: [`../docs/06-game-load-and-reassembly.md`](../docs/06-game-load-and-reassembly.md),
[`../reference/resource-type-ids.md`](../reference/resource-type-ids.md).

---

## 🦴 Skeleton Reflex Scanner — which skeletons carry **bone physics**?

Not every flowing thing in GRB is cloth. Hair, ponytails, backpack straps, weapon
slings, scarves — and the **Bodark trench coat** — move via **Reflex3**, Anvil's
per-bone secondary-motion system (swing/slide constraints with gravity and wind).
This tool tells you which skeletons carry it and how much.

**Why you care:** `.cloth` is welded to one specific mesh's vertices, so it can't
be moved to a new garment. **Bone physics can** — you weight-paint the new mesh to
the same bones. That makes Reflex3 the practical route for "put this coat's motion
on my mesh." Full write-up:
[`../reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

```
python skeleton_reflex.py "D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"
python skeleton_reflex.py DataPC.forge --csv skeletons.csv
python skeleton_reflex.py 1889064665537_-_Player_Kilt_Addon.data
```

Reads forge indexes directly (no unpacking) and decompresses only the skeleton
entries, so a whole install scans in a couple of minutes. Needs the game's
`oo2core_7_win64.dll` — auto-found next to the forge, or pass `--oodle`.
**Read-only; it never writes to the game.**

What the report means:

- **blob = 8 B** → header only → that skeleton has **no** bone physics.
- **blob > 8 B** → real per-bone constraints. Bigger = more constrained bones.
- Names ending `_Reflex` or `_Addon` are the physics layer for a character or a
  garment. ⚠️ A big blob does not mean the garment moves by bones:
  `Tsec_Trench_AddonSkeleton` (43,494 B) sits beside the trench coat's cloth, and the
  coat mesh is not weighted to any bone it drives *(2026-09-16)*. A mesh moves with a
  rig only if it is weighted to the rig's driven bones — `rebind_check.py` checks that.

⚠️ Skeletons are **forge-shadowed** like cloths — the same ID lives in
`DataPC.forge` *and* a WorldMap `_Split` base. An override must go into **both**
families' patch forges.

---

## 🧍 Entity Skeletons — what rigs does this character or item use?

Walks a `.data` container and prints its skeleton build sheet: every rig assigned in
it, **which build table assigns it**, the column Index, and which rigs carry bone
physics.

```
python entity_skeletons.py "28830_-_TSec_MIS_Blake(184).data" ^
    --install "D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"
python entity_skeletons.py 23_-_TEAMMATE_Template.data --install "…" --grep Kilt
```

```
 held by                                  index  skeleton                        bone physics
 TP_Blake_Skeleton                            2  Regular_Male_Reflex_SklAdd         107,350 B
 TP_Blake_Skeleton                            1  Regular_Male_Body_Skl                      -
 TP_Blake_Skeleton                            4  Player_Props_Addon                         -
 TSec_CIN_Blake_Head                          2  Skeleton_IanBlake_Head                     -
 Tsec_IanBlake_Trench_Mcloth_MISSION          4  Tsec_Trench_AddonSkeleton           43,494 B
```

A character is a plain base rig **plus a stack of add-on rigs**, and the ones with
physics are the parts that move — hair, straps, a beard, a coat. Note *who* assigns
Blake's trench coat rig: the **coat's own build table**. That is the rule — the kilt's
rig comes from `TP_PANT_Kilt`, not from the player template.

**Why it matters:** an assignment is a `BuildTable` row component holding a plain
64-bit ID, so it's re-pointable — the same trick as the community's hex item swaps.
And ATK round-trips `BuildTable` as XML for GRB, so you don't have to do it in hex:
`python atk_bridge.py <container.data> --xml out.xml --resource <TableName>`. Record
format and the evidence:
[`../reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

> ⚠️ **Rewritten 2026-09-16.** The old version printed a "slot" that was really the *next*
> component's index, and credited each rig to the nearest name in the file instead of the
> table that holds it. The IDs it printed were right.

Without `--install` it still lists the holders, indexes and raw ClassIDs — you just
don't get names or physics sizes. **Read-only.**

---

## 🪢 Reflex3 Decoder — read a skeleton's bone physics in degrees

`skeleton_reflex.py` tells you *whether* a rig has bone physics. This one tells
you **what the physics actually says**.

```
python reflex3.py 1889064665537_-_Player_Kilt_Addon.data
```

```
  1 constraint record(s); 1 delimited exactly, 0 located by scan
  by type: 21=1 (Physics (swing/slide/gravity))
  skeleton declares 4 bone(s); 1/1 constraint BoneIDs resolve to one of them
      #        bone  <- parent  swing 1     swing 2     slide  mass* spring* damp*   p3  grav  height
      0*   b99cb525   92941bb9  [-15,+15]   [-5,+5]     -        0.2       0     0    0   9.8    0.96
```

The kilt is one bone at hip height that swings ±15° one way and ±5° the other,
under normal gravity. Hair reads as a chain — `+` marks a record whose parent is
the previous record's bone — with limits widening and mass falling toward the tip:

```
  0*   3451cb89   ad589a33  [-10,+10]   [+0,+25]    -        0.4       0     0  0.6   9.8    1.62
  1*+  4356fb1f   3451cb89  [-15,+15]   [-1,+30]    -        0.3       0     0  0.6   9.8    1.58
  2*+  dd326ebc   4356fb1f  [-20,+20]   [-3,+35]    -        0.2       0     0  0.6   9.8    1.54
  3*+  04b9192e   dd326ebc  [-25,+25]   [-5,+40]    -        0.1       0     0  0.6   9.8    1.49
```

Stiff and heavy at the root, light and loose at the tip — and the fore-aft swing
is one-sided, which is what keeps hair out of the head: no physics record carries
a collision shape. `height` is where the bone's parent sits on the character
(hair ≈ 1.6 m, kilt 0.96 m). Columns marked `*` are inferred names.

Add `--raw` for every record — hinges, pose-driven orientation records, and the
body bones a rig attaches to by name (`body bones referenced by name:
T_SpineTrenchCoat`) — and `--names ..\reference\grb-bone-names.tsv` (or the
`atk_hashes.py` dictionary) to see names instead of hashes.

**ATK cannot do this.** Its Reflex3 parser checks Mirage's magic numbers and is
gated behind `Version != Game.Mirage`, so for Breakpoint it keeps the whole thing
as an opaque Base64 lump. Format, and the evidence behind it:
[`../reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md);
the vanilla chain recipes:
[`../reference/reflex3-chain-templates.md`](../reference/reflex3-chain-templates.md).

⚠️ Reading is solid — every one of the install's 204 distinct blobs reads to its
last byte, and the physics, hinge and three other record types delimit themselves
(2026-09-20). **Writing is not implemented**, and any skeleton edit inherits the
forge-shadow and hang-on-load hazards documented for cloth. **Read-only.**

---

## 🧷 Reflex3 Writer — edit, generate and splice bone physics (never into the game)

`reflex3.py` reads a rig's bone physics. This one **writes** it — into a scratch
copy of the skeleton's `.data`, which you then place into an unpacked forge folder
and repack yourself.

```
python reflex3_write.py --selftest "D:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"
  204 distinct blobs; 204 round-trip byte-exact; 0 do not
```

That is the writer's acid test: every Reflex3 blob in the install, parsed and
re-emitted, comes back byte for byte. Physics records are rebuilt from their
fields; every other record type is carried through verbatim.

**Edit** a rig — swing limits in degrees, slide limits in metres, the nine
parameters by index (0 is mass):

```
python reflex3_write.py 45229_-_BP_wStraps_Hill_MEDIUMVEST.data --set-swing 9650dc43 1 -30 30 --set-swing 9650dc43 2 -10 30 --out 1_-_BP_wStraps_Hill_MEDIUMVEST.data
  blob 50,587 B -> 50,587 B; 2 physics record(s) edited; changed
  wrote 1_-_BP_wStraps_Hill_MEDIUMVEST.data (... B container); re-read and verified.
```

**Generate** a whole physics blob from a JSON spec of records (bone, parent, the
two swing ranges, mass and the rest), taking each bone's transforms from the
skeleton the rig will live in and the character-space frame from a body rig:

```
python reflex3_write.py --example-spec > poncho.json          # the hair-strand pattern
python reflex3_write.py MyPoncho_Addon.data --generate poncho.json --body Regular_Male_Body_Skl.data --out 1_-_MyPoncho_Addon.data
```

Regenerating the kilt and the Casper hair rig from their own decoded fields
reproduces every matrix to the float; the Herzog and Layla hair rigs come back
within 3 mm on the character-space frame (they were compiled against a
different character, `--h` sets the lift).

**Splice** happens with `--out`: the new blob goes into the Skeleton resource,
the resource and metadata lengths are fixed up, both container blocks are
rebuilt with the game's own Oodle DLL, and the result is read back and compared
before it is kept. A no-op edit reproduces the original container's content
exactly.

⚠️ **The game is never touched.** Putting the file into a forge is the manual
step: number it *below* the copy you are replacing (`1_-_...`) in the unpacked
forge folder, back the forge up, repack with ATK. What the install has already
proven about such files, and what it has not:
[`../reference/install-edit-classes.md`](../reference/install-edit-classes.md).
The recipes: [`../reference/reflex3-chain-templates.md`](../reference/reflex3-chain-templates.md).

---

## 🔤 ATK Hash Dictionary — turn bone numbers into bone names

Anvil names things by **CRC32 of the name**, so a skeleton stores `LeftForeArm`
as `220238864`. ATK ships the reverse lookup as a compressed resource inside its
own assembly. This pulls it out of **your** install:

```
python atk_hashes.py "E:\Anvil Toolkit" -o hashes.txt
python reflex3.py Watch_Skeleton.data --names hashes.txt
```

276,087 names, ~2 minutes. The dictionary is ATK's data and is **not shipped with
this repo** — extract your own.

⚠️ **Coverage is partial, and usefully so.** The list targets ATK's primary games
(the Assassin's Creed line), so it resolves the **standard biped bones** GRB
shares with them — about 4% of GRB's skeleton bone hashes — but not GRB's own
dangle-bone names (coat panels, hair strands). The ones it does resolve are the
attachment points, which is what you want to know:

| Rig | hangs off |
| --- | --- |
| Bodark trench coat | `Spine2` |
| Hunter scarf | `Spine2` |
| Watch | `LeftForeArm` |

A watch on the left forearm, a coat on the spine. **Read-only** on the toolkit.

For GRB's *own* bone names — the ones ATK never had — this repo ships
[`../reference/grb-bone-names.tsv`](../reference/grb-bone-names.tsv) (126 names
recovered from their hashes, each tagged with the evidence behind it). `--names`
accepts it directly:

```
python reflex3.py Tsec_Trench_AddonSkeleton.data --names ..\reference\grb-bone-names.tsv
```

The prefixes are the part worth memorising: **`RFX_`** is Reflex — the physics
bones themselves — `T_` are targets/attachment points, `L_` are no-roll helpers,
`Prop_` are prop attach points, and unprefixed names are the standard biped.

---

## 🧊 Blender bridge — drive Blender from a terminal

Everything above reads **game files**. This one drives **Blender**, the other end of
the authoring pipeline.

Blender ships its own Python and runs with no window at all, so importing a mesh,
transferring weight painting and exporting a GLB can all be scripted — repeatable,
diffable, and drivable by an assistant working alongside you.

```
python blender\grbblend.py doctor            # is Blender here, and does it have what we need?
python blender\grbblend.py selftest          # prove the bridge works, touching no game files
python blender\grbblend.py inspect Coat.glb  # UV sets, vertex colors, bones, weights, warnings
python blender\grbblend.py transfer-weights --source Coat.glb --target Poncho.glb ^
       --out Bound.glb --with-colors
```

**There is no GRB-specific Blender add-on to hunt down, and none is needed** — the
connector is **glTF**. ATK exports and imports GLB; Blender reads and writes GLB
natively. What was missing was tooling around that seam.

`inspect` checks the failure modes
[`../docs/10-meshes-and-skeletons.md`](../docs/10-meshes-and-skeletons.md) names by
hand — missing UVs, more than 5 UV sets, missing vertex colours, more than 4 bone
influences per vertex, unweighted vertices, multiple materials.

`transfer-weights` is [Sami's move](../meta/project-goal.md) scripted: take the weight
painting off a vanilla garment and put it on a new mesh. It reports **what percentage
of the new mesh's vertices actually got a weight** — anything under 100 % means
geometry that will not deform in game.

⚠️ **Read-only with respect to your GRB install** — it only touches the files you point
it at. The ATK export/import clicks at either end stay manual; ATK has no CLI.

⚠️ This does **not** solve the `.cloth` rebind — cloth is welded to one mesh's exact
vertices. Where it helps the north star is the **bone-physics route**, which transfers
precisely because it is weight-painted:
[`../reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

Full guide: [`blender/README.md`](blender/README.md).

---

## ⚙️ `atk_bridge.py` — call ATK's own readers from Python

ATK has no command line, but `AnvilToolkit.dll` is an ordinary .NET library and
the app is only a WPF shell over it. This loads that library into CPython through
pythonnet, so ATK — **the community's reference implementation of these formats**
— can be used as a second, independent opinion against the parsers in this folder.

```
python atk_bridge.py 87874_-_TP_Tacvest_Walker_Coat_LOD0.data
```

```
  ClassID       1707208439117
  VertexFormat  Pos3s_Col1s_Norm3ub_Col1ub_Tan4ub_Binorm4ub_Tex2s_Joint4_Col4ub
  Vertices      1816
  Faces         3263
  index range   0..1815
  Bones         30
  influences/vertex  {1: 490, 2: 53, 3: 238, 4: 1035}
```

It also **exports a garment to GLB with no ATK GUI at all** — the click at the
front of the authoring pipeline, automated:

```
python atk_bridge.py 87874_-_TP_Tacvest_Walker_Coat_LOD0.data --export Coat.glb
```

It finds the rigs itself. A GRB garment needs **two** — a character skeleton plus a
garment addon (the Walker coat: 24 bones from one, 6 from `Vest_Generic_Addon`) —
and `CreateGLTF` refuses a skinned mesh whose bones it cannot find. ⚠️ Auto-discovery
picks by bone coverage alone, so ties between character rigs break arbitrarily; names
and hierarchy will be right, **rest pose may not be**. Pass `--skeleton` to choose.

### `--import` — check a mesh write-back before you believe it

The other direction, and the one with traps. `--import` runs your GLB through ATK's own
`AnvilGLTF.FromGLTF` and reports **what vertex format the file would actually get** —
without writing anything.

```
python atk_bridge.py <donor.data> --import new.glb
```

```
  file carries  1816 verts, 1 mesh(es), colours=True uvs=True
  Bones         25   (donor has 30)
  donor         colours=3 uvs=1  …_Tex2s_Joint4_Col4ub / stride 36
  corrected     colours=3 uvs=1 vertex.Version=3 game=GhostReconBreakpoint
  would write   Pos3s_Col1s_Norm3ub_Col1ub_Tan4ub_Binorm4ub_Tex2s_Joint4_Col4ub
                game format id 1, stride 36
  MATCHES DONOR True
```

**Give it the donor.** `FromGLTF` on its own does not reconstruct a vertex format — it
**normalises** one: every skinned GRB mesh comes back as *3 colours / 4 UVs* whatever went
in, because ATK's glTF *writer* pads all five colour and all five UV channels
unconditionally and nothing in the GLB says which were real. Most GRB garments already sit
at (3, 4) and so appear to round-trip perfectly; the Walker coat, at (3, **1**), is the one
that exposes it. The donor `.data` is where the true channel counts come from. Without one
the tool still runs and says so, loudly — and reports stride **48** for a coat whose real
stride is **36**.

It also corrects two things you would otherwise never see: `DataStorage.ActiveGame` (unset,
it reads as **BlackFlag**, and the importer drops a colour channel from any skinned mesh)
and `mesh.Version` (hardcoded to `Game.BlackFlag` by `MeshFromGLTF` and never assigned,
while `Mesh.WriteToFile` switches on it in ten places). Exit status is **2** when the result
does not match the donor.

⚠️ **It suppresses a modal dialog to work at all.** `MeshFromGLTF` calls
`WpfMessageBox.Show` when a GLB has no vertex colours or no UVs — i.e. on exactly the
fresh-from-Blender mesh you are most likely to bring — and headless there is no dispatcher,
so the import dies in `WpfMessageBox..ctor()`. The bridge borrows
`Settings.SuppressMeshViewerImportErrorMessages` for the call and hands it straight back,
then reports the same two conditions itself. **`Settings.Save()` is never called** and must
not be; that would write ATK's user config.

⚠️ **Nothing is written.** You get a live in-memory `Mesh`. Getting it into a `.data` and
repacking a forge is still manual and still needs a verified backup — by policy, not by
capability.

### `--xml` — ATK's editable round-trip, without ATK

Some resource types declare `FileActionType.Xml`: `EntityBuilder`, `BuildTable`, `Material`,
`TextureSet`, `LODSelector`. Those are the community's editable surface, and this reaches
them without the application.

```
python atk_bridge.py <file.data> --xml out.xml
python atk_bridge.py 23_-_TEAMMATE_Template.data --xml out.xml --resource PLAYER_SkelAddons
```

Without `--resource` it exports the container's first resource. With it, any resource inside
the container — which matters, because the tables worth editing usually live inside someone
else's container (`PLAYER_SkelAddons` and every garment table sit in `TEAMMATE_Template.data`).

Verified 2026-09-09 on `PLAYER_Template` — 651 KB, 11,234 lines, both the base and the patch
copy — and 2026-09-16 on `PLAYER_SkelAddons` and `TP_PANT_Kilt` from inside
`TEAMMATE_Template`. Add types to `ATK_XML_TYPES` as you need them.

Two WPF gates sit on this path, and both are handled:

- **`ToXml` needs an STA thread.** It recurses into `Handle.ToXml` →
  `XmlUtils.WriteToXMLRef` → `GameFileList.GetFileReference`, which reaches `WpfMessageBox`,
  and WPF refuses to initialise outside a single-threaded apartment. pythonnet's CLR thread
  is MTA, so the export dies with *"The calling thread must be STA"* before writing a byte.
- **`GameFileList` looks for its list at a *relative* path** — `Lists/<ActiveGame>.gfl`,
  relative to the process working directory — and on a miss offers to **download** it in a
  dialog. ATK ships `<ATK>/Lists/GhostReconBreakpoint.gfl` (6.8 MB), so `prime_filelist()`
  points the working directory there for the call and restores it after.

**That second one is not just a workaround.** With the list primed — 1,053,342 entries —
every 64-bit reference in the XML renders as a real path:

```xml
<FileReference Name="Value" IsGlobal="0"
    Path="DataPC\TEAMMATE_Template\PLAYER_SkelAddons.BuildTable">1898138514560</FileReference>
```

Without it you get `1898138514560` and nothing else. Like `HashedData.CheckStrings`, the list
loads inside a `Task.Run` and has to be waited for.

Needs `pythonnet`, the .NET 9 runtime, and an ATK install. **It finds ATK itself**
(2026-09-10) — every drive root plus `Program Files`, `Games`, `Modding`, `Tools`
and your user folders, for anything named `*anvil*` holding `AnvilToolkit.dll`;
`--atk <dir>` or `$GRB_ATK` overrides, and the same search finds the GRB install
(by `GRB.exe`) for `find_skeletons_for`. It used to hardcode `D:`, which meant it
only ran on one of the two machines this repo is worked on. The container layer
stays **ours** — `data_inspect.py`
decompresses and walks the `.data`, and only one resource's header + payload (the
same bytes ATK's own unpack would write to a file) goes to ATK. That is what makes
the two readers independent.

Seven gates — four silent, three very loud. All seven are handled here and
explained in the module docstring:

1. ATK's dependencies live in `Libs\`, which .NET will not probe on its own.
2. `DataStorage.GlobalScimitarClassReader` is a static only the GUI populates.
3. `Mesh.Read` **catches its own exceptions** and hands back a half-built object
   that looks plausible.
4. `DataStorage.ActiveGame` has **no initialiser**, and `Game.Null` is -1 — so unset
   it reads as `(Game)0` = **BlackFlag**, a real game with real, wrong code paths.
   The read helpers dodge it by passing the game explicitly, but 68 files consult
   the global; `AnvilGLTF.MeshFromGLTF` is one, and its Black Flag branch silently
   drops a colour channel from any skinned GRB mesh. *(Found 2026-09-09.)*
5. `MeshFromGLTF` opens a **WPF modal dialog** for a GLB with no vertex colours or
   no UVs, which cannot work headless — this one is loud, not silent, and it kills
   the import outright. `import_gltf` suppresses it and reports the condition
   instead. *(Found 2026-09-09.)*
6. `ScimitarClass.ToXml` needs an **STA thread**; pythonnet's is MTA. *(2026-09-09.)*
7. `GameFileList` resolves its file list from a **relative** path and offers to
   download it in a dialog when it misses. *(2026-09-09.)*

⚠️ **Do not read a vertex format off `FromGLTF`'s output.** The importer preps
`Vertices[0]` and *then* calls `RemapBuffers`, which rebuilds the list in
face-traversal order — so the one prepped vertex is wherever that put it. Measured:
the Walker coat's stayed at index 0, the selftest poncho's landed at index **67**.
Writing self-corrects (`WriteToFile` re-preps index 0); only inspection is fooled.

~~⚠️ **`mesh.Failed` is not a success signal** for GRB meshes in ATK 1.3.1 — the
reader wants exactly one byte past the resource payload. The bridge pads one zero
byte; the geometry is identical either way.~~ **Resolved 2026-09-16:** that "extra
byte" was our slicer cutting off the payload's last byte. Sliced correctly, ATK
reads the mesh with `Failed = False` and no padding.

⚠️ **Read-only by policy, and not incidentally.** `ForgeFile.Serialize` and
`Mesh.WriteToFile` sit in the same object graph, and ATK's backup defaults are
*application* settings that do **not** apply to direct library calls. The bridge
also never calls `DataFile` — its `Deserialize` runs `CreateBackup` and unpacks
to an `Extracted\` folder, i.e. it writes to your install.

This is how the 2026-09-01 correction was found: ATK reads GRB garment skinning
as **four-influence** at vertex bytes 24–31, not two-bone at 32–35 (those are a
colour channel). See [`../meta/research-log.md`](../meta/research-log.md).

---

## 🧵 `rebind_check.py` — will this rebound garment actually move?

The pre-flight check for [the project goal](../meta/project-goal.md). You have
taken a vanilla garment's weight painting onto a new mesh and you are about to
import the GLB and repack. **Launching the game is the expensive step** — a hung
GRB needs `taskkill /F /T` — so this answers, from files alone, the question a
rebind actually fails on:

> Does the new mesh's weight painting reach the bones Reflex3 actually drives?

```
python rebind_check.py --skeleton Tsec_Trench_AddonSkeleton.data --mesh MyPoncho.glb
python rebind_check.py --skeleton Player_Kilt_Addon.data --mesh New.glb ^
       --donor 87874_-_TP_Tacvest_Walker_Coat_LOD0.data
```

```
[  ok  ] Influences per vertex within GRB's Joint4 limit
[ FAIL ] Weight coverage 75.00% - 3 of 12 vertices have NO weight
[ FAIL ] 1 driven bones are in the rig but carry NO weight
           These chains will not move, and ATK 'removes unused bones' on GRB
           import - so they may vanish from the mesh entirely and take the
           physics with them.
[ FAIL ] 1 driven bones are absent from the GLB's skin
```

**Why this tool can exist here and nowhere else.** ATK reads GRB meshes and
skeletons but **cannot parse Reflex3** — its parser validates Mirage's constants
and is gated behind `Version != Game.Mirage`, so for GRB it keeps the constraint
blob as an opaque Base64 lump. This repo decodes it ([`reflex3.py`](reflex3.py)).
The question above needs *both halves at once*, and only this repo has both.

It reads the GLB itself — **stdlib only, no Blender and no dependencies** — so it
runs anywhere. Exit code is `0` on pass/warn, `2` on fail, for scripting.

### How bone names are matched — the bit that makes it work at all

Reflex3 addresses bones by **CRC32 of the exact-case bone name**, and most of
GRB's per-garment dangle bones are *not* in ATK's dictionary (only 8 of 30 resolve
on the Walker coat). So ATK writes those glTF nodes with the **number** as the
name — `HashedData.GetHashedString` falls back to `id.ToString()`.

That fallback is load-bearing: **a numeric node name IS the bone hash.** A name is
taken literally when it is all digits and CRC32-ed otherwise (exact/lower/upper,
matching how ATK builds its map); Blender's `.001` suffixes are stripped. Names
that match nothing are reported as a warning — the tool degrades to *"I cannot
check this"*, never to a silent pass.

**Pass `--donor` (the vanilla garment's `.data`).** It scopes the physics check to the
bones the *original* garment actually used. Without it the whole rig is in scope — and
a character rig drives hair, straps and other garments, so a perfectly good coat gets
reported as failing dozens of bones it was never meant to touch. Findings drop to
warnings when no donor is given, because the tool genuinely cannot tell the difference.

⚠️ **It checks files, not the game.** It cannot tell you whether a modified
skeleton loads at all — that is still the open both-patch-forge question in
[`../meta/next-session.md`](../meta/next-session.md).

---

## 🎪 `rig_census.py` — which bone-physics rigs actually **move** a mesh?

`rebind_check.py` above answers *"will my new mesh move on this rig?"*. This one
answers the question that comes **before** it: *"which rig should I even be
copying?"*

It matters because a rig can carry 62 KB of Reflex3 constraints and move nothing
visible. `Tsec_Trench_AddonSkeleton` is 43 KB of bone physics assigned right next
to a flowing trench coat — and **no LOD of that coat carries any weight on any
bone the rig drives**. The coat flows because of its *cloth*. A plan built on
"copy the trench coat's rig" is built on a rig that, as far as that coat is
concerned, does nothing.

```
python rig_census.py --install "H:/SteamLibrary/steamapps/common/Ghost Recon Breakpoint"
python rig_census.py --install <GRB> 28398_-_TEAMMATE_Template.data --csv out.csv
python rig_census.py --install <GRB> --grep Backpack --all-lods
```

With no container given it censuses `TEAMMATE_Template` and `PLAYER_Template`,
which between them hold every player-wearable item's build table.

### What it joins

Three things that had only ever been joined by hand:

```
BuildTable row  ──►  Skeleton handle      the rig          (entity_skeletons.py)
                └─►  GraphicObject        the meshes
Skeleton        ──►  Reflex3 driven bones                  (reflex3.py)
Mesh            ──►  per-bone Joint weights                (ATK, via atk_bridge.py)
```

and then intersects: **do any of this row's meshes carry weight on the bones this
row's rig actually drives?**

### The three verdicts, and why there are three

| bucket | means |
| --- | --- |
| **MOVES A MESH** | a mesh in the same row weights bones the rig's Reflex3 records *drive*. This is the donor shortlist. |
| **NO WEIGHT ON ANY DRIVEN BONE** | meshes were found and checked, and none of them touch a driven bone. Weight on a record's **parent** is reported separately — that is the chain's anchor, and a mesh hanging off it does not swing. |
| **NO MESH IN THE ROW** | the row assigns a rig but no mesh reachable from it. **Not evidence either way** — it is a gap in what can be seen, not a finding. |

That third bucket exists deliberately. Collapsing "we found nothing to check" into
"it drives nothing" is how a rig gets written off for the wrong reason.

### Things it gets right that are easy to get wrong

- **Per row, never per table.** `Hats_forREGULAR` holds hundreds of rows, each a
  different hat with its own rig and mesh. Pairing across the whole table would
  invent motion that is not there, so rows are read through ATK's own `BuildTable`
  reader and paired only within a row.
- **Sub-tables are followed one level.** A garment's mesh is not always in the row
  that names the rig — the Walker coat's mesh and cloth live in
  `TP_TACVEST_Walker_Coat_Cloth`, a sub-table of `TP_VestMedium_Walker`.
- **The joint offset is parsed, not assumed.** GRB garments use at least strides
  32, 36 and 48, with the joint block at 24, 24 and **32**. A fixed offset reads a
  stride-48 backpack's normals as weights and reports a fully skinned mesh as
  carrying none. The offset comes out of `VertexFormat`, the parsed tokens must add
  up to the mesh's own stride, and the result is cross-checked against ATK's own
  `PackedJoints` decode before it is believed — with a per-vertex fallback through
  ATK when they disagree.
- **Record head, not record parent.** A Reflex3 record is
  `u32 BoneID | u32 ParentBoneID`; `BoneID` is the constrained bone. Counting both
  would score a garment as moving because it is anchored.

### Limits, stated rather than hidden

- LOD0 only unless `--all-lods`.
- A `GraphicObject` handle usually points at a `LODSelector`, and **ATK's own
  LODSelector reader fails on GRB** (`Failed=True`, every LOD null, and `WriteXml`
  then throws). The mesh IDs are recovered by scanning the LODSelector payload for
  64-bit values that are `Mesh` containers — which finds all five kilt LODs.
- Only rigs *assigned by a table in the containers given* can appear. A physics rig
  nothing assigns is invisible to this.
- **It reads files, not the game.** "This mesh is weighted to bones this rig drives"
  is a much stronger statement than the trench-coat premise it replaced, and still
  not the same as having watched it move.

READ-ONLY: containers are read straight out of the forges by offset. Nothing is
unpacked, nothing is written, no forge is opened for writing.
