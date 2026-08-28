# Changelog

All notable changes to PyKuma are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project is
pre-release, so everything currently lives under **Unreleased**.

Gameplay values that are not yet ROM/decomp-calibrated are marked **provisional**
in code and noted here where relevant — hitbox/animation geometry remains
ROM-accurate.

## [Unreleased]

### Added
- **Sprites, axis and timing from the ROM.** `tools/rom_extract/dump_cels.lua`
  + `cel_decode.py` rip a character's cels pixel-exact out of the emulator
  (sprite list, tiles from a savestate's character RAM, palettes), keyed by ROM
  cel id and positioned on the character's own axis; `build_rom_animations.py`
  joins them with the frame dumps' per-frame cel ids into per-move tables
  (`data/characters/akuma/rom_animations.json`: cel sequence, ROM hold per cel,
  bbox from the axis). Akuma now plays these `CelAnimation` clips for every
  move whose sequence is complete — 44 clips: stance, walks, dashes, the three
  jumps, all far and crouching normals, jump normals with their neutral-jump
  variants, f+MP, the DPs and tatsus, both blocks — placed by exact axis offset
  (no canvas centring, padding or body anchoring), and P2 renders in the game's
  own alternate palette (`rom_palettes.json`, pen-for-pen). Incomplete
  sequences (close normals, reactions) keep the zweifuss folder clips.
- **On-block ROM data + a self-sufficient capture script.** `dump_framedata.lua`
  now pins the round timer, refills life while idle and drives the dummy itself
  (`B` cycles stand / block / block_always / crouch_block / jump — the arcade
  ROM has no training menu and only one Lua script runs at a time). The
  2026-08-27 session produced the first 84 block samples: blockstun 11 / 14 / 17
  for light / medium / heavy normals, chip 0 on normals and 1–2 on specials, and
  the engine now applies captured blockstun ahead of the community estimate
  (st.MK 17, cr.MP 14 — the calibration had them at 21 / 20). Its whiff pass
  took the ROM per-move hurtboxes from 5 to **31 of 43** attack scripts
  (`merge` prefers whiffed runs, since a connect freezes the attacker).
- **ROM per-move hurtboxes (v_hb) start landing.** The live capture's
  `ext_vulnerability` array is confirmed as the limb-that-becomes-hittable box
  (st.LK matches the Baston seed to the pixel), and `ingest.py merge` now backfills
  it into `gouki_framedata.json` — far LP, LK, neutral-jump HK, LP DP and LK tatsu
  from the 2026-08-26 capture carry `verified` ROM hurtbox extensions (the Baston
  supplement is ignored once a move has ROM data). `merge` counts a move's frames
  from the anim change, skipping frames the attacker is frozen by hitstop, and
  annotates only a move whose captured attack boxes line up frame-for-frame with
  the vendored framedata (the rest are reported; drive moves on whiff for the
  hurtbox pass). `validate` works again (it read `move_names.json` inverted).

### Fixed
- **Corner cross-ups no longer jitter or freeze.** Jumping over a cornered
  opponent (plain jump, air tatsu or demon flip) shoved them off the wall and
  then swapped the two fighters every frame, flipping both facings and
  cancelling their walks; an air tatsu that touched down mid-spin sat in a
  grounded JUMPING state until the safety timeout. The pushbox resolver now
  has explicit wall ownership (the fighter grounded at the wall longest keeps
  it; the other is placed inside), which makes the per-frame double resolution
  idempotent, and the air tatsu recovers on the ground when it lands early.
- **Specials and jump normals follow the ROM's hand-offs.** The frame dumps
  record what the game plays after a script ends: MP/HP Goshoryuken fall
  through the LP DP script from its 5th cel (`84f8`, movement rows included, so
  the arcs are the ROM's 88 / 125 / 56 px and the moves land on f42 / f51 /
  f35), every tatsu lands with `645c`, jump normals with `5c7c`, jumps with
  `5b7c`, the air fireball with `7684`. `rom_animations.json` carries those
  links; the animation controller chains clips on completion and Akuma plays
  the landing clip on touchdown and recovers for its ROM length. The Frame Lab
  no longer flags hand-offs as held cels or wrong animations.
- **Multi-hit moves no longer double-scale or false-flag.** The combo system
  stepped damage scaling down for every hit window of the same move (cl.HK's
  second hit 12 → 10, MP DP 8 → 7) although the ROM-captured per-window values
  already are what the game applies inside the move; scaling is now anchored at
  a move's first hit and only a new move steps it down. The Frame Lab diffed
  every hit against the first window's expectation; it now diffs each hit
  against its own ROM window (`window` on hit events, `Expected.rom_hits`).
- **Multi-hit ROM combat windows.** Session 1's vendored raw samples had `frame`
  = the ROM cel id (`22047` reached `hitboxes.yaml`) and a multi-hit move's later
  connects were placed by a frame the defender's hitstop cannot pin, collapsing
  cl.HK / MP DP / HP DP onto one window. Connects now carry their ordinal in the
  run (`hit_index`/`run_hits`) and a run that landed every hit is placed by
  ordinal: cl.HK 21+12, MP DP 17+8, HP DP 10+9+9. Session 1's raw was repaired
  from recorded data (its `_meta.frame_repair`), session 2's re-derived.
- **Knockdowns are no longer "hitstun".** A hit that changes the defender's
  posture (launch / down) records `knockdown` + `down_frames` instead of a
  115-frame hitstun; the engine falls back to the community hitstun for those.
  A multi-hit move whose later hits never landed reports no `damage_total`
  (`complete: false`) so a partial sum is never read as the move's damage.
- **Arcade ROM tables read directly** (`tools/rom_extract/cps3_chardata.py`):
  decrypts the sfiii3nr1 program SIMMs in memory (CPS3 cipher + table
  locations from crowded-street/3sx) and vendors Akuma's `atta` attack boxes
  and `atit` attack data (`data/sources/cps3_akuma_chardata.json`). Every
  attack box in the RAM dump is in the ROM table verbatim (test), so the
  geometry tier is verified against the ROM itself; the attack table gives
  raw damage (`Power_Data[pow]`), stun index, hitstop, guard bits, reaction
  and level per cel — linking them to moves is the next step.
- **ROM-exact combat capture pipeline** (`tools/rom_extract`): the dump script
  now records both players' applied damage / stun, hitstop (freeze), recovery,
  blocking and the attack/defense multipliers every frame (all addresses are
  ones 3rd_training_lua reads; semantics confirmed in the 3s-decomp disc
  source: `dm_vital` is post-multiplier damage and the life bar is 0xA0 = 160
  for everyone). `ingest.py combat` turns a session into `rom_combat.json`
  (per move + hit frame: damage, stun, hitstop, hitstun, blockstun, chip); the
  converter attaches it per hit window as a `verified` `rom_combat` block and
  records the life-bar scale; the engine then runs at 160 vitality, prefers
  captured values, rescales community-only moves, and the Frame Lab reports
  combat discrepancies as `verified`. Recipe: `tools/rom_extract/CAPTURE.md`.
  No capture is checked in yet — Baston remains the live tier until then.
- **Proximity normals, straight-jump normals, f+MP and the dive kick.** The
  remaining unnamed ROM scripts (bar the Demon Flip followups) are mapped:
  close Jab `13a8`, far Strong `1598`, close Fierce `1728`, far Forward `1a38`,
  far Roundhouse `1bf8` (Baston startup/active frame-exact), the five
  `Straight Air` normals, `Forward MP` `1638` (Zugai Hasatsu, two-hit
  overhead) and `Air Down MK` `2aa0` (Tenma Kujin Kyaku, ROM-movement dive).
  Standing normals pick close/far by distance (`CLOSE_NORMAL_RANGE`,
  **provisional** single threshold) and play the extracted close clips
  (`akuma-mpc/hpc/mkc/hkc`); a straight jump uses the neutral scripts.
  Holding forward + MP is now the command normal, as in 3S.
- **Specials are ROM-driven.** The converter now exports each ROM script's
  per-frame `movement` table and its `hit_frames` as `hit_windows`, and the
  Goshoryuken / Tatsumaki pointers are mapped (Baston startup/active
  cross-match, frame-exact): `84f8/85c8/8658` LP/MP/HP DP, `86e8/87f8/8968`
  LK/MK/HK Tatsu, `9618/9738/9818` the air versions. The engine moves these
  states from the ROM table (physics resumes when it ends; the DP then holds
  a landing recovery so the move lasts the Baston total 43/50/59) and looks
  boxes up per strength via `Character.move_variant`.
- **P2 palette**: Player 2's Akuma gets a blue gi (`graphics/palette.py`,
  applied once per cel at sprite load, <1ms). Both fighters used to share the
  identical P1 palette, so a side switch was indistinguishable from a control
  swap. The colour is a PyKuma choice, not a ROM palette dump (**provisional**).
- **F2 world-coordinate grid**: labeled 50/100-px grid drawn into the world
  buffer (zooms with the camera), gold floor/stage-center axes. Gives humans
  a shared address space for positions — "the spark should spawn at x=560,
  y=300" maps 1:1 onto the coordinates the code uses. The frame-data overlay
  toggle moved from F2 to **F6**.
- **Copyable discrepancies**: every `!!` line the F4 meter shows is appended
  as plain text to `bugs/discrepancies.log` (and the console log);
  `PYKUMA_DISCREPANCY_LOG` overrides the path, empty disables.
- **Joystick hot-plug**: JOYDEVICEADDED/REMOVED events trigger an input-system
  rescan, so a fight stick plugged in (or powered on) mid-session connects
  instead of only being detected at launch.
- Bug tickets carry a `resolution` field (closing note) and per-hit
  `move_frame` (which active window a hit landed on).

### Fixed
- **Ground normals no longer slide.** A normal started out of a walk kept its
  walk velocity for the whole move — you could punch while drifting forward or
  back instead of freezing in place. Grounded attack states now zero horizontal
  velocity (air normals keep their jump momentum; moves with built-in travel
  drive velocity from their own ROM table). Regression: `tests/test_movement.py`.
- **Block levels are enforced.** Holding back used to block everything. Guard
  posture is now re-evaluated every frame from the held direction
  (`Character._update_guard`: back = standing, down-back = crouching; none
  while attacking, jumping or in hitstun; still switchable during blockstun)
  and the collision adapter checks the hit's level against it: MID blocked
  either way, HIGH (jump-ins, UOH, air tatsu) only standing, LOW (crouching
  kicks) only crouching. The old flag also went stale while the guarder
  attacked (it "blocked" during its own moves). The CPU now crouch-blocks by
  default and stands against jump-ins/overheads (subject to its reaction delay).
- **Low parry never worked.** A down-forward tap also counted as forward, so
  the high parry window opened first and the low one was refused; and every
  hit reached the parry check tagged MID. The parry now sees the real hit
  level (lows need a down-forward parry) and the two taps are exclusive.
- **Goshoryuken and Tatsumaki did no damage** — they had no ROM pointer
  mapping, so no hitboxes at all (every CPU anti-air DP was a whiff). Now
  1/2/3-hit DPs and multi-hit Tatsus with ROM boxes; damage is the community
  move total split per ROM hit window (**provisional** scale, Baston x7.5).
- **UOH did 0 damage and locked the defender for 61 frames**: it had ROM boxes
  but no combat row, and a 0-hitstun hit never counted down. Added its Baston
  combat row and floored hitstun at 1 frame in `apply_reaction`.
- **Multi-hit moves connected once.** A hit now registers once per ROM hit
  window (cl.HK's two windows, the HP DP's three hits), and frames the ROM
  draws boxes on but registers no hit for (between windows) no longer connect.
- **Hit levels reconciled.** `HitType.HIGH` meant "can be blocked standing" in
  one enum and "must be blocked standing" in the one it maps onto; grounded
  normals were tagged HIGH. All grounded normals are now `MID`, jump-ins and
  the UOH `HIGH` (overhead class), crouching kicks `LOW`. Blocking itself still
  ignores level (holding back blocks everything) — only parry direction reads it.
- **st.HP no longer launches.** Standing heavy punch was tagged `JUGGLE` by
  old gameplay tuning (`tools/framedata/convert_3rd_training.py` COMBAT_MAP);
  in 3S it is a plain hit. Mashing HP produced a launch -> juggle -> knockdown
  -> relaunch loop. Now `NORMAL` (hitboxes.yaml regenerated from the converter).
- **Goshoryuken moon launch.** The DP still launched at the pre-rescale
  vy=-18 after gravity went 0.8 -> 0.34: 467px apex (off-screen), 104 airborne
  frames, then JUMPING's 60-frame safety cap forced STANDING mid-air (floating
  down in the idle pose, able to "walk" in the air), and it inherited walk/dash
  momentum (a dash-cancelled DP crossed the whole stage). The arc is now sized
  to the move's total (**provisional**: 37/42/47 airborne frames from the
  Baston LP/MP/HP totals; forward hop not yet ROM-captured), horizontal
  velocity is zeroed, the DP holds its own state until touchdown, and the clip
  is re-fit to the arc so the Frame Lab doesn't flag it.
- **Jumping over a cornered opponent stole the corner.** The jumper, clamped
  to the wall mid-air (x == wall == defender.x), won the pushbox tie-break on
  landing: the defender was shoved inward and both facings flipped -- with two
  identical Akuma sprites that read as "P1 froze and my controls moved to P2".
  A defender grounded AT the wall now keeps it; the lander is placed on the
  open side (no corner crossup, as in 3S). Off-the-wall crossups still work.
- Block pushback / throw placement write `x` directly while the defender is
  in hitfreeze (no stage clamp runs) -- now clamped to the walls immediately.
- **Frame advantage now measures the community values.** Declared
  hitstun/blockstun were estimates, mutually inconsistent with the ROM
  timeline (s.MK: 16 hitstun in a 23-frame move can only ever yield -3 on
  hit vs the community +1). Hitstun/blockstun are now back-solved from
  community on_hit/on_block against the ROM timing
  (`akuma_hitboxes._calibrated_stun`); the adapter applies declared blockstun
  (the old `max(4, hitstun//2)` derivation survives only as a no-data
  fallback). Grounded normals only; air normals keep the airborne model.
  Pinned by `tests/test_advantage_calibration.py`.
- **Multi-hit moves no longer false-flag recovery/total.** s.HK is two hits
  (active 6-8 and 16-20 in a 39-frame ROM total); the 7 boxes-off frames
  between the windows are now measured and drawn as GAP (ember pips), the
  ROM total is the diffing ruler, and community advantage is only diffed
  when the final window connects. This was the visible
  `!! recovery: observed 26 != expected 19` bug.
- **Animations are ROM-fitted.** The live sprite track (folder clips in
  `Akuma._setup_animations` — `animations.yaml`'s numbered lists are a
  legacy path Akuma doesn't render) ran hand-tuned uniform durations
  (e.g. MK 22 frames vs the 23-frame move, HP 28 vs 38). Attack animations
  now get per-cel holds computed from the ROM totals at registration
  (Bresenham distribution; `create_folder_animation` accepts per-cel
  durations). `tools/framelab/audit_animations.py` audits the LIVE
  controller and reports zero findings.
- **Hitstop freezes the sprite too.** Animations advanced during hit freeze
  while mechanics paused, desyncing cels from frame data by the freeze
  length on every connect (and not matching 3S's held impact pose).
- Frame Lab animation-completion measurement had an off-by-one (playback
  raises is_finished during the final played frame, not after it).
- All seven open Frame Lab tickets closed with resolution notes (advantage
  on hit for s.HK/s.MK/cr.MP; sprite timing for s.MK/s.HP/cr.MP; sprite
  sync for cr.MP).


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
- **Combat runs on the ROM's own scale now.** Two live Fightcade captures
  (Akuma vs Akuma; session 1 the ground normals, session 2 the specials /
  neutral-jump normals / demon flip), merged by `ingest.py merge-combat`
  (**30 mapped moves**; per-session raws vendored under
  `data/characters/akuma/rom_combat_sessions/`), confirmed the arcade life bar
  is 0xA0 = **160** for everyone and that our stored damage was a x7.5 inflation
  of the real values. Akuma's `max_health` is now 160; the captured moves use
  their exact ROM damage / stun / hitstun (st.MP 20 dmg / 15 hitstun, cr.HK 22 /
  60-frame knockdown, heavies 24; LP DP one 23-dmg hit, HP DP three hits, tatsu
  106-frame knockdown); every other move's community damage is divided by the
  7.5 anchor to recover the raw (== ROM) value on the same bar (throw 19,
  fireball 17, SA2 66, KKZ 107, Raging Demon 87). The Frame Lab tags captured
  moves `verified` and stops diffing their damage / hitstun / advantage against
  the community tier. Not captured yet (stay calibrated community): the on-block
  pass (blockstun/chip), the air tatsus, ground HK tatsu, f+MP, UOH, the dive
  kick, a few jump normals, throws and supers. Multi-hit hitstun (e.g. s.HK's
  first window) is a single-sample estimate pending more captures
  (`tools/rom_extract/CAPTURE.md`).
- **Community tier regenerated from Baston (revised) at one scale.** The
  damage/stun/advantage rows were "Baston + tuning" on no fixed scale (st.LP
  was 20x its Baston number, st.HP 7.5x) and many advantages disagreed with
  Baston (st.HP +1/-2 vs -4/-6, cr.HK -2/-5 vs knockdown/-15). The three
  Baston tables are vendored (`data/sources/baston/`) and
  `tools/framedata/baston_to_community.py` regenerates the yaml from them:
  damage x7.5 anchored on st. Fierce 24 -> 180 (**provisional** absolute
  scale), stun and advantage verbatim, a `baston:` provenance line per move.
  Jabs now do ~2% (22) instead of 5.7%; hitstun/blockstun follow the new
  advantages. Throw, fireball and super-art damage now read the yaml
  (`data/community.py`) instead of hard-coded constants (throw 180 -> 142,
  fireballs 60/70/80 -> 128, SA2 180 -> 495, KKZ 220 -> 802, Raging Demon
  500 -> 652). SA2's yaml key `tensho_kaireki_jin` renamed `messatsu_gou_shoryu`.
- **Dead code and stale docs removed** (git history keeps them): the four
  import-broken `scripts/demo_*.py` + two superseded demos, `debug_hitbox.py`,
  `joystick_test.py`; the never-wired `characters/ken.py` / `shoto_base.py`; the
  orphaned `graphics/sprite_manager.py` (`SF3SpriteManager`) and its test; the
  one-shot `tools/sprite_extraction/*.py` scrapers and `tools/extract_*.py`;
  13 docs that contradicted the code (old roadmaps, PROJECT_STRUCTURE,
  IMPLEMENTATION_GUIDE, BLOCKING plan, TESTING_GUIDE, AKUMA_FRAME_DATA, phase
  notes, RUN_DEMOS). `docs/ROADMAP.md` is now a short current-status page.
- Renamed: `scripts/audit_animations.py` → `animation_contact_sheets.py`
  (no longer collides with `tools/framelab/audit_animations.py`; stale sprite
  paths fixed), `scripts/test_hud_visual.py` → `hud_visual_preview.py`,
  `tools/test_joystick.py` → `joystick_probe.py` (no `test_*.py` outside
  `tests/`).
- CI byte-compiles `src scripts tools tests` so broken imports can't rot unnoticed.
- `uv run sf3-dev` works again (it passed a `--dev` flag that didn't exist).
- Provenance tier `baston` documented in the yaml banner and ARCHITECTURE.
- **Main menu trimmed**: MODE SELECT and MOVES LIST are gone (each entry
  already starts its own mode; the special-move inputs live on CONTROLS), and
  the "Current Mode" indicator with them.
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
- Tatsumaki has no hitbox data and Demon Flip lacks ROM arc data + Hyakki Go
  follow-ups (those manual tickets were superseded by newer F9 tickets; the
  underlying work — ROM records for the specials — remains open).
- ~~Animation drift / advantage deviation~~ fixed: animations are ROM-fitted
  at registration and hitstun/blockstun are calibrated from community
  advantage; `python tools/framelab/audit_animations.py` reports zero
  findings on the live sprite track.

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
