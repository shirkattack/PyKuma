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


def test_native_view_is_a_fixed_384x224_window_scrolled_after_the_fighters():
    from street_fighter_3rd.data.constants import (
        NATIVE_VIEW_WIDTH, NATIVE_VIEW_HEIGHT, NATIVE_VIEW_GROUND_ROW, CAMERA_GROUND_Y)
    g = _game()
    g.native_view = True
    g.player1.x, g.player2.x = 400, 500
    cx, cy, cw, ch = g._compute_camera()
    assert (cw, ch) == (NATIVE_VIEW_WIDTH, NATIVE_VIEW_HEIGHT)
    assert cx == 450 - NATIVE_VIEW_WIDTH / 2                          # centred on the midpoint
    assert cy == CAMERA_GROUND_Y - NATIVE_VIEW_GROUND_ROW              # feet line on its viewport row
    g.player1.x, g.player2.x = 80, 120                                 # left corner: clamps to the stage edge
    assert g._compute_camera()[0] == 0
    g.player1.x, g.player2.x = 800, 816
    assert g._compute_camera()[0] == SCREEN_WIDTH - NATIVE_VIEW_WIDTH


def test_native_view_blits_at_an_integer_scale_and_maps_world_to_screen_with_the_letterbox():
    from street_fighter_3rd.data.constants import NATIVE_VIEW_WIDTH, NATIVE_VIEW_HEIGHT
    g = _game()
    g.native_view = True
    g.player1.x, g.player2.x = 400, 500
    g._blit_world_zoomed()
    cx, cy, zoom = g._cam
    k = g._native_scale()
    assert zoom == k and k == min(SCREEN_WIDTH // NATIVE_VIEW_WIDTH, SCREEN_HEIGHT // NATIVE_VIEW_HEIGHT)
    ox, oy = g._cam_off
    assert ox == (SCREEN_WIDTH - NATIVE_VIEW_WIDTH * k) // 2 and oy == (SCREEN_HEIGHT - NATIVE_VIEW_HEIGHT * k) // 2
    sx, sy = g._world_to_screen(cx, cy)
    assert (sx, sy) == (ox, oy)
    sx2, _ = g._world_to_screen(cx + 100, cy)
    assert sx2 == ox + 100 * k
    # the default camera still maps with no letterbox
    g.native_view = False
    g._blit_world_zoomed()
    assert g._cam_off == (0, 0)


def test_f3_toggles_the_native_view():
    g = _game()
    assert g.native_view is False
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3))
    assert g.native_view is True


def test_native_view_hud_is_laid_out_inside_the_384x224_frame():
    """Phase 8: in the CPS3 view the HUD belongs to the arcade frame, not the
    896-px window -- nothing may be drawn in the letterbox around it."""
    from street_fighter_3rd.data.constants import NATIVE_VIEW_WIDTH, NATIVE_VIEW_HEIGHT
    g = _game()
    g.native_view = True
    g.player1.x, g.player2.x = 400, 500
    g.player1.health = int(g.player1.max_health * 0.5)
    g.player2.super_meter = 96
    g.render()
    k = g._native_scale()
    ox, oy = g._cam_off
    assert (ox, oy) != (0, 0), "this window letterboxes the 384x224 frame"
    # the HUD buffer is viewport-sized ...
    assert g._native_hud_buf.get_size() == (NATIVE_VIEW_WIDTH, NATIVE_VIEW_HEIGHT)
    # ... and the health bar it drew lands inside the frame, not above it
    bar_y = oy + g.NATIVE_HUD_BAR_Y * k
    assert oy < bar_y < oy + NATIVE_VIEW_HEIGHT * k
    # the letterbox columns stay empty (the classic HUD used to paint here)
    for y in range(0, SCREEN_HEIGHT, 17):
        assert g.screen.get_at((ox // 2, y))[:3] == (0, 0, 0), f"letterbox painted at y={y}"
