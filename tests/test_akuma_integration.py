"""
Akuma integration test: verifies Akuma can be created with the SF3 sprite
integration and updated for a frame without crashing.
"""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_akuma_creation():
    """Akuma constructs with SF3-authentic stats and a sprite system flag."""
    akuma = Akuma(200, 500, player_number=1)

    assert akuma.name == "Akuma"
    assert akuma.player_number == 1
    assert akuma.max_health == 145, "Akuma's SF3 max health is 145"
    assert akuma.health == akuma.max_health, "Akuma must start at full health"

    # Single animation path: the controller exists and resolves a stance sprite
    assert akuma.animation_controller is not None, "Akuma must have an animation controller"
    assert akuma.animation_controller.get_current_sprite() is not None, \
        "stance must resolve to a real sprite"


def test_akuma_update():
    """A frame update against an opponent runs and advances the state frame."""
    akuma = Akuma(200, 500, player_number=1)
    opponent = Akuma(400, 500, player_number=2)

    start_frame = akuma.state_frame
    akuma.update(opponent)

    assert akuma.state_frame == start_frame + 1, "update() must advance the state frame"
    assert akuma.health == akuma.max_health, "a neutral update must not change health"
