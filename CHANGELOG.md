# Changelog

All notable changes to PyKuma are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project is
pre-release, so everything currently lives under **Unreleased**.

Gameplay values that are not yet ROM/decomp-calibrated are marked **provisional**
in code and noted here where relevant — hitbox/animation geometry remains
ROM-accurate.

## [Unreleased]

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
