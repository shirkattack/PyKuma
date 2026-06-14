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

**PRIME DIRECTIVE: we do NOT make up hitbox/frame data. Every value must be
referenced from the game (Baston/esn3s).** This is enforced in code, not just by
convention — see the five enforcement points below.

- **Canonical source of truth:** `data/characters/<char>/frames.yaml` (one file per
  character), loaded and validated through `schemas/sf3_schemas.py:CharacterFrames`
  by `data/frame_data_loader.py`. The collision adapter reads **only** the loader
  (`get_hitboxes` / `get_hurtboxes` / `get_move_frame_data`).
- **Provenance is mandatory.** Every move declares `provenance.status` —
  `verified` (transcribed from Baston), `unverified` (hand-authored placeholder), or
  `derived` (computed from a verified move). The field has no default; a move cannot
  be defined without it.
- **Enforcement (5 points):** (1) the required `provenance` schema field; (2) the
  loader's boot-time `VERIFIED/UNVERIFIED` log; (3) `tests/test_data_provenance.py`,
  which fails on any unverified move not in its shrinking `UNVERIFIED_BACKLOG`;
  (4) the hitbox viewer shows each move's tag on screen; (5) quarantined fabricated
  files live in `attic/` so nothing reads them by accident.
- **Pipeline:** real numbers come from Baston via `scripts/baston_to_yaml.py`
  (Phase 3), then get visually confirmed in the hitbox viewer before flipping to
  `verified`.

Quarantined (do not use): `attic/data/akuma_hitboxes.py` and
`attic/data/characters/akuma/sf3_authentic_frame_data.yaml` were hand-approximated
placeholders. `data/frame_data.py` still defines shared dataclasses (`MoveData` used
by `characters/character.py`) and `data/animations.yaml` holds animation timing —
neither is a hitbox source.
