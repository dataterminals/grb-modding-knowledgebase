# 14 — AI and NPC behaviour: the gameplay DB layer

> **Status:** First map of GRB's gameplay-logic layer — 2026-09-16. Everything in §1–§4 was
> **read out of the live install on this machine** with [`../tools/db_inspect.py`](../tools/db_inspect.py)
> (written for this pass), and the §5 worked example is a byte-level diff of an installed mod
> against the vanilla records it replaces. Field *semantics* are inferred and flagged as such.
> Provenance: [`../meta/research-log.md`](../meta/research-log.md) (2026-09-16 entry).
>
> ⚠️ **Corrected later on 2026-09-16.** The first walk of the container stopped at its first
> unnamed record, so the container totals and the base/patch comparison were counts over a
> prefix. They are corrected below (61,426 records, not 50,098). **Every per-type count in this
> document held up in the full walk.** §9's bytes 38–49 are corrected too. See the research-log
> entry *"The container walker was one byte off"*.

Every other doc in this repo is about *art* — meshes, textures, cloth, item definitions. This
one is about the other half of the game: **how enemies see, hear, think, call for help, and
die.** That layer exists, it is large, it is well-named, and it is barely touched by the
modding scene.

---

## 1. Where gameplay logic actually lives

Not in the item forges. GRB keeps its gameplay database in **one forge entry**:

```
DataPC.forge            / <N>_-_DBContainerEntry_0X104634F921.data     ← base
DataPC_patch_01.forge   / <N>_-_DBContainerEntry_0X104634F921.data     ← patch (override here)
```

That single 13.9 MB entry decompresses to ~57 MB and holds **61,426 named records**.

> **Verified (2026-09-16).** `python tools/db_inspect.py <DBContainerEntry…data>` on the base
> container of this install reports: 61,426 records — 23,914 `DB*`-named, 37,512 other —
> spanning **1,012 distinct DB types** over 830 type ids, and the walk ends exactly on the last
> byte of the block, agreeing with the container's own metadata index. This install's patch copy
> holds 61,446.

The records are simply this container's **resources**, framed like any other `.data`'s. The layer
stayed invisible to earlier passes of this knowledgebase because, until 2026-09-16,
[`data_inspect.py`](../tools/data_inspect.py) could not read past the first resource of *any*
container — not because the records are hidden or nested.

The 37,512 non-`DB*` records are the same database: spawn descriptors (`TGT_Heavy_Marks1`),
reinforcement waves (`WaveSetting_Hunt_UNI_BA_D01`, 198 of them), entity spawn descriptors
(`…_SpawnEntityDescriptor`, 225), quest and dialogue plumbing, and a long tail of effects
(`GFX_*`, `FX_*`), store and UI records.

### The record format

> **Verified — from ATK's source and from bytes.** The decompressed *files* block is a flat stream of:
>
> ```
> [uint32 typeId][int32 payloadLen][int32 nameLen][name bytes][FileHeader][payload]
> ```
>
> The FileHeader is counted by **neither** length. It is one `0x00` byte for almost every record;
> when that byte is `0x01` an object-block-allocator table follows and the header is `8 + 12N`
> bytes (17 `Animation` records here). Some records have no name at all (`nameLen == 0`). The
> payload starts with the record's own 64-bit ClassID. Record 0 is a `DBContainerEntry` resource;
> the rest are the database. An ATK-unpacked record file is FileHeader + payload — which is why the
> files are one byte longer than the payload.

`typeId` is the **schema**; the name is the **instance**. All 48 `DBNpcHealth_*` records carry
typeId `0xefb394e7` and are each exactly 408 B. 76 type ids are shared by more than one name
prefix — `DBSimpleFightingBehaviour` and `DBDefensiveStrafeBehaviour` are both `0x131086dd`,
`DBCircularSideBehaviour` and `DBAgressiveStrafeBehaviour` are both `0x6e77432e` — so **trust
the id for layout and the name for meaning.**

---

## 2. ATK cannot decode these — and that is the central constraint

> **Verified.** ATK's `AnvilToolkit.dll` exposes 1,245 types. **Zero** of them are `DB*`
> classes; nothing named `RadioCall`, `SpawnNpc`, or similar exists either. 350 classes declare
> a `WriteXml()` (`BuildTable`, `EntityBuilder`, `Cloth`, `Material`, …) — **no DB record type
> is among them.**

So the editable-XML round-trip documented in [`../reference/buildtable-xml.md`](../reference/buildtable-xml.md)
**does not exist for gameplay records**. ATK can still unpack the container into individual
per-record files and repack it — that part works, and installed mods prove it — but the record
bodies are opaque blobs to it.

**Consequence:** AI modding in GRB is a **binary-patching** discipline, not a config-editing
one. That sounds worse than it is, because of the next section.

---

## 3. Why binary patching is tractable here: fixed sizes and the game's own "off" switches

> **Verified.** 777 of the 1,012 DB types have a **single fixed record size** across every
> instance. `DBNpcHealth` is always 408 B; `DBSoldierVisualDetectionConfig` always 525 B;
> `DBSoldierSoundDetectionConfig` always 303 B; `DBSoldierAimingModifierConfig` always 29 B.

Two records of a fixed-size type are therefore **field-aligned**: byte 84 means the same thing
in both. You get the schema without having a schema — diff two variants and the differing
offsets *are* the fields.

Better: Ubisoft shipped **null variants** of most AI configs — `_NoDetection`, `_NoCall`,
`_NoConfidence`, `_NoReactionPack`, `_Civilian_Invincible`. Diffing a live config against its
own null variant lights up the entire tunable surface at once.

`tools/db_inspect.py --diff` on the sound-detection pair does exactly that:

```
DBSoldierSoundDetectionConfig_Default  vs  DBSoldierSoundDetectionConfig_NoDetection  (303 B)
  125 differing bytes
    @24     1 -> 0      @77     50 -> 0     @167    25 -> 0      @263    10 -> 0
    @28     3 -> 0      @81    135 -> 0     @171    25 -> 0      @267    15 -> 0
    @32     8 -> 0      @85    150 -> 0     @175    25 -> 0      @283    25 -> 0
    @36    15 -> 0      @98..@126: 10 ×8    @199..@223: 100 ×7   @291   150 -> 0
  (49 differing float-plausible fields)
```

Every value is a clean human-scaled number, laid out in **runs of seven** — seven repetitions
of 10, of 25, of 100, of 1.

> **Inferred:** these are hearing radii in metres, banded across seven levels (alert states, or
> sound classes). The run-of-seven shape is verified; the meaning of the seven is not. The
> singletons (50 / 135 / 150 at @77–@85, and 10 / 15 / 25 / 50 / 150 / 75 / 25 at @263–@299)
> read like per-sound-type ranges — gunshot, suppressed shot, footstep, body fall.

A first experiment that needs no theory at all: halve every value in the run at @199–@223 and
listen for whether enemies react later.

---

## 4. What is actually in there — the AI subsystem

The full catalogue is in [`../reference/ai-db-records.md`](../reference/ai-db-records.md). The
shape of it:

| Cluster | Types | What it governs |
| --- | --- | --- |
| **Perception** | `DBSoldierVisualDetectionConfig` (9×525 B), `DBSoldierSoundDetectionConfig` (5×303 B), `DBNpcPerceptionConfig` (6×40 B), `DBAISoundDetection` (7×305 B), `DBSoldierDetectorConfig` | Sight cones and ranges, hearing radii, what an NPC is allowed to notice |
| **Reaction & escalation** | `DBAIRadioCallConfig`, `DBAIConfidenceConfig`, `DBAIReactionConfig`, `DBFeedbackAlertStateSettings`, `DBPlayerAlertNotifierConfig`, `DBNPCStateNotifierConfig` | Calling for backup, alert-state transitions, how bold a unit is |
| **Reinforcement** | `DBHunt` (66), `WaveSetting_Hunt_*` (198), `DBSpawnDescList` (39), `TGT_*_Marks*` spawn descriptors (54) | Who shows up, in what waves, at what tier |
| **Fighting** | `DBCustomFightingBehaviour` (149), `DBSimpleFightingBehaviour` (43), `DBStaticFightingBehaviour` (24), `DBAgressiveStrafeBehaviour` (19), `DBDefensiveStrafeBehaviour` (26), `DBCircularSideBehaviour` (54), `DBChargeBehaviour`, `DBFollowTargetFightingBehaviour` | Movement-under-fire patterns — flanking, strafing, charging |
| **Tactics** | `DBAIAssaultConfig` (17×63 B), `DBAICoverConfig` (16×134 B), `DBAIChaseConfig`, `DBAIVantageConfig`, `DBAIStaticDefendConfig`, `DBCoverSearch` (22×73 B), `DBSoldierInvestigateSearch`, `DBSoldierRetrenchConfig` | Assault vs. hold, cover selection, chasing, searching after losing you |
| **Gunplay** | `DBSoldierWeaponUsageConfig` (93), `DBSoldierAimingModifierConfig` (6×29 B), `DBSoldierGrenadeConfig`, `DBSoldierTurretConfig`, `DBAIWeaponManagementConfig` | Fire discipline, burst length, aim behaviour, grenade use |
| **Durability** | `DBNpcHealth` (48×408 B), `DBHumanHealth` (44), `DBHealthLogic` (30), `DBArmorType` (42), `DBBodyPartDescriptor` (155), `DBSoldierRevivalConfig` | Health pools, armour, hit zones, whether a downed NPC gets revived |
| **The cheat layer** | `DBAICheatConfig` (44×162 B) — instances include `_Walker`, `_Children`, **`_Miter_Omniscience`**, `_BlackGate` | Named, per-encounter. The engine has an explicit knob for AI knowing things it should not |
| **Squad / faction** | `DBAITeamsConfig`, `DBFactionFightNotifierConfig`, `DBFactionWarfareSettings`, `DBFactionsSettings`, `DBNPCSignalConfig` | Group coordination, who fights whom |
| **Drones & machines** | `DBDroidFightingConfig` (32), `DBDroidVisualDetectionConfig`, `DBDroidSoundDetectionConfig`, `DBDroidAlertState`, `DBDroneConfiguration`, `DBMechanicalAIHierarchyConfig` (53), `DBAutonomousElement*` (186 across 19 types) | The entire drone/turret/Behemoth AI, structured in parallel to the human one |
| **Patrols & ambience** | `DBPatrolConfig`, `DBPatrolConfigSettings`, `DBAirPatrolSettings` (15, incl. per-drone-type), `DBWildPatrolConfigSettings`, `DBTrafficPatrolPath` | Where units walk when they have not seen you |

Most types are **named per faction and per tier** — `_Wolves`, `_Bodark`, `_Miter`, `_Fighter`,
`_Vantage` (snipers), `_Rusher`, `_Heavy`, `_MK1`/`_MK2`/`_MK3`. That naming is the whole point:
it means you can make a change that hits *one faction at one tier* rather than the whole game.

### Two findings that save wasted effort

> **Verified — NPC tier is not in `DBNpcHealth`.** `DBNpcHealth_Rifleman_MK1` and
> `DBNpcHealth_Rifleman_MK3` differ by **2 bytes**, both inside the record's own ClassID. The
> MK1/MK2/MK3 records are otherwise identical. Tier scaling is resolved elsewhere — the
> `TGT_*_Marks1/2/3` spawn descriptors are the obvious candidate, and Fear the Radio edits
> exactly those, but that is unverified. **Do not go hunting for a health multiplier in
> `DBNpcHealth`.**

> **Verified — some "different" configs are byte-identical.** `DBSoldierVisualDetectionConfig_Wolves`
> and `_Vantage` differ by **5 bytes**, all ClassID. The Wolves and the snipers genuinely share
> one sight config. Where two named variants differ for real (`_Fighter` vs `_Wolves`: 33 bytes)
> the differences are **64-bit handles, not floats** — that record is a bundle of references to
> sub-configs, so you retarget it rather than tune it. `DBSoldierSoundDetectionConfig` is the
> opposite: raw numbers. **Check which kind you have before planning an edit.**

---

## 5. Worked example — what "Fear the Radio" actually does

The installed `FearTheRadio_DBContainer` mod ships five records into
`DataPC_patch_01.forge / DBContainerEntry_0X104634F921.data`:

```
1_-_DBAIRadioCallConfig_CallPMC.DBAIRadioCallConfig        225 B
1_-_TGT_Heavy_Marks1.GR_SpawnNpcDescriptor                 272 B
1_-_TGT_Heavy_Marks2.GR_SpawnNpcDescriptor                 272 B
1_-_TGT_Heavy_Marks3.GR_SpawnNpcDescriptor                 272 B
1_-_TGT_Rusher_Marks1.GR_SpawnNpcDescriptor                272 B
```

`DBAIRadioCallConfig` is one of the 235 **variable-size** types. Vanilla ships three:

| Record | Size | Content |
| --- | ---: | --- |
| `DBAIRadioCallConfig_NoCall` | 20 B | empty — the "off" switch |
| `DBAIRadioCallConfig_CallPMC` | 54 B | **one** call entry |
| `DBAIRadioCallConfig_CallBodark` | 224 B | **six** call entries |

The mod's `CallPMC` is **225 B**. Strip the leading byte ATK writes and it is 224 B — and a
byte-for-byte compare against vanilla `CallBodark` differs in **31 of 224 bytes**.

> **Verified.** The mod is vanilla **`CallBodark`'s body transplanted onto `CallPMC`**: one
> differing byte keeps `CallPMC`'s own ClassID, and the other 30 are **six 5-byte runs — one
> 64-bit handle per wave, all six repointed.** Timings and wave sizes are Bodark's, unchanged.

Each wave entry is the `f8 00 00 00 00` marker, 4 bytes identical in every entry
(`34 c4 61 39`), an int32 count, two floats, two bytes (`01 00`), then a 64-bit handle at
marker + 23. *(Inferred 2026-09-16 from ATK's serializer, which writes an embedded object as a
file-local ID `0xF80000nn` followed by a class hash — a pattern checked byte by byte in build tables
and in §9: the "marker" is the top five bytes of each wave object's ID and `34 c4 61 39` its class
hash. The offsets are unchanged.)* **The handles resolve** — see *Resolving a handle*
below — so here is what each config actually summons:

| Wave | Floats | Count | vanilla `CallBodark` → | Fear the Radio `CallPMC` → |
| ---: | --- | ---: | --- | --- |
| 0 | 15, 45 | −1 | `WaveSetting_TGT_CallerBodark_Wave1` | `WaveSpawner_TGT_Y1E3MM08_Ambush_FatBoy` |
| 1 | 10, 55 | −1 | `WaveSetting_TGT_CallerBodark_Wave2` | `PvEE_WaveSpawner_Basic` |
| 2 | 10, 55 | 5 | `WaveSetting_TGT_CallerBodark_Wave3` | `WaveSetting_Hunt_TGT_GQ250_AmbushMaoriFort` |
| 3 | 10, 55 | 6 | `WaveSetting_TGT_CallerBodark_Wave4` | `WaveSetting_Hunt_TGT_OnFootBackup_MQ190_3HNTR-RFLM` |
| 4 | 10, 55 | 6 | `WaveSetting_TGT_CallerBodark_Wave5` | `PvEE_WaveSpawner_Warfare_Wolf` |
| 5 | 20, 45 | 3 | `WaveSetting_TGT_CallerBodark_Wave6` | `WaveSpawner_WildHunt_VHC` |

Vanilla `CallPMC` has one entry — floats (20, 180), count −1 — pointing at
`WaveSetting_TGT_CallerBackup`.

> **Verified:** all 13 handles above resolve to exactly one record each. So the mod is not "give
> PMCs Bodark's backup" — it is **Bodark's escalation schedule, aimed at the nastiest spawners the
> game already has**: two mission ambushes, a quest on-foot hunter squad, two PvE-Elite wave
> spawners (one of them Wolves warfare), and a vehicle Wild Hunt. That is why calling for backup
> becomes so dangerous.
>
> **Not referenced:** the four `TGT_*_Marks*` spawn descriptors the mod also ships are **not**
> what `CallPMC` points at — none of the six handles is theirs. They are a separate edit, most
> likely to units those spawners field; that link is unresolved.
>
> **Inferred:** the float pairs are delay-before-call and cooldown in seconds, and `count` is units
> per wave with −1 meaning "the spawner's own default". On that reading vanilla PMCs make one
> call and wait three minutes; the mod gives them six waves on ~10–55 s cooldowns.

### Resolving a handle

> **Verified.** A 64-bit handle inside a record is the **ClassID of its target**, and every
> record's payload *begins* with its own ClassID. So index `payload[0:8]` across the container —
> 61,452 ClassIDs between base and patch — and every handle becomes a name by lookup. No schema
> needed, and it works for any record type.

### The generalisable technique

Fear the Radio is an instance of a pattern that works across this whole layer:

1. **Find a record that already does the thing you want, on somebody else.** Ubisoft built the
   six-wave escalation schedule for Bodark; the mod gave it to the regular army.
2. **Copy its body over the weaker record**, preserving the target's first 8 bytes (its
   ClassID) so it keeps its identity.
3. **Repoint the handles** at whatever you want the behaviour to summon — resolve them first
   so you know what you are replacing. Any record in the container is a valid target by ClassID.
4. **Ship any other records you changed**, alongside.

This is the gameplay-layer twin of the community's "move a mod to another slot" XML copy-paste
([`../reference/buildtable-xml.md`](../reference/buildtable-xml.md)) — same instinct, done in
hex because ATK gives no XML here.

For **fixed-size** types the cheaper variant applies: keep the record, edit fields in place
against an offset map you got from `--diff` (§3). No size change means no container reflow.

---

## 6. How to actually do it

1. **Back up first.** [`../CLAUDE.md`](../CLAUDE.md) rule 1 is not optional. Confirm ATK's
   backup exists before any repack.
2. In ATK, open `DataPC_patch_01.forge` → unpack → find `DBContainerEntry_0X104634F921.data` →
   unpack **that** too. You get one file per record, named `<name>.<TypeName>`.
3. Edit the record bytes in a hex editor. Use `tools/db_inspect.py --diff` first to know which
   offsets matter.
4. **Mind the number in front of the file.** ATK's repack keeps the **lowest-numbered** file per
   ClassID and silently drops the rest — so if you save your edit as a copy beside the vanilla file
   (rather than overwriting it), give the copy a lower number, the way installed mods ship
   `1_-_…` files. See [`08-naming-conventions.md`](08-naming-conventions.md).
5. **Repack inside-out**: the `DBContainerEntry` container first, let it finish, *then*
   `DataPC_patch_01.forge`. This is the same two-stage rule as `TEAMMATE_Template` and
   `Dbcontainer` — see [`../reference/mod-anatomy.md`](../reference/mod-anatomy.md) §5.
6. Compression: the cloth work found raw/uncompressed blocks hang GRB at load
   ([`../meta/research-log.md`](../meta/research-log.md), 2026-07-02) — but this install's DB
   container is already fully raw after ATK's repack and reportedly plays, so the rule is narrower
   than it sounds (§8).

To read a record without ATK:

```bash
python tools/db_inspect.py "<install>/Extracted/DataPC.forge/5_-_DBContainerEntry_0X104634F921.data" --grep '^DBSoldier' --out ./out
```

> **Untested:** nothing in this document has been repacked and launched. The read path is
> verified end to end; the **write** path is inferred from how the installed mods are shaped.
> The first in-game test should be a single-field change to one fixed-size record, so a failure
> is unambiguous.

---

## 7. Open questions

- **Where does MK1/2/3 tier scaling live?** Not `DBNpcHealth` (§4). Check `TGT_*_Marks*`
  (`GR_SpawnNpcDescriptor`, 54 records, 278–483 B) — Fear the Radio shipped exactly these.
- **What are the 1,557 `[MVET] AI_*` and `[VECN] AI_*` records?** 940 and 617 of them, one type id
  each, named per mission (`[MVET] AI_TU_2E4_MIS_Z03_…`, `[VECN] AI_TGT_SYS_NME_SPE_INT_…`). The
  first walk never reached them. Their naming matches the `[VE] AI_…` voice events found on
  2026-08-14, so dialogue plumbing is more likely than behaviour — *inferred from names only*.
- **What are the seven bands** in `DBSoldierSoundDetectionConfig`? Alert states or sound classes.
- **Which cheat config does a given NPC use?** `DBAICheatConfig` has no `_Wolves` or `_Rifleman`
  instance, so the NPC → cheat-config mapping runs through handles in `DBNpcGeneralConfig`
  (61 records × 38 B). Handles resolve by ClassID lookup (§5), so this is a lookup away rather
  than a research problem — it just has not been run on `DBNpcGeneralConfig` yet.

*(The "full copy or delta?" and "do two AI mods conflict?" questions that stood here were
answered on 2026-09-16 — see §8. "What does `DBAICheatConfig` grant?" was answered too — §9.)*

---

## 8. The patch container is a FULL COPY — and what that means for stacking

> **Verified (2026-09-16), three ways.** The patch `DBContainerEntry` carries the entire
> database, not a set of overrides:
>
> | Container | Records | Entry size | Blocks |
> | --- | ---: | ---: | --- |
> | base `DataPC.forge` | 61,426 | 13,908,748 B | all Oodle-compressed (ratio 0.24) |
> | **pristine** `DataPC_patch_01.forge` (Sept 2023 backup, pre-modding) | **61,452** | 13,911,655 B | all Oodle-compressed (ratio 0.27) |
> | **live, modded** `DataPC_patch_01.forge` | **61,446** | 57,688,741 B | **all raw/uncompressed** (ratio 1.00) |
>
> Matched by ClassID against base, the live patch container reproduces **61,030 records
> byte-for-byte**, changes 390, adds 26 and drops 6. Ubisoft's own untouched 2023 patch container
> is the same shape — against base it changes 71 and adds 26 — and the installed mods account for
> the rest: **319 changed, 6 removed, none added.** So there is no record-level override mechanism
> here: the whole container wins by ID, the way any forge entry does
> ([`06-game-load-and-reassembly.md`](06-game-load-and-reassembly.md)).
>
> *(Corrected 2026-09-16: the first version of this table came from walks that stopped early and
> compared records by name — 50,098 / 50,121 / 50,434 records, and 49,265 identical, 160 changed,
> 597 added, 264 dropped. The conclusion did not change.)*

### But mods *do* stack — verified

Both installed DB mods are live in that one container simultaneously:

- `DBAIRadioCallConfig_CallPMC` is **224 B** in the patch (vanilla is 54 B) — Fear the Radio.
- `DBUnlockEverything (1…235)` records are present — the UE 2.0 unlock mod.

They coexist because of *how* the install works, not because the format merges anything: each
ATK repack rewrites the container **from its current on-disk state**, so dropping new records
into the already-modded container accumulates them. This is the same "an install accumulates
mods in its forges over time" model as the rest of GRB modding.

> **The actual conflict risk** is therefore narrower than "two AI mods clobber each other", and
> sharper: **a mod that ships a pre-built whole `DBContainerEntry_0X104634F921.data` (a ~14–58 MB
> file rather than a folder of small records) will replace the entire database and silently wipe
> every other DB mod you have.** Both mods examined here ship *individual records* to be dropped
> into your own container, which is the safe pattern — and the pattern to insist on.

### Side effect worth knowing: ATK's repack drops the compression

The pristine container is Oodle-Mermaid compressed; the live one is **entirely raw** — all 27
meta blocks and all 1,734 file blocks have `uncompressed == compressed`. The repack inflated
the entry 4.1× (13.9 MB → 57.7 MB) and the whole `DataPC_patch_01.forge` from 831 MB to 1.63 GB.

> **This narrows an earlier finding.** [`../meta/research-log.md`](../meta/research-log.md)
> (2026-07-02) concluded that a `.data` written with **raw/uncompressed** blocks makes GRB
> crash or hang at load, and [`../reference/mod-anatomy.md`](../reference/mod-anatomy.md) §5
> repeats it as a general rule. That was established on **cloth** `.data`. Here is a 57.7 MB
> fully-raw DB container sitting in an install that is played with these mods — so the rule is
> **not universal**; it holds for cloth and does not hold for this container.
>
> *Verified:* the block flags and sizes, read from the live forge index. *Resting on the
> modder's report:* that this install launches and plays. Someone should establish where the
> boundary actually is before the rule is restated as general.

## 9. Worked example 2 — `DBAICheatConfig`, field-mapped

44 records, all exactly **162 B**, so they are field-aligned (§3) and the game ships a null
variant, `_NoCheat`. That is the ideal subject, and the answer to "is *enemies always know
where you are* one byte?" is **no — it is a coordinated profile.**

> **Verified.** Across all 44 records only **46 of 162 bytes ever vary**, and the 44 records
> collapse to **22 distinct profiles** once the 8-byte ClassID is ignored. **18 of them share
> one identical body** — `_NoCheat`, `_SC_TGT_Grenadier`, `_BlackGate`, the Goliath/Ogre arms,
> the autonomous turrets and mortar, `_Suicide`, the Cherubims. That is the "honest" default.

Layout, read off a `_NoCheat` vs `_Miter_Omniscience` hex diff:

| Offset | Content |
| --- | --- |
| 0–7 | ClassID (identity) |
| 8–12 | `9f cb be 07 01` — the typeId echoed, then a constant. Identical in all 44. |
| 13, 18, 19, 35, 36, 37 | **group A** single-byte flags — `0` in the default |
| 14, 20, 28 | three floats. A fourth at **24** is used by exactly one record (`_Miter_Omniscient_InFight`, = 10). |
| 38–49 | `00 00 00 f8 00 00 00 00` + `b9 a6 e0 c8`: an **embedded object's header** — file-local ID `0xF8000000` and class hash `0xC8E0A6B9`. **Identical in all 44** because every cheat config embeds one object of the same class, not because they share a target. *(Corrected 2026-09-16; first published as "a handle marker + a 64-bit handle".)* |
| 50–55 | **group B** single-byte flags — all `1` in the default. Omniscience clears **51–55**; byte 50 is `1` in 43 of 44 (only `_FactionWarfare` clears it). |
| 56, 57, 58 | three more flags — `_NoPerception` sets 56, `_Children` and `_LE2_Low_Stim` set 57, `_FactionWarfare` sets 57 and 58 |
| 59–161 | zero in **40** of 44. A sparse further flag bank at 62, 63, 73, 78, 81, 83, 88, 108, 115, 123, 129, 143, 148, 160, 161, used only by `_Children`, `_LE2_Low_Stim`, `_FactionWarfare` and `_Suicide`. |

The two flag groups move in **opposite directions**:

| Record | 13 | 18 | 19 | 35 | 36 | 37 | 51–55 | @14 | @20 | @28 |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | ---: | ---: | ---: |
| `_NoCheat` (and 17 others) | 0 | 0 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 2 | 0 | 100 |
| `_Walker` | 1 | 0 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 2 | 0 | **75** |
| `_Teammate` | 1 | 0 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 2 | 0 | 100 |
| `_Omniscience_OnMarked` | 1 | 0 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | 2 | 0 | 100 |
| `_DC_TGT_Dragonfly_Ambush` | 1 | 1 | 0 | 0 | 0 | 0 | `1 1 1 1 1` | **5** | **30** | **800** |
| `_FactionWarfare` | 1 | 0 | 0 | 0 | 0 | 0 | `1 0 0 0 0` | 2 | 0 | 100 |
| **`_Miter_Omniscience`** | **1** | **1** | **1** | **1** | **1** | **1** | **`0 0 0 0 0`** | **10** | **22** | **250** |
| `_Miter_Omniscience_Ambush` | 1 | 1 | 0 | 1 | 0 | 1 | `0 0 0 0 0` | 10 | **40** | **200** |
| `_Miter_Omniscient_InFight` | 1 | 0 | 1 | 1 | 1 | 1 | `0 0 0 0 0` | 10 | 22 | 250 |

> **Inferred — but strongly patterned.** Group A reads as **cheat grants** (off by default, all
> six set for full omniscience) and group B as **honesty gates** that omniscience *clears*.
> Byte 13 looks like a master "this unit cheats at all" switch: it is set on the Omniscience
> family, the scripted boss `_Walker`, the Behemoths — **and on `_Teammate`**, which fits, since
> your AI squad has to spot things for you.
>
> `@28` behaves like a **distance in metres** and scales exactly as you'd expect a cheat radius
> to: `_Walker` 75, Goliath 80, turrets 120, `_RAID_BlackGates` 200, omniscient Miter 250,
> ambushing Dragonfly 800, and **0** for the plain `_DC_TGT_Ogre_base` / `_Dragonfly_base`.
> None of the three floats' units are verified.

### What this buys you

Making a unit omniscient is not a byte flip, but it *is* a one-record change: **transplant
`_Miter_Omniscience`'s 154-byte body onto the target's cheat config, keeping the target's own
8-byte ClassID** — the same technique Fear the Radio used (§5). Going the other way is just as
easy: paste the `_NoCheat` body over `_Walker` or a Behemoth to strip a scripted boss's
advantage.

What is still missing is §7's open question — `DBAICheatConfig` has no `_Wolves` or `_Rifleman`
instance, so which config a regular soldier uses is decided by a handle in `DBNpcGeneralConfig`.
That handle resolves by the §5 lookup; until someone runs it, you can only retarget the units
that already have a named cheat record.

## See also

- [`../reference/ai-db-records.md`](../reference/ai-db-records.md) — the type catalogue
- [`../tools/db_inspect.py`](../tools/db_inspect.py) — the walker/extractor/differ
- [`03-data-and-resources.md`](03-data-and-resources.md) — `.data` containers and nesting
- [`../reference/mod-anatomy.md`](../reference/mod-anatomy.md) — install/repack mechanics
- [`../reference/hex-item-swaps.md`](../reference/hex-item-swaps.md) — hex-editing precedent
