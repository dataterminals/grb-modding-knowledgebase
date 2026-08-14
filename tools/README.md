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
python data_inspect.py  foo.data --oodle "D:\...\Ghost Recon Breakpoint\oo2core_7_win64.dll"
```

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
python skeleton_reflex.py "H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"
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
  garment — `Tsec_Trench_AddonSkeleton` (43,494 B) is a vanilla flowing coat done
  entirely with bones.

⚠️ Skeletons are **forge-shadowed** like cloths — the same ID lives in
`DataPC.forge` *and* a WorldMap `_Split` base. An override must go into **both**
families' patch forges.

---

## 🧍 Entity Skeletons — what rigs does this character or item use?

Reads a character's or item's **`EntityBuilder`** and prints its skeleton build
sheet: every rig it pulls in, and which of those carry bone physics.

```
python entity_skeletons.py 1536663434687_-_PLAYER_Template.data ^
    --install "H:\SteamLibrary\steamapps\common\Ghost Recon Breakpoint"
```

```
 slot  skeleton                          bone physics   assigned near
    1  Regular_Male_Reflex_SklAdd           107,350 B   TP_Blake_Skeleton
    4  Regular_Male_Body_Skl                        -   TP_Blake_Skeleton
    5  Tsec_Trench_AddonSkeleton             43,494 B   Tsec_IanBlake_Trench_Mcloth_MISSION
```

A character is a plain base rig **plus a stack of add-on rigs**, and the ones with
physics are the parts that move — hair, straps, a beard, a coat. Blake's trench
coat is one line in that list.

**Why it matters:** the assignment is a plain 64-bit ID sitting at a fixed offset
in a fixed-shape record, so it's re-pointable — the same trick as the community's
hex item swaps. And ATK exports `EntityBuilder` to XML for GRB, so you don't have
to do it in hex. Record format and the evidence:
[`../reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

Without `--install` it still lists the raw ClassIDs and slots — you just don't get
names or physics sizes. **Read-only.**

---

## 🪢 Reflex3 Decoder — read a skeleton's bone physics in degrees

`skeleton_reflex.py` tells you *whether* a rig has bone physics. This one tells
you **what the physics actually says**.

```
python reflex3.py 1889064665537_-_Player_Kilt_Addon.data
```

```
  1 constraint record(s); 394/394 bytes accounted for
  by type: 21=1 (Physics (swing/gravity))
  skeleton declares 4 bone(s); 1/1 constraint BoneIDs resolve to one of them
       #  bone (CRC32)   <- parent  swing limits (degrees)      gravity  damping
       0*  3114054949  2459179961  [ -15.0, +15.0] [ -5.0, +5.0]  9.800  0.2
```

The kilt is one bone that swings ±15° one way and ±5° the other, under normal
gravity. The Bodark trench coat is **36 hinges plus 10 swinging bones**, half
limited −20°→0° and half 0°→+20° — panels hinging fore and aft.

Bone IDs are **CRC32 of the bone's name**, so a rig's structure comes out too.
Hair reads as a chain — each record's parent is the previous record's bone, with
limits widening and damping falling toward the tip:

```
  0*   877775753  2908265011  [ -10.0, +10.0] [ +0.0, +25.0]  9.800  0.4
  1*  1129773855   877775753  [ -15.0, +15.0] [ -1.0, +30.0]  9.800  0.3
  2*  3711069884  1129773855  [ -20.0, +20.0] [ -3.0, +35.0]  9.800  0.2
  3*    79239470  3711069884  [ -25.0, +25.0] [ -5.0, +40.0]  9.800  0.1
```

Stiff at the root, floppy at the tip — exactly how an animator authors hair.

Add `--raw` for every record including the non-physics constraint types.

**ATK cannot do this.** Its Reflex3 parser checks Mirage's magic numbers and is
gated behind `Version != Game.Mirage`, so for Breakpoint it keeps the whole thing
as an opaque Base64 lump. Format, and the evidence behind it:
[`../reference/skeleton-reflex3-physics.md`](../reference/skeleton-reflex3-physics.md).

⚠️ Reading is solid — the record walk accounts for every byte in 204 of 205
skeletons. **Writing is not implemented**, and any skeleton edit inherits the
forge-shadow and hang-on-load hazards documented for cloth. **Read-only.**

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
