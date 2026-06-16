"""H2: the frame-data panel latches and lingers after the move, centered bottom.

It used to render only while attacking (it vanished the instant the move ended)
and sat in a corner. Now it captures the last move and keeps showing for ~2s.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold, tap
from street_fighter_3rd.data.enums import Button, InputDirection, FacingDirection


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _game_with_hp():
    g = new_game()
    g.config.show_frame_data = True
    g.player1.x, g.player2.x = 320, 360
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    g.input_system = ScriptedInputSystem(
        hold(InputDirection.NEUTRAL, 2) + tap(Button.HEAVY_PUNCH) + hold(None, 200), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    return g


def test_frame_data_latches_and_lingers_then_clears():
    g = _game_with_hp()
    first = cleared = None
    for i in range(180):
        g.update()
        if g._fd_latch and first is None:
            first = i
        if first is not None and g._fd_latch is None and cleared is None:
            cleared = i
    assert first is not None, "a move should latch frame data"
    assert cleared is not None, "the latch should clear after the linger"
    # lingers well beyond the move itself (the ~120-frame linger), not instantly.
    assert cleared - first >= g._FD_LINGER, "panel must persist ~2s past the move"


def test_frame_data_panel_renders_without_error():
    g = _game_with_hp()
    for _ in range(10):
        g.update()
    assert g._fd_latch is not None
    g._render_frame_data()  # centered-bottom panel; must not raise
