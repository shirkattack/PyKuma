"""ROM move-duration conformance.

THE MECHANICAL TIMING IS THE RULER. Attack states used to end when their
animation finished, so every animation-length error was silently a
gameplay-timing error (s.MP ran ~16 frames instead of the ROM's 22). Normals
now exit at the ROM-verified total from the hitbox repository; these tests
pin that contract for every grounded normal + OVERHEAD, and cross-check it
through the Frame Lab so the measured-vs-declared diff comes back clean on
all timing channels.

Runs the REAL game (headless) with the REAL Akuma — no stubs — so a state
machine, animation controller, or repository regression shows up here.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.data.hitbox_repository import HitboxRepository

GROUNDED_NORMALS = [
    CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH,
    CharacterState.HEAVY_PUNCH, CharacterState.LIGHT_KICK,
    CharacterState.MEDIUM_KICK, CharacterState.HEAVY_KICK,
    CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_MEDIUM_PUNCH,
    CharacterState.CROUCH_HEAVY_PUNCH, CharacterState.CROUCH_LIGHT_KICK,
    CharacterState.CROUCH_MEDIUM_KICK, CharacterState.CROUCH_HEAVY_KICK,
    CharacterState.OVERHEAD,
]


@pytest.fixture
def game():
    # Per-test init, matching the suite's convention: other tests call
    # pygame.quit() in teardown, which invalidates any fonts/surfaces created
    # under a previous init — so a shared module-scoped Game dies mid-suite.
    # We also never call game.render(): duration is measured from update()
    # alone, keeping these tests independent of the font/display lifecycle.
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.core.game import Game
    g = Game(screen, GameModeManager(GameMode.TRAINING))
    g.show_frame_meter = True  # keeps the Frame Lab observing
    # Whiff range: duration must be measured without hitstop complications.
    g.player2.x = g.player1.x + 400
    return g


def rom_total(state) -> int:
    move = HitboxRepository.instance().get_move_by_state(state.name)
    assert move is not None, f"no ROM record for {state.name}"
    return int(move.timing["total"])


def start_move(game, state):
    """Enter a move the way real gameplay orders it: the transition lands
    inside the frame, so state_frame 0 is observed by that frame's end.
    (Forcing the transition between frames would skip frame 0 and shave one
    frame off both the duration count and the Frame Lab's measurement.)"""
    p1 = game.player1
    p1._transition_to_state(state)
    p1.state_frame = -1  # first update increments to 0, mirroring live input


def settle(game, frames=40):
    for _ in range(frames):
        game.update()


@pytest.mark.parametrize("state", GROUNDED_NORMALS, ids=lambda s: s.name)
def test_normal_runs_exactly_rom_total(game, state):
    settle(game)
    assert game.player1.state == CharacterState.STANDING

    expected = rom_total(state)
    start_move(game, state)
    frames_in_state = 0
    for _ in range(expected + 30):  # generous ceiling; loop exits on recovery
        game.update()
        if game.player1.state == state:
            frames_in_state += 1
        else:
            break
    assert frames_in_state == expected, (
        f"{state.name}: spent {frames_in_state} frames in state, "
        f"ROM total is {expected}")
    assert game.player1.state in (CharacterState.STANDING,
                                  CharacterState.CROUCHING), \
        f"{state.name} must recover to a neutral posture"


def test_frame_lab_measures_medium_punch_clean(game):
    """End-to-end: the Frame Lab's measured S/A/R/T must now MATCH the ROM
    declaration — zero discrepancies on any timing channel. (sprite_timing
    may legitimately fire until animations are refitted to the ROM totals.)"""
    settle(game)
    start_move(game, CharacterState.MEDIUM_PUNCH)
    settle(game, rom_total(CharacterState.MEDIUM_PUNCH) + 10)

    report = game.frame_lab.last_reports[1]
    assert report is not None and report.move == "MEDIUM_PUNCH"
    assert (report.startup, report.active, report.recovery,
            report.total) == (5, 4, 13, 22), report.summary()

    timing = [d for d in report.discrepancies
              if d["channel"] in ("startup", "active", "recovery", "total")]
    assert timing == [], f"timing channels must be clean: {timing}"


def test_specials_still_end_on_animation(game):
    """Specials are deliberately NOT ROM-timed (no mapped ROM record; their
    movement/projectile logic is animation-coupled). Guard that they still
    recover on animation completion rather than hanging or being truncated."""
    settle(game)
    start_move(game, CharacterState.GOHADOKEN)
    for _ in range(120):
        game.update()
        if game.player1.state != CharacterState.GOHADOKEN:
            break
    assert game.player1.state != CharacterState.GOHADOKEN, \
        "Gohadoken must still recover via its animation"
