# Phase A — Integration Roadmap

Phase A delivered **catalogs + tooling + cleanup only** (see `docs/ASSET_LAYOUT.md`
and `docs/asset_catalog/`). No gameplay/VFX/screen code changed. This doc maps each
cataloged asset set to the phase that will use it, and records the per-set findings.

Catalogs produced:
- `docs/asset_catalog/AKUMA_REACTIONS.md` — 15 reaction/block/throw folders (self-labeled via description.txt)
- `docs/asset_catalog/DUDLEY.md` — Dudley 04993–06115, 8 candidate-animation segments
- `docs/asset_catalog/EFFECTS.md` — 10 effect categories, 37 gap-split sequences
- `docs/asset_catalog/SELECT.md` — select-screen portraits + chrome

---

## NEXT PHASE → Hit-reaction system (user-prioritized)

Goal: distinct reactions per hit (high/low/crumble/launch/knockdown) + block feedback,
replacing the single `HITSTUN_STANDING` pose.

**Prerequisite (blocker):** the animation-controller consolidation. The game currently
renders the folder sprites via the crude `_render_sf3_sprites` global-timer path, which
loops every clip and can't play a one-shot knockdown-then-getup. Hit reactions need
proper one-shot, state-driven playback (per-animation durations, loop flags, completion)
— i.e. route the folder sprites through `AnimationController`.

**Reaction → animation mapping** (assets confirmed present, from AKUMA_REACTIONS.md):

| Reaction | Source folder | Notes |
|---|---|---|
| standing hit (high/mid) | `akuma-stand-hit` (50f) | multi-reaction — split (below) |
| crouching/low hit | `akuma-crouch-hit` (11f) | "Crouching Hitstun" |
| crumble / dizzy | `akuma-shocked` (3f) | "Stun State" — short; may need a slow-collapse compose |
| launch (juggle) | `akuma-twist` (27f) | "Spinning Knockdown" — airborne spin |
| knockdown | `akuma-slam` (25f) | "Knockdown. Being slammed to the ground" |
| chip KO | `akuma-chipdeath` (17f) | |
| block (stand/crouch) | `akuma-block-high` (6f) / `akuma-block-crouch` (5f) | block, not a hit |
| parry | `akuma-parry` (5f) / `akuma-parry-low` (4f) | already partly wired |
| throws | `akuma-throw-forward/back/miss` (17/14/6f), `akuma-airthrow` (52f) | later |

**Proposed `akuma-stand-hit` split** (50 frames; *proposed, verify in-engine* — the folder
is one "Standing Hit Stun" clip containing several intensities + a fall):
- `hit_light`  ≈ frames 0–7 (quick flinch → neutral)
- `hit_medium` ≈ frames 8–17
- `hit_heavy`  ≈ frames 18–31 (deep stagger)
- `knockdown_fall` ≈ frames 42–49 (collapses to ground)
- 32–41 read as recovery/transition between stagger and fall.

**State machine work:** add `CharacterState.CRUMBLE` and `CharacterState.LAUNCH`
(`KNOCKDOWN`, `HITSTUN_STANDING/CROUCHING/AIRBORNE`, `BLOCKSTUN_*` already exist); map each
to its animation in `Akuma._transition_to_state`; in
`systems/sf3_collision_adapter.py:_apply_hit_to_character`, choose the reaction from the
attack's reaction-type + defender state instead of always `HITSTUN_STANDING`.

**VFX fix this phase needs (from EFFECTS.md):** `spawn_hit_spark` is called with
`"normal"` / `"block"` / `"parry"` (`sf3_collision_adapter.py:579/604/630`) but `HitSparkType`
only defines `light/medium/heavy/special` → all fall back to LIGHT. Add/remap those types
and pick spark by hit strength. Confirmed spark sequences: light `29361–29369`,
medium `29383–29388`, special `29846–29854`, heavy `30102–30141` (**note:** `vfx.py`
currently caps heavy at 30122 — extend to 30141). A distinct **block spark** sequence
should be chosen from the catalog for block feedback.

---

## Deferred phases

### Effects → VFXManager expansion
`EFFECTS.md` catalogs 37 sequences across 10 categories; only 4 hitspark ranges are wired
in `systems/vfx.py`. Work: generalize VFX loading to any category, per-strength hit sparks,
block/parry sparks, route `fireballs`/`superart`/`ground`/`shadow`/`dizzies`. Projectiles
(`core/projectile.py`) currently use Akuma sprite-sheet IDs, not the `fireballs` category —
could migrate. The hit-reaction phase does the minimal spark-type fix above; full breadth here.

### Character select → screen revival
`SELECT.md` indexes portraits `1.gif`–`20.gif` + nameplates `n1`–`n20` + chrome. The old
`attic/ui/character_select.py` is stale (imports deleted modules) — rewrite against current
`systems/`. Needs: a real **character registry** in `src/` (none today), and `core/game.py`
to accept a chosen character instead of hardcoding `Akuma` (`game.py:78-82`), plus menu→select
wiring (`MenuState.CHARACTER_SELECT` exists, unused).

### Dudley → 2nd playable character
`DUDLEY.md` shows 1103 frames in 8 candidate-animation segments (all flagged for transparent
frames to review). Work: name the segments → `characters/dudley.py` (mirror `akuma.py`) +
its own `animations.yaml` block. **Dudley needs its own `sprite_scale`/`feet_offset`** —
Akuma's (`feet_offset=86`, scale 2.0) are tuned to Akuma's canvas sizes; not drop-in.
Depends on the character registry from the select-screen phase.

---

## Phase A boundary

Done in Phase A: generalized `scripts/audit_animations.py`, asset cleanup (Dudley extracted,
3 redundant zips removed, catalog images gitignored), `docs/ASSET_LAYOUT.md`, the four
catalogs, and this roadmap. **Not** done (deferred as above): any `src/` code, new
`CharacterState`s, VFX/animation-controller changes, character registry, select-screen code,
`characters/dudley.py`, or `animations.yaml` edits.
