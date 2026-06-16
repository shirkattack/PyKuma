"""BT3: super-meter system + Super Arts (SA1/SA2/SA3), plus projectile damage.

Simple single-bar meter (the chosen model): fills on hits/blocks, a Super Art
costs a full bar. SA1 = 236236P super-fireball burst, SA2 = 236236K launcher,
SA3 = 214214P heavy hit. Also covers the now-wired projectile-vs-character hit.
"""

import os
import sys
from types import SimpleNamespace

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold, qcf
from street_fighter_3rd.data.enums import Button, InputDirection, FacingDirection, CharacterState

D, DF, F = InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD
DB, B = InputDirection.DOWN_BACK, InputDirection.BACK


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _qcf2(b):
    return [(D, []), (DF, []), (F, []), (D, []), (DF, []), (F, [b])]


def _qcb2(b):
    return [(D, []), (DB, []), (B, []), (D, []), (DB, []), (B, [b])]


def _run(motion, full_meter, p1x=300, p2x=440):
    g = new_game()
    g.player1.x, g.player2.x = p1x, p2x
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    if full_meter:
        g.player1.super_meter = 100
    g.input_system = ScriptedInputSystem(hold(InputDirection.NEUTRAL, 2) + motion + hold(None, 95), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    hp0 = g.player2.health
    states = set()
    min_meter = g.player1.super_meter
    for _ in range(98):
        g.update()
        states.add(g.player1.state)
        min_meter = min(min_meter, g.player1.super_meter)
    return g, states, hp0 - g.player2.health, min_meter


def test_meter_gains_on_hit():
    g = new_game()
    g.player1.x, g.player2.x = 320, 360
    g.player1._transition_to_state(CharacterState.HEAVY_PUNCH)
    m0 = g.player1.super_meter
    g.player1.attack_connected = False
    g.collision_system._apply_hit_to_character(
        g.player1, g.player2, SimpleNamespace(damage=20, hitstun=12), None)
    assert g.player1.super_meter > m0, "attacker should gain meter on a hit"


def test_sa1_super_fireball():
    g, states, dmg, min_meter = _run(_qcf2(Button.LIGHT_PUNCH), full_meter=True)
    assert CharacterState.SUPER_ART_1 in states
    assert min_meter == 0, "the super spends the full bar (may rebuild from its own hits)"
    assert dmg > 0, "super fireball should damage (projectile collision)"


def test_sa2_launcher_and_sa3_heavy():
    _, s2, d2, _ = _run(_qcf2(Button.LIGHT_KICK), full_meter=True, p2x=390)
    assert CharacterState.SUPER_ART_2 in s2 and d2 > 0
    _, s3, d3, _ = _run(_qcb2(Button.LIGHT_PUNCH), full_meter=True, p2x=390)
    assert CharacterState.SUPER_ART_3 in s3 and d3 > 0


def test_no_super_without_meter():
    g, states, _, _ = _run(_qcf2(Button.LIGHT_PUNCH), full_meter=False)
    assert not any(s.name.startswith("SUPER_ART") for s in states), \
        "without a full bar, 236236P must not super (falls through to a fireball)"


def test_projectile_now_damages():
    # The normal Gohadoken had no collision; it should now deal its damage.
    g = new_game()
    g.player1.x, g.player2.x = 300, 480
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    g.input_system = ScriptedInputSystem(qcf(Button.LIGHT_PUNCH) + hold(None, 95), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    hp0 = g.player2.health
    for _ in range(95):
        g.update()
    assert g.player2.health < hp0, "a Gohadoken that reaches the opponent should damage them"
