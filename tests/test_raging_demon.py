"""BT4: Raging Demon / Shun Goku Satsu (LP, LP, F, LK, HP) -- an unblockable
close command grab that costs a full super bar."""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.data.enums import Button, InputDirection, FacingDirection, CharacterState

LP, LK, HP = Button.LIGHT_PUNCH, Button.LIGHT_KICK, Button.HEAVY_PUNCH
N, F = InputDirection.NEUTRAL, InputDirection.FORWARD
SEQ = [(N, [LP]), (N, []), (N, [LP]), (N, []), (F, []), (F, [LK]), (N, []), (N, [HP])]


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _run(p2x, meter=100):
    g = new_game()
    g.player1.x, g.player2.x = 320, p2x
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    g.player1.super_meter = meter
    g.input_system = ScriptedInputSystem(hold(N, 2) + SEQ + hold(None, 60), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    hp0 = g.player2.health
    states = set()
    for _ in range(70):
        g.update()
        states.add(g.player1.state)
    return (CharacterState.RAGING_DEMON in states), hp0 - g.player2.health


def test_raging_demon_connects_point_blank():
    triggered, dmg = _run(390)            # within grab range
    assert triggered, "LP,LP,F,LK,HP with meter should trigger the Raging Demon"
    assert dmg >= 400, "the command grab should deal massive damage"


def test_raging_demon_whiffs_out_of_range():
    triggered, dmg = _run(760)            # too far
    assert triggered, "the super still comes out"
    assert dmg == 0, "the grab whiffs out of range (no damage)"


def test_raging_demon_needs_meter():
    triggered, _ = _run(390, meter=0)
    assert not triggered, "no full bar -> no Raging Demon"
