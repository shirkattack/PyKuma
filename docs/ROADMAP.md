# Roadmap

Short and current. The long-form phase history and the older roadmap drafts were
removed (git history has them); `CHANGELOG.md` is the record of what shipped.

## Where things stand

- **Engine**: fixed 60 FPS timestep, deterministic sim, reset contract, headless
  diagnostics harness (`tools/diagnostics/`), Frame Lab (`docs/FRAME_LAB.md`).
- **Akuma**: full moveset — 18 normals (ROM boxes + timing), UOH, throws, taunt,
  Gohadoken (+air), Goshoryuken, Tatsumaki (+air), teleport, demon flip, SA1–SA3,
  Raging Demon. Specials are driven by the ROM movement scripts and hit per ROM
  hit window (see `docs/AKUMA_MOVE_MAP.md`).
- **Systems**: parry (7f, high/low), level-aware blocking (MID/HIGH/LOW), chip, pushback, hitstop,
  juggle cap, combo scaling, super meter, round flow, CPU opponent with a
  selectable difficulty ladder, P2 palette.
- **Data**: no invented geometry — ROM dump → converter → `hitboxes.yaml` with
  provenance tiers (`ARCHITECTURE.md`). Damage/stun/advantage are community tier.

## Next

1. **ROM backfill of provisional values** (`tools/rom_extract/`): special-move
   damage scale (currently Baston ×7.5), DP blockstun columns, knockback
   magnitudes, the P2 palette (a PyKuma colour, not a ROM palette dump).
2. **Demon Flip followups** (`af08/b118/b218`) — the last unwired ROM scripts
   (the flip itself has no hitbox; the dive/throw/palm followups do). Also:
   per-move proximity ranges for the close/far normals (one provisional
   threshold today).
3. **Shin Akuma** final boss + arcade-ladder progression (menu entry is teased).
4. **Second character + character select** (`GameMode.VERSUS` / `DEMO` exist but
   are not reachable from the menu).
5. Sound & music; chip-death KO pose.
