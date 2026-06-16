"""BT2: Demon Flip / Hyakkishu (QCF+K) -- an arcing forward jump toward the
opponent. The flip itself has no hitbox (followups, deferred, would)."""

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


def test_qcf_kick_demon_flip_arcs_and_lands():
    g = new_game()
    g.player1.x, g.player2.x = 300, 560
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    motion = [(InputDirection.DOWN, []), (InputDirection.DOWN_FORWARD, []),
              (InputDirection.FORWARD, [Button.MEDIUM_KICK])]
    g.input_system = ScriptedInputSystem(hold(InputDirection.NEUTRAL, 2) + motion + hold(None, 60), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2

    x0, y0 = g.player1.x, g.player1.y
    triggered = airborne = False
    peak = 0.0
    for _ in range(60):
        g.update()
        if g.player1.state == CharacterState.DEMON_FLIP:
            triggered = True
            airborne = airborne or not g.player1.is_grounded
            peak = min(peak, g.player1.y - y0)
    assert triggered, "QCF+K should start a demon flip"
    assert airborne, "demon flip should go airborne"
    assert -peak > 40, "should rise into an arc"
    assert g.player1.x - x0 > 100, "should travel forward toward the opponent"
    assert g.player1.is_grounded and g.player1.state == CharacterState.STANDING, "should land + recover"
