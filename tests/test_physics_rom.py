"""Phase 5: in-engine physics matches the ROM-derived values (physics.yaml).

These pin the applied constants to the values captured from sfiii3nr1:
standard jump apex ~83px / ~44 airborne frames, forward dash ~95px, back dash
~45px. Tolerances absorb the 1px/frame integer quantization of the capture.
"""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import CharacterState, InputDirection


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((8, 8))
    yield
    pygame.quit()


def _pair():
    return Akuma(300, STAGE_FLOOR, 1), Akuma(650, STAGE_FLOOR, 2)


def test_jump_apex_and_airtime_match_rom():
    a, b = _pair()
    a.jump_direction = InputDirection.UP
    a._transition_to_state(CharacterState.JUMP_STARTUP)
    apex, airborne = 0.0, 0
    for _ in range(90):
        a.update(b)
        apex = max(apex, STAGE_FLOOR - a.y)
        if not a.is_grounded:
            airborne += 1
        elif airborne:
            break
    assert abs(apex - 83) <= 6, f"jump apex {apex} should be ~83 (ROM)"
    assert abs(airborne - 44) <= 5, f"airborne {airborne} should be ~44 (ROM)"


def test_forward_dash_distance_matches_rom():
    a, b = _pair()
    a._transition_to_state(CharacterState.DASH_FORWARD)
    x0 = a.x
    for _ in range(20):
        a.update(b)
    assert abs((a.x - x0) - 95) <= 8, f"forward dash {a.x - x0} should be ~95 (ROM)"


def test_back_dash_distance_matches_rom():
    a = Akuma(500, STAGE_FLOOR, 1)
    b = Akuma(150, STAGE_FLOOR, 2)  # opponent to the left so 'back' is to the right edge-free
    a._transition_to_state(CharacterState.DASH_BACKWARD)
    x0 = a.x
    for _ in range(20):
        a.update(b)
    assert abs(abs(a.x - x0) - 45) <= 8, f"back dash {abs(a.x - x0)} should be ~45 (ROM)"
