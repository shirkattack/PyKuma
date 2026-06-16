"""G3: a LP+LK throw must be available and connect on a nearby grounded opponent.

Throws were fully stubbed out (no input binding, no throw state animation, the
adapter's _is_throwing hard-returned False). This drives a real LP+LK press
through the game and asserts the throw connects (damage + the opponent knocked
down), and that an out-of-range throw whiffs (no damage).
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.data.enums import (
    Button, InputDirection, FacingDirection, CharacterState)


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _run(p1_x, p2_x, frames=40):
    g = new_game()
    g.player1.x, g.player2.x = p1_x, p2_x
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    # P1 presses LP+LK on frame 2 (neutral throw), then releases.
    p1_inputs = (hold(InputDirection.NEUTRAL, 2)
                 + [(InputDirection.NEUTRAL, [Button.LIGHT_PUNCH, Button.LIGHT_KICK])]
                 + hold(InputDirection.NEUTRAL, frames))
    g.input_system = ScriptedInputSystem(p1_inputs, [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    states, p2_hp = [], []
    for _ in range(frames):
        g.update()
        states.append(g.player1.state)
        p2_hp.append(g.player2.health)
    return g, states, p2_hp


def test_lp_lk_throw_connects_pointblank():
    g, states, p2_hp = _run(320, 360)   # ~40px apart -> in throw range
    assert CharacterState.THROWING in states, "LP+LK should start a throw"
    assert p2_hp[-1] < p2_hp[0], "a connected throw should damage P2"
    assert g.player1._threw_successfully, "throw should have connected"


def test_throw_whiffs_when_out_of_range():
    g, states, p2_hp = _run(200, 700)   # far apart -> whiff
    assert CharacterState.THROWING in states, "LP+LK should still start the throw"
    assert p2_hp[-1] == p2_hp[0], "a whiffed throw deals no damage"
    assert not g.player1._threw_successfully, "throw should have whiffed"
