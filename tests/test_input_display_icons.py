"""H1: the on-screen input display renders vendored icon sprites.

Guards that the direction/button icons load and the input column renders without
error (it previously drew text glyphs).
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from street_fighter_3rd.core.game import Game


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def test_all_input_icons_load():
    icons = Game._load_input_icons()
    assert len(icons["dir"]) == 9, "all nine numpad direction arrows must load"
    assert set(icons["btn"]) == {"LP", "MP", "HP", "LK", "MK", "HK"}
    # scaled to the configured row-icon height
    for s in list(icons["dir"].values()) + list(icons["btn"].values()):
        assert s.get_height() == Game._INPUT_ICON_H


def test_input_display_renders_without_error():
    screen = pygame.display.get_surface()
    g = Game(screen)
    # push a few frames of varied input through the real buffer
    from street_fighter_3rd.data.enums import InputDirection, Button
    from street_fighter_3rd.systems.input_system import InputState
    pi = g.input_system.player1
    for i, (d, btns) in enumerate([
        (InputDirection.DOWN, set()),
        (InputDirection.DOWN_FORWARD, set()),
        (InputDirection.FORWARD, {Button.LIGHT_PUNCH}),
    ]):
        pi.input_buffer.append(InputState(d, set(btns), set(btns), set(), i))
    g._render_input_display(pi, side="left")  # must not raise
