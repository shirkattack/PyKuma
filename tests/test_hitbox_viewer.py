"""Frame-step hitbox viewer tests (headless)."""

import pygame
import pytest

from street_fighter_3rd.core.hitbox_viewer import HitboxViewer
from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def _viewer():
    return HitboxViewer(pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)))


def test_loads_moves_from_canonical_loader():
    v = _viewer()
    assert len(v.moves) == 7  # the 7 migrated Akuma normals
    assert v.frame == 1


def test_step_advances_one_frame_and_wraps():
    v = _viewer()
    total = v.current.total_frames
    v.step(+1)
    assert v.frame == 2
    v.frame = total
    v.step(+1)
    assert v.frame == 1            # wraps forward
    v.step(-1)
    assert v.frame == total        # wraps backward


def test_selecting_move_resets_frame():
    v = _viewer()
    v.step(+1)
    v.step(+1)
    assert v.frame == 3
    v.next_move()
    assert v.frame == 1            # frame resets when the move changes


def test_phase_tracks_startup_active_recovery():
    v = _viewer()
    m = v.current  # light_punch: startup 4, active [5,6,7], recovery 5
    assert m.phase(m.startup) == "STARTUP"
    assert m.phase(m.startup + 1) == "ACTIVE"
    assert m.phase(m.startup + len(m.active)) == "ACTIVE"
    assert m.phase(m.total_frames) == "RECOVERY"


def test_active_frames_have_hitboxes_in_panel():
    from street_fighter_3rd.data.frame_data_loader import get_hitboxes
    v = _viewer()
    m = v.current
    first_active = m.active[0]
    assert get_hitboxes(m.state, first_active)        # active frame has a box
    assert not get_hitboxes(m.state, m.startup)       # startup does not


def test_provenance_label_reflects_status():
    v = _viewer()
    # All migrated normals are unverified placeholders right now.
    assert "UNVERIFIED" in v.provenance_label()


def test_play_toggle_and_update_advances():
    v = _viewer()
    assert not v.playing
    v.toggle_play()
    assert v.playing
    start = v.frame
    for _ in range(HitboxViewer.PLAY_FRAME_TICKS):
        v.update()
    assert v.frame == start % v.current.total_frames + 1


def test_render_does_not_raise():
    v = _viewer()
    v.render()           # startup frame
    v.step(+1); v.step(+1); v.step(+1); v.step(+1)  # into active frames
    v.render()
