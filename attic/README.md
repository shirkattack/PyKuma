# Attic

Dead parallel implementations moved out of `src/` so contributors don't have
to reverse-engineer which stack is live. See `ARCHITECTURE.md` at the repo
root for the canonical module per concern.

Nothing in here is imported by the live game or the test suite. Kept for
reference while the SF3 stack matures; safe to delete (git remembers).

| Module | Superseded by |
|---|---|
| `systems/collision.py` (legacy CollisionSystem) | `systems/sf3_collision_adapter.py` |
| `systems/sf3_input.py` | `systems/input_system.py` |
| `input/keyboard_input.py` | `systems/input_system.py` |
| `graphics/animation_system.py` | `systems/animation.py` |
| `sprite_integration.py` | `graphics/sprite_manager.py` |
| `integration/` (SF3GameManager stack) | `core/game.py` |
| `modes/training_mode.py` | `core/game_modes.py` training mode |
| `ui/character_select.py` | not yet replaced (single-character game) |
| `effects/visual_effects.py` | `systems/vfx.py` |
| `gameplay/character_controller.py` | `characters/character.py` |
