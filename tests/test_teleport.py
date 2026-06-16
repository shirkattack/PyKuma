"""BT1: Ashura Senku teleport (623/421 + PPP or KKK).

Strike-invulnerable reposition forward/back; no hitbox/damage. Disambiguates from
Goshoryuken (623 + single punch).
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

PPP = [Button.LIGHT_PUNCH, Button.MEDIUM_PUNCH, Button.HEAVY_PUNCH]


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _run(motion, p1x=400, p2x=640):
    g = new_game()
    g.player1.x, g.player2.x = p1x, p2x
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    g.input_system = ScriptedInputSystem(hold(InputDirection.NEUTRAL, 2) + motion + hold(None, 50), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    x0 = g.player1.x
    states, invuln = set(), False
    for _ in range(55):
        g.update()
        states.add(g.player1.state)
        if g.player1.state == CharacterState.ASHURA_SENKU:
            invuln = invuln or g.player1.is_invincible
    return g, states, g.player1.x - x0, invuln


def test_forward_teleport_623_ppp():
    g, states, dx, invuln = _run([(InputDirection.FORWARD, []), (InputDirection.DOWN, []),
                                   (InputDirection.DOWN_FORWARD, PPP)])
    assert CharacterState.ASHURA_SENKU in states
    assert dx > 100, "forward teleport should move forward a good distance"
    assert invuln, "teleport should be invulnerable"
    assert g.player1.state == CharacterState.STANDING, "should recover"


def test_back_teleport_421_ppp():
    g, states, dx, _ = _run([(InputDirection.BACK, []), (InputDirection.DOWN, []),
                             (InputDirection.DOWN_BACK, PPP)])
    assert CharacterState.ASHURA_SENKU in states
    assert dx < -100, "back teleport should move backward"


def test_single_dp_punch_is_goshoryuken_not_teleport():
    g, states, _, _ = _run([(InputDirection.FORWARD, []), (InputDirection.DOWN, []),
                            (InputDirection.DOWN_FORWARD, [Button.LIGHT_PUNCH])])
    assert CharacterState.GOSHORYUKEN in states
    assert CharacterState.ASHURA_SENKU not in states


def test_invincible_defender_is_not_hit():
    # An invulnerable defender must take no damage from an active attack.
    from types import SimpleNamespace
    g = new_game()
    p1, p2 = g.player1, g.player2
    p1.x, p2.x = 320, 360
    p1._transition_to_state(CharacterState.HEAVY_PUNCH)
    p2.is_invincible = True
    hp0 = p2.health
    p1.attack_connected = False
    g.collision_system._apply_hit_to_character(p1, p2, SimpleNamespace(damage=50, hitstun=12), None)
    assert p2.health == hp0, "invulnerable defender should take no damage"
