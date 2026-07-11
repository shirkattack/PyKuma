# Frame Lab — systematic frame-data debugging

The Frame Lab closes the gap between what you *see* ("the HP does too much
damage and freezes the opponent too long") and what an AI assistant can *act
on* (`channel=damage observed=200 expected=180 [community]`). The frame
number is the shared address space: every pip on the meter, every measured
value, and every bug ticket refers to the same `(move, frame N)`.

It reads **live engine truth** — the same `state_frame + 1` indexing the
collision adapter uses, the values actually applied on hit — never the data
files, so an engine bug shows up as an engine bug instead of being masked by
re-deriving from the same data the engine read.

## Hotkeys

| Key | Action |
|-----|--------|
| F4  | Toggle the frame meter (on by default in Training/Dev) |
| F9  | File bug ticket(s) for the last completed move → `bugs/*.yaml` |

(F10/F11/F12 issue-report/clip/snapshot tools are unchanged and complementary.)

## Reading the meter

Two pip strips (P1 above P2), one pip per game frame, last ~90 frames:

- **Green** startup · **Red** active · **Blue** recovery · **Ember** gap (boxes-off frames BETWEEN the active windows of a multi-hit move, e.g. s.HK — not recovery)
- **Yellow** hitstun · **Cyan** blockstun · **Grey** movement · dark = neutral
- **White notch** on top of a pip = hitstop (frozen frames are *excluded*
  from measured counts, matching how SF3 frame data is quoted)
- **Filmstrip row** (above each strip) = the sprite track on the same frame
  ruler: alternating grey blocks per cel hold (you can *see* the cel rhythm
  against the phase colours), a white tick at every cel change, **magenta**
  where a placeholder rectangle was drawn instead of a sprite
- **Thin underline** beneath the pips = the *declared* (expected) phase for
  that frame. When the underline colour disagrees with the pip colour, you
  are literally looking at a timing bug — the misalignment is the diagnosis.
- A white tick marks each move start.

Below the strips, the last completed move per player is summarised:
`meas S/A/R/T` vs `exp S/A/R/T`, damage vs expected, hitstop, and measured
frame advantage. Discrepancies render in **orange** with a `!!` line.

## What gets diffed, against what

| Channel | Expected source | Provenance | If they differ… |
|---|---|---|---|
| startup / active / recovery / total | `hitboxes.yaml` (ROM dump) | verified | the **engine** is wrong — never edit the data |
| damage / hitstun / blockstun | community tier; hitstun/blockstun are back-solved from on_hit/on_block against the ROM timeline (`_calibrated_stun`) | community | recheck the community advantage numbers or the calibration |
| hitstop | adapter formula | engine-formula | engine mis-applied freeze, or tune the constants |
| advantage on hit/block | community tier | community | emergent — fix hitstun or recovery, never the output. Only diffed when the move's FINAL active window connects (a partial multi-hit connect is not the quoted scenario) |
| sprite_mapping | `_STATE_ANIM` (akuma.py) | engine-mapping | wrong/undefined animation for the state |
| sprite_timing | anim length vs ROM total | verified | fit the animation to the move, never the reverse |
| sprite_sync | cel timeline vs active window | verified | auto-flagged only when provably impossible; otherwise human-filed via F9 |
| sprite_fallback | renderer | engine | missing local sprite assets or bad sprite id/path |
| data_drift | animations.yaml embedded blocks vs ROM repo | verified | delete/regenerate the stale duplicate |

Measurement details worth knowing:
- **Multi-hit gaps are not recovery.** Boxes-off frames between a move's
  active windows are measured (and drawn) as GAP; recovery is only what
  follows the last active frame, and total is diffed against the ROM total.
- **Hitstop freezes the sprite too.** Animations no longer advance during
  hit freeze (they used to desync from the frame data by the freeze length
  on every connected hit).
- **Cancels don't false-flag.** A move cancelled into a special legitimately
  truncates recovery; recovery/total diffs are skipped for cancelled moves.
- **Advantage is measured emergently**: the frame the defender becomes
  actionable minus the frame the attacker does. Knockdowns are excluded
  (different advantage model).
- **Raw vs scaled damage** are both recorded; damage is diffed on the raw
  value so combo scaling can't masquerade as a data bug.

## The debugging loop

1. Play in Training or Dev mode; watch the meter.
2. Something looks off → the meter usually already shows it (orange line or
   colour misalignment). Press **F9**.
3. Optionally add a one-line `complaint` to the ticket in `bugs/`.
   Every `!!` line the meter shows is also appended as plain text to
   `bugs/discrepancies.log` (and the console log), so it can be copied or
   grepped instead of transcribed off the screen
   (`PYKUMA_DISCREPANCY_LOG` overrides the path; empty disables).
4. Hand the repo to your assistant: *"fix the open tickets in bugs/"*.
   `bugs/README.md` is the assistant's consumption contract — provenance
   rules, canonical files per channel, and the requirement to re-verify.
5. Fixed tickets stay in `bugs/` with `status: fixed` as the audit trail;
   promote recurring ones into `tests/`.

## The sprite track (phase 2)

Every ticket for a move now carries `repro.cel_timeline`: one row per cel
hold, annotated with the mechanical phase it landed in. That table IS the
sprite-sync spec — "the fist extends at cel 5 but the boxes go live during
cel 3" becomes rows an assistant can act on. Automatic flags stay
conservative (wrong animation, missing art, animation provably unable to
match the hit); whether the *right cel* shows at the right time is a human
judgement, filed with F9 like everything else.

### Static audit (no gameplay needed)

```
python tools/framelab/audit_animations.py            # console report
python tools/framelab/audit_animations.py --tickets  # file bugs/*.yaml
```

Audits the LIVE sprite track — the folder animations Akuma registers in
`_setup_animations` (NOT `animations.yaml`, whose numbered-sprite lists are
a legacy path Akuma doesn't render): unregistered animations for mapped
states, registered length (sum of per-cel holds) vs ROM move total, missing
animation folders on disk, plus the `animations.yaml` embedded-block guard
(`data_drift`). Since the ROM-fit pass, attack animations receive per-cel
holds computed FROM the ROM totals at registration, and the audit reports
**zero findings** — it now exists to catch regressions (a hand-tuned
duration creeping back, a deleted folder, a remapped state).

## Deliberately next

A headless scripted-scenario runner so tickets carry a *replayable* repro
(input script) instead of a recorded one, and per-move regression scenarios
generated from fixed tickets.

## Testing

```
uv run pytest tests/test_frame_lab.py -v
```

Covers: correct moves produce zero discrepancies; phase classification
matches the ROM windows frame-for-frame; hitstop is excluded from counts;
a seeded wrong-damage hit yields exactly one `damage` discrepancy and a
schema-valid ticket; cancels don't false-flag; blocked hits diff blockstun.
