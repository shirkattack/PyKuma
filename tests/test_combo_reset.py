"""B1: a combo is a hitstun chain, not a wall-clock timer.

Mashing st.LP with recovery gaps lets the defender leave hitstun between hits,
so each hit is its own 1-hit combo -- the counter must NOT accumulate (the clip
showed a bogus "7 HITS" off mashing). A genuine chain (defender stays in
hitstun) still counts up; that's covered by test_collision_detection /
test_sf3_complete_integration.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, mash_jabs
from street_fighter_3rd.data.enums import FacingDirection


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _run_mash():
    scn = mash_jabs()
    g = new_game()
    g.player1.x, g.player2.x = scn.p1["x"], scn.p2["x"]
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    g.input_system = ScriptedInputSystem(scn.p1_inputs, scn.p2_inputs)
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2

    combo = g.collision_system.sf3_combo_system
    max_count = 0
    hits = 0
    prev_hp = g.player2.health
    for _ in range(scn.frames):
        g.update()
        max_count = max(max_count, combo.get_combo_count(2))
        if g.player2.health < prev_hp:
            hits += 1
            prev_hp = g.player2.health
    return hits, max_count


def test_mashing_jabs_does_not_rack_a_combo():
    hits, max_count = _run_mash()
    assert hits >= 1, "the mash should land at least one jab (else the test is vacuous)"
    assert max_count <= 1, (
        f"mashed jabs (defender recovers between) must each be a 1-hit combo; "
        f"got a {max_count}-hit combo")
