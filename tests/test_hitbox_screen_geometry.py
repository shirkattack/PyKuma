"""Phase 2: the debug overlay's screen-space box transform (SF3Hitbox.get_screen_rect).

Boxes are stored in ROM-native, feet-origin units (offset_y negative = up). The
overlay must scale them by SPRITE_SCALE and anchor them at the on-screen feet
line so they line up with the scaled sprite. Collision math (get_rect, world
units) must be untouched.
"""

import pygame
import pytest

from street_fighter_3rd.systems.sf3_hitboxes import SF3Hitbox
from street_fighter_3rd.data.constants import SPRITE_SCALE


def test_center_box_scales_and_anchors_at_feet():
    # idle head hurtbox (hitboxes.yaml): offset_x 3, offset_y -101, 22x20, center.
    hb = SF3Hitbox(offset_x=3, offset_y=-101, width=22, height=20, anchor="center")
    r = hb.get_screen_rect(center_x=448, feet_y=430, facing=1, scale=2.0)
    assert (r.width, r.height) == (44, 40)               # scaled x2
    assert r.top == 228                                   # 430 + (-101)*2, head region
    assert r.centerx == 454                               # 448 + 3*2


def test_center_box_mirrors_when_facing_left():
    hb = SF3Hitbox(offset_x=3, offset_y=-101, width=22, height=20, anchor="center")
    right = hb.get_screen_rect(448, 430, 1, 2.0)
    left = hb.get_screen_rect(448, 430, -1, 2.0)
    # centers are mirror images about center_x=448
    assert (right.centerx - 448) == -(left.centerx - 448)


def test_edge_attack_box_mirrors_both_edges():
    # an attack box: offset_x 32 (forward near edge), 36 wide, anchor edge.
    hb = SF3Hitbox(offset_x=32, offset_y=-80, width=36, height=8, anchor="edge")
    right = hb.get_screen_rect(448, 430, 1, 2.0)
    left = hb.get_screen_rect(448, 430, -1, 2.0)
    assert right.left == 448 + 32 * 2                      # near edge forward (right)
    assert left.left == 448 - 32 * 2 - 36 * 2              # mirrored to the left
    assert right.width == left.width == 72


def test_default_scale_is_sprite_scale():
    hb = SF3Hitbox(offset_x=0, offset_y=-40, width=10, height=10, anchor="center")
    r_default = hb.get_screen_rect(100, 200, 1)
    r_explicit = hb.get_screen_rect(100, 200, 1, SPRITE_SCALE)
    assert r_default == r_explicit


def test_get_rect_world_units_unchanged():
    # collision rect must remain 1.0x anchored at character_y (no regression).
    hb = SF3Hitbox(offset_x=3, offset_y=-101, width=22, height=20, anchor="center")
    r = hb.get_rect(448, 344, 1)
    assert (r.width, r.height) == (22, 20)
    assert r.top == 344 - 101
    assert r.centerx == 448 + 3
