"""Fireball (Gohadoken): QCF+P spawns a projectile that travels forward and
renders. (Projectile art is a procedural placeholder until a real sprite lands.)"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, qcf, hold
from street_fighter_3rd.data.enums import Button


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _throw_fireball():
    g = new_game()
    g.player1.x, g.player2.x = 250, 700
    script = qcf(Button.LIGHT_PUNCH) + hold(None, 50)
    g.input_system = ScriptedInputSystem(script)
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    return g


def test_qcf_spawns_a_fireball():
    g = _throw_fireball()
    spawned = False
    for _ in range(30):
        g.update()
        if g.player1.projectiles:
            spawned = True
            break
    assert spawned, "QCF+LP should spawn a Gohadoken projectile"


def test_fireball_travels_forward_and_renders():
    g = _throw_fireball()
    xs = []
    for _ in range(40):
        g.update()
        g.render()  # exercises the procedural projectile render (must not raise)
        if g.player1.projectiles:
            xs.append(g.player1.projectiles[0].x)
    assert len(xs) >= 3
    assert xs[-1] > xs[0], "fireball should travel forward (P1 faces right)"
