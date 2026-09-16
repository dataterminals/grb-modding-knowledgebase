# Reference — AI / NPC gameplay DB records

> **Status:** Machine-generated inventory — 2026-09-16. Every row was read from the **base**
> `DBContainerEntry_0X104634F921.data` of a live GRB install with
> [`../tools/db_inspect.py`](../tools/db_inspect.py). Counts, payload sizes and type ids are
> **verified**; the grouping and any reading of what a type *does* is **inferred from its name**.
> Background and method: [`../docs/14-ai-and-npc-behaviour.md`](../docs/14-ai-and-npc-behaviour.md).
> Provenance: [`../meta/research-log.md`](../meta/research-log.md) (2026-09-16).

The container holds **50,098 records** — 23,617 `DB*`-named across **1,008 types**, plus 26,481
others (`TGT_*`, `WaveSetting_*`, `*_SpawnEntityDescriptor`, quest/dialogue plumbing). This file
lists the **217 types** whose names place them in the AI / NPC / combat / drone area:
**2,674 instances** in total.

## How to read the table

- **Instances** — how many named records of that type exist. High counts mean per-faction,
  per-tier, per-unit variants; low counts mean a handful of global presets.
- **Payload** — a single number means **every instance is that size**, so instances are
  field-aligned and [`db_inspect.py --diff`](../tools/db_inspect.py) gives you an offset map.
  A range means the type is variable-size and you transplant whole bodies instead (see the
  `DBAIRadioCallConfig` worked example in the main doc).
- **Type id** — the schema. Names are the instances. **76 type ids in the container are shared
  by more than one name prefix** (`DBSimpleFightingBehaviour` and `DBDefensiveStrafeBehaviour`
  are both `0x131086dd`), so identical ids mean identical layout, not identical meaning.
- **Example instances** — the type prefix is stripped; these are the suffixes as they appear.

Recurring suffixes are the useful part: `_Default` and a **null variant** (`_NoCall`,
`_NoDetection`, `_NoConfidence`, `_NoChase`, `_NoGrenade`, `_NoRevive`, `_NoBush`,
`_NoStaticDefend`, `_NoVantage`, `_NoEscape`) that ships the "off" values — diff against those
to see the whole tunable surface at once. Then faction and role: `_Wolves`, `_Bodark`, `_Miter`,
`_Walker`, `_Fighter`, `_Rifleman`, `_Rusher`, `_Heavy`, `_Vantage` (snipers), `_DroneCarrier`,
`_Teammate`, `_Civilian`, and tiers `_MK1` / `_MK2` / `_MK3`.

## Regenerating this table

```bash
python tools/db_inspect.py "<install>/Extracted/DataPC.forge/<N>_-_DBContainerEntry_0X104634F921.data"
```

…for the summary line, and `--grep '^DBAI' --out ./out` to pull records for diffing. The table
below was produced by the same walker; re-run it after a title update to catch new types.

## Quick index — the highest-leverage types

| Want to change | Start at |
| --- | --- |
| How far enemies **see** | `DBSoldierVisualDetectionConfig` (525 B, handle bundle), `DBSoldierDetectorConfig` (507 B) |
| How far enemies **hear** | `DBSoldierSoundDetectionConfig` (303 B, raw metres — best first experiment) |
| Whether they **call backup**, and how much | `DBAIRadioCallConfig`, then `DBHunt` / `WaveSetting_Hunt_*` |
| How **aggressive** they push | `DBAIAssaultConfig`, `DBAgressiveStrafeBehaviour`, `DBChargeBehaviour` |
| How well they **shoot** | `DBSoldierAimingModifierConfig` (29 B), `DBSoldierWeaponUsageConfig` |
| **Grenades** | `DBSoldierGrenadeConfig` (41 B) |
| How long they **hunt you after losing contact** | `DBSoldierInvestigateSearch` (220 B), `DBAIChaseConfig` (54 B), `DBBushSearch` (55 B) |
| Whether downed enemies get **revived** | `DBSoldierRevivalConfig` (19 B) |
| **Toughness** | `DBNpcHealth` (408 B — but see the tier caveat in the main doc), `DBArmorType`, `DBHumanBodyPartType` |
| AI **knowing what it should not** | `DBAICheatConfig` (162 B; one instance is `_Miter_Omniscience`) |
| **Drones / Behemoths** | the `DBDroid*` and `DBAutonomousElement*` families (19 types, 186 instances) |
| **Difficulty presets** | `DBPredatorSettings` (`Conquest_Easy/Medium/Hard`), `DBDifficultyLevelBonusSettings` |

---

## The catalogue (217 types, sorted by instance count)

| Type | Instances | Payload (B) | Type id | Example instances |
| --- | ---: | --- | --- | --- |
| `DBBodyPartDescriptor` | 155 | 106 | `0x07bda218` | `Droid_AirSmall_Rotors`, `Droid_AirSmall_Hull`, `Droid_MediumAir_Shell`, `Droid_AirMedium_Rotors` |
| `DBCustomFightingBehaviour` | 149 | 408 to 754 (11 sizes) | `0x61810935` | `DF_CobraApproach_Wild`, `DF_Wave_Right_Up_Camp`, `DF_Wave_Left_Up_Camp`, `DF_Wave_Right_Down_Camp` |
| `DBArmorVisual` | 128 | 223 to 556 (6 sizes) | `0xc9d53e36` | `Miter_Head_MetalBossC`, `Mk2_Boot_Low`, `Mk2_Hood_Low`, `Hood_Mk1` |
| `DBSoldierWeaponUsageConfig` | 93 | 48 to 113 (3 sizes) | `0x6c925baa` | `SNR_HDG_Raid_Wolves`, `RL_HDG_Raid_Wolves`, `MG_Raid_Mark3`, `ASR_Raid_Marks3` |
| `DBAILootConfig` | 78 | 40 | `0x26e89da5` | `Rifleman_Walker`, `Rifleman_Rosebud`, `Rifleman_Silverback`, `Rifleman_Flycatcher` |
| `DBHumanBodyPartDescriptor` | 70 | 106 | `0x07bda218` | `Torso`, `Head`, `Left_Leg`, `Right_Leg` |
| `DBHunt` | 66 | 40 to 58 (2 sizes) | `0x76bba011` | `Ground_UNI_P1_D1`, `Ground_UNI_P2_D1`, `Ground_UNI_P2_D4`, `Ground_UNI_P3_D4` |
| `DBNpcGeneralConfig` | 61 | 38 | `0x0eddf5f8` | `Fighter`, `Sniper_MK1`, `Rusher_MK1`, `Civilian_Unaligned` |
| `DBCircularSideBehaviour` | 54 | 283 to 323 (4 sizes) | `0x6e77432e` | `default`, `Wolf`, `Alternate_Wolf`, `LKP_Wolf` |
| `DBMechanicalAIHierarchyConfig` | 53 | 38 to 492 (5 sizes) | `0x5970b0c8` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DC_TGT_Ogre_base` |
| `DBNpcHealth` | 48 | 408 | `0xefb394e7` | `Miter_boss`, `Miter_Weak_Endoskeleton`, `Miter_FirstEncounter`, `Fighter` |
| `DBMechanicalElementAnimationConfig` | 47 | 179 to 267 (5 sizes) | `0x508fe856` | `DBVehiclePodConfig_Turret`, `DBVehiclePodConfig_ArmLeft`, `DBVehiclePodConfig_ArmRight`, `DBATC_Ogre_Arm_Left` |
| `DBAIActivityGameplayTagConfig` | 45 | 27 to 37 (2 sizes) | `0x6cc17d46` | `ScriptedHostage`, `Y1E3MM01_Sphynx`, `Officer_PVEE`, `MiTer` |
| `DBSpawnPerfParams` | 45 | 98 | `0x2ab28c78` | `LargeDrone`, `GroundVHC`, `AirVHC`, `IngredientClose` |
| `DBAICheatConfig` | 44 | 162 | `0x07becb9f` | `Walker`, `Children`, `Miter_Omniscience`, `LE2_Low_Stim` |
| `DBHumanHealth` | 44 | 266 | `0xc0a3544e` | `default`, `ShootingRange`, `Teammates`, `Heavy` |
| `DBSimpleFightingBehaviour` | 43 | 259 to 268 (4 sizes) | `0x131086dd` | `default`, `Wolf`, `LKP_Wolf`, `AgressiveLKP_Wolf` |
| `DBArmorType` | 42 | 39 to 48 (2 sizes) | `0x2dbc89bb` | `Dragonfly_Shell`, `VeryHigh`, `None`, `VeryLow` |
| `DBHealth` | 41 | 127 | `0x63d5f0a8` | `Wasp_Walker`, `TGT_DroidConfig_AirWasp_MainCharacter_PvP`, `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base` |
| `DBBodyPartVisual` | 39 | 70 to 403 (7 sizes) | `0x0a1f6102` | `MiterUpperBody_CryeG3`, `MiterUpperBody_ArmyJacket`, `MiterUpperBody_ArmoredShirt`, `MiterUpperBody_Sweater` |
| `DBMechanicalAISignAndFeedbackConfig` | 39 | 17 to 97 (8 sizes) | `0x451b51d6` | `DBVehiclePodConfig_ArmLeft`, `DBVehiclePodConfig_Turret`, `DBVehiclePodConfig_ArmRight`, `DBATC_Ogre_Arm_Left` |
| `DBSpawnDescList` | 39 | 42 to 1142 (19 sizes) | `0xcde1265d` | `MIL-Air-Helicopters_VHC`, `ALL-Ground-All_VHC`, `CIV-Marine-All_VHC`, `MIL-Marine-All_VHC` |
| `DBDroidFightingConfig` | 32 | 16 to 18501 (27 sizes) | `0xc9df4445` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `DC_TGT_Ogre_Camp`, `DC_TGT_Ogre_Training` |
| `DBHealthLogic` | 30 | 17 to 205 (8 sizes) | `0x242f7e17` | `ImmunityToDamages_BlackGates`, `ImmunityToDamages_BlackGates_Ogre`, `ImmunityToDamages_Walker_Drones`, `ImmunityToDamages_Miter` |
| `DBAutonomousElementWeaponUsageConfig` | 29 | 107 | `0xf7819490` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBDroidGeneralConfig` | 27 | 75 to 84 (2 sizes) | `0xf3c26325` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `DC_TGT_Dragonfly_MK2`, `DC_TGT_Dragonfly_MK3` |
| `DBDroidLocomotionConfig` | 27 | 376 | `0xcbcaab46` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `DC_TGT_Dragonfly_MK2_base`, `DC_TGT_Dragonfly_MK3_base` |
| `DBMechanicalStunConfig` | 27 | 57 | `0x82aadee2` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DC_TGT_Ogre_base` |
| `DBBodyPart` | 26 | 37 to 327 (10 sizes) | `0xab43bb41` | `Container_Turret`, `Container_Mortar`, `ContainerAI_Y1E2MM09_ClawWeakPoint`, `ContainerDrone_MediumAir` |
| `DBDefensiveStrafeBehaviour` | 26 | 267 to 297 (4 sizes) | `0x131086dd` | `Wolf`, `LKP_Wolf`, `AgressiveLKP_Wolf`, `Short_Wolf` |
| `DBDroidBodyPartType` | 25 | 222 to 231 (2 sizes) | `0xe9414294` | `SkyCherubim`, `CityCherubim`, `Goliath_Turret`, `Goliath_ArmLeft` |
| `DBStaticFightingBehaviour` | 24 | 259 to 286 (4 sizes) | `0x5c0ae1b2` | `NormalStance_Pause_1s`, `NormalStance_Pause_2s`, `NormalStance_Pause_5s`, `DF_Pause_5s_Camp` |
| `DBDroidAlertStateSignAndFeedback` | 23 | 625 | `0xb62020b5` | `DragonFly_Eye`, `OgreLIDAR`, `Wasp_EYE`, `SkyCherubin` |
| `DBHumanBodyPartType` | 23 | 224 to 345 (3 sizes) | `0x20201b31` | `Head`, `Torso`, `Left_Leg`, `Left_Arm` |
| `DBCoverSearch` | 22 | 73 | `0xa3851e73` | `Emergency`, `Offensive`, `Defensive`, `Progress` |
| `DBMechanicalWeaponUsageConfig` | 22 | 107 | `0x7ccf85be` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `DC_TGT_Dragonfly_MK2_base`, `DC_TGT_Dragonfly_MK3_base` |
| `DBModularBehaviourAbilityConfig` | 22 | 16 to 109 (7 sizes) | `0xcd7c530f` | `Y1E2MM09_ClawWeakPoint_AnimationPattern_1`, `Y1E2MM09_ClawWeakPoint_AnimationPattern_2`, `Y1E2MM09_ClawWeakPoint_AnimationPattern_3`, `Y1E2MM09_ClawWeakPoint_AnimationPattern_4` |
| `DBAgressiveStrafeBehaviour` | 19 | 283 to 323 (3 sizes) | `0x6e77432e` | `Goliath`, `DF_Medium_Training`, `DF_Long_camp`, `DF_Long` |
| `DBHumanBodyPartContainer` | 19 | 47 to 167 (7 sizes) | `0x56b2390c` | `Default`, `Civilian`, `Walker`, `RocketLauncher` |
| `DBAutonomousElementDeathConfig` | 18 | 69 | `0x45d799bc` | `RA01_Droid_WaspKamikaze_Config_Movement_Suicide`, `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret` |
| `DBAutonomousElementGeneralConfig` | 18 | 59 to 68 (2 sizes) | `0x98af5af9` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBAIAssaultConfig` | 17 | 63 | `0xff09c412` | `Rifleman`, `Miter`, `Default`, `Rusher` |
| `DBAutonomousElementSoundDetectionConfig` | 17 | 303 | `0x4c04ba82` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBAICoverConfig` | 16 | 134 | `0x97b59592` | `Cover_Walker`, `Cover_Wolves_Black_Gate`, `Default`, `Sniper` |
| `DBAutonomousElementHealth` | 16 | 134 | `0xa10757c9` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBAutonomousElementTargetConfig` | 16 | 146 | `0xcdf7c9c5` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBDroidUIConfig` | 16 | 82 | `0xc32611fe` | `OgreWild`, `DragonFlyWild`, `Goliath`, `Wasp` |
| `DBAITargetConfig` | 15 | 101 | `0x1476f64d` | `Miter`, `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Default` |
| `DBAirPatrolSettings` | 15 | 36 | `0x7c875e62` | `MAIN`, `Falcon_RAID`, `Taipan_RAID`, `Raptor` |
| `DBAutonomousElementDetectorConfig` | 15 | 439 | `0xeca6349e` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBAutonomousElementSignalConfig` | 15 | 29 | `0xbef3e1ab` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBAutonomousElementSoundConfig` | 15 | 31 | `0x0ecf8cd7` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBAutonomousElementVisualDetectionConfig` | 15 | 525 | `0xc0097dc1` | `DBATC_Ogre_Arm_Left`, `DBATC_Ogre_Arm_Right`, `DBATC_Ogre_DSTurret`, `DBATC_Goliath_Turret` |
| `DBDroidDeathConfig` | 15 | 206 to 398 (3 sizes) | `0x9b4ad6f9` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Wasp_Default`, `DC_TGT_Goliath` |
| `DBCoverActionLoop` | 14 | 115 | `0x9e35477b` | `default`, `Defend`, `Approach`, `PostFight` |
| `DBDroidVisualDetectionConfig` | 14 | 525 | `0xf6c8a4cb` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Wasp_Default`, `DC_TGT_Goliath` |
| `DBModularEntityHealth` | 14 | 143 | `0xd680fdfa` | `RA01_Boss_TankAnalyser_Config_Modular`, `RA01_Boss_ControlRoom_Config_Modular`, `RA01_Boss_Wyvern_Config_Modular`, `RA01_Boss_KingCom_Config_Modular` |
| `DBSoldierDetectorConfig` | 14 | 507 | `0x565e1210` | `RAID`, `Vantage_RAID`, `Default`, `Vantage` |
| `DBArmorPartShapeEffect` | 13 | 18 to 28 (2 sizes) | `0xf4ccd0fc` | `default`, `enableEye`, `Goliath_Enable_WKPT`, `Goliath_Enable_WKPT_front` |
| `DBCampConfigTemplate` | 13 | 227 to 318 (4 sizes) | `0xacfe4161` | `WarfareNoDialogues`, `GoliathArena_Swamp`, `GoliathArena_Sand`, `GoliathArena_Snow` |
| `DBChargeBehaviour` | 13 | 259 to 268 (2 sizes) | `0xf3a25740` | `Ogre`, `Wolf`, `Goliath`, `DF` |
| `DBAdversarialSpawnCamera` | 12 | 34 | `0x04a29f3a` | `RND_Center_001`, `RND_Center_002`, `Bunker_001`, `Bunker_002` |
| `DBDroidSignalConfig` | 12 | 17 | `0xb89bc9fb` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `NoSignal`, `DC_TGT_Goliath` |
| `DBEntryBulkAiSound` | 12 | 367 | `0xafdebefb` | `Chickens`, `Cattle`, `Sheep`, `Llama` |
| `DBTerrainDisplacementCapsule` | 11 | 96 to 366 (5 sizes) | `0x6c6229ef` | `Mud_Extrude`, `Mud_Dig`, `ActiveWeapon`, `Snow_Extrude_old` |
| `DBAIFollowConfig` | 9 | 23 to 44 (2 sizes) | `0xbd3987fb` | `Autofollow`, `Autofollow_activable`, `NoDisableActivities`, `SC_TGT_Grenadier` |
| `DBDroidDetectorConfig` | 9 | 349 | `0x63a8c758` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Wasp_Default`, `DC_TGT_Goliath` |
| `DBDroidFollowConfig` | 9 | 314 | `0x62d09023` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Wasp`, `DC_TGT_Goliath` |
| `DBDroidSoundDetectionConfig` | 9 | 303 | `0x8e974628` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Wasp_Default`, `DC_TGT_Goliath` |
| `DBPredatorSettings` | 9 | 36 to 104 (2 sizes) | `0x8557c78f` | `Conquest_Hard`, `Conquest_Medium`, `Conquest_Easy`, `Predator` |
| `DBSoldierInvestigateSearch` | 9 | 220 | `0x3509a586` | `Default`, `Hunter`, `OnlyFight`, `Walker` |
| `DBSoldierSoundThreatConfig` | 9 | 27 | `0xc7df969b` | `Fighter`, `Sniper`, `Rusher`, `DroneCarrier` |
| `DBSoldierVisualDetectionConfig` | 9 | 525 | `0xc35ebf27` | `Fighter`, `SC_TGT_Grenadier`, `Vantage`, `Teammate` |
| `DBAISpecialAbilityConfig` | 8 | 15 to 547 (7 sizes) | `0x88d6e5d7` | `Miter`, `Miter_Weak`, `NoAbility`, `Finka` |
| `DBDroidLookAtConfig` | 8 | 17 | `0xdaa5c471` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `DC_TGT_Wasp`, `DC_TGT_Goliath` |
| `DBDroidSoundThreatConfig` | 8 | 27 | `0x11c72ca5` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Wasp_Default`, `DC_TGT_Goliath` |
| `DBDroneAirMedium` | 8 | 222 | `0xe9414294` | `Rotors`, `Shell`, `Arms`, `Shell_Succubus` |
| `DBSoldierLocomotionConfig` | 8 | 41 | `0x05d37de6` | `Default`, `Rusher`, `SC_TGT_Grenadier`, `Vantage` |
| `DBAISoundDetection` | 7 | 305 | `0xf7d7a528` | `MovingSounds_Goliath`, `MovingSound_Ogre`, `MovingSound_Dragonfly`, `MovingSounds_Generic` |
| `DBAdversarialOutroCamera` | 7 | 43 to 52 (2 sizes) | `0x04a29f3a` | `RND_Center`, `TestZoo`, `Bunker`, `Harbor` |
| `DBDroidCollisionConfig` | 7 | 31 | `0x794418a0` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `Default`, `DC_TGT_Goliath` |
| `DBDroidDriveConfig` | 7 | 17 | `0xc61288cd` | `DC_TGT_Ogre_base`, `DC_TGT_Dragonfly_base`, `NoDrive`, `DC_TGT_Goliath` |
| `DBNPCHostageConfig` | 7 | 27 to 37 (2 sizes) | `0xed8fdf10` | `ScriptedHostage`, `NoHostage`, `Default`, `SC_TGT_Grenadier` |
| `DBSoldierSpawnedItemUsageConfig` | 7 | 118 | `0x9b369e3d` | `NoItem`, `SC_TGT_Grenadier`, `DroneCarrier_MK1`, `DroneCarrier_MK2` |
| `DBAIMarkConfig` | 6 | 25 | `0x77c0e5d4` | `Default`, `SC_TGT_Grenadier`, `None`, `NoSyncShot` |
| `DBAIToxicGasConfig` | 6 | 26 | `0x5e26b2fc` | `Civilians_WithMasks`, `Teammate_R6_AlwaysMask`, `Teammate`, `Fighters` |
| `DBBushSearch` | 6 | 55 | `0x7ef7500a` | `Emergency`, `Defensive`, `Progress`, `Offensive` |
| `DBDroidAlertState` | 6 | 625 | `0xb62020b5` | `Eye`, `IdleToFight_Canon_FX`, `IdleToFight_Core_FX`, `Goliath_IdleToFight_Core_FX` |
| `DBNpcPerceptionConfig` | 6 | 40 | `0x98879fe3` | `Default`, `Civilian`, `SC_TGT_Grenadier`, `ReactionPack` |
| `DBNpcVehicleUsageConfig` | 6 | 87 to 96 (2 sizes) | `0x3ad6522b` | `Default`, `SC_TGT_Grenadier`, `FleeingMan`, `FleeingMan_Helicopter` |
| `DBSoldierAimingModifierConfig` | 6 | 29 | `0xa88736f5` | `Rifleman`, `SC_TGT_Grenadier`, `Vantage`, `Rusher` |
| `DBSoldierGrenadeConfig` | 6 | 41 | `0x5bcb9cce` | `Default`, `SC_TGT_Grenadier`, `NoGrenade`, `Thatcher` |
| `DBAIStaticDefendConfig` | 5 | 18 | `0x0e0f8d37` | `YES_STAY`, `NoStaticDefend`, `SC_TGT_Grenadier`, `YES` |
| `DBAIUsabilityConfig` | 5 | 17 to 172 (4 sizes) | `0xf744a279` | `default`, `Thatcher`, `Ash`, `Vasily` |
| `DBAutonomousTurretConfig` | 5 | 183 | `0xc42137e3` | `Arm_Left_Turret`, `Arm_Right_Turret`, `Base_Turret`, `RAID` |
| `DBCampCustomSpawnDistances` | 5 | 73 | `0x5e764123` | `Village_SB_District`, `Ingredient_Prison_Gen`, `Systemic_BreachComCenter`, `Ingredient_Prison_Spe` |
| `DBModularEntityConfig` | 5 | 93 | `0x0bbc12d1` | `Default`, `Y1E2MM09_ClawWeakPoint_Template`, `Y1E2MM09_ClawWeakPoint_First`, `Y1E2MM09_ClawWeakPoint_Second` |
| `DBNPCSignalConfig` | 5 | 21 | `0xbbee5dcc` | `Default`, `NoDifference`, `SC_TGT_Grenadier`, `Teammate` |
| `DBSoldierRetrenchConfig` | 5 | 19 | `0xef12dae5` | `MediumRange`, `SC_TGT_Grenadier`, `LongRange`, `ShortRange` |
| `DBSoldierSoundDetectionConfig` | 5 | 303 | `0xad245000` | `Default`, `SC_TGT_Grenadier`, `Teammate`, `Miter` |
| `DBStatic` | 5 | 259 to 263 (2 sizes) | `0x5c0ae1b2` | `Wasp_CloseRange_DroneCarrier_Target_Old`, `Wasp_CloseRange_DroneCarrier_Visual_Old`, `Wasp_DroneCarrier_Visual`, `Wasp_DroneCarrier_NoVisual` |
| `DBAIBushConfig` | 4 | 128 | `0x8aa5b727` | `Default`, `SC_TGT_Grenadier`, `Teammate`, `NoBush` |
| `DBAIConfidenceConfig` | 4 | 61 | `0xcf946f3d` | `Default`, `SC_TGT_Grenadier`, `Vantage`, `NoConfidence` |
| `DBAIOpticalCamoConfig` | 4 | 283 to 430 (3 sizes) | `0x5a26cdfb` | `NoOpticalCamo`, `DefaultBodarkCamo`, `DefaultBodarkCamo_OnByDefault`, `TeamMatesCamo` |
| `DBAIWeaponManagementConfig` | 4 | 251 to 1081 (3 sizes) | `0x12760668` | `Default`, `SC_TGT_Grenadier`, `Teammate`, `Teammate_Ash` |
| `DBBodyPartType` | 4 | 215 | `0xf0f0c681` | `Turret`, `Mortar`, `Turret_Eye`, `Y1E2MM09_ClawWeakPoint` |
| `DBDroidSoundLeaderFollowerConfig` | 4 | 137 | `0x8b70b4c7` | `Goliath`, `Ogre`, `Dragonfly`, `Cores` |
| `DBDroneHandling` | 4 | 1284 | `0x0f9b734d` | `default`, `PVP`, `medic`, `Pathfinder` |
| `DBModularEntityBehaviorConfig` | 4 | 1892 to 2760 (4 sizes) | `0xabfdd32a` | `Y1E2MM09_ClawWeakPoint_Template`, `Y1E2MM09_ClawWeakPoint_First`, `Y1E2MM09_ClawWeakPoint_Second`, `Y1E2MM09_ClawWeakPoint_Third` |
| `DBNpcEscapeConfig` | 4 | 29 | `0x9953a17f` | `NoEscape`, `SC_TGT_Grenadier`, `Default`, `Delayed` |
| `DBSoldierRevivalConfig` | 4 | 19 | `0x4a7250c8` | `NoRevive`, `SC_TGT_Grenadier`, `Default`, `Teammate` |
| `DBSpawnModularEntityDescriptor` | 4 | 271 | `0xa21e2ce4` | `Y1E2MM09_ClawWeakPoint_Template`, `Y1E2MM09_ClawWeakPoint_First`, `Y1E2MM09_ClawWeakPoint_Second`, `Y1E2MM09_ClawWeakPoint_Third` |
| `DBAIChaseConfig` | 3 | 54 | `0xa5653bbf` | `CanChase_Runner`, `NoChase`, `CanChase_Long_Range` |
| `DBAIRadioCallConfig` | 3 | 20 to 224 (3 sizes) | `0xf0a7eb4e` | `NoCall`, `CallPMC`, `CallBodark` |
| `DBAIReactionConfig` | 3 | 30 | `0x73673c19` | `SC_TGT_Grenadier`, `NoReactionPack`, `FactionWarfare` |
| `DBAITeamsConfig` | 3 | 14 | `0xba69ebaa` | `NoSoloTeam`, `SC_TGT_Grenadier`, `SoloTeam` |
| `DBAIVantageConfig` | 3 | 14 | `0x1f544cc2` | `NoVantage`, `SC_TGT_Grenadier`, `Default` |
| `DBBodyPartStunEffect` | 3 | 17 | `0x68a38d05` | `Ogre_Eye`, `Goliath_Weakpoints`, `Goliath_Weakpoints_Small` |
| `DBDroidSignAndFeedback` | 3 | 15 to 19 (2 sizes) | `0xe2323101` | `AlertSpread_VoiceCall`, `AlertSpread_RadioCall`, `Investigation` |
| `DBDroneAirWasp` | 3 | 222 | `0xe9414294` | `Hull`, `Rotors`, `Folded` |
| `DBDroneConfiguration` | 3 | 1335 | `0x45a13d06` | `default`, `medicDrone`, `Pathfinder` |
| `DBNpcFidgetConfig` | 3 | 30 to 62 (2 sizes) | `0xc6a02506` | `Default`, `SC_TGT_Grenadier`, `NoFidget` |
| `DBPatrolConfig` | 3 | 111 | `0xff90e7e7` | `Test_DroneHumains`, `Test`, `Test_Goliath` |
| `DBSoldierApproachConfig` | 3 | 14 | `0x9774b2fc` | `Default`, `SC_TGT_Grenadier`, `NoApproach` |
| `DBSoldierSoundThreatSystemModifierSettings` | 3 | 165 | `0xecaefb33` | `default`, `Rusher`, `Sniper` |
| `DBSoldierTurretConfig` | 3 | 18 | `0x27bc138a` | `Default`, `SC_TGT_Grenadier`, `NoTurret` |
| `DBWildExclusionSearchOptions` | 3 | 117 to 146 (3 sizes) | `0x6fecb3a0` | `Air_Default`, `Air_MAIN`, `Air_RAID` |
| `DBAdversarialIntroCamera` | 2 | 34 | `0x04a29f3a` | `TestZoo_001`, `TestZoo_002` |
| `DBAimingDists` | 2 | 213 | `0x0769a401` | `NPC`, `Miter` |
| `DBAirScheduledVehicleSettings` | 2 | 69 | `0x49b8db74` | `FlyingLootbox_ZOO`, `Predator_ZOO` |
| `DBAutonomousElementFightingConfig` | 2 | 16 | `0x46d1b783` | `Default`, `RA01_Droid_WaspKamikaze_Config_Movement` |
| `DBAutonomousElementInertConfig` | 2 | 63 | `0x4d5e817d` | `Default`, `Y1E2MM09_ClawWeakPoint` |
| `DBAutonomousElementLocomotionConfig` | 2 | 376 | `0x72def726` | `RA01_Droid_WaspKamikaze_Config_Movement`, `Default` |
| `DBAutonomousMortarConfig` | 2 | 183 | `0xc42137e3` | `RAID` |
| `DBBodyPartExplosionEffect` | 2 | 47 | `0xc035b697` | `RocketBagExplosion`, `Goliath_Weakpoints` |
| `DBCivilianFleeConfig` | 2 | 20 | `0x2316dc73` | `NoFlee`, `flee` |
| `DBCustomGameplayPreset` | 2 | 123 | `0x1cce7a1b` | `Regular`, `Immersive` |
| `DBDifficultyLevelBonusSettings` | 2 | 117 | `0xe2692763` | `Skreds`, `XP` |
| `DBDroidLocomotionFX` | 2 | 815 to 1087 (2 sizes) | `0x92323504` | `Goliath` |
| `DBDroneAirSmall` | 2 | 222 | `0xe9414294` | `Rotors`, `Hull` |
| `DBFactionPass` | 2 | 86 | `0x4a57eddf` | `Season1_Act1`, `Season1_Act2` |
| `DBFactionPassEpisode` | 2 | 208 | `0x9bdcf534` | `Episode1_Act1`, `Episode1_Act2` |
| `DBMechanicalCollisionConfig` | 2 | 27 | `0xad9b6f46` | `RA01_Droid_WaspKamikaze_Config_Modular`, `Y1E2MM09_ClawWeakPoint` |
| `DBModularEntityHierarchyConfig` | 2 | 47 to 151 (2 sizes) | `0xa3f43cf7` | `Default`, `Y1E2MM09_ClawWeakPoint` |
| `DBModularEntitySoundThreatConfig` | 2 | 27 | `0xf79f1bab` | `RA01_Droid_WaspKamikaze_Config_Modular`, `Default` |
| `DBNpcBaseJumpSettings` | 2 | 53 | `0x470b7aa9` | `Skydiving`, `Parachuting` |
| `DBNpcPatchingConfig` | 2 | 16 | `0x90068823` | `Default`, `NOPATCHING` |
| `DBWildExclusion` | 2 | 134 | `0x6fecb3a0` | `RoadEvents_RAIDOnly`, `RoadEvents_MAINOnly` |
| `DBAIGeneralConfig` | 1 | 29 | `0x7b15d0d4` | `DBPuppetConfig_DIAL` |
| `DBAdversarialSpawnCameraConfig` | 1 | 206 | `0xc5fac712` | `default` |
| `DBAirPatrolSettingsFalcon` | 1 | 36 | `0x7c875e62` |  |
| `DBAirPatrolSettingsRaptor` | 1 | 36 | `0x7c875e62` |  |
| `DBAirPatrolSettingsSparrow` | 1 | 36 | `0x7c875e62` |  |
| `DBAirPatrolSettingsTaipan` | 1 | 36 | `0x7c875e62` |  |
| `DBAirPatrolSettingsZOO` | 1 | 36 | `0x7c875e62` |  |
| `DBAirdropConfig` | 1 | 547 | `0xc5337dac` | `debug` |
| `DBAutonomousElementAnimationConfig` | 1 | 179 | `0x508fe856` | `Default` |
| `DBAutonomousElementCheatConfig` | 1 | 162 | `0x07becb9f` | `Default` |
| `DBAutonomousElementHealthConfig` | 1 | 134 | `0xa10757c9` | `Default` |
| `DBAutonomousElementLootConfig` | 1 | 40 | `0x26e89da5` | `Default` |
| `DBAutonomousElementSignAndFeedbackConfig` | 1 | 17 | `0x451b51d6` | `Default` |
| `DBAutonomousElementStunConfig` | 1 | 57 | `0x82aadee2` | `Default` |
| `DBAutonomousFiringElementConfig` | 1 | 183 | `0xc42137e3` | `Default` |
| `DBAutonomousMovingElementConfig` | 1 | 193 | `0x13a23785` | `Default` |
| `DBAutonomousSearchLightConfig` | 1 | 183 | `0xc42137e3` |  |
| `DBBodyPartEffect` | 1 | 13 | `0xb82c7b04` | `KillOwner` |
| `DBCampAlarmSettings` | 1 | 19 | `0xf6039b79` | `default` |
| `DBCampBudgetConfig` | 1 | 208 | `0x730f8c5a` | `default` |
| `DBCivilianAffinityConfig` | 1 | 18 | `0x93ed1a46` | `default` |
| `DBCivilianDetectorConfig` | 1 | 145 | `0xcb1aae50` | `Civilian` |
| `DBCivilianSoundDetectionConfig` | 1 | 207 | `0x96f65bb0` | `Civilian` |
| `DBCivilianVisualDetectionConfig` | 1 | 297 | `0x0804dea0` | `Civilian` |
| `DBDelegateSpawnConfig` | 1 | 23 | `0x1b3adbc6` |  |
| `DBDroidMoverSpeedToUVSignAndFeedback` | 1 | 40 | `0x384d51dc` | `0X1B6C5233277` |
| `DBDroidSoundConfig` | 1 | 74 | `0xd052c392` | `NoSounds` |
| `DBDroidSoundThreatSystemModifierSettings` | 1 | 165 | `0x84f58be6` | `default` |
| `DBDroneAbilityConfig` | 1 | 121 | `0xdbb7d5d8` | `Gas` |
| `DBDroneAbilityConfigContainer` | 1 | 71 | `0x395a6823` |  |
| `DBDroneTrackerParams` | 1 | 29 | `0xf2ebfb63` |  |
| `DBFactionFightNotifierConfig` | 1 | 1759 | `0xeacc3fce` | `default` |
| `DBFactionFightNotifierManagerSettings` | 1 | 17 | `0xd534e956` | `default` |
| `DBFactionWarfareSettings` | 1 | 49 | `0xf7e268b6` |  |
| `DBFactionsSettings` | 1 | 335 | `0x5a59c2a3` | `default` |
| `DBFeedbackAlertStateSettings` | 1 | 453 | `0xe39e2263` | `default` |
| `DBFightReasonConfig` | 1 | 1101 | `0x75e1cfe6` |  |
| `DBFollowTargetFightingBehaviour` | 1 | 260 | `0xb086d114` | `Raid_WaspKamikaze_GoToTarget` |
| `DBHumanDebug` | 1 | 13 | `0xce5a28af` |  |
| `DBHumanObstacle` | 1 | 137 | `0x0dcb944e` | `0XB464B30144` |
| `DBModularBehaviorEntityGeneralConfig` | 1 | 33 | `0xa30dd400` | `Y1E2MM09_ClawWeakPoint` |
| `DBModularEntityBehaviourConfig` | 1 | 29 | `0xabfdd32a` | `Default` |
| `DBModularEntityCollisionConfig` | 1 | 27 | `0xad9b6f46` | `Default` |
| `DBModularEntityGeneralConfig` | 1 | 33 | `0xa30dd400` | `Default` |
| `DBModularEntityGroupConfig` | 1 | 21 | `0x094db58a` | `Default` |
| `DBModularEntityHealthConfig` | 1 | 143 | `0xd680fdfa` | `Default` |
| `DBModularEntitySignAndFeedbackConfig` | 1 | 17 | `0x451b51d6` | `Default` |
| `DBModularSoundThreatConfig` | 1 | 27 | `0xf79f1bab` | `Y1E2MM09_ClawWeakPoint` |
| `DBNPCStateNotifierConfig` | 1 | 628 | `0x93cb1b3b` | `default` |
| `DBNPCStateNotifierManagerSettings` | 1 | 30 | `0x9de361a8` | `Singleton` |
| `DBNPCTagSettings` | 1 | 67 | `0x078dfbbb` |  |
| `DBNpcCivilianSettings` | 1 | 110 | `0x152da150` | `default` |
| `DBNpcDebug` | 1 | 1386 | `0xb1e60693` |  |
| `DBNpcDefaultSettings` | 1 | 39816 | `0x5f09e026` | `default` |
| `DBNpcLobotomy` | 1 | 26 | `0xba4f5c07` | `default` |
| `DBNpcLocomotionConfig` | 1 | 39 | `0xe4882db1` | `Civilian` |
| `DBPatrolConfigSettings` | 1 | 73 | `0x8423a7bd` |  |
| `DBPlayerAlertNotifierConfig` | 1 | 483 | `0x8a04779a` | `default` |
| `DBPlayerCover` | 1 | 755 | `0xe95a3aef` |  |
| `DBPredatorDetectionExclusionZones` | 1 | 105 | `0x6fecb3a0` |  |
| `DBPredatorFlareGunParams` | 1 | 128 | `0x31794cac` |  |
| `DBPredatorRegionSettings` | 1 | 36 | `0x7c875e62` | `ZOO` |
| `DBRadioCallSettings` | 1 | 795 | `0xd543bbd0` |  |
| `DBSpawnAutonomousElementDescriptor` | 1 | 304 | `0xa811e479` | `Y1E2MM09_ClawWeakPoint` |
| `DBSpawnDescriptorList` | 1 | 92 | `0xcde1265d` | `BreachDoors` |
| `DBTerrainAnalyzer` | 1 | 248 | `0x3030d4c0` | `NPC` |
| `DBWildEventsExclusionZones` | 1 | 150 | `0x6fecb3a0` |  |
| `DBWildPatrolConfigSettings` | 1 | 466 | `0xe2807e4e` |  |
| `DBWildPatrolsExclusionZones` | 1 | 150 | `0x6fecb3a0` |  |

---

Generated from the base container of a 2026-09 GRB install by [`../tools/db_inspect.py`](../tools/db_inspect.py). A patch forge may add types this list does not have.
