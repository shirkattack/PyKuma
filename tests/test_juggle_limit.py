"""G1: a launched opponent can't be juggled forever.

A juggle counter caps the number of air-hits per airborne sequence (further hits
whiff), each re-launch pops progressively lower, and the counter resets on
landing. Without the cap, repeatedly hitting an airborne opponent landed an
unbounded number of hits (the infinite juggle).
"""

import os
import sys
from types import SimpleNamespace

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from street_fighter_3rd.characters.character import (
    apply_reaction, LAUNCH_VELOCITY, JUGGLE_LIMIT,
    JUGGLE_LAUNCH_DECAY, JUGGLE_LAUNCH_FLOOR)
from street_fighter_3rd.data.enums import CharacterState, HitEffect


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def test_repeated_air_hits_are_capped():
    g = new_game()
    p1, p2 = g.player1, g.player2
    p1.x, p2.x = 320, 360
    p1._transition_to_state(CharacterState.HEAVY_PUNCH)  # a JUGGLE launcher
    hs = SimpleNamespace(damage=20, hitstun=12)

    hits_landed = 0
    for _ in range(12):
        p1.attack_connected = False           # simulate a fresh attack each time
        before = p2.health
        g.collision_system._apply_hit_to_character(p1, p2, hs, None)
        if p2.health < before:
            hits_landed += 1

    # launch + (JUGGLE_LIMIT-1) follow-ups connect, then air-hits whiff.
    assert hits_landed == JUGGLE_LIMIT, f"expected {JUGGLE_LIMIT} hits, got {hits_landed}"
    assert p2.juggle_count <= JUGGLE_LIMIT


def test_each_relaunch_pops_lower():
    g = new_game()
    p2 = g.player2
    speeds = []
    for jc in range(4):
        p2.juggle_count = jc
        apply_reaction(p2, HitEffect.JUGGLE, 12)
        speeds.append(p2.velocity_y)
    # |launch velocity| strictly decreases with juggle count, down to the floor.
    assert speeds[0] == LAUNCH_VELOCITY
    assert all(abs(speeds[i]) < abs(speeds[i - 1]) for i in range(1, 3))
    assert abs(speeds[-1]) >= abs(LAUNCH_VELOCITY) * JUGGLE_LAUNCH_FLOOR - 0.001


def test_juggle_count_resets_on_landing():
    g = new_game()
    p2 = g.player2
    p2.juggle_count = JUGGLE_LIMIT
    apply_reaction(p2, HitEffect.JUGGLE, 12)   # launches; airborne
    assert not p2.is_grounded
    for _ in range(200):                        # fall back to the floor
        p2.update(g.player1)
        if p2.is_grounded:
            break
    assert p2.is_grounded, "should have landed"
    assert p2.juggle_count == 0, "landing must reset the juggle counter"
