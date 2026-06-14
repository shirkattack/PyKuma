# Debug Backlog

Reported issues, their status, and which phase they belong to. See
`docs/phases/PHASE_A_INTEGRATION_ROADMAP.md` for the phase definitions.

## Fixed

- **Attacking hand drawn behind opponent's back** — render z-order. The attacker's
  sprite is now drawn on top when exactly one player is attacking
  (`core/game.py` `_render_fight`, `Character.is_attacking()`).
  *Note:* this is a per-character heuristic; true per-limb depth would need the
  hit-reaction/animation work. Good enough for the reported case.
- **`STATE TIMEOUT: CROUCH_HEAVY_PUNCH/…` spam** — crouch & jump attacks lingered
  to the 30–50f safety timeout because animation-completion is only checked on the
  non-simple sprite path (the game runs `use_sf3_sprites=True`). Interim fix: they
  now recover in `Character._update_state` (crouch attacks → CROUCHING, jump attacks
  → STANDING at 20f). **Proper per-move timing is deferred to the animation-controller
  consolidation** (the hit-reaction prerequisite).
- **Menu grey-out mechanism** — `MenuItem(available=…)`; locked items are skipped in
  navigation, no-op on select, and rendered greyed with a `(soon)` suffix
  (`core/main_menu.py`). Currently locked: **VERSUS** and **DEMO** modes (no CPU AI /
  no distinct flow yet). Flip `available=True` as each ships.
- **Menu didn't launch START/TRAINING/DEV ("nothing happens")** — root cause: the
  menu-flow `run_game_loop(...)` call (`main_with_menu.py:243`) was missing the `clock`
  arg after `window` was added, so every menu selection raised a `TypeError` that
  `main()`'s broad `try/except` swallowed (app just exited). Fixed by passing `clock`.
  (`sf3-training`/`sf3-dev` use `--no-menu`, hitting the correct call, which is why they
  worked directly.) Side note: this is the swallow-everything antipattern from the
  original review §2.4 — `main()`'s catch hid the real error; worth narrowing later.

## Tied to later phases

- **Distinct hit reactions** (high/low/crumble/launch/knockdown) + **block feedback**
  + **hit/block sparks** → hit-reaction phase (next). Prereq: animation-controller
  consolidation (also fixes the crouch/jump timing properly).
- **Character select** (un-grey nothing here yet) → select-screen phase: needs a
  character registry + Game accepting a chosen character.
