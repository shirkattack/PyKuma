# PyKuma Architecture

One page on which module is the canonical implementation of each concern.
If you (or your AI assistant) are wondering "which of these files is real?" —
this is the answer. Everything else of historical interest lives in `attic/`.

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
│   └── projectile.py     # Gohadoken etc.
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
- **Reset contract.** Every round starts from a clean slate:
  `Character.reset()`, `InputSystem.reset()`, `VFXManager.clear()`,
  `SF3CollisionAdapter.reset()`. If you add a stateful system, give it a
  `reset()` and call it from `Game._reset_round_state()`.

## The attic

`attic/` holds parallel implementations that are **not** imported by the live
game: the legacy `CollisionSystem`, the alternate `SF3InputSystem`,
keyboard_input, the `SF3AnimationController` stack, the
`SF3GameManager`/character-select/training-mode experimental stack, and the
alternate visual effects manager. They are kept for reference only; don't
import them from `src/`. (Git remembers everything if you want to delete it.)

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
