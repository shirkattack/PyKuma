"""Universal Overhead (MP+MK) and Taunt (HP+HK) command actions.

These animations existed as assets but were never wired to a state/input.
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


def _run(buttons, anim_name):
    g = new_game()
    g.player1.x, g.player2.x = 320, 540
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    inp = (hold(InputDirection.NEUTRAL, 2)
           + [(InputDirection.NEUTRAL, buttons)]
           + hold(InputDirection.NEUTRAL, 50))
    g.input_system = ScriptedInputSystem(inp, [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    states, anims = set(), set()
    for i in range(55):
        g.update()
        g.render()
        states.add(g.player1.state)
        anims.add(g.player1.animation_controller.current_name)
    recovered = g.player1.state == CharacterState.STANDING
    return states, anims, recovered


def test_overhead_mp_mk():
    states, anims, recovered = _run([Button.MEDIUM_PUNCH, Button.MEDIUM_KICK], "overhead")
    assert CharacterState.OVERHEAD in states
    assert "overhead" in anims
    assert recovered, "overhead should recover to standing"


def test_taunt_hp_hk():
    states, anims, recovered = _run([Button.HEAVY_PUNCH, Button.HEAVY_KICK], "taunt")
    assert CharacterState.TAUNT in states
    assert "taunt" in anims
    assert recovered, "taunt should recover to standing"
