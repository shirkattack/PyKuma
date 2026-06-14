# PyKuma Controls

Directions are **facing-relative**: "forward" = toward the opponent. Akuma faces right as P1, so
forward = right; the input layer mirrors automatically when facing left.

## Keyboard

| Action | Player 1 | Player 2 |
|---|---|---|
| Up / Down / Left / Right | `W` / `S` / `A` / `D` | `↑` / `↓` / `←` / `→` |
| Light / Medium / Heavy Punch | `J` / `K` / `L` | `KP1` / `KP2` / `KP3` |
| Light / Medium / Heavy Kick | `U` / `I` / `O` | `KP4` / `KP5` / `KP6` |

Keyboard reads each direction key independently, so diagonals (e.g. down+forward, up+forward) work
by holding two keys.

## Gamepad / controller

All three direction sources are read **and OR-combined** every frame, so diagonals register no matter
how your pad reports directions:
- **Analog stick** (axes 0/1), deadzone `0.3` — push past ~1/3 to register; a true diagonal sets
  both axes.
- **D-pad / hat** (hat 0) — diagonals set both hat axes.
- **Leverless / hitbox** direction buttons (buttons 6–17 → up/down/left/right).

Because the sources are combined (not "buttons else stick"), mixed setups still produce diagonals.
This is what makes **jump-forward / jump-back** and the **down-forward of a fireball** work on a pad.
(Tuning lives in `systems/input_system.py`: `joystick_deadzone`, `_read_joystick_direction`.)

> Button→action mapping for a specific controller may need per-pad calibration; see
> `scripts/joystick_test.py` to discover your pad's button numbers.

## Special-move motions

Motions are buffered and matched within `MOTION_INPUT_WINDOW = 16` frames (~0.27s @ 60fps), defined
in `data/constants.py`. Definitions in `systems/input_system.py:_setup_motion_inputs`.

| Move | Motion | Buttons |
|---|---|---|
| Gohadoken (fireball) | QCF — down → down-forward → forward | any Punch |
| Goshoryuken (DP) | DP — forward → down → down-forward | any Punch |
| Tatsumaki (hurricane) | QCB — down → down-back → back | any Kick |

Tips: a motion needs its diagonal frame (e.g. QCF must pass through **down-forward**); on keyboard
hold the two keys briefly so the diagonal is captured. Specials are checked **before** normals, so a
completed motion takes priority over the raw punch/kick.
