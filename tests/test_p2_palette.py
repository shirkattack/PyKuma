"""P2 palette: the two Akumas must be visually distinct.

Both fighters are Akuma and the extracted cels carry one palette, so a side
switch used to be indistinguishable from a control swap. P2's sprites are
recoloured at load time (gi -> blue); skin, hair and outlines stay put.
"""

import os

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.graphics.palette import akuma_p2, recolor_surface
from tests.asset_guard import require_assets, STANCE as STANCE_DIR


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


STANCE = STANCE_DIR


def test_rule_recolors_gi_but_not_skin_hair_or_outline():
    assert akuma_p2((41, 16, 57, 255)) != (41, 16, 57, 255)      # gi purple
    assert akuma_p2((65, 65, 82, 255)) != (65, 65, 82, 255)      # gi grey-blue
    assert akuma_p2((164, 98, 65, 255)) == (164, 98, 65, 255)    # skin
    assert akuma_p2((172, 0, 0, 255)) == (172, 0, 0, 255)        # hair
    assert akuma_p2((0, 0, 0, 255)) == (0, 0, 0, 255)            # outline
    assert akuma_p2((0, 0, 0, 0)) == (0, 0, 0, 0)                # transparent


@require_assets(STANCE)
def test_recolor_surface_keeps_alpha_and_untouched_pixels():
    p1 = Akuma(200, STAGE_FLOOR, 1)
    src = p1.sprite_manager.load_sprite_from_folder(STANCE, 0)
    out = recolor_surface(src, akuma_p2)
    assert out.get_size() == src.get_size()
    changed = 0
    for x in range(src.get_width()):
        for y in range(src.get_height()):
            a, b = src.get_at((x, y)), out.get_at((x, y))
            assert a.a == b.a, "alpha must be preserved"
            if tuple(a) != tuple(b):
                changed += 1
                assert tuple(b) == akuma_p2(tuple(a))
            else:
                assert akuma_p2(tuple(a)) == tuple(a)
    assert changed > 500, f"only {changed} gi pixels recoloured"


@require_assets(STANCE)
def test_p2_sprites_differ_from_p1_and_caches_do_not_leak():
    p1 = Akuma(200, STAGE_FLOOR, 1)
    p2 = Akuma(300, STAGE_FLOOR, 2)
    s1 = p1.sprite_manager.load_sprite_from_folder(STANCE, 0)
    s2 = p2.sprite_manager.load_sprite_from_folder(STANCE, 0)
    assert pygame.image.tobytes(s1, "RGBA") != pygame.image.tobytes(s2, "RGBA")
    # P1 again is still the original palette (per-character cache)
    s1b = p1.sprite_manager.load_sprite_from_folder(STANCE, 0)
    assert pygame.image.tobytes(s1, "RGBA") == pygame.image.tobytes(s1b, "RGBA")
