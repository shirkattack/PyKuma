"""Controller-input regression tests: gamepad diagonals + fireball motion.

Covers two reported bugs:
  A) "jump + forward/back" not registering on a gamepad (diagonals dropped).
  B) Akuma's fireball (QCF+P) never coming out (down-forward missing from the buffer).

The joystick is stubbed so these run headlessly with no real controller.
"""

import pygame
import pytest

from street_fighter_3rd.systems.input_system import PlayerInput, InputState
from street_fighter_3rd.data.enums import InputDirection, Button, CharacterState
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.characters.akuma import Akuma


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    yield
    pygame.quit()


class StubJoystick:
    """Minimal pygame-joystick stand-in for _read_joystick_direction."""

    def __init__(self, axes=(0.0, 0.0), hat=(0, 0), buttons=()):
        self._axes = axes
        self._hat = hat
        self._buttons = set(buttons)

    def get_numbuttons(self):
        return 18

    def get_button(self, i):
        return i in self._buttons

    def get_numaxes(self):
        return 2

    def get_axis(self, i):
        return self._axes[i]

    def get_numhats(self):
        return 1

    def get_hat(self, i):
        return self._hat


def _dir(**kw):
    p = PlayerInput(1)
    p.joystick = StubJoystick(**kw)
    return p._read_joystick_direction(facing_right=True)


# --- Bug A: gamepad diagonals -------------------------------------------------

def test_analog_up_forward():
    # x right (+), y up (-)  -> UP_FORWARD (forward jump while facing right)
    assert _dir(axes=(0.6, -0.6)) == InputDirection.UP_FORWARD


def test_analog_down_forward():
    # the QCF-critical diagonal
    assert _dir(axes=(0.6, 0.6)) == InputDirection.DOWN_FORWARD


def test_hat_up_back():
    # d-pad up-left -> UP_BACK (back jump)
    assert _dir(hat=(-1, 1)) == InputDirection.UP_BACK


def test_hat_down_forward():
    assert _dir(hat=(1, -1)) == InputDirection.DOWN_FORWARD


def test_lower_deadzone_allows_partial_diagonal():
    # 0.35 on each axis used to fall under the old 0.5 deadzone (neutral);
    # now registers as a diagonal.
    assert _dir(axes=(0.35, -0.35)) == InputDirection.UP_FORWARD


def test_mixed_button_dir_plus_analog_combine():
    # Button 6 = 'up' (leverless map) + analog pushed right must OR-combine into
    # UP_FORWARD -- the old code skipped the analog read once a button set a dir.
    assert _dir(buttons=(6,), axes=(0.6, 0.0)) == InputDirection.UP_FORWARD


# --- Bug B: fireball motion triggers the move --------------------------------

def _feed(player, direction):
    player.frame_count += 1
    player.current_direction = direction
    player.input_buffer.append(InputState(
        direction=direction, buttons_pressed=set(), buttons_just_pressed=set(),
        buttons_just_released=set(), frame_number=player.frame_count,
    ))


def test_qcf_punch_triggers_gohadoken():
    akuma = Akuma(200, STAGE_FLOOR, player_number=1)
    akuma.input = PlayerInput(1)
    for d in (InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        _feed(akuma.input, d)
    akuma.input.buttons_pressed_this_frame = {Button.MEDIUM_PUNCH}

    assert akuma._check_special_moves() is True
    assert akuma.state == CharacterState.GOHADOKEN
    assert akuma.pending_projectile_strength == "medium"


def test_gohadoken_spawns_projectile_on_active_frame():
    """Driving the GOHADOKEN state to its spawn frame produces a projectile."""
    akuma = Akuma(200, STAGE_FLOOR, player_number=1)
    akuma.input = PlayerInput(1)
    for d in (InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        _feed(akuma.input, d)
    akuma.input.buttons_pressed_this_frame = {Button.LIGHT_PUNCH}
    akuma._check_special_moves()
    assert akuma.state == CharacterState.GOHADOKEN

    opponent = Akuma(400, STAGE_FLOOR, player_number=2)
    spawned = False
    for _ in range(30):  # GOHADOKEN spawns its projectile on frame 14
        akuma.update(opponent)
        if akuma.projectiles:
            spawned = True
            break
    assert spawned, "Gohadoken must spawn a projectile during its active window"
