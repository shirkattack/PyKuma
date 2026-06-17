"""CPU AI opponent: deterministic decision logic + it actually fights.

The AI feeds inputs into the normal pipeline (it doesn't bypass the state
machine) and must stay deterministic (the engine has no RNG).
"""

import os
import sys
from types import SimpleNamespace as NS

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from street_fighter_3rd.systems.ai_controller import AIController
from street_fighter_3rd.data.enums import InputDirection, Button


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _me(x=300, grounded=True):
    return NS(x=x, is_grounded=grounded)


def _opp(x, grounded=True, attacking=False):
    return NS(x=x, is_grounded=grounded, is_attacking=lambda: attacking)


# --- unit: decision per state -------------------------------------------------

def test_far_opponent_approaches():
    c = AIController()
    dirs = [c.decide(_me(100), _opp(700))[0] for _ in range(120)]
    assert dirs.count(InputDirection.FORWARD) > 10, "should mostly walk forward when far"


def test_blocks_incoming_attack_up_close():
    c = AIController()
    d, btns = c.decide(_me(300), _opp(360, attacking=True))
    assert d == InputDirection.BACK and not btns, "hold back to block a close attack"


def test_anti_airs_airborne_opponent():
    c = AIController()
    seq = [c.decide(_me(300), _opp(360, grounded=False)) for _ in range(3)]
    # a Shoryuken motion: forward, down, down-forward + a punch
    assert [s[0] for s in seq] == [InputDirection.FORWARD, InputDirection.DOWN, InputDirection.DOWN_FORWARD]
    assert any(b in s[1] for s in seq for b in
               (Button.LIGHT_PUNCH, Button.MEDIUM_PUNCH, Button.HEAVY_PUNCH))


def test_pokes_when_in_range():
    c = AIController()
    pressed = set()
    for _ in range(60):
        pressed |= set(c.decide(_me(300), _opp(380))[1])
    assert pressed, "should throw out pokes in normal range"


# --- integration: the CPU actually fights, deterministically ------------------

def _normal_game():
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    return Game(pygame.display.get_surface(), GameModeManager(GameMode.NORMAL))


def test_cpu_opponent_is_active():
    g = _normal_game()
    states, xs = set(), set()
    for _ in range(400):
        g.update()
        states.add(g.player2.state)
        xs.add(round(g.player2.x))
    non_idle = states - {g.player2.state.__class__.STANDING}
    assert len(non_idle) >= 3, f"CPU should do several actions, saw {states}"
    assert len(xs) > 3, "CPU should move around"


def test_cpu_match_is_deterministic():
    def timeline():
        g = _normal_game()
        t = []
        for _ in range(200):
            g.update()
            t.append((round(g.player2.x, 2), g.player2.state, round(g.player2.health)))
        return t
    assert timeline() == timeline(), "CPU runs must be identical (no RNG)"
