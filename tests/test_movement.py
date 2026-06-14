"""Movement / pushbox tests: airborne characters can pass over each other."""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.data.constants import STAGE_FLOOR


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    yield
    pygame.quit()


def test_grounded_characters_separate():
    """Two grounded, overlapping characters get pushed apart."""
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    b = Akuma(210, STAGE_FLOOR, player_number=2)  # overlapping (10px < min_distance)
    a.is_grounded = b.is_grounded = True
    before = abs(a.x - b.x)
    a._resolve_character_collision(b)
    assert abs(a.x - b.x) > before, "grounded overlap should push apart"


def test_airborne_character_passes_over():
    """An airborne character is NOT separated, so you can jump over the opponent."""
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    b = Akuma(205, STAGE_FLOOR, player_number=2)
    a.is_grounded = False   # a is mid-jump, directly above b
    b.is_grounded = True
    ax, bx = a.x, b.x
    a._resolve_character_collision(b)
    assert (a.x, b.x) == (ax, bx), "airborne character must pass over (no separation)"
