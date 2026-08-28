"""Phase 1 (docs/PLAN_OF_ATTACK.md): multi-hit moves apply each ROM hit
window's own values, the combo scaling does not step down between the windows
of ONE move, and the Frame Lab diffs every hit against its own window."""

import os

import pygame
import pytest

from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.systems.sf3_combo_system import SF3ComboSystem
from tests.asset_guard import require_assets, ANIMATIONS

pytestmark = require_assets(ANIMATIONS)


@pytest.fixture
def game():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.core.game import Game
    g = Game(screen, GameModeManager(GameMode.TRAINING))
    g.show_frame_meter = True
    return g


def _run(game, state, gap, frames=170):
    game.player2.x = game.player1.x + gap
    for _ in range(40):
        game.update()
    game.player1._transition_to_state(state)
    game.player1.state_frame = -1
    for _ in range(frames):
        game.update()
        if (game.frame_lab.last_reports.get(1) is not None
                and game.frame_lab.captures.get(1) is None and not game.frame_lab._watches):
            break
    return game.frame_lab.last_reports[1]


def test_close_hk_applies_each_rom_window_without_double_scaling(game):
    report = _run(game, CharacterState.HEAVY_KICK, gap=60)
    hits = [h for h in report.hits if not h.blocked]
    assert [(h.window, h.raw_damage, h.hitstun) for h in hits] == [(0, 21, 35), (1, 12, 19)]
    # the second window's ROM value is what the game applied inside the move: no 90% step
    assert [h.scaled_damage for h in hits] == [21, 12]
    assert not [d for d in report.discrepancies if d["channel"] in ("damage", "hitstun")], report.discrepancies


def test_combo_scaling_anchors_at_a_moves_first_hit():
    cs = SF3ComboSystem()
    assert cs.register_hit(1, 2, 100, "normal") == 100                                   # hit 1 of move A
    assert cs.register_hit(1, 2, 100, "normal", defender_in_hitstun=True, same_move=True) == 100   # hit 2, same move
    assert cs.register_hit(1, 2, 100, "normal", defender_in_hitstun=True) == 80         # move B: combo hit 3 -> 80%
    assert cs.register_hit(1, 2, 100, "normal", defender_in_hitstun=True, same_move=True) == 80    # B's 2nd window
    assert cs.player_combo_states[2].combo_count == 4
    assert cs.register_hit(1, 2, 100, "normal", defender_in_hitstun=False) == 100       # recovered: fresh combo
