# The studied mod corpus

This knowledgebase was built partly by examining a working library of **150+ GRB mods** in `Extracted\GRBMods\` on the research machine. The mods themselves are **not** in this repo (they're third-party content and large) — this is a *map* of what was studied, to show the breadth of the corpus and to give examples per category.

Folder naming in the corpus follows two patterns (see [`docs/08-naming-conventions.md`](../docs/08-naming-conventions.md)):
- **Nexus-style**: `<Name>-<modID>-<version>-<unixTimestamp>` e.g. `Strix face V2-1550-V2-1757740151`.
- **Workflow folders**: named for the forge layer they repack, e.g. `Sheva_resources`, `Sheva_buildtables`, `mechanix_2_bt`, `acostabisonbattlebelt_DataPC_Resources_patch_01.forge`.

## Categories (with representative examples)

### Weapons (replacements & additions)
`USP Tactical + Burris FF3` (see [case study](case-study-usp-tactical.md)), `MK17`, `MK18Mjolnir_553ScoutReplacement`, `HK G39C`, `L85A3 V2`, `L119A1`, `SA58`, `AKM_KYPK`, `MB47`, `Sig_XM7_MCXSPEAR`, `SIG rattler`, `Steyr_DMR`, `DDM4A1`, `Deagle`, `MP9`, `Kalashnikova_SR1`, `VEKR-99S(HDG)`, `M45A1_M1911Replacement`, `PM MAKAROV(replaces mk23)`, `Gazza_MP5*` (A2/K/SD variants), `JAE_M1A_FirstWave_MK14Replacement`, `M4A1_URG-I_T1X_ViruS`, `ViruS_HK416D_T1X`, `APC9 RepScorpionCQC`, `T1 Noveske Chainsaw`.

### Weapon attachments / optics / suppressors
`EOTech_Vudu_Trijcon`, `Vortex XM157 Scope`, `Romeo4T_Wilcox_mount`, `YHM Turbo T3 Suppressor DefaultASRReplacement`, `BTRotexVCompact_Suppressor_HiveReplacement`, `shinysuppressor_prismreplacer`, `BT Quick-Detach Vertical Grip RepLightweightVerticalForegrip`, `Weapon Emporium Attachments`, `KOBLINOverhaul_MagwellSkullGrip_remover`.

### Gear / vests / plate carriers / belts
`Crye AVS` / `Crye JPC` (multiple "Loaded V2" variants), `DEVGRU_NJPC_WithATAK`, `CFLIONNESS_JPCVest` / `CFLIONNESS_BangerJPC` / `CFLIONNESS_CondorTop`, `Acosta - The Bison Belt - Ferro Concepts` (+ `bisonbelt_datapc`, `acostabisonbattlebelt_*`), `Fitted Battle Belt`, `battlebelt_23teammatetemplate`, `SBA3 Stock Loaded`, `Strandhogg V3 D3CRX`, `Individual Buildtables - Vests/Helmets/Headsets/NVGs/Glasses` (definition-layer-only mods).

### Outfits / clothing
`Cinematic Outfits`, `Eva Modern Outfit`, `Tactical Human Set`, `Patagonia BDU High`, `CFLIONNESS_*` (jackets, flannels, cargos, jeans), `LIONNESS_Jeans` / `LIONNESS_RolledSlimShirt`, `Mara Leggings`, `Nomad Leggings`, `Fitted jeans`, `Modern Boots`, `TF141_Fleece`, `Water G3's Jacket`, `Shoko Shirt Lift`, `OPMCH_TrackSuit_PioneerReplacement`.

### Faces / heads / hair / makeup
`Strix face V2`, `Better Faces`, `Non-Angry and Better Faces`, `Sheva_*` (resources + buildtables — see naming), `Mara_MW2019_*`, `Lara Croft - Icon and Face`, `Bonnie Macfarlane`, `Panam`, `Valeria Garza`, `Goth shadowheart`, `Croft Phantom Raider Eye Makeup`, `Freckles + Eyeshadow`, `Caveira_BlackNails`, `Ponytail`, `Mid Cut Length Hair`, `LongHair_HelmetsHats`, `Mila`, `Hibana_Basefiles`, `BerthaTohibana`.

### Camo / textures / patches
`Desert Night Camo` (+ Revamped, Black/Green/Grey/Tan variants), `Strichtarn Camo`, `Irish DPM Camouflage Patterns`, `3DPrinted_Camo_ScalesReplacer`, `UrbanTopo_*` (gear/weapon camo replacers), `UFProFlecktarnBlack_UrbanERDL_replacement`, `Deckard_ATACSWeaponPaintReplacement`, plus many **patch** mods (`Devil Gal`, `Devil Horn`, `Project Shokushu`, `LV x MP7`, `Dont Be Poor - Martial Artist Patch`).

### Headwear / helmets / accessories
`OPS-CORE AMP`, `0N3_PULZ_OpsCore_RAILINK_PULZV3`, `NOCTURNO X1 CAP 2.0`, `Reverse Ronin Cap Resized`, `Stetson Replacement`, `Sniper Hood Nomad Cap`, `PMC Hood-Trucker cap`, `SAMI_GenRamenCatHat_FlatCapReplacement`, `Magpul Patrol Gloves`, `Mechanix Gloves` / `Mechanix MPAct Agilite Gloves 2.0` (+ `mechanix_2_bt`).

### Footwear (notable for non-tactical content)
`EXCLUSIVE Zephyr Shoes`, `Jordan 1 Travis Scott Colorable`, `NIKE JORDAN 1 FRAGMENT X TRAVIS SCOTT SNEAKERS`, `Vans Defcon - uormomchesthair`.

### Vehicles / drones / gadgets
`ducati_scrambler`, `MQ9_REAPER_AmarosReplacement`, `iDroid`, `LumiaPhonePathfinderReplacement`, `QBoombox_Jur3uk_M110Replacement`.

### UI / quality-of-life / fixes
`4HealthBarsAllClasses`, `GRBNo-IntroFix`, `behemoth_42kcredits`, `daboss`, `ThankTheRadio`, `Sheva ui`.

### Faction / NPC overhauls
`Guerilla Outcasts` / `Guerrilla Outcasts` / `Less stupid looking outcasts`, `LessEdgyWolves_*`, `Honey Badger Overhaul Redux`, `KOBLIN_Overhaul`, `OPMCH_Bodark_Overhaul_16`, `SC_Revamp_PMC_*` (a full PMC class set: bagman, breacher, commander, droneop, radioop, rifleman, rocketeer, sniper, support).

### Tooling / update packages
`UE Update` (engine/update package containing forge data), `tac_anim`, `faith_resources`, `gorgon_nohead_*`.

## What the corpus tells us

- **Cosmetic dominance.** The overwhelming majority are visual: gear, weapons, faces, camo. Gameplay/logic mods are rare.
- **The layer split is real and visible** in the folder names: `*_resources` vs `*_buildtables`/`*_bt` vs full three-forge bundles.
- **Replacement is the norm.** Mod names constantly say `…Replacement` / `Rep…` / `replaces …` — they hijack an existing in-game item's slot (and ID) rather than adding wholly new ones.
- **Heavy reuse of base assets.** "Individual BuildTables" mods ship *only* definition-layer `.data` to re-point existing resources — a cheap, resource-free way to mod.

> If you add a new worked example, follow the [USP case study](case-study-usp-tactical.md) format: show the actual `.data` layout, decode the names, and extract the general lesson.
