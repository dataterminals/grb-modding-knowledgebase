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
