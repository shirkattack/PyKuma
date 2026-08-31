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
   magnitudes. (The P2 palette is done — `rom_palettes.json` is the game's own
   alternate palette, pen for pen.)
2. **Per-move proximity ranges** for the close/far normals (one provisional
   threshold today). The Demon Flip followups are wired: a punch during the
   arc cancels into `b118` (Hyakki Goushou), a kick into `b218` (Hyakki
   Goujin), both on their ROM boxes and captured damage. Still open there: the
   throw followup (Hyakki Gousai — `b308` fits the signature but the ROM
   metadata does not name it) and whether the flip itself hits (`af08` carries
   attack boxes in the vendored framedata; the live capture read none).
3. **Shin Akuma** final boss + arcade-ladder progression (menu entry is teased).
4. **Second character + character select** (`GameMode.VERSUS` / `DEMO` exist but
   are not reachable from the menu).
5. Sound & music; chip-death KO pose.
