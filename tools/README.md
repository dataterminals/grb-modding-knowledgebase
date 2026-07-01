# 🧵 GRB Cloth Inspector

A little tool that reads a **Ghost Recon: Breakpoint cloth file** and tells you, in
plain language, **what that cloth is** — which body parts it simulates, the exact
**mesh + LOD** each piece is bound to, and which cloth features it uses (wind,
constraints, presets…).

It's aimed at modders — **you do not need to know any coding to use it.**

> Why this helps: GRB cloth is baked to one specific mesh at one specific LOD. This
> tool shows you that binding at a glance (e.g. a body named
> `Sim_TP_Tacvest_Walker_Coat_LOD1` is the *wearable* Walker coat cloth at LOD1),
> so you can tell which `.cloth` goes with which garment before you start. Full
> background: [`../docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md).

---

## What you need first

1. **A cloth file to look at.** Cloth resources are the unpacked `.data` files whose
   names contain **`Cloth`** — e.g. `34224_-_TP_WalkerCoat_Cloth.data` or
   `35720_-_Cloth_WalkerCoat.data`. You get them by unpacking a `.forge` with **ATK**
   (they live in `DataPC.forge`). If you've unpacked a forge, look in its `Extracted`
   folder for files with `Cloth` in the name.
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
FILE: 34224_-_TP_WalkerCoat_Cloth.data   (103,408 bytes)
  Cloth bodies (simulated pieces): 1
    - Sim_TP_Tacvest_Walker_Coat_LOD1   [gameplay / wearable cloth]

  A body name reads as  Sim_<TargetMesh>_LOD<n>  - it tells you the
  exact mesh + LOD this cloth is bound to. Match your mod to that.
  ...
  Highlights: carries constraint buffers; has tuning presets
```

- **Cloth bodies** = the separate simulated pieces in the file.
- **Body name** `Sim_<Mesh>_LOD<n>` = **the mesh and LOD this cloth is welded to.** This
  is the big one: if it says `..._CIN_...` it's a **cinematic** (cutscene) cloth; if it
  says `Sim_TP_<gear>` it's the **wearable** one you want for player gear.
- **Section list / Highlights** = which cloth features are present (wind, constraint
  buffers, presets, etc.), so you can compare two cloths' capabilities.

## Good to know / limits

- The tool is **read-only** — it never changes your files. Safe to point at anything.
- Counts are **approximate**: a few section counts can be off by one or two (a
  technical detail explained in [`../meta/research-log.md`](../meta/research-log.md)).
  The **body names, LOD/mesh binding, and “which cloth is which”** are reliable — and
  that's what you actually need it for.
- It reads **uncompressed** GRB cloth `.data` (the normal unpacked form).

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

*Files here:* `cloth_inspect.py` (the engine), `cloth_inspect_gui.py` (the window),
and the two `.bat` launchers. All read-only, all documented.
