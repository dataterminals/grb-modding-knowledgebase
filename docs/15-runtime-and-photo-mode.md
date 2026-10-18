# 15 — Runtime modding and the photo-mode project

Every other page in this KB covers the **data side**: forges, `.data` containers, and the resources
inside them. This page covers the **runtime side**: code and memory inside the running `GRB.exe`.
The first runtime project is an extended **photo mode**: a free camera with no range limit, then
time control, then posing and animating the character.

> **Status (2026-10-13): planning plus offline recon.** Nothing on this page has been observed in a
> running game yet. The verified facts come from static reads of the exes and forge indexes. The
> in-game recon is the next step (see [Recon recipe](#recon-recipe-phase-0)).

## Why runtime work is possible now

> **Verified (web, logged 2026-10-04):** BattlEye was removed from GRB in 2023. Code running inside
> the game process is no longer fighting an anti-cheat.

> **Verified (Nexus, 2026-10-13):** other modders already change GRB at runtime.
> - A Cheat Engine first-person table ([Nexus 532](https://nexusmods.com/ghostreconbreakpoint/mods/532))
>   requires the DX11 executable.
> - *Easy First Person* ([Nexus 2053](https://www.nexusmods.com/ghostreconbreakpoint/mods/2053)) is
>   a DLL-style mod. Nexus's scan reports "some suspicious files". It was **not** run for this KB.

> **Inferred:** GRB still needs a connection to Ubisoft's services. Keep runtime experiments to solo
> play, never PvP. A web guide says vanilla photo mode is disabled in PvP anyway.

## The build you are touching

> **Verified (memory-mapped string search, 2026-10-13):** both executables embed the same build
> string:
>
> ```
> ChangeList:7793716;Version:E450_1.24;User:silex-buildfarm;Branch://tgt-streams/Y2E4.5.0;…
> ```
>
> It sits at file offset `0x50a8f90` in `GRB.exe` (536,007,208 B) and at `0x50c6ba0` in
> `GRB_vulkan.exe` (519,231,016 B). Steam rewrote both files on 2026-10-08, but the ChangeList is
> the same as the one read on 2026-10-04. That rewrite did not change the code build.

> **Inferred:** branch `Y2E4.5.0` matches title update 4.5.0, which was reported in 2022 as the
> game's last major update. Code addresses are therefore probably stable. Steam still rewrites the
> files, though, so runtime tools should find code by **byte signature (AOB)**, never by a fixed
> address, and should refuse to patch when the build string isn't one they know.

## What the files say about photo mode

**The executable has almost no readable names.** A case-insensitive search of `GRB.exe` for
`photo`, `freecam`, `debugcam` and `spectat` finds only the strings below. Anvil hashes its class
names, so the camera code can't be found by name. It has to be traced at runtime.

```
StateFlowPhotoMode
%s/photobooth_%s.bmp   %s/photobooth_%s.jpg   %s/photobooth_%s.png
ACTIVITY_SPECTATE
```

**The photo-mode UI is data.** Index-only reads (`tools/forge_inspect.py`, no payload decoded):

| Forge | Entry (64-bit ID) | Type | Notes |
| --- | --- | --- | --- |
| `DataPC_extra` | `PhotoModeGameContext` (`0x1b350c06014`) | `#3683486083` | UI game context |
| `DataPC_extra` | `PhotoModeMainContainer`, `PhotoModeMenu`, `PhotoModeGrid`, `PhotoModeSubCategoryItemList`, `PhotoModeListButtonContainer*`, `PhotoModeNonEditableButtonsLoader`, `PhotomodeTabNav*` | `#3683486083` | UI widgets. Each name carries a GUID suffix |
| `DataPC_extra` + `DataPC_extra_patch_01` | `PhotoModeDescription` (`0x1b350c11c72`) | `#3683486083` | Overridden in the patch forge. Not checked whether by Ubisoft or by an installed mod |
| `DataPC_extra` | `UI_ICO_PhotoMode_{Camera,Effects,Shutter,WorldSettings}_MapDesc` | `TextureMapSpec` | Tab icons |
| `DataPC` | `Entity_ObserverCamera` (`0x132c56d5d30`) | `Entity` | Not opened |

> **Inferred:**
> - The icon names suggest four photo-mode tabs: Camera, Effects, Shutter and World Settings.
> - `Entity_ObserverCamera` may be the camera entity that photo mode or spectating drives.
> - No record is named for photo-mode camera limits. If the range limit and collision are
>   data-driven, they sit inside a record named for something else.
> - The name of type `#3683486083` is unresolved. It is clearly a UI widget type.

## Plan: "unchained" vanilla photo mode first

Vanilla photo mode already has a free camera, FOV, filters and a hidden HUD. We believe two things
hold it back: a **range limit around the player** and **camera collision**. Neither has been
measured yet. Removing both gives a usable noclip camera with the least new code, and it shows
whether the approach works.

| Phase | Deliverable |
| --- | --- |
| 0 | Recon: measure vanilla photo mode, find the camera and player transforms, and find the code sites for the range limit and the collision check |
| 1 | A Cheat Engine table: patches found by `aobscanmodule`, gated on the build string, each one switching back to vanilla cleanly |
| 2 | A DLL: ImGui overlay, our own free camera, HUD and FOV control, time freeze and single-frame step |
| 3 | The character: move and rotate the player, trigger emotes, play any `Animation` (type `0x0FA3067F`) with a scrub slider |
| 4 | A per-bone pose editor using [`grb-bone-names.tsv`](../reference/grb-bone-names.tsv); AI teammates as extra models |
| 5 | Extras: time of day, weather, camera paths, supersampled capture |

Constraints, because the goal is a public release:
- Patches live **in memory only**. Never patch `GRB.exe` on disk.
- No forge is touched, so no repack is needed.
- Unknown builds fail cleanly.
- DX11 first, since the existing community tools and our earlier static reads were all on the DX11
  exe. Vulkan comes later.

**A data-side alternative for poses:** write a static pose into an emote's `Animation` clip, so that
triggering the emote plays the pose. Animation clips have already been edited in place by installed
mods ([`install-edit-classes.md`](../reference/install-edit-classes.md): 22 clips). The `Animation`
binary format is not decoded here yet; ATK's source is where to start.

## Recon recipe (Phase 0)

1. Launch GRB **solo** with the DX11 exe. Check that no forge edit or ATK repack is running at the
   same time.
2. Open vanilla photo mode. Record how far the camera can get from the player, whether it collides
   with walls, whether the world pauses in solo, and which toggles it offers.
3. In Cheat Engine, find the camera position: an unknown-value float scan, then move the camera and
   rescan for changed or unchanged values. Do the same for the player position.
4. On the camera position, run "Find out what writes to this address". Expect the range limit to be
   a length compare followed by a scale-back toward the player. Expect the collision check to be a
   probe that pulls the camera inward.
5. Record each code site as an AOB pattern, with how it was found.

> **Inferred caution:** if CE's default debugger interface trips the game, switch CE to its VEH
> debugger. Nobody has tested this on GRB yet.

## Tooling on the reference machine (SylDesk, 2026-10-13)

- Cheat Engine 7.6 is installed.
- Visual Studio Build Tools 2022 (17.14) is installed, for the Phase 2 DLL.
- x64dbg and Ghidra are not installed. Phase 1 doesn't need them.
