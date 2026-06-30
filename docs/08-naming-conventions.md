# 08 — Naming conventions

GRB resources carry highly structured names. ATK resolves many of them from its hash dictionary, so when you unpack a forge you see names like `107094_-_FTP_Head_Angel_DiffuseMap_PC_Mip0.data`. Decoding these names tells you *what a resource is, what it's part of, and which variant it represents* — essential for finding the right thing to replace.

> **Verification note:** the *patterns* below (LOD/Mip suffixes, the `_-_` separator, component/variant naming, the `77777` placeholder) are **verified** by direct observation across the studied corpus. The expansions of short **prefixes** (`FTP`, `TP`, `WG`, `WI`, `HDG`, `ENV`…) are **inferred** from context and are marked accordingly. Corrections welcome — log them in [`meta/research-log.md`](../meta/research-log.md).

## The unpacked filename shape

```
<decimalFileID> _-_ <ResourceName> . <ext>
        │          │        │          └─ .data (container) or typed ext (.BuildTable, .Mesh, …)
        │          │        └─ resolved human name (or numeric if hash unknown)
        │          └─ the literal separator "_-_"
        └─ 64-bit file ID in decimal (the real identity)
```

## Name body grammar

Resource names read roughly as **`<DomainPrefix>_<Subject>_<Identifier>_<Component>_<Channel>_<Platform>_<DetailLevel>`**, with parts omitted as appropriate. Examples decoded:

| Name | Reading |
| --- | --- |
| `FTP_Head_Angel_DiffuseMap_PC_Mip0` | Head model "Angel", diffuse texture, PC, mip level 0 |
| `FTP_Head_Angel_NormalMap_PC` | same head, normal-map texture, base (no mip suffix) |
| `TP_Hair_CornRawA_LOD0` | third-person Hair "CornRawA", highest-detail mesh |
| `TP_Hair_CornRawAForGoggles_LOD2` | same hair, *goggles-compatible* variant, LOD2 |
| `WG_HK_USP45_Receiver_LOD0` | weapon-gameplay HK USP45, Receiver part, LOD0 mesh |
| `WI_HDG_P12_Main` | weapon-item handgun "P12", Main component definition |
| `UI_HDG_P12_Map` | UI icon/map for the P12 handgun |

## Domain prefixes (inferred)

| Prefix | Inferred meaning | Seen in |
| --- | --- | --- |
| `TP_` | **Third-Person** model (the world/character model) | hair, body, gear meshes |
| `FTP_` | **F**ace/**F**emale **T**hird **P**erson (appears on `Head` resources) | heads, face textures |
| `WG_` | **Weapon — Gameplay** definition / its meshes | `DataPC_extra_patch_01`, resources |
| `WI_` | **Weapon — Item / Inventory** definition | `DataPC_patch_01` |
| `UI_` | **User Interface** asset (icons, maps) | inventory icons |
| `ENV-` | **Environment** asset (props, goods) — note dash-separated style `ENV-SPE-Props-…`, `ENV-GLO-PRO-Goods-…` | `DataPC_Resources.forge` |
| `RA01_`, `MQ_ACT…`, `milM_Act_` | mission/AI/animation data (campaign, quests, locomotion acts) | `DataPC_patch_01` |
| `HDG` (mid-name) | **Handgun** weapon class (e.g. the P12 pistol) | weapon names |
| `HK` (mid-name) | manufacturer/family tag (Heckler & Koch) | weapon names |

> These are working interpretations. `FTP` vs `TP` in particular needs confirmation — both appear, and the F could denote face, female, or first-person-vs-third. Don't hard-code assumptions on the unverified expansions.

## Detail-level suffixes (verified)

### `LOD0` … `LOD3` — mesh Level Of Detail
Lower number = higher detail. `LOD0` is what you see up close; `LOD3` is the distant/cheap version. A mesh resource typically exists as a **full LOD set**; a replacement should provide (or at least not break) all the LODs the original had, or the asset will pop/disappear at distance. See [`10-meshes-and-skeletons.md`](10-meshes-and-skeletons.md).

### `Mip0` … `MipN` — texture mipmaps
`Mip0` = full resolution; each higher number = half-size. Textures may also exist as a **base entry with no mip suffix** plus separate `Mip0`/`Mip1` entries (observed: `FTP_Head_Angel_NormalMap_PC` alongside `FTP_Head_Angel_NormalMap_PC_Mip0` and `…_Mip1`). ATK can generate the mip chain on import. See [`09-textures.md`](09-textures.md).

### Texture channel tags (verified)
`DiffuseMap`, `NormalMap` are common; materials reference a set of these. The named slots live in a **TextureSet** (ATK gives names to all TextureMap slots).

## Variant suffixes (verified — important for faces/hair)

Hair and headgear-adjacent meshes ship **compatibility variants** so they fit under different equipment. Observed for one hairstyle:

```
TP_Hair_CornRawA                 (base)
TP_Hair_CornRawAForGoggles
TP_Hair_CornRawAForHelmetGoggles
TP_Hair_CornRawAForGazMask
TP_Hair_CornRawAForHeadsetsGoggles
TP_Hair_CornRawA_ForNVG
```

Each variant has its **own full LOD set**. The practical lesson: **a single visible hairstyle is many resources.** Replacing "the hair" means handling every `For…` variant × every `LOD`, or the hair will look wrong whenever the player wears the corresponding headgear.

Face heads similarly split into sub-meshes: `…_eyebrow`, `…_eyeShadow`, `…_eyelashes`, each with their own LODs, plus the head mesh and its diffuse/normal textures.

## Weapon component sub-parts (verified)

Weapons decompose into named components, each a separate resource: `_Main`, `_Receiver`, `_Barrel`, `_Muzzle`, `_Magazine`, etc. The item/gameplay definitions (`WI_`/`WG_`) reference these parts; the resources forge holds their meshes. (See the USP case study: [`examples/case-study-usp-tactical.md`](../examples/case-study-usp-tactical.md).)

## The `77777` placeholder-ID convention (inferred, strong)

In the USP mod, **every new mesh resource in the resources forge shares the file ID `77777`**:

```
77777_-_WG_HK_USP45_Receiver_LOD0
77777_-_WG_HK_USP45_Magazine_LOD0
77777_-_WI_HK_USP45_Receiver_LOD0
…
```

Real game IDs are unique, so `77777` is clearly a **modder placeholder/sentinel** used while authoring new (non-replacement) content — a recognizable "this is mine / assign me a real ID" marker. The corresponding *definition* entries use normal-looking IDs (`30091`, `28580`, `26`, `3950`), suggesting the placeholder is used on the bulk resource side and reconciled with real references via the BuildTable/definition layer.

> **Open question:** exactly how `77777` resources get resolved to real IDs at repack/load — whether ATK reassigns them, whether the BuildTable references resolve them by name, or whether the game tolerates duplicate IDs in a patch context. Flagged in [`meta/research-log.md`](../meta/research-log.md). Treat `77777` as a known idiom, not a fully-understood mechanism, until confirmed.

## Mod folder naming (community / Nexus)

Folder names in the wild mix two styles:
- **Nexus-style**: `Strix face V2-1550-V2-1757740151` → `<Name>-<modID>-<version>-<unixTimestamp>`.
- **Workflow folders** the author made: `Sheva_resources`, `Sheva_buildtables`, `acostabisonbattlebelt_DataPC_Resources_patch_01.forge` — named for *which forge layer* they repack into.
