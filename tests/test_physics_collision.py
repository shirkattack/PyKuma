"""Phase 3: pushbox collision (no dash-through / side-switch) + jump-flip mapping."""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.systems.input_system import PlayerInput
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import CharacterState, InputDirection


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((8, 8))
    yield
    pygame.quit()


def test_akuma_uses_rom_pushbox_width():
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    assert a.pushbox_width == 50  # ROM idle pushbox width, not the generic 40


def test_resolver_uncrosses_a_tunnelling_dash():
    # a started LEFT of b last frame, but this frame's dash overshot PAST b's center.
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    b = Akuma(300, STAGE_FLOOR, player_number=2)
    a.is_grounded = b.is_grounded = True
    a._prev_x, b._prev_x = 200, 300       # stable order: a left of b
    a.x, b.x = 320, 300                   # a tunnelled to the right of b
    a._resolve_character_collision(b)
    assert a.x <= b.x, "stable order must be restored (a stays on the left)"
    assert (b.x - a.x) >= (a.pushbox_width + b.pushbox_width) / 2 - 0.001


def test_dash_into_opponent_never_crosses_over_many_frames():
    a = Akuma(200, STAGE_FLOOR, player_number=1); a.input = PlayerInput(1)
    b = Akuma(300, STAGE_FLOOR, player_number=2); b.input = PlayerInput(2)
    a.is_grounded = b.is_grounded = True
    a._transition_to_state(CharacterState.DASH_FORWARD)  # a dashes toward b
    min_d = (a.pushbox_width + b.pushbox_width) / 2
    for _ in range(30):
        a.update(b)
        b.update(a)
        assert a.x <= b.x + 0.001, "dasher must never cross to the right of the opponent"
        assert (b.x - a.x) >= min_d - 1.0, "must stay ~pushbox apart (no tunnelling)"


def test_dash_into_opponent_does_not_shove_them():
    # B9: a forward dash stops AT the pushbox contact line; it must not push the
    # standing opponent across the screen (that read as dashing "through" them),
    # and no leftover dash velocity may lunge into them after the dash ends.
    a = Akuma(200, STAGE_FLOOR, player_number=1); a.input = PlayerInput(1)
    b = Akuma(300, STAGE_FLOOR, player_number=2); b.input = PlayerInput(2)
    a.is_grounded = b.is_grounded = True
    b_start = b.x
    a._transition_to_state(CharacterState.DASH_FORWARD)
    for _ in range(30):
        a.update(b); b.update(a)
    assert abs(b.x - b_start) < 1.0, "a standing opponent must not be shoved by a dash"


def test_facing_stable_while_dashing_in():
    a = Akuma(200, STAGE_FLOOR, player_number=1); a.input = PlayerInput(1)
    b = Akuma(300, STAGE_FLOOR, player_number=2); b.input = PlayerInput(2)
    a.is_grounded = b.is_grounded = True
    a._transition_to_state(CharacterState.DASH_FORWARD)
    facings = []
    for _ in range(30):
        a.update(b); b.update(a)
        facings.append(a.is_facing_right())
    # a is on the left throughout, so it should keep facing right the whole time.
    assert all(facings), "facing must not oscillate when blocked by the pushbox"


def test_forward_jump_uses_flip_clip():
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    fwd = a.animation_controller.animations["jump_forward"]
    back = a.animation_controller.animations["jump_backward"]
    assert "akuma-jumpf" in fwd.frames[0].folder_path
    assert "akuma-jumpb" in back.frames[0].folder_path
    # neutral jump remains the plain jump clip
    up = a.animation_controller.animations["jump_up"]
    assert "akuma-jump" in up.frames[0].folder_path and "jumpf" not in up.frames[0].folder_path


def test_forward_jump_transition_plays_flip():
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    a.jump_direction = InputDirection.UP_FORWARD
    a.is_grounded = False
    a._transition_to_state(CharacterState.JUMPING)
    cur = a.animation_controller.get_current_animation_name()
    assert cur == "jump_forward"
