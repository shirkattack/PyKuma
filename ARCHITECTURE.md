# PyKuma Architecture

One page on which module is the canonical implementation of each concern.
If you (or your AI assistant) are wondering "which of these files is real?" —
this is the answer. Superseded implementations were removed from the tree;
git history remembers them (see "The attic", below).

## The live game

```
src/street_fighter_3rd/
├── main.py               # Entry point: quick play (no menu, no rounds)
├── main_with_menu.py     # Entry point: menu + normal/training/dev modes
├── core/
│   ├── game.py           # Game loop owner: update order, round flow, HUD
│   ├── round_manager.py  # Round/timer/win state machine
│   ├── game_modes.py     # Mode config (training, dev, no-rounds)
│   ├── main_menu.py      # Menu for main_with_menu
│   ├── projectile.py     # Gohadoken etc.
│   ├── diagnostics.py    # Invariant checks + per-frame session recorder
│   └── frame_lab.py      # Frame meter + measured-vs-declared diffing (F4/F9)
├── characters/
│   ├── character.py      # Base: state machine, physics, reset() contract
│   └── akuma.py          # The one playable character
├── systems/
│   ├── input_system.py   # CANONICAL input: buffer, motions, joystick
│   ├── sf3_collision_adapter.py  # CANONICAL collision: bridges Characters
│   │                     #   to the SF3 core (tick() once per frame!)
│   ├── sf3_collision.py  # SF3 32-slot hit queue (used via the adapter)
│   ├── sf3_core.py       # SF3 WORK/PLW structures, state hierarchy
│   ├── sf3_hitboxes.py   # SF3 hitbox types
│   ├── sf3_parry.py      # Parry system (live: wired via the adapter)
│   ├── sf3_combo_system.py  # Combo scaling
│   ├── animation.py      # CANONICAL animation + sprite cache
│   ├── animation_loader.py  # YAML animation loading
│   ├── hitbox_data.py    # Shared HitboxData record
│   └── vfx.py            # CANONICAL VFX (hit sparks)
├── graphics/sprite_manager.py  # Alternate sprite loader used by akuma.py
└── data/                 # Constants, enums, frame data, YAML
```

## Engine model

- **Fixed timestep.** One `Game.update()` call is one game frame at 60 FPS.
  There is no delta-time anywhere; do not add one. This keeps the simulation
  deterministic, which is the foundation for replays/netcode later.
- **Frame order per fight frame:** facing → input → parry windows →
  character updates → `collision.tick()` → collision checks (P1→P2, P2→P1)
  → VFX.
- **ROM-driven durations.** Normals (+ Universal Overhead) end at the
  ROM-verified total via `Character._move_total_frames()` (Akuma overrides it
  with the hitbox-repository lookup). Animations FILL that window — they never
  define it: `Akuma._setup_animations` computes per-cel holds FROM the ROM
  totals at registration (the folder clips there are the live sprite track;
  `animations.yaml`'s numbered lists are a legacy path Akuma doesn't render).
  Specials remain animation-driven until they get ROM records.
- **Calibrated combat values.** Per-move hitstun/blockstun are back-solved
  from the community on_hit/on_block against the ROM timeline
  (`akuma_hitboxes._calibrated_stun`) — advantage is what the community
  actually documents, so it is the source of truth; grounded normals only.
- **Reset contract.** Every round starts from a clean slate:
  `Character.reset()`, `InputSystem.reset()`, `VFXManager.clear()`,
  `SF3CollisionAdapter.reset()`. If you add a stateful system, give it a
  `reset()` and call it from `Game._reset_round_state()`.

## The attic

The `attic/` directory has been deleted from the working tree; git history
holds the parallel implementations that were **not** imported by the live
game: the legacy `CollisionSystem`, the alternate `SF3InputSystem`,
keyboard_input, the `SF3AnimationController` stack, the
`SF3GameManager`/character-select/training-mode experimental stack, and the
alternate visual effects manager. They were kept only for reference and have since been removed; recover them
from git history if ever needed. Don't reintroduce imports of them in `src/`.

Characters `ken.py` / `shoto_base.py` remain in `src/` but are **experimental**:
nothing constructs Ken yet; both players are Akuma (`core/game.py`).

## Frame data — canonical source & the no-made-up-data rule

**PRIME DIRECTIVE: we do NOT make up hitbox/frame data.** Box geometry and timing are
ROM-accurate, dumped from the SF3:3S ROM; every box/move is tagged with its provenance
tier so nothing fabricated can pass as real.

- **Vendored source:** `data/sources/gouki_framedata.json` — per-frame box geometry
  (attack / vulnerability / push / throwable) dumped from the `sfiii3nr1` ROM by the
  [3rd_training_lua](https://github.com/Grouflon/3rd_training_lua) project. Full
  attribution in `data/sources/SOURCE.txt`.
- **Converter:** `tools/framedata/convert_3rd_training.py` reads that JSON, applies the
  PyKuma coordinate transform, and emits `data/characters/akuma/hitboxes.yaml`. It
  self-checks the idle base boxes and refuses to run if they don't match the source.
  Regenerate from source; do not hand-edit the output.
- **Runtime:** `data/hitbox_repository.py:HitboxRepository` loads `hitboxes.yaml`; the
  collision adapter and the hitbox viewer (`core/hitbox_viewer.py`) read it.
- **Provenance tiers** (each box/move is tagged): `verified` = box geometry + frame
  timing from the ROM dump; `inferred` = the ROM-pointer→`CharacterState` *name*
  assignment (geometry is ROM-verified, the name is a guess, see
  `data/characters/akuma/move_names.json`); `community` = damage / stun / frame
  advantage from Baston ESN3S tuning in `data/characters/akuma/sf3_authentic_frame_data.yaml`
  (NOT ROM-verified). Enforced by `tests/test_hitbox_provenance.py`.
- **Verification:** the hitbox viewer (`--hitbox-viewer`) draws non-`verified` boxes
  **dashed** so they're never mistaken for ROM-accurate geometry.

`data/frame_data.py` still defines shared dataclasses (`MoveData` used by
`characters/character.py`); `data/animations.yaml` holds animation timing — neither is a
hitbox source.

## Frame Lab (debugging system)

The bridge between human perception ("the HP does too much damage") and a
machine-actionable claim (`channel=damage observed=200 expected=180`). The
frame number is the shared address space. See `docs/FRAME_LAB.md`.

- `core/frame_lab.py` — live per-frame phase classification (reads the SAME
  `state_frame + 1` indexing the collision adapter uses), move measurement
  with hitstop excluded, expected-vs-actual diffing against the provenance
  tiers above, sprite-track capture (anim/cel/fallback per frame), and the
  SF6-style meter (F4).
- `schemas/bug_ticket.py` — the Pydantic ticket format written to `bugs/`
  (F9): one dimensioned claim per move per channel, with provenance-aware
  `fix_hints`. `bugs/README.md` is the consumption contract for AI assistants.
- `tools/framelab/audit_animations.py` — static cross-check of the sprite
  track (`data/animations.yaml`) against the ROM repository; flags missing
  animations, anim-length vs ROM-total drift, and any reintroduced embedded
  frame_data/hitbox blocks (`data_drift`).
- `data/animations.yaml` is **presentation-only** (sprites, durations,
  offsets). Its legacy embedded frame_data/hitbox blocks were removed after
  verifying nothing reads them; the ROM repository stays the sole timing and
  geometry source of record.
