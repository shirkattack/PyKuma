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


def test_fireball_is_actually_drawn_by_character_render():
    """Regression: the projectile-render loop used to live only in the
    never-called _render_fallback_rectangle, so a fireball spawned and moved but
    was never drawn. Assert Akuma.render() adds the projectile's pixels."""
    from street_fighter_3rd.core.projectile import Gohadoken
    from street_fighter_3rd.data.enums import FacingDirection
    g = _throw_fireball()
    p1 = g.player1

    surf_a = pygame.Surface((900, 520), pygame.SRCALPHA)
    p1.render(surf_a)
    before = pygame.mask.from_surface(surf_a).count()

    feet_y = p1.y + p1.feet_offset
    p1.projectiles.append(Gohadoken(p1.x + 120, feet_y - 70, 7.0,
                                    FacingDirection.RIGHT, "light", ground_y=feet_y))
    surf_b = pygame.Surface((900, 520), pygame.SRCALPHA)
    p1.render(surf_b)
    after = pygame.mask.from_surface(surf_b).count()

    assert after > before + 200, "Akuma.render must draw the fireball's pixels"
