"""
Geometry regression tests for box placement: facing-mirror + per-box anchor.

The oracle is the cross-validated Baston / ensabahnur jab dump and the
3rd_training_lua box-structure doc:
- attack boxes are "edge"-anchored: offset_x is the forward-positive NEAR edge;
  facing left mirrors BOTH edges.
- hurt / push / throw boxes are "center"-anchored: offset_x is the box center.

Baston jab active box raw [X=-48, W=14] -> PyKuma edge offset_x = -X - W = 34, width 14.
Baston pushbox raw [X=-25, W=50] -> PyKuma center offset_x = -(X + W/2) = 0, width 50.
"""

import pygame

from street_fighter_3rd.systems.sf3_hitboxes import SF3Hitbox
from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
from street_fighter_3rd.systems.vfx import VFXManager
from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.data.enums import CharacterState, FacingDirection
from street_fighter_3rd.data.constants import STAGE_FLOOR

CHAR_X = 100
CHAR_Y = 0


def test_edge_box_facing_right():
    """Attack (edge) box facing right: offset_x is the near edge, extends forward."""
    box = SF3Hitbox(offset_x=34, offset_y=-96, width=14, height=12, anchor="edge")
    rect = box.get_rect(CHAR_X, CHAR_Y, facing=1)
    assert rect.left == 134 and rect.right == 148


def test_edge_box_facing_left_mirrors_both_edges():
    """Facing left must mirror the WHOLE box, not just shift the near edge."""
    box = SF3Hitbox(offset_x=34, offset_y=-96, width=14, height=12, anchor="edge")
    rect = box.get_rect(CHAR_X, CHAR_Y, facing=-1)
    # mirror of [134,148] about CHAR_X=100 -> [52,66]
    assert rect.left == 52 and rect.right == 66


def test_center_box_is_centered():
    """Pushbox (center) offset_x=0 -> box straddles the axis, not anchored at it."""
    box = SF3Hitbox(offset_x=0, offset_y=-84, width=50, height=84, anchor="center")
    right = box.get_rect(CHAR_X, CHAR_Y, facing=1)
    assert right.left == 75 and right.right == 125
    left = box.get_rect(CHAR_X, CHAR_Y, facing=-1)
    assert left.left == 75 and left.right == 125  # offset_x=0 -> symmetric either way


def test_center_box_offset_mirrors_with_facing():
    """A non-zero center offset flips side with facing."""
    box = SF3Hitbox(offset_x=10, offset_y=-60, width=50, height=20, anchor="center")
    right = box.get_rect(CHAR_X, CHAR_Y, facing=1)   # center 110 -> [85,135]
    assert right.centerx == 110 and right.left == 85
    left = box.get_rect(CHAR_X, CHAR_Y, facing=-1)    # center 90 -> [65,115]
    assert left.centerx == 90 and left.left == 65


def test_collision_is_facing_symmetric():
    """A move that hits to the right must also hit when both sides are mirrored.

    Guards the facing bug end-to-end: previously left-facing attack boxes landed
    ~width px off, so the mirrored case would miss.
    """
    pygame.init()
    pygame.display.set_mode((1, 1))
    try:
        def run(att_x, def_x, face_right):
            attacker = Akuma(att_x, STAGE_FLOOR, player_number=1)
            defender = Akuma(def_x, STAGE_FLOOR, player_number=2)
            attacker.facing = FacingDirection.RIGHT if face_right else FacingDirection.LEFT
            defender.facing = FacingDirection.LEFT if face_right else FacingDirection.RIGHT
            attacker._transition_to_state(CharacterState.MEDIUM_PUNCH)
            attacker.state_frame = 5  # active frame
            adapter = SF3CollisionAdapter()
            adapter.tick()
            return adapter.check_attack_collision(attacker, defender, VFXManager())

        hit_right = run(200, 250, face_right=True)    # attacker faces right, def +50
        hit_left = run(250, 200, face_right=False)    # mirrored: attacker faces left, def -50
        assert hit_right, "MP must hit a defender 50px in front (facing right)"
        assert hit_left, "MP must hit symmetrically when facing left (regression: get_rect mirror)"
    finally:
        pygame.quit()
