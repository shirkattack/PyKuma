# Debugging PyKuma

Tools for finding and *communicating* bugs — especially the visual/numerical
kind (wrong sprite, bad position, off frame timing).

## In-game hotkeys

| Key | Action |
|-----|--------|
| `F1` | Toggle the live debug overlay (per-player state panels + invariant status) |
| `F10` | **Build an issue report** — bundle for handing to an assistant (see below) |
| `F11` | **Save a clip** — the last ~4s of per-frame state as a timeline |
| `F12` | Save a debug snapshot (PNG + JSON) to `debug_snapshots/` |
| `ESC` | Pause / resume (freezes the whole sim, including the timer) |

## The fastest way to report a gameplay issue → press F10

When something feels off, hit **F10**. It writes `debug_snapshots/report_<frame>/`
with everything an assistant needs to act:
- `report.md` — a pasteable summary (both players' state, anim + sprite numbers,
  recent invariant violations with frame numbers, missing-art flags)
- `snapshot.png` / `snapshot.json` — the exact frame
- `frames.json` — the recent timeline (so dynamic issues are captured over time)
- `violations.json` — everything the invariant checker flagged

Hand me the `report_<frame>/` folder (or just paste `report.md`).

## The debug overlay (F1)

Shows, per player, the numbers that matter when something looks wrong:

- `state` + `state_frame` — state machine
- `anim` + `frame N/total` + **`spr=<number>`** — the exact sprite being drawn
- `pos`, `vel`, `facing`
- `hp`, `feet_y` (on-screen feet line)
- `stun` (hitstun / blockstun / hitfreeze)
- `grnd` / `act` / `inv` (grounded / can-act / invincible)

The `spr=` field is the key one: if an animation looks wrong, read off the
sprite number and you instantly know which frame is mismapped (this is how the
crouch bug — `crouch_hold` showing `spr=18439` — was found).

The overlay also shows an **invariant status line**: green `INV OK`, or red
`INV <type> p<player> @f<frame>` when the checker catches an anomaly.

## Invariant checker (automatic anomaly detection)

While the overlay is on (or in `--strict`/`DEBUG_MODE`), `core/diagnostics.py`
checks every frame for: feet off the floor, health out of bounds, position out
of stage bounds, NaN/inf in pos/vel, a stuck state, missing sprite art, and
characters fully overlapping. Each anomaly is logged once with the frame number
and the offending values, and surfaced in the overlay + any F10 report. This
turns "it looks like it's floating" into "f412 feet_off_floor p1 y=200 floor=344".

## Fail-loud mode + crash reports

Run with `--strict` (or set `DEBUG_MODE`/`PYKUMA_STRICT=1`) and a frame error
crashes loudly with a traceback instead of being swallowed. Either way, an
unhandled per-frame error writes `debug_snapshots/crash_<frame>/` (traceback +
full state + final PNG). Without `--strict`, the game logs the crash and exits
gracefully. Logging level: `PYKUMA_LOG=DEBUG|INFO|WARNING` (default INFO; DEBUG
when `DEBUG_MODE`). Logs also go to `debug_snapshots/pykuma.log`.

## Snapshots (F12) — the bug-report channel

Press `F12` at the exact moment something looks wrong. It writes:

- `debug_snapshots/snapshot_<frame>.png` — what's on screen
- `debug_snapshots/snapshot_<frame>.json` — full numerical state of both players

Send **both files**. The JSON pins down the exact sprite/frame/position/state, so
a fix can target the right data without guessing. Example of what it captures:

```json
"anim": { "animation": "crouch_hold", "frame_index": 0,
          "total_frames": 1, "sprite_number": 18438 },
"feet_y": 430, "pos": [200, 344], "state": "CROUCHING"
```

`debug_snapshots/` is git-ignored.

## Animation audit (offline)

To review every animation's frames and catch mislabeled/missing art:

```
SDL_VIDEODRIVER=dummy uv run python scripts/audit_animations.py
```

Writes labeled filmstrips to `docs/animation_audit/` and a reference table to
`docs/ANIMATIONS.md`. Red cell = size-outlier frame to review; orange `MISSING`
= no source art. Regenerate after re-extracting sprites. See `docs/ANIMATIONS.md`.

## Headless run (no window)

All of the above work headless for scripted checks / CI:

```
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run pytest -q
```
