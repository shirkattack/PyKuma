"""Button edge-detection across keyboard + joystick.

Regression for the pad continuous-fire bug: the old update() ran two independent
button loops, and the keyboard loop cleared any Button whose key was up -- which
clobbered a joystick-held button every frame, so holding a pad button registered
as "just pressed" on every frame and retriggered the attack continuously.
"""

import pygame
import pytest

from street_fighter_3rd.systems.input_system import PlayerInput
from street_fighter_3rd.data.enums import Button


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    yield
    pygame.quit()


class _FakeJoystick:
    """Minimal stick: only button states, no axes/hats."""
    def __init__(self):
        self._buttons = {}

    def init(self):
        pass

    def get_name(self):
        return "fake"

    def get_numbuttons(self):
        return 16

    def get_button(self, i):
        return 1 if self._buttons.get(i) else 0

    def get_numaxes(self):
        return 0

    def get_numhats(self):
        return 0

    def press(self, i):
        self._buttons[i] = True

    def release(self, i):
        self._buttons[i] = False


@pytest.fixture
def all_keys_up(monkeypatch):
    """pygame.key.get_pressed() reports every key released."""
    class _NoKeys:
        def __getitem__(self, _):
            return 0
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _NoKeys())


def test_held_pad_button_is_just_pressed_once(all_keys_up):
    pi = PlayerInput(1)
    js = _FakeJoystick()
    pi.joystick = js
    js.press(0)  # button 0 -> LIGHT_PUNCH

    pi.update()
    assert pi.is_button_just_pressed(Button.LIGHT_PUNCH)  # frame 1: pressed
    assert pi.is_button_pressed(Button.LIGHT_PUNCH)

    # Holding across many frames must NOT keep re-firing just_pressed.
    for _ in range(10):
        pi.update()
        assert not pi.is_button_just_pressed(Button.LIGHT_PUNCH)
        assert pi.is_button_pressed(Button.LIGHT_PUNCH)


def test_pad_button_release_is_detected(all_keys_up):
    pi = PlayerInput(1)
    js = _FakeJoystick()
    pi.joystick = js
    js.press(2)  # HEAVY_PUNCH
    pi.update()
    assert pi.is_button_pressed(Button.HEAVY_PUNCH)

    js.release(2)
    pi.update()
    assert not pi.is_button_pressed(Button.HEAVY_PUNCH)
    assert Button.HEAVY_PUNCH in pi.buttons_released_this_frame

    # A fresh press after release fires just_pressed again.
    js.press(2)
    pi.update()
    assert pi.is_button_just_pressed(Button.HEAVY_PUNCH)
