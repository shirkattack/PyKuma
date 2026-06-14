"""Tests for the diagnostics + logging infrastructure."""

import logging

import pygame
import pytest

from street_fighter_3rd.core.diagnostics import InvariantChecker, FrameRecorder
from street_fighter_3rd.util import logging_config


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture
def game():
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT
    gmm = GameModeManager(GameMode.NORMAL)
    gmm.config.no_rounds = True
    return Game(pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)), gmm)


def test_clean_game_has_no_violations(game):
    checker = InvariantChecker()
    for _ in range(30):
        game.update()
        checker.check(game)
    ok, last = checker.last_status()
    assert ok, f"clean run should have no invariant violations, got {last}"


def test_health_out_of_bounds_flagged(game):
    checker = InvariantChecker()
    game.player2.health = -5
    checker.check(game)
    assert any(v.type == "health_oob" and v.player == 2 for v in checker.recent(10))


def test_nan_velocity_flagged(game):
    checker = InvariantChecker()
    game.player1.velocity_x = float("nan")
    checker.check(game)
    assert any(v.type == "nan_inf" and v.player == 1 for v in checker.recent(10))


def test_feet_off_floor_flagged(game):
    checker = InvariantChecker()
    game.player1.y = 200          # well above the floor line
    game.player1.is_grounded = True
    checker.check(game)
    assert any(v.type == "feet_off_floor" for v in checker.recent(10))


def test_violation_is_serializable(game):
    checker = InvariantChecker()
    game.player1.health = 9999
    checker.check(game)
    v = checker.recent(1)[0]
    d = v.as_dict()
    assert {"frame", "type", "severity", "player", "values"} <= set(d)


def test_frame_recorder_ring(game):
    rec = FrameRecorder(ring=5)
    for _ in range(8):
        game.update()
        rec.record(game)
    assert len(rec.ring) == 5  # bounded
    assert len(rec.recent(3)) == 3


def test_log_once_emits_once(caplog):
    logging_config.reset_log_once()
    log = logging_config.get_logger("street_fighter_3rd.test_once")
    with caplog.at_level(logging.WARNING, logger="street_fighter_3rd.test_once"):
        for i in range(4):
            logging_config.log_once(log, ("dup",), logging.WARNING, "msg %d", i)
    assert sum(1 for r in caplog.records if r.name == "street_fighter_3rd.test_once") == 1


def test_setup_logging_honors_env(monkeypatch):
    monkeypatch.setenv("PYKUMA_LOG", "DEBUG")
    logging_config.setup_logging()
    assert logging.getLogger("street_fighter_3rd").level == logging.DEBUG
