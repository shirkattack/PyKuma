"""Motion-input matcher tests, including consume-on-match semantics."""

import pygame
import pytest

from street_fighter_3rd.systems.input_system import PlayerInput, InputState
from street_fighter_3rd.data.enums import InputDirection, Button


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    yield
    pygame.quit()


def make_input() -> PlayerInput:
    return PlayerInput(1)


def feed(player: PlayerInput, direction: InputDirection):
    """Append one frame of directional input to the buffer."""
    player.frame_count += 1
    player.current_direction = direction
    player.input_buffer.append(InputState(
        direction=direction,
        buttons_pressed=set(),
        buttons_just_pressed=set(),
        buttons_just_released=set(),
        frame_number=player.frame_count,
    ))


def press(player: PlayerInput, button: Button):
    player.buttons_pressed_this_frame = {button}


def test_qcf_detected():
    p = make_input()
    for d in (InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        feed(p, d)
    press(p, Button.LIGHT_PUNCH)
    assert p.check_motion_input("QCF", Button.LIGHT_PUNCH)


def test_qcf_requires_button():
    p = make_input()
    for d in (InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        feed(p, d)
    p.buttons_pressed_this_frame = set()
    assert not p.check_motion_input("QCF", Button.LIGHT_PUNCH)


def test_motion_is_consumed_on_match():
    """A second punch press within the window must not re-trigger the same QCF."""
    p = make_input()
    for d in (InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        feed(p, d)

    press(p, Button.LIGHT_PUNCH)
    assert p.check_motion_input("QCF", Button.LIGHT_PUNCH)

    # Forward is still held; the buffered QCF directions are still in range
    feed(p, InputDirection.FORWARD)
    press(p, Button.LIGHT_PUNCH)
    assert not p.check_motion_input("QCF", Button.LIGHT_PUNCH), \
        "a used motion must be consumed from the buffer"


def test_fresh_motion_after_consume_retriggers():
    p = make_input()
    for d in (InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        feed(p, d)
    press(p, Button.LIGHT_PUNCH)
    assert p.check_motion_input("QCF", Button.LIGHT_PUNCH)

    # Perform a brand-new QCF: a new DOWN input restarts the motion
    for d in (InputDirection.NEUTRAL, InputDirection.DOWN,
              InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        feed(p, d)
    press(p, Button.LIGHT_PUNCH)
    assert p.check_motion_input("QCF", Button.LIGHT_PUNCH)


def test_reset_clears_buffer_and_consumed_state():
    p = make_input()
    for d in (InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD):
        feed(p, d)
    press(p, Button.LIGHT_PUNCH)
    assert p.check_motion_input("QCF", Button.LIGHT_PUNCH)

    p.reset()

    assert len(p.input_buffer) == 0
    assert p.current_direction == InputDirection.NEUTRAL
    assert p.consumed_motion_frames == {}
    # And nothing fires from the cleared buffer
    press(p, Button.LIGHT_PUNCH)
    assert not p.check_motion_input("QCF", Button.LIGHT_PUNCH)
