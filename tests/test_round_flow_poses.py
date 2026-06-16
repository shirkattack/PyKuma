"""Round-flow poses: intro at round start, win pose on K.O., time-over pose.

These animations existed as assets but were never driven by the round manager.
Uses NORMAL mode (TRAINING/DEV are no_rounds=True, so the round flow is skipped).
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from street_fighter_3rd.data.enums import GameState, RoundResult


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _to_fighting(g, limit=200):
    for _ in range(limit):
        g.update()
        if g.round_manager.game_state == GameState.FIGHTING:
            return True
    return False


def test_intro_plays_during_pre_round():
    g = new_game("NORMAL")
    g.update()  # first pre-round frame
    assert g.round_manager.game_state == GameState.PRE_ROUND
    assert g.player1.animation_controller.current_name == "intro1"
    assert g.player2.animation_controller.current_name == "intro1"


def test_winner_plays_win_pose_on_ko():
    g = new_game("NORMAL")
    assert _to_fighting(g), "should reach FIGHTING"
    g.player2.health = 0           # P1 wins by K.O.
    g.update()
    assert g.round_manager.game_state == GameState.ROUND_END
    assert g.round_manager.round_winner == 1
    assert g.player1.animation_controller.current_name == "win1"


def test_time_over_plays_timeout_pose_on_loser():
    g = new_game("NORMAL")
    assert _to_fighting(g)
    # force the timer to expire this frame, P1 ahead on health
    g.round_manager.timer_seconds = 1
    g.round_manager.timer_frames = 10 ** 6
    g.player1.health, g.player2.health = 900, 500
    g.update()
    assert g.round_manager.round_result == RoundResult.TIME_OVER
    assert g.player1.animation_controller.current_name == "win1"      # winner
    assert g.player2.animation_controller.current_name == "timeout"   # loser
