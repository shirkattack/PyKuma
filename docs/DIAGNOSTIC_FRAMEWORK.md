# Diagnostic & feedback framework

The standard way we identify gameplay issues, compare against the real game, and
exchange feedback — so we stop guessing and fixing-then-breaking. Two principles:

1. **No invented data** (already enforced for hitboxes) **+ no invented logic**:
   combat algorithms are ported from the SF3 decompilation (`crowded-street/3s-decomp`,
   provenance-tagged), not guessed.
2. **Every fix is seen and proven**: from a captured clip (visual) and a scenario
   test (objective), not from one person's eyeballing.

## The loop

**You (reproduce → capture):**
1. In `uv run sf3-training`, reproduce the issue.
2. Press **F11** immediately — writes a ~10s session clip to
   `debug_snapshots/clip_<frame>/frames.json` (+ `current.png`, `summary.md`).
   The clip records, per frame, both players' state / pos / facing / animation
   **and the raw inputs you held**.
3. Send me the clip path + a one-line symptom (e.g. "back-jump plays forward flip").

**Me (see → diagnose → fix → prove):**
1. **See it:** `uv run python tools/diagnostics/replay.py debug_snapshots/clip_<frame>`
   → `montage.png`, a contact-sheet of the recorded frames I can open. (State
   playback — faithful to what happened; it renders the recorded state, no re-sim.)
2. **Find the truth:** read the authoritative routine in the decomp
   (`src/anniversary/sf33rd/Source/Game/` — e.g. `HITCHECK.c`).
3. **Reproduce as a scenario:** add a `Scenario` in `tools/diagnostics/scenario.py`
   that scripts the same inputs and runs through the real sim.
4. **Compare to expected:** capture the ROM behavior for that scenario (see
   `tools/rom_extract/`) into `data/golden/<name>.jsonl`, or hand-author a
   decomp-derived expectation; diff with
   `uv run python tools/diagnostics/compare.py actual.json golden.json`.
5. **Fix + lock it:** port the logic (provenance comment citing the decomp), then
   add a scenario test under `tests/` so it can't regress.

## Tools

| Tool | What it does |
|---|---|
| **F11** (in game) | session clip → `debug_snapshots/clip_*/frames.json` (state + inputs) |
| `tools/diagnostics/replay.py <clip>` | recorded clip → labeled montage PNG (see the motion) |
| `tools/diagnostics/scenario.py` | scripted, re-simulated scenarios (`ScriptedInputSystem`); `SEED_SCENARIOS` |
| `tools/diagnostics/compare.py a.json b.json` | diff a timeline vs a golden (pos/state/health/hitstun) |
| `tools/rom_extract/` | capture ground-truth ROM timelines (FBNeo) |

Determinism (fixed timestep, no RNG) makes replay/scenarios reproducible — guarded
by `tests/test_determinism.py`. See also `docs/DEBUGGING.md`, `docs/DEBUG_BACKLOG.md`.

## Known targets surfaced by the framework (Phase 2, decomp-sourced)

The `jab_knockback` scenario already exposes, from data:
- the **attacker** also enters `HITSTUN` when its own hit connects (wrong);
- **no knockback** on hit (defender doesn't move);
- jab **hitstun runs too long**.

These are fixed in Phase 2 by porting the reaction/knockback/hitstun logic from the
decomp, each gated by a scenario test.
