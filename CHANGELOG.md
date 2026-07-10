# Changelog

All notable changes to PyKuma are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project is
pre-release, so everything currently lives under **Unreleased**.

Gameplay values that are not yet ROM/decomp-calibrated are marked **provisional**
in code and noted here where relevant — hitbox/animation geometry remains
ROM-accurate.

## [Unreleased]

### Added
- **Frame Lab** debugging system (`core/frame_lab.py`, `schemas/bug_ticket.py`,
  `tools/framelab/audit_animations.py`, `bugs/`, `docs/FRAME_LAB.md`):
  SF6-style frame meter (F4) with expected-vs-actual phase underline and a
  sprite filmstrip row; live measured-vs-declared diffing across provenance
  tiers (ROM timing / community combat / engine formulas); measured emergent
  frame advantage; F9 writes Pydantic-validated bug tickets with per-frame
  phase and cel timelines for AI-assisted fixing; static animation audit
  cross-checks `animations.yaml` against the ROM repository.
- `LICENSE` file (MIT) — README and pyproject already declared MIT but the
  file itself was missing.

### Fixed
- **Neverending s.HP juggle.** Two root causes: landing from air hitstun
  transitioned straight to STANDING (now lands into KNOCKDOWN with its
  wakeup window), and knocked-down characters still had hurtboxes (now
  invulnerable during KNOCKDOWN — no OTG on normals, matching 3S). Pinned by
  `tests/test_gameplay_bugs.py`.
- **Corner shove / back-and-forth on crossup.** The pushbox resolver's 50/50
  split pushed a cornered defender inward when the attacker landed on top,
  then re-clamped — oscillation. A cornered character now keeps their corner
  and the full separation correction goes to the other player.
- **Hit sparks at the wrong location.** The collision system passed the
  DEFENDER'S ORIGIN (feet, on the floor line) as the hit position; sparks now
  spawn at the center of the attack-box/hurtbox intersection — the engine's
  own contact point. Block/parry sparks moved from defender center to the
  guard side at chest height.
- **Normals now run their ROM-verified durations.** Attack-state duration was
  the minimum of (animation length, a hardcoded 20-frame placeholder in
  `Character._update_state`) — the placeholder's own comment asked for this
  fix. Duration now flows through one overridable hook,
  `Character._move_total_frames()`, which Akuma backs with the ROM repository
  (all 18 normals + OVERHEAD; specials stay animation-driven pending ROM
  records). s.MP now runs 22 frames instead of ~16; air normals that outlast
  their duration resume the jump arc instead of snapping to STANDING mid-air.
  Raised the j.LP/j.MP safety caps that sat below their ROM totals. Pinned by
  `tests/test_rom_move_durations.py` (per-move conformance + a Frame Lab
  end-to-end check that all timing channels measure clean).

### Changed
- **Damage/frame-data panel moved to the top of the background** (under the
  health bars), per user request; combo counters flank it. The fight area and
  F4 frame meter keep the bottom.
- **Input display: newest input at the TOP, 20 rows** (was newest-at-bottom,
  12 rows). Inputs persist until they scroll off the bottom of the window.
- **User-replaceable stage backgrounds**: drop an image in
  `assets/backgrounds/` (896x512 native; auto-scaled with a warning
  otherwise) and it loads automatically. See `assets/backgrounds/README.md`
  for the size/layout guide.
- `data/animations.yaml` is now presentation-only: legacy embedded
  `frame_data:`/`hitbox:` blocks removed after verifying no live code reads
  them (the loaded `animation_hitboxes` dict had no readers). The ROM
  repository remains the sole timing/geometry source of record; the framelab
  audit flags any reintroduced block as `data_drift`.
- `requirements.txt` synced with `pyproject.toml` (was missing pydantic and
  friends — a crash for plain-pip users).
- README/ARCHITECTURE consistency: `uv run sf3` is quick play and
  `sf3-menu` is the menu entry (README had them reversed); references to the
  deleted `attic/` directory now point at git history; training hotkeys
  document F4/F9.

### Known issues (tracked as Frame Lab tickets)
- Tatsumaki has no hitbox data (`bugs/manual_tatsumaki_incorrect.yaml`) and
  Demon Flip lacks ROM arc data + Hyakki Go follow-ups
  (`bugs/manual_demon_flip_incorrect.yaml`).
- Animation lengths in `animations.yaml` disagree with ROM totals on every
  grounded normal (now visible as held last cels / truncated tails —
  `sprite_timing`); the six jump normals map to undefined animations
  (renderer falls back); measured frame advantage deviates from community
  values pending blockstun/hitstun calibration. Run
  `python tools/framelab/audit_animations.py --tickets` to (re)generate the
  ticket set. With durations now ROM-driven, the remaining work is fitting
  animations into the ROM windows and calibrating the combat formulas.

### Added
- **AI difficulty tiers / boss ladder** — a selectable ladder of CPU profiles
  (Novice → Brawler → Technician → Veteran → Master, with a locked input-reading
  **Shin Akuma** final boss) chosen from a difficulty screen. Tiers differ by
  reaction-delay, input accuracy, spacing/cadence, capability gating, and super
  usage; all deterministic (fixed-seed PRNG + reaction buffer, no wall-clock RNG).
  `AIProfile` registry in `systems/ai_profiles.py`; `AIController` refactored into a
  profile-driven, frame-aware decision engine.
- **CPU AI opponent** (deterministic, no RNG) — Normal/Demo modes now fight back:
  approaches, pokes, blocks incoming attacks, Shoryuken anti-airs, throws at
  point-blank, and throws the occasional fireball. Feeds the normal input pipeline,
  so it uses the same moves a human does.
- **Super-meter system** — a single 0–100 bar that builds on hits/blocks; a Super
  Art costs a full bar. Bars render in the bottom corners (gold when full).
- **Super Arts**: SA1 Messatsu Gou Hadou (`236236P`, multi-hit super fireball),
  SA2 Messatsu Gou Shoryu (`236236K`, launcher), SA3 Kongou Kokuretsu Zan
  (`214214P`, heavy hit). Super-freeze on activation. *(provisional damage)*
- **Raging Demon / Shun Goku Satsu** (`LP, LP, →, LK, HP`) — unblockable close
  command grab; comes out from its lead-in jabs even through hitstop. *(provisional)*
- **Ashura Senku teleport** (`623/421 + PPP/KKK`) — strike-invulnerable reposition.
- **Hyakkishū demon flip** (`QCF+K`) — arcing approach (dive/throw/palm followups TBD).
- **Throws** (`LP+LK`, forward/back) with connect + whiff animations.
- **Universal Overhead** (`MP+MK`) and **Taunt** (`HP+HK`).
- **Real Gou Hadouken projectile sprite** (replaces the procedural placeholder)
  and the **air fireball** (Zanku Hadou).
- **Projectile↔character collision** — fireballs (and super fireballs) now deal
  damage (chip when blocked, nothing when invulnerable); previously they only
  traveled and rendered.
- **HUD**: icon-based input-history display (vendored `3rd_training_lua` glyphs)
  and a bottom-centered, ~2s-lingering frame-data panel (S/A/R + advantage +
  Damage/Combo/Total).
- **Round-flow poses**: intro on round start, win pose on K.O., time-over pose.
- **Diagnostic framework**: deterministic replay/montage, scenario harness,
  ROM-golden compare (earlier in the project).

### Fixed
- **Fireball never drew** — the projectile-render loop lived in a dead
  (never-called) method, so fireballs spawned and moved but were invisible.
- **Infinite juggle** — added a juggle counter (air-hits cap) + diminishing
  re-launch height; a launched opponent can no longer be juggled forever.
- **Bogus mash "combos"** — a combo is now a hitstun chain (continues only while
  the defender is still in hitstun), not a 2-second wall-clock timer.
- **QCF leniency** — a keyboard quarter-circle that drops the diagonal now still
  fires (matching 3S); a DP or a walk-forward+punch still won't.
- **Dash pass-through** — a forward dash stops at the pushbox contact line and no
  longer shoves the opponent across the screen.
- **Jump direction glitch** — forward/back somersault jumps no longer lurch the
  wrong way (anchor the baked-travel clips by their body center).
- **Crouching MP/HP dealt no damage** — were unmapped ROM moves; now mapped.
- **Invincibility was never honored** — the hit path now respects `is_invincible`
  (teleport / DP-startup / wake-up i-frames actually whiff hits).

### Changed
- Combo expiry and super-freeze are **deterministic** (no wall-clock timers), so
  replays/tests stay reproducible.

### Notes
- Provisional / not-yet-ROM-calibrated values (flagged in code): juggle limit &
  launch decay, throw damage/range, super & teleport & demon-flip damage/timing,
  super-meter gain rates, knockback magnitude, hitstun counts.
- Known gaps tracked for upcoming work: character select + a 2nd character (Ken),
  UOH damage (currently 0), chip-death KO pose, sound/music.
