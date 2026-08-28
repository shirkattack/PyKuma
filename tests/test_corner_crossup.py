"""Phase 3 (docs/PLAN_OF_ATTACK.md): jumping over a cornered opponent with an
air special must not shove them off the wall, swap the pair every frame
(facing jitter) or leave the attacker in a grounded JUMPING state (freeze)."""

import os

import pygame
import pytest

from street_fighter_3rd.data.constants import STAGE_RIGHT_BOUND
from street_fighter_3rd.data.enums import Button, CharacterState, FacingDirection, InputDirection
from tests.asset_guard import require_assets, ANIMATIONS
from tools.diagnostics.scenario import ScriptedInputSystem, hold

pytestmark = require_assets(ANIMATIONS)


@pytest.fixture(scope="module", autouse=True)
def headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _game(p1x, p2x):
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.core.game import Game
    g = Game(pygame.display.set_mode((896, 512)), GameModeManager(GameMode.TRAINING))
    for _ in range(3):
        g.update()
    for p, x in ((g.player1, p1x), (g.player2, p2x)):
        p.x = x
        p._prev_x = x
    for _ in range(3):
        g.update()          # wall ownership settles
    return g


def _cross_up(g, move, frames=140):
    p1, p2 = g.player1, g.player2
    g.input_system = ScriptedInputSystem(hold(InputDirection.UP_FORWARD, 4) + hold(InputDirection.NEUTRAL, 200),
                                         hold(InputDirection.NEUTRAL, 64) + hold(InputDirection.BACK, 40) + hold(InputDirection.NEUTRAL, 100))
    p1.input, p2.input = g.input_system.player1, g.input_system.player2
    rows = []
    for i in range(frames):
        if i == 16 and move and not p1.is_grounded:
            p1._execute_demon_flip() if move == "flip" else p1._execute_tatsumaki(move)
        g.update()
        rows.append((p1.x, p1.facing, p1.state, p1.is_grounded, p2.x, p2.facing, p2.state))
    return rows


@pytest.mark.parametrize("move", [None, Button.LIGHT_KICK, Button.HEAVY_KICK, "flip"], ids=["jump", "air_LK_tatsu", "air_HK_tatsu", "demon_flip"])
@pytest.mark.parametrize("offset", [50, 70])
def test_cornered_defender_keeps_the_wall_and_nobody_jitters(move, offset):
    g = _game(STAGE_RIGHT_BOUND - offset, STAGE_RIGHT_BOUND)
    rows = _cross_up(g, move)
    # the cornered fighter never leaves the wall
    assert all(r[4] == STAGE_RIGHT_BOUND for r in rows), min(r[4] for r in rows)
    # after touchdown, positions and facings are stable: P1 in front, facing each other
    landed = next(i for i, r in enumerate(rows) if i > 10 and r[3])
    tail = rows[landed + 3:]
    assert len(tail) > 40 and all(r[3] for r in tail)
    assert {round(r[0]) for r in tail} == {STAGE_RIGHT_BOUND - 50}
    assert {r[1] for r in tail} == {FacingDirection.RIGHT} and {r[5] for r in tail} == {FacingDirection.LEFT}
    # no grounded JUMPING (the old freeze until the safety timeout)
    assert not any(r[2] == CharacterState.JUMPING and r[3] for r in rows)


def test_open_field_cross_up_still_switches_sides():
    g = _game(440, 500)
    rows = _cross_up(g, Button.LIGHT_KICK)
    tail = rows[60:]
    assert all(r[0] > r[4] for r in tail)                   # P1 landed behind P2
    assert tail[-1][1] == FacingDirection.LEFT and tail[-1][5] == FacingDirection.RIGHT
    assert rows[104][4] < rows[64][4] - 50                  # P2's held BACK actually walks
