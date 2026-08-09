# Reference — BuildTable XML (ATK export format)

> **Status:** First structural reference for GRB BuildTables. Derived 2026-08-09 from **two screenshots of a real ATK XML export** (`0_-_TP_Pants_511Apex.xml`, `tool="AnvilToolkit" toolVersion="1.2.10"`) posted by **SAMIEVILPUMA** in *Tier 1 Imports* `#mod-tutorials`, thread *"Super short and simple way to move mods to another slot"* (message `1414435798090256437`, 2025-09-08; attachments `Screenshot_2025-06-17_211627.png` / `…211641.png`). **Element and attribute names below are read directly off those exports and are verified as literal text.** Their *semantics* are largely **inferred** and flagged where so. Provenance: [`../meta/research-log.md`](../meta/research-log.md) (2026-08-09).

[`docs/03-data-and-resources.md`](../docs/03-data-and-resources.md) describes a BuildTable as the "recipe" that assembles an item from parts, and notes ATK can export one to XML. This file documents **what that XML actually looks like** — which matters because the community's standard technique for moving a mod between gear slots is a copy-paste inside this XML.

## Getting the XML in and out of ATK

| Direction | Action |
| --- | --- |
| **BuildTable → XML** | Double-click the `.buildtable` in ATK → it prompts to save → ATK writes a sibling `.xml` **in the same folder as the buildtable**. |
| **XML → BuildTable** | Right-click the `.xml` in ATK → **Compile**. ATK overwrites the existing BuildTable, or creates a new one, from the edited XML. |

Then repack normally: the inner container first (`TEAMMATE_Template`), then the outer forge (`DataPC_patch_01`). See [`../docs/07-modding-workflow.md`](../docs/07-modding-workflow.md).

## Document skeleton (verified — names as they appear)

```xml
<?xml version="1.0" encoding="utf-16"?>
<?info tool="AnvilToolkit" toolVersion="1.2.10" type="0"?>
<BuildTable ID="1778867967382">                        ← real 64-bit resource ID. NEVER copy this line.
  <List Name="ForceBuiltTableTOCOrder" Type="FileReference" />
  <List Name="BuildColumns">
    <BuildColumn ID="4160749568" Index="1">
      <Value Name="Pass" Type="Enum" EnumName="BuildColumnPass"
             ValueName="PropertyModifications2">5</Value>
      <PropertyPath Name="TargetProperty" ID="4160749569">
        <List Name="Nodes" />
        <Value Name="TargetMustBeUnique" Type="Bool">True</Value>
        <Value Name="SetWholeArray"      Type="Bool">False</Value>
      </PropertyPath>
      <List  Name="EntityPositionSelections" Type="ScimitarClass" />
      <Value Name="HasTableRef" Type="Byte">1</Value>
      <List  Name="Components" Type="DynamicProperty">
        <DynamicProperty>
          <Value Name="DataType" Type="UInt32" HashName="GraphicObject">3966419799</Value>
          <Value Name="Type"     Type="UInt32">1835008</Value>
          <Value Name="Unk00"    Type="UInt32">0</Value>
          <Reference>
            <FileReference Name="Value" IsGlobal="0" Path="0">0</FileReference>
          </Reference>
        </DynamicProperty>
      </List>
    </BuildColumn>
    <BuildColumn ID="4160749570" Index="2"> … HashName="BuildTable">585940579 … </BuildColumn>
    <BuildColumn ID="4160749572" Index="10"> … </BuildColumn>
  </List>

  <List>                                               ← BuildRows
    <BuildRow>
      <List>
        <DynamicProperty Index="13">
          <Value Name="DataType" Type="UInt32" HashName="GraphicObject">3966419799</Value>
          <Value Name="Type"     Type="UInt32">1179648</Value>
          <Value Name="Unk00"    Type="UInt32">0</Value>
          <Handle>
            <Value Name="Value" Type="UInt64"
                   Path="DataPC\TP_Holster_Omnivor\TP_Holster_Omnivor.LODSelector">1661865036083</Value>
          </Handle>
        </DynamicProperty>
        <DynamicProperty Index="18"> … FTP_Casper_Holster.LODSelector">1746200992799 … </DynamicProperty>
      </List>
    </BuildRow>
  </List>

  <Value Name="ShuffleSelection" Type="Bool">False</Value>   ← copy boundary (see below)
  <BaseObject Name="DefaultSelections">
    <RowSelector ID="4160749580">
      <Value Name="BuildColumnMask"  Type="UInt32">0</Value>
      <Value Name="StableRandomSeed" Type="UInt32">0</Value>
      <BaseObject Name="SelectedTags">
        <BuildTags Name="Value" ID="4160749581"><List Name="Tags" /></BuildTags>
      </BaseObject>
      <List Name="Selections" />
      <Handle Name="AssociatedEntityBuilder">
        <Value Name="Value" Type="UInt64"
               Path="DataPC\TEAMMATE_Template\TP_Pants_511Apex.BuildTable">1778867967382</Value>
      </Handle>
      <List Name="AdditionalTables" />
    </RowSelector>
  </BaseObject>
  <Value Name="IgnoreDefaultSelectionsWhenUsingTags" Type="Bool">False</Value>
  <Value Name="AlwaysMergeDefaultSelections"         Type="Bool">False</Value>
  <Value Name="DynamicTable"                         Type="Bool">True</Value>
  <Value Name="x73B5D0A0"                            Type="Bool">False</Value>
  <List  Name="x67660D91">
    <Handle><Value … Path="DataPC\BODARK_RIFLEMAN_CAMO\tag_MAL.BuildTable">516281366872</Value></Handle>
    <Handle><Value … Path="DataPC\BODARK_RIFLEMAN_CAMO\tag_FEM.BuildTable">516281366871</Value></Handle>
  </List>
</BuildTable>
```

## Two ID spaces — don't confuse them (verified)

This is the single most important structural fact in the file, and it is why the slot-move procedure works.

| Where | Example | What it is |
| --- | --- | --- |
| `<BuildTable ID="…">` (root) and every `Handle`/`FileReference` value | `1778867967382`, `1661865036083` | A **real 64-bit resource ID** — the embedded `ClassID` (see [`../docs/03-data-and-resources.md`](../docs/03-data-and-resources.md)). Identity. Global. |
| `ID=` on `BuildColumn`, `PropertyPath`, `RowSelector`, `BuildTags` | `4160749568`…`4160749581` | A **file-local object handle**, allocated as a sequential counter. |

> **Verified:** the inner `ID`s are consecutive values starting at **`0xF8000000`** — `4160749568 = 0xF8000000`, `…569 = 0xF8000001`, `…570 = 0xF8000002`, `…580 = 0xF800000C`, `…581 = 0xF800000D`. They are per-file serialization handles, not resource IDs, and carry no meaning outside the document.

So the root `ID` line says *"which BuildTable this is"* — i.e. which item slot the game resolves — while everything under it says *"what that slot builds."* Swapping the body while keeping the root ID is exactly how you move a mod onto a different slot.

Note that `AssociatedEntityBuilder` near the bottom **re-states the root ID** (`1778867967382`) with a resolved path. It travels with the *original* slot, which is why the tail is left alone.

## Resolved `Path=` strings (verified)

ATK resolves handle targets to readable logical paths of the shape **`DataPC\<Container>\<Name>.<Type>`**:

```
DataPC\TEAMMATE_Template\TP_Pants_511Apex.BuildTable
DataPC\TP_Holster_Omnivor\TP_Holster_Omnivor.LODSelector
DataPC\FTP_Casper_Holster\FTP_Casper_Holster.LODSelector
DataPC\BODARK_RIFLEMAN_CAMO\tag_MAL.BuildTable
DataPC\BODARK_RIFLEMAN_CAMO\tag_FEM.BuildTable
```

Two things this independently confirms:

- **`TEAMMATE_Template` really is the container worn-gear item definitions route through** — previously established from mod folder names ([`mod-anatomy.md`](mod-anatomy.md)); here it appears inside live data, on a *pants* BuildTable. Reinforces that the "TEAMMATE" name is misleading and covers player gear.
- **Gender variants are handled by tag BuildTables**, `tag_MAL` / `tag_FEM`, carried in a list of `Handle`s at the document tail (IDs `516281366872` / `516281366871` — consecutive). This is the mechanism behind the `TP_`/`FTP_` pairing documented in [`mod-anatomy.md`](mod-anatomy.md).

## `DynamicProperty.DataType` is a CRC32 type id (verified)

`DataType` carries the **same 32-bit type-id space** as a `.data`'s typed-resource records — `CRC32(typeName)` — with ATK resolving it in the `HashName` attribute:

| Value | `HashName` | Check |
| ---: | --- | --- |
| `3966419799` | `GraphicObject` | `zlib.crc32(b"GraphicObject") = 3966419799` ✓ |
| `585940579` | `BuildTable` | already verified in [`resource-type-ids.md`](resource-type-ids.md) ✓ |

So a `DynamicProperty` is *"a slot of type T, pointing at resource R"*. See [`resource-type-ids.md`](resource-type-ids.md) for the full id↔type table and the method.

## Field notes (inferred unless marked)

| Element / attribute | Reading |
| --- | --- |
| `ForceBuiltTableTOCOrder` | A `FileReference` list, empty here. Name implies an explicit **table-of-contents ordering** override for built tables. *(inferred; unexercised in this sample)* |
| `BuildColumn` `Index` | Observed `1`, `2`, `10` — sparse, so the index is a **meaningful slot number**, not a position. *(inferred)* |
| `Pass` = `PropertyModifications2` (`5`) | Enum `BuildColumnPass`; which build pass the column applies in. *(inferred)* |
| `PropertyPath` / `Nodes` / `TargetMustBeUnique` / `SetWholeArray` | Addresses the target property the column writes into. `Nodes` empty in this sample. *(inferred)* |
| `HasTableRef` (Byte) | `1` on the columns seen; flags that the column references another table. *(inferred)* |
| `DynamicProperty` `Index` | Observed `13`, `18` on rows — again sparse slot numbers. *(inferred)* |
| `Type` (UInt32) | `1835008` = `0x1C0000`, `1179648` = `0x120000`. Both are `<byte> << 16`. Meaning unknown — a slot/usage code. **Open.** |
| `Unk00` | Named `Unk00` by ATK itself, i.e. unknown to the tool too. `0` throughout. |
| `Reference` / `FileReference IsGlobal="0" Path="0">0` | An **empty/null** reference — the "no target" form, contrasted with `Handle` which carries a real one. *(inferred)* |
| `ShuffleSelection`, `DefaultSelections`, `RowSelector`, `BuildColumnMask`, `StableRandomSeed`, `SelectedTags`/`BuildTags` | Selection machinery — how the game picks a row (randomized/tagged variants). *(inferred)* |
| `DynamicTable` = `True` | *(inferred)* the table is resolved at runtime rather than fully baked. |
| `x73B5D0A0`, `x67660D91` | **Unresolved name hashes.** ATK prints `x<HEX>` when a field-name hash isn't in its dictionary (`0x73B5D0A0` = `1941295264`, `0x67660D91` = `1734741393`). `x67660D91` holds the gender-tag handles. Good candidates for the hash dictionary. |

## Procedure — move a mod to another gear slot

Source: SAMIEVILPUMA, thread above. Positioned as the **quick path for like-for-like moves** (vest → another vest slot). For cross-category moves that need precision (e.g. scarf → face paint), he points to **Spncryn's** longer BuildTable tutorial instead. Step numbering normalized (the original has two step 3s).

1. In ATK, double-click the `.buildtable` **the mod shipped** — the one you want to move.
2. Click **save**; ATK writes an `.xml` beside it. Open the XML.
3. **Start the highlight directly under the `<BuildTable ID="…">` line.** That ID line and everything above it is never copied and never overwritten.
4. **End the highlight directly above the `<Value Name="ShuffleSelection" …>` line.** `ShuffleSelection` and everything below stays as-is — it's not important to the move, but keeping it documents what the original table was for.
5. Copy the highlighted block.
6. Open the `.buildtable` of the **destination gear slot** the same way (steps 1–2). These live in **`TEAMMATE_Template`**.
7. In the destination XML, highlight **the exact same region** — under its own `ID` line, down to above its own `ShuffleSelection`.
   > ⚠️ The highlights must match in shape on both sides. Formatting matters; follow the boundaries above precisely.
8. Paste. It should overwrite all of those lines. Save the XML.
9. In ATK, right-click the saved XML → **Compile**. ATK overwrites the BuildTable, or writes a new one, with your edits.
10. ⚠️ Repack `TEAMMATE_Template`, then repack `DataPC_patch_01`.

**Why it works:** the destination keeps its own root `ID` — so the game still resolves *that* slot — while the body it builds becomes the mod's. Consistent with the ID-keyed override model in [`../docs/06-game-load-and-reassembly.md`](../docs/06-game-load-and-reassembly.md).

**What it does not cover:** mods that ship only `.data` files (camo, textures, faces, UI). There is no BuildTable to edit — SamiPuma's answer in-thread is to open the target's **DiffuseMap and replace it** instead. Matches the resource-only fingerprint in [`mod-anatomy.md`](mod-anatomy.md).

**Fan-out warning:** some slots are not one BuildTable. Beards, like hair, are split by headgear compatibility — *"the beard that shows up when you're wearing a facemask, a balaclava, helmet with straps, etc are all different, meaning you have to add it to all relevant buildtables"* (SAMIEVILPUMA, same thread). Doing one is not doing the slot. "Not hard, just tedious."

## Open questions

- The `Type` code (`0x1C0000` / `0x120000`) on `DynamicProperty`.
- Whether `ForceBuiltTableTOCOrder` is ever populated, and what ordering it forces — potentially relevant to the entry-ordering question in [`../docs/08-naming-conventions.md`](../docs/08-naming-conventions.md).
- Resolve `x73B5D0A0` / `x67660D91` against ATK's hash dictionary.
- Whether the copy boundaries hold for **non-gear** BuildTables (weapons via `dbcontainer`, solid-colour mods) — the procedure is only attested for `TEAMMATE_Template` gear slots.
- Only one export has been seen (a pants item, ATK 1.2.10). A second sample from a different category would confirm which elements are universal.
