# bugs/ — Frame Lab tickets (the human → AI hand-off)

Every `.yaml` in this directory is one **dimensioned claim about one move on
one channel**, emitted by the Frame Lab (press **F9** in-game) and validated
by `src/street_fighter_3rd/schemas/bug_ticket.py`. This replaces prose bug
reports like "the HP does too much damage": the ticket already contains the
observed value, the expected value, its provenance, and where the value lives.

## For the human

1. Play. Watch the frame meter (**F4**). When something looks wrong — or the
   meter flags a discrepancy in orange — press **F9**.
2. Optionally open the newest ticket(s) and replace the `complaint`
   placeholder with what it looked or felt like. This is colour, not spec —
   the numbers are already in the ticket.
3. Hand the repo to your AI assistant: *"fix the open tickets in bugs/"*.

## For the AI assistant (Claude Code et al.)

Process each ticket with `status: open`:

1. **Trust the provenance tier before anything else.**
   - `provenance: verified` (startup/active/recovery/total): the expected
     value is ROM-dumped and is NOT wrong. If measured != declared, the
     **engine** is at fault. Never "fix" a verified ticket by editing
     `data/characters/akuma/hitboxes.yaml` — it is generated output.
   - `provenance: community` (damage/hitstun/blockstun/advantage): the
     expected value is community data. The fix is usually in the declared
     data or in the engine code that ignores/derives it — read the ticket's
     `note` field (e.g. blockstun is currently derived as
     `max(4, hitstun // 2)` and never reads the declared value).
   - `provenance: engine-formula` (hitstop): expected comes from the design
     formula in `sf3_collision_adapter.py`. Deviation means the engine
     double-applied or skipped freeze; a "feels wrong" complaint with NO
     deviation means the constants themselves should be tuned.
2. **Start from `fix_hints`** — they list the canonical files per channel.
   Cross-check `ARCHITECTURE.md` for which module is canonical.
3. **Use `measured_summary` and `repro.phase_timeline`** to see exactly which
   frames did what; `repro.session_clip` (when present) has the inputs.
4. **After fixing:** rerun `pytest tests/test_frame_lab.py`, then reproduce
   the scenario if possible. Set the ticket's `status: fixed` and append a
   short note of what changed. Do not delete tickets — they are the audit
   trail, and fixed tickets should become regression tests where practical.

## Ticket anatomy (annotated example)

```yaml
schema_version: 1
id: 000206_p1_medium_punch_recovery_002
status: open
move: MEDIUM_PUNCH          # CharacterState name
player: 1
channel: recovery           # the ONE dimension this ticket is about
frame_range: [166, 206]     # global game frames the move spanned
observed: 7                 # what the engine actually did (measured live)
expected:
  value: 13
  source: data/characters/akuma/hitboxes.yaml (ROM dump)
  provenance: verified      # => the ENGINE is wrong, not this number
delta: -6.0
complaint: "<optional: describe what you saw or felt>"
measured_summary: { ... }   # full measured S/A/R/T, hits, advantage
repro:
  phase_timeline: [ ... ]   # per-frame phase + frozen flag for the move
fix_hints: [ ... ]          # canonical files for this channel
```
