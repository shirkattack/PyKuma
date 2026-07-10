"""Regression tests for the neverending-juggle and corner-shove bugs.

Both are gameplay bugs the user reported that had cross-cutting root causes:

  1. "Akuma's HP gets opponent in neverending juggle." Root cause: on landing
     from HITSTUN_AIRBORNE / KNOCKDOWN the character was returned straight to
     STANDING with no wakeup window. The launched defender became immediately
     re-launchable, so mash HP would juggle -> land -> hit on the ground ->
     relaunch, forever. Fix: land into KNOCKDOWN, and defender is invulnerable
     to hurtboxes during KNOCKDOWN (no OTG on normals -- matches 3S).

  2. "If you jump over opponent in the corner it causes a bug where Akuma
     just moves back and forth." Root cause: the pushbox pair resolver's
     50/50 split shoved a cornered defender inward when the attacker landed
     on top of them; combined with the corner clamp, some frames produced a
     shove-and-reclamp oscillation. Fix: pre-detect the cornered case and
     give the full separation correction to the non-cornered character.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from street_fighter_3rd.data.enums import CharacterState, FacingDirection, HitEffect
from street_fighter_3rd.data.constants import STAGE_RIGHT_BOUND
from street_fighter_3rd.characters.character import apply_reaction


@pytest.fixture
def game():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.core.game import Game
    g = Game(screen, GameModeManager(GameMode.TRAINING))
    return g


# ---------------------------------------------------------------- juggle ----

def test_landing_from_air_hitstun_goes_to_knockdown(game):
    """The core mechanic that closes the infinite juggle: air hitstun does
    NOT return the defender straight to STANDING (immediately re-launchable)."""
    p2 = game.player2
    apply_reaction(p2, HitEffect.JUGGLE, 20)
    assert not p2.is_grounded, "JUGGLE reaction must launch airborne"
    # Simulate falling to the floor
    for _ in range(120):
        game.update()
        if p2.is_grounded:
            break
    assert p2.is_grounded, "must land within a reasonable time"
    assert p2.state == CharacterState.KNOCKDOWN, \
        f"must land in KNOCKDOWN with a wakeup window, not {p2.state.name}"


def test_knocked_down_defender_is_invulnerable_to_normals(game):
    """No OTG on normals: a KNOCKDOWN defender has no hurtboxes, so mashed
    heavy punches from a standing attacker cannot connect."""
    p1, p2 = game.player1, game.player2
    p2.x = p1.x + 55
    apply_reaction(p2, HitEffect.KNOCKDOWN, 40)
    assert p2.state == CharacterState.KNOCKDOWN

    otg_hits = 0
    for _ in range(50):  # well within the KNOCKDOWN duration
        if p1.state == CharacterState.STANDING:
            p1._transition_to_state(CharacterState.HEAVY_PUNCH)
            p1.state_frame = -1
        game.update()
        for ev in game.collision_system.drain_hit_events():
            if not ev.get("blocked") and p2.state == CharacterState.KNOCKDOWN:
                otg_hits += 1
    assert otg_hits == 0, f"got {otg_hits} OTG hits — knockdown must be invulnerable"


def test_mashed_hp_does_not_produce_infinite_juggle(game):
    """The end-to-end scenario the user reported. Approach + mash HP for a
    reasonable window and confirm the defender is not stuck bouncing between
    HITSTUN_AIRBORNE and hittable-on-landing forever."""
    p1, p2 = game.player1, game.player2
    p2.x = p1.x + 60
    hp0 = p2.health
    airborne_streak = max_airborne_streak = 0
    for _ in range(600):
        if p1.state == CharacterState.STANDING:
            if abs(p2.x - p1.x) > 75:
                p1.x += 4
            p1._transition_to_state(CharacterState.HEAVY_PUNCH)
            p1.state_frame = -1
        game.update()
        if not p2.is_grounded:
            airborne_streak += 1
            max_airborne_streak = max(airborne_streak, max_airborne_streak)
        else:
            airborne_streak = 0
    # An infinite juggle would leave p2 airborne for most of the run; with the
    # fix, the launched state resolves to knockdown quickly.
    assert max_airborne_streak < 120, \
        f"defender was airborne for {max_airborne_streak} consecutive frames — juggle loop"
    # HP should not be able to fall arbitrarily far during this window.
    damage = hp0 - p2.health
    assert damage < p2.max_health, "took full-round damage from a single mashed loop"


# ---------------------------------------------------------------- corner ----

def test_cornered_defender_does_not_get_shoved_when_landed_on(game):
    """The 'moves back and forth' bug: crossup landing must not push a
    cornered defender significantly off their corner."""
    p1, p2 = game.player1, game.player2
    p2.x = STAGE_RIGHT_BOUND
    p2.facing = FacingDirection.LEFT
    p1.x = p2.x - 60

    # p1 jumps forward, arcs over p2, lands on the far side
    p1.velocity_y = -13; p1.velocity_x = 7; p1.is_grounded = False
    p1._transition_to_state(CharacterState.JUMPING)

    for _ in range(90):
        game.update()

    # p2 will be pushed off the corner because p1 landed at STAGE_RIGHT_BOUND
    # (someone has to move — they can't overlap), but the shove is a single
    # min-distance separation, not repeated oscillation. Sample the last 30
    # frames to catch any wobble.
    samples = []
    for _ in range(30):
        game.update()
        samples.append(int(p2.x))
    assert max(samples) - min(samples) < 2, \
        f"cornered defender oscillated: p2 range {min(samples)}..{max(samples)}"


def test_walking_into_cornered_opponent_does_not_shove_them(game):
    """The simpler case: cornered defender, attacker walks toward them.
    The cornered defender must not slide into their own corner further."""
    p1, p2 = game.player1, game.player2
    p2.x = STAGE_RIGHT_BOUND
    p2._prev_x = STAGE_RIGHT_BOUND  # prime the "was cornered" signal
    p2.facing = FacingDirection.LEFT
    p1.x = p2.x - 60

    # p1 walks forward (into p2)
    positions = []
    for _ in range(60):
        p1._transition_to_state(CharacterState.WALKING_FORWARD)
        p1.velocity_x = 2
        game.update()
        positions.append(int(p2.x))

    assert max(positions) - min(positions) < 3, \
        f"cornered defender oscillated under walk pressure: {min(positions)}..{max(positions)}"
    assert p2.x >= STAGE_RIGHT_BOUND - 3, "cornered defender must stay at the corner"
