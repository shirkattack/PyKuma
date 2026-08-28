# Plan of attack — after the ROM sprite pipeline (2026-08-27)

The game now draws Akuma from the ROM's own cels, placed by the ROM's axis
offsets and timed by the ROM's cel holds (44 clips live; `tools/rom_extract/
README.md`). This plan orders the remaining bugs by leverage: a few single
root causes sit behind most of the Frame Lab warnings, and several "missing
features" (throws, supers, follow-up animations) are already *described* by the
frame dumps — they need wiring, not research.

Effort: **S** < half a day, **M** a day, **L** several days. "Test" is the
regression pin each fix lands with.

## Phase 0 — quick wins (all S) — **done 2026-08-27 except 0.6 (needs the top-up rip)**

| # | Symptom | Root cause (verified) | Fix | Files | Test |
|---|---|---|---|---|---|
| 0.1 | Walking: Akuma turns backwards on `cel_21525..21527` | Those cels (5 in all: `cels.json` `flip: 0`) were ripped while P1 faced **left**; the decoder stored them as drawn (mirrored), the engine mirrors again | `cel_decode.py --p1`: when `p1.flip` says left, mirror the PNG and negate the bbox (`left' = -(left+width)`); `--redo` the 5 cels; rebuild tables | `tools/rom_extract/cel_decode.py`, `build_rom_animations.py` | decoder test: a left-facing dump renders identically to a right-facing one |
| 0.2 | Frame Lab `sprite_mapping observed=far_heavy_punch expected=heavy_punch` (and `medium_goshoryuken`, `heavy_tatsumaki`, `neutral_jump_light_kick`) | `frame_lab._expected_anim_for` reads `_STATE_ANIM` and doesn't know the ROM variant clips | expected = `resolve_variant_anim(base, variant, rom_names, all_names)` | `core/frame_lab.py` | frame-lab test: a far HP with the ROM clip raises no mapping flag |
| 0.3 | P2 changes colour when hit | ROM cels use the ROM P2 palette (white gi); the hit-reaction folder clips still use the old HSV blue-gi rule | folder-clip recolour = nearest P1-ROM-palette colour → P2 pen (`rom_palettes.json`), so both sources agree; goes away entirely with Phase 6 | `graphics/palette.py` | palette test: zweifuss gi colour maps to the ROM P2 gi |
| 0.4 | `STATE TIMEOUT: JUMP_LIGHT_KICK exceeded 30 frames` | jump normals have a 30-frame cap but last until landing | jump-normal states end on landing (no timeout while airborne) | `characters/character.py` (`max_state_frames`), akuma `_update_state` | scenario: late-in-jump normal lands cleanly |
| 0.5 | Air fireball uses the ground clip | ROM air Gohadoken anim is `a130` (airborne, then `7684`); engine has no air variant | build tool role `air_gohadoken` (+ `7684` tail); engine plays variant `air` for GOHADOKEN when `pending_projectile_air` | `build_rom_animations.py`, `characters/akuma.py` | frame info shows `rom_cels` of `a130` during an air fireball |
| 0.6 | Close normals / tatsu still on folder clips | 1–3 hit-branch cels missing (`13a8 14e8 1728 1988 1b08`, cel `22216`) | the top-up rip (dummy `stand`, let them **hit**) + `cel_decode --p1` + rebuild | — (data) | `rom_animations.json` complete count 47 → 53 |

## Phase 1 — combat correctness: multi-hit windows — **done 2026-08-27**

Warnings: `HEAVY_KICK damage observed=12 expected=21 / hitstun 19 vs 35`,
`GOSHORYUKEN damage 8 vs 17`, `TATSUMAKI damage 3-5 vs 16`.

**What it actually was** (the plan's off-by-one hypothesis was wrong; the
repro showed cl.HK applying 21/35 then 12/19 — the ROM's own per-window
values):

1. The Frame Lab diffed *every* hit of a move against the **first** window's
   expected values, so the second hit of any multi-hit move was flagged.
   Fixed: hit events carry their ROM window and `Expected.rom_hits` holds the
   per-window values; each hit is diffed against its own window.
2. The combo system stepped the damage scaling down for every window of the
   same move (12 → 10, 8 → 7). The captured per-window values already are
   what the game applied inside that move, so scaling is now anchored at a
   move's first hit (`register_hit(same_move=True)` from the collision
   system); only a new move steps it down.

Test: `tests/test_multihit_windows.py` (cl.HK windows 21/35 then 12/19,
scaled 21/12; scaling anchor unit test).

## Phase 2 — move chains: follow-up animations from the dumps (M)

Warnings: `GOSHORYUKEN sprite_timing observed=19 expected=50 (held its last
cel)`, `JUMP_MEDIUM_PUNCH recovery/total/sprite_timing`.

The ROM ends a script and hands off to another anim id; the dumps record every
hand-off (`c1.anim` transitions):

| move | chain in the ROM |
|---|---|
| LP DP `84f8` | → `6a2c` (fall/land, 3 cels) |
| MP/HP DP `85c8`/`8658` | → `84f8` (shared rise/fall tail) → `6a2c` |
| ground tatsu `86e8`/`87f8`/`8968`, air tatsu `9618`… | → `645c` (landing recovery, 4 cels) |
| jump normals `22a8`, `2b30`, … | → `5c7c` (landing, 3 cels) |
| jumps `8f20`/`8e20`/`9030` | → `5b7c` (landing) or the jump normal |
| air fireball `a130` | → `7684` |

- `build_rom_animations.py`: record `next` per anim (from the transition table) and emit **chained clips** (`sequence` = own script + tail anims), so a DP clip covers rise + fall + landing and the state's full duration.
- Engine: `CelAnimation` chains are just longer sequences; the state machine's
  `_move_total` / landing logic then matches the clip. Jump normals: end the
  state at the ROM landing (Phase 0.4) so `total` matches the script + `5c7c`.
- Jump physics: verify the engine's arc uses `physics.yaml` (ROM airborne frames / apex) so the jump normals' observed totals (15–19) approach the script totals (31) for the same reason.
- Test: frame-lab audit clean for DP (all strengths) and one jump normal.

## Phase 3 — corner cross-up jitter/freeze (M)

Repro: P1 jumps over a cornered P2 with a special (air tatsu / demon flip);
P2 jitters and freezes. Likely the wall clamp (`character.py` `STAGE_*_BOUND`)
and pushbox separation (`sf3_collision_adapter`) alternate every frame when
both fighters are against the wall and the attacker is airborne behind the
defender, and the freeze is the side-switch guard refusing to flip facing while
overlapped.

- Write the repro as a `tools/diagnostics/scenario.py` script first (it becomes the test).
- Fix: resolve pushbox overlap by moving the **un-cornered** fighter only; allow the air side switch; never clamp past the wall twice in one frame.
- Test: scenario asserts no per-frame x oscillation > 1 px and both facings settle within N frames.

## Phase 4 — throws (M–L)

Nothing is wired; the ROM data is mostly captured:

- Chains from the dumps: `3768` (grab attempt, 3 f) → `d8d4` (forward throw, 11 cels) or `d524` (back throw); whiff → `645c`. The thrown opponent's anims are `e7f0`/`ea48` (P2 side of the dumps); those cels still need ripping (add a `throw` mode to the P2 auto-attack so P1 gets thrown).
- Range: the ROM catch/caught boxes are in `cps3_akuma_chardata.json` (`cata`/`caua`) and the throwbox in `hitboxes.yaml`.
- Damage: `rom_combat.json` `3768` shows 0 `dm_vital` — throw damage lands after the settle window; re-capture with a longer settle for the grab or read it from `d8d4`'s connect.
- Engine: THROWING state → grab check on frame 3 using the ROM boxes → success plays `d8d4`/`d524` on P1 and the thrown anim on P2 with the ROM's relative positioning (the P2 object's offset during the throw is in the dumps too), else `645c`.

## Phase 5 — supers (L)

- Identify ids with a **labelled capture**: run `dump_framedata.lua`, perform SA1, SA2, SA3, Raging Demon in that order with 3 s pauses (the frame counter labels them). Current evidence: `68cc` = SA1 (multi-hit, 162 f), `7754` → `8af8` = Raging Demon (105-frame freeze), `e1d4` (16 cels, rises 40 px) probably SA3 Kongou Kokuretsu Zan, `7cf4`/`7bc4` candidates for SA2.
- Rip cels with each SA selected (three short sessions; the manifest accumulates).
- Engine: super freeze (the ROM's own freeze count from the capture), meter cost/stocks, SA1 projectile, SA3 ground quake hit, RD grab; hitboxes from `hitboxes.yaml` once the ids are in `move_names.json`.

## Phase 6 — reactions from the ROM (M)

- Rip P1's reaction cels with the P2 auto-attack (`jab` / `hk` / `sweep`, standing and crouching): stand reels light/medium/heavy, crouch reels, launch, lying, wake-up, dizzy.
- Map reel ids by strength/height from the dumps (`a26c a2ec a38c a88c a91c …`; the dummy's reel per attacking move is recorded).
- Replace the last folder clips (`hit_medium`, `crouch_hit`, `knockdown`, `launch_spin`) → uniform ROM look, and Phase 0.3 becomes moot.

## Phase 7 — hit effects (L)

Ground/damage effects are separate sprite objects in the ROM; the cel ripper already sees them (the white swoosh that briefly polluted `b118`).

- `dump_cels.lua`: on each connect (defender `hits_received` / `conn_marker` rises) dump **all** objects for a few frames; `cel_decode.py --effects` renders objects that are not a player, keyed by (tile, palette), with their offset from the **defender's** axis.
- Catalogue: hit sparks (light/medium/heavy, block spark, parry flash), dust (landing, dash, wake-up), KO/dizzy stars.
- Engine: an effect layer (`assets/vfx/` is the fallback) spawned at the ROM offset on hit/block/land/dash, ROM-timed.

## Phase 8 — native-resolution view (M)

CPS3 is **384×224**. The world buffer is already composed at native scale
(`SCREEN_WIDTH 896`, dynamic zoom 0.7–1.0 of a crop). A "CPS3 view" mode:

- a fixed 384×224 viewport at 1:1 world units, scrolled by the ROM camera rule (follow the midpoint, clamp to the stage), integer-upscaled ×2/×3 to the window; no zoom.
- stage art at native size: the ROM's stage tilemaps can be ripped the same way as the cels (tilemap RAM + tiles); interim: downscale the izakaya background to 2 screens wide.
- HUD re-laid out for 384 px.

## Order

0 → 1 → 2 → 3 (all gameplay-visible now), then 6 (needs a rip session), 4, 5 (need labelled captures), 7, 8. The top-up rip (0.6) and the reaction rip (6) can be one Fightcade session.
