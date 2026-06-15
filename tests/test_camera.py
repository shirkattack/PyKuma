"""Dynamic view camera: zoom tracks fighter separation; world->screen mapping.

The simulation stays in world units; the camera only scales a crop of the world
buffer onto the screen, so movement/spacing look proportional to the characters.
"""

import pygame
import pytest

from street_fighter_3rd.core.game import Game
from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
from street_fighter_3rd.data.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_MAX_ZOOM, CAMERA_MIN_ZOOM)


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    yield
    pygame.quit()


def _game():
    return Game(pygame.display.get_surface(), GameModeManager(GameMode.TRAINING))


def test_camera_zooms_in_when_close_out_when_far():
    g = _game()
    g.player1.x, g.player2.x = 300, 360          # close
    _, _, cw_close, _ = g._compute_camera()
    g.player1.x, g.player2.x = 120, 780          # far apart
    _, _, cw_far, _ = g._compute_camera()
    # closer fighters -> smaller crop -> higher zoom
    assert cw_close < cw_far
    assert SCREEN_WIDTH / cw_close > SCREEN_WIDTH / cw_far


def test_camera_zoom_stays_within_bounds():
    g = _game()
    for p2 in (305, 400, 600, 880, 80):
        g.player1.x, g.player2.x = 300, p2
        _, _, cw, ch = g._compute_camera()
        zoom = SCREEN_WIDTH / cw
        assert CAMERA_MIN_ZOOM - 0.01 <= zoom <= CAMERA_MAX_ZOOM + 0.01
        # crop must stay inside the world buffer
        cx, cy, cw, ch = g._compute_camera()
        assert cx >= 0 and cy >= 0
        assert cx + cw <= SCREEN_WIDTH + 0.5 and cy + ch <= SCREEN_HEIGHT + 0.5


def test_world_to_screen_uses_current_camera():
    g = _game()
    g.player1.x, g.player2.x = 300, 420
    g._blit_world_zoomed()                         # sets g._cam
    cx, cy, zoom = g._cam
    sx, sy = g._world_to_screen(cx, cy)
    assert sx == pytest.approx(0.0) and sy == pytest.approx(0.0)
    sx2, _ = g._world_to_screen(cx + 100, cy)
    assert sx2 == pytest.approx(100 * zoom)


def test_render_runs_with_camera():
    g = _game()
    for _ in range(3):
        g.update()
    g.render()  # must not raise; world buffer -> zoomed screen -> UI/overlays
