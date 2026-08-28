"""B10: forward/back jumps must not lurch the wrong way before moving.

Akuma's somersault jump clips (akuma-jumpf/jumpb) bake the body's horizontal
travel into an oversized canvas. Rendering them canvas-centered on x shoved the
body ~70px toward the opponent on the first airborne frame, then drifted it back
-- the clip's "weird forward movement before moving the right way". The fix
anchors those clips by their opaque-pixel body center, so the drawn body tracks
x (which physics moves monotonically). This test renders each airborne frame and
measures the actually-drawn body center; it fails if the anchoring regresses.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.data.enums import InputDirection, FacingDirection, CharacterState
from tests.asset_guard import require_assets, ANIMATIONS

pytestmark = require_assets(ANIMATIONS)


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _airborne_body_centers(jump_dir):
    """World-x of the actually-drawn body center for each airborne frame."""
    g = new_game()
    g.player1.x, g.player2.x = 700, 980
    g.player1.facing = FacingDirection.RIGHT
    g.player2.facing = FacingDirection.LEFT
    g.input_system = ScriptedInputSystem(hold(jump_dir, 4) + hold(InputDirection.NEUTRAL, 30), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2

    p = g.player1
    samples = []  # (drawn_body_center_x, p.x)
    for _ in range(34):
        g.update()
        if p.state != CharacterState.JUMPING:
            continue
        surf = pygame.Surface((1400, 600), pygame.SRCALPHA)
        # render() draws at world x (the camera zoom is applied later by Game)
        p.x -= 0  # no-op; keep world coords
        saved_y = p.y
        p.render(surf)
        bbox = surf.get_bounding_rect()
        assert bbox.width, "a sprite should have been drawn"
        samples.append((bbox.centerx, p.x))
        p.y = saved_y
    return samples


def _rom_jump_clips():
    from street_fighter_3rd.systems.animation import CelAnimation
    from street_fighter_3rd.characters.akuma import Akuma
    a = Akuma(200, 300, 1)
    return isinstance(a.animation_controller.animations["jump_forward"], CelAnimation)


def _check_no_lurch(samples, wrong_way):
    # Facing right, a back jump travels LEFT. The drawn body must stay glued to x
    # (no ~70px forward shove). With the folder somersault clips the body must
    # also never move the wrong way frame to frame; with the ROM cel clips the
    # body's offset from the axis is the game's own (a somersault swings the
    # body a few px), so the guard is: no per-frame jump, no wrong-way lurch.
    rom = _rom_jump_clips()
    prev = None
    for body_x, world_x in samples:
        assert abs(body_x - world_x) < (40 if rom else 20), (
            f"drawn body ({body_x}) must track x ({world_x}); a big gap is the lurch")
        if prev is not None:
            if rom:
                assert abs(body_x - prev) <= 12, "drawn body must not jump between frames"
            else:
                assert not wrong_way(body_x, prev), "body must not drift the wrong way"
        prev = body_x


def test_back_jump_body_never_lurches_forward():
    samples = _airborne_body_centers(InputDirection.UP_BACK)
    assert len(samples) >= 8
    _check_no_lurch(samples, wrong_way=lambda body_x, prev: body_x > prev + 1)


def test_forward_jump_body_never_lurches_backward():
    samples = _airborne_body_centers(InputDirection.UP_FORWARD)
    assert len(samples) >= 8
    _check_no_lurch(samples, wrong_way=lambda body_x, prev: body_x < prev - 1)
