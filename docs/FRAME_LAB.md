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

- **Green** startup · **Red** active · **Blue** recovery
- **Yellow** hitstun · **Cyan** blockstun · **Grey** movement · dark = neutral
- **White notch** on top of a pip = hitstop (frozen frames are *excluded*
  from measured counts, matching how SF3 frame data is quoted)
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
| damage / hitstun / blockstun | community tier (Baston ESN3S) | community | data or the code that ignores it (see ticket note) |
| hitstop | adapter formula | engine-formula | engine mis-applied freeze, or tune the constants |
| advantage on hit/block | community tier | community | emergent — fix hitstun or recovery, never the output |

Measurement details worth knowing:
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
4. Hand the repo to your assistant: *"fix the open tickets in bugs/"*.
   `bugs/README.md` is the assistant's consumption contract — provenance
   rules, canonical files per channel, and the requirement to re-verify.
5. Fixed tickets stay in `bugs/` with `status: fixed` as the audit trail;
   promote recurring ones into `tests/`.

## Scope of v1 (and what's deliberately next)

v1 covers the **mechanical channel** (timing, damage, hitstun, blockstun,
hitstop, advantage). The architecture already reserves the next channels:
sprite↔hitbox sync and sprite mapping (a filmstrip row locked to the same
frame ruler), and a headless scripted-scenario runner so tickets can carry a
replayable repro instead of a recorded one.

## Testing

```
uv run pytest tests/test_frame_lab.py -v
```

Covers: correct moves produce zero discrepancies; phase classification
matches the ROM windows frame-for-frame; hitstop is excluded from counts;
a seeded wrong-damage hit yields exactly one `damage` discrepancy and a
schema-valid ticket; cancels don't false-flag; blocked hits diff blockstun.
