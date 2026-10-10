# Converting GRW Materials to GRB (2026-10-10)

How Ubisoft converted Wildlands (GRW) Materials and TextureSets when it brought
shared meshes into Breakpoint (GRB). Also how
[`tools/grw_materials.py`](../tools/grw_materials.py) reproduces that conversion for the Bolivia
port. The tool's rule tables are in
[`tools/grw_materials_rules.json`](../tools/grw_materials_rules.json). Running `grw_materials.py learn`
regenerates them from the two installs.

Related: [notes-id-collisions.md](notes-id-collisions.md) covers which texture IDs can be kept,
and [notes-terrain-tbf.md](notes-terrain-tbf.md) covers terrain materials, which are a different
resource type (`TerrainMaterial`) handled by `terrain_material.py`.

## Summary

- **Evidence.** 1,315 Mesh entry IDs exist in both installs. Inside them, **238 GRW/GRB material
  pairs share at least one TextureMap.** Those are Ubisoft's own conversions. Positional pairs
  that share no texture are Ubisoft swapping in a GRB library material, so they are not
  conversions and are not used for rules.
- **Format.**
  - Every Material and TextureSet in both games parses and rebuilds byte-exact: 3,310 GRW and
    3,644 GRB payloads, none unparsed.
  - The GRB head differs from GRW in two places: 7 extra flag bytes, and no `Category` field.
  - TextureSets have the same 202-byte layout in both games.
- **Parameter names are CRC32 of the template's display label,** category prefix included. For
  example, `crc32("0: Layer1 Albedo Map") = 0xE81E62B3`. The labels are plain strings inside the
  MaterialTemplate payloads, so every hash can be named.
- **A GRB material writes the template's full parameter set:** one label set per template, 21 of
  21 targets. Only the order varies.
- **What happens to GRW spec maps.** Ubisoft dropped them: 5 of 89 Specular TextureSet slots
  survive. The `Specular` selectors and every gloss/spec scalar are dropped too. No GRW spec or
  gloss value is carried into a GRB roughness or metal parameter.
- **The template choice is reproducible for most materials, but not all.**
  - `SHD_Basic` → `SHD_BAS_Dielectric` 44 of 58, otherwise `…DielectricMetallic_v2_TEMP`.
  - Nothing in the GRW material predicts which of the two Ubisoft picked. Float values, texture
    layout and header bytes are identical between the two groups, so the choice was an artist's.
  - The tool takes the majority and says so.
- **Held-out validation** (learn on half the twins, test on the other half):
  - 86% of parameter values equal Ubisoft's (88% in-sample);
  - 94–96% of texture references equal;
  - the template equals Ubisoft's in 69–72% of pairs.

## Method (verified)

Read-only, memory-capped, streamed one container at a time.

- **Twins.**
  - Collect every Mesh entry ID found both in GRW `DataPC*.forge` (including the `dlc_NN\`
    subfolders, with patch overriding base) and in GRB `DataPC_Resources*.forge`.
  - Read both containers. Pair materials inside them greedily, by the number of shared
    TextureMap IDs. IDs below 4096 are engine defaults (`Default Normal Texture` = 9) and are
    ignored.
  - A material's textures are its TextureSet's slots plus its selectors' TextureMap refs.
- **Positional pairing over-counts.** The earlier mesh-slot pairing, which compares material *i*
  of a GRW mesh with material *i* of its GRB twin, produced 381 pairs. Many of those are
  replacements, for example:
  - `BAS_ENV-SPE-PropsBenchRural-B` → `TRIM_GEN_WoodEndsCutA_CONVERT`;
  - `BAS_ENV-GEN-MetalWire-C-AlphaTest-2S` → `BAS_GEN_MetalRustA`.

  Replacements are almost always on `SHD_BAS_DielectricMetallic_v2_TEMP`, which is why
  positional counts overstate that template. The W3 statue test's hand-cloned GRB material,
  `BAS_GEN_MetalRustA`, is one of these library materials.
- **Labels.** Hash every printable string in all 152 GRW and 124 GRB MaterialTemplate payloads
  with CRC32. The result names every parameter hash seen in the twins.

## Format (verified; details in the tool's docstring)

### Material

```
u64 ClassID | u32 0x85C817C3 | u8 1 | FileRef template @13 | FileRef TextureSet @23
| Mask object @33 (u64 0xF8000000, u32 0xDF5D6C0E, u8) | i32 BlendMode @46 | i32 AlphaDisplayMode @50
| flags @54 | FileRef backface | MaterialMatchMask object (u64 0xF8000001, u32 0x92B95F74, 16 B)
| [GRW only: i32 Category, = 5 in every twin] | u32 n | n x param
```

GRW has 22 flag bytes and its params start at 118. GRB has 29 flag bytes and its params start at
121. ATK's GRB reader names the 29 flags (`AlphaTestValue`, `ZWriteDisabledOpaque`, …,
`ExtraShaderListReserve`).

> **Verified:** aligning GRW's 22 flags into GRB's 29 over 235 twins gives
> `GRB = GRW[0:10] + 0 + GRW[10:14] + 0×5 + GRW[14:21] + 0 + GRW[21]`, with
> **5,156 of 5,170** flag bytes agreeing. The 14 misses are Ubisoft retouching individual
> materials (mostly `AlphaTestValue`). The seven inserted bytes are 0 in every twin.

> **Inferred:** the names of the seven new flags are ambiguous. They sit inside runs of other
> always-zero flags, so the alignment fixes their positions but not which of ATK's names they
> carry.

- **Template ref.** GRB writes the template ref as `01 01 <id>` (230/235).
- **TextureSet ref.** GRB writes `01 00 <id>`.
- **Copied fields.** Mask, BlendMode/AlphaDisplayMode and MatchMask copy straight across
  (235/235, 233/235 and 218/235).

### Parameters

The parameter record is `u32 nameHash | u32 DataType | u32 Type | u32 unk | value`. Three kinds
of inline object (Type `0x130000`) occur:

- **TextureSelector** (DataType `0x7D08460D`, 53 B).
- **UVTransform** (`0xC52E2125`, 46 B).
- **TimeOscillatorData** (`0xECE5D96C`, 36 B). ATK reads a u32 type and three floats; 8 more
  bytes follow in both games. 36 is the only size that parses every material, which covers the
  laser dot and rotor-blur materials.

### TextureSelector

```
u64 objectId | u32 0x7D08460D | u8 | i32 method @13 | i32 mapType @17 | i32 frame @21
| FileRef TextureSet @25 | FileRef TextureMap @35 | u64 @45
```

> **Verified:** the method values follow ATK's `TextureSpecificationMethod` (0
> `MaterialTextureSet`, 1 `OverridenTextureSet`, 2 `OverridenTextureMap`). **With method 0,
> the TextureMap ref is a cached copy of the material TextureSet's `slot[mapType]`.** That holds
> in every resolvable case: GRW 749/749, GRB 679/679. So textures mostly flow through the
> TextureSet, and the selector caches the result.

### TextureSet

```
u64 ClassID | u32 0xD70E6670 | u8 1 | 18 x FileRef @13 | u8 0 | u64 source
```

The 18 slots are: Diffuse, Normal, Specular, OffsetBump, Emissive, Transmission, Occlusion, Mask1,
Mask2, Cookie, EnvLighting, Generic, Diffuse1–5, VectorDisplace. `mapType` is the slot index.
171 twin TextureSets keep their ClassID across games.

### Inline object IDs

GRB keeps the GRW object ID when a parameter label survives (357/442). Renamed or new labels get
fresh IDs. About 10% of objects in both games use local-style IDs (`0xF80000xx`), and a few IDs
repeat across materials, so global uniqueness is not required.

> **Inferred:** keeping GRW IDs, and using local `0xF8000002+` IDs for new objects, is safe. The
> tool does this.

### `IsGlobal`

This is the middle byte of a FileReference, named by ATK. It is a per-texture property:

- 613/619 GRB and 749/758 GRW textures are always referenced with the same value.
- All GRB textures live in `DataPC_Resources`, yet carry 1, 2 or 4, so the byte does not encode
  the forge.
- Ubisoft changed it for some shared textures. Of the textures referenced in both games, 115
  went from 2 to 1.

> **Inferred:** use GRB's value for class-a textures. `grw_materials.ref_flags_from()` reads it
> from GRB payloads. For textures new to GRB, keep GRW's value. Its meaning is still open.

## Template choice (verified counts; `grw_materials.py templates` prints the live table)

"Thin" means fewer than 3 conversions, or a majority under 67%.

| GRW template | id | conversions | GRB target(s) |
| --- | --- | --- | --- |
| SHD_Basic | 42175742799 | 58 | **SHD_BAS_Dielectric** 44, DielectricMetallic_v2_TEMP 13, BreakableFence 1 |
| SHD_Weapon_Gunsmith | 306813097118 | 41 | **SHD_W_Body_Main** 41 |
| SHD_Weapon_InGame | 276823147996 | 38 | **SHD_W_Body_Main** 32, Dielectric 5, v2_TEMP 1 |
| SHD_Basic_Metallic_GlossMask | 1107529338323 | 36 | **v2_TEMP** 24, Dielectric 12 (thin) |
| VEH_Body_WITHCUSTOMNODE | 519127172610 | 11 | **TGT_VHC_Body** 11 |
| SHD_Nat_Veg_Leaves_Mask | 77971378242 | 8 | **SHD_NAT_Veg_Leaves_Mask** 5, …_ALPHATEST_NotGPU 3 (thin) |
| SHD_Basic_Metallic | 34179593778 | 8 | **SHD_Basic_Metallic** 5 (same template, still in GRB), 3 others (thin) |
| SHD_Nat_Veg_Basic_AO | 74456416868 | 6 | **SHD_NAT_Veg_Basic_AO** 6 |
| SHD_Basic_AlbedoColor | 173768518260 | 4 | v2_TEMP 2, Dielectric 2 (thin) |
| SHD_Detail_AlbedoColor | 243142767540 | 3 | Dielectric 2, Dielectric_Cloth 1 (thin) |
| 21 more | | 1–2 each | see `templates`. All thin; the VEH_* and SHD_IA/SHD_W_Laser templates map to themselves |

Target IDs: SHD_BAS_Dielectric `1498533326620`, SHD_BAS_DielectricMetallic_v2_TEMP
`1825790666323`, SHD_W_Body_Main `1656562692981`, TGT_VHC_Body `1456070671961`,
SHD_NAT_Veg_Leaves_Mask `1498533388534`, SHD_NAT_Veg_Basic_AO `1561874137350`.

> **Verified: thin evidence, not guessable.** For `SHD_Basic`, the 44 Dielectric and 13 v2_TEMP
> conversions have identical distributions of every GRW float, the same texture layout and the
> same 85 header bytes.
>
> For `SHD_Basic_Metallic_GlossMask`, `2: Gloss is Specular Color = 1.0` leans towards v2_TEMP
> (13 of 24 conversions, against 1 of 12 Dielectric ones). But 11 v2_TEMP conversions have 0.0,
> as 11 Dielectric ones do, so the parameter does not decide the target.
>
> The tool takes the majority. `convert(..., target=)` overrides it.

### Coverage of GRW's real materials (verified)

A census of every GRW Mesh container (18,809) found **5,292 distinct materials**:

| | strong evidence | thin | none |
| --- | --- | --- | --- |
| all 5,292 | 34% | 17% | 49% |
| 1,816 in `GRN_WorldMap*` forges | 29% | 40% | 31% |

Most of the "none" share is characters: `CHR_cloth_Detail` 1,500, `CHR_Skin` 258, `CHR_Hair` 97.
For the world, these templates have no conversion (world-forge material counts shown):

- **Blend family:** `SHD_Blend_Basic` 84, its two ColorMul variants 67,
  `SHD_Blend_Parallax-to-Basic` 24, `SHD_Blend_Metal` 13.
- **Rocks:** `SHD_Nat_Rock` 34, `SHD_Nat_Rock_LOD` 18.
- **Others:** `SHD_Basic_AlbedoColorMask` 51, `SHD_Basic_Glass` 21, `SHD_Nat_Veg_Leaves` 15.

Ubisoft's *replacements* for those templates are nearly all v2_TEMP library materials. That
records Ubisoft's habit, not a conversion rule.

`convert()` raises `NoEvidence` for these templates unless you pass `fallback=`. The `report`
shows which texture slots found a source.

> **Inferred:** single-layer templates whose labels the Dielectric rules recognise convert
> sensibly with `fallback=1498533326620`. Blend materials lose their second layer under every
> target the tool knows. A real blend target would need GRB blend twins, and no
> `SHD_BLE_SPB-Structure_Array` conversion exists.

## What a conversion does (rules learned per GRB target)

### Labels

- A GRB label is filled from the GRW label whose texture matched it.
- Scalars are copied when the GRW label exists **and** copying reproduces more twins than
  Ubisoft's usual value. Otherwise the scalar gets Ubisoft's usual (modal) value.
- GRW labels with no GRB counterpart are dropped and listed in `report["dropped"]`.

### Texture slots

| GRB target | GRB label ← GRW label (by matching texture) |
| --- | --- |
| SHD_BAS_Dielectric | `0: Layer1 Albedo Map` ← `0: Layer1 Diffuse + Alpha Map` (or `0: Layer1_Diffuse+Alpha Map`, `3:Layer0_Diffuse`); `0: Layer1 Normal Map` ← same label (or `0: Layer1_Normal Map`, `3:Layer0_Normal`) |
| DielectricMetallic_v2_TEMP | `0-Albedo/Reflectance + Metallness Map` ← `0: Layer1 Diffuse + Alpha Map`; `0-Normal Map` ← `0: Layer1 Normal Map` |
| SHD_W_Body_Main | `0: Layer1 Diffuse + Alpha Map`, `0: Layer1 Normal Map`, `Camo`: same labels |
| SHD_NAT_Veg_* | `0: Layer1 Diffuse + Alpha Map`, `0: Layer1 Normal Map`, `0: Layer1 Mask`: same labels |
| TGT_VHC_Body | only `0: Mask2` matches. The vehicle diffuse, normal and camo textures were re-authored, so the selector is built from Ubisoft's usual `(method, mapType)` and resolves through the TextureSet |

### Scalars

- **SHD_BAS_Dielectric** (9 params):
  - Copied: `4: U/V Transform`, `5: Heat` and `2: Specular Occlusion`. For Specular Occlusion,
    copying matches 37 twins and the constant 25.
  - Constants: `1: Color` = (1,1,1,1), `1: Vertex Color` = 0 and `2: Specular Roughness Offset`
    = 0.
  - Dropped: `1: Alpha Power/Value`, `2: Specular Gloss Intensity/Mask`,
    `2: Specular Reflectance` and the `2: Gloss is Specular *` family.
- **v2_TEMP** (32 params): 30 are Ubisoft's usual values: paint mask, metal mask, roughness
  array and dust. They do not track any GRW value (checked against Specular Reflectance, Gloss
  Intensity/Mask, Specular Occlusion and Gloss power over all 43 twins). Only albedo and normal
  come from GRW.
- **SHD_W_Body_Main:** the `[Paint] Color/Gloss/SpecReflectance` values were changed by Ubisoft
  in every weapon (73/73), so the tool writes GRB's usual values, not GRW's.

### Every GRB material needs a non-null TextureSet

> **Verified in game:** a GRB material whose TextureSet ref is null renders **magenta**.
> - In W6, 12 of 12 converted materials had null sets and every one rendered magenta.
> - All 158 vanilla GRB materials on v2_TEMP carry a set.
> - W6b fixed it with a synthesized 202-byte set.

> **Verified (twins):** Ubisoft did the same thing every time a GRW material had no set (9
> conversions):
> - It built a set from the material's direct selectors: the diffuse into slot 0 and the normal
>   into slot 1, **by role**. One GRW diffuse sat at mapType 12 and still went to slot 0.
> - It switched those selectors to method 0 with mapType 0/1.
>
> `convert_pair()` reproduces this. Its synthesized Diffuse+Normal equals Ubisoft's set in 8 of
> 9 cases; in the ninth, Ubisoft swapped in a sibling's diffuse by hand. Selector
> method+mapType equals Ubisoft's in 16 of 18; in the other two, Ubisoft left a Dielectric
> normal on method 2.

- **The set's ID** is `textureset_id=` if given. Otherwise it is the material ClassID with bit 45
  set (`SYNTH_TS_TAG`).
- **Inferred:** bit 45 is safe because no ID in either game uses bits 42–62 (see
  notes-id-collisions.md), and it cannot meet the re-ID tags at bits 46 and 62.
- **The trailing `source`** is set to `id − 1`. That is the pattern of 213/260 GRW and 212/264
  GRB sets; the field is never 0 in vanilla.

### TextureSets

- Same layout.
- IDs go through the texture map; an unmapped ID → null slot (`03` + 9 zero bytes).
- Slots that Ubisoft dropped for the target become null: **Specular everywhere (5/89 kept), and
  Mask1 too for Dielectric (1/11 kept).** Mask1 survives for weapons (73/73).

### Header

- ClassID and the TextureSet ref are kept.
- The template ref is replaced.
- Flags are expanded as above, and `Category` is removed.

## Validation (verified, `grw_materials.py selftest`, 2026-10-10 installs)

The tool learns from half the twins and converts the other half, forcing the target to
Ubisoft's template so that parameter fidelity is measured on its own.

| | in-sample | held-out A→B | held-out B→A |
| --- | --- | --- | --- |
| template = Ubisoft's | 195/238 | 82/119 (+7 unseen) | 86/119 (+12 unseen) |
| same parameter set | 238/238 | 112/112 | 112/112 |
| parameter values equal | 3,890/4,427 (88%) | 1,797/2,078 (86%) | 1,813/2,119 (86%) |
| texture refs equal | 561/589 (95%) | 267/283 (94%) | 266/278 (96%) |
| header 0..121 equal | 196/238 | 97/112 | 92/112 |
| TextureSet byte-exact, GRB `IsGlobal` | 193/225 | 87/108 | 92/106 |
| whole material byte-exact | 11/238 | 2/112 | 4/112 |

Whole-material byte-exactness is low for two reasons that do not change behaviour:

- **Ubisoft's parameter order is arbitrary.** There are 37 orders over 72 Dielectric materials,
  and kept labels follow GRW's order only 113/235 times.
- **Ubisoft gave renamed selectors fresh object IDs.**

The remaining value differences are Ubisoft's own edits: re-authored textures, retouched paint,
and per-material v2_TEMP values.

## Dry run: Cell02757 (2026-10-10)

Every material used by the cell's 21 external and 22 cell-local meshes was converted. That is
12 materials, the same set as the port's dependency list.

The texture map:
- shipped textures → identity;
- 7 colliding textures → `grw_reid.reid()`;
- anything else stays only if it is class a;
- not-shipped class-b/c textures → None.

> **Verified (dry run):**
> - **Converted:** 12/12, each returned with a non-null TextureSet, **4 of them synthesized**
>   (both BrickMessy materials, RoadPlate-Town and MetalBolts).
> - **References:** **0 dangling texture references.** Every ref in every output material and
>   set is shipped (27), re-IDed (3) or class a.
> - **Templates:**
>   - Six materials took majority targets: `SHD_Basic` → Dielectric for 5, and
>     `SHD_Basic_Metallic_GlossMask` → v2_TEMP for the electric pole.
>   - Two kept `SHD_Basic_Metallic`.
>   - Four had no twin evidence and used the agreed Dielectric fallback:
>     - `BLE_…BrickMessy…` and `BLE_…MetalBareSteel…`, two-layer blends, which lose layer 2
>       (14 and 15 GRW labels dropped);
>     - `SHD_Basic_TerrainAlbedo` (BrickMessy-Cap);
>     - `306120848940` (FabricCanvasDirt-VertexNoise).

> **Hazard: class-a IDs.** The converter keeps the material's ClassID and its TextureSet's ID.
> `BAS_ENV-SPE-PropsElectricPole-A` (material `68310988285`, set `68310988260`) is **class a
> with its GRB home in `DataPC_Resources`**: Ubisoft ships its own conversion under those IDs.
> Putting ours in a patch forge under the same IDs would override Ubisoft's for every GRB asset
> that uses it. Either reference GRB's copy (the class-a policy in notes-id-collisions.md) or
> re-ID ours with `class_id=` and `textureset_id=`.
>
> Four more cell materials looked like class a in an earlier census, whose only GRB home for
> them was `DataPC_GRN_GhostRoom`, where the W3 statue test had staged them. The final census
> (`id_census.py`, taken after GhostRoom was restored) lists them as class c: they are our
> objects, not Ubisoft's. The pole's two textures and `ENV-GEN-Template-Color-Normal_NormalMap`
> are class a (same name and type in GRB). Class a does not promise identical bytes (see
> notes-id-collisions.md, open item 4), so re-IDing them to ship GRW's pixels is a content
> choice, not a collision fix.

## Open items

1. **The Blend family and rocks** have no conversion. They need a GRB blend twin, or an explicit
   decision to flatten them onto Dielectric.
2. **`IsGlobal` meaning.** It is a per-texture byte, values 1/2/4. Find out what it selects
   before relying on GRW's value for new textures.
3. **Does parameter order matter to the engine?** Inferred no, since every reader looks params
   up by hash and Ubisoft's own order varies. W8 is planned as the first in-game test of
   converter-built materials.
4. **The GRW `Category` value** (5 in every twin) is dropped. GRB has no such field in ATK's
   reader, and no twin contradicts dropping it.
5. **Method-1 selectors** (37 in GRW) point at their own TextureSet. The tool maps their cached
   TextureMap, but does not convert the referenced set.
