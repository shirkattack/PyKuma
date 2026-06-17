"""Tiered AI "boss" profiles: deterministic, distinct, and monotonically harder.

Phase A: profiles differ by reaction delay, accuracy, spacing/cadence, capability
gating, and super usage. Determinism (no RNG) must hold per tier.
"""

import os
import sys
from types import SimpleNamespace as NS

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from street_fighter_3rd.core.game import Game
from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
from street_fighter_3rd.systems.ai_controller import AIController, AIPlayerInput
from street_fighter_3rd.systems.ai_profiles import (
    PROFILES, get_profile, selectable_profiles, DEFAULT_PROFILE)
from street_fighter_3rd.data.enums import InputDirection


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _game(difficulty):
    return Game(pygame.display.get_surface(), GameModeManager(GameMode.NORMAL),
                cpu_difficulty=difficulty)


def _timeline(difficulty, frames=200):
    g = _game(difficulty)
    t = []
    for _ in range(frames):
        g.update()
        t.append((round(g.player2.x, 2), g.player2.state, round(g.player2.health)))
    return t


def _head_to_head(p1_diff, p2_diff, frames=1200):
    g = _game(p2_diff)
    ai1 = AIPlayerInput(1, me=g.player1, opponent=g.player2, profile=get_profile(p1_diff))
    g.input_system.player1 = ai1
    g.player1.input = ai1
    for _ in range(frames):
        g.update()
        if g.player1.health <= 0 or g.player2.health <= 0:
            break
    return g.player1.health, g.player2.health


# --- registry sanity ---

def test_profiles_present_and_default_is_brawler():
    for key in ("novice", "brawler", "technician", "veteran", "master", "shin_akuma"):
        assert key in PROFILES
    assert DEFAULT_PROFILE == "brawler"
    # Shin Akuma is the locked final boss; not offered in the selector.
    assert PROFILES["shin_akuma"].locked
    assert "shin_akuma" not in {p.key for p in selectable_profiles()}


# --- determinism (no RNG) ---

@pytest.mark.parametrize("difficulty", ["novice", "brawler", "master"])
def test_each_tier_is_deterministic(difficulty):
    assert _timeline(difficulty) == _timeline(difficulty), \
        f"{difficulty} must be reproducible (fixed seed, no wall-clock RNG)"


# --- tiers are actually different ---

def test_tiers_are_distinct():
    assert _timeline("novice") != _timeline("master"), "tiers should play differently"


# --- monotonic challenge (head-to-head) ---

def test_stronger_tier_beats_weaker():
    # Master vs Novice: Master should end with more health (and usually a KO).
    h1, h2 = _head_to_head("novice", "master")
    assert h2 > h1, f"Master should out-fight Novice (P1 novice={h1}, P2 master={h2})"


def test_brawler_matches_today_via_default_controller():
    # A bare AIController() defaults to Brawler and stays active/usable.
    c = AIController()
    assert c.profile.key == "brawler"
    # far opponent -> approaches forward at least sometimes
    dirs = [c.decide(NS(x=100, is_grounded=True),
                     NS(x=700, is_grounded=True, is_attacking=lambda: False))[0]
            for _ in range(120)]
    assert dirs.count(InputDirection.FORWARD) > 10


# --- reaction-delay buffer returns delayed perception ---

def test_reaction_delay_perceives_the_past():
    prof = get_profile("novice")  # reaction_frames = 14
    c = AIController(profile=prof)
    me = NS(x=300, is_grounded=True)
    # Opponent teleports far on frame 1, then we observe what the AI "sees".
    for f in range(5):
        opp = NS(x=(900 if f == 0 else 305), is_grounded=True, is_attacking=lambda: False)
        x_seen, _, _ = c._perceive(opp)
    # With a 14-frame delay and only 5 frames of history, perception is still the
    # oldest snapshot (the far x=900), not the recent close one.
    assert x_seen == 900, "delayed perception should lag behind current state"
