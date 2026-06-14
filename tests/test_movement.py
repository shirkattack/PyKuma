"""Movement / pushbox tests: airborne characters can pass over each other."""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.systems.input_system import PlayerInput
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import CharacterState, InputDirection


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


def test_can_jump_forward_out_of_walking():
    """Holding forward (-> WALKING_FORWARD) then up must start a forward jump.

    Regression: jump used to be gated to STANDING/CROUCHING, so a pad forward-jump
    (hold forward, then up) never left the ground.
    """
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    a.input = PlayerInput(1)
    a.is_grounded = True
    a._transition_to_state(CharacterState.WALKING_FORWARD)
    a._check_movement(InputDirection.UP_FORWARD)
    assert a.state == CharacterState.JUMP_STARTUP
    assert a.jump_direction == InputDirection.UP_FORWARD


def test_can_jump_backward_out_of_walking():
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    a.input = PlayerInput(1)
    a.is_grounded = True
    a._transition_to_state(CharacterState.WALKING_BACKWARD)
    a._check_movement(InputDirection.UP_BACK)
    assert a.state == CharacterState.JUMP_STARTUP
    assert a.jump_direction == InputDirection.UP_BACK
