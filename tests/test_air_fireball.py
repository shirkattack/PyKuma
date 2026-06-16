"""Phase 2.3: air Gohadoken (Zanku Hadou) -- down-forward trajectory, dissipates
at the ground; the grounded fireball stays flat."""

import os

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.systems.input_system import PlayerInput
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import Button


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((8, 8))
    yield
    pygame.quit()


def _pair():
    a = Akuma(300, STAGE_FLOOR, 1); a.input = PlayerInput(1)
    b = Akuma(600, STAGE_FLOOR, 2); b.input = PlayerInput(2)
    return a, b


def _fire(a, b):
    for _ in range(20):
        a.update(b)
        if a.projectiles:
            return a.projectiles[0]
    return None


def test_ground_fireball_is_flat():
    a, b = _pair()
    a._execute_gohadoken(Button.MEDIUM_PUNCH)        # grounded
    p = _fire(a, b)
    assert p is not None and p.velocity_y == 0 and abs(p.velocity_x) > 0


def test_air_fireball_angles_down_forward():
    a, b = _pair()
    a.y, a.is_grounded, a.velocity_y = STAGE_FLOOR - 150, False, 0.0
    a._execute_gohadoken(Button.MEDIUM_PUNCH)        # airborne -> Zanku Hadou
    p = _fire(a, b)
    assert p is not None
    assert p.velocity_y > 0, "air fireball must travel downward"
    assert abs(p.velocity_x) > 0, "and forward"
    assert p.y < STAGE_FLOOR, "spawned in the air"


def test_air_fireball_dissipates_at_ground():
    a, b = _pair()
    a.y, a.is_grounded, a.velocity_y = STAGE_FLOOR - 150, False, 0.0
    a._execute_gohadoken(Button.HEAVY_PUNCH)
    p = _fire(a, b)
    assert p is not None
    for _ in range(200):
        p.update()
        if not p.active:
            break
    assert not p.active and p.y <= STAGE_FLOOR, "air fireball should dissipate at the ground"
