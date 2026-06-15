"""Attack state-machine regressions: walk-and-punch, and crouch normals must
recover back to crouch (not briefly stand up) while down is held."""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.systems.input_system import PlayerInput, InputState
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import CharacterState, InputDirection, Button


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((8, 8))
    yield
    pygame.quit()


def _set_input(pi, direction, held=None):
    """Drive a character's PlayerInput by hand for one frame (held = re-press
    only when newly added, matching real edge detection)."""
    pi.current_direction = direction
    newly = held is not None and held not in pi.buttons_held
    pi.buttons_pressed_this_frame = {held} if newly else set()
    pi.buttons_held = {held} if held is not None else set()
    pi.frame_count += 1
    pi.input_buffer.append(InputState(
        direction, set(pi.buttons_held), set(pi.buttons_pressed_this_frame),
        set(), pi.frame_count))


def _pair():
    a = Akuma(200, STAGE_FLOOR, player_number=1); a.input = PlayerInput(1)
    b = Akuma(440, STAGE_FLOOR, player_number=2); b.input = PlayerInput(2)
    return a, b


def test_can_attack_while_walking_forward():
    a, b = _pair()
    for _ in range(8):                         # establish WALKING_FORWARD
        _set_input(a.input, InputDirection.FORWARD)
        a.update(b)
    assert a.state == CharacterState.WALKING_FORWARD
    _set_input(a.input, InputDirection.FORWARD, Button.MEDIUM_PUNCH)
    a.update(b)
    assert a.state == CharacterState.MEDIUM_PUNCH


def test_crouch_normal_recovers_to_crouch_not_standing():
    a, b = _pair()
    for _ in range(8):                         # establish CROUCHING
        _set_input(a.input, InputDirection.DOWN)
        a.update(b)
    assert a.state == CharacterState.CROUCHING

    _set_input(a.input, InputDirection.DOWN, Button.MEDIUM_PUNCH)  # crouch MP
    a.update(b)
    assert a.state == CharacterState.CROUCH_MEDIUM_PUNCH

    seen = set()
    for _ in range(40):                        # hold down, release button
        _set_input(a.input, InputDirection.DOWN)
        a.update(b)
        seen.add(a.state)
        if a.state == CharacterState.CROUCHING:
            break
    assert a.state == CharacterState.CROUCHING
    # The bug returned to STANDING for a frame between crouch attacks.
    assert CharacterState.STANDING not in seen
