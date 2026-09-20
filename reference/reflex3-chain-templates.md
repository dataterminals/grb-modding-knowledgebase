# Reflex3 chain templates — how vanilla builds a bone-physics chain

*Written 2026-09-20 from the physics record decode of that day. Every number here was read out
of the install's skeleton resources with [`tools/reflex3.py`](../tools/reflex3.py); nothing was
written or launched. Format background: [`skeleton-reflex3-physics.md`](skeleton-reflex3-physics.md).*

> **Why this page exists.** There is no vanilla garment that flows on bones alone (2026-09-16):
> every flowing coat, cape and kilt is cloth, and bone physics swings *danglers* — hair, straps,
> zipper pulls, backpacks. A poncho on bones is therefore a **new, hand-authored chain rig**, and
> this page is the set of vanilla recipes to copy from. Hair is the closest thing the game has to a
> hanging panel: a strand is a chain of four or six physics records, stiff and heavy at the root,
> loose and light at the tip, and only allowed to swing *away* from the body.

---

## What one physics record says

A type-21 record drives **one bone**. The fields an author sets (full layout on the format page):

| Field | Unit | What vanilla does with it |
| --- | --- | --- |
| `BoneID`, `ParentBoneID` | CRC32 of the bone names | the driven bone and what it hangs from |
| swing 1 `[min, max]` | degrees (stored as radians) | side-to-side limit; symmetric on hair |
| swing 2 `[min, max]` | degrees | fore-and-aft limit; **one-sided** wherever the body is on one side |
| slide X / Y / Z | metres | off on every garment and hair record; only weapons use it (≤ 2.5 mm) |
| mass\* | — | `0.2` default; `0.4 → 0.1` down a hair strand; `5.0` for a whole backpack |
| spring\* | — | `0` on hair and garments; `25` on backpacks (spring-returned to rest); `20` with slide |
| slide damping\* | — | `0` unless slide is on (then `0.95` / `0.98`) |
| `p3` | — | `0` default; `0.6` on hair strands, `0.8` ponytail, `1.0` backpacks — **meaning unresolved** (swing damping or centre of mass; both fit) |
| gravity | m/s² | `9.8` everywhere |
| gravity factor\*, wind factor\* | — | `1.0`, `1.0`; wind `0` on knives and one backpack |

\* inferred name, from value distributions and ATK's Mirage field list. The four matrices per
bone are derived, not authored: local bind twice, the parent's character-space frame, and the swing
rest frame twice (equal to the local bind in 1,194 of 1,362 records). See the format page for how
the character-space frame is computed.

> **Verified:** the layout and every value below. **Inferred:** the field names marked \*, and
> everything under *A poncho recipe*.

---

## Template 1 — a hair strand (`Tsec_Herzog_Hair_Skeleton`, 28 records)

Seven strands of four bones and two of two, all hanging from bones the rig parents under `Head`.
Segment length ≈ 5 cm. Read root to tip:

| depth | swing 1 | swing 2 | mass\* | `p3` | link length |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | ±10° | 0 … +25° | 0.4 | 0.6 | 0.048 m |
| 2 | ±15° | −1 … +30° | 0.3 | 0.6 | 0.051 m |
| 3 | ±20° | −3 … +35° | 0.2 | 0.6 | 0.051 m |
| 4 (tip) | ±25° | −5 … +40° | 0.1 | 0.6 | — |

The shorter strands taper the same way from a tighter start (±5° / 0 … +15°, mass 0.4) to ±20° /
−5 … +40° (mass 0.1). The two-bone strands sit at ±5° / −3 … +5° (mass 0.3, `p3` 0.25) then ±10° /
−3 … +10° (mass 0.2, `p3` 0.1).

**The pattern:** limits widen by 5° per link, mass falls by 0.1 per link, fore-aft swing is
one-sided at the root and opens up by a few degrees toward the tip. The strand can swing *out* from
the head freely and *into* it hardly at all. **That one-sided limit is the collision proxy** — no
record on any hair rig carries a collision shape.

`Tpri_Hair_Addon_Rosa` is the same 28-record rig with different bone names.

## Template 2 — a long chain and a tuft (`FTP_Casper_Hair_Skeleton`, 8 records)

Two chains straight off `Head`. The six-bone chain is the deepest physics chain on any garment-like
rig in the game:

| depth | swing 1 | swing 2 | mass\* | `p3` |
| ---: | --- | --- | ---: | ---: |
| 1 | ±3° | ±3° | 0.2 | 0 |
| 2 | ±5° | −145 … +4° | 0.2 | 0 |
| 3 | ±10° | ±10° | 0.2 | 0 |
| 4 | ±10° | ±10° | 0.2 | 0 |
| 5 | ±15° | ±15° | 0.2 | 0 |
| 6 | ±15° | ±15° | 0.2 | 0 |

The two-bone tuft: [−10, +2°] / ±170° then [−15, +5°] / ±15°, mass 0.2, `p3` 1.0. Link lengths
5–10 cm. Note the second link's −145° fore-aft limit: one link is allowed to fold almost flat while
the rest are held tight.

## Template 3 — a ponytail that swings back only (`Tter_ponytail_layla`, 4 records)

Four links of 7–8 cm, every one `[0, +90°]` / `[−45, +45°]`, mass 0.2, `p3` 0.8. No taper: the
whole tail may swing 90° backward and not at all forward, and ±45° sideways.

## Template 4 — a single hanging panel (`Player_Kilt_Addon`, 1 record)

One bone, **45.5 cm** long, hanging from a bone parented under `Hips`: ±15° / ±5°, mass 0.2,
`p3` 0, gravity 9.8. The kilt also has a cloth; this record sits beside it. It is the only vanilla
garment record, and it shows a panel can be one long bone rather than a chain.

## Template 5 — straps, pulls and the pack itself (`BP_wStraps_Hill_MEDIUMVEST`, 6 records)

| bone hangs from | swing 1 | swing 2 | mass\* | `p3` | what it is |
| --- | --- | --- | ---: | ---: | --- |
| `RFX_BackPack` | ±2° | −1 … +2° | **5.0** | 1.0 | the whole pack: heavy, barely moves |
| `T_Strap01`, `T_Strap02` | 0 … +10° | ±20° | 0.2 | 0 | shoulder straps |
| `T_Strap03` | 0 … +5° | 0 … +20° | 0.2 | 0 | |
| `T_Zipper01`, `T_Zipper02` | ±30°, ±60° | −5 … +19°, −5 … +26° | 0.2 | 0 | zipper pulls |

The `T_` bones are static anchor bones the physics bones hang from — the same grammar as the trench
coat's `T_SpineTrenchCoat`. The 2026-09-16 check found the backpack meshes weighted to these driven
bones, so this is a rig that demonstrably moves geometry.

## Template 6 — what the trench coat's bones actually do (`Tsec_Trench_AddonSkeleton`)

Ten physics records with **swing 1 off** and swing 2 one-sided, `[−20°, 0]` on five and `[0, +20°]`
on five — panels allowed to fold one way — mass 0.2, `p3` 0. Their parents are the twelve bones a
pose-driven orientation record (type 9) hangs under `Spine2` and the shoulders. Beside them sit 36
hinge records (type 6), each blending a bone 50 % toward `T_SpineTrenchCoat` or one other bone. The
coat *mesh* is not weighted to any of these bones (2026-09-16); what they move is still open. But as
a *grammar* for a hanging garment it is the closest thing in the game: anchor bones under the spine,
one-sided fore-aft limits, no side swing.

## Template 7 — the slide record (`WI_LMG_MK48`, 4 records)

Weapon parts that translate rather than swing: slide on X and Y (one on Z too), limits ±0.5 mm to
2.5 mm, spring 20, slide damping 0.95–0.98, mass 0.4–0.8. Not a garment pattern; listed so the slide
fields have a worked example.

---

## A poncho recipe

*Inferred throughout. Nothing here has been written into a skeleton or loaded in game.*

1. **Anchor.** Hang the rig under `Spine2` (the trench coat, the scarf and every backpack do), with
   one static anchor bone per panel at the shoulder line, named `T_…` by the vanilla grammar.
2. **Panels.** Six strands — front left/right, side left/right, back left/right — of four or five
   links each. A 50 cm drop at 10–12 cm per link keeps the chain in vanilla's range (hair 5 cm,
   ponytail 8 cm, kilt 45 cm for a single bone).
3. **Per link, copy template 1:** swing 1 (side-to-side) ±10° → ±25°, swing 2 (fore-aft)
   one-sided *away* from the body opening from 0 … +25° to −5 … +40°, mass 0.4 → 0.1, `p3` 0.6,
   gravity 9.8, factors 1.0, slide off. Mirror the fore-aft sign for the back panels so both swing
   outward.
4. **Record order** as vanilla writes it: root to tip along one strand, then the next strand. A
   two-swing record is 386 bytes; the blob is the 8-byte header followed by the records, nothing
   else — the kilt and every hair rig are exactly that.
5. **Matrices:** the bone's local bind transform four times (positions 1, 2, 4, 5), and in position 3
   the parent bone's frame in character space, computed from the body rig as the format page
   describes.
6. **Weight-paint the poncho mesh to the link bones** (four influences per vertex, 2026-09-01) and
   run [`rebind_check.py`](../tools/rebind_check.py) against the rig before any launch.

**What this does not give you.** Collision: the limits are the only thing keeping a panel out of
the body, so start conservative. Wind: the wind factor exists but nothing shows what feeds it. The
meaning of `p3`. And the write path: ATK round-trips the blob as Base64 inside its skeleton XML, so
a generated blob can be carried into a skeleton through the existing `--xml` route — but no modified
skeleton has ever been confirmed to load (lane 2B, [`../meta/next-session.md`](../meta/next-session.md)).
